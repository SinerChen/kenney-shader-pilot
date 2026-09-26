# B_L3｜原场景文件、输入与绑定清单

**作者侧规划，路径未核验/文件尚未随包提供。** 本页区分原工程查找线索与Codex要新建的任务文件。

## 1. 场景职责

将前级脚印压痕和湿润扩散接入指定森林地形区域。只在题目授权的地表材质区域产生压痕和湿润状态，按公开边界规则阻止向禁止区域扩散，同时保留原地形分层外观、法线和非目标材质。

前级从B_L2完整封存solution复制。场景环境换为净化后的完整原森林，不把合成L2舞台当L3。对于没有原生挂载的资源，按[工程组织](02_L3完整工程组织与权限.md)标constructed_fixture，不能冒称native。

## 2. 原文件线索及绑定门禁

- `Materials/Terrain 1.tres`：只作待查线索。
- `Blend8 splat.gdshader（报告仅给引用名，完整路径待查）`：只作待查线索。

尚未核验完整混合 Shader、各纹理数组层的语义和该材质的实际场景绑定；不预设任何 splat 通道等于泥土。

1. 确认目标地形活动材质及完整依赖，能求出最终混合后的有效层贡献而非仅原始 splat 值。
2. 作者人工核验泥土/石质等语义，将允许层标签及判定阈值公开；不得把猜测通道当成真值。
3. 选择具有授权与禁止区域的近水平、可使用单值米制局部 chart 的真实地形片区，固定曲率/倾斜范围和投影规则。
4. 检查原材质与高度/法线合成可保留；不能以新建纯色平面覆盖真实地形来充当 native L3。

填写[本题source_binding模板](source_bindings/B_L3.template.json)；实际路径、NodePath、表面索引、活动材质、共享消费者、原行为和证据必须齐全。模板null不是授权猜值。

## 3. 新建的任务文件

以下相对路径在`starters/B_L3/`根内。共同需要：`fixture/entry.tscn`、`fixture/scene_access.gd`、`fixture/adapter_base.gd`、`public/task.json`、`public/api.md`、`public/scene_inventory.json`、`public/scene_files.json`、`public/permissions.json`、`public/source_context.json`及继承的`solution/effect.tscn/adapter.gd`。不得把原场景路径整体加前缀而不修复并验证res引用。

| 需要新建的目标路径 | 职责和允许内容 |
| --- | --- |
| public/terrain_task.json | 目标 chart、语义层标签、tau_allow、物理单位、授权与禁止规则；不含求好的 H。 |
| assets/task_inputs/B_L3/foot_stamp.bin | 与 B_L1 兼容的中性鞋底输入及元数据。 |
| public/terrain_events.json | 公开开发接触/注水事件；正式序列私有。 |

这些文件必须由Codex实际创建并导入验证。本包不含任何.tscn、第三方纹理或GPU解。公共输入不能含已求出的H/光透射/源投影/捕获答案。源角色分类采用source_context、inherited_solution、neutral_input、public_fixture；作者参考/判断信息不可导出。

## 4. 权限矩阵

| 类别 | 要求 |
| --- | --- |
| 模型可写 | solution/**、scratch/**；生成缓存由工具管理 |
| 授权运行时操作 | 在指定地形表面绑定 solution 中保留原混合的局部材质扩展；向其提供新深度/湿度场和局部效果参数。 |
| 受保护 | 改原 splat/纹理数组/地形几何、改碰撞、全局环境变化、覆盖禁止材质区域、建立替身地形遮住原物体。 |
| 作者测试控制 | 仅公开合法域内的相机、事件和参数干预；具体序列私有 |
| 新建测试对象 | 必须记录为作者干预，不替换真实核心场景绑定 |

权限要落实到确切object/property/surface路径，而不是整个SceneTree可写。原文件保持只读，新绑定引用solution资源。隔离测试检查共享资源和全局状态，不只看文件diff。

## 5. 摄像、状态与回归

层内部、禁止区内部、软边界和斜视 POM；增加湿痕到达边界的时序和关效果材质回归。

每次采集真实输出：original_effective_layer_weights, submitted_support_domain, depth_wetness_and_boundary_flux, terrain_material_protection。保留原始场景、关新增显示但保留配置、detach恢复三类基线。新效果的合法遮挡/反射影响按规则判断，不要求全图像素不变。

## 6. 放行

确认source lock、所有目标路径及许可、实际原始数据/渲染行为、空接口边界、前级继承hash、原始GPU采集、正负对照、保护检查、干净导入和预算。状态从SOURCE_UNVERIFIED到SOURCE_BOUND_RUNTIME_VERIFIED必须有证据；完成本页不等于已运行。
