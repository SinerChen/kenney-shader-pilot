# F02_L1 · 能量走廊 · 基础能量材质

为 Emitter 和 Panel 实现空间上连续的能量发光纹理，保留表面结构与明暗层次，画面不能整体过曝。

本任务使用固定的 Godot 4.6.1 / Forward+ 场景。先阅读 HOST_API.md 和本题 task.json。只修改分配的 effects/F02/ 目录，可增加该目录下的 shader 和辅助脚本；保留场景几何、资产、相机、事件协议及测试脚本。

从无目标效果的基线开始。

验收要点：
- 发光限制于指定载体
- 纹理具有空间连续性
- 基础结构仍可辨识
- 亮部不过度覆盖其他内容

setup(context)、reset(state)、step(dt,state)、on_event(name,payload,state) 是统一入口。效果时间使用 state.elapsed，不依赖机器墙钟；事件目标名称与坐标以场景合同为准。输出修改后的完整文件，不输出仅说明实现意图的伪代码。
