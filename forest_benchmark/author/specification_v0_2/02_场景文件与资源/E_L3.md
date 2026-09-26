# E_L3｜原场景文件、输入与绑定清单

**作者侧规划，路径未核验/文件尚未随包提供。** 本页区分原工程查找线索与Codex要新建的任务文件。

## 1. 场景职责

将前级涟漪状态加入指定原河流，并在前景水滴/水膜中观察当前河流及涟漪结果。模型需自行组织本级必要的渲染输入，保持当前帧一致、遮挡和原水体效果，不用削弱折射掩盖问题。

前级从E_L2完整封存solution复制。场景环境换为净化后的完整原森林，不把合成L2舞台当L3。对于没有原生挂载的资源，按[工程组织](02_L3完整工程组织与权限.md)标constructed_fixture，不能冒称native。

## 2. 原文件线索及绑定门禁

- `Shaders/River.tres`：只作待查线索。

尚未核验原材质在 Main.tscn 的活动挂载、渲染后端、透明/屏幕输入及前后层捕获能力。没有原水体实际参与时不能用新建测试平面代替 native 任务。

1. 确认真实原水体及其屏幕读取/透明流程，在冻结后端实测哪些内容可进入前景输入。
2. 先实现至少一份原水体+前景的合法可运行参考，支持原水体透明/流动和当前tick采集；不能以设置某API就假定可捕获。
3. 冻结一层前景+一层原水体+不透明背景的范围、路径长度和相机域，验证无遮挡/遮挡的正确参考。
4. 读清原水体法线空间，确认 E2 波法线能以零扰动恒等的方式组合并保持原光学。

填写[本题source_binding模板](source_bindings/E_L3.template.json)；实际路径、NodePath、表面索引、活动材质、共享消费者、原行为和证据必须齐全。模板null不是授权猜值。

## 3. 新建的任务文件

以下相对路径在`starters/E_L3/`根内。共同需要：`fixture/entry.tscn`、`fixture/scene_access.gd`、`fixture/adapter_base.gd`、`public/task.json`、`public/api.md`、`public/scene_inventory.json`、`public/scene_files.json`、`public/permissions.json`、`public/source_context.json`及继承的`solution/effect.tscn/adapter.gd`。不得把原场景路径整体加前缀而不修复并验证res引用。

| 需要新建的目标路径 | 职责和允许内容 |
| --- | --- |
| public/optical_layer_scope.json | 前景/原水体/不透明对象的目标与关系、合法相机/路径长度域；不是完成捕获方案。 |
| public/wave_region.json | 原水面局部chart、波网格与法线框架/扰动范围。 |
| assets/task_inputs/E_L3/front_geometry.tres | 中性前景水膜/水滴几何，不含折射实现。 |
| fixture/l3_input_socket.gd | 空的公开输出/绑定槽，不提供完成的后景捕获；缺输出应报未实现。 |

这些文件必须由Codex实际创建并导入验证。本包不含任何.tscn、第三方纹理或GPU解。公共输入不能含已求出的H/光透射/源投影/捕获答案。源角色分类采用source_context、inherited_solution、neutral_input、public_fixture；作者参考/判断信息不可导出。

## 4. 权限矩阵

| 类别 | 要求 |
| --- | --- |
| 模型可写 | solution/**、scratch/**；生成缓存由工具管理 |
| 授权运行时操作 | 局部原水体法线扩展、前景材质、新离屏资源/匹配镜头副本及solution组合；只改授权目标绑定。 |
| 受保护 | 继承L2只读完整捕获桥作为本级答案、改主相机/全局可见性/曝光、改原水透明性、隐藏目标或预制目标帧。 |
| 作者测试控制 | 仅公开合法域内的相机、事件和参数干预；具体序列私有 |
| 新建测试对象 | 必须记录为作者干预，不替换真实核心场景绑定 |

权限要落实到确切object/property/surface路径，而不是整个SceneTree可写。原文件保持只读，新绑定引用solution资源。隔离测试检查共享资源和全局状态，不只看文件diff。

## 5. 摄像、状态与回归

前景内外对照、当前输入内容、波事件序列、遮挡/越界、零波原水体回归、simulate-once多pass时间证据。

每次采集真实输出：wave_state_and_native_combined_normal, actual_front_background, capture_tick_content_markers, occlusion_and_original_water_snapshot。保留原始场景、关新增显示但保留配置、detach恢复三类基线。新效果的合法遮挡/反射影响按规则判断，不要求全图像素不变。

## 6. 放行

确认source lock、所有目标路径及许可、实际原始数据/渲染行为、空接口边界、前级继承hash、原始GPU采集、正负对照、保护检查、干净导入和预算。状态从SOURCE_UNVERIFIED到SOURCE_BOUND_RUNTIME_VERIFIED必须有证据；完成本页不等于已运行。
