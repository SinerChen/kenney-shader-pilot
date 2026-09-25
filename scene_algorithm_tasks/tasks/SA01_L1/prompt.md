# 交互场与固定根部变形

在当前 Godot 实验中实现以下效果。在 effect/ 中创建实现。

## 测试环境

从原草地拆出通行路径附近的一排草，保留原草片网格、地面、玩家、光照和相机；关闭风动。

复用现有 Godot 宿主。scene/main.tscn 为本层入口，scene/project/ 可读取原工程，scene/environment.json 说明本层范围。effect/main.gd 是效果入口：configure 接收原场景和固定输入，step 推进效果，sample 返回下述数值输出；可在 effect/ 中添加所需 shader 和辅助文件。

## 使用的算法

持久化交互场、指数时间衰减、双线性场采样及沿草高加权的顶点弯曲。

## 固定测试输入

本次输入固定如下，inputs/test_input.json 保存同一份数据。

```json
{
  "seed": 20260924,
  "dt_seconds": 0.016666666666666666,
  "steps": 240,
  "record_after_steps": [1, 60, 120, 240],
  "patch": {"origin_xz_m": [-4, -4], "size_m": 8, "resolution": [64, 64]},
  "interaction": {"radius_m": 0.95, "strength": 0.95, "persistence_per_60hz_step": 0.92, "bend_m": 0.35, "flatten_m": 0.1},
  "player_keyframes": [
    {"time_s": 0, "position_xz_m": [-3, 0]},
    {"time_s": 2, "position_xz_m": [3, 0]},
    {"time_s": 4, "position_xz_m": [3, 0]}
  ],
  "interaction_active_until_s": 2,
  "wind": {"strength": 0, "speed": 1.6, "direction_xz": [1, 0.35]},
  "camera": "overview"
}
```

Y 向上，位置和长度使用米。玩家位置在关键帧间线性插值，速度由该轨迹求得；每步先推进到新时间，再衰减并写入当前交互。到 2 秒时移除交互者，历史继续衰减。场纹素中心均匀分布在固定世界 patch；场外采样为零。草片根部和归一化高度从当前场景读取。

## 输出要求

将实现保存到 effect/。运行输出采用以下字段和顺序；render 将 sample 返回的数据保存到 observations/ 下的 samples.json：

- `samples`：按 record_after_steps 顺序输出，每项含 step、elapsed_s、field_rgba、positions、normals。
- `field_rgba`：64×64 行优先浮点数组，每点 [方向X×强度, 方向Z×强度, 压低强度, 0]。
- `positions`：按场景提供的实例及顶点顺序排列的世界坐标 [x,y,z] 数组。
- `normals`：与 positions 一一对应的单位世界法线 [x,y,z] 数组。

## 需要生成的效果

草在玩家经过的位置局部向外弯倒；根部固定，中上部产生主要位移。玩家离开后保留短时轨迹并平滑恢复；草片持续可见。该阶段风动关闭。

## 可观察和修改的目录

所有路径相对于当前实验根目录。

| 目录 | 权限 | 内容 |
|---|---|---|
| scene/ | 只读 | 当前实验场景、资产和固定宿主文件 |
| inputs/ | 只读 | 本次固定输入 |
| observations/ | 只读 | 当前实现运行后产生的图像、日志及数值结果 |
| effect/ | 可读写 | 本次需要实现或修改的效果文件 |

## 工具

- `read(path, start_line=1, max_lines=400)`：读取文件或列出目录；图像以图像数据返回。
- `write(path, content)`：在 effect/ 内创建或覆盖文件，content 为完整文本。
- `render(scene="scene/main.tscn", camera=..., frames=..., resolution=..., camera_track=...)`：运行当前实现并返回真实 PNG、日志路径和相机记录。

## 自主渲染观察

你可以自行选择观察角度、距离、透视或正交投影、视野、截图帧和图像分辨率，也可以设置相机轨迹。题面中的 camera 仅为默认观察设置；render 的相机参数只用于本次观察，不改写固定输入文件。

例如，从自选位置观察第 1、60、120 帧：

```json
{"camera":{"position":[6,4,8],"look_at":[0,0,0],"fov_degrees":50},"frames":[1,60,120],"resolution":[960,640]}
```

camera.position、look_at 和可选 up 使用世界坐标。俯视可设置 position=[0,8,0]、look_at=[0,0,0]、up=[0,0,-1]；正交视图用 projection="orthogonal" 和 orthogonal_size。省略 camera 时使用场景相机。

camera_track 为按帧递增的 [{frame,position,look_at}, ...]，位置与目标在关键帧之间线性插值。每次可取 1–4 个递增截图帧，范围不超过固定输入 steps，最多 720 帧。resolution 为 [宽,高]，各边 128–1920，总像素最多 2073600。

每次 render 从当前文件的新场景实例开始。返回的图像可直接观察，也可通过 read 再读取 observations/ 下的 PNG、日志、参数与结果。可通过日志定位编译或运行问题。需要隔离预览时，可在 effect/ 中创建 preview.tscn 并指定 scene="effect/preview.tscn"。

根据实现需要自行调用 read、write 和 render，调用顺序及是否渲染由你决定。完成后简要说明修改了哪些文件和实现了什么效果。
