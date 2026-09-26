# Forest Benchmark v0.2

[GitHub 上传内容与恢复说明](GITHUB_CONTENTS.md) | [S1/P3 实验状态](experiment/STATUS.md)

[L3 tasks and native source status](README_L3.md) | [Review page](index.html) | [L3 validation status](L3_STATUS.md)

# L1/L2 v0.1 baseline

以下介绍 v0.1 的 5 条森林效果链、10 道 L1/L2 题，使用独立的合成最小场景。v0.2 已新增 6 道 L3 定义，其中五题有完整原森林空接入工程；详情和未完成的验收条件见 [L3 说明](README_L3.md)。

先打开 [题目与视频检查页](index.html)，或查看 [验证汇总](VALIDATION.md)。页面中的视频是作者参考实现，尚未进行模型实验。

| 链 | L1 单效果 | L2 效果交互 |
| --- | --- | --- |
| A | [程序灼烧与焦化](tasks/A_L1/prompt.md) | [灼烧前沿驱动的旋涡余烬](tasks/A_L2/prompt.md) |
| B | [持久化脚印压痕与 POM](tasks/B_L1/prompt.md) | [压痕约束的湿润扩散与干燥](tasks/B_L2/prompt.md) |
| C | [三维云密度驱动的地面云影](tasks/C_L1/prompt.md) | [云遮光约束的薄雾与体积光](tasks/C_L2/prompt.md) |
| D | [双相位 Flow Mapping 水纹](tasks/D_L1/prompt.md) | [固定接触源的泡沫输运](tasks/D_L2/prompt.md) |
| E | [透明水膜的折射与吸收](tasks/E_L1/prompt.md) | [交互涟漪与前景折射的组合](tasks/E_L2/prompt.md) |

## 文件与边界

- tasks/：逐题 prompt，仅包含效果与算法名称、输入输出类型、目录内容表、工具和自主渲染观察说明，无算法库编号、私有测试实例或调用次数。
- starters/：10 个完整 Godot 起始工程。fixture/、assets/ 只读，solution/ 和 scratch/ 可写。空接口返回 NOT_IMPLEMENTED，不带目标算法答案。
- starters/public/<任务>/：移到工程外的宿主配置、prompt、类型说明和文件清单；不在模型工作目录内。导出工程采用同样的并列布局。
- author/：原始规范、独立 float64 参考、GPU 参考、100 组私有数值案例、25 组因果干预、错误对照、判题器及证据。整个目录不进入模型导出包，随本次仓库快照上传。
- exports/：从文件白名单生成的单题工作区。L2 在投放前注入指定前级代码，并记录来源哈希。
- main.py：构建、验证、导出入口；也提供 ModelTools 与 read/write/render 函数定义。

数值使用同步后的 GPU float32 原始缓冲，截图与 MP4 用于展示。参考实现的核心在计算 Shader；CPU 负责资源、事件记账和显示数据传输。报告保留 GPU 数值、实际绑定的纹理、前后景捕获、文件哈希和原始日志。

## 使用

在仓库根目录执行；本机也可把 python 替换为 D:\shaderagent17_s0_s1\.venv\Scripts\python.exe。

~~~powershell
python forest_benchmark/main.py build_starter all
python forest_benchmark/main.py run_reference all
python forest_benchmark/main.py run_numeric A_L1
python forest_benchmark/main.py run_numeric A_L2 --inherited
python forest_benchmark/main.py run_interactions A_L2
python forest_benchmark/main.py capture_visuals E_L2 --frames 90
python forest_benchmark/main.py audit_submission A_L1 --submission forest_benchmark/starters/A_L1
python forest_benchmark/main.py validate_release all
~~~

Godot 默认使用本仓库 tools/godot/ 下的 4.6.1 console 可执行文件，可通过 GODOT_BIN 指定。Python 依赖为 numpy、Pillow；MP4 编码使用 ffmpeg 或 imageio-ffmpeg。

导出供人工检查的工作区：

~~~powershell
python forest_benchmark/main.py package_model_task A_L1 --review
python forest_benchmark/main.py package_model_task A_L2 --review --predecessor path/to/sealed/A_L1 --condition self_predecessor
python forest_benchmark/main.py package_model_task A_L2 --review --predecessor forest_benchmark/author/gold/A_L1 --condition gold_predecessor
~~~

目标目录必须不存在，避免覆盖已有候选。self_predecessor 复制同一模型的前级 solution；gold_predecessor 只接受经过校验、已去掉下一层实现的作者 L1 导出。未注入前级的 L2 仅为起始模板。

## 模型调用

~~~python
from forest_benchmark.main import ModelTools, tool_definitions

tools = ModelTools(workspace, renderer=isolated_render_worker)
definitions = tool_definitions()
tools.call("read", path="solution/adapter.gd")
tools.call("write", path="solution/adapter.gd", content=source)
tools.call("render", frames=90, camera={
    "position": [3, 2, 4], "look_at": [0, 0.5, 0]
})
~~~

宿主从工程旁的 public/<工程目录名>/ 加载运行配置；模型只接收组装好的 prompt，read/write 的根目录仍为工程目录。搬运或复制可运行工程时，宿主须同时携带这一外层目录。

模型可自行选择调用顺序与调试相机。次数由宿主计数，耗尽后返回 ENDED，prompt 不透露次数。正式评价使用事先固定的观察配置。render 由宿主传入隔离执行器；未提供时返回 INFRA_ERROR，避免把拥有作者文件读取权限的本机进程用于正式求解。

当前本机运行命令仅执行作者参考与作者构造的对照。它们不等于操作系统沙箱；正式投放仍须通过隔离、视觉评分配置和预算锁定门禁。validate_release 不会把数值通过自动升级为 RELEASE_READY。

## 验证与来源

~~~powershell
python -m unittest discover -s forest_benchmark/tests -p test_tools.py -v
python forest_benchmark/author/test_reference.py
python forest_benchmark/author/verify_starters.py
python forest_benchmark/author/visual_controls.py
~~~

完整逐题状态、局限与实际证据见 VALIDATION.md 和 author/status.md。VLM 审美评分与正式模型实验不在本次执行结果中；原实验继续保持暂停。

计算与捕获接口核对了 Godot 4.6 官方文档：[Compute shaders](https://docs.godotengine.org/en/4.6/tutorials/shaders/compute_shaders.html)、[RenderingDevice](https://docs.godotengine.org/en/4.6/classes/class_renderingdevice.html)、[SubViewport](https://docs.godotengine.org/en/4.6/classes/class_subviewport.html)。
