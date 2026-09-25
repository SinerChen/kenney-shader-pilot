# 当前模型输入

基础请求包含当前题 `prompt.md` 的文本，以及 `model_tools.json` 中 `read`、`write`、`render` 三个工具定义。本次用户指定的串行 S1/P3 实验额外将 [P3 系统 prompt](experiment/P3.md) 放在 system 消息，user 仍为原题面，不追加其他题目或评测文档；[完整输入预览](experiment/review/INDEX.md) 已生成，待用户检查后才调用模型。

题面提供算法名称、一份固定测试输入、输出字段、目标效果、目录权限和自主渲染方式。不包含算法库/构想编号、公开验收操作、评分条目或引用链接，不要求读取算法契约或通用接口。`task.json`、`cases.json`、来源映射、评分材料、作者算法及参考结果均留在模型文件工具根之外。

| 当前实验目录 | 权限 | 用途 |
|---|---|---|
| scene/ | 只读 | 本层场景入口、范围配置及现有宿主；project/ 为原工程只读目录 |
| inputs/ | 只读 | 已生成的 test_input.json，与题面 JSON 一致 |
| observations/ | 只读 | render 产生的真实 PNG、日志、相机参数与运行记录 |
| effect/ | 可读写 | main.gd 效果入口与辅助文件；L2/L3 运行前继承前级候选 |

每题的工具根为 `tasks/<题目>/model_workspace/`。`tools/model_io.py` 的 `FileTools` 限制文件工具的目录范围，拒绝越界路径和对只读目录的写入。`read` 支持目录枚举、分页文本与 PNG/JPEG/WebP 读取；`write` 保存完整 UTF-8 效果文件。

## 自由观察与真实渲染

`render` 默认运行 `scene/main.tscn`，也允许运行模型在 `effect/` 内编写的 `.tscn` 预览。模型可设定位置、观察目标、up 方向、透视/正交投影、FOV、正交尺寸、裁剪面、分辨率、截图帧及相机轨迹。省略相机参数时使用场景相机。每次渲染从当前文件的新实例开始，不修改固定输入。

```json
{
  "camera": {
    "position": [6, 4, 8], "look_at": [0, 0, 0],
    "projection": "perspective", "fov_degrees": 50
  },
  "frames": [1, 60, 120],
  "resolution": [960, 640]
}
```

帧范围受当前固定输入 steps 限制，最多 720 帧；一次最多取 4 张图。相机轨迹最多 8 个关键帧，按帧线性插值。图像各边为 128–1920 像素，总像素不超过 2073600。工具返回 `images`（PNG 的 base64 数据、路径和实际相机参数）、日志路径、运行状态及耗时。返回 `ok=false` 时不提供成功图像；应先用 `read` 查看日志。

每次调用在 `observations/render_<时间>_<编号>/` 保存 `request.json`、`files.json`、`import.log`、`godot.log`、`capture.json`、`result.json` 、samples.json 和 PNG。编译提前失败时只保存已产生的文件。目录不存在或场景缺失时直接返回错误，不沿用历史截图，不生成效果评分。隔离预览的结果标记为 `candidate_preview`。

## 实验侧调用

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scene_algorithm_tasks/tools").resolve()))
from model_io import FileTools, compose_request

task = Path("scene_algorithm_tasks/tasks/SA01_L1")
request = compose_request(task)  # 基础模式；P3 模式另用 experiment/prepare_review.py 的 p3_request
host = FileTools(task / "model_workspace")
result = host.call("render", {"frames": [1], "camera": {
    "position": [6, 4, 8], "look_at": [0, 0, 0]}})
```

模型 provider 尚未接入。接入时，需将 `render.images` 和 `read` 的图像数据转为 provider 的图像消息，不能只把 base64 当文本发送给模型。

渲染桥位于 `tools/model_render.py` 与 `tools/render_capture.gd`。它对当前文件做快照，使用已有的 Godot 4.6.1 原生 Forward+ 渲染，共用 GPU 文件锁，启动隐藏窗口并设定超时；headless 仅用于导入资源，不用于截图。默认入口 `res://scene/main.tscn` 继承原场景。`scene/project/` 是受限只读映射，原资源继续使用原来的 res:// 路径。引擎在本包 runtime/ 下复用各原工程的运行副本及导入缓存，不改写原工程；GPU 锁覆盖候选替换、导入和渲染全过程。每次启动全新场景实例并替换上一轮候选文件。`effect/main.gd` 的 configure/step/sample 只负责本题候选；原宿主保留。隔离预览仍可使用 preview_reset/preview_step；全局 shader TIME 可能包括初始化时间，精确算法时间应由宿主传入。

文件工具的路径限制不是 Godot 进程的操作系统沙箱：候选 GDScript 会由原生引擎执行。正式接入不可信候选前，应在隔离运行账户或容器内执行渲染；不要把文件工具的只读权限当作对候选脚本的进程限制。

## 当前完成范围与检查

15 题均已配置现有宿主环境（environment_ready=true）：L1 为原场景相关子集，L2 按需保留交互对象，L3 使用原完整场景。空候选不实现目标算法，sample() 初始返回空字典，不能当作正确数值结果。模型调用流程与正式评分尚未启用，runtime_ready=false。环境启动验证见 verification/environments/validation.json；它只证明宿主、裁剪与真实截图工作，不代表候选效果通过。

- `tools/build_pack.py` / `tools/validate_pack.py`：重新生成题面、工具和结构检查。
- `tools/test_model_io.py` / `tools/test_render_tool.py`：文件边界和相机参数检查。
- `tools/smoke_environments.py`：串行验证 15 个现有宿主环境和原文件未变。
- `tools/smoke_render.py`：原生 GPU 验证透视、正交俯视、相机轨迹、逐帧变化、候选预览和编译错误返回。
- `verification/render_tool/validation.json`：最近一次完整 GPU 工具自检结果与截图路径。

生成器不会覆盖 effect/ 中已有候选，也不会向模型追加内部实验规程。
