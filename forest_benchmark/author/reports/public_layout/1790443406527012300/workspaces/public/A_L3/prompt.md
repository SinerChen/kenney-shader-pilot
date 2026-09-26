## 1. 效果与算法

效果：完整森林中的目标树呈现灼烧与余烬，近远景表示的灼烧阶段一致，多棵树状态独立；原有植被风动和非目标树外观保持正常。

算法：三维梯度噪声与 fBM 灼烧、Curl Noise、RK2 粒子运动、多实例与跨 LOD 状态一致性。

## 2. 输入输出类型

输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。

查询输出类型：`Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}`，或 `Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。

标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。

| 查询 | 输入字段与类型 | 输出字段与类型 |
| --- | --- | --- |
| `burn_query` | `P: Array[int]`；`points: Vector3[N]`；`time: float`；`t0: float`；`origin_ref: Vector3`；`R0: float`；`speed: float`；`noise_amplitude: float`；`base_frequency: float`；`octaves: int`；`gain: float`；`lacunarity: float`；`width: float`；`enabled: bool` | `noise: float`；`signed_front: float`；`char_fraction: float`；`front_strength: float` |
| `curl_query` | `P: Array[int]`；`frequency: float`；`epsilon: float`；`drift: Vector3`；`offsets: Array[Vector3]`；`up_speed: float`；`curl_strength: float`；`points: Vector3[N]`；`time: float` | `curl: Vector3`；`velocity: Vector3` |
| `particle_step` | `P: Array[int]`；`frequency: float`；`epsilon: float`；`drift: Vector3`；`offsets: Array[Vector3]`；`up_speed: float`；`curl_strength: float`；`particles: Tuple[x:float,y:float,z:float,age:float][N]`；`time: float`；`dt: float`；`lifetime: float` | `next_position: Vector3`；`age: float`；`active: bool`；`cooling: float` |

场景输入类型：`object_id: String`；`points_ref: Vector3[N]`；`time: float`；`instance_transform: Matrix4`；`anchors: Tuple[position:Vector3,normal:Vector3][N]`。

场景输出类型：`burn_state: Dictionary[String,GPUField]`；`emitter_history: Array[Dictionary{object_id:String,anchor_id:int,birth_time:float}]`；`particle_state: Dictionary[String,GPUField]`；`display_resources: Dictionary[String,Resource]`。

## 3. 当前任务工作目录

`D:/shaderagent17_s0_s1/kenney_shader_pilot/forest_benchmark/author/reports/public_layout/1790443406527012300/workspaces/A_L3`

```text
./
├── assets/
│   ├── task_inputs/
│   │   └── A_L3/
│   │       ├── emitter_anchors.bin
│   │       ├── tree_1_anchors.bin
│   │       └── tree_2_anchors.bin
│   ├── emitter_anchors.bin
│   ├── metadata.json
│   ├── noise_permutation.json
│   └── wood_base.png
├── fixture/
│   ├── adapter_base.gd
│   ├── entry.gd
│   ├── entry.tscn
│   └── scene_access.gd
├── Groundcover/
│   ├── Forest plants test.tres
│   ├── Forest plants.tres
│   └── Groundcover.txt
├── Materials/
│   ├── dry_branches_medium_01.tres
│   ├── fern_02.tres
│   ├── River.tres
│   ├── rock_moss_set_01.tres
│   ├── rock_moss_set_02.tres
│   ├── Terrain 1.tres
│   ├── Terrain 2.tres
│   ├── Tree bark.tres
│   ├── Tree branch LOD.tres
│   ├── Tree branch.tres
│   └── Tree LOD.tres
├── Meshes/
│   ├── Plants/
│   │   ├── fern_02_a.glb
│   │   ├── fern_02_a.glb.import
│   │   ├── fern_02_b.glb
│   │   ├── fern_02_b.glb.import
│   │   ├── fern_02_c.glb
│   │   ├── fern_02_c.glb.import
│   │   ├── fern_02_d.glb
│   │   ├── fern_02_d.glb.import
│   │   ├── Grass1.glb
│   │   ├── Grass1.glb.import
│   │   ├── Grass2.glb
│   │   ├── Grass2.glb.import
│   │   ├── Grass3.glb
│   │   ├── Grass3.glb.import
│   │   ├── Grass4.glb
│   │   ├── Grass4.glb.import
│   │   ├── Grass5.glb
│   │   ├── Grass5.glb.import
│   │   ├── Grass6.glb
│   │   ├── Grass6.glb.import
│   │   ├── Grass7.glb
│   │   ├── Grass7.glb.import
│   │   ├── Grass8.glb
│   │   └── Grass8.glb.import
│   ├── Rocks/
│   │   ├── rock_moss_set_01_rock01.glb
│   │   ├── rock_moss_set_01_rock01.glb.import
│   │   ├── rock_moss_set_01_rock02.glb
│   │   ├── rock_moss_set_01_rock02.glb.import
│   │   ├── rock_moss_set_01_rock03.glb
│   │   ├── rock_moss_set_01_rock03.glb.import
│   │   ├── rock_moss_set_01_rock04.glb
│   │   ├── rock_moss_set_01_rock04.glb.import
│   │   ├── rock_moss_set_01_rock05.glb
│   │   ├── rock_moss_set_01_rock05.glb.import
│   │   ├── rock_moss_set_01_rock06.glb
│   │   ├── rock_moss_set_01_rock06.glb.import
│   │   ├── rock_moss_set_02_rock07.glb
│   │   ├── rock_moss_set_02_rock07.glb.import
│   │   ├── rock_moss_set_02_rock08.glb
│   │   ├── rock_moss_set_02_rock08.glb.import
│   │   ├── rock_moss_set_02_rock09.glb
│   │   ├── rock_moss_set_02_rock09.glb.import
│   │   ├── rock_moss_set_02_rock10.glb
│   │   ├── rock_moss_set_02_rock10.glb.import
│   │   ├── rock_moss_set_02_rock11.glb
│   │   ├── rock_moss_set_02_rock11.glb.import
│   │   ├── rock_moss_set_02_rock12.glb
│   │   ├── rock_moss_set_02_rock12.glb.import
│   │   ├── rock_moss_set_02_rock13.glb
│   │   └── rock_moss_set_02_rock13.glb.import
│   ├── Trees/
│   │   ├── dry_branches_medium_01_a.glb
│   │   ├── dry_branches_medium_01_a.glb.import
│   │   ├── dry_branches_medium_01_b.glb
│   │   ├── dry_branches_medium_01_b.glb.import
│   │   ├── dry_branches_medium_01_c.glb
│   │   ├── dry_branches_medium_01_c.glb.import
│   │   ├── Tree big 1.glb
│   │   ├── Tree big 1.glb.import
│   │   ├── Tree_big_2.glb
│   │   ├── Tree_big_2.glb.import
│   │   ├── Tree_med_1.glb
│   │   ├── Tree_med_1.glb.import
│   │   ├── Tree_med_2.glb
│   │   ├── Tree_med_2.glb.import
│   │   ├── Tree_small_1.glb
│   │   ├── Tree_small_1.glb.import
│   │   ├── Tree_small_2.glb
│   │   ├── Tree_small_2.glb.import
│   │   ├── Tree_tall_1.glb
│   │   ├── Tree_tall_1.glb.import
│   │   ├── Tree_tall_2.glb
│   │   └── Tree_tall_2.glb.import
│   ├── Main Terrain.glb
│   └── Main Terrain.glb.import
├── scratch/
├── Scripts/
│   └── Import/
│       └── Tree_LOD.gd
├── Shaders/
│   ├── Sky/
│   │   ├── perlworlnoise.tga
│   │   ├── perlworlnoise.tga.import
│   │   ├── sky volumetric clouds.gdshader
│   │   ├── weather.bmp
│   │   ├── weather.bmp.import
│   │   ├── worlnoise.bmp
│   │   └── worlnoise.bmp.import
│   ├── Blend4 vcol.gdshader
│   ├── Blend8 splat.gdshader
│   ├── Plant.gdshader
│   └── River.tres
├── solution/
│   ├── adapter.gd
│   ├── defaults.json
│   ├── display.gd
│   ├── effect.tscn
│   ├── kernel.txt
│   └── wire.json
├── Textures/
│   ├── Plants/
│   │   ├── fern_02_diff_4k.png
│   │   ├── fern_02_diff_4k.png.import
│   │   ├── fern_02_nor_gl_4k.png
│   │   ├── fern_02_nor_gl_4k.png.import
│   │   ├── fern_02_rough_4k.png
│   │   ├── fern_02_rough_4k.png.import
│   │   ├── Grass_BaseColor.png
│   │   ├── Grass_BaseColor.png.import
│   │   ├── Grass_Dry_BaseColor.png
│   │   ├── Grass_Dry_BaseColor.png.import
│   │   ├── Grass_Normal.png
│   │   ├── Grass_Normal.png.import
│   │   ├── Grass_ORM.png
│   │   └── Grass_ORM.png.import
│   ├── Rocks/
│   │   ├── rock_moss_set_01_diff_4k.jpg
│   │   ├── rock_moss_set_01_diff_4k.jpg.import
│   │   ├── rock_moss_set_01_nor_gl_4k.jpg
│   │   ├── rock_moss_set_01_nor_gl_4k.jpg.import
│   │   ├── rock_moss_set_01_nor_gl_4k.png.import
│   │   ├── rock_moss_set_01_rough_4k.jpg
│   │   ├── rock_moss_set_01_rough_4k.jpg.import
│   │   ├── rock_moss_set_02_diff_4k.jpg
│   │   ├── rock_moss_set_02_diff_4k.jpg.import
│   │   ├── rock_moss_set_02_nor_gl_4k.jpg
│   │   ├── rock_moss_set_02_nor_gl_4k.jpg.import
│   │   ├── rock_moss_set_02_nor_gl_4k.png.import
│   │   ├── rock_moss_set_02_rough_4k.jpg
│   │   └── rock_moss_set_02_rough_4k.jpg.import
│   ├── Terrain/
│   │   ├── terrain1_color.jpg
│   │   ├── terrain1_color.jpg.import
│   │   ├── terrain1_normal.jpg
│   │   ├── terrain1_normal.jpg.import
│   │   ├── terrain1_ormh.png
│   │   ├── terrain1_ormh.png.import
│   │   ├── terrain2_color.jpg
│   │   ├── terrain2_color.jpg.import
│   │   ├── terrain2_normal.jpg
│   │   ├── terrain2_normal.jpg.import
│   │   ├── terrain2_ormh.png
│   │   └── terrain2_ormh.png.import
│   ├── Trees/
│   │   ├── bark_brown_01_arm_4k.jpg
│   │   ├── bark_brown_01_arm_4k.jpg.import
│   │   ├── bark_brown_01_diff_4k.jpg
│   │   ├── bark_brown_01_diff_4k.jpg.import
│   │   ├── bark_brown_01_nor_gl_4k.png
│   │   ├── bark_brown_01_nor_gl_4k.png.import
│   │   ├── bark_brown_02_arm_4k.jpg
│   │   ├── bark_brown_02_arm_4k.jpg.import
│   │   ├── bark_brown_02_diff_4k.jpg
│   │   ├── bark_brown_02_diff_4k.jpg.import
│   │   ├── bark_brown_02_nor_gl_4k.png
│   │   ├── bark_brown_02_nor_gl_4k.png.import
│   │   ├── dry_branches_medium_01_arm_4k.jpg
│   │   ├── dry_branches_medium_01_arm_4k.jpg.import
│   │   ├── dry_branches_medium_01_diff_4k.jpg
│   │   ├── dry_branches_medium_01_diff_4k.jpg.import
│   │   ├── dry_branches_medium_01_nor_gl_4k.png
│   │   ├── dry_branches_medium_01_nor_gl_4k.png.import
│   │   ├── Tree_Branch_BaseColor.png
│   │   ├── Tree_Branch_BaseColor.png.import
│   │   ├── Tree_Branch_LOD_BaseColor.png
│   │   ├── Tree_Branch_LOD_BaseColor.png.import
│   │   ├── Tree_Branch_LOD_Normal.png
│   │   ├── Tree_Branch_LOD_Normal.png.import
│   │   ├── Tree_Branch_LOD_orm.png
│   │   ├── Tree_Branch_LOD_orm.png.import
│   │   ├── Tree_Branch_Normal.png
│   │   ├── Tree_Branch_Normal.png.import
│   │   ├── Tree_Branch_orm.png
│   │   ├── Tree_Branch_orm.png.import
│   │   ├── Tree_LOD_BaseColor.png
│   │   ├── Tree_LOD_BaseColor.png.import
│   │   ├── Tree_LOD_Normal.png
│   │   ├── Tree_LOD_Normal.png.import
│   │   ├── Tree_LOD_orm.png
│   │   └── Tree_LOD_orm.png.import
│   ├── Splat map 1.png
│   ├── Splat map 1.png.import
│   ├── Splat map 2.png
│   └── Splat map 2.png.import
├── Main.tscn
└── project.godot
```

## 4. 可用工具

- `read`：读取文件或列出目录。
- `write`：写入文件。
- `render`：渲染图像或视频，可设置观察位置、朝向、帧数和分辨率。
