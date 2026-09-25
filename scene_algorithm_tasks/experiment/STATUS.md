# 实验运行入口

[HTML 实验结果页](http://127.0.0.1:8770/scene_algorithm_tasks/index.html) · [独立展示服务](http://127.0.0.1:8771/index.html)

用户已于 2026-09-24 授权“进行实验”。正式实验已启动，采用一条后台串行队列。

- [实时状态](../runtime/experiment/status.json)：当前模型、题目、调用计数和完成题数。
- [进程记录](../runtime/experiment/process.json)：后台启动进程；实时状态中的 pid 为实际工作进程。
- [生效配置](../runtime/experiment/run_config.json)：已授权的 P3/S1 配置。
- [授权与冻结记录](../runtime/experiment/approval.json)：审阅清单哈希及冻结输入哈希。
- [启动预检](../runtime/experiment/preflight.json) · [运行器测试日志](../runtime/experiment/tests.log)。
- [首题状态](../runs/s1_p3/openai_astra/SA01_L1/status.json) · [首题计划](../runs/s1_p3/openai_astra/SA01_L1/model_workspace/effect/plan.json) · [首题调用轨迹](../runs/s1_p3/openai_astra/SA01_L1/trajectory.jsonl)。

顺序为 GPT-6 Astra → GPT-5.6 Sol → Claude Sonnet 5 → Kimi K3；各模型依次执行 SA01–SA05，每组 L1 → L2 → L3，共 60 题。同一时刻只有一个模型请求或一次工具执行。所有 HTTP 错误（包括 400、401、403、404、429、5xx）及网络传输错误均等待 300 秒后继续重试，期间不推进队列；重试仍计入本题预算。重试截止时间写入检查点，恢复时继续剩余等待。非 HTTP 的配置或宿主故障停止队列并记录原因。

每题上限为 80 次模型请求和 80 次 render 调用，失败尝试也计数，预算不进入模型输入。任一上限耗尽时，正在执行的操作允许返回并保存结果，随后停止当前题；不再执行新工具，不追加最终模型请求或额外渲染。第 80 次模型请求返回的工具调用只记录、不执行。模型也可以自行提前给出最终回复。

模型只得到已审阅的 system、user 和 read/write/render 定义；按需使用工具，没有强制逐项渲染。截图以原生图像内容回传；本地轨迹将图像去重存入 images/，checkpoint 保留恢复原始消息所需的引用。OpenAI 图像工具结果格式参照 [官方 function calling 文档](https://developers.openai.com/api/docs/guides/function-calling)。

输出目录为 `scene_algorithm_tasks/runs/s1_p3/<模型别名>/<题号>/`：

- `input.json`：实际起始输入。
- `model_workspace/effect/`：模型当前实现及计划。
- `model_workspace/observations/`：该模型实际渲染的 PNG、日志和数值输出。
- `trajectory.jsonl`、`checkpoint.json`：请求、响应、工具结果及恢复记录。
- `result.json`：结束原因、调用计数、候选文件哈希与模型自评状态。算法质量不因模型结束或渲染成功而自动判为通过。

S1 仅继承同模型、同组前一级的实际 effect/ 文件，排除 plan.json；对话、观察图像和输入场景不继承。前一级预算耗尽仍继承其现有候选。每一级都有独立场景和工作目录。

`experiment/config.json`、`review/` 保留审阅时的历史快照，因此其中的待审阅标记不代表当前运行状态；以此页链接的 runtime 文件为准。运行中不要重新生成或改写冻结输入。

运行入口为 `experiment/run.py`。`--preflight` 只做本地检查；`--launch` 启动或恢复串行队列，已有计数和候选不会重置。若进程在请求或工具执行中异常退出，恢复前需要检查该次操作是否完成，以免重复执行。


## HTML 展示

页面每 15 秒刷新，展示服务每 10 秒从实际结果更新 `runtime/dashboard.json`。不调用模型或 Godot。服务重启命令（在项目根目录执行）：

```powershell
& '..\.venv\Scripts\python.exe' -B -X utf8 scene_algorithm_tasks/serve.py --port 8771
```

[页面交互与布局验证](../verification/dashboard/validation.json)。


## 连续效果视频

[打开效果视频](http://127.0.0.1:8771/index.html#model=openai_astra&task=SA01_L1)。页面默认展示视频，支持循环、进度拖动、0.25× / 0.5× 慢放、全屏与 MP4 下载；原观察记录保留在“过程截图”页签。

视频从各模型实际保存的候选文件重新运行原生 Godot 场景生成：1280×720，30 fps，按固定输入以 60 Hz 推进。草地录制完整 4 秒输入，水面与贴花为 3 秒；静态材质和雾场景录制 6 秒小幅相机环绕。优先沿用模型最后一次成功观察目标场景的相机；很远的纯俯视诊断机位改用此前的细节机位。相机、输入、候选文件 SHA256 和录制日志均可在“录制记录”查看。

后台 `tools/render_videos.py --watch` 自动为已结束任务补录，也可预览 HTTP 等待中已保存的候选。视频明确区分“最终候选”和“任务未结束”。候选改变后，旧视频不再作为当前结果显示；原候选编译或运行失败会显示失败原因。视频生成成功仅表示可播放，不等于算法验收通过。

录制与实验共用串行 GPU 锁，只使用实验结束、暂停或足够长的 HTTP 重试等待窗口。此流程专供人工检查，不调用模型、不回传给模型、不修改候选、不占模型实验预算。

- 输出：`runs/s1_p3/<模型>/<任务>/presentation/latest.json`，其中指向对应版本的 `effect.mp4`、`poster.png` 和日志。
- 后台进度：[video_review/status.json](../runtime/video_review/status.json)。
- 播放与拖动验证：[video/validation.json](../verification/video/validation.json)。

```powershell
& '..\.venv\Scripts\python.exe' -B -X utf8 scene_algorithm_tasks/tools/render_videos.py --watch
```

录制进程有独占锁，已在运行时无需重复启动。

[Prompt、调用轨迹与修改文件展示](CASE_VIEWER.md)：每个模型×任务均可在页面内查看实际输入、事件详情及代码差异。
