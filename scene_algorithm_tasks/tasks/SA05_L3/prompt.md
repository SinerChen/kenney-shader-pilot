# 晨雾的完整覆盖与景观可读性

在当前 Godot 实验中实现以下效果。继续修改 effect/ 中上一阶段保留的实现。

## 测试环境

使用原完整森林，保留全部地形、树木、岩石、Groundcover、天空、云和自由相机。

复用现有 Godot 宿主。scene/main.tscn 为本层入口，scene/project/ 可读取原工程，scene/environment.json 说明本层范围。effect/main.gd 是效果入口：configure 接收原场景和固定输入，step 推进效果，sample 返回下述数值输出；可在 effect/ 中添加所需 shader 和辅助文件。

## 使用的算法

指数高度雾与按可见表面应用的场景合成，保留天空及 UI 路径。

## 固定测试输入

本次输入固定如下，inputs/test_input.json 保存同一份数据。

```json
{
  "reference_height_m": 0,
  "density_per_m": 0.01,
  "height_falloff_per_m": 0.15,
  "fog_color_linear": [0.65, 0.72, 0.78],
  "rays": [
    {"start": [0, 0, 0], "end": [10, 0, 0], "background_linear": [0.2, 0.4, 0.1]},
    {"start": [0, 0, 0], "end": [8, 6, 0], "background_linear": [0.2, 0.4, 0.1]},
    {"start": [0, 6, 0], "end": [8, 0, 0], "background_linear": [0.2, 0.4, 0.1]}
  ],
  "camera": "forest_overview",
  "preserve_sky": true,
  "preserve_ui": true,
  "scene_density_reference": "initial_camera_world_y"
}
```

Y 向上，距离为米，密度为每米，所有颜色在线性空间。密度随世界高度按指数下降：rho(y)=density×exp(−height_falloff×(y−reference_height))。积分使用完整起终点间的有限线段，输出透射率与合成颜色。场景阶段每个有效像素的端点来自当前相机与最近可见表面。

## 输出要求

将实现保存到 effect/。运行输出采用以下字段和顺序；render 将 sample 返回的数据保存到 observations/ 下的 samples.json：

- `rays`：按输入射线顺序输出 optical_depth、transmittance、opacity、color_linear。
- `optical_depth`：沿有限线段积分得到的非负光学厚度。
- `transmittance_opacity`：分别为 [0,1] 的透射率和不透明度，两者之和为 1。
- `color_linear`：透射率×原颜色 + 不透明度×雾颜色的 RGB。

## 需要生成的效果

雾覆盖地形、树干、岩石、草和蕨叶，形成完整森林的远近与高低层次。近景地面边界和关键景物仍可辨识，原天空、云、植被分布和自由相机功能保留。

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
