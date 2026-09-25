# 命中事件、移动受体与遮挡

在当前 Godot 实验中实现以下效果。继续修改 effect/ 中上一阶段保留的实现。

## 测试环境

保留 TargetA、TargetB、Cover、地面与射击控制，观察移动受体、命中、遮挡和寿命。

复用现有 Godot 宿主。scene/main.tscn 为本层入口，scene/project/ 可读取原工程，scene/environment.json 说明本层范围。effect/main.gd 是效果入口：configure 接收原场景和固定输入，step 推进效果，sample 返回下述数值输出；可在 effect/ 中添加所需 shader 和辅助文件。

## 使用的算法

投影贴花，组合局部命中锚点变换、当前深度遮挡及单贴花生命周期。

## 固定测试输入

本次输入固定如下，inputs/test_input.json 保存同一份数据。

```json
{
  "dt_seconds": 0.016666666666666666,
  "steps": 180,
  "record_after_steps": [1, 30, 60, 180],
  "viewport": [128, 128],
  "camera": {"eye": [0, 0, 4], "target": [0, 0, 0], "up": [0, 1, 0], "fov_degrees": 60, "near": 0.1, "far": 20},
  "surface": {
    "vertices": [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]],
    "triangles": [[0, 1, 2], [0, 2, 3]],
    "albedo_linear": [0.5, 0.5, 0.5]
  },
  "projector": {
    "origin": [0, 0, 0],
    "rotation_degrees": [0, 0, 0],
    "scale": [0.5, 0.5, 0.2],
    "cos_reject": 0.2,
    "cos_full": 0.8,
    "albedo_linear": [0.15, 0.03, 0.01],
    "opacity": 0.8
  },
  "hit": {"event_id": 1, "target": "target_a", "time_s": 0, "local_position": [0, 0, 0], "local_normal": [0, 0, 1]},
  "lifetime_s": 2,
  "allowed_targets": ["target_a", "target_b"],
  "target_motion": {"translation_m_s": [0.1, 0, 0], "yaw_degrees_s": 15}
}
```

世界坐标 Y 向上，角度为度，长度为米；投影盒局部范围为 [-0.5,0.5]³，UV=local.xy+0.5。深度采用近端 1、远端 0 的 reverse-Z。朝向阈值之间平滑过渡。初始事件在首次步进前注入；同时只保留一个贴花，寿命按显式时间计算。场景阶段同名逻辑目标由当前场景绑定；命中位置/法线为目标局部坐标。

## 输出要求

将实现保存到 effect/。运行输出采用以下字段和顺序；render 将 sample 返回的数据保存到 observations/ 下的 samples.json：

- `samples`：按 record_after_steps 输出；每项含 step、elapsed_s、active_target 和逐像素数据。
- `pixel_data`：按 128×128 行优先输出 visible、world_position、projector_local_position、uv、opacity、normal、albedo_linear。
- `background`：visible=false 时位置/UV/法线填 null，opacity 为 0。
- `active_target`：有效期内为目标名，到期后为 null；到期后材质恢复当前受体的原值。

## 需要生成的效果

贴花出现在实际命中的局部位置，目标运动时随目标移动；前景会遮住贴花。新命中替换旧贴花，重复事件不延长寿命，到期恢复原材质。

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
