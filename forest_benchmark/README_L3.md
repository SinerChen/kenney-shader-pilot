# L3 场景任务（v0.2）

从 `forest_benchmark_codex_v0_2.zip` 新增 6 道 L3，保留原有 10 道 L1/L2 的题面、起始工程和核心数学。先打开 [检查页面](index.html)，查看题目、可见文件、继承代码、视频和逐项证据。实际完成与未完成项见 [L3 状态](L3_STATUS.md)。

| 任务 | 继承 | 场景作用 |
| --- | --- | --- |
| [A_L3](tasks/A_L3/prompt.md) | A_L2 | 原森林树木各个 LOD 表示的灼烧状态、独立余烬身份与风动保护 |
| [B_L3](tasks/B_L3/prompt.md) | B_L2 | 由原地形实际材质权重决定足迹、湿润的允许区域 |
| [C_L3_R](tasks/C_L3_R/prompt.md) | C_L2 | 复用原天空纹理资源，在局部区域加入云影与雾 |
| [C_L3_S](tasks/C_L3_S/prompt.md) | C_L2 | 与原天空可见云系统共用密度、坐标及时间；当前源绑定阻塞 |
| [D_L3](tasks/D_L3/prompt.md) | D_L2 | 原河流局部坐标、物理流速、世界接触源与泡沫输运 |
| [E_L3](tasks/E_L3/prompt.md) | E_L2 | 原河流法线叠加、涟漪与前后折射层的当前帧捕获 |

C 的两个分支独立继承同一份 C_L2，不相互继承。题目不包含私有测试编号、答案、评分阈值或调用预算。

目前五个起始工程使用完整森林，接入接口保持空实现。页面中的 L3 视频是原场景检查视频，**不是 L3 最终效果**。L3 的合格集成参考、60 组可执行集成测试及对照尚未完成；正式投放关闭。C_L3_S 尚不能确定与所有相机一致的原生世界云场，因此没有用替代场景生成该题工程。

## 原工程与输入

原森林来自本地 `realistic/downloads/forest.zip`，提交为 `ac523ed97ca1719f517cd3968f3ff49d76274baa`。源归档、逐文件哈希、真实节点与活动资源均记录在作者目录。缺失的编辑器地被生成插件已解除挂载，保留全部烘焙实例；Godot 导入兼容设置单独记录。实际运行的是这一归一化版本，不称为未修改的上游工程。

每题保留原 `res://` 根路径和完整上下文。外层 `public/<任务>/scene_files.json` 列出可读原文件；外层 `public/<任务>/permissions.json` 指定可局部绑定的实际表面。只允许写入 `solution/`、`scratch/`。继承的 L2 已裁为本链核心；没有继承 L2 舞台，也没有为 E_L3 提供已完成的后景捕获桥。

外层 `public/<任务>/task.json` 的 `input_files` 指向本题场景输入，包括实际树锚点、地形片区、原纹理类型、河流坐标及物理流速。外层 `io_schema.json` 仅描述字段类型和形状；旧样例文件也只保留类型定义。场景输入已根据原资源选定，但正式误差与可见性校准仍未冻结。

## 已实现入口

在仓库根目录执行，Python 可替换为本机 `D:\shaderagent17_s0_s1\.venv\Scripts\python.exe`。

```powershell
python forest_benchmark/main.py inspect_source
python forest_benchmark/main.py resolve_bindings A_L3
python forest_benchmark/main.py build_l3_starter A_L3
python forest_benchmark/main.py audit_runtime A_L3 --frames 30
python forest_benchmark/main.py run_integration A_L3
python forest_benchmark/main.py package_model_task A_L3 --review --output path/to/new/review
python forest_benchmark/main.py validate_release all
```

`audit_runtime` 只运行封存空接入工程的独立副本，检查导入、源节点变化、解绑恢复并生成 MP4。它拒绝被修改的候选；`run_integration` 当前返回明确的 `NOT_RUN`，不生成虚假的通过率。查看 [逐项状态](L3_STATUS.md) 后再选择命令，不能将这些入口理解为 L3 裁判已经完成。

模型的 `read/write/render` 使用原有 `ModelTools`。`render` 的相机和帧数可由模型按需指定，宿主注入渲染执行器。未配置执行器时返回 `INFRA_ERROR`。本机封存工程也可设置调试相机：

```python
from forest_benchmark.main import capture_visuals

capture_visuals("A_L3", frames=30, camera={
    "position": [40, 2, -20], "look_at": [43, -3, -26]
})
```

## 作者侧复核

```powershell
python forest_benchmark/author/l3_regression.py
python forest_benchmark/author/verify_l3_starters.py
python -m unittest discover -s forest_benchmark/tests -p "test_*.py" -v
python forest_benchmark/author/make_report.py
python forest_benchmark/author/check_review_page.py
python forest_benchmark/author/check_l3_page.py
```

每个分支已独立对封存 L2 执行 20 个数值与 5 个联动预检，总计 120 + 30；这是前级预检，不是 L3 候选回归。完整源绑定、导出记录、日志、视频和未执行的集成设计保存在 `author/`，不交给求解模型。GitHub 仅保留 A_L3 完整工程；其余四个可运行分支保存为差异文件，恢复方式见 [上传说明](GITHUB_CONTENTS.md)。

本次没有调用求解模型，原实验仍保持暂停。
