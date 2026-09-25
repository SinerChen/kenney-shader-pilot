# 湿路面的作用边界与街道用途

在当前 Godot 实验中实现以下效果。继续修改 effect/ 中上一阶段保留的实现。

## 测试环境

使用原完整 Bistro 街景，保留各街区、室内入口、道具、碰撞、日夜控制和相机。

复用现有 Godot 宿主。scene/main.tscn 为本层入口，scene/project/ 可读取原工程，scene/environment.json 说明本层范围。effect/main.gd 是效果入口：configure 接收原场景和固定输入，step 推进效果，sample 返回下述数值输出；可在 effect/ 中添加所需 shader 和辅助文件。

## 使用的算法

四层高度材质混合、RNM，以及按表面和区域遮罩限定的湿润材质绑定。

## 固定测试输入

本次输入固定如下，inputs/test_input.json 保存同一份数据。

```json
{
  "transition": 0.25,
  "wetness": 0.6,
  "layers": [
    {
      "height": 0.8,
      "control": 0.4,
      "albedo_linear": [0.45, 0.42, 0.38],
      "roughness": 0.8,
      "metallic": 0,
      "normal_ts": [0, 0, 1]
    },
    {
      "height": 0.8,
      "control": 0.6,
      "albedo_linear": [0.25, 0.23, 0.21],
      "roughness": 0.25,
      "metallic": 0,
      "normal_ts": [0, 0, 1]
    },
    {
      "height": 0.2,
      "control": 0.2,
      "albedo_linear": [0.12, 0.09, 0.06],
      "roughness": 0.6,
      "metallic": 0,
      "normal_ts": [0, 0, 1]
    },
    {
      "height": 0,
      "control": 0,
      "albedo_linear": [0, 0, 0],
      "roughness": 0.5,
      "metallic": 0,
      "normal_ts": [0, 0, 1]
    }
  ],
  "detail_normal_ts": [0.3, 0, 0.9539392014169457],
  "detail_enabled": true,
  "eligible_region": "outdoor_road_wet",
  "camera": "road_close"
}
```

四层依次表示干石材、湿石材、缝隙泥层、备用层；高度采用同一单位，颜色在线性空间。输入 control 已包含 wetness 的分配，不能再次乘 wetness。先比较各层 height×control 得到共同最高值，再按 transition 建立非负竞争量并归一化；竞争量在乘 control 前加 1e-6，transition 下限为 1e-5，归一化分母下限为 1e-6。场景应用时从当前场景的固定高度图和区域遮罩取得逐点输入。

## 输出要求

将实现保存到 effect/。运行输出采用以下字段和顺序；render 将 sample 返回的数据保存到 observations/ 下的 samples.json：

- `weights`：按四层原顺序输出四个浮点权重。
- `albedo_linear`：同一组权重混合得到的线性 RGB。
- `roughness_metallic_height`：分别输出 roughness、metallic、height 三个浮点字段。
- `base_normal_ts`：混合后归一化的切线空间法线；相消时为 [0,0,1]。
- `final_normal_ts`：细节关闭时等于 base_normal_ts；开启时为 RNM 组合后的单位法线。

## 需要生成的效果

只湿润指定室外石路区域，完整覆盖其目标表面。干燥路脊、门口、人行区、室内地面、桌椅、招牌、玻璃和角色保留原材质与功能；街道入口与通行边界仍清晰可辨。

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
