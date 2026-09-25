# 场景与效果接口（pilot_v1）

本轮为 5 个场景、15 个任务的准备环境。模型效果入口为空；场景资产、控制器、碰撞、相机和事件由本地宿主提供。原项目保留在 `upstream/`，可运行副本在 `projects/platformer/` 与 `projects/fps/`，两者不共享 Autoload 或 Godot 资源 UID 空间。

## 固定条件

- Godot 4.6.1，Forward+，基准视口 960×640，种子 20260923。
- 基线相机 `Observer` 位于 (15, 13, 19)，看向 (0, 1, -2)，FOV 48°。
- 180 步基线自检中，第 91 步之前相机向世界 X 正方向平移 1，然后继续看向同一目标。
- 同一条任务链继承同一个模型上一等级的提交。第一级从空效果基线开始；不自动补入正确答案。
- 模型只改对应 `effects/<scene_id>/`，可在该目录新增 `.gdshader`、`.gd`、`.tres`。不改宿主、资源、测试事件、目标节点名称、相机或原玩家逻辑。
- 新效果必须由模型实现。已收集的完整 shader 答案不会自动复制到任务输入中。

## 效果入口

每个项目中 `effects/<scene_id>/effect.gd` 挂在 `EffectAdapter`。必须提供四个函数：

```gdscript
func setup(context: Dictionary) -> void:
    pass
func reset(state: Dictionary) -> void:
    pass
func step(dt: float, state: Dictionary) -> void:
    pass
func on_event(event_name: String, payload: Dictionary, state: Dictionary) -> void:
    pass
```

`setup` 在节点就绪后调用一次。`context` 包含：

| 键 | 内容 |
| --- | --- |
| scene_id | P01/P02/P03/F01/F02 |
| targets | 名称到实际 Node3D 的字典；可能是模型根或 MeshInstance3D，应遍历其网格子节点 |
| environment | 当前 Environment 资源 |
| camera | 固定观察 Camera3D；自动评测使用该相机 |
| root | 当前场景根节点 |
| hud | 空白 Control，仅供待实现的任务 HUD 使用 |
| seed | 固定初值 20260923 |

`reset` 必须清除模型新增的事件状态、历史资源与临时对象，并重新设置材质初始值。宿主恢复相机、玩家、目标变换和事件日志；不会替模型恢复被其修改的材质。`step` 使用秒为单位的 dt，每次负责一帧效果推进，不能再通过 `_process` 重复推进。shader 使用自定义时间参数或从 `state.elapsed` 派生的值；不要依赖全局 TIME 来冒充可重放时间。

`state` 包含 level、elapsed、frame、seed，以及预留的 wind_strength、wind_direction、wetness、power、health、scan_enabled。事件 payload 是本题交互的权威输入；宿主不自动推断或实现对应 shader 状态机。模型自行保存并更新事件状态。

宿主提供 `reset(seed)`、`step(dt)`、`set_parameters(values)`、`emit_event(name,payload)`。dt 范围 (0, 0.1]。一次 step 不应启动重叠的异步更新。世界坐标使用 Godot 的右手坐标，Y 向上；JSON 中向量以数组给出，效果脚本需转换为 Vector3。

## 五个场景的载体

| 场景 | 目标节点 | 用途 |
| --- | --- | --- |
| P01 | MaterialA/B/C、CollectibleA/B、Gate | 三种材质、两个收集物、解锁门 |
| P02 | Water、BridgeA/B、Obstacle | 水面、跳台、交界物；水面 y=0.22 |
| P03 | GrassField、Flag、InteractionMarker | 草实例组、细分旗面、局部作用位置标记 |
| F01 | TargetA/B/C、Cover | 可射击靶标、遮挡物；靶标 damage() 转成 hit/destroy 事件 |
| F02 | Emitter、BeamVolume、Occluder、Panel | 能量源、预留体积载体、遮挡体、显示面板 |

P03 的 Flag 是额外细分平面，便于顶点变形；GrassField 包含 25 个 Kenney 草实例。F02 的 BeamVolume 在基线中不可见；实现体积任务时模型可设置其材质和可见性。新增基础网格是评测载体，不是完整效果答案。其他 Kenney 几何与贴图保持来源关联。

## 事件与检查

各场景 `pilot/scenes.json`、根目录 `manifest.json` 提供具体帧号、事件名和 payload。事件在表中指定 step **之前**发出；例如 before_step=30 表示已完成 29 步。日志同时记录 before_step、completed_frames 和时间，避免把前帧状态误作触发后的状态。

基线自检先等待一次场景就绪帧，然后 reset。从此以 dt=1/60 推进 180 步，在第 1/60/120/180 步后记录截图；全程累计 3 秒效果时间。这里只验证场景、接口、加载和基本渲染，不代表 15 个 shader 任务已经通过。后续正式验收还需按 EVALUATION_DESIGN.md 增加静止尾段、重复事件和不同相机路径。

交互查看：TAB 切换观察/原角色控制，SPACE 在观察模式中依次发出本场景事件，R 重置，1/2/3 切换等级；Platformer 用 WASD、Space、方向键，FPS 用 WASD、鼠标、左键、E、Esc。交互游玩并非固定时间的评分轨迹。
