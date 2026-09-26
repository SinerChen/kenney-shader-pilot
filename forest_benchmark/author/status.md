# 作者侧状态

生成：2026-09-27T01:31:18+08:00

已完成 5 条链、10 道 L1/L2 题的本地作者侧制作与验证。正式投放状态为 **BLOCKED_RELEASE**。

[题目与视频检查页](../index.html) · [使用说明](../README.md) · [机器可读报告](../VALIDATION.json)

已执行：新增数值 100/100，继承回归 50/50，合法实现变体 100/100，因果数值 25/25，因果图像响应 25/25，错误变体拒绝 49/49。

CPU 解析锚点测试 19/19，read/write/render 工具测试 10/10。10 个起始工程均完成干净导入、空实现检查、文件保护与白名单导出检查。

| 题目 | GPU 数值 | 最大绝对误差 | 继承回归 | 因果数值 / 图像 | 错误变体拒绝 | 视频 |
| --- | --- | --- | --- | --- | --- | --- |
| [A_L1 · 程序灼烧与焦化](../tasks/A_L1/prompt.md) | 10/10 | 2.98e-07 | — | — | 4/4 | [主视角](reports/A_L1/visual/effect.mp4) · [斜视角](reports/A_L1/oblique/effect.mp4) |
| [A_L2 · 灼烧前沿驱动的旋涡余烬](../tasks/A_L2/prompt.md) | 10/10 | 2.44e-05 | 10/10 | 5/5 · 5/5 | 5/5 | [主视角](reports/A_L2/visual/effect.mp4) · [斜视角](reports/A_L2/oblique/effect.mp4) |
| [B_L1 · 持久化脚印压痕与 POM](../tasks/B_L1/prompt.md) | 10/10 | 3.34e-08 | — | — | 5/5 | [主视角](reports/B_L1/visual/effect.mp4) · [斜视角](reports/B_L1/oblique/effect.mp4) |
| [B_L2 · 压痕约束的湿润扩散与干燥](../tasks/B_L2/prompt.md) | 10/10 | 1.46e-07 | 10/10 | 5/5 · 5/5 | 5/5 | [主视角](reports/B_L2/visual/effect.mp4) · [斜视角](reports/B_L2/oblique/effect.mp4) |
| [C_L1 · 三维云密度驱动的地面云影](../tasks/C_L1/prompt.md) | 10/10 | 7.15e-07 | — | — | 5/5 | [主视角](reports/C_L1/visual/effect.mp4) · [斜视角](reports/C_L1/oblique/effect.mp4) |
| [C_L2 · 云遮光约束的薄雾与体积光](../tasks/C_L2/prompt.md) | 10/10 | 3.2e-07 | 10/10 | 5/5 · 5/5 | 5/5 | [主视角](reports/C_L2/visual/effect.mp4) · [斜视角](reports/C_L2/oblique/effect.mp4) |
| [D_L1 · 双相位 Flow Mapping 水纹](../tasks/D_L1/prompt.md) | 10/10 | 2.14e-06 | — | — | 5/5 | [主视角](reports/D_L1/visual/effect.mp4) · [斜视角](reports/D_L1/oblique/effect.mp4) |
| [D_L2 · 固定接触源的泡沫输运](../tasks/D_L2/prompt.md) | 10/10 | 1.91e-05 | 10/10 | 5/5 · 5/5 | 5/5 | [主视角](reports/D_L2/visual/effect.mp4) · [斜视角](reports/D_L2/oblique/effect.mp4) |
| [E_L1 · 透明水滴/水膜的折射与吸收](../tasks/E_L1/prompt.md) | 10/10 | 1.83e-06 | — | — | 5/5 | [主视角](reports/E_L1/visual/effect.mp4) · [斜视角](reports/E_L1/oblique/effect.mp4) |
| [E_L2 · 交互涟漪与前景折射的正确组合](../tasks/E_L2/prompt.md) | 10/10 | 7.44e-08 | 10/10 | 5/5 · 5/5 | 5/5 | [主视角](reports/E_L2/visual/effect.mp4) · [斜视角](reports/E_L2/oblique/effect.mp4) |

## 如何理解这些结果

数值判定读取同步后的 GPU float32 原始缓冲，与独立 float64 CPU 参考比较。显示检查读取实际绑定材质资源；前后景折射检查还核对当前帧捕获纹理与层掩码。截图、MP4 不作为数值替代。

25 组因果检查同时记录受控参数变化、应改变的结果和指定不变量。图像响应通过表示存在正确的依赖证据，不等同于最终美观程度通过。

5 份 L1-only gold 前级参考已逐份通过 10 组数值与渲染检查。L2 的 self_predecessor 与 gold_predecessor 由导出器分开记录；不向模型继承作者私有分数或对话。

## 环境与证据

Godot 4.6.1 / Forward+ / Vulkan；AMD Radeon 780M Graphics；驱动 32.0.13046.2004；Python 3.14.4。每题 2 段 6 秒视频，640×360、15 fps。

- [逐组 max / mean / p95 误差](reports/error_statistics.json)
- [继承与合法变体](reports/variants.json)
- [错误变体结果](reports/negative_controls.json)
- [因果图像证据](reports/visual_coupling.json)
- [最终渲染与 GPU 一致性](reports/final_checks.json)
- [干净工程与导出检查](reports/starter_validation.json)
- [大整数事件 ID 回归](reports/large_event_ids/report.json)
- [单元测试](reports/unit_tests.json)
- [性能观测](reports/profile_summary.json)

性能数据仅为本机观测，含参考调度及显示所需的回读/上传；Viewport GPU 计时不包含本地 RenderingDevice 的计算队列，不能作为总 GPU 耗时或性能通过结论。

## 未完成的投放条件与限制

- 正式模型实验未启动，原实验保持暂停；没有模型成绩或调用轨迹。
- L1/L2 使用合成最小场景；v0.2 的 6 个 L3 及原生源绑定状态单独见 L3_STATUS.md。
- read/write 路径限制和运行时快照不等于 OS 沙箱。外部候选执行器尚未接入，默认拒绝执行任意候选。
- 图像响应、不变量、资源绑定检查已运行；VLM 审美评分、评分模型和阈值仍未校准。
- 推理与资源预算尚未锁定，正式模型导出门禁保持关闭；--review 仅用于人工检查。
- 错误变体含部分故障代理，例如方向性扩散算子模拟串行原地更新偏差；不是每种作弊实现的穷尽证明。
- 合法实现变体主要改变线程组、噪声多项式求值和 POM 粗搜索，不代表已覆盖全部合法解法。
- 当前容限为 atol=rtol=2e-4，布尔值精确匹配；跨 GPU 的最终容限仍待锁定。

私有案例、参考、原始日志与视频保存在 author/，该目录已从 Git 和模型包排除。公开页面只适合在这份完整的本地目录中查看，单独复制页面不会携带视频。


Additional review evidence:

- [HTML playback and link checks](reports/review_page/report.json)
- [Review exports and inheritance sources](reports/review_exports.json)


[L3 v0.2 status](../L3_STATUS.md): 6 definitions, 5 native blank starters; integration NOT_RUN.
