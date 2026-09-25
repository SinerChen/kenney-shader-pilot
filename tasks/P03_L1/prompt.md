# P03_L1 · 风动草地 · 锚定风动形变

让 GrassField 的草与 Flag 旗面随时间摆动。根部/固定边保持锚定，实例相位有空间变化，不通过整体平移模型制造摇摆。

本任务使用固定的 Godot 4.6.1 / Forward+ 场景。先阅读 HOST_API.md 和本题 task.json。只修改分配的 effects/P03/ 目录，可增加该目录下的 shader 和辅助脚本；保留场景几何、资产、相机、事件协议及测试脚本。

从无目标效果的基线开始。

验收要点：
- 草根和旗固定边稳定
- 形变连续且无整物漂移
- 不同实例不是完全同步
- 法线或明暗变化与形变相容

setup(context)、reset(state)、step(dt,state)、on_event(name,payload,state) 是统一入口。效果时间使用 state.elapsed，不依赖机器墙钟；事件目标名称与坐标以场景合同为准。输出修改后的完整文件，不输出仅说明实现意图的伪代码。
