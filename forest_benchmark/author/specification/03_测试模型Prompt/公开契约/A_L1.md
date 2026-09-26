# A_L1｜程序灼烧与焦化：公开数值契约 v0.1


## 输入与确定性

`burn_query(points_ref, time, params)`；params 包含 origin_ref、R0、speed、noise_amplitude、base_frequency、octaves、gain、lacunarity、width、enabled，以及置换表 P 与梯度表 G。所有方向/距离以对象参考空间定义；本级参考空间保持单位尺度。

本版梯度噪声定义：P 是运行输入提供的 0..255 的排列，索引按 256 环绕。格点 (i,j,k) 的梯度索引是 `P[(P[(P[i mod 256]+j) mod 256]+k) mod 256] mod 12`。G 按顺序为 `(1,1,0),(-1,1,0),(1,-1,0),(-1,-1,0),(1,0,1),(-1,0,1),(1,0,-1),(-1,0,-1),(0,1,1),(0,-1,1),(0,1,-1),(0,-1,-1)`，不归一化。格点贡献为梯度与点到格点偏移的点积，三轴以 `6u^5-15u^4+10u^3` 插值。这里给出数学变体是为使输出唯一，不提供实现代码。P 的具体排列是公开输入数据；不要求你实现生成排列的随机数器。

`F(p)=sum(gain^k * N(base_frequency*lacunarity^k*p))/sum(gain^k)`，k=0..octaves-1，不额外映射到 [0,1]。频率和 octave 数为合法正值，gain 在 [0,1]，分母包含 k=0 的 1。

## 状态定义

`R(t)=R0+speed*(t-t0)`；`q=R(t)-length(p-origin_ref)+noise_amplitude*F(p)`。

`b=smoothstep(-width,+width,q)`，`a=4*b*(1-b)`，width>0。b 为累计焦化程度，a 为活动前沿强度。enabled=false 时 b=a=0。噪声在整个 run 内不随时间改变；合法的单调性测试仅对 speed>=0、其他参数固定的运行成立。reset 才开始新一轮灼烧。

输出 `noise, signed_front, char_fraction, front_strength`。前沿、焦化的材质颜色/发光采用公开美术参数，但必须以 b/a 驱动；不要用全局曝光增强前沿。隐藏测试也会查询负坐标与对象相机运动后的同一参考点。
