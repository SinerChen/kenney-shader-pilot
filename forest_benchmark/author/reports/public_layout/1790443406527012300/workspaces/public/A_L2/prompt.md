## 1. 效果与算法

效果：保留木质物体的灼烧效果，余烬从活动前沿出现，向上漂移并形成旋涡，随时间冷却消失。

算法：三维梯度噪声与 fBM 灼烧、Curl Noise、RK2 粒子运动、粒子生命周期。

## 2. 输入输出类型

输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。

查询输出类型：`Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}`，或 `Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。

标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。

| 查询 | 输入字段与类型 | 输出字段与类型 |
| --- | --- | --- |
| `burn_query` | `P: Array[int]`；`points: Vector3[N]`；`time: float`；`t0: float`；`origin_ref: Vector3`；`R0: float`；`speed: float`；`noise_amplitude: float`；`base_frequency: float`；`octaves: int`；`gain: float`；`lacunarity: float`；`width: float`；`enabled: bool` | `noise: float`；`signed_front: float`；`char_fraction: float`；`front_strength: float` |
| `curl_query` | `P: Array[int]`；`frequency: float`；`epsilon: float`；`drift: Vector3`；`offsets: Array[Vector3]`；`up_speed: float`；`curl_strength: float`；`points: Vector3[N]`；`time: float` | `curl: Vector3`；`velocity: Vector3` |
| `particle_step` | `P: Array[int]`；`frequency: float`；`epsilon: float`；`drift: Vector3`；`offsets: Array[Vector3]`；`up_speed: float`；`curl_strength: float`；`particles: Tuple[x:float,y:float,z:float,age:float][N]`；`time: float`；`dt: float`；`lifetime: float` | `next_position: Vector3`；`age: float`；`active: bool`；`cooling: float` |

## 3. 当前任务工作目录

`D:/shaderagent17_s0_s1/kenney_shader_pilot/forest_benchmark/author/reports/public_layout/1790443406527012300/workspaces/A_L2`

```text
./
├── assets/
│   ├── emitter_anchors.bin
│   ├── metadata.json
│   ├── noise_permutation.json
│   └── wood_base.png
├── fixture/
│   ├── adapter_base.gd
│   ├── base_stage.tscn
│   ├── bridge.gd
│   └── entry.tscn
├── scratch/
├── solution/
│   ├── adapter.gd
│   └── effect.tscn
└── project.godot
```

## 4. 可用工具

- `read`：读取文件或列出目录。
- `write`：写入文件。
- `render`：渲染图像或视频，可设置观察位置、朝向、帧数和分辨率。
