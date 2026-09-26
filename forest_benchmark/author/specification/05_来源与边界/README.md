# 来源与证据边界（作者侧）

## 本包主要依据

1. 当前对话已经确认的五条 L1→L2 前置任务链及 F01–F06 的映射。
2. [既有森林静态审计](forest_integration_constraints_static_audit.md)：有限源码片段与候选约束，不是六个运行 bug。
3. [结构化审计候选](forest_integration_constraint_candidates.json)：保留未知绑定、未实现检测和来源。
4. [既有算法构想表](shader_algorithm_scenarios.md)：150 技术条目/300 构想的扩展表，原文自己说明未与旧完整清单逐项对照，不能写成已验证实现数据集。

本轮没有重新取得完整森林 checkout，也没有在 Godot 运行上述任务。源审计中的固定 diff 提交和 main 配置不能自动合并成一个完整同提交工程。所有新建 starter 路径是计划路径，不是已发现源路径。

## 本轮核对的技术参考（2026-09-26 读取）

- R01 Godot 官方 Screen-reading shaders：三维屏幕输入的阶段限制与深度数据。https://docs.godotengine.org/en/stable/tutorials/shaders/screen-reading_shaders.html
- R02 Godot 官方 Using compute shaders：计算路径与 GPU 资源/回读能力。https://docs.godotengine.org/en/stable/tutorials/shaders/compute_shaders.html
- R03 PBRT 4e Specular Reflection and Transmission：折射与介质反射的背景。https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission
- R04 PBRT 4e The Equation of Transfer：透射和体积贡献积分的背景。https://pbr-book.org/4ed/Light_Transport_II_Volume_Rendering/The_Equation_of_Transfer

这些资料仅解释引擎/图形学机制，不证明原森林已具有某项失败，也不意味着本包每个近似公式来自该页面。具体灼烧规则、干燥函数、网格格式、采样、近似折射投影和评分流程是本次作者侧规格选择。stable 文档会变化，Codex 必须在锁定引擎后引用相应版本，不默认当前最新版本与源工程兼容。

## 许可

未打包上游森林模型、贴图或代码。后续复用真实资产须逐项查许可、署名、可再分发范围，记录在 asset manifest。合成中性输入应声明 generated；不得伪造上游来源或把完整效果当作普通输入资源。
