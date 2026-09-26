## 1. 效果与算法

效果：保留木质物体的灼烧效果，余烬从活动前沿出现，向上漂移并形成旋涡，随时间冷却消失。

算法：三维梯度噪声与 fBM 灼烧、Curl Noise、RK2 粒子运动、粒子生命周期。

## 2. 输入输出类型

以下输入输出约定用于后续的算法函数测试。测试程序将按这些接口和类型传入数据、调用算法函数，并读取返回结果进行验证。

输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。

查询输出类型：`Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}`，或 `Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。

标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。

| 查询 | 输入字段与类型 | 输出字段与类型 |
| --- | --- | --- |
| `burn_query` | `P: Array[int]`；`points: Vector3[N]`；`time: float`；`t0: float`；`origin_ref: Vector3`；`R0: float`；`speed: float`；`noise_amplitude: float`；`base_frequency: float`；`octaves: int`；`gain: float`；`lacunarity: float`；`width: float`；`enabled: bool` | `noise: float`；`signed_front: float`；`char_fraction: float`；`front_strength: float` |
| `curl_query` | `P: Array[int]`；`frequency: float`；`epsilon: float`；`drift: Vector3`；`offsets: Array[Vector3]`；`up_speed: float`；`curl_strength: float`；`points: Vector3[N]`；`time: float` | `curl: Vector3`；`velocity: Vector3` |
| `particle_step` | `P: Array[int]`；`frequency: float`；`epsilon: float`；`drift: Vector3`；`offsets: Array[Vector3]`；`up_speed: float`；`curl_strength: float`；`particles: Tuple[x:float,y:float,z:float,age:float][N]`；`time: float`；`dt: float`；`lifetime: float` | `next_position: Vector3`；`age: float`；`active: bool`；`cooling: float` |

## 可观察和修改的目录

当前实验根目录：`D:/shaderagent17_s0_s1/kenney_shader_pilot/forest_benchmark/exports/1790412198137779500/A_L2`。

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
