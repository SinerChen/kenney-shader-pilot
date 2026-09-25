已完成实现。

修改文件：
- `effect/main.gd`
- `effect/four_layer_height_blend.gdshader`
- `effect/plan.json`

实现效果：
- 四层 `height × control` 高度竞争、epsilon 与归一化。
- 一致混合颜色、粗糙度、金属度和高度。
- 基法线安全归一化与 RNM 细节法线组合。
- 湿色、低粗糙度高光和法线细节共用湿区权重。
- 保留石缝、石脊细节及随真实表面朝向变化的受光。
- Ground 与相邻 Section01 街区保持可见。

最终渲染无脚本或 Shader 编译错误，数值输出字段完整。固定输入权重约为：
`[0.19354929, 0.80644964, 0.00000108, 0]`。