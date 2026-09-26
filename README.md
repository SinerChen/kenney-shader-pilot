# Kenney Shader Pilot

[Forest Benchmark：题目、现有报告、实验记录及一个完整 L3 工程](forest_benchmark/README.md) · [上传内容说明](forest_benchmark/GITHUB_CONTENTS.md)

[Repository contents and restore instructions](REPOSITORY.md)

新增 [场景算法递进任务包](scene_algorithm_tasks/README.md)：依据已实现算法和现有场景编写 **5 组、15 题**，按“L1 算法正确性 → L2 效果交互 → L3 场景影响与设计作用”划分。模型基础输入为简化题面与 read/write/render 工具；本次串行 S1/P3 另有[系统 prompt 待审阅](scene_algorithm_tasks/experiment/P3.md)。模型可自行设置相机和截图帧获取真实渲染结果；固定输入输出写在题面内，内部评测材料单独保留。各题复用现有宿主，L1 拆分、L2 按需、L3 完整场景，尚未执行模型或正式效果评分，原有任务与实验保留。

独立的 Godot 试点环境：**3 个 Platformer 场景 + 2 个 FPS 场景，共 15 个三级递进任务**。目前准备了基线场景、效果入口、提示词、验收条目和事件回放，没有启动模型实验。

[打开本地场景与任务页面](http://127.0.0.1:8770/index.html) · [任务清单](manifest.json) · [接口合同](HOST_API.md) · [评测设计](EVALUATION_DESIGN.md)

扩展 [Bistro、Sponza、Open Forest Benchmark、官方 TPS Demo、Boujie Water Shader 场景库](http://127.0.0.1:8770/realistic/index.html)，文件位于 `realistic/projects/`。五个独立工程的启动方式、兼容性与许可见 [扩展场景说明](realistic/README.md)。当前共 10 个场景；扩展工程尚未编制三级模型任务，现有 15 个任务保留。

新增独立的 [Forest 草地小场景 / L1–L3 题目预览](http://127.0.0.1:8770/forest_grass_lab/index.html)：风动 → 固定根部 → 玩家压草与恢复。位于 `forest_grass_lab/`，含 1 个基础小场景和 3 份待审核题目；不并入原 15 题，尚未接入 API。双击 `Forest_Grass_Preview.cmd` 查看本地参考效果。

## 查看与启动

完整的 Godot 4.6.1 图形编辑器已放在本项目 `tools/godot/`，是免安装便携版。双击 [Godot_Editor.cmd](Godot_Editor.cmd) 打开项目管理器；双击 [Edit_Platformer.cmd](Edit_Platformer.cmd) 或 [Edit_FPS.cmd](Edit_FPS.cmd) 直接编辑对应工程。编辑器中按 F6 运行当前打开的场景，按 F8 停止。程序和本项目启动入口使用的编辑器数据均保存在 D 盘。

双击 `P01.cmd`、`P02.cmd`、`P03.cmd`、`F01.cmd`、`F02.cmd` 可打开对应原生 Godot 场景。页面里的图片是本机实际生成的**基线截图**，不是模型结果；本轮尚未做浏览器 Web 导出。

在本目录打开 PowerShell：

```powershell
.\launch.ps1 -Scene P01
.\launch.ps1 -Scene F01 -Editor
```

查看模式用方向键转动相机，SPACE 逐个触发公开事件，TAB 切到原项目角色控制，R 重置，1/2/3 选择等级。原项目控制器和场景载体已接入，效果槽为空，所以触发事件首先能看到状态记录；目标 shader 反馈是待评测任务。

## 文件

| 位置 | 内容 |
| --- | --- |
| upstream/ | 两个 Kenney 官方项目的原始快照，保持原样 |
| projects/platformer/ | P01–P03 可运行 Godot 工程 |
| projects/fps/ | F01–F02 可运行 Godot 工程 |
| projects/*/pilot/ | 场景 `.tscn`、固定宿主及事件配置 |
| projects/*/effects/ | 每个场景独立的空效果入口 |
| tasks/*/prompt.md | 15 份模型提示词 |
| tasks/*/task.json | 任务要求、前序任务、允许修改范围与验收条目 |
| verification/ | 基线加载/回放日志、实际渲染截图与检查结果 |
| tools/godot/ | 官方 Godot 4.6.1 便携版；未安装到系统目录 |
| sources.json / downloads/ | 原始下载来源、时间、字节数和保留的压缩包 |

两份新工程保持独立的资源路径和 Audio Autoload；不调用旧实验 runner，不读取旧 API 密钥，也不改旧实验结果。

## 复现

以下命令在工作区根目录执行。脚本仅使用 Python 标准库；准备脚本额外使用已安装的 certifi 提供公开 CA 证书。原生场景启动不依赖 Python 环境。

```powershell
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\tools\prepare.py
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\tools\run.py --scene all --mode import
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\tools\run.py --scene all --mode verify
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\tools\run.py --scene all --mode capture
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\tools\build_page.py
```

`verify` 使用无显示模式检查逻辑；`capture` 使用真实 Windows/Vulkan Forward+ 渲染，不能用 headless 的空画布代替。现有 180 步自检不是完整的任务评分器。`prepare.py` 会刷新基线场景、宿主与任务定义，保留已经存在的 effects 文件；有后续模型提交时，应先建立独立运行副本，不在基线目录混写。

本机最初遇到受限环境的 AppData/证书读取问题、上游砖块材质自动提取提示，以及停用角色后自动脚步音频在退出时的资源提示。已将数据路径改到本项目、为项目与便携编辑器配置公开 CA 包、关闭该砖块的材质自动提取，并在进入游玩模式时才启动脚步音效。原始 upstream 文件没有变动，未关闭 TLS 校验。

## 来源与许可

- [Kenney Starter Kit 3D Platformer](https://github.com/KenneyNL/Starter-Kit-3D-Platformer)：脚本 MIT；包内图形和音效 CC0，许可保留在 [原项目](upstream/platformer/LICENSE.md)。
- [Kenney Starter Kit FPS](https://github.com/KenneyNL/Starter-Kit-FPS)：脚本 MIT；包内资产 CC0，许可保留在 [原项目](upstream/fps/LICENSE.md)。
- [Godot 4.6.1 官方下载归档](https://godotengine.org/download/archive/4.6.1-stable/)；Godot 使用 MIT 许可。
- [Video-MME-v2](https://github.com/MME-Benchmarks/Video-MME-v2)：仅借鉴分级与关联任务设计，不复用其数据或声称复现其分数。

扩大至约 900 题的草案为 100 场景 × 3 条效果链 × 3 级；本轮只准备每场景 1 条链。场景与评分细节应先由你检查，再根据试跑反馈定版。
