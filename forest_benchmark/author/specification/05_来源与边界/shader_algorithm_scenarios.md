# Shader 算法 × 应用场景：150条、300个构想

整理日期：2026-09-24。

范围：此前完整算法清单未检索到，本表为扩展构想版，尚未一一对照。所有场景未实现、未运行、未测量性能。
条目包含算法、物理／反射模型和工程技术族；条目数不等于互相独立的算法数。
应用场景是基于机制构造的候选，不表示来源作者已实现这些具体项目，也不表示每一种技术都在应用中同样普及。
标有“相关背景”或“资料待补充”的来源不作为该具体算法原始文献的证明。典型运行载体不是平台支持承诺。

## A. 噪声与程序图案

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| A01 | 哈希／白噪声 | 生成可复现的随机量，而非连续结构 | 为同种草的每个实例分配不同风摆相位，避免整齐同步 | 给岩石实例分配稳定的色差和粗糙度偏差 | 材质／顶点 | 随机值是否随镜头移动而闪变；种子是否可复现 | [S01](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-5-implementing-improved-perlin-noise)；直接相关的机制／实现资料 |
| A02 | Value Noise（值噪声） | 插值随机格点值，构造连续变化 | 为墙面涂层生成缓慢变化的斑驳颜色 | 调制地面积水覆盖率，形成大小不一的湿斑 | 材质 | 格点感、周期性、缩放后的接缝 | [S02](https://docs.blender.org/manual/en/latest/compositing/types/texture/noise.html)；相关背景；未核到该变体专门资料 |
| A03 | Perlin Noise | 用梯度噪声构造连续空间变化 | 为山坡生成平滑起伏的基础高度 | 为烟雾密度添加柔和的不均匀分布 | 材质／顶点／体积 | 把密度变化与完整烟雾渲染分开；检查坐标连续性 | [S01](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-5-implementing-improved-perlin-noise)；直接相关的机制／实现资料 |
| A04 | Simplex Noise | 在单纯形格上构造梯度噪声 | 为流动熔岩添加连续变化的温度／亮度扰动 | 为传送门表面生成连续时变的扭曲场 | 材质 | 时间连续性、方向性伪影与重复图案 | [S51](https://stegu.github.io/webgl-noise/)；直接相关的机制／实现资料 |
| A05 | Worley／Voronoi Noise | 用最近特征点的距离构造细胞结构 | 为泡沫块生成细胞状分区和边界 | 为干燥泥地生成裂块图案；裂缝深度需另做 | 材质 | 单元尺度、边界连续性；不要当成真实断裂模拟 | [S03](https://docs.blender.org/manual/en/latest/compositing/types/texture/voronoi.html)；直接相关的机制／实现资料 |
| A06 | fBM 分形噪声 | 叠加多尺度噪声细节 | 为岩石同时生成大尺度斑块和细颗粒变化 | 为体积云的密度生成大小层次不同的云团 | 材质／体积 | 不同尺度是否各有贡献；远处高频是否闪烁 | [S02](https://docs.blender.org/manual/en/latest/compositing/types/texture/noise.html)；直接相关的机制／实现资料 |
| A07 | Turbulence 噪声 | 对噪声取绝对值等非线性处理并叠加 | 为火焰遮罩生成翻卷破碎的边缘 | 为大理石色带增加细碎扰动 | 材质／体积 | 是否误称真实湍流；形态与动画是否重复 | [S02](https://docs.blender.org/manual/en/latest/compositing/types/texture/noise.html)；相关背景；未核到该变体专门资料 |
| A08 | Ridged Noise | 将噪声整形成脊状分布 | 为高山地形生成连续山脊 | 为岩壁生成尖锐的凸脊和沟槽高度 | 材质／顶点 | 脊线连贯性、高频锯齿与法线一致性 | [S02](https://docs.blender.org/manual/en/latest/compositing/types/texture/noise.html)；相关背景；未核到该变体专门资料 |
| A09 | Domain Warping（域扭曲） | 先扭曲采样坐标，再求基础图案 | 把规则条纹扭成木纹或大理石纹 | 把云／烟的规则噪声结构扭成翻卷轮廓 | 材质／顶点／体积 | 坐标扭曲是否破坏周期；位移后法线是否同步 | [S47](https://arxiv.org/html/2405.07124v1)；直接相关的机制／实现资料 |
| A10 | Curl Noise | 从势场的旋度构造旋转式速度场 | 让篝火余烬沿小涡旋上升，而非直线飞走 | 让魔法烟带在目标周围绕行并卷曲 | 计算／反馈 | 不是完整流体；离散误差和边界处理需检查 | [S08](https://dl.acm.org/doi/10.1145/1276377.1276435)；直接相关的机制／实现资料 |
| A11 | 可平铺／周期噪声 | 让空间或时间的边界周期连续 | 生成可重复铺设的海面细波法线 | 生成首尾无跳变的循环烟雾扰动素材 | 材质／预计算 | 对边数值与梯度一致；空间周期不等于时间周期 | [S51](https://stegu.github.io/webgl-noise/)；直接相关的机制／实现资料 |
| A12 | Gabor Noise | 控制随机纹理的主方向和频率 | 为拉丝金属生成有方向的微细表面纹理 | 为织物生成略不规则的方向性纤维纹理 | 材质 | 纹理方向需匹配材质方向；不代替各向异性BRDF | [S04](https://docs.blender.org/manual/en/latest/compositing/types/texture/gabor.html)；直接相关的机制／实现资料 |
| A13 | 解析条纹／环纹 | 用解析周期函数生成规则图案 | 为木材切面生成可扰动的年轮基础图案 | 为雷达／扫描装置生成扩张的同心环 | 材质 | 缩小时抗锯齿；条纹频率与物体尺度一致 | [S05](https://docs.blender.org/manual/en/latest/compositing/types/texture/wave.html)；直接相关的机制／实现资料 |
| A14 | 砖块／六边形程序平铺 | 按规则分格生成图案和单元坐标 | 为建筑墙面生成砖块、砂浆与逐砖色差 | 为科幻地板生成六边形面板和可控接缝 | 材质 | 接缝宽度、转角连续性、远景闪烁 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |

## B. 纹理映射与材质构造

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| B01 | UV 平移／旋转 | 随时间改变纹理采样坐标 | 让传送带表面纹理按运输方向滚动 | 让瀑布薄片的水纹向下流动 | 材质 | 速度与方向一致；重复纹理接缝 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B02 | 极坐标映射 | 将平面坐标转为角度和半径 | 制作从中心向外扩散的法阵光环 | 制作绕中心旋转的风暴／传送门纹理 | 材质 | 角度接缝、中心奇点和宽度畸变 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B03 | Triplanar（三平面投影） | 按表面方向混合三组投影纹理 | 为没有优质UV的悬崖铺岩石材质 | 为洞穴墙、顶、地连续铺设石纹 | 材质 | 斜面接缝、法线混合、物体移动后的纹理漂移 | [S46](https://docs.unity3d.com/Packages/com.unity.shadergraph%4014.0/manual/Triplanar-Node.html)；直接相关的机制／实现资料 |
| B04 | 随机化纹理平铺 | 随机采样变换并混合以减轻重复 | 让大面积草地不出现棋盘式贴图重复 | 用少量岩石贴图覆盖长距离山路 | 材质 | 混合区发灰、结构断裂；不能保证消除所有重复 | [S07](https://eheitzresearch.wordpress.com/738-2/)；直接相关的机制／实现资料 |
| B05 | Splat 权重混合 | 用多通道权重分配不同材质 | 在地形上混合道路、泥土和草地 | 给角色盔甲局部分配泥污、锈蚀和裸露金属 | 材质 | 权重归一化、不同材质通道同步 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B06 | 高度混合 | 依据局部高度比较决定材质覆盖 | 让泥浆先填满鹅卵石之间的低凹缝隙 | 让积雪盖住石板而保留较高的石棱 | 材质 | 高度约定、阈值过渡和多层顺序依赖 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B07 | 坡度／海拔遮罩 | 用法线方向与世界高度控制分布 | 让雪主要覆盖朝上的山体表面 | 让陡坡偏岩石、缓坡偏草地，并按高度分带 | 材质 | 坐标系、物体旋转；不等于真实沉积模拟 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B08 | TBN 法线映射 | 将切线空间法线转换到着色空间 | 在低模砖墙上表现砖缝凹凸光照 | 为角色皮肤补充毛孔级光照细节 | 材质 | 镜像UV、切线手性、法线贴图轴向 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B09 | RNM 重定向法线混合 | 在已有表面朝向上叠加细节法线 | 在石头大凹凸上叠加细颗粒法线 | 在角色皮肤基础法线上叠加局部皱纹 | 材质 | 细节是否跟随基础法线；平坦输入是否保持不变 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B10 | 高度导数凹凸映射 | 从高度梯度计算表面法线扰动 | 用程序噪声为橘子皮生成细小凹凸 | 用高度图为雨后地面生成细密水滴凸起感 | 材质 | 只改变着色，不改变轮廓；导数尺度正确 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B11 | 基础视差映射 | 用视线方向和高度近似偏移UV | 给粗糙墙面增加轻量视差深度感 | 给木地板接缝增加随视角变化的偏移 | 材质 | 掠射角拉伸；轮廓、遮挡并非真实几何 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B12 | POM（视差遮蔽映射） | 沿视线在高度场中搜索表面交点 | 让近景鹅卵石路呈现石缝自遮挡和视差 | 让砖墙凹槽在斜视角产生可读的深度 | 材质 | 交点稳定、采样预算、深度与阴影是否另行匹配 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B13 | 投影贴花 | 将局部图案投射到已有表面 | 把弹孔投射到墙面并按表面方向裁切 | 将泥点和轮胎痕附加到地形与道路 | 材质／管线 | 穿投背面、跨物体溢出、深度冲突 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| B14 | Flow Mapping（流向贴图） | 用速度场扭曲UV并周期重置混合 | 让河面纹理沿弯曲河道流动 | 让岩浆纹理在石块旁分流，表达美术指定的流向 | 材质 | 相位接缝、长期拉伸；流向图不自动求物理流动 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |

## C. 光照与材质反射模型

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| C01 | Lambert 漫反射 | 计算与入射角相关的理想漫反射 | 为哑光石膏雕像建立基础明暗 | 为低成本场景的无光泽墙面提供基础照明 | 材质／管线 | 法线与光方向；避免和环境光重复计入 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| C02 | Blinn–Phong 高光 | 用半角向量构造经验高光 | 为风格化塑料玩具生成可控高光斑 | 为复古渲染风格的金属道具制作廉价亮点 | 材质 | 不应当作完整PBR；高光随镜头和光源合理移动 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| C03 | Oren–Nayar 粗糙漫反射 | 描述粗糙表面的漫反射变化 | 区分砂土与光滑哑光涂层的明暗响应 | 为粗陶器表面表现较粗糙的漫反射 | 材质 | 粗糙度控制的是漫反射模型，不等于金属粗糙度参数 | [S49](https://pbr-book.org/3ed-2018/Reflection_Models/Microfacet_Models)；直接相关的机制／实现资料 |
| C04 | Cook–Torrance＋GGX | 组合微表面分布、遮蔽与Fresnel | 制作可调粗糙度的金属水壶 | 制作具有柔和镜面反射的塑料设备外壳 | 材质／管线 | 能量、粗糙度极值、金属与介质参数约定 | [S10](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory)；直接相关的机制／实现资料 |
| C05 | Fresnel／Schlick 近似 | 表达反射随入射／观察角度变化 | 让湖面在掠射角更突出环境反射 | 让玻璃边缘与正面呈现不同反射强度 | 材质 | 不要把任意轮廓发光当成物理Fresnel | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| C06 | 各向异性 BRDF | 让反射沿切线方向具有不同展宽 | 为拉丝金属电梯门制作方向性高光 | 为唱片或抛光金属盘制作随切线变化的高光 | 材质／管线 | 切线场、旋转响应；不是简单拉长贴图 | [S10](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory)；直接相关的机制／实现资料 |
| C07 | Clear Coat 清漆层 | 在底层材质上叠加独立透明反射层 | 为车漆表现底色与表面清漆双层高光 | 为上清漆的木桌表现木纹与光滑表面反射 | 材质／管线 | 上下层能量分配、法线和粗糙度分工 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| C08 | Cloth Sheen 织物绒光 | 近似纤维表面的掠射角柔和亮边 | 为天鹅绒沙发制作随视角变化的绒光 | 为衣物袖口表现柔和的布料边缘反射 | 材质／管线 | 不应全角度自发光；纤维方向与材质一致 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| C09 | SSS 扩散近似 | 近似光在介质内部的空间传播 | 为人脸制作不过分塑料化的皮肤光照 | 为蜡烛和玉石表现柔和的内部散射 | 材质／屏幕／管线 | 薄厚变化、散射半径；屏幕滤波不能穿错误边界 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| C10 | 薄片透射／包裹光近似 | 低成本表达薄表面的背光与柔化明暗 | 让太阳背后的树叶呈现透亮叶肉 | 让背光布帘表现柔和透光而非完全黑面 | 材质 | 与真正体积SSS分开；正反面法线、厚度遮罩 | [S33](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis)；直接相关的机制／实现资料 |
| C11 | 发丝切线高光模型 | 按发丝方向计算纤维式光照 | 为长发角色生成沿发束延伸的高光带 | 为动物鬃毛表现随梳理方向变化的光泽 | 材质／管线 | 发丝切线连续；不能只用普通表面法线高光 | [S50](https://pbr-book.org/4ed/Reflection_Models/Scattering_from_Hair)；直接相关的机制／实现资料 |
| C12 | 薄膜干涉 | 根据薄膜厚度和角度计算干涉色 | 为肥皂泡生成随厚度与视角变化的彩色纹带 | 为水面油膜制作角度相关的虹彩 | 材质 | 厚度、角度与色彩联动；不是固定彩虹贴图 | [S59](https://belcour.github.io/blog/research/publication/2017/05/01/brdf-thin-film.html)；直接相关的机制／实现资料 |
| C13 | 衍射近似 | 依据微细周期结构描述分光图案 | 为光盘沟槽生成移动的彩虹反射带 | 为全息防伪膜制作与方向相关的分光外观 | 材质／管线 | 与薄膜干涉区分；沟槽方向、光视角一致 | [S11](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-8-simulating-diffraction)；直接相关的机制／实现资料 |

## D. 阴影与环境遮蔽

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| D01 | Shadow Mapping（阴影贴图） | 比较光源视角深度判断遮挡 | 让角色经过路灯时在地面投下动态阴影 | 让可移动箱子遮挡窗外阳光 | 管线 | 阴影痤疮、悬浮偏移、深度精度与裁切 | [S12](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows/chapter-11-shadow-map-antialiasing)；直接相关的机制／实现资料 |
| D02 | PCF 阴影过滤 | 对深度比较结果做邻域过滤 | 平滑室外树影边缘的像素锯齿 | 平滑手电筒照射栏杆形成的动态阴影 | 材质／管线 | 过滤比较值而非先模糊深度；采样图案是否可见 | [S12](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows/chapter-11-shadow-map-antialiasing)；直接相关的机制／实现资料 |
| D03 | PCSS 接触硬化软阴影 | 估计遮挡距离并改变过滤范围 | 让悬空箱子的阴影随离地高度增加而变软 | 让桌腿根部阴影较实、远离接触点处较软 | 管线 | 半影随遮挡距离和光源尺寸改变；边界稳定 | [S13](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-8-summed-area-variance-shadow-maps)；相关背景；未核到该变体专门资料 |
| D04 | VSM 方差阴影 | 用深度矩估计可过滤的阴影可见性 | 为大型室内场景生成可预过滤的宽软阴影 | 为枝叶密集的场景尝试较大半径阴影过滤 | 管线 | 漏光与过度模糊；不承诺薄遮挡物始终正确 | [S13](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-8-summed-area-variance-shadow-maps)；直接相关的机制／实现资料 |
| D05 | CSM 级联阴影 | 分配不同距离段的太阳阴影分辨率 | 让近景草地与远景山坡同时获得可用太阳阴影 | 让驾驶镜头沿长道路前进时保持近处阴影细节 | 管线 | 级联接缝、游动、远近分辨率变化 | [S14](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/cascaded-shadow-maps)；直接相关的机制／实现资料 |
| D06 | 屏幕空间接触阴影 | 在屏幕深度中补充短距离遮挡 | 补足鞋底与地面接触处的小阴影 | 补足桌面小物件与桌面之间的短阴影 | 屏幕／管线 | 屏外和遮挡信息缺失；不能代替完整阴影 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| D07 | 光线追踪阴影 | 对场景几何查询到光源的可见性 | 为百叶窗和细栏杆生成细节明确的阴影 | 让移动面光源下的物体生成形状相关软阴影 | 管线／高级 | 光线预算、噪声、透明裁切与降噪 | [S18](https://gpuopen.com/fidelityfx-hybrid-reflections/)；相关背景；未核到该变体专门资料 |
| D08 | SSAO | 从深度／法线近似局部环境遮蔽 | 加强家具与墙角的接触层次 | 加强石阶缝隙和散落石块之间的局部遮蔽 | 屏幕 | 不替代直接光阴影；边缘光晕、屏外缺失 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；直接相关的机制／实现资料 |
| D09 | HBAO | 根据周围深度的地平线遮挡估计AO | 为管线密集的工业设备增加凹陷遮蔽 | 为起伏明显的岩石地面增加局部环境遮蔽 | 屏幕 | 半径与世界尺度、深度不连续处的光晕 | [S57](https://developer.nvidia.com/rendering-technologies/horizon-based-ambient-occlusion-plus)；直接相关的机制／实现资料 |
| D10 | GTAO | 用几何与积分近似估计屏幕空间AO | 为室内桌椅接触区域生成较稳定遮蔽 | 为角色装备间隙生成尺度受控的局部遮蔽 | 屏幕 | 厚度假设、薄物体过暗、空间和时间稳定性 | [S56](https://github.com/GameTechDev/XeGTAO)；直接相关的机制／实现资料 |

## E. 反射、折射与间接光

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| E01 | Split-sum IBL | 预过滤环境光并用BRDF查找表近似积分 | 用同一HDR环境展示不同粗糙度的金属球 | 让室外车辆同时接收天空漫反射和环境高光 | 材质／预计算 | 粗糙度与mip映射、色彩空间、环境旋转一致 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| E02 | 球谐光照（SH） | 用低阶系数表示低频方向光照 | 让移动角色从户外走入阴影时平滑改变环境光 | 给大场景植被实例提供低成本方向性环境照明 | 材质／管线 | 只适合低频；不期待恢复清晰镜面图像 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| E03 | 盒投影反射探针 | 用代理空间修正局部环境反射方向 | 改善房间内光滑家具反射墙壁的位置感 | 改善走廊金属柜表面反射的局部空间关系 | 材质／管线 | 探针范围、过渡、代理盒不符合几何时的误差 | [S17](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/reflection_probes.html)；直接相关的机制／实现资料 |
| E04 | 平面反射 | 从镜像相机渲染平面另一侧视图 | 为平静湖面生成岸边建筑倒影 | 为室内大镜子生成角色和房间反射 | 多遍／管线 | 裁切面、反射方向、递归与非平面限制 | [S25](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)；直接相关的机制／实现资料 |
| E05 | SSR 屏幕空间反射 | 在屏幕深度中搜索反射方向的命中 | 为雨后街道路面添加当前画面内的霓虹倒影 | 为室内抛光地板添加可见家具的反射 | 屏幕 | 屏外缺失、边缘消失、厚度假设和粗糙反射 | [S16](https://gpuopen.com/fidelityfx-sssr/)；直接相关的机制／实现资料 |
| E06 | 光线追踪反射 | 在场景表示中追踪反射方向 | 让金属茶壶反射摄像机背后的道具 | 让室内镜面反射画面外移动的人物 | 管线／高级 | 多次反射、动态更新与噪声；不是单个局部材质任务 | [S18](https://gpuopen.com/fidelityfx-hybrid-reflections/)；直接相关的机制／实现资料 |
| E07 | Snell 折射与屏幕近似 | 求折射方向并采样背景／场景 | 为清水池表现池底的视线偏移 | 为玻璃瓶表现后方图案的变形；厚壁需处理多界面 | 材质／屏幕／管线 | 薄片近似与厚介质分开；全反射与屏幕边界 | [S30](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)；直接相关的机制／实现资料 |
| E08 | Beer–Lambert 吸收 | 按介质路径长度衰减不同颜色 | 让深水比浅水更暗并产生水色变化 | 让有色玻璃厚边比薄片区域颜色更浓 | 材质／体积 | 使用真实或合理近似路径长度；不能仅按世界高度染色 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| E09 | LTC 面光源积分 | 用可积近似求多边形灯的表面反射 | 表现办公桌上方长条灯在粗糙金属上的宽高光 | 表现摄影棚矩形柔光箱在产品表面的反射 | 材质／管线／高级 | 光源形状和朝向响应；阴影需另解 | [S19](https://eheitzresearch.wordpress.com/415-2/)；直接相关的机制／实现资料 |
| E10 | 体素锥追踪间接光 | 在体素场中近似查询多方向间接光 | 让红墙向附近白墙产生间接染色 | 让场景中的发光物体为周围漫反射表面提供间接光 | 计算／管线／高级 | 体素分辨率、漏光、几何更新与反射细节限制 | [S20](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/using_voxel_gi.html)；直接相关的机制／实现资料 |
| E11 | DDGI 动态漫反射探针 | 用更新的探针采样重建间接漫反射 | 让室内灯开关后墙面的间接亮度逐步更新 | 让门打开后相邻房间接收到变化的间接光 | 计算／管线／高级 | 探针可见性、漏光、更新滞后；不代替镜面反射 | [S21](https://morgan3d.github.io/articles/2019-04-01-ddgi/)；直接相关的机制／实现资料 |

## F. 雾、云与大气

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| F01 | 距离雾 | 用到相机的距离控制介质混合近似 | 让远处山体渐渐融入空气颜色 | 为沙漠或雪原控制远景可见度 | 材质／屏幕 | 以线性距离计算；不自动生成局部体积光 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；直接相关的机制／实现资料 |
| F02 | 高度雾 | 让介质密度随世界高度变化 | 让峡谷底部比山顶更浓雾 | 让清晨湖边的低洼处被薄雾覆盖 | 屏幕／体积 | 相机上下移动时雾层仍固定在世界空间 | [S22](https://docs.godotengine.org/en/stable/tutorials/3d/volumetric_fog.html)；直接相关的机制／实现资料 |
| F03 | 体积光线步进 | 沿视线积分密度、透射与散射 | 在森林中渲染有内部厚度的局部雾团 | 让相机穿过烟柱时看到连续的密度变化 | 屏幕／体积／计算 | 步长、积分顺序、深度截断和采样条纹 | [S22](https://docs.godotengine.org/en/stable/tutorials/3d/volumetric_fog.html)；直接相关的机制／实现资料 |
| F04 | Henyey–Greenstein 相函数 | 近似散射方向分布 | 让雾中的探照灯在不同观察方向亮度不同 | 表现逆光薄雾较明显的前向散射感 | 体积 | 光线与视线方向约定；g接近极值的数值稳定性 | [S22](https://docs.godotengine.org/en/stable/tutorials/3d/volumetric_fog.html)；直接相关的机制／实现资料 |
| F05 | 体积阴影／光程透射 | 估计光到采样点沿途被介质／几何遮挡的程度 | 让仓库横梁切断空气中的灯光柱 | 让浓烟内部背向光源区域变暗 | 体积／多遍 | 表面阴影与介质自阴影分开；避免墙后漏光 | [S22](https://docs.godotengine.org/en/stable/tutorials/3d/volumetric_fog.html)；直接相关的机制／实现资料 |
| F06 | Rayleigh 散射 | 表达分子尺度散射的大气色彩变化 | 为昼夜系统生成随太阳高度变化的天空颜色 | 从高空或轨道观察行星大气边缘 | 天空／体积／预计算 | 行星尺度、太阳方向、视线路径长度 | [S23](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-16-accurate-atmospheric-scattering)；直接相关的机制／实现资料 |
| F07 | Mie 散射近似 | 表达气溶胶等颗粒的方向性散射 | 在晴空太阳周围生成雾霾光晕 | 为沙尘天气生成偏前向的散射感 | 天空／体积／预计算 | 不把单个亮圆盘当完整散射；与Rayleigh分工 | [S23](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-16-accurate-atmospheric-scattering)；直接相关的机制／实现资料 |
| F08 | 大气散射 LUT 预计算 | 将重复的大气积分存入查找表 | 为开放世界日落到夜晚的天空变化降低重复积分量 | 为不同海拔的飞行镜头提供一致的大气透射 | 计算／预计算／高级 | LUT参数域、插值、太阳／高度改变时的适用范围 | [S55](https://ebruneton.github.io/precomputed_atmospheric_scattering/)；直接相关的机制／实现资料 |
| F09 | Froxel 体积光照 | 在视锥体网格中组织介质与多光源照明 | 为工厂空间的多盏射灯计算有雾照明 | 为夜间街道组合路灯和车灯的局部体积贡献 | 计算／管线／高级 | 网格分辨率、薄雾细节与运动拖影 | [S22](https://docs.godotengine.org/en/stable/tutorials/3d/volumetric_fog.html)；直接相关的机制／实现资料 |
| F10 | 屏幕空间 God Rays | 径向累积屏幕遮挡，近似可见光束 | 在日落树林画面中生成穿过树冠的光芒 | 在门窗开口周围生成风格化逆光束 | 屏幕 | 视角与屏外光源限制；不是任意视点都正确的体积光 | [S24](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process)；直接相关的机制／实现资料 |
| F11 | 云多次散射近似 | 补偿仅单次散射时云体过暗的部分能量 | 改善厚积云内部的柔和亮度层次 | 表现背光云的亮边与较暗内部之间的过渡 | 体积／高级 | 与密度和光照方向联动；不以任意环境亮度掩盖误差；所引资料仅为大气背景，云模型需单独核对 | [S23](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-16-accurate-atmospheric-scattering)；相关背景；未核到该变体专门资料 |

## G. 水面与流体模拟

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| G01 | 正弦波叠加 | 叠加有限数量的解析水面波 | 为池塘生成幅度受控的小幅水面起伏 | 为风格化海面生成可读的方向性波浪 | 顶点／材质 | 波向与速度、解析法线；波浪不自动与障碍物交互 | [S25](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)；直接相关的机制／实现资料 |
| G02 | Gerstner 波 | 同时改变水平与垂直位置形成较尖波峰 | 为近海帆船场景生成具有波峰感的海浪 | 为风格化大海生成方向明确的涌浪轮廓 | 顶点／材质 | 陡峭度导致自交；位移、法线和浮动物体采样一致 | [S25](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)；直接相关的机制／实现资料 |
| G03 | FFT 频谱海洋 | 从波谱合成大量空间频率的海浪 | 为远海航行场景生成大范围多尺度波浪 | 为暴风天气生成随风场设置变化的海面统计形态 | 计算／多遍／高级 | 周期重复、不同尺度拼接；不自动处理近岸破浪 | [S25](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)；直接相关的机制／实现资料 |
| G04 | 解析径向涟漪 | 从事件中心生成传播衰减的环形波 | 为雨滴落入水洼生成可控环形波纹 | 为手指点水的交互装置生成圆形涟漪 | 材质／顶点 | 多源叠加、时间衰减；不自动在池壁反射 | [S25](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)；直接相关的机制／实现资料 |
| G05 | 高度场波动方程 | 以相邻格点状态传播波动 | 让水池中落物波纹碰到池壁后反射 | 让多次点击的水面波互相叠加干涉 | 计算／反馈 | 边界条件、时间步稳定性、格点方向偏差 | [S58](https://matthias-research.github.io/pages/publications/hfFluid.pdf)；直接相关的机制／实现资料 |
| G06 | 浅水方程 | 演化水深与水平流速 | 让浅溪绕过石块并在狭窄处改变流速 | 让闸门开启后浅层水流沿渠道传播 | 计算／反馈／高级 | 水量守恒、干湿边界与地形；不擅长翻卷飞溅 | [S58](https://matthias-research.github.io/pages/publications/hfFluid.pdf)；直接相关的机制／实现资料 |
| G07 | 半拉格朗日平流 | 沿速度场回溯搬运标量或速度 | 让彩色染料在二维水流中被带动 | 让烟的密度和温度随已知速度场移动 | 计算／反馈 | 数值耗散、边界采样；平流不是完整流体求解器 | [S26](https://developer.nvidia.com/gpugems/gpugems/part-vi-beyond-triangles/chapter-38-fast-fluid-dynamics-simulation-gpu)；直接相关的机制／实现资料 |
| G08 | 压力投影 | 解压力并修正速度以减少散度 | 让二维烟流绕过障碍时维持近似不可压缩 | 让封闭容器内的流动不持续凭空收缩或膨胀 | 计算／反馈／高级 | 散度残差、边界条件、迭代预算 | [S26](https://developer.nvidia.com/gpugems/gpugems/part-vi-beyond-triangles/chapter-38-fast-fluid-dynamics-simulation-gpu)；直接相关的机制／实现资料 |
| G09 | 涡量限制／补偿 | 减轻数值耗散造成的小涡旋丢失 | 让烟柱上升时保留翻卷细节 | 让爆炸后的烟团保持可读的旋转结构 | 计算／反馈 | 强度过高注入非物理能量；与分辨率时间步联动 | [S27](https://developer.nvidia.com/gpugems/gpugems3/part-v-physics-simulation/chapter-30-real-time-simulation-and-rendering-3d-fluids)；直接相关的机制／实现资料 |
| G10 | SPH 粒子流体 | 用粒子邻域估计流体量和相互作用 | 模拟杯子倾倒时流出的自由表面液体 | 模拟喷泉水滴落入盆中并汇聚 | 计算／高级 | 邻域搜索、密度误差、时间步与固体边界 | [S29](https://matthias-research.github.io/pages/publications/sca03.pdf)；直接相关的机制／实现资料 |
| G11 | PBF 基于位置的流体 | 迭代位置约束以控制粒子密度 | 让交互水箱中的液体随移动障碍物晃动 | 让容器倾斜时液体倒出并与盆壁碰撞 | 计算／高级 | 约束收敛、粒子聚团与能量损失；仍需表面渲染 | [S28](https://mmacklin.com/pbf_sig_preprint.pdf)；直接相关的机制／实现资料 |
| G12 | 焦散生成／投影 | 生成或近似聚焦光斑并投到接收面 | 在游泳池底生成随水波变化的亮纹 | 在浅海岩石上叠加随水面变化的焦散光斑 | 材质／多遍／高级 | 视觉投影与物理焦散不是同一要求；水外表面应受限 | [S30](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)；直接相关的机制／实现资料 |
| G13 | 泡沫分布遮罩 | 用岸线距离、深度或波面压缩等信息分配泡沫 | 让礁石接触水面附近出现局部白沫 | 让陡峭波峰按压缩程度出现白浪覆盖 | 材质／计算 | 遮罩来源应与场景匹配；不能把全海面随机白点当白浪 | [S25](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)；相关背景；未核到该变体专门资料 |

## H. 几何、植被与动画

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| H01 | 几何位移映射 | 直接修改表面顶点位置 | 让近景雪地具有真实起伏轮廓 | 让岩石表面的较大凸起投下对应几何阴影 | 顶点／计算 | 顶点密度、法线更新、包围盒与阴影一致 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| H02 | 自适应细分 | 按距离或屏幕误差分配几何精度 | 给近处岩石位移更多三角形而减少远处开销 | 让海面近处波浪轮廓细致、远处网格更稀疏 | 管线／计算／高级 | 裂缝、细分级别跳变、边界匹配 | [S31](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-1-generating-complex-procedural-terrains-using-gpu)；相关背景；未核到该变体专门资料 |
| H03 | 层级程序风 | 分离整体弯曲、枝条摆动与叶片细动 | 让树干缓慢摆动而叶片快速颤动 | 让草根基本固定、草尖随阵风摆动 | 顶点 | 根部约束、不同层级频率和阴影同步 | [S32](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-6-gpu-generated-procedural-wind-animations-trees)；直接相关的机制／实现资料 |
| H04 | 支点／Pivot 动画 | 围绕预编码支点旋转局部部件 | 让棕榈叶绕各自叶柄摆动而非整片平移 | 让花朵各花瓣绕根部张开和闭合 | 顶点／预处理 | 支点数据、局部坐标、父子变换次序 | [S33](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis)；相关背景；未核到该变体专门资料 |
| H05 | 交互场植被弯曲 | 用角色或轨迹影响场修改植被姿态 | 让角色走过草丛时草叶向外压倒后恢复 | 让载具经过时在附近灌木中留下短暂扰动 | 顶点／反馈 | 影响范围、恢复时间、根部不脱离地面 | [S33](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis)；相关背景；未核到该变体专门资料 |
| H06 | 线性混合蒙皮（LBS） | 按骨骼权重混合顶点变换 | 驱动角色走路和手臂动作 | 让鱼群实例使用低成本骨骼游动动画 | 顶点／计算 | 权重、绑定姿态、法线；大扭转可能塌缩 | 机制资料待补充；场景为技术构想 |
| H07 | 双四元数蒙皮（DQS） | 以刚体变换的双四元数混合减少扭转塌缩 | 改善角色前臂大角度旋转时的体积保持 | 改善软管或触手的骨骼扭转外观 | 顶点／计算 | 归一化、符号一致性、缩放与关节鼓胀 | 机制资料待补充；场景为技术构想 |
| H08 | VAT 顶点动画纹理 | 从纹理读取预烘焙的位置／旋转动画 | 在实时场景回放破碎石块飞散动画 | 在装饰喷泉中回放预计算的复杂水花网格 | 顶点／预计算 | 帧插值、精度、包围盒；不是实时重新求解模拟 | [S52](https://www.sidefx.com/docs/houdini/nodes/out/labs--vertex_animation_textures-3.0.html)；直接相关的机制／实现资料 |
| H09 | Marching Cubes | 从体积标量场提取等值面网格 | 从密度场生成带洞穴和悬垂的地形 | 从粒子密度场重建可着色的液体表面 | 计算／高级 | 等值面裂缝、法线、拓扑和输出容量 | [S31](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-1-generating-complex-procedural-terrains-using-gpu)；直接相关的机制／实现资料 |
| H10 | SDF Sphere Tracing | 用距离界控制沿光线前进的步长 | 渲染会变形融合的隐式黏液物体 | 在没有显式网格时渲染程序几何雕塑 | 材质／屏幕／计算 | 非精确距离、变形和缩放后的步长安全性 | 机制资料待补充；场景为技术构想 |
| H11 | SDF 布尔／平滑并集 | 用距离场运算构造组合形状 | 让多个黏液团接触后形成柔和连接 | 在程序岩石上挖出洞口并组合隧道形状 | 材质／计算 | 平滑运算可能破坏精确距离；法线和后续步进 | 机制资料待补充；场景为技术构想 |
| H12 | Impostor 替身渲染 | 用预渲染视图近似远处复杂物体 | 用多视角树木替身表现远景森林 | 为远处城市建筑群降低几何绘制开销 | 顶点／材质／预计算 | 转角跳变、深度视差、光照变化与近远切换 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；相关背景；未核到该变体专门资料 |
| H13 | Shell Fur 壳层毛发 | 叠加偏移壳层并用遮罩表现毛束 | 为毛绒玩偶制作短绒毛轮廓 | 为地毯制作可受方向控制的绒毛表面 | 多遍／顶点／材质 | 侧视分层、透明排序、壳层数与风向 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；相关背景；未核到该变体专门资料 |

## I. 特效与持续交互

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| I01 | 溶解／阈值裁切 | 用空间遮罩推进显示与消失边界 | 让敌人从受击位置向外溶解消失 | 让纸张沿烧灼边缘逐渐消失并出现亮边 | 材质 | 边缘宽度、阴影同步；纯遮罩不模拟燃烧 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| I02 | Soft Particles 深度淡出 | 按粒子与场景深度差柔化交界 | 消除脚边烟尘与地面的硬切线 | 让雾片靠近岩石处逐渐融入场景 | 材质／屏幕 | 深度线性化、透明物深度缺失、近相机淡出 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；相关背景；未核到该变体专门资料 |
| I03 | Flipbook 序列帧 | 按时间读取图集中的预烘焙帧 | 播放爆炸火球和烟团的动画贴片 | 用离线模拟素材制作实时火把火焰 | 材质／预计算 | 帧间跳变、图集串色、循环边界与视角限制 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| I04 | Billboard 面向相机 | 让低面数卡片朝向视线或固定轴 | 渲染场景中的烟尘和飘落火星卡片 | 让远景草丛／花丛卡片保持可见面积 | 顶点 | 顶视角退化、旋转锁定、阴影朝向与平面感 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| I05 | 粒子状态积分 | 更新粒子位置、速度、年龄等状态 | 模拟喷泉粒子的发射、重力下落与死亡 | 模拟焊接火花的抛射和逐渐冷却 | 计算／反馈 | 帧率依赖、寿命边界、重生和随机种子 | [S35](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/particle_shader.html)；直接相关的机制／实现资料 |
| I06 | SDF 粒子碰撞 | 根据距离和梯度进行近似碰撞响应 | 让烟尘／魔法粒子绕开角色模型 | 让火花接触雕像表面后反弹或滑落 | 计算／反馈 | SDF精度、薄物体穿透、高速粒子与运动碰撞体 | [S34](https://docs.godotengine.org/en/stable/tutorials/3d/particles/collision.html)；直接相关的机制／实现资料 |
| I07 | Ribbon／Trail 轨迹带 | 连接历史采样点形成连续带状几何 | 表现剑刃挥动时的残影轨迹 | 表现赛车轮胎扬尘或导弹尾迹的连续路径 | 顶点／计算／反馈 | 历史点间距、带宽、相机转动时的翻转 | [S35](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/particle_shader.html)；相关背景；未核到该变体专门资料 |
| I08 | 向量场／吸引子 | 用指定方向场或目标力控制运动 | 让粒子被传送门吸入并形成旋转漏斗 | 让群体光点沿曲线路径飞向交互目标 | 计算／反馈 | 时间步、稳定性、聚集到中心时的数值异常 | [S08](https://dl.acm.org/doi/10.1145/1276377.1276435)；直接相关的机制／实现资料 |
| I09 | 反应扩散 | 迭代耦合的扩散与反应形成图案 | 为生物皮肤生成可生长的斑点／条纹 | 为魔法污染区域生成逐步扩展的活性纹理 | 计算／反馈 | 参数与图案稳定性；不等于真实生物生长模型 | [S36](https://www.karlsims.com/rd.html)；直接相关的机制／实现资料 |
| I10 | 持久化 Render Target 绘制 | 将局部交互累计到纹理状态 | 让脚印与轮胎印留在雪地或泥地上 | 让水枪在墙面上留下可累积和干燥的湿痕 | 材质／反馈 | 世界到纹理映射、UV接缝、分辨率和时间衰减 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；相关背景；未核到该变体专门资料 |
| I11 | JFA 跳跃泛洪距离变换 | 在图像网格传播种子以近似最近距离 | 从选中物体遮罩生成可调宽度外轮廓光 | 从海岸遮罩生成水面泡沫的距离控制带 | 计算／多遍 | 近似距离误差、内外符号和分辨率依赖 | [S37](https://www.comp.nus.edu.sg/~tants/jfa/i3d06.pdf)；直接相关的机制／实现资料 |

## J. 非写实与风格化

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| J01 | Cel／Ramp 分段光照 | 把连续光照映射为有限色阶或色带 | 为卡通角色生成清晰的明暗块面 | 为风格化建筑统一受光面与背光面的色调 | 材质 | 灯光移动下分界稳定；阴影与材质色阶协调 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| J02 | Inverted Hull 反向外壳描边 | 渲染膨胀的背面几何得到外轮廓 | 为卡通人物提供外轮廓黑线 | 为可拾取道具添加选择外框 | 顶点／多遍 | 硬法线裂缝、屏幕线宽、穿插与内部线缺失 | [S38](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-15-blueprint-rendering-and-sketchy)；相关背景；未核到该变体专门资料 |
| J03 | 深度／法线 Sobel 描边 | 检测屏幕空间深度或法线变化 | 为建筑展示生成技术图式边缘线 | 为场景中的相交物体补充轮廓与折线 | 屏幕 | 深度阈值随距离变化；透明物和纹理边界区别 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；直接相关的机制／实现资料 |
| J04 | MatCap 材质捕捉 | 用视空间法线查询预绘制材质球图 | 为雕刻模型提供清晰的黏土预览 | 为风格化道具提供固定摄影棚式亮暗外观 | 材质 | 光照通常绑定视图；不应要求真实响应场景灯 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；相关背景；未核到该变体专门资料 |
| J05 | Hatching 排线 | 以线条密度和方向表达明暗 | 将机械零件渲染成铅笔工程素描 | 用交叉排线表现风格化角色阴影 | 材质／屏幕 | 线条随物体／屏幕的固定方式与远景闪烁 | [S38](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-15-blueprint-rendering-and-sketchy)；直接相关的机制／实现资料 |
| J06 | Halftone 网点 | 以点阵覆盖率表达色调 | 将角色阴影转为漫画印刷网点 | 为海报或游戏过场制作复古印刷外观 | 材质／屏幕 | 点阵尺度、摩尔纹、暗部饱和与运动稳定性 | [S38](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-15-blueprint-rendering-and-sketchy)；相关背景；未核到该变体专门资料 |
| J07 | 各向异性 Kuwahara | 用局部方向结构控制保边平滑 | 将风景画面转成具有笔触块面的油画风 | 为角色过场生成保留边缘的绘画化外观 | 屏幕 | 滤波尺度、边缘方向、视频闪烁 | [S39](https://www.kyprianidis.com/p/gpupro/)；直接相关的机制／实现资料 |
| J08 | 调色板量化／抖动 | 将颜色压到指定色板并分配量化误差 | 为复古游戏画面限制可用颜色 | 让天空渐变在少色条件下仍保持可读过渡 | 屏幕 | 色板一致性、条带和运动时的抖动 | [S41](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)；相关背景；未核到该变体专门资料 |
| J09 | 像素化／低分辨率重建 | 以固定像素网格重新采样画面 | 将三维场景表现为像素艺术画面 | 为监控摄像机画面制造低分辨率视觉 | 屏幕 | 像素栅格稳定、UI独立处理、距离和分辨率约定 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；直接相关的机制／实现资料 |

## K. 后处理与成像

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| K01 | 可分离高斯模糊 | 将二维卷积分成两次一维过滤 | 为游戏暂停菜单制作背景模糊 | 为发光层或降噪阶段提供基础平滑 | 屏幕／计算 | 权重归一化、边缘采样、线性空间 | [S53](https://gpuopen.com/fidelityfx-blur/)；直接相关的机制／实现资料 |
| K02 | Dual Kawase 多尺度模糊 | 用多级降采样和上采样近似宽模糊 | 为全屏菜单生成大半径背景虚化 | 为宽范围光晕生成低成本多尺度模糊 | 屏幕／多遍 | 半径一致性、亮点稳定性；非精确高斯 | [S53](https://gpuopen.com/fidelityfx-blur/)；相关背景；未核到该变体专门资料 |
| K03 | 双边／联合双边滤波 | 用空间与颜色／深度／法线相似度控制权重 | 平滑AO噪声同时保留物体边界 | 放大低分辨率体积光时减少穿过前景边缘的漏色 | 屏幕／计算 | 引导缓冲一致性、边缘漏色和过锐边界 | [S44](https://research.nvidia.com/publication/2017-07_spatiotemporal-variance-guided-filtering-real-time-reconstruction-path-traced)；直接相关的机制／实现资料 |
| K04 | Bloom 泛光 | 将高亮能量扩散到邻域 | 让霓虹灯和火花具有可读的亮光晕 | 表现阳光在金属表面的强反射扩散 | 屏幕／多遍 | 曝光与阈值、能量保持；不能代替照亮周围物体 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；直接相关的机制／实现资料 |
| K05 | CoC 景深 | 用弥散圈半径决定失焦模糊 | 产品展示时对焦前景商品并虚化背景 | 角色对话时在近远角色间转移焦点 | 屏幕／多遍 | 前景遮挡、焦外亮点、边缘漏色与焦平面 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；直接相关的机制／实现资料 |
| K06 | 运动向量模糊 | 沿像素的屏幕运动路径近似曝光积分 | 为快速驶过的汽车表现方向一致的拖模糊 | 在急转镜头时表现合理的场景运动模糊 | 屏幕 | 物体与相机运动、遮挡显露、透明物运动向量 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；相关背景；未核到该变体专门资料 |
| K07 | 直方图自动曝光 | 从亮度分布估计曝光并做时间适应 | 让玩家从暗洞走到阳光下时逐步适应亮度 | 防止夜街上的小块强灯光把整幅画面压得过暗 | 计算／屏幕 | 测光区域、极亮值、适应速度与闪烁 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；直接相关的机制／实现资料 |
| K08 | 色调映射（模型族） | 将HDR亮度映射到显示范围 | 在明亮天空下同时保留建筑阴影与高光层次 | 展示发光特效与普通材质时控制高亮压缩 | 屏幕 | Reinhard、Filmic、ACES等不是同一公式；色域和曝光需固定 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；直接相关的机制／实现资料 |
| K09 | 3D LUT 调色 | 以颜色查找表统一外观变换 | 为同一场景切换冷夜与暖日落的美术调色 | 为回忆片段施加一致的低饱和电影色调 | 屏幕 | LUT输入空间、插值、越界颜色与重复变换 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；相关背景；未核到该变体专门资料 |
| K10 | 屏幕折射／扭曲 | 用位移场重采样背景 | 在篝火上方表现热浪空气扭曲 | 在爆炸中心生成向外传播的冲击波背景变形 | 材质／屏幕 | 深度遮挡、采样越界；不能变形本应位于前景的物体 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；直接相关的机制／实现资料 |
| K11 | 色差近似 | 对不同颜色通道采用不同采样位移 | 模拟廉价镜头画面边缘的轻微色散 | 为受击或科幻视效制造受控的通道偏移 | 屏幕 | 中心与边缘强度、UI可读性；不是实际所有色差的模型 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；相关背景；未核到该变体专门资料 |
| K12 | 镜头光晕／Ghosts | 按亮源位置生成镜头式鬼影和光纹 | 摄像机朝向低空太阳时出现镜头眩光 | 夜间车灯朝向镜头时产生可见光晕串 | 屏幕／多遍 | 光源遮挡、视角依赖、与Bloom职责不同 | [S15](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)；相关背景；未核到该变体专门资料 |
| K13 | CAS 对比度自适应锐化 | 根据局部对比度调整锐化 | 缓解时序抗锯齿后画面整体偏软 | 为上采样后的建筑和材质细节恢复局部清晰感 | 屏幕／计算 | 过冲、白边、噪声放大；不能恢复不存在的真细节 | [S54](https://gpuopen.com/fidelityfx-cas/)；直接相关的机制／实现资料 |

## L. 采样、透明与GPU管线

| 编号 | 算法／技术 | 负责的部分 | 场景1 | 场景2 | 运行载体 | 检查点 | 资料 |
|---|---|---|---|---|---|---|---|
| L01 | Mipmapping／三线性过滤 | 依据采样尺度选择和混合预过滤纹理 | 降低远处屋顶瓦片的闪烁 | 让重复地砖纹理远近切换时更连续 | 材质／预计算 | mip内容、LOD与色彩空间；不要用于不应插值的ID数据 | [S09](https://google.github.io/filament/main/filament.html)；相关背景；未核到该变体专门资料 |
| L02 | 各向异性纹理过滤 | 对拉长的像素覆盖区域增加方向性采样 | 保持掠射视角公路纹理的可读性 | 改善沿长走廊观察时地板细节的模糊 | 材质／管线 | 与各向异性BRDF完全不同；纹理边缘和开销 | [S09](https://google.github.io/filament/main/filament.html)；相关背景；未核到该变体专门资料 |
| L03 | 基于导数的解析抗锯齿 | 用屏幕导数估计边缘覆盖宽度 | 让程序网格线在缩放时保持平滑 | 让SDF文字和图形边缘在不同尺寸下稳定 | 材质／屏幕 | 导数坐标、非均匀分支、线宽的空间单位 | [S06](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)；直接相关的机制／实现资料 |
| L04 | FXAA | 根据单帧颜色边缘作快速平滑 | 在轻量三维预览中缓解模型轮廓锯齿 | 为不保留历史帧的应用增加低成本后处理AA | 屏幕 | 文字变软、细节损失；不保证消除时序闪烁 | [S41](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)；直接相关的机制／实现资料 |
| L05 | SMAA | 用形态边缘模式进行抗锯齿混合 | 改善建筑窗框和栏杆等细线边缘 | 在不使用历史帧时改善场景几何锯齿 | 屏幕／多遍 | 对角线、亚像素细节；区分1x与时序变体 | [S41](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)；直接相关的机制／实现资料 |
| L06 | TAA | 重投影并累积历史帧降低锯齿 | 稳定植被与细小高光在移动镜头下的闪烁 | 稳定栅栏和远处重复细节 | 屏幕／历史缓冲 | 拖影、遮挡显露、运动向量与历史拒绝 | [S41](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)；直接相关的机制／实现资料 |
| L07 | 时序上采样 | 综合低分辨率当前帧与历史信息重建高分辨率 | 在较低内部渲染分辨率下显示高分辨率游戏画面 | 在负载变化时用动态分辨率维持可读画面 | 屏幕／计算／高级 | 与插帧不同；透明特效、细线和历史失效 | [S41](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)；直接相关的机制／实现资料 |
| L08 | 蓝噪声／时空蓝噪声 | 将稀疏采样误差分布得更利于感知或重建 | 为体积雾步进抖动减少规则条纹 | 为低采样AO或软阴影分配采样偏移 | 材质／屏幕／计算 | 采样分布、循环周期、与时序滤波配合 | [S42](https://research.nvidia.com/publication/2022-07_spatiotemporal-blue-noise-masks)；直接相关的机制／实现资料 |
| L09 | Alpha-to-Coverage | 将透明裁切边缘映射到多重采样覆盖 | 平滑树叶透明裁切轮廓 | 改善草尖和铁丝网透明纹理的边缘 | 材质／MSAA管线 | 依赖覆盖采样；不是一般半透明排序方案 | [S41](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)；直接相关的机制／实现资料 |
| L10 | Weighted Blended OIT | 以加权累积近似不排序透明混合 | 合成大量交错的烟尘粒子 | 合成相互穿插的半透明能量薄片 | 多遍／管线 | 近似而非精确；不适合承诺正确的厚玻璃折射 | [S60](https://jcgt.org/published/0002/02)；相关背景；未核到该变体专门资料 |
| L11 | Depth Peeling 深度剥离 | 多遍提取可见透明深度层再合成 | 展示多层透明工业结构的内部关系 | 为多层交错的半透明模型生成排序参考 | 多遍／管线／高级 | 层数预算、近似终止和多遍成本 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；相关背景；未核到该变体专门资料 |
| L12 | Hi-Z 层级深度剔除 | 用深度金字塔快速拒绝被遮挡对象 | 避免绘制城市街区里被整栋楼挡住的实例 | 在工厂场景中剔除大型机器背后的零件 | 计算／管线／高级 | 保守性、深度方向、相机运动导致的错误剔除 | [S40](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)；相关背景；未核到该变体专门资料 |
| L13 | Clustered／Tiled Lighting | 按屏幕或视锥区域构建局部灯光列表 | 为夜街大量路灯与店招组织光照计算 | 为工业大厅的多盏局部灯减少无关光源计算 | 计算／管线／高级 | 不是增加灯数量的参数题；列表溢出和边界正确性 | [S09](https://google.github.io/filament/main/filament.html)；直接相关的机制／实现资料 |
| L14 | Prefix Scan／流压缩 | 用前缀和为有效元素分配紧凑索引 | 把存活粒子压紧后生成绘制列表 | 为可见草丛实例构建间接绘制参数 | 计算／高级 | 前缀偏移、容量、同步与零元素输入 | [S45](https://gpuopen.com/fidelityfx-parallel-sort/)；直接相关的机制／实现资料 |
| L15 | GPU Radix Sort 基数排序 | 按键值分组重排大量GPU数据 | 按深度排序透明粒子以改善传统透明混合 | 按空间网格键排列流体粒子以服务邻域搜索 | 计算／高级 | 键编码、稳定性、并行同步；排序不是邻域求解本身 | [S45](https://gpuopen.com/fidelityfx-parallel-sort/)；直接相关的机制／实现资料 |
| L16 | 重要性采样／MIS | 按贡献分布采样并组合不同采样策略 | 为HDR环境中的小亮太阳分配更多有效采样 | 同时处理光泽材质反射和小面积灯的光照积分 | 计算／管线／高级 | PDF与权重一致、偏差和火花噪声 | [S10](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory)；相关背景；未核到该变体专门资料 |
| L17 | ReSTIR 直接光采样 | 通过时空重采样复用候选光源样本 | 为含大量发光广告牌的夜景选择直接光样本 | 为大量动态发光物体组成的场景估计直接照明 | 计算／管线／高级 | 本条限直接光版本；可见性变化、权重和时空相关误差 | [S43](https://research.nvidia.com/publication/2020-07_spatiotemporal-reservoir-resampling-real-time-ray-tracing-dynamic-direct)；直接相关的机制／实现资料 |
| L18 | SVGF 时空降噪 | 利用历史和方差信息引导多尺度滤波 | 重建低采样路径追踪室内的间接光 | 让稀疏采样全局光照在动态镜头下更稳定 | 屏幕／计算／高级 | 运动边界、历史失效、细节抹除和偏差 | [S44](https://research.nvidia.com/publication/2017-07_spatiotemporal-variance-guided-filtering-real-time-reconstruction-path-traced)；直接相关的机制／实现资料 |

## 组合场景包

### P01 雨后森林小径

基础条件：有土路、石块、草和灌木；保留可接近的地表与水洼。
拟制作效果：湿斑与干区分布；水洼波纹；人物经过草丛后的短暂弯曲。
候选算法：A02, B06, B08, C05, G04, H03, H05, I10。
边界：让湿度、局部事件和植被运动各有独立输入；不要依赖固定视角。
变化条件：镜头近远移动、人物经过、雨滴事件位置改变。
范围：材质＋反馈。状态：构想，未实现。

### P02 带礁石的浅溪

基础条件：弯曲河道、坡度变化、岸边石块和浅滩。
拟制作效果：基础版流向纹理；进阶版水深／速度变化与障碍响应。
候选算法：B14, E07, E08, G06, G12, G13, I11。
边界：区分预画流向与模拟速度；水流、泡沫和水色的空间关系需一致。
变化条件：移动石块或改变入流，观察流向与水量；水外区域不出现焦散。
范围：材质＋计算。状态：构想，未实现。

### P03 烟雾工厂车间

基础条件：封闭室内、横梁、门窗、多个可开关灯与烟源。
拟制作效果：烟随流动传播；灯光照亮烟；横梁切断光柱。
候选算法：A06, F03, F04, F05, F09, G07, G08, G09, K03。
边界：将密度模拟、体积积分和光照遮挡分开；静态亮雾不能替代动态行为。
变化条件：移动光源、关闭灯、移动镜头、增减烟源。
范围：计算＋体积管线。状态：构想，未实现。

### P04 材质摄影棚

基础条件：统一几何、可移动面光源、统一环境图、固定曝光。
拟制作效果：拉丝金属、清漆木材、布料、蜡／皮肤和薄膜样本。
候选算法：B09, C04, C06, C07, C08, C09, C12, E01, E09。
边界：同一控制变量下区分反射模型，避免换贴图或曝光制造差异。
变化条件：旋转物体、光源与相机；比较粗糙度和厚度变化。
范围：材质＋照明。状态：构想，未实现。

### P05 雪地营地

基础条件：可踩踏雪地、石块、篝火、帐篷与植被。
拟制作效果：积雪分布；脚印累积；火焰、余烬和热扭曲。
候选算法：A07, B06, B07, H01, I03, I05, I10, K04, K10。
边界：区分积雪遮罩与真实压痕；区分粒子火焰与流体火焰。
变化条件：重复踩踏同位置、改变光照方向、近景检查轮廓与阴影。
范围：顶点＋材质＋反馈。状态：构想，未实现。

### P06 交互液体桌面

基础条件：杯、盆、倾倒容器与可移动障碍物。
拟制作效果：液体倾倒、碰撞、汇聚及表面反射／吸收。
候选算法：G10, G11, H09, E05, E07, E08。
边界：SPH和PBF作为可替换路线，不必同时使用；模拟与表面重建分开。
变化条件：倾斜容器、移动障碍，检查体积／密度漂移、穿透与稳定性。
范围：高级计算。状态：构想，未实现。

### P07 霓虹雨夜街道

基础条件：灯牌、湿路面、金属道具、玻璃、烟尘与移动角色。
拟制作效果：湿地反射、多灯照明、透明叠加、曝光适应。
候选算法：E05, E06, K04, K07, K08, L06, L10, L13, L17, L18。
边界：SSR／光追与聚类／ReSTIR是不同任务路线；避免全部强塞成一个项目。
变化条件：光源开关、反射对象出屏、角色穿过烟尘、镜头快速移动。
范围：多路线的管线场景。状态：构想，未实现。

### P08 风格化角色展厅

基础条件：角色、道具、可控灯光与带纵深的背景。
拟制作效果：卡通块面、轮廓、排线／网点；展示皮肤、头发和服装分工。
候选算法：C08, C11, H06, H07, J01, J02, J03, J05, J06。
边界：固定目标风格与视角范围；外轮廓和内部折线分开设计。
变化条件：角色旋转、骨骼扭转、光源绕行、镜头拉远。
范围：材质＋顶点＋后处理。状态：构想，未实现。

## 参考资料

- S01：[NVIDIA GPU Gems：Improved Perlin Noise](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-5-implementing-improved-perlin-noise)。覆盖主题：噪声基础、梯度噪声。
- S02：[Blender Manual：Noise Texture](https://docs.blender.org/manual/en/latest/compositing/types/texture/noise.html)。覆盖主题：分形噪声、octave与纹理。
- S03：[Blender Manual：Voronoi Texture](https://docs.blender.org/manual/en/latest/compositing/types/texture/voronoi.html)。覆盖主题：Worley/Voronoi图案。
- S04：[Blender Manual：Gabor Texture](https://docs.blender.org/manual/en/latest/compositing/types/texture/gabor.html)。覆盖主题：有方向的程序纹理。
- S05：[Blender Manual：Wave Texture](https://docs.blender.org/manual/en/latest/compositing/types/texture/wave.html)。覆盖主题：条纹、环纹。
- S06：[Unity Shader Graph：Feature Examples](https://docs.unity3d.com/Packages/com.unity.shadergraph@17.0/manual/Shader-Graph-Sample-Feature-Examples.html)。覆盖主题：材质混合、法线混合、坐标、风格化、VFX等技术示例。
- S07：[Deliot与Heitz：Procedural Stochastic Textures by Tiling and Blending](https://eheitzresearch.wordpress.com/738-2/)。覆盖主题：随机化纹理平铺。
- S08：[Bridson等：Curl-noise for procedural fluid flow](https://dl.acm.org/doi/10.1145/1276377.1276435)。覆盖主题：程序速度场；非完整流体求解。
- S09：[Google Filament：Physically Based Rendering](https://google.github.io/filament/main/filament.html)。覆盖主题：反射模型、IBL、材质与渲染管线。
- S10：[PBRT v4：Roughness Using Microfacet Theory](https://pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory)。覆盖主题：微表面模型、各向异性。
- S11：[NVIDIA GPU Gems：Simulating Diffraction](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-8-simulating-diffraction)。覆盖主题：衍射的视觉建模。
- S12：[NVIDIA GPU Gems：Shadow Map Antialiasing](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows/chapter-11-shadow-map-antialiasing)。覆盖主题：阴影贴图与PCF。
- S13：[NVIDIA GPU Gems 3：Summed-Area Variance Shadow Maps](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-8-summed-area-variance-shadow-maps)。覆盖主题：VSM、软阴影与滤波。
- S14：[Microsoft：Cascaded Shadow Maps](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/cascaded-shadow-maps)。覆盖主题：级联阴影。
- S15：[Godot Manual：Environment and Post-processing](https://docs.godotengine.org/en/stable/tutorials/3d/environment_and_post_processing.html)。覆盖主题：AO、雾、曝光、色调映射、后处理。
- S16：[AMD GPUOpen：Stochastic Screen Space Reflections](https://gpuopen.com/fidelityfx-sssr/)。覆盖主题：屏幕空间反射。
- S17：[Godot Manual：Reflection Probes](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/reflection_probes.html)。覆盖主题：反射探针与盒投影。
- S18：[AMD GPUOpen：Hybrid Stochastic Reflections](https://gpuopen.com/fidelityfx-hybrid-reflections/)。覆盖主题：屏幕空间与光线追踪反射。
- S19：[Heitz等：Real-Time Polygonal-Light Shading with LTCs](https://eheitzresearch.wordpress.com/415-2/)。覆盖主题：线性变换余弦、面光源积分。
- S20：[Godot Manual：VoxelGI](https://docs.godotengine.org/en/stable/tutorials/3d/global_illumination/using_voxel_gi.html)。覆盖主题：体素全局光照。
- S21：[McGuire：Dynamic Diffuse Global Illumination](https://morgan3d.github.io/articles/2019-04-01-ddgi/)。覆盖主题：动态漫反射探针光照。
- S22：[Godot Manual：Volumetric Fog](https://docs.godotengine.org/en/stable/tutorials/3d/volumetric_fog.html)。覆盖主题：体积密度、光照、各向异性和时序。
- S23：[NVIDIA GPU Gems 2：Accurate Atmospheric Scattering](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-16-accurate-atmospheric-scattering)。覆盖主题：大气散射、Rayleigh、Mie。
- S24：[NVIDIA GPU Gems 3：Volumetric Light Scattering as a Post-Process](https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process)。覆盖主题：屏幕空间光束近似。
- S25：[NVIDIA GPU Gems：Effective Water Simulation from Physical Models](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models)。覆盖主题：波浪、几何与法线分层。
- S26：[NVIDIA GPU Gems：Fast Fluid Dynamics Simulation on the GPU](https://developer.nvidia.com/gpugems/gpugems/part-vi-beyond-triangles/chapter-38-fast-fluid-dynamics-simulation-gpu)。覆盖主题：网格流体、平流、压力投影。
- S27：[NVIDIA GPU Gems 3：Real-Time Simulation and Rendering of 3D Fluids](https://developer.nvidia.com/gpugems/gpugems3/part-v-physics-simulation/chapter-30-real-time-simulation-and-rendering-3d-fluids)。覆盖主题：烟火流体模拟、涡量与渲染。
- S28：[Macklin与Müller：Position Based Fluids](https://mmacklin.com/pbf_sig_preprint.pdf)。覆盖主题：基于位置约束的粒子液体。
- S29：[Müller等：Particle-Based Fluid Simulation for Interactive Applications](https://matthias-research.github.io/pages/publications/sca03.pdf)。覆盖主题：SPH交互液体。
- S30：[NVIDIA GPU Gems：Rendering Water Caustics](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics)。覆盖主题：水下焦散、物理过程与外观近似。
- S31：[NVIDIA GPU Gems 3：Generating Complex Procedural Terrains Using the GPU](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-1-generating-complex-procedural-terrains-using-gpu)。覆盖主题：密度场、Marching Cubes、地形。
- S32：[NVIDIA GPU Gems 3：GPU-Generated Procedural Wind Animations for Trees](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-6-gpu-generated-procedural-wind-animations-trees)。覆盖主题：层级树木风动画。
- S33：[NVIDIA GPU Gems 3：Vegetation Procedural Animation and Shading in Crysis](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis)。覆盖主题：主弯曲、叶片细动与植被着色。
- S34：[Godot Manual：Particle Collision](https://docs.godotengine.org/en/stable/tutorials/3d/particles/collision.html)。覆盖主题：粒子与SDF/高度场碰撞。
- S35：[Godot Manual：Particle Shaders](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/particle_shader.html)。覆盖主题：有状态GPU粒子更新。
- S36：[Karl Sims：Reaction-Diffusion Tutorial](https://www.karlsims.com/rd.html)。覆盖主题：反应扩散图案。
- S37：[Rong与Tan：Jump Flooding in GPU](https://www.comp.nus.edu.sg/~tants/jfa/i3d06.pdf)。覆盖主题：近似Voronoi与距离变换。
- S38：[NVIDIA GPU Gems 2：Blueprint Rendering and Sketchy Drawings](https://developer.nvidia.com/gpugems/gpugems2/part-ii-shading-lighting-and-shadows/chapter-15-blueprint-rendering-and-sketchy)。覆盖主题：工程图与素描风格化。
- S39：[Kyprianidis等：Anisotropic Kuwahara Filtering on the GPU](https://www.kyprianidis.com/p/gpupro/)。覆盖主题：方向自适应的绘画滤波。
- S40：[Godot Manual：Advanced Post-processing](https://docs.godotengine.org/en/stable/tutorials/shaders/advanced_postprocessing.html)。覆盖主题：全屏处理、深度重建。
- S41：[Godot Manual：3D Antialiasing](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html)。覆盖主题：AA、时序超采样、透明裁切边缘。
- S42：[NVIDIA Research：Spatiotemporal Blue Noise Masks](https://research.nvidia.com/publication/2022-07_spatiotemporal-blue-noise-masks)。覆盖主题：时空采样噪声。
- S43：[NVIDIA Research：Spatiotemporal Reservoir Resampling for Real-Time Ray Tracing](https://research.nvidia.com/publication/2020-07_spatiotemporal-reservoir-resampling-real-time-ray-tracing-dynamic-direct)。覆盖主题：ReSTIR直接光采样。
- S44：[NVIDIA Research：Spatiotemporal Variance-Guided Filtering](https://research.nvidia.com/publication/2017-07_spatiotemporal-variance-guided-filtering-real-time-reconstruction-path-traced)。覆盖主题：SVGF时空降噪。
- S45：[AMD GPUOpen：FidelityFX Parallel Sort](https://gpuopen.com/fidelityfx-parallel-sort/)。覆盖主题：GPU基数排序与前缀扫描。
- S46：[Unity Shader Graph：Triplanar Node](https://docs.unity3d.com/Packages/com.unity.shadergraph%4014.0/manual/Triplanar-Node.html)。覆盖主题：三平面投影与法线。
- S47：[Vertex Shader Domain Warping with Automatic Differentiation](https://arxiv.org/html/2405.07124v1)。覆盖主题：空间扭曲和几何法线。
- S48：[AMD GPUOpen：CACAO](https://gpuopen.com/fidelityfx-cacao/)。覆盖主题：计算着色器环境遮蔽。
- S49：[PBRT v3：Microfacet Models（含Oren–Nayar）](https://pbr-book.org/3ed-2018/Reflection_Models/Microfacet_Models)。覆盖主题：粗糙漫反射与微表面反射。
- S50：[PBRT v4：Scattering from Hair](https://pbr-book.org/4ed/Reflection_Models/Scattering_from_Hair)。覆盖主题：沿发丝坐标系的纤维散射。
- S51：[Gustavson：webgl-noise](https://stegu.github.io/webgl-noise/)。覆盖主题：Simplex、经典梯度噪声、周期噪声。
- S52：[SideFX：Vertex Animation Textures](https://www.sidefx.com/docs/houdini/nodes/out/labs--vertex_animation_textures-3.0.html)。覆盖主题：VAT、复杂动画的纹理编码回放。
- S53：[AMD GPUOpen：FidelityFX Blur](https://gpuopen.com/fidelityfx-blur/)。覆盖主题：高斯滤波和GPU图像模糊。
- S54：[AMD GPUOpen：Contrast Adaptive Sharpening](https://gpuopen.com/fidelityfx-cas/)。覆盖主题：自适应锐化。
- S55：[Bruneton：Precomputed Atmospheric Scattering](https://ebruneton.github.io/precomputed_atmospheric_scattering/)。覆盖主题：预计算大气积分、GLSL实现及测试。
- S56：[Intel GameTechDev：XeGTAO](https://github.com/GameTechDev/XeGTAO)。覆盖主题：GTAO实现、厚度假设和误差。
- S57：[NVIDIA：Horizon-Based Ambient Occlusion Plus](https://developer.nvidia.com/rendering-technologies/horizon-based-ambient-occlusion-plus)。覆盖主题：HBAO家族的官方技术说明。
- S58：[Chentanez与Müller：Real-time Simulation of Large Bodies of Water with Small Scale Details](https://matthias-research.github.io/pages/publications/hfFluid.pdf)。覆盖主题：波动方程与浅水方程差别、浅水求解与粒子混合。
- S59：[Belcour与Barla：A Practical Extension to Microfacet Theory for Varying Iridescence](https://belcour.github.io/blog/research/publication/2017/05/01/brdf-thin-film.html)。覆盖主题：薄膜干涉与微表面外观。
- S60：[JCGT 2013：Weighted Blended OIT 出版目录](https://jcgt.org/published/0002/02)。覆盖主题：论文出版条目；本次未读到论文正文。