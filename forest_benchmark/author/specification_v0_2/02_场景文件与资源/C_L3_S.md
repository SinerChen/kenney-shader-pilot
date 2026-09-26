# C_L3_S｜原场景文件、输入与绑定清单

**作者侧规划，路径未核验/文件尚未随包提供。** 本页区分原工程查找线索与Codex要新建的任务文件。

## 1. 场景职责

将前级云影和薄雾体积光接入森林，使二者读取原天空所表示的同一云场、时钟和光源关系。改变原云层时间或运动条件时，地面和雾中的响应保持一致；不得替换天空或建立独立假云场。

前级从C_L2完整封存solution复制。场景环境换为净化后的完整原森林，不把合成L2舞台当L3。对于没有原生挂载的资源，按[工程组织](02_L3完整工程组织与权限.md)标constructed_fixture，不能冒称native。

## 2. 原文件线索及绑定门禁

- `Shaders/Sky/sky volumetric clouds.gdshader`：只作待查线索。
- `Main.tscn（实际天空材质/方向光/时钟绑定待核验）`：只作待查线索。

只有时间/方向相关片段，完整密度函数、天空锚定策略、世界单位、云层范围、光源和时钟映射未核实。若原天空只有不可唯一映射到有限世界体积的方向性画面，不可给它虚构唯一的地面真值。

1. 读全原天空密度/变换/时间更新，证明可建立有限、世界锚定且单位明确的云场到森林映射，并记录所有参与资源/uniform。
2. 用独立作者诊断比对原天空密度采样与世界空间查询；不以天空最终RGB倒推出唯一密度。
3. 若原天空相机相对或无有限空间映射，native 任务阻塞；可另建明确标记的 constructed_fixture，但不可混入 native 分数。
4. 验证可控天空时钟、方向光、雾盒及目标直接光接入；需要作者时钟桥时先作为无目标算法的归一化补丁记录并建立同样基线。

填写[本题source_binding模板](source_bindings/C_L3_S.template.json)；实际路径、NodePath、表面索引、活动材质、共享消费者、原行为和证据必须齐全。模板null不是授权猜值。

## 3. 新建的任务文件

以下相对路径在`starters/C_L3_S/`根内。共同需要：`fixture/entry.tscn`、`fixture/scene_access.gd`、`fixture/adapter_base.gd`、`public/task.json`、`public/api.md`、`public/scene_inventory.json`、`public/scene_files.json`、`public/permissions.json`、`public/source_context.json`及继承的`solution/effect.tscn/adapter.gd`。不得把原场景路径整体加前缀而不修复并验证res引用。

| 需要新建的目标路径 | 职责和允许内容 |
| --- | --- |
| public/sky_domain.json | 公开空间单位/云积分域/世界锚定条件/原时钟控制及合法参数范围；不含派生阴影。 |
| public/cloud_fog_receivers.json | 指定真实接收区、薄雾范围与方向光权限。 |
| fixture/source_clock_access.gd | 只读原生状态/作者时钟接入，未经核验不实现成假原时钟。 |

这些文件必须由Codex实际创建并导入验证。本包不含任何.tscn、第三方纹理或GPU解。公共输入不能含已求出的H/光透射/源投影/捕获答案。源角色分类采用source_context、inherited_solution、neutral_input、public_fixture；作者参考/判断信息不可导出。

## 4. 权限矩阵

| 类别 | 要求 |
| --- | --- |
| 模型可写 | solution/**、scratch/**；生成缓存由工具管理 |
| 授权运行时操作 | 读取原天空数据及密度定义，在 solution 内适配前级云影/雾；为指定接收面组合直接光贡献。 |
| 受保护 | 重写原天空时间/位置/密度以匹配自身输出；替换原天空；改全局光照/曝光；给模型标准密度网格或目标阴影。 |
| 作者测试控制 | 仅公开合法域内的相机、事件和参数干预；具体序列私有 |
| 新建测试对象 | 必须记录为作者干预，不替换真实核心场景绑定 |

权限要落实到确切object/property/surface路径，而不是整个SceneTree可写。原文件保持只读，新绑定引用solution资源。隔离测试检查共享资源和全局状态，不只看文件diff。

## 5. 摄像、状态与回归

天空及地面同tick序列、雾内空间查询、暂停/继续、相机位移、原环境关效果回归。

每次采集真实输出：original_sky_state_signature, world_density_samples, cloud_fog_current_tick, protected_lighting_snapshot。保留原始场景、关新增显示但保留配置、detach恢复三类基线。新效果的合法遮挡/反射影响按规则判断，不要求全图像素不变。

## 6. 放行

确认source lock、所有目标路径及许可、实际原始数据/渲染行为、空接口边界、前级继承hash、原始GPU采集、正负对照、保护检查、干净导入和预算。状态从SOURCE_UNVERIFIED到SOURCE_BOUND_RUNTIME_VERIFIED必须有证据；完成本页不等于已运行。
