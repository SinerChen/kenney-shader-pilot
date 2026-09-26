# C_L2｜云遮光约束的薄雾与体积光：公开数值契约 v0.1


## 依赖与符号

继承 C_L1 的密度、变换和 cloud_query。雾体为世界 AABB，雾密度 rho_f>=0，sigma_s/sigma_a>=0（每米），k_f=rho_f*(sigma_s+sigma_a)。视线为 `q=o+s*d`，d 指向场景；L 仍指向光源。HG 的入射传播方向为 -L、出射方向为 -d，故 `cos_theta=dot(L,d)`。

相函数使用 `p=(1-g²)/(4*pi*(1+g²-2*g*cos_theta)^(3/2))`，g 限于 [-0.9,0.9]。该方向约定决定正 g 的前向峰，不能混用其他文献的方向符号。

雾中点 q 的单次散射源项为 `j(q)=rho_f*sigma_s*light_rgb*T_cloud(q)*T_fog_light(q)*p`。T_cloud 来自继承核心；T_fog_light 是从 q 沿 L 离开雾盒的透射 `exp(-k_f*light_path_length)`。在本级均匀雾中该项可解析计算；不能省略雾自身对入射太阳光的衰减。

## 视线合成

由相机视线与雾盒及提供的不透明深度截断得到有效区间，按给定 Nv 个中点估计 j。每段视线透射为 exp(-k_f*ds)，源项段积分系数为 `(1-exp(-k_f*ds))/k_f`；k_f→0 时按连续极限 ds 处理。按前到后透射累积得到 L_scatter 与 T_view。最终 `C=T_view*C_background+L_scatter`。背景地面本身已由 C_L1 的云影着色，不能再重复施加同一云透射。

输出 `T_cloud_at_samples, T_fog_light, phase, L_scatter, T_view`。积分在场景线性颜色空间。k_f=0 时 rho_f*sigma_s 也为 0，因此无散射；不要在除零补丁中凭空产生发光。
