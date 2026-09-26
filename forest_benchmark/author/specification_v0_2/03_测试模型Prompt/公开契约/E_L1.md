# E_L1｜透明水滴/水膜的折射与吸收：公开数值契约 v0.1


## 光学定义

I 为指向界面的单位入射传播方向；N 指向入射介质且与 I 相反，`ci=-dot(I,N)>=0`。eta_i/eta_t>0；有效输入避免非同介质的精确掠射奇点。`eta=eta_i/eta_t`，`k=1-eta²*(1-ci²)`。

若 k<0，全反射：F=1、has_transmission=false、Tdir=[0,0,0]。否则 ct=sqrt(k)，`Tdir=eta*I+(eta*ci-ct)*N`；F 为精确无偏振介质 Fresnel，即两种偏振反射率的均值，不采用 Schlick 近似。本题使用方向向量和未偏振强度定义，不引入偏振状态。eta_i=eta_t 时 F=0、Tdir=I（包括方向退化处理）。反射方向 `R=I+2*ci*N`。

给定沿传播路径长度 ell>=0（米），而不是法线厚度；吸收 `A_rgb=exp(-sigma_a_rgb*ell)`，sigma_a 每通道>=0。接口输出 F、Tdir、R、A_rgb、has_transmission。禁止直接调用 refract()、现成 Fresnel/透明材质求解节点替代被考计算；sqrt/exp/dot/normalize/普通采样允许。

## 本版显示近似

表面点 x 的后景查询点 `q=x+ell*Tdir`，用给定相机矩阵投影 q 得到背景 UV。屏幕后/越出 [0,1] 时 valid=false，使用公开 fallback_color，不以边缘 clamp 假装命中。ell 可以来自已给的路径长度图或几何诊断输入；不假设它等于真实完整水滴内的折线路径。

`C=F*C_reflection+(1-F)*A_rgb*C_background(sample_uv)`。反射背景由给定中性环境查取；全反射只使用反射项。这个合成式是本题显示近似，不宣称为完整路径追踪通量权重。输出 background_uv、valid、optical_terms；最终图与 OJ 使用同一光学核心。

不得以过小 ell、关闭反射/折射或提高曝光掩盖错误；正式配置由测试端控制。
