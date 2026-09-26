# C_L1｜三维云密度驱动的地面云影：公开数值契约 v0.1


## 输入数据与坐标

`cloud_query(points_world,L,density,config)`。L 是从查询点指向光源的单位方向。云体有明确世界到局部的刚体变换、局部 AABB 和线性 float32 非负密度网格；本级只允许平移/旋转，不允许未声明的非均匀缩放。密度三线性采样；AABB 外为 0，内部边界夹到最近体素中心。每一轴坐标、尺寸、布局按公共契约。

光线 `r(s)=p+s*L, s>=0`。与云 AABB 求前向有效区间 [s0,s1]，无交或长度为零时 tau=0、T=1。光线起于云体内时 s0=0；各轴平行时必须正确处理是否在相应 slab 内。

本版正式数值查询指定分段数 N>=1，以 N 个等长区间中点采样。`tau=sigma_t_cloud*sum(rho(r(s_mid))*ds)`；`T=exp(-tau)`。sigma_t_cloud 单位 1/m，rho 无量纲。采样密度非负，tau>=0。输出 valid_interval、s0/s1、optical_depth、transmittance；无交时输出约定的 s0=s1=0 和 valid_interval=false。

最终云影只调制该方向光的直接贡献：`ground = base_ambient + T*base_direct`。base_* 由中性材质/灯光配置定义，不得通过把所有环境光乘 T 代替。视觉路径可在公开预算内增加采样，但 OJ 路径必须按输入 N 的定义计算并复用相同密度/光程核心。另用采样收敛验证视觉近似。
