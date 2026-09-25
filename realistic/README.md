# Godot 扩展场景库

五个用户指定的场景 / Shader 示例已加入 `D:\shaderagent17_s0_s1\kenney_shader_pilot\realistic`，复用上一级 `tools/godot/` 中的 **Godot 4.6.1 官方便携版**。

[打开场景展示页](http://127.0.0.1:8770/realistic/index.html) · [返回五场景 / 15 任务试点](../README.md) · [下载来源](sources.json) · [场景与检查清单](catalog.json)

这些工程是新增的场景底座，尚未编制新的三级任务，也没有调用模型 API。原有 5 个 Kenney 场景和 15 个任务保留。当前共收录 10 个场景，其中扩展的 5 个各自为独立 Godot 工程。

## 启动

在上一级 `kenney_shader_pilot` 文件夹双击：

| 场景 | 实时运行 | 编辑工程 | 目录 |
| --- | --- | --- | --- |
| Bistro | [Bistro.cmd](../Bistro.cmd) | [Edit_Bistro.cmd](../Edit_Bistro.cmd) | `realistic/projects/bistro/` |
| Sponza | [Sponza.cmd](../Sponza.cmd) | [Edit_Sponza.cmd](../Edit_Sponza.cmd) | `realistic/projects/sponza/` |
| Open Forest Benchmark | [Forest.cmd](../Forest.cmd) | [Edit_Forest.cmd](../Edit_Forest.cmd) | `realistic/projects/forest/` |
| 官方 TPS Demo | [TPS.cmd](../TPS.cmd) | [Edit_TPS.cmd](../Edit_TPS.cmd) | `realistic/projects/tps/` |
| Boujie Water Shader | [Water.cmd](../Water.cmd) | [Edit_Water.cmd](../Edit_Water.cmd) | `realistic/projects/water/` |

也可以在项目管理器中导入上述目录的 `project.godot`。编辑器中 F6 运行当前场景，F5 运行工程，F8 停止。首次打开大型工程需要加载资源；当前已生成本机的导入缓存。

HTML 展示的是本机实际 GPU 渲染的静态截图，点击图片可查看原图。浏览器不会直接执行 `.cmd`；实时动画和交互在 Godot 中查看。截图上的 FPS 受本次检查环境和固定时间步影响，不作为性能测评分数。

## 操作

- Bistro：WASD 移动，Shift 冲刺，空格跳跃，V 第一/第三人称切换，~ 自由穿行，H 切换界面，Esc 释放鼠标。左侧面板调整日夜、画质、渲染分辨率。
- Sponza：欢迎界面选择画质并点击 OK。WASD 移动，空格上升、Shift 下降，右键加速，滚轮调速，Esc 设置，F10 释放鼠标。
- Forest：新增自由观察相机。按住右键转动，WASD 移动，Q/E 下降/上升，Shift 加速，R 恢复初始镜头，Esc 释放鼠标。没有角色碰撞。
- TPS：主菜单点击 Play；WASD 移动，鼠标观察，空格跳跃，右键瞄准后左键射击，Esc 返回菜单，F11 全屏。
- Water：方向键移动，鼠标观察，Enter 或空格捕获/释放鼠标，Tab 隐藏/显示帮助，Page Up / Page Down 调整相机远裁剪距离，Esc 退出。预览截图隐藏帮助界面，正常运行保留原始帮助。

## 兼容性与已知提示

| 场景 | 上游版本标记 | 本地处理与检查结果 |
| --- | --- | --- |
| Bistro | 4.4 | 已导入并完成 120 帧渲染。原项目 FSR2 与 TAA 同时启用，引擎会自动停用重复 TAA。检查退出时仍有 ObjectDB / 4 个资源未释放提示，出现在截图完成之后。首次导入缺少 `Bent_Quad.mtl`，实际街区已显示；没有伪造该材质文件。 |
| Sponza | 4.6 | 首次多线程 EXR 导入进程异常退出，使用单线程资源导入后完成。首次 Collada 导入有 `polygons` 和空节点名称提示。实际运行无错误、无警告，完成 120 帧渲染。 |
| Forest | 4.0 | 上游引用了未随仓库发布的 `addons/groundcover`。解除缺失生成器引用，保留全部 15,869 个节点、3,709 个已生成的 MultiMesh 节点、几何、变换和材质。实际运行无错误，仍有三个旧纹理 UID 回退到真实路径的提示，以及八个旧网格格式自动升级提示。 |
| TPS | 4.7 | 4.6.1 能运行关卡，但原菜单引用了 4.7 新增的 `SCALING_3D_MODE_NEAREST`。本地隐藏该选项并移除两个枚举引用，版本标记调整为 4.6。主菜单及关卡均已分别完成 120 帧实际渲染，运行日志无错误、无警告。首次导入仍有重复动画名、旧门纹理引用和空网格提示。 |

Boujie Water Shader 的上游项目标注 4.1。其 `.gitattributes` 使用 `export-ignore`，所以 ZIP 只包含 `addons/` 和 `example/`；已从同一官方 main 分支补齐 `project.godot`，原配置另存为 `downloads/water-project.godot`。水面 Shader 和示例源码未修改。在 4.6.1 / Forward+ 下完成 120 帧渲染，运行无错误、无警告；首次导入有 `mountains.mtl`、`subdivcube.mtl` 缺失提示，记录保留在 [导入报告](verification/water/import-status.json)。

五个工程的 `override.cfg` 使用单线程导入，并指定本地公开 CA 证书包，适配当前受限环境；没有关闭 TLS 校验。

Forest 的缺失插件不能用于重新生成或编辑草木分布，本地相机只便于观察现有场景。原始 ZIP 完整保存在 `downloads/`；森林和 TPS 的改动记录在各自 `verification/*/adaptation.json`。第一次失败及后续复测日志保存在 `verification/*/history/`，不会把这些错误算作模型错误。

检查覆盖场景加载、实际渲染与基本启动兼容性；TPS 另外检查了从主菜单点击 Play 进入关卡并继续渲染 120 帧，过程无报错。尚未对全部菜单选项、战斗流程或后续 shader 任务评分。

## 文件与复现

- `downloads/`：五个 GitHub 分支 ZIP，合计约 1.70 GiB，另有 Water 的原始项目配置。保留原始归档，不混用模型输出。
- `projects/`：五个可打开的独立工程，附原作者文档、许可证和资产署名。
- `verification/`：每场景第 30 / 120 帧截图、运行和导入日志、兼容性记录；TPS 另有 `menu/` 检查。
- `sources.json`：仓库、分支、下载时间、URL、压缩包字节数。
- `catalog.json`：场景说明、操作、许可摘要与实际检查结果。
- `tools/prepare.py`：森林缺失编辑器插件引用处理、相机安装、TPS 4.6 菜单兼容。

从工作区根目录运行：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\realistic\tools\download.py
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\realistic\tools\prepare.py
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\realistic\tools\check.py forest import
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\realistic\tools\check.py forest capture
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\realistic\tools\build_page.py
```

其他场景用 `bistro`、`sponza`、`tps`、`water` 替换 `forest`。TPS 关卡截图用 `tps capture --scene res://level/level.tscn`，主菜单检查用 `tps capture --label menu`，从菜单点击 Play 的完整启动检查用 `tps capture --label play`。下载器保留已有下载；`prepare.py` 保留现有场景内容，仅做列明的适配。

## 来源与署名

- [Bistro-Demo-Tweaked](https://github.com/Jamsers/Bistro-Demo-Tweaked)：John James Gutib；源于 Logan Preshaw 的 Godot 移植及 Amazon Lumberyard Bistro。代码 MIT，大部分资产 CC BY 4.0，音乐 CC BY 3.0；部分音效为 CC BY-NC 4.0，不能将整个包统一标为 CC0 或无条件商用。完整说明见 [ATTRIBUTION](projects/bistro/ATTRIBUTION)。
- [Godot Sponza](https://github.com/Calinou/godot-sponza)：Hugo Locurcio 与贡献者；代码 MIT；Crytek Sponza 模型按上游说明为 public domain，字体 SIL OFL 1.1。见 [README](projects/sponza/README.md)、[LICENSE](projects/sponza/LICENSE.md)。
- [Open Forest Benchmark](https://github.com/Rytelier/Godot-4-forest-benchmark)：Rytelier；仓库 MIT，模型及贴图引用 Poly Haven、ambientCG 等来源，保留 [Asset Credits.txt](projects/forest/Asset%20Credits.txt)。
- [官方 TPS Demo](https://github.com/godotengine/tps-demo)：Godot Engine 贡献者；资产作者 Juan Linietsky、Fernando Miguel Calabró，音乐 Christian Fernando Perucchi。代码 MIT，资产和音乐 CC BY 3.0，另有 GameTextures.com 派生材质署名。见 [LICENSE.md](projects/tps/LICENSE.md)。
- [Boujie Water Shader](https://github.com/Chrisknyfe/boujie_water_shader)：Zach Bernal 与贡献者，MIT；原始水面 Shader 来自 Tom Langwaldt，其他参考与署名保留在 [插件 README](projects/water/addons/boujie_water_shader/README.md) 和 [LICENSE](projects/water/addons/boujie_water_shader/LICENSE.md)。核心实现为 `projects/water/addons/boujie_water_shader/shader/water.gdshader`，示例为 `example/boujie_water_shader/water_shader_examples.tscn`。
