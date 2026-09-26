## 1. 效果与算法

效果：完整森林的原河流出现交互涟漪，波纹改变河流折射，前景透明层同步呈现当前水面变化，原河流细节和层间遮挡保持正常。

算法：二维阻尼波动方程、原河流法线与波面法线合成、Snell 折射、Fresnel 反射、Beer–Lambert 吸收、多层折射。

## 2. 输入输出类型

以下输入输出约定用于后续的算法函数测试。测试程序将按这些接口和类型传入数据、调用算法函数，并读取返回结果进行验证。

输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。

查询输出类型：`Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}`，或 `Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。

标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。

| 查询 | 输入字段与类型 | 输出字段与类型 |
| --- | --- | --- |
| `optics_query` | `optical_rays: Tuple[Ix:float,Iy:float,Iz:float,Nx:float,Ny:float,Nz:float,x:float,y:float,z:float][N]`；`eta_i: float`；`eta_t: float`；`ell: float`；`sigma_a: Vector3`；`view_projection: Matrix4`；`texture_size: Vector2i`；`color_texture: Vector3[H,W]`；`reflection_color: Vector3`；`fallback_color: Vector3` | `F: float`；`Tdir: Vector3`；`R: Vector3`；`A: Vector3`；`has_transmission: bool`；`background_uv: Vector2`；`valid: bool`；`color: Vector3` |
| `wave_step` | `grid_size: Vector2i`；`domain_min: Vector2`；`domain_size: Vector2`；`height: float[Nz,Nx]`；`height_prev: float[Nz,Nx]`；`force: float[Nz,Nx]`；`dt: float`；`wave_speed: float`；`gamma: float` | `height: float` |
| `wave_normal_query` | `grid_size: Vector2i`；`domain_min: Vector2`；`domain_size: Vector2`；`height: float[Nz,Nx]` | `normal: Vector3` |

场景输入类型：`surface_transform: Matrix4`；`base_normal: Texture2D`；`wave_events: Array[Dictionary]`；`front_background: Texture2D`；`water_background: Texture2D`；`camera: Camera3D`；`tick: int`。

场景输出类型：`wave_height: GPUField`；`wave_normal: GPUField`；`composed_normal: GPUField`；`front_input: Texture2D`；`water_input: Texture2D`；`capture_tick: int`；`capture_camera: Dictionary`。

## 可观察和修改的目录

当前实验根目录：`D:/shaderagent17_s0_s1/kenney_shader_pilot/forest_benchmark/exports/20260926T102550Z/E_L3`。

所有路径相对于当前实验根目录。

| 目录 / 文件 | 内容 |
|---|---|
| project.godot | 当前 Godot 工程配置 |
| Main.tscn | 完整森林场景 |
| fixture/ | 当前实验场景入口与固定宿主文件 |
| assets/ | 当前任务使用的纹理、采样数据与输入资源 |
| Materials/ | 原场景材质资源 |
| Meshes/ | 原场景模型与网格资源 |
| Shaders/ | 原场景着色器与相关资源 |
| Scripts/ | 原场景脚本 |
| Textures/ | 原场景纹理 |
| Groundcover/ | 原场景地表植被资源 |
| solution/ | 本次需要实现或修改的效果文件 |
| scratch/ | 临时脚本、调试材料与中间文件 |

## 工具

- `read(path, start_line=1, line_count=200)`：读取文本文件或列出目录。
- `write(path, content)`：在 solution/ 或 scratch/ 内创建或覆盖文件，content 为完整文本。
- `render(camera=..., frames=..., resolution=...)`：运行当前实现并获取渲染结果，可请求视频。

## 自主渲染观察

你可以自行选择观察位置、角度、距离、连续渲染帧数和图像分辨率。render 的相机参数仅用于本次观察，不改写场景相机或输入配置文件。

例如，从自选位置连续观察 120 帧：

```json
{"camera":{"position":[6,4,8],"look_at":[0,0,0]},"frames":120,"resolution":[960,640]}
```

camera.position 和 look_at 使用世界坐标，分别表示相机位置与观察目标。省略 camera 时使用场景相机。frames 为连续渲染帧数，使用 1–180 的整数；resolution 为 [宽,高]。

每次 render 从当前文件的新场景实例开始。可以从不同位置重复观察效果，结合渲染结果和日志定位编译或运行问题。

根据实现需要自行调用 read、write 和 render，调用顺序及是否渲染由你决定。完成后简要说明修改了哪些文件和实现了什么效果。
