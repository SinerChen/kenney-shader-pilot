# C_L3_R｜原场景文件、输入与绑定清单

**作者侧规划，路径未核验/文件尚未随包提供。** 本页区分原工程查找线索与Codex要新建的任务文件。

## 1. 场景职责

使用森林工程中指定的既有噪声资产构造局部云密度，并接入前级云影与薄雾体积光。正确解释资源及数据约定，保持原天空及其他既有消费者不变。本变体不要求局部云场与天空动画同步。

前级从C_L2完整封存solution复制。场景环境换为净化后的完整原森林，不把合成L2舞台当L3。对于没有原生挂载的资源，按[工程组织](02_L3完整工程组织与权限.md)标constructed_fixture，不能冒称native。

## 2. 原文件线索及绑定门禁

- `Main.tscn（报告记录 3D TGA / 2D BMP 噪声引用，具体资源路径待核验）`：只作待查线索。

具体噪声文件名、导入类型/布局/采样、维度和所有消费者未闭合。不得凭文件扩展名编造 Texture3D 或 Texture2D 数据，也不得默认两份资源已可重分发。

1. 找到报告所述两类资源的真实路径、资源类、原导入设置和天空消费者；没有所需资源时不换生成噪声却仍称 native。
2. 在固定引擎中验证原始数据的线性采样、尺寸、切片和轴向；为输入取值提供可复核元数据。
3. 验证前级云影和薄雾可在选定真实接收区局部接入且不改原天空/环境；局部云盒与雾盒不相交。
4. 原天空可在统一时钟下建立稳定回归基线，新增资源副本/派生缓冲不会污染共享消费者。

填写[本题source_binding模板](source_bindings/C_L3_R.template.json)；实际路径、NodePath、表面索引、活动材质、共享消费者、原行为和证据必须齐全。模板null不是授权猜值。

## 3. 新建的任务文件

以下相对路径在`starters/C_L3_R/`根内。共同需要：`fixture/entry.tscn`、`fixture/scene_access.gd`、`fixture/adapter_base.gd`、`public/task.json`、`public/api.md`、`public/scene_inventory.json`、`public/scene_files.json`、`public/permissions.json`、`public/source_context.json`及继承的`solution/effect.tscn/adapter.gd`。不得把原场景路径整体加前缀而不修复并验证res引用。

| 需要新建的目标路径 | 职责和允许内容 |
| --- | --- |
| public/resource_inputs.json | 精确输入资源 ID、通道/采样/范围、用途；不含转换后密度答案。 |
| public/local_cloud_fog.json | 密度构造系数、grid、云盒/雾盒、接收区和方向光权限。 |
| public/source_variants.json | 公开输入变体的合法域，不含正式选择/期望。 |

这些文件必须由Codex实际创建并导入验证。本包不含任何.tscn、第三方纹理或GPU解。公共输入不能含已求出的H/光透射/源投影/捕获答案。源角色分类采用source_context、inherited_solution、neutral_input、public_fixture；作者参考/判断信息不可导出。

## 4. 权限矩阵

| 类别 | 要求 |
| --- | --- |
| 模型可写 | solution/**、scratch/**；生成缓存由工具管理 |
| 授权运行时操作 | 新建 solution 中的派生资源、密度处理、局部云影接收材质和薄雾合成；只读访问原天空噪声。 |
| 受保护 | 改共享噪声/导入/天空材质、用其他噪声替代、改全局方向光强度/曝光/AA、影响非目标接收物。 |
| 作者测试控制 | 仅公开合法域内的相机、事件和参数干预；具体序列私有 |
| 新建测试对象 | 必须记录为作者干预，不替换真实核心场景绑定 |

权限要落实到确切object/property/surface路径，而不是整个SceneTree可写。原文件保持只读，新绑定引用solution资源。隔离测试检查共享资源和全局状态，不只看文件diff。

## 5. 摄像、状态与回归

原天空固定时刻基线、资源非对称诊断截面、地面云影、薄雾受光以及关新增显示后的天空对照。

每次采集真实输出：source_resource_samples, derived_density_grid, cloud_and_fog_outputs, original_sky_consumer_snapshot。保留原始场景、关新增显示但保留配置、detach恢复三类基线。新效果的合法遮挡/反射影响按规则判断，不要求全图像素不变。

## 6. 放行

确认source lock、所有目标路径及许可、实际原始数据/渲染行为、空接口边界、前级继承hash、原始GPU采集、正负对照、保护检查、干净导入和预算。状态从SOURCE_UNVERIFIED到SOURCE_BOUND_RUNTIME_VERIFIED必须有证据；完成本页不等于已运行。
