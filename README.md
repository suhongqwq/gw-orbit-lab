# 引力波轨道实验室 · GW Orbit Lab

拖动天体，按下播放，看看双星怎样越转越快，或者让一颗小天体在黑洞旁画出进动花瓣。支持双星、三体和 Schwarzschild 测地线三种模式。

**[在线试玩](https://suhongqwq.github.io/gw-orbit-lab/)** · 下载 `index.html` 也可离线打开

## 并合前的啁啾

![GW150914 质量预设的频率优先 STFT 长窗时频图，亮色谱带在并合参考时刻之前逐渐上升](docs/images/gw150914-chirp.png)

*运行 GW150914 的质量预设。播放到示意并合后，勾选「并合前视图」，即可在默认的频率优先长窗下观察上扬的亮带。也可以切到时间优先短窗或 CQT。*

## 黑洞旁的进动花瓣

![典型 EMRI 预设在 Schwarzschild 时空中的蓝色进动轨迹](docs/images/emri-orbit.png)

*从预设菜单选「典型 EMRI」。每圈的近心点都在转动，轨迹逐渐画出花瓣。*

二维、无初始自旋的教学玩具模型。双星和三体可选有限阶后牛顿近似，Schwarzschild 使用固定背景测地线。完整数值相对论演化超出模型范围。

## 模型与参考文献

- **轨道与耗散**。双星在标准谐和坐标下使用最高 3PN 的无自旋保守动力学，可开启最低阶 2.5PN 辐射反作用。三体在两两牛顿引力上，可对中心天体与小天体逐对加入 1PN 和 2.5PN 项。 [Blanchet，式 219–220](https://arxiv.org/html/1310.1528v4) · [Arun 等，式 3.6 的 2.5PN 项](https://arxiv.org/abs/0908.3854)
- **引力波与偏心率**。波形使用主导质量四极矩。双星的径向偏心率每个完整径向周期由近、远心距离估计。 [LIGO–Virgo，四极矩推导](https://dcc.ligo.org/public/0126/P1600161/013/BBHBasicsANDPFullAuth.pdf) · [Memmesheimer 等，径向偏心率定义](https://arxiv.org/abs/gr-qc/0407049)
- **Schwarzschild 测地线**。用 Darwin 参数化积分固定背景中的稳定束缚轨道，波形由坐标轨道代入四极矩公式估算。 [Vega 等，§II A 测地线方程](https://arxiv.org/html/1307.3476v2#S2.SS1)
- **并合与铃宕**。示意过渡接到 Kerr 基频 (2, 2, 0) 的指数衰减波形。剩余黑洞质量和自旋取 UIB2016 的零初始自旋拟合，频率和阻尼时间由准正规模拟合得到。 [Jiménez-Forteza 等，UIB2016](https://arxiv.org/abs/1611.00332) · [Berti 等，表 VIII](https://arxiv.org/abs/gr-qc/0512160)
- **时频分析**。STFT 使用 Hann 窗。CQT 按对数频率取点，使用随频率缩短的 Hann 窗，窗长为该频率的八个周期。 [Harris，Hann 窗](https://doi.org/10.1109/PROC.1978.10837) · [Brown，常 Q 变换](https://www.ee.columbia.edu/~dpwe/papers/Brown91-cqt.pdf)
