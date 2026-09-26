# B_L1｜持久化脚印压痕与 POM：公开数值契约 v0.1


## 压痕状态与事件

域为世界 XZ 平面，边界、纹素大小来自 config。深度 `d>=0` 表示位于基准 y=0 下方，初始 d=0。印章为作者提供的线性 [0,1] 单通道遮罩 M，双线性读取、遮罩外为 0。每个事件包含唯一 event_id、世界中心、平面旋转角、正的长宽和 depth_increment>=0。

按事件的逆平面变换将世界位置映射到 M，更新 `d_new=min(d_max,d_old+depth_increment*M)`。越出地面部分裁掉，不环绕。事件仅应用一次；同一 ID 重发不累加。不同 ID 的重复踩踏可以加深。d_max>0，且每轮无自动恢复。

## POM 的唯一几何含义

视线 V 为从基准表面指向相机的单位向量，分量基于 (+X,+Y,+Z)，有效域 Vy>=0.1。深度参数 s>=0 的视线点在地面平面上为 `xz(s)=xz0-s*(Vx,Vz)/Vy`，高度为 -s。

沿该射线找 `s=d(xz(s))` 的最小有效交点，s 在 [0,d_max]，d 按双线性插值。跨域离开时返回 valid=false；不能把越界点 clamp 成边缘脚印。零深度在 s=0 命中。公开误差预算允许步进/细化近似，不固定唯一循环组织；必须使用 POM 类的高度场沿视线交点，而不是固定 UV 偏移。

接口 `stamp_query(events,grid)` 输出 depth_field；`pom_query(xz0,V,depth_field)` 输出 valid、hit_depth、hit_uv、hit_xz。画面必须使用同一 depth_field 和同一 POM 结果。压力感颜色可以调节，但不能作为唯一压痕实现。
