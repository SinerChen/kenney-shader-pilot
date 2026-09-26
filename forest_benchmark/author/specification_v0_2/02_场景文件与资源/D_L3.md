# D_L3｜原场景文件、输入与绑定清单

**作者侧规划，路径未核验/文件尚未随包提供。** 本页区分原工程查找线索与Codex要新建的任务文件。

## 1. 场景职责

将前级双相位水纹与泡沫输运接入选定真实河流区域。接触位置按世界空间关系确定，生成后的泡沫沿规定的物理流场移动；改变图案平铺或水域实例变换时，不能破坏接触锚点和物理速度。

前级从D_L2完整封存solution复制。场景环境换为净化后的完整原森林，不把合成L2舞台当L3。对于没有原生挂载的资源，按[工程组织](02_L3完整工程组织与权限.md)标constructed_fixture，不能冒称native。

## 2. 原文件线索及绑定门禁

- `Shaders/River.tres`：只作待查线索。

报告读取到 River 材质中时间偏移 UV 的片段，但未确认其 Main.tscn 挂载、目标节点、UV/变换、区域有效性和原速度含义。

1. 在冻结源工程中验证 River 真实挂载和活动材质；未挂载时禁止宣称原森林已有河段，constructed 版本另行标记。
2. 选择可以用正交米制表面 chart 表达的真实水域片区，验证几何、有效水域和原材质数据流。
3. 原流纹速度不能自动当物理速度；作者为本题公开给定 m/s 流场和基/单位定义，记录其为任务输入而非上游真值。
4. 确认可在保留原折射/透明/其他材质职责时替换被考流纹子功能；选定接触对象/锚点及不接触干扰对象。

填写[本题source_binding模板](source_bindings/D_L3.template.json)；实际路径、NodePath、表面索引、活动材质、共享消费者、原行为和证据必须齐全。模板null不是授权猜值。

## 3. 新建的任务文件

以下相对路径在`starters/D_L3/`根内。共同需要：`fixture/entry.tscn`、`fixture/scene_access.gd`、`fixture/adapter_base.gd`、`public/task.json`、`public/api.md`、`public/scene_inventory.json`、`public/scene_files.json`、`public/permissions.json`、`public/source_context.json`及继承的`solution/effect.tscn/adapter.gd`。不得把原场景路径整体加前缀而不修复并验证res引用。

| 需要新建的目标路径 | 职责和允许内容 |
| --- | --- |
| public/river_domain.json | 真实目标逻辑节点、参考域、坐标/物理单位和变换范围；不直接提供已变换源坐标。 |
| assets/task_inputs/D_L3/physical_flow.bin | 本题明确给定的物理速度场及元数据，不声称来自原流纹速度。 |
| public/contact_objects.json | 接触/干扰对象和公开锚点规范、距离阈值。 |

这些文件必须由Codex实际创建并导入验证。本包不含任何.tscn、第三方纹理或GPU解。公共输入不能含已求出的H/光透射/源投影/捕获答案。源角色分类采用source_context、inherited_solution、neutral_input、public_fixture；作者参考/判断信息不可导出。

## 4. 权限矩阵

| 类别 | 要求 |
| --- | --- |
| 模型可写 | solution/**、scratch/**；生成缓存由工具管理 |
| 授权运行时操作 | 目标材质的流纹子功能和泡沫显示可在 solution 中派生后绑定；允许必要的局部事件/状态资源。 |
| 受保护 | 改水域几何以迎合源、改相机或全局光照、删除原光学职责、移动非授权对象、用滚动UV定义世界接触。 |
| 作者测试控制 | 仅公开合法域内的相机、事件和参数干预；具体序列私有 |
| 新建测试对象 | 必须记录为作者干预，不替换真实核心场景绑定 |

权限要落实到确切object/property/surface路径，而不是整个SceneTree可写。原文件保持只读，新绑定引用solution资源。隔离测试检查共享资源和全局状态，不只看文件diff。

## 5. 摄像、状态与回归

接触近景、俯视源与尾迹、图案参数干预、实例变换对照及原水体关效果基线。

每次采集真实输出：world_and_chart_sources, flow_physical_units, actual_foam_state_and_pattern_uv, river_material_protection。保留原始场景、关新增显示但保留配置、detach恢复三类基线。新效果的合法遮挡/反射影响按规则判断，不要求全图像素不变。

## 6. 放行

确认source lock、所有目标路径及许可、实际原始数据/渲染行为、空接口边界、前级继承hash、原始GPU采集、正负对照、保护检查、干净导入和预算。状态从SOURCE_UNVERIFIED到SOURCE_BOUND_RUNTIME_VERIFIED必须有证据；完成本页不等于已运行。
