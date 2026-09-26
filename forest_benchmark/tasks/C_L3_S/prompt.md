## 1. 效果与算法

效果：完整森林的原天空云、地面云影和薄雾明暗在空间与时间上保持一致，云移动时下方遮光和雾中光照同步变化。

算法：原天空云密度采样、世界空间云遮光、单次散射、Henyey–Greenstein 相函数、深度截断。

## 2. 输入输出类型

以下输入输出约定用于后续的算法函数测试。测试程序将按这些接口和类型传入数据、调用算法函数，并读取返回结果进行验证。

输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。

查询输出类型：`Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}`，或 `Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。

标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。

| 查询 | 输入字段与类型 | 输出字段与类型 |
| --- | --- | --- |
| `cloud_query` | `cloud_world_to_local: Matrix4`；`cloud_min: Vector3`；`cloud_max: Vector3`；`density_size: Vector3i`；`density: float[Nz,Ny,Nx]`；`cloud_sigma: float`；`cloud_steps: int`；`light_dir: Vector3`；`points: Vector3[N]` | `valid_interval: bool`；`s0: float`；`s1: float`；`optical_depth: float`；`transmittance: float` |
| `fog_query` | `cloud_world_to_local: Matrix4`；`cloud_min: Vector3`；`cloud_max: Vector3`；`density_size: Vector3i`；`density: float[Nz,Ny,Nx]`；`cloud_sigma: float`；`cloud_steps: int`；`light_dir: Vector3`；`view_rays: Tuple[ox:float,oy:float,oz:float,dx:float,dy:float,dz:float,opaque_distance:float][N]`；`light_rgb: Vector3`；`fog_min: Vector3`；`fog_max: Vector3`；`fog_density: float`；`fog_scatter: float`；`fog_absorb: float`；`g: float`；`view_steps: int` | `phase: float`；`L_scatter: Vector3`；`T_view: float`；`T_cloud_at_samples: float[Nv]`；`T_fog_light: float[Nv]` |

场景输入类型：`world_points: Vector3[N]`；`source_transform: Matrix4`；`source_time: float`；`source_tick: int`；`camera: Camera3D`。

场景输出类型：`native_cloud_samples: GPUField`；`rho_grid: GPUField`；`source_tick: int`；`source_time: float`；`source_version: String`。

## 可观察和修改的目录

当前实验根目录：`D:/shaderagent17_s0_s1/kenney_shader_pilot/forest_benchmark/tasks/C_L3_S`。

所有路径相对于当前实验根目录。

| 目录 / 文件 | 内容 |
|---|---|

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
