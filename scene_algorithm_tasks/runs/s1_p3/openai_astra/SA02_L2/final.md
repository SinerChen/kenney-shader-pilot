已完成实现，修改文件：

- `effect/main.gd`
  - Gerstner 波面位置与单位法线
  - 周期中央差分水平位移 Jacobian
  - 泡沫指数衰减、压缩增长及 `[0,1]` 限制
  - 输出固定格式的 `positions`、`normals`、`jacobian`、`foam`
- `effect/ocean_surface.gd`
  - 将数值泡沫历史上传为 RF 纹理
  - 泡沫按相同参数坐标 `q` 绑定到波面
  - 支持中心及相邻 LOD 网格连续显示
  - 保留海床与宿主水面效果，禁用无关原生泡沫源
- `effect/verify.gd`
  - 增加独立 Gerstner、Jacobian 和泡沫历史回归验证
- `effect/plan.json`
  - 已记录完整计划、观察结果并标记为 `completed`

验证结果：

- 固定记录帧 `1、60、120、180` 均正常生成 samples。
- 4096 个网格点通过独立数值验证。
- 位置误差最高约 `4.77e-7`。
- Jacobian 误差最高约 `3.0e-8`。
- 泡沫历史误差最高约 `2e-9`。
- 泡沫随压缩波带生成、衰减并附着于对应波面位置。
- `scene/main.tscn` 无运行错误，保留中心及相邻 LOD 网格和海床。