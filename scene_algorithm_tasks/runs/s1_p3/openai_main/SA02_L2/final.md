已完成并保存至 `effect/`：

- **`effect/main.gd`**
  - 实现双 Gerstner 波的位置与单位法线计算。
  - 按 64×64 行优先参数网格输出数据。
  - 对周期水平位移使用中央差分，计算映射 Jacobian。
  - 泡沫按“旧值指数衰减 → 加入压缩源 → 限制到 `[0,1]`”更新。
  - 泡沫状态始终绑定同一参数点 `q`，随其变形位置运动。
  - `sample()` 输出 `step`、`elapsed_s`、`positions`、`normals`、`jacobian` 和 `foam`。

- **`effect/gerstner_water.gdshader`**
  - 同步显示 Gerstner 波面。
  - 使用 Jacobian 压缩程度为波面添加泡沫高亮。

- **`effect/plan.json`**
  - 记录各阶段实施和验证结果，已标记完成。

已在第 **1、60、120、180** 帧进行完整渲染验证：Godot 导入与运行均无错误或警告，四个记录样本和对应画面均成功生成。