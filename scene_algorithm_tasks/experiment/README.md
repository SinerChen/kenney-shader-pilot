# 本次串行 S1 / P3 实验（待用户审阅）

> Run authorized on 2026-09-24. See [live experiment status](STATUS.md); the review snapshot below is retained for reproducibility.

本轮先交付可检查的 prompt 和队列，不启动模型。用户要求“先让我检查此次实验的 P3 prompt 再调用”；审阅完成后，才进行模型调用。当前 API 调用数为 0。

## 先检查这些文件

- [P3.md](P3.md)：所有模型共用的完整系统 prompt。
- [SA01_L1 完整输入预览](review/SA01_L1.md)：系统 prompt、该题原始题面及三项工具定义的拼接。
- [SA01_L3 完整输入预览](review/SA01_L3.md)：当前关注的场景级任务输入。
- [审阅索引](review/INDEX.md)：全部 15 份完整输入预览。
- [串行配置](config.json)：模型名单、顺序、预算和 S1 继承规则。
- [串行队列](queue.json)：60 个模型任务及各自的前级依赖。

## 本次 P3 的定义

P3 保留先制定 4–8 项计划、逐项推进和最后检查目标场景的结构。模型按需自行调用 read、write、render，不规定各子任务的工具顺序或最低渲染次数；已删除固定工作循环及‘保持结果可信’部分。根据用户已经确定的工具范围，本次只暴露 read、write、render；计划和阶段结论改用 write 保存到 effect/plan.json，结束使用最终回复。它是三工具版 P3，不是旧 set_plan/finish_step/submit 状态机的原样复用。

不向模型追加公开案例、评分材料、算法编号、作者源码、算法契约或通用接口。每题输入由以下内容组成：

1. system：本目录 P3.md 的完整文本。
2. user：当前 tasks/<题号>/prompt.md 的完整文本，不附加 task.json、cases.json 或其他文档。
3. tools：当前 model_tools.json 中 read、write、render 的原始定义。

后续工具返回当前实验文件和真实图像。模型应得到实际图像内容，不能只得到路径或作为文本的 base64。工具结果由宿主执行后返回的基本结构参照 [OpenAI 官方 function calling 文档](https://developers.openai.com/api/docs/guides/function-calling)；本地审阅文件使用 provider 中立格式，不声称是各 API 可直接提交的最终请求体。

## 模型与串行顺序

沿用已有实验配置中的四个模型标识：gpt-6-astra → gpt-5.6-sol → claude-sonnet-5 → kimi-k3。每个模型按 SA01 → SA02 → SA03 → SA04 → SA05，每组内部 L1 → L2 → L3，共 4 × 5 × 3 = 60 个任务。

整个新实验只有一个执行队列，API 和 GPU 都串行；重试等待期间不启动后续任务。每题内部上限为 80 次模型请求、80 次 render 调用，分别计数，失败尝试也计数；重试不重置预算。预算数值、剩余次数和停止规则不进入模型消息或工具返回。任一上限耗尽时，由宿主保存正在执行的操作结果及现有候选，自动结束当前题并记录 budget_exhausted；不再启动新操作、不向模型发预算提醒，也不追加最终总结请求。之后按 S1 规则推进串行队列。为使计数明确，拟采用显式重试循环，禁用传输层隐藏重试。可重试错误间隔 300 秒；认证、配置或基础运行环境错误暂停队列，等待修复。上述为本次待审阅配置，尚未执行。

## S1 继承

同一模型、同一组内，L2 继承 L1 最终保存的真实效果文件，L3 继承 L2；即使前级因预算停止，也保留其真实候选和未完成状态，不换入参考答案。基础环境或 API 错误不作为正常完成项继续传播。

每一级新开对话，使用本级独立的 scene/ 与 inputs/，重新创建 observations/。仅复制前级 effect/ 中的候选文件，不继承 plan.json、对话、截图、评分或其他模型的输出；前级工作记录保存在前级运行目录。跨模型、跨组均从相同冻结起点开始。

初始候选不自动拼接到 user 消息；模型通过 read 查看本题 effect/。正式运行目录拟为 runs/s1_p3/<模型别名>/<题号>/model_workspace/，不覆盖 tasks/ 中的模板、旧 FG01 实验或其他模型的运行。

## 当前状态

P3 文本、离线请求拼接和串行队列已生成。三工具的文件访问与真实 Godot 渲染已实现，15 题已复用原 Godot 宿主并配置分层环境，候选数值通过 sample() 返回；三工具版 P3 运行状态机、宿主预算终止逻辑和 provider 连接尚未接入完整执行流程；自动结束策略已写入配置，列为启动前必检项。审阅文件中的 runtime_ready=false 如实保留；本轮没有执行 launch，也没有试探性请求、模型列表查询或付费模型调用。

环境分层为 L1 原场景相关子集、L2 按需交互子集、L3 原完整场景，详见 [环境配置](../ENVIRONMENTS.md)。批准 prompt 后先完成模型循环接入与本地预检，再进入串行队列；当前不调用模型。

## 重新生成审阅包

在工作区根目录执行：

```powershell
& '..\.venv\Scripts\python.exe' -B scene_algorithm_tasks/experiment/prepare_review.py
```

此脚本只读取本地 prompt、工具定义、模型配置和任务元数据，生成审阅文件及 SHA-256 记录；不会读取密钥、连接网络、启动 Godot 或修改候选。审阅后如果输入发生变化，须重新生成预览，让最终运行使用确认过的版本。
