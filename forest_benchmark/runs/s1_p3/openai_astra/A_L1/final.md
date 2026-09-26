已完成实现，计划已标记为 `completed`。

**修改与新增文件**
- `solution/adapter.gd`：状态接口、GPU 查询及目标材质绑定。
- `solution/burn_math.gdshaderinc`：三维梯度噪声、fBM、空间灼烧前沿。
- `solution/wood_burn.gdshader`：木纹、橙黄发亮前沿和深色焦化区域。
- `solution/check.gd`：保留未挂载的自检脚本。
- `solution/plan.json`：实施与验证记录。`effect.tscn` 已恢复原始结构。

**验证结果**
- 120 帧渲染观察到起燃、逐渐扩展、最终完全焦化，三个区域清晰可辨。
- GPU 输出布局、前沿数值及禁用掩码自检通过。
- 场景保护检查通过，最终运行日志无错误。

**限制**
未取得资源中提及的完整算法契约，梯度顺序及 fBM 归一化约定仍需外部参考测试确认；当前静态场景未实测物体运动，图案采用物体局部坐标保持附着。