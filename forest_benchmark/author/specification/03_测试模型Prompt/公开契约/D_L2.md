# D_L2｜固定接触源的泡沫输运：公开数值契约 v0.1


## 独立数据

源的坐标、泡沫状态采样域、Flow Mapping 图案 UV 是三种独立量。表面位置 s=(x,z) 用米表示，流场 v(s) 与 D_L1 相同输入。

泡沫 f∈[0,1]，初场为零或给定。源 `S(s)=sum(rate_j*max(0,1-(length(s-source_j)/radius_j)^2)^2)`，radius_j>0、rate_j 单位 1/s；source_j 为本 tick 固定世界点投影到表面基的坐标。关闭源仅令 S=0。

本版回溯 `q=s-dt*v(s)`（一次 Euler 回溯）；`f_next(s)=clamp(sample(f_old,q)*exp(-decay*dt)+dt*S(s),0,1)`。decay>=0。sample 在域内双线性、边缘夹到最近单元中心，q 位于域外时取 0（零入流），不环绕。源加入新时刻网格，刚生成泡沫从下一步起参与输运。

真实 dt、域长宽和速度共同决定输运，不能用纹理平铺 K 或相位 P 替代它们。半拉格朗日的数值耗散不自动违反本题；正式判题比较此离散格式，不要求严格质量守恒。

接口 `foam_step(f_old,flow,sources,config)` 输出 f_next/source_field；运行诊断分别公开 source positions、f、L1 phase UV。渲染的泡沫覆盖必须读 f，不能只画源遮罩。
