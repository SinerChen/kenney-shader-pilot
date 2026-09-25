# 算法与现有场景依据

本次读取库进度快照时间：`2026-09-24T18:56:56.944416+08:00`。以下 selected validation.json 均记录 passed=true；本轮仅核对源码/契约/证据存在及记录，不重新运行原算法，也不据此宣称新任务已通过。哈希见 [library_snapshot.json](sources/library_snapshot.json)。

| 算法 | 名称 | 既有隔离验收 | 来源与限制 |
|---|---|---|---|
| SH018 | 投影贴花重建 / Projective / deferred decal mapping | [passed=true，cases=118](../../godot_algorithm_catalog/verification/SH018/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH018/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH018.json) |
| SH023 | 高度驱动材质混合 / Height-based material blending | [passed=true，cases=76](../../godot_algorithm_catalog/verification/SH023/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH023/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH023.json) |
| SH043 | 重定向法线混合 / Reoriented Normal Mapping (RNM) | [passed=true，cases=74](../../godot_algorithm_catalog/verification/SH043/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH043/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH043.json) |
| SH179 | 指数高度雾积分 / Exponential height-fog integration | [passed=true，cases=70](../../godot_algorithm_catalog/verification/SH179/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH179/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH179.json) |
| SH185 | Gerstner海浪 / Gerstner waves | [passed=true，cases=79](../../godot_algorithm_catalog/verification/SH185/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH185/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH185.json) |
| SH192 | 泡沫历史演化 / Foam accumulation and decay | [passed=true，cases=76](../../godot_algorithm_catalog/verification/SH192/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH192/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH192.json) |
| SH234 | 交互草压弯场 / Interaction-field vegetation bending | [passed=true，cases=71](../../godot_algorithm_catalog/verification/SH234/validation.json) | [实现说明](../../godot_algorithm_catalog/godot/algorithms/SH234/README.md) · [契约](../../godot_algorithm_catalog/contracts/SH234.json) |


## 组合映射与场景锚点


### SA01 · 草地通行：局部踩踏与自然风动

取 P01 的人物经过植被子问题；H05 对应 SH234。H03 的风动作为冻结的配套模块，未把尚未实现的 SH233 层级树木风动列作已完成依赖。

- [forest_grass_lab/project/scenes/GrassPatch.tscn](../forest_grass_lab/project/scenes/GrassPatch.tscn)：场景与固定宿主入口。
- [forest_grass_lab/project/host/grass_host.gd](../forest_grass_lab/project/host/grass_host.gd)：335 张草片、玩家回放及程序生成对象。
- [forest_grass_lab/HOST_API.md](../forest_grass_lab/HOST_API.md)：UV2 高度、实例相位和现有场地说明。


### SA02 · 海面展示：Gerstner 波与波峰泡沫

选 G02 波面与 G13 压缩泡沫；P02 仅提供水/障碍关系的场景设计启发。实际载体是现有海面展示，不声称它已有弯曲浅溪，也不要求未选用的浅水求解器。

- [realistic/projects/water/example/boujie_water_shader/water_shader_examples.tscn](../realistic/projects/water/example/boujie_water_shader/water_shader_examples.tscn)：DeepOcean、Other_Designers、Material_Testers、Camera、HUD。


### SA03 · Bistro 雨后路面：湿区覆盖与材质保留

抽取 P07 湿路面的材质子问题，使用 B06/SH023 四层高度混合与 B09/SH043 法线细节；不把反射求解、多光源系统或降噪一并塞入任务。

- [realistic/projects/bistro/MainScene.tscn](../realistic/projects/bistro/MainScene.tscn)：Level Geometry/Ground/Ground；Props、Patches/Blockers、Human-For-Scale、Night Lights 作为保护范围。


### SA04 · FPS 命中反馈：有边界的投影贴花

使用 B13 的弹孔/命中贴花子问题，SH018 已包含深度重建、投影裁剪、法线/材料混合和后续照明；与射击事件、目标变换和遮挡的连接属于 L2。

- [projects/fps/pilot/F01.tscn](../projects/fps/pilot/F01.tscn)：World/TargetA、TargetB、TargetC、Cover、Player、HUD/Crosshair。
- [projects/fps/pilot/hit_target.gd](../projects/fps/pilot/hit_target.gd)：现有 hit 仅含 target/amount/health，没有 position/normal。
- [projects/fps/objects/player.tscn](../projects/fps/objects/player.tscn)：原玩家、武器视口及射线节点。


### SA05 · 森林晨雾：高度层次与景观可读性

取 F02 的清晨低洼薄雾，并放入现有森林；SH179 是有限视线段指数高度雾积分，不等同于 P03 的烟雾流体、局部灯光散射或体积阴影。

- [realistic/projects/forest/Main.tscn](../realistic/projects/forest/Main.tscn)：WorldEnvironment、Decorations-Forest、Groundcover、Main Terrain。
- [realistic/README.md](../realistic/README.md)：现有 Forest 自由相机与场景保留说明。


构想文档中的 P01/P02 等编号属于外部场景包，与旧 pilot 的同名 P01/P02 不是同一标识空间。新任务统一使用 SA01–SA05，避免误链接或覆盖历史实验。
