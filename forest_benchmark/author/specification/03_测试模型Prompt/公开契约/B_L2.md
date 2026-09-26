# B_L2｜压痕约束的湿润扩散与干燥：公开数值契约 v0.1


## 模型

w 为无量纲 [0,1] 湿度；d 是继承的实际脚印深度。`lambda(d)=lambda0/(1+beta*d/d_max)`，lambda0>=0、beta>=0。

本版一步显式更新为 `w_next=clamp(w+dt*(D*Laplacian(w)-lambda(d)*w+S),0,1)`。D 单位 m²/s，lambda 单位 1/s，S 是本 tick 水源率场（1/s）。d 使用本 tick 已处理接触事件后的状态，w 的所有扩散邻居来自同一旧时刻，禁止就地写后读串行更新。

Laplacian 使用 X/Z 五点差分与真实 dx/dz。边界为零通量：缺失邻居取本边界单元值。有效测试配置满足 `dt*(2D/dx²+2D/dz²+lambda0)<=1`。测试不会用违反此条件的输入要求这个显式格式保持稳定。clamp 是公开模型的一部分，但不能在异常不稳定时用它掩盖错误离散。

水接触事件携带 amount 与遮罩，仅在该 tick 加入 `S += amount*M/dt`；持续源直接以 S 输入。事件 ID 按公共契约去重。reset 时 w=0 或给定初场。

接口 `wet_step(w,d,S,params)` 输出 w_next；正常运行输出 depth_field、wetness_field 及实际干燥率。材质粗糙度/底色采用公开的干湿端点按 w 插值，端点由作者配置。不得让湿度反过来无条件清掉脚印深度。
