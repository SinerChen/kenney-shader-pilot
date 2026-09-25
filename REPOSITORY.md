# 仓库内容与恢复

本仓库保存 Kenney 场景试点、森林草地实验，以及五组十五题的场景算法实验代码、题面、P3 提示词、HTML 查看器和检查脚本。

本次提交还保存已经结束的场景算法实验：真实输入与调用轨迹、初始候选、当前候选、结果、观测截图，以及已录制的连续 MP4。结果状态不代表通过独立效果验收。实验继续运行时，GitHub 上的内容是提交时的快照。

`.env`、登录凭据、Python/Godot 缓存、下载压缩包、引擎程序、运行锁、重复渲染工作目录和大型逐帧 `samples.json` 不提交。此前独立的 `forest_grass_lab/runs/` 暂不归档。GitHub 不自动运行模型，也不部署此本地查看器。

## 查看已保存实验

使用 Python 3.11 或更新版本，在仓库根目录运行：

```powershell
python scene_algorithm_tasks/serve.py --port 8771
```

打开 <http://127.0.0.1:8771/index.html>，可查看视频、Prompt、调用轨迹和修改文件。网页派生索引会在本地重建。被排除的逐帧采样文件不能从下载链接直接访问；轨迹中已经返回给模型的读取内容仍保留。仅查看结果不需要 Godot 或 API 密钥。

## 恢复大型场景资源

为了控制仓库体积，`external_assets.json` 列出的原始大型资源从 Git 中排除。清单包含原压缩包与每个文件的 SHA-256；本地修改过、无法与原始包匹配的文件不会被此机制排除。

```powershell
python tools/restore_external_assets.py
python tools/restore_external_assets.py --check-only
```

恢复脚本只补齐缺失资源，并校验现有文件，不覆盖仓库里的场景或脚本改动。上游分支如果已经变化而压缩包校验不匹配，需要提供清单中记录的原始压缩包到 `realistic/downloads/`；脚本不会悄悄采用新版资源。

原生渲染使用 Godot 4.6.1。引擎不包含在 Git 中，Windows 版本应放在 `tools/godot/Godot_v4.6.1-stable_win64.exe`。各上游资产的许可证和来源保留在项目目录及 `sources.json`、`realistic/sources.json`。

运行模型实验还需要安装其 Python 依赖，并按 `scene_algorithm_tasks/experiment/config.json` 中的环境变量名设置 API 密钥。部分既有实验脚本含本机绝对路径，换机需按对应实验说明配置；不要上传 `.env`。现有 runner 的默认凭据回退路径属于原本机配置。
