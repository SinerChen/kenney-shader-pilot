# 波面压缩驱动泡沫历史

在当前 Godot 实验中实现以下效果。继续修改 effect/ 中上一阶段保留的实现。

## 测试环境

保留中心及相邻 LOD 网格、海床，观察波面与泡沫的时空关系；隐藏无关展示物。

复用现有 Godot 宿主。scene/main.tscn 为本层入口，scene/project/ 可读取原工程，scene/environment.json 说明本层范围。effect/main.gd 是效果入口：configure 接收原场景和固定输入，step 推进效果，sample 返回下述数值输出；可在 effect/ 中添加所需 shader 和辅助文件。

## 使用的算法

Gerstner 波、水平位移 Jacobian 压缩检测、参数附着的泡沫增长与指数衰减。

## 固定测试输入

本次输入固定如下，inputs/test_input.json 保存同一份数据。

```json
{
  "dt_seconds": 0.016666666666666666,
  "steps": 180,
  "record_after_steps": [1, 60, 120, 180],
  "grid": {"size": [64, 64], "length_xz_m": [8, 8], "origin_xz_m": [0, 0]},
  "waves": [
    {
      "amplitude_m": 0.2,
      "wavelength_m": 4,
      "speed_m_s": 1,
      "direction_xz": [1, 0],
      "phase_rad": 0,
      "steepness": 0.4
    },
    {
      "amplitude_m": 0.1,
      "wavelength_m": 8,
      "speed_m_s": 0.5,
      "direction_xz": [0, 1],
      "phase_rad": 0.5,
      "steepness": 0.3
    }
  ],
  "foam": {"enabled": true, "threshold": 1, "grow_per_s": 1, "decay_per_s": 1, "initial_value": 0},
  "camera": "overview"
}
```

Y 向上，XZ 网格为周期参数域；q=(列号×8/64,行号×8/64)，从 0 编号。波相位取 k·(方向·q−速度·时间)+初相位，k=2π/波长。初始时间为 0，每步只推进一次。泡沫开启时，以周期中央差分求水平位移 Jacobian，源项为 max(threshold−J,0)，先指数衰减旧值再加入 grow×dt×源项，结果限制在 [0,1]；泡沫始终附着于同一 q 的变形位置。

## 输出要求

将实现保存到 effect/。运行输出采用以下字段和顺序；render 将 sample 返回的数据保存到 observations/ 下的 samples.json：

- `samples`：按 record_after_steps 输出；每项含 step、elapsed_s、positions、normals、jacobian、foam。
- `positions`：64×64 行优先的波面世界位置 [x,y,z]。
- `normals`：同顺序的单位世界法线 [x,y,z]。
- `jacobian`：同顺序的水平位移映射行列式，每点一个浮点数。
- `foam`：同顺序的泡沫覆盖度，每点 [0,1]；泡沫关闭时全零。

## 需要生成的效果

波面发生水平压缩的位置生成泡沫，已有泡沫逐渐衰减并随对应波面位置运动。泡沫与波浪共享时间和坐标。

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
