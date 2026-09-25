# FG01 · S1 P3

用户已授权 Astra、Sol、Claude、Kimi 各完成 L1→L2→L3，共 12 项。每项沿用 80 次请求 / 24 次模型检查，追加一次不反馈的最终公开渲染。HTTP 可重试错误等五分钟再请求；失败请求同样计入预算。

- `project/`：最小 Godot 场景、宿主、唯一候选 shader 与两张必需贴图。原始 GLB 和未使用法线图移入 `source_archive/`，运行不依赖它们。
- `experiment/`：此协议和 API/渲染驱动。providers.py、state.py、local_lock.py、工具 schema 与计划协议沿用现有 Three.js P3，只将代码文件改为 Godot shader。
- `runtime/project/`：串行 GPU 检查用副本。不会覆盖静态 starter 或作者参考。
- `runs/s1_p3/<alias>/L<level>/`：每个条件一个固定目录，代码、计划、PNG、动画、阶段状态、逐条格式化事件和原始 JSONL 均保留。重新执行入口跳过已有结果，不新开重复批次。
- `reference/`、`verification/`：作者参考和本地检查记录；不进入模型输入。模型只收到题面、HOST_API、当前候选和自己的检查截图。

API 复用 `D:\threejs_seven_experiments\.env`，不复制密钥、不输出认证头。配置固定在 models.json；Kimi 沿用已配置的 131072 输出上限。每次调用在 `runtime/logs/<alias>.log` 打印完整文本输入；图像在日志中列出 PNG 路径，实际 API 仍发送图像字节。调用记录也保存于 events/ 和 trajectory.jsonl。

从本目录的父目录运行：

```powershell
D:\shaderagent17_s0_s1\.venv\Scripts\python.exe experiment/run.py --dry-run
D:\shaderagent17_s0_s1\.venv\Scripts\python.exe experiment/run.py --launch
```

创建 `experiment/PAUSE` 文件会在下一次 API 调用前暂停；删除后继续。暂停不会中断已经发送的付费请求。已运行 worker 有操作系统锁，防止同模型重复调用。`runtime/processes.json` 记录本轮进程号。

指定模型恢复因 API/本地错误中断的任务：

```powershell
D:\shaderagent17_s0_s1\.venv\Scripts\python.exe experiment/run.py --launch --models openai_main --resume-errors
```

恢复会先把旧终止记录、最终截图和检查点副本保存在该项 `restart_history/`，接续同一段对话、代码和剩余预算；已完成项直接跳过。554（EdgeOne 超时）和 524 一样每五分钟重试。重试恢复后，旧 HTTP 错误保留在轨迹，不再作为最终失败显示。

2026-09-24 用户安排：Sol 本轮结束后，Claude 从 L1 重跑。`after_sol.py` 通过同一个操作系统锁等待 Sol 整条任务链（包括重试等待）结束，随后归档 Claude 原目录到 `runs/archive/`，新任务仍使用 `runs/s1_p3/claude_main/`，每级重新给予 80 次请求 / 24 次检查。队列状态保存在 `runtime/after_sol.json`，结果页显示队列进度和旧记录链接。此队列只执行一次；整台电脑或调度进程退出后不会自行重启。

后续追加：Claude 本轮结束后恢复 Kimi L3。`after_claude.py` 等待上述队列的整个生命周期结束，再从 Kimi L3 第 9 次请求后的检查点恢复，沿用剩余 71 次请求 / 21 次检查；L1/L2 不重跑。状态为 `runtime/after_claude.json`，展示仍是原 Kimi L3 卡片。流式响应缺少结束原因时保留完整错误记录、不执行残缺工具调用，等待五分钟后重试。

展示入口：[results.html](../results.html)，[题目和作者参考](../index.html)。阶段 pass 为模型自评；技术执行成功仅说明编译、运行和截图完成，不能等同任务视觉通过。
