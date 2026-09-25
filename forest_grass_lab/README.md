# FG01 · Forest 草地递进题

**当前阶段：用户已批准 Astra、Sol、Claude、Kimi 的 L1→L2→L3 S1/P3 实验。** [实验结果与进度](results.html) · [协议、预算和运行方式](experiment/README.md)。

从原 Forest Benchmark 提取 Grass1–4 模型与草贴图，搭建一个轻量草地小场景，提供三个递进等级入口。原大森林和露珠场景保留。此次只有一条三级任务链，不把同一草地的三个难度重复算成三个基础场景。

[打开预览页面](http://127.0.0.1:8770/forest_grass_lab/index.html) · [题目清单](manifest.json) · [宿主合同](HOST_API.md)

| 等级 | 新要求 | 继承 |
| --- | --- | --- |
| L1 | 草随风平滑运动，响应风向、风强和速度 | 静态初始代码 |
| L2 | 根部固定，顶部随风摆动，沿高度连续弯曲 | 同一模型的 L1 提交 |
| L3 | 玩家经过后局部向外倒伏，短时保留后恢复 | 同一模型的 L2 提交 |

L2 已按用户确认使用“根部固定，顶部随风摆动”。L1 的参考演示允许根部随风滑动，便于看清 L2 增加的约束；不能把 L1 的宽松要求用于 L2/L3。

## 怎么查看

在上一级 `kenney_shader_pilot` 目录：

- 双击 `Forest_Grass_Preview.cmd`：打开本地作者参考效果，可点击 L1/L2/L3 切换，点击 `Show starter` 查看静态待填写版本。
- 双击 `Forest_Grass_Starter.cmd`：只打开初始代码，没有参考答案。
- 双击 `Edit_Forest_Grass.cmd`：编辑工程，F6 运行当前 `.tscn`。编辑器默认运行的是初始代码；参考效果使用专门预览启动器。

按钮和快捷键都在弹出的 **Godot 场景画面窗口**里操作，不是在 CMD 中操作。面板按钮不会抢占空格键：1/2/3 切等级，空格暂停，R 重置。`Root close-up` 查看前排草与青色固定地标；`Top view` 查看玩家路径。L3 点击 `Replay / WASD` 后，可用 WASD 手动移动橙色玩家占位体。黄色圈表示影响半径，仅作观察标记。

网页动画来自本机 Godot 连续步进后的真实截图，标注为“本地参考”，不是模型输出。网页支持等级切换、定帧和题面查看；实时手动交互在原生场景中进行。

## 文件与拆分边界

- `project/`：独立 Godot 工程；只加载草资产、小地面、标记、相机和玩家占位体。
- `source_archive/source/`：4 个原始 Grass GLB，仅供溯源，已移出运行工程；`project/assets/grass_cards.json` 保留其角点和 UV。
- `project/host/grass_host.gd`：固定宿主，生成细分网格、提供风与玩家原始轨迹输入、实现回放和查看 UI。
- `project/effect/grass.gdshader`：唯一待填写文件，当前只有静态材质和空顶点效果。
- `tasks/FG01_L1`、`FG01_L2`、`FG01_L3`：各级 `prompt.md`、`task.json`。
- `reference/`：本地作者参考 shader，在 learner project 之外；不能作为后续模型输入。
- `tools/`：资产准备、本地参考生成、题面生成、Godot 检查脚本；没有 API 调用代码。
- `verification/`：实际渲染截图、动画和运行记录。

草片的原模型每张只有 4 个顶点，不足以展示沿高度弯曲。宿主保留原角点之间的形状/UV 插值，将底边对齐地面，放大 4 倍，增加 18 段高度和 4 段宽度细分，并用 `UV2.y` 标记归一化高度。335 张草片共用这套准备；模型不需要重新生成网格。

渲染使用原 BaseColor 的 Alpha 裁切和原 ORM 粗糙度。未使用的法线图移入 `source_archive/`；运行工程只保留两张必需贴图。场景采用固定日光及环境补光。

## 当前检查的含义

已准备公开检查条件：无风、普通风、强风与变向、玩家经过与恢复、无风压草、反向与停留。它们是可观察的验收要求；**完整自动评分器尚未实现**。

本地检查验证场景加载、参考材质编译、连续步进、重置与实际画面输出。作者预览以 8 fps 采样；正式 S1/P3 以 1/60 秒逐帧运行，保存实际 PNG，最终候选另导出动画。本地参考不是唯一允许的实现方式。

准备/复查（从工作区根目录执行）：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\forest_grass_lab\tools\prepare_assets.py
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\forest_grass_lab\tools\build_tasks.py
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\forest_grass_lab\tools\run_checks.py import
.\.venv\Scripts\python.exe -B -X utf8 kenney_shader_pilot\forest_grass_lab\tools\run_checks.py capture
```

许可：原 Forest 仓库 MIT，草资产来源按上游记录为 Poly Haven `grass_medium_01`。原许可和完整资产署名已复制到 `project/assets/`，来源记录在 `project/assets/source.json`。项目配置使用随工程附带的公开 CA 包，避免本机证书库读取报错；不关闭 TLS 校验。
