# FG01 · 草地小场景合同

本题基于 Forest Benchmark 的 Grass1–4 草片与原贴图，搭建独立草地小场景。Godot 4.6.1 / Forward+；场地约 7.2 × 6.8 m，335 张草片，固定布局种子 20260923。草片在原四角间增加 18 段高度、4 段宽度的细分，每张 95 个顶点；这是三关共同的输入资产，不是模型需要补写的内容。

## 可修改与固定部分

- 只编辑 `project/effect/grass.gdshader`，输出其完整代码。
- 保留原草贴图、Alpha 裁切与受光，不用色块、屏幕晃动或相机移动伪装草的形变。
- 场景、草实例的节点变换、相机、玩家控制、光照和回放由宿主固定提供。
- 不修改 `host/`、`assets/`、`scenes/`、`project.godot` 或测试过程。
- 使用宿主传入的 `elapsed`，不能依赖全局 `TIME`，保证暂停、重置与手动步进有效。
- L2、L3 接续同一个模型的上一层候选代码；不自动填入本地参考答案。上一层有缺陷时允许在升级中修复，并记录上一层是否正式提交。

## Shader 数据

草片启用 `world_vertex_coords`：`VERTEX` 和 `NORMAL` 为世界空间，Y 向上。

| 输入 | 含义 |
| --- | --- |
| `UV` | 原草贴图的 atlas 坐标，不等同于草叶高度 |
| `UV2.y` | 沿草片的归一化高度，根部 0，顶边 1 |
| `MODEL_MATRIX[3].xz` | 当前草实例根部中心的世界 XZ 坐标 |
| `INSTANCE_CUSTOM.r` | 固定在实例上的 0–1 随机值，可用于相位差异 |
| `elapsed` | 自 reset 起累计秒数，由 step 驱动 |
| `wind_strength` | 风动幅度输入，默认 0.22，公开检查范围 0–0.45 |
| `wind_speed` | 时间变化速率输入，默认 1.6，检查范围 0–3 |
| `wind_direction` | 世界 XZ 风向向量，默认 (1, 0.35)；零向量视为无风，不能产生 NaN |
| `player_position` | 当前玩家脚底中心世界坐标 |
| `interaction_radius` | 玩家影响半径，默认 0.95 m |
| `interaction_strength` | 压草程度输入，默认 0.95 |
| `player_history[32]` | vec4 数组，各元素为 `(world_x, world_z, age_seconds, valid)` |
| `grass_albedo` / `grass_orm` | 已绑定的原始草贴图 |
| `audit_roots` / `audit_tips` | 预留的端点诊断显示，不是运动算法；默认 false |

history 第 0 项为当前位置，age=0；其余项为约每 0.1 秒记录的最近位置。valid=0 的项无效。宿主只记录原始轨迹，不计算影响权重、外倒方向、恢复程度或根部形变，这些由提交的 shader 实现。轨迹可用于“经过后”的短时响应；不能只检测当前玩家位置然后立刻恢复。

## 宿主接口

```gdscript
reset()                         # elapsed/frame/轨迹清零，玩家回到 (-4,0,0)
step(dt)                        # 0 < dt <= 0.1，推进一次效果输入
set_parameters(values)          # wind_strength / wind_speed / wind_direction / player_position
set_level(1 | 2 | 3)             # 切换等级并重置
set_camera("overview" | "roots" | "top")
```

使用 `--manual-step` 时宿主不会在 `_process` 内自动推进。拟接入的公开自动检查以 1/60 秒推进；当前网页动画通过每次 5 个 0.025 秒步骤生成 8 fps 采样，不是模型评测分数。

自动玩家回放为 11 秒：前 1 秒位于 x=-4；第 1–6.5 秒沿 z=0 从 x=-4 行走至 x=4；第 6.5–11 秒停留在草地外，用于观察恢复。原生预览也可点击 `Replay / WASD`，以 WASD 手动经过不同位置。

## 输入边界

模型输入为当前题面、本合同、初始/上一层候选代码以及公开检查说明；不能将 `reference/`、`tools/build_reference.py` 或参考源码作为模型输入。S1/P3 只回传模型自己候选的真实 PNG，不输入作者参考图。模型只可修改 grass.gdshader，不能读取本地任意文件。
