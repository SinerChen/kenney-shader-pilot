已完成完整 Gerstner 波面实现。

修改文件：
- `effect/main.gd`：实现双方向 Gerstner 波、水平/垂直位移、解析切向与单位法线、周期中央差分 Jacobian、泡沫递推及采样输出。
- `effect/ocean_surface.gd`：保留原水材质与光照，仅替换顶点波面阶段，使 GPU 波形与数值采样一致。
- `effect/verify.gd`：加入固定输入闭式数值回归验证。
- `effect/plan.json`：记录实现计划与验证结果。

验证结果：
- 64×64 网格输出共 4096 个位置、法线、Jacobian 和泡沫值。
- 固定记录步 `1、60、120、180` 输出正常。
- 泡沫关闭时全部为 `0`。
- 法线单位化，水平位移和波峰移动可见。
- `scene/main.tscn` 渲染通过，无错误或警告。
- 观察结果保存在 `observations/render_20260924_224829_0a5674ad/`。