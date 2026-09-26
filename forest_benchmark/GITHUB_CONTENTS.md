# GitHub 内容

本次上传当前已有内容，不补做尚未完成的算法参考或验收。题库共 16 道题面：10 道 L1/L2、6 道 L3 定义；`C_L3_S` 仍为源绑定阻塞状态。实验状态文件是提交时快照，不会随本机进程实时更新。

包含题面、外层 public 配置、10 个 L1/L2 起始工程、作者实现与测试数据、现有报告和视频、S1/P3 实验代码、已产生的模型输入、轨迹及修改文件。`author/` 为作者侧资料，不应作为模型工作目录。

L3 只上传一份完整工程：[`starters/A_L3/`](starters/A_L3/)，约 688 MiB，保留原生场景、模型、纹理、许可证及资产来源说明。它是当前空接入起始工程，包含封存的前级实现；现有 L3 视频展示原场景，不代表 L3 目标效果已完成。运行时还需要同级的 [`starters/public/A_L3/`](starters/public/A_L3/)。

`B_L3`、`C_L3_R`、`D_L3`、`E_L3` 保留完整题面、public 配置以及 [`starters/l3_overlays/`](starters/l3_overlays/) 中的差异文件和逐文件 SHA-256。克隆后可恢复为与当前工程内容一致的文件集合：

```powershell
python forest_benchmark/tools/restore_l3.py all
```

该命令复用 `A_L3` 的原场景资产，不联网、不调用模型，也不覆盖已有任务工程。`C_L3_S` 没有可恢复的工程。Godot 为 4.6.1；Python 依赖见 `requirements.txt`，模型运行另依赖原宿主环境。

浏览现有题目、报告及视频可打开 [`index.html`](index.html)。查看本次模型实验的 prompt、轨迹和文件变化：

```powershell
python forest_benchmark/experiment/serve.py --port 8772
```

随后访问 `http://127.0.0.1:8772/experiment/index.html`。此命令只读取已保存的实验记录，不启动模型调用。

Git 中排除了 `.godot`、Python/GPU 缓存、密钥、进程锁、恢复用 checkpoint，以及 author、exports、runtime、render_runtime 中重复的原生工程副本。保留现有证据文件中的历史路径；被排除的运行副本路径可能仅在原机器上存在。L3 原始来源和归一化改动见 [`author/forest_source_lock.json`](author/forest_source_lock.json)，当前完成范围见 [`L3_STATUS.md`](L3_STATUS.md)。
