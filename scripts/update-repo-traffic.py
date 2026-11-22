"""Update the public GW Orbit Lab traffic summary from GitHub's rolling window."""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ONE_DAY = timedelta(days=1)


def utc_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Expected a UTC date in YYYY-MM-DD format.")
    return date.fromisoformat(value)


def count_value(value):
    if type(value) is not int or value < 0:
        raise ValueError("Expected a nonnegative integer page-view count.")
    return value


def daily_views(payload, today):
    if not isinstance(payload, dict) or not isinstance(payload.get("views"), list):
        raise ValueError("Expected the GitHub traffic API's daily views response.")
    counts = {}
    for view in payload["views"]:
        if not isinstance(view, dict) or not isinstance(view.get("timestamp"), str):
            raise ValueError("A GitHub traffic row has no timestamp.")
        timestamp = datetime.fromisoformat(view["timestamp"].replace("Z", "+00:00"))
        day = timestamp.date()
        if timestamp.utcoffset() != timedelta(0) or timestamp.time() != time.min or day > today or day in counts:
            raise ValueError("GitHub traffic rows must have distinct dates at 00:00 UTC, through today.")
        counts[day] = count_value(view.get("count"))
    if count_value(payload.get("count")) != sum(counts.values()):
        raise ValueError("GitHub's window total does not match the daily page-view counts.")
    return counts


def update_summary(existing, payload, since, today):
    if since > today:
        raise ValueError("The starting date is in the future.")
    counts = daily_views(payload, today)
    sealed_through = since - ONE_DAY
    observed = sealed_through
    sealed_total = 0
    previous_total = 0
    coverage = True
    if existing is not None:
        if not isinstance(existing, dict) or utc_date(existing.get("since")) != since:
            raise ValueError("The previous summary has a different starting date.")
        sealed_through = utc_date(existing.get("sealedThrough"))
        sealed_total = count_value(existing.get("sealedTotal"))
        previous_total = count_value(existing.get("total"))
        observed = utc_date(existing.get("lastObserved"))
        coverage = existing.get("coverageComplete")
        if not (since <= observed <= today and type(coverage) is bool and
                sealed_through == max(since - ONE_DAY, observed - 2 * ONE_DAY) and
                sealed_total <= previous_total and
                (sealed_through >= since or sealed_total == 0)):
            raise ValueError("The previous summary has an invalid checkpoint.")

    # The official rolling window is 14 days. Use the 13 UTC dates before
    # today when inferring zero-volume dates from omissions, so this remains
    # conservative whether a partial row for today is present or absent.
    unsealed_start = sealed_through + ONE_DAY
    seal_target = max(sealed_through, today - 2 * ONE_DAY)
    oldest_guaranteed = today - 13 * ONE_DAY
    # A returned row on the older edge of the rolling window contributes to
    # the total, but the API does not guarantee coverage of that entire day.
    coverage = coverage and unsealed_start >= oldest_guaranteed
    newly_sealed = sum(count for day, count in counts.items() if unsealed_start <= day <= seal_target)
    if unsealed_start <= observed and unsealed_start < oldest_guaranteed:
        # A long outage can put the previous two provisional days outside the
        # rolling window. Preserve the larger aggregate for those same dates.
        recovered_overlap = sum(count for day, count in counts.items() if unsealed_start <= day <= observed)
        newly_sealed += max(0, previous_total - sealed_total - recovered_overlap)
    # Only a single aggregate is carried forward. The most recent two days
    # are read afresh on each run instead of accumulating partial counts.
    sealed_total += newly_sealed
    total = sealed_total + sum(count for day, count in counts.items() if seal_target < day <= today)
    return {"since": since.isoformat(), "total": total, "lastObserved": today.isoformat(),
            "coverageComplete": coverage, "sealedThrough": seal_target.isoformat(), "sealedTotal": sealed_total}


def render_badge(summary):
    """Render a standalone SVG from an already collected public summary."""
    total = count_value(summary.get("total"))
    complete = summary.get("coverageComplete")
    if not isinstance(complete, bool):
        raise ValueError("Expected a boolean coverage status for the repository traffic badge.")
    value = f"{total:,}{'' if complete else '+'}"
    title = f"Repository views: {value}" + (" (coverage incomplete)" if not complete else "")
    label_width = 75
    value_width = max(35, 16 + 7 * len(value))
    width = label_width + value_width
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="22" viewBox="0 0 {width} 22" role="img" aria-labelledby="title">
  <title id="title">{title}</title>
  <clipPath id="frame"><rect width="{width}" height="22" rx="4"/></clipPath>
  <g clip-path="url(#frame)">
    <rect width="{width}" height="22" fill="#303b4d"/>
    <rect x="{label_width}" width="{value_width}" height="22" fill="#2b584e"/>
  </g>
  <g fill="#f8fafc" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" font-weight="600" aria-hidden="true">
    <text x="{label_width / 2:g}" y="15">Repo views</text>
    <text x="{label_width + value_width / 2:g}" y="15">{value}</text>
  </g>
</svg>
'''


def replace_text(path, content):
    scratch = path.with_name(f".{path.name}.tmp")
    scratch.write_text(content, encoding="utf-8", newline="\n")
    scratch.replace(path)


class RefuseRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_views(repository, token):
    if not repository or not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Set the repository to OWNER/REPO.")
    if not token:
        raise ValueError("Set TRAFFIC_READ_TOKEN to a fine-grained token with repository Administration: Read permission.")
    request = Request(f"https://api.github.com/repos/{repository}/traffic/views?per=day", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "gw-orbit-lab-traffic-collector",
    })
    with build_opener(RefuseRedirects()).open(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", required=True, help="UTC release date in YYYY-MM-DD format")
    parser.add_argument("--output", required=True, type=Path, help="Existing and updated public summary file")
    parser.add_argument("--badge", type=Path, help="Also write an SVG badge using the same summary")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"), help="OWNER/REPO for a live request")
    parser.add_argument("--input", help="Read a trusted traffic API export from a file or '-' for stdin")
    parser.add_argument("--today", help="UTC observation date for an API export")
    args = parser.parse_args()
    if args.today and args.input is None:
        parser.error("--today can only be set with --input.")

    try:
        if args.badge is not None and args.badge.resolve() == args.output.resolve():
            raise ValueError("The badge and the JSON summary need different output files.")
        since = utc_date(args.since)
        today = utc_date(args.today) if args.today else datetime.now(timezone.utc).date()
        existing = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else None
        if args.input is None:
            payload = fetch_views(args.repository, os.environ.get("TRAFFIC_READ_TOKEN"))
        elif args.input == "-":
            payload = json.load(sys.stdin)
        else:
            payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        summary = update_summary(existing, payload, since, today)
        if args.badge is not None:
            replace_text(args.badge, render_badge(summary))
        replace_text(args.output, json.dumps(summary, indent=2) + "\n")
    except HTTPError as error:
        reason = (" Check the token's repository access and Administration: Read permission."
                  if error.code in (401, 403, 404) else "")
        print(f"GitHub traffic API returned HTTP {error.code}.{reason}", file=sys.stderr)
        return 1
    except URLError:
        print("Could not connect to the GitHub traffic API.", file=sys.stderr)
        return 1
    except (OSError, OverflowError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Updated the repository traffic summary through {summary['lastObserved']} UTC.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
