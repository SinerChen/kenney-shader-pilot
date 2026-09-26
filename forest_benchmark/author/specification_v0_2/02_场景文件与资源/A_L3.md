# A_L3｜原场景文件、输入与绑定清单

**作者侧规划，路径未核验/文件尚未随包提供。** 本页区分原工程查找线索与Codex要新建的任务文件。

## 1. 场景职责

将前级灼烧、焦化及前沿余烬接入指定森林树木。在相机远近切换、目标暂时离开画面以及多个实例并存时，维持每棵树自己的灼烧状态和发射历史；保留原植被运动、轮廓和非目标树木。

前级从A_L2完整封存solution复制。场景环境换为净化后的完整原森林，不把合成L2舞台当L3。对于没有原生挂载的资源，按[工程组织](02_L3完整工程组织与权限.md)标constructed_fixture，不能冒称native。

## 2. 原文件线索及绑定门禁

- `Scripts/Import/Tree_LOD.gd`：只作待查线索。
- `Materials/Tree branch LOD.tres`：只作待查线索。

报告只读到导入脚本和 LOD 材质片段；哪些模型绑定该脚本、最终实例层级、真实切换距离及全部活动材质均待核验。300/500 只是既有报告中的脚本值，不作为运行时真值。

1. 同一完整提交中至少找到一类真实具有两个可观察表示的目标树，记录所有生效表面/材质和切换区间。
2. 确认目标逻辑根节点、参考空间、实例变换和中性发射锚点；初版锚点选在实际不受局部顶点风变形的稳定枝干区域，不能冻结全森林风动。
3. 确认共享资源的非目标树作为对照，记录原裁切轮廓、风动、阴影及 LOD 基线。若无法找到合适目标则阻塞 native 发布。

填写[本题source_binding模板](source_bindings/A_L3.template.json)；实际路径、NodePath、表面索引、活动材质、共享消费者、原行为和证据必须齐全。模板null不是授权猜值。

## 3. 新建的任务文件

以下相对路径在`starters/A_L3/`根内。共同需要：`fixture/entry.tscn`、`fixture/scene_access.gd`、`fixture/adapter_base.gd`、`public/task.json`、`public/api.md`、`public/scene_inventory.json`、`public/scene_files.json`、`public/permissions.json`、`public/source_context.json`及继承的`solution/effect.tscn/adapter.gd`。不得把原场景路径整体加前缀而不修复并验证res引用。

| 需要新建的目标路径 | 职责和允许内容 |
| --- | --- |
| public/targets.json | 目标逻辑根、object_id、参考系、授权表面范围；不附私有 LOD 配对答案。 |
| assets/task_inputs/A_L3/emitter_anchors.bin | 经许可选定稳定枝干上的中性锚点，附单位与参考系。 |
| public/burn_ember_config.json | 沿用 A_L1/A_L2 参数及合法域；不含出生答案。 |

这些文件必须由Codex实际创建并导入验证。本包不含任何.tscn、第三方纹理或GPU解。公共输入不能含已求出的H/光透射/源投影/捕获答案。源角色分类采用source_context、inherited_solution、neutral_input、public_fixture；作者参考/判断信息不可导出。

## 4. 权限矩阵

| 类别 | 要求 |
| --- | --- |
| 模型可写 | solution/**、scratch/**；生成缓存由工具管理 |
| 授权运行时操作 | 在目标实例内绑定 solution 中的新材质/实例参数和余烬子节点；保留原风动、裁切、LOD 与非目标消费者。 |
| 受保护 | 修改源树模型、重命名导入依赖节点、改变 LOD 阈值/可见性、共享资源全局改写、改环境/相机。 |
| 作者测试控制 | 仅公开合法域内的相机、事件和参数干预；具体序列私有 |
| 新建测试对象 | 必须记录为作者干预，不替换真实核心场景绑定 |

权限要落实到确切object/property/surface路径，而不是整个SceneTree可写。原文件保持只读，新绑定引用solution资源。隔离测试检查共享资源和全局状态，不只看文件diff。

## 5. 摄像、状态与回归

至少近景、过渡前后、远景、离屏返回、共享资源对照五类采集；原场景存在的运动使用同一模拟时刻比较。

每次采集真实输出：logical_burn_state, active_representation_materials, birth_and_particle_state, protected_tree_runtime_snapshot。保留原始场景、关新增显示但保留配置、detach恢复三类基线。新效果的合法遮挡/反射影响按规则判断，不要求全图像素不变。

## 6. 放行

确认source lock、所有目标路径及许可、实际原始数据/渲染行为、空接口边界、前级继承hash、原始GPU采集、正负对照、保护检查、干净导入和预算。状态从SOURCE_UNVERIFIED到SOURCE_BOUND_RUNTIME_VERIFIED必须有证据；完成本页不等于已运行。
