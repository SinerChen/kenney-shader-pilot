## 1. 效果与算法

效果：地面云影与薄雾明暗随同一云场变化，雾中可见体积光，前景物体具有正确的遮挡关系。

算法：云光学深度、均匀薄雾单次散射、Henyey–Greenstein 相函数、视线积分与深度截断。

## 2. 输入输出类型

以下输入输出约定用于后续的算法函数测试。测试程序将按这些接口和类型传入数据、调用算法函数，并读取返回结果进行验证。

输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。

查询输出类型：`Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}`，或 `Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。

标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。

| 查询 | 输入字段与类型 | 输出字段与类型 |
| --- | --- | --- |
| `cloud_query` | `cloud_world_to_local: Matrix4`；`cloud_min: Vector3`；`cloud_max: Vector3`；`density_size: Vector3i`；`density: float[Nz,Ny,Nx]`；`cloud_sigma: float`；`cloud_steps: int`；`light_dir: Vector3`；`points: Vector3[N]` | `valid_interval: bool`；`s0: float`；`s1: float`；`optical_depth: float`；`transmittance: float` |
| `fog_query` | `cloud_world_to_local: Matrix4`；`cloud_min: Vector3`；`cloud_max: Vector3`；`density_size: Vector3i`；`density: float[Nz,Ny,Nx]`；`cloud_sigma: float`；`cloud_steps: int`；`light_dir: Vector3`；`view_rays: Tuple[ox:float,oy:float,oz:float,dx:float,dy:float,dz:float,opaque_distance:float][N]`；`light_rgb: Vector3`；`fog_min: Vector3`；`fog_max: Vector3`；`fog_density: float`；`fog_scatter: float`；`fog_absorb: float`；`g: float`；`view_steps: int` | `phase: float`；`L_scatter: Vector3`；`T_view: float`；`T_cloud_at_samples: float[Nv]`；`T_fog_light: float[Nv]` |

## 可观察和修改的目录

当前实验根目录：`D:/shaderagent17_s0_s1/kenney_shader_pilot/forest_benchmark/exports/final_review_1790414793007604600/C_L2`。

所有路径相对于当前实验根目录。

| 目录 / 文件 | 内容 |
|---|---|
| project.godot | 当前 Godot 工程配置 |
| fixture/ | 当前实验场景入口与固定宿主文件 |
| assets/ | 当前任务使用的纹理、采样数据与输入资源 |
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
