# 给 Codex 的开始指令

你现在是 **benchmark 作者与实现者**，不是被测模型。请按本包构建 Godot 最小场景、算法参考、测试器和干净任务工作区。不要直接把作者参考解交给求解模型，也不要自行启动正式模型评测。

## 首次执行

先阅读根 README，再读 `04_作者侧流程与评测/00_决策与适用范围.md`、`01_算法实现与测试/00_通用实现与测试规范.md`、`02_场景文件与资源/00_工程布局与文件权限.md`。检查可用 Godot、GPU、数据权限；把精确版本和阻塞项写入 author/status.md。

本包是 MD 规格，未包含可运行 Godot 工程。你需要创建文件；不要在不存在的目录上声称运行成功。所有源路径的 verified/unknown 状态按来源报告保留。

## 构建顺序

1. 固定本地工作根、环境和约定；创建 CPU 参考/私有裁判/模型 starter 的分离目录。先验证 float GPU 输出和 E_L2 后景捕获能力。
2. 按 A_L1→A_L2、B_L1→B_L2、C_L1→C_L2、D_L1→D_L2、E_L1→E_L2 的依赖实施；相互独立的链可以并行。L1/L2 不必等真实森林绑定补齐。
3. 每题先做独立 CPU 参考与解析检查，再做 GPU 合格参考、实际显示与状态回读；制作 10 个正式数值组、独立开发样例和错误对照。L2 另制作 5 个干预测试并回归前级。
4. 新建中性最小场景和只读桥；从白名单导出没有目标解的 starter。E_L2 桥只做层组织，不替模型实现光学/波动。
5. 标定数值/图像/交互容差、拍摄条件、资源预算，补齐 public/task.json。使用正确与错误对照校准，不用被测模型成绩调阈值。
6. 验证文件/运行时保护、GPU 核心与输出一致性、干净重导入、秘密隔离，再组装单任务 Prompt。只在全部 release gate 通过后标记可投放。

## 必须交付的实现产物

每题：CPU 参考、GPU 参考、测试输入生成器、正式私有输入/答案、公开样例、至少列明的错误对照、检测脚本、中性 starter、公共 API/契约/资源清单、参数与预算 lock、运行报告和可重放证据。任务 ID 使用本包，不临时改名；算法修改必须更新版本和 changelog。

需要生成的入口命令统一由你实现为以下逻辑工具，并在最终 README 写出可实际执行的参数/示例：build_starter(task)、run_reference(task)、run_numeric(task,submission)、run_interactions(task,submission)、capture_visuals(task,submission)、audit_submission(task,submission)、package_model_task(task)、validate_release(task)。这些名称是要实现的接口，不是本包已提供的可执行命令；你可以用一个 CLI 的子命令实现，避免过度抽象。

## 遇到不确定项

Godot/GPU 不可用：标 NOT_RUN/INFRA_ERROR，保留可执行产物与下一步，不伪造截图和通过率。数值定义有冲突：提出具体差异，停在该题发布门禁，不暗选另一公式。上游资产不可用：合成 L1/L2 可以继续；真实 L3 标阻塞，不冒称原场景。

F01–F06 的 L3 本轮只保留映射和核验，未经新的目标/绑定/裁判确认不扩展为正式任务。不要把 F03/F04 共用的 C 链重复计数。

## 最终汇报

逐题给出 spec / CPU / GPU / numeric / interaction / visual / protection / starter / release 状态、真实命令、环境、失败日志及下一步。区分 SPEC_VALIDATED、RUNTIME_VALIDATED 和 RELEASE_READY。不要只写“已完成所有文件”。
