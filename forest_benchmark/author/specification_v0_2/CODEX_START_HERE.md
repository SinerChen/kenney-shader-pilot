# 给Codex的开始指令｜v0.2（含L3）

你是benchmark作者和实现者，不是被测模型。本包定义10项L1/L2与6项L3，共5条算法链。不要将作者参考、测试输入/答案或本包整体交给求解模型；不要自行启动正式模型评测。

## 首先读取

根README → 04的L3任务总览与迁移 → 01的通用数值规范及L3检测规范 → 02的最小工程、完整工程组织与源绑定核验 → 04的L3门禁。检查本地Godot/GPU/源工程权限，记录实际环境到author/status.md。

已有v0.1实现时记录哈希并运行前级回归，不能因为包升级改写旧数学。尚未实现则按原五链L1→L2制作；L3源审计可并行，但实际接入应继承封存L2。

## 构建顺序

1. 取得完整同提交森林，完成源锁定、许可、固定引擎导入及原基线。填写6份source_binding模板。遇到缺绑定/缺可行性标该题BLOCKED_SOURCE；其他题继续。
2. 按原规范创建或回归A–E的L1/L2：独立CPU、真实GPU、100组数值覆盖、25组联动及正确/错误对照。数值格式和query必须与画面一致。
3. A_L2→A_L3；B_L2→B_L3；D_L2→D_L3；E_L2→E_L3。C_L2分别→C_L3_R和C_L3_S，两分支同起始哈希、独立构建及评测。不能把R结果装进S。
4. 每个L3先做作者合格接入与可观测oracle，补齐10组正式集成输入/阈值/反例，再回归20个前级数值和5组前级联动。实际原材质、资源、时钟、坐标和捕获必须运行检查。
5. 从净化基线导出完整原上下文starter：原res根路径不乱搬，原文件默认只读，授权绑定只涉及指定属性。保留合法既有功能，移除本级新增目标答案。E_L3不能带上L2作者捕获fixture。
6. 冻结公开目标、原场景语义、算法扩展、权限、容差、相机/时间、AA和预算。只给求解模型单题Prompt+公共配置+合法场景输入+指定前级产物。
7. 运行源门禁S0–S3和评测T0–T4、干净重导入及泄露审计，按真正通过的任务子集生成release。未运行不填通过率。

## 需要实际实现的入口

沿用build_starter、run_reference、run_numeric、run_interactions、capture_visuals、audit_submission、package_model_task、validate_release；新增inspect_source、resolve_bindings、build_l3_starter、run_integration、audit_runtime。可统一为一个CLI子命令。

这些只是要实现的逻辑接口，本包没有Godot执行脚本。必须在最终README给出你真正实现并运行过的命令。唯一本包已经可运行的工具是tools/validate_spec_package.py，它只校验文档。

## 每个L3交付

完整源绑定/归一化记录、允许原上下文/移除目标答案清单、CPU与GPU合格参考、真实状态和帧采集、10组私有集成用例及公开开发样例、前级20+5回归、错误对照、合法替代、静态/运行时审计、净化starter、冻结公开配置和已组装Prompt、可复现运行报告。

## 不确定性和边界

不凭旧报告创造确切路径/通道/云场高度；不把未挂载River改挂后称原工程已有。F04缺少唯一有限世界映射必须阻塞native，可单列构造实验。F06若当前后端无可行捕获参考，先解决作者环境，不给模型零分。

无Godot/GPU或资源：记NOT_RUN/INFRA_ERROR并保留阻塞详情。规范冲突：提出具体版本差异并停在该题门禁，不暗改测试。数值/视觉阈值只用基线和参考校准，不按某模型调节。

## 最终汇报

逐题给spec/source_binding/CPU/GPU/numeric_regression/coupling_regression/integration/visual/protection/starter/release状态、真实环境/命令/日志/证据。区分SPEC_VALIDATED、RUNTIME_VALIDATED、RELEASE_READY。6份L3文档完成不代表6个真实工程已经可以投放。
