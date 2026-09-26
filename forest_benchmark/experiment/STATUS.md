# 森林 S1 / P3 模型实验

[实验展示页](http://127.0.0.1:8772/experiment/index.html) · [实时状态](../runtime/experiment/status.json) · [生效配置](../runtime/experiment/run_config.json) · [P3 系统提示](P3.md)

本轮独立测试 forest_benchmark。旧 scene_algorithm_tasks 实验保持暂停。模型顺序沿用 GPT-6 Astra → GPT-5.6 Sol → Claude Sonnet 5 → Kimi K3；同一时刻只执行一个模型请求或工具调用。

每个模型依次运行 A–E 各组的 L1、L2、L3。C_L3_R 正常排队；C_L3_S 缺少可运行源场景映射，单独记录为 blocked_source，不向模型发请求、不算作模型失败。共 60 个可运行案例与 4 个源阻塞记录。

S1 只继承同模型、同组前一级实际生成的 solution/，排除 plan.json。上一级预算耗尽时继承其现有文件；各题重新开始对话，不继承图像、评分或作者参考实现。L3 从该模型 L2 候选进入完整森林。

P3 使用 solution/plan.json 记录计划，按需调用 read、write、render。每题最多 80 次模型请求、80 次 render；耗尽自动结束，限制不进入模型输入。HTTP/传输错误等待五分钟后重试，保留计数、历史和候选，不推进其他案例。

render 使用候选快照运行 Godot，返回 PNG 图像数据、相机记录、日志和连续 MP4。候选编译错误直接作为工具反馈。每题结束后保存最终候选视频供人工查看，此步骤不调用模型、不回传模型、不占模型工具预算。执行采用独立工程快照及过滤密钥环境变量的子进程；尚未配置操作系统级沙箱。本轮是模型求解过程实验，正式投放门禁与算法质量评分保持独立，不把模型自评、成功渲染或未执行的集成测试当作通过。

每例保存在 `runs/s1_p3/<模型>/<题号>/`，包含实际 input.json、trajectory.jsonl、checkpoint.json、initial_solution/、model_workspace/solution/、继承记录与 result.json。页面可查看 prompt、工具调用、计划、文件差异及视频。

```powershell
python forest_benchmark/experiment/run.py launch
python forest_benchmark/experiment/run.py pause
python forest_benchmark/experiment/run.py resume
python forest_benchmark/experiment/serve.py --port 8772
```

暂停命令在当前请求或工具操作返回后停止，HTTP 等待期间会及时停止。已经完成的案例不会重复调用。
