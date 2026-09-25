"""Build the authored 5x3 task specification pack; never launch Godot/model APIs."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from model_prompts import TOOLS, profile, render_prompt
from environments import PROFILES as ENVIRONMENTS, definition, prepare_task

PACK = Path(__file__).resolve().parents[1]
WORKSPACE = PACK.parent
LIBRARY = WORKSPACE.parent / "godot_algorithm_catalog"
SOURCE = Path("D:/EdgeDownload_File/shader_algorithm_scenarios.md")


def case(key, intervention, expected, evidence, failure):
    return dict(id=key, intervention=intervention, expected=expected,
                evidence=evidence, typical_failure=failure)


def level(title, goal, requirements, cases):
    return dict(title=title, goal=goal, requirements=requirements, cases=cases)


CHAINS = [
    dict(
        id="SA01", title="草地通行：局部踩踏与自然风动",
        scene="forest_grass_lab/project/scenes/GrassPatch.tscn",
        project="forest_grass_lab/project/project.godot",
        source_ids=["P01", "H05", "H03", "I10"], algorithms=["SH234"],
        rationale="取 P01 的人物经过植被子问题；H05 对应 SH234。H03 的风动作为冻结的配套模块，未把尚未实现的 SH233 层级树木风动列作已完成依赖。",
        anchors=[("forest_grass_lab/project/scenes/GrassPatch.tscn", "场景与固定宿主入口"),
                 ("forest_grass_lab/project/host/grass_host.gd", "335 张草片、玩家回放及程序生成对象"),
                 ("forest_grass_lab/HOST_API.md", "UV2 高度、实例相位和现有场地说明")],
        target="固定草地中所有被有效交互 footprint 覆盖的草实例及对应的变形阴影",
        protect="作用范围外草的原风动；所有草根；地面、玩家显示体、场景控制和 UI",
        purpose="玩家仍可看清草地中的自身位置、经过方向及短时痕迹，远处草保持环境风动。",
        scope="固定 XZ patch，二维交互场；不扩展到全森林、树木分层动画、坡地高度判定或相机滚动场重投影。",
        fixture=[],
        impact_path=["玩家脚底位置/速度/有效半径", "固定世界 patch 的衰减与写入", "每个草实例采样同一交互场", "叠加冻结风动并约束根部", "顶点、法线与阴影", "全景中的通行痕迹及远处植被"],
        levels=[
            level("交互场与固定根部变形", "这个压草模块是否真正计算了局部影响、历史恢复和草片形变？", [
                "按 SH234 契约完成 GPU 衰减、交互者写入、双线性场采样和草片位置/法线输出；L1 关闭基础风动。",
                "根部固定是算法本身的不变量，放在 L1 验证；不能把整片平移、变色、隐藏或缩放为零当作压草。",
                "保留该变体的方向累积与峰值压低语义：相反方向可以抵消，压低强度不因此归零。",
                "使用显式 step/reset；维持合法微小半径可能漏采的契约，不擅自放大半径。数值输入域和容差继承 SH234。"
            ], [
                case("locality", "关闭风，单个静止交互者；采样中心、有效 footprint 内外及 patch 外。", "GPU 场与独立参照一致；patch 外采样为零；所有根部位置不变。", "场 RGBA、所有顶点/法线读回、roots viewer。", "颜色变化近似正确，但场域、坐标或根部错误。"),
                case("conflict", "在固定位置放两个相向交互者，再交换输入顺序。", "方向合成与峰值压低符合契约；交换顺序不引入可见或数值偏差。", "独立 float64 对照及两次字段差值。", "最后一个输入覆盖此前状态或方向抵消时草完全恢复。"),
                case("recovery", "写入后移除所有交互者；p=.92，以 1/60 秒运行 2 秒，再 reset 重放。", "纯恢复按 p^(60*dt) 衰减；reset 场和时间清零；根部仍固定。", "每 30 步字段采样及 reset 前后读回。", "离开立即恢复、永不恢复或按帧率而非 dt 衰减。"),
                case("domain", "运行公开契约边界、无效配置、dt=0 和 subtexel 案例。", "非法更新原子拒绝；暂停无推进；微小合法输入按声明的采样限制报告。", "错误返回、旧状态哈希、既有独立测试协议。", "NaN、偷偷截断输入或把所有异常统一返回成功。")
            ]),
            level("压草、风动与阴影的关系", "单独正确的压草和风动组合后，是否仍共享空间、时间与根部约束？", [
                "接续 L1 候选，接入宿主冻结的基础风动、现有草片 UV2 和光照，不重写玩家轨迹。",
                "风与交互分别有开关；停风仍能压草，移除交互后仍有风动。组合不能把根部重新移走。",
                "草片可见位置、法线/受光与投影使用同一变形和 elapsed；不用独立 TIME 驱动某一 pass。",
                "世界位置映射与 instance ID 一致，移动相机不应改变场或压倒方向。"
            ], [
                case("factorial", "固定时间/轨迹，运行风关交互关、仅风、仅交互、二者都开四组。", "单模块结果可复现；两模块都开时均有贡献，风关不抹掉交互历史。", "四组字段/顶点差值与同步短视频。", "某模块覆盖另一模块或两个开关共享错误状态。"),
                case("attachment", "固定交互者与时间，切换 overview/roots/top；检查多个不同朝向实例。", "场和世界顶点不变，实例不串位；根部仍在各自原位置。", "相机矩阵、实例 ID、顶点读回。", "屏幕空间压草，或用 atlas UV 代替草高。"),
                case("shadow", "保持光源固定推进 3 秒，再暂停；观察草尖与地面阴影。", "阴影对应同一时刻变形；暂停后两者停止且无静止直立草的残影。", "可见 pass/shadow pass 的时间与几何诊断、连续帧。", "只修改可见 pass，阴影不动或滞后一帧。"),
                case("history", "前行、短暂停留、反向、移除交互者；风向保持不变。", "历史持续衰减，新轨迹连续叠加；set_interactors 不导致全场 reset。", "输入记录、场序列和去除交互后的风动片段。", "每帧 configure 清历史，或初始坐标被重复加速度。")
            ]),
            level("通行痕迹的覆盖与场景保留", "是否影响了整条经过路径中的必要草叶，同时保留周围植被和原场景用途？", [
                "在完整草地复查所有实际受影响实例，不能只让镜头中央或某一张草响应。",
                "以相同时间的仅风基线作为负对照：有效 footprint 外草保持原风动，地面/玩家/UI 不继承草材质或位移。",
                "保留草的可见数量、根部、贴图 Alpha 和光照；不能靠删草、遮住场景、换相机或减小显示范围达标。",
                "全景、近景和顶视都能读出玩家与轨迹关系；离开后逐步恢复，reset 后可以完整再次走过。"
            ], [
                case("coverage", "执行原 11 秒穿场轨迹、偏移一条平行轨迹和反向轨迹。", "实例清单中全部有效覆盖草有正确局部响应，无只处理一块 mesh 或一种草资产的遗漏。", "实例覆盖表、轨迹/footprint 叠图、三条全景视频。", "主画面有效但边缘、另一种草或另一条路径完全无效。"),
                case("negative_controls", "对比相同时间的仅风与风+交互；检查 footprint 外实例和非草对象。", "远草不被压倒；地面、玩家和 UI 的资源、几何与行为不变。", "目标/非目标资源绑定表、字段外采样、负对照截图。", "共享材质写入污染全部对象，或全场同时趴倒。"),
                case("purpose", "使用原相机与手动控制从草地一侧走到另一侧，再切顶视检查。", "玩家、经过方向和草地范围仍可辨；无新增遮挡屏片、删草或控制中断。", "操作记录、原/新节点与实例数量、完整画面视频。", "局部效果漂亮但角色被遮死、草消失或原控制不可用。"),
                case("reset_scene", "完成交互后 reset，再重放；检查新建 GPU 资源和所有材质绑定。", "历史清空且重放一致；资源数量不逐轮增长；无需重载整个原项目。", "两轮字段/覆盖报告、资源计数和全景对照。", "上轮轨迹残留，或释放/重绑破坏其他草材质。")
            ])
        ]
    ),
    dict(
        id="SA02", title="海面展示：Gerstner 波与波峰泡沫",
        scene="realistic/projects/water/example/boujie_water_shader/water_shader_examples.tscn",
        project="realistic/projects/water/project.godot",
        source_ids=["G02", "G13", "P02"], algorithms=["SH185", "SH192"],
        rationale="选 G02 波面与 G13 压缩泡沫；P02 仅提供水/障碍关系的场景设计启发。实际载体是现有海面展示，不声称它已有弯曲浅溪，也不要求未选用的浅水求解器。",
        anchors=[("realistic/projects/water/example/boujie_water_shader/water_shader_examples.tscn", "DeepOcean、Other_Designers、Material_Testers、Camera、HUD")],
        target="DeepOcean 的海面网格及其各 LOD 表面；同一 q 参数上的波形、法线和泡沫",
        protect="OceanFloor、岸上/展示台几何、IceCube、ObsidianCube、OutsetOceanSphere、DeepOceanSphere 对照样本、HUD 和原相机控制",
        purpose="在保留原材质展览与相机游览功能的条件下，海面波峰及泡沫随同一波形运动。",
        scope="只做参数附着的波峰泡沫；不要求泡沫流体平流、岸边浪花、反射/折射新算法或水下切换重写。",
        fixture=[],
        impact_path=["显式波参数与 elapsed", "P(q,t)、完整切向和法线", "水平位移场 D(q,t)", "J 与泡沫历史 F(q)", "同一 q 对应的显示位置 P(q,t)", "完整海面 LOD 与独立展示材质"],
        levels=[
            level("完整 Gerstner 波面", "位移、切向和法线是否符合波模型，而非只让水纹滚动？", [
                "按 SH185 契约输出水平/垂直位移、两个完整切向、世界法线、速度、Jacobian 和退化状态。",
                "方向需要按契约归一化；矩阵变换与负行列式时的几何朝向不能省略。",
                "原场景子集 显示真实 GPU 输出，不能以法线贴图或平面 UV 平移代替几何位移。",
                "保留合法折叠输入并报告状态；场景演示的非折叠参数预设不能替代 L1 极端输入验收。"
            ], [
                case("geometry", "单波沿 X、沿 Z，再叠加两方向波；在 t=0/1/2 采样。", "位置、切向、速度和法线均在 SH185 既定误差界内。", "逐点 GPU/独立 CPU 数据、隔离网格动画。", "只有高度变化，漏掉水平位移或切向交叉项。"),
                case("limits", "空波组、零振幅、反向速度与非单位方向。", "平面极限、传播方向和方向归一化均正确。", "原契约边界样本及法线可视化。", "方向长度错误改变波长或平面极限仍有波动。"),
                case("transform", "施加合法非均匀缩放及负行列式矩阵。", "世界位置和切向一致，法线方向按契约处理。", "变换前后读回和斜视 viewer。", "用位置矩阵直接变换法线。"),
                case("degeneracy", "运行折叠/近退化输入，暂停并 reset。", "如实返回 J、normal_valid 和 orientation；dt=0 无推进；reset 回到初始时间。", "状态位、实际 GPU dispatch 和误差报告。", "夹小 steepness，伪造向上法线或隐藏失败点。")
            ]),
            level("波面压缩驱动泡沫历史", "泡沫来源、历史与显示位置是否都来自同一个波面？", [
                "把 L1 的水平位移 D(q,t) 送给 SH192；波高仅用于显示，不能替代水平压缩计算。",
                "按 SH192 的 central difference、source=max(whitecap-J,0) 与分步增长/衰减规则更新 F；显示于同一 P(q,t)。",
                "set_surface 只更新表面，不清空 F、不推进第二次时间；每个逻辑 step 的顺序为波面更新、表面同步、泡沫更新、显示。",
                "SH192 可作为冻结的配套模块；评测候选负责的连接关系，记录实际数值来源。"
            ], [
                case("source", "锁定 q 网格和时间，分别只改变波高展示与水平位移输入。", "只改展示高度不改变 J/source；水平压缩改变 source，相关 F 随之演化。", "D、四个导数、J、source、F 同步读回。", "把高处或随机白噪声直接当白沫源。"),
                case("history", "有压缩时生成泡沫，随后 grow=0，保持波运动 2 秒。", "新生成停止，已有 F 按衰减保留并跟随同一参数位置。", "标记 q 的世界轨迹、F 曲线、连续帧。", "每帧重置历史、泡沫悬浮或沿屏幕滑动。"),
                case("timing", "固定 1/60 秒推进 180 步；记录各模块时间和 set_surface 前后状态。", "各模块时间一致；set_surface 不额外推进或清零；没有双重速度。", "调用顺序日志和 step_count。", "wave 和 foam 时间失配，或同时开启 pattern_velocity 导致二次运动。"),
                case("ablation", "同一轨迹跑波+泡沫、仅波、grow=0 三组；改相机不改世界状态。", "波结果在三组一致，泡沫差异只沿其来源/历史路径产生。", "同时间世界采样点、模块消融视频。", "关泡沫改变波形，或移动相机使 source 跟着走。")
            ]),
            level("完整海面覆盖与展览保留", "整个目标海面都获得波峰反馈，同时其他材质样本仍发挥对照作用吗？", [
                "作用于 DeepOcean 的全部显示表面和 LOD；不能仅修复近处一个网格。",
                "避免修改共享原材质导致冰、黑曜石、海面球样本同步变化；目标材质须有清晰的实例绑定记录。",
                "原展示台、相机、HUD、基础反射/折射和天空保持；波面新增效果不能覆盖整屏或给干燥对象加泡沫。",
                "从原入口连续游览近远海面及各展示物，证明波形/泡沫增强海面读感且材质展览仍可使用。"
            ], [
                case("lod_coverage", "沿预置世界相机路径跨过近中远 LOD 边界，固定若干世界 q 标记点。", "必要海面表面均响应；同一 q 无可见重置、突然位移或泡沫粘屏。", "LOD/网格覆盖清单、世界点轨迹及全程视频。", "近景成功但远景漏绑或相机移动重置历史。"),
                case("resource_isolation", "在相同时间切候选开关，逐一查看 IceCube、ObsidianCube 和两个海面球。", "冻结对照样本的原 shader、参数与外观不被候选写入污染。", "共享资源身份/参数差异表、各样本 ROI 截图。", "编辑共享 .tres 改坏整个材质展台。"),
                case("dry_objects", "检查 OceanFloor、展示台、天空、HUD；从多个视角看前景交叠。", "泡沫只属于目标水面，其他对象不出现波位移/白沫；遮挡及原基础水材质功能仍成立。", "对象 ID/mask、全景和前景交叠序列。", "全屏噪声覆盖干物体或海面效果穿过展示台。"),
                case("purpose", "使用原 Camera 操作游览，开关效果后 reset 重放。", "既能读出波峰泡沫，又能继续比较原展示材质；重置不改变原相机/展示对象布局。", "实际操作视频、节点/资源快照和两轮回放。", "为了效果删掉展台、更换观察范围或锁死相机。")
            ])
        ]
    ),
    dict(
        id="SA03", title="Bistro 雨后路面：湿区覆盖与材质保留",
        scene="realistic/projects/bistro/MainScene.tscn",
        project="realistic/projects/bistro/project.godot",
        source_ids=["P07", "B06", "B09"], algorithms=["SH023", "SH043"],
        rationale="抽取 P07 湿路面的材质子问题，使用 B06/SH023 四层高度混合与 B09/SH043 法线细节；不把反射求解、多光源系统或降噪一并塞入任务。",
        anchors=[("realistic/projects/bistro/MainScene.tscn", "Level Geometry/Ground/Ground；Props、Patches/Blockers、Human-For-Scale、Night Lights 作为保护范围")],
        target="经明确 surface/region 白名单标记的室外石路低洼湿区，不是 Ground 节点下所有表面",
        protect="干燥路脊、约定干燥人行区/门口、室内地面、桌椅招牌玻璃、角色、碰撞与日夜控制",
        purpose="路面呈现雨后湿润与原石材细节，仍可辨别通行边界、入口和原有材质。",
        scope="美术指定湿区和高度混合，不求解雨水汇流、积水几何、SSR 或完整反射；保留原照明与反射配置。",
        fixture=[],
        impact_path=["wetness 与作者给定的材质高度/区域 mask", "四层同时竞争的权重", "颜色、粗糙度、金属度、基础法线共用权重", "同切线空间的 RNM 细节", "指定道路 surface 的原照明响应", "街道入口、干区和道具仍可辨识"],
        levels=[
            level("四层高度材质混合", "高度混合是否保持各材料通道一致，并正确处理零与极小权重？", [
                "实现 SH023 的四层同时竞争变体，不能用有顺序的逐层 mix 代替。",
                "同一组权重用于线性 albedo、roughness、metallic、高度和基础法线；法线按契约归一化并处理退化。",
                "全零 control 返回契约定义的零材质；极小总权重的分母下限允许权重和不为 1，不能强行当作普通归一化。",
                "使用隔离材质图谱验证，不增加雨、反射或场景筛选作为 L1 评分内容。"
            ], [
                case("oracle", "普通、负高度、大高度、小 transition 样本逐像素求值。", "所有 16 个输出通道符合 SH023 固定容差。", "独立 float64 参照、GPU 读回和材质图谱。", "结果颜色近似正确但粗糙度/法线使用了另一组权重。"),
                case("permutation", "对同一像素的四层执行全部 24 种排列。", "对应还原层编号后，材料结果保持一致。", "排列对照和每通道误差。", "两两折叠产生顺序依赖。"),
                case("zeros", "全零、one-hot、极小 control 以及相消法线。", "分别遵守零策略、单层退化和法线回退；不捏造原材质回退。", "权重和/法线读回及边界案例。", "除零、把零输入渲成随机灰色或总是强行归一化。"),
                case("invalid", "非法数值/尺寸/法线输入后再次读取旧输出。", "原子拒绝，静态 step 不随时间改变结果。", "错误状态和前后数据。", "错误更新部分写入资源或静态混合持续闪动。")
            ]),
            level("湿区权重、细节法线与受光一致", "湿润分布与法线细节的组合是否表达同一片材质？", [
                "接入冻结的 SH043 RNM 细节模块；先用 L1 权重得到基础法线，再在同一切线空间组合细节。",
                "颜色、粗糙度与法线变化共用同一局部湿区输入；不能湿色在石缝而高光在石脊，或仅通过曝光伪装湿润。",
                "不把 RNM 与高度混合的法线线性混合互换；RNM 平坦 detail 应还原基础法线。",
                "固定曝光和输入纹理，分别消融湿区和法线细节，证明两者独立可控。"
            ], [
                case("mask_relation", "同一局部 patch 将 wetness 从 0 改到 .5、1；读取权重和材料通道。", "各通道响应同一权重来源，湿区位置一致；0 使用冻结的原材质 one-hot 输入。", "权重、颜色、roughness、normal 对齐视图。", "湿颜色和高光/法线边界脱离。"),
                case("normal_identity", "将 detail 置平坦法线，再还原细节；保留湿区不变。", "平坦 detail 等于混合基础法线；细节变化不改变 wetness 权重。", "RNM 输入输出向量和固定光照对照。", "把法线图当颜色混合，或 detail 重置了湿度。"),
                case("tangent_frame", "旋转 patch/相机和光源，检查带镜像 UV 的固定诊断 patch。", "细节仍贴在表面，受光随真实方向变化而非随屏幕旋转。", "TBN/世界法线可视化、旋转序列。", "手性或坐标混用导致一侧法线凹凸翻转。"),
                case("factorial", "固定曝光运行干+无细节、湿+无细节、干+细节、湿+细节四组。", "每次只有声明的输入变化；组合中仍能辨认原石材大结构。", "四组材料数据和斜视截图。", "改曝光/灯光补偿算法错误，或细节抹平原材质。")
            ]),
            level("湿路面的作用边界与街道用途", "是否只湿润必要路面，同时保留干区、入口和道具材质？", [
                "按已冻结的 surface/region 清单覆盖室外目标湿区；每个必要 surface 都检查，不只验摄像机正前方。",
                "保留干脊、约定干燥门口/人行区、室内地面；高度图的局部低值不意味着任何对象都应变湿。",
                "不修改全局曝光、灯光、玻璃、招牌、桌椅和共享原材质；保留角色控制与实际碰撞。",
                "在近景和完整街景中仍能识别石缝、通行边界及入口，效果关闭回到同一日夜模式的基线。"
            ], [
                case("coverage", "遍历湿区 surface/region，改变 wetness 并移动镜头至原画面外的街段。", "清单内必要低洼湿区均有对应材料响应；不依赖固定视角。", "surface 覆盖矩阵、mask 叠图、街段全景。", "只修改一张材质或遗漏第二个道路 surface。"),
                case("protected", "选择低高度但属于门口/室内/道具的负样本，湿度从 0 到 1。", "对象/区域准入先于材质高度判断；这些样本保持基线。", "负样本列表、材质参数哈希和匹配截图。", "按全局高度让桌面、室内和干区一起变湿。"),
                case("shared_resource", "对照候选开关与原资源使用者，分别在日景和夜景观察。", "只改变目标 surface 的实例材质；灯具、玻璃和道具不受污染。", "material resource 使用者清单、绑定差异、日夜 A/B。", "共享资源串改，或改变整个环境来强化湿地。"),
                case("purpose", "使用原角色沿固定路线经过路口和入口；再关闭效果/reset。", "入口、地面边界与石材细节可辨，原通行/碰撞/日夜操作可用；关闭后恢复。", "操作视频、关键对象截图及状态回归记录。", "地面过亮成一片、入口不可读，或为了遮错改变路线/碰撞。")
            ])
        ]
    ),
    dict(
        id="SA04", title="FPS 命中反馈：有边界的投影贴花",
        scene="projects/fps/pilot/F01.tscn", project="projects/fps/project.godot",
        source_ids=["B13", "B08"], algorithms=["SH018"],
        rationale="使用 B13 的弹孔/命中贴花子问题，SH018 已包含深度重建、投影裁剪、法线/材料混合和后续照明；与射击事件、目标变换和遮挡的连接属于 L2。",
        anchors=[("projects/fps/pilot/F01.tscn", "World/TargetA、TargetB、TargetC、Cover、Player、HUD/Crosshair"),
                 ("projects/fps/pilot/hit_target.gd", "现有 hit 仅含 target/amount/health，没有 position/normal"),
                 ("projects/fps/objects/player.tscn", "原玩家、武器视口及射线节点")],
        target="最近一次有效命中的 TargetA 或 TargetB 上朝向正确、位于投影体内的实际可见表面",
        protect="TargetC、Cover、墙/地、目标背面、其他共享材质实例、武器视口与 HUD；全部原命中/生命值/碰撞逻辑",
        purpose="玩家能判断最近一次命中发生在哪个目标和位置，同时保留遮挡、瞄准与原射击流程。",
        scope="一次只保留一个活动贴花，寿命 2 秒；不要求多贴花排序、透明受体、蒙皮目标或完整 deferred renderer。",
        fixture=[],
        impact_path=["原射线命中与独立 hit_surface 输入", "target_id/局部锚点/目标变换", "当前深度重建和投影体裁剪", "受体法线/材料修改后照明", "最近一次命中反馈", "遮挡、原伤害和瞄准流程"],
        levels=[
            level("深度重建与完整投影贴花", "贴花是否真的基于表面重建和投影体裁剪，而非屏幕上的装饰图？", [
                "按 SH018 选定变体执行真实深度/材料 pass、逆投影与世界/局部变换、六面裁剪、朝向过滤、mip 采样和材料后照明。",
                "读取真实最近深度与 primitive identity；背景/背面和投影体外不能收到贴花。",
                "贴花法线、粗糙度等先进入材料再受光，不能把完成照明的图像上直接叠弹孔算作实现。",
                "接受原契约的精度与硬边界限制，单独保留边界歧义诊断；不以截图接近代替数值数据。"
            ], [
                case("reconstruction", "运行透视/正交相机、平移、近远平面与斜面输入。", "深度、世界/局部位置、UV 和 primitive ID 与独立 ray-triangle 参照匹配。", "SH018 固定容差逐像素读回及原场景子集。", "reverse-Z 或齐次除法错误，只在一个相机角度正确。"),
                case("volume", "检查六个盒面、背面、正负 scale 与朝向阈值。", "体积和朝向裁剪符合契约；临界 float32 分类按已有限制独立报告。", "inside/facing/alpha 通道和边界报告。", "贴花穿透背面、遗漏一个盒面或把边界反例删掉。"),
                case("material", "只改变贴花 normal_roughness 并移动固定 viewer 光源。", "材料变化进入后续照明，深度和几何保持。", "before/after G-buffer、光照输出。", "后期叠图在所有角度保持同一明暗。"),
                case("filtering", "缩小贴花、拉远相机并运行非法输入/暂停/reset。", "使用完整 mip；错误原子拒绝；暂停/reset 符合契约。", "LOD/导数诊断、错误日志及状态读回。", "远处闪烁、dt=0 仍推进或错误破坏已提交材质。")
            ]),
            level("命中事件、移动受体与遮挡", "事件位置、贴花受体、照明和时序是否指向同一次真实命中？", [
                "消费宿主新增的 hit_surface 数据；以局部锚点和当前目标变换定位，不能假设旧 hit 事件含有位置。",
                "只保留最近有效事件的一个贴花；新事件切换受体，重复 ID 不重置寿命；暂停不耗时，2秒后清除。",
                "固定目标局部锚点后移动/旋转目标，贴花必须跟随；移动相机不能改变锚点。",
                "当前前景深度遮住贴花，移开前景后仍显示在原受体；法线与材质进入原光照。"
            ], [
                case("anchor", "命中 A，冻结逻辑时间，平移并旋转 A，再移动相机。", "贴花世界位置随目标变换，局部位置不变；相机单独移动不改锚点。", "事件局部坐标、投影变换和连续视角视频。", "命中后漂在原世界位置或贴在屏幕上。"),
                case("occlusion", "贴花有效期内将 Cover 放到相机和 A 之间，再移开。", "贴花被前景遮住且不画在 Cover 上；移开后回到 A 的原位置。", "当前深度/receiver ID、遮挡前中后帧。", "穿透遮挡或把弹孔转移到遮挡物。"),
                case("events", "A 事件后 0.4秒命中 B；再次发送 B 的相同 event_id。", "活动受体从 A 切到 B，A 清除；重复 ID 不延长 B 的两秒寿命。", "事件 ID、active slot、target_id 与寿命日志。", "串目标、重复计时或出现未声明的多个贴花。"),
                case("lighting", "保持命中和时间，分别改变相机、灯光和贴花 opacity。", "位置/深度不变，贴花随表面受光；opacity=0 恢复原材料。", "材料通道与受光 A/B，原伤害状态日志。", "屏幕装饰不受光或视觉事件再次造成伤害。")
            ]),
            level("有效命中覆盖与射击流程保留", "反馈是否只出现在应接收命中的表面，且不改变射击和遮挡用途？", [
                "对 TargetA/B 的已标记可见 surface/锚点全面检查；禁止只支持其中一个模型实例或一个正面角度。",
                "TargetC、Cover、墙地、目标背面和武器视口是负对照；共享材质不能传播命中效果。",
                "视觉适配不改变原生命值、damage 次数、碰撞层、射线或 HUD；非法受体事件被忽略且不伪造成有效命中。",
                "保留完整场景的瞄准、掩体遮挡与重复射击；玩家能指出最近一次命中的目标和位置。"
            ], [
                case("coverage", "按清单射击 A/B 的正面与斜面锚点，包含初始镜头外的锚点。", "全部允许锚点有局部反馈，无漏 surface；最近命中位置可辨。", "锚点覆盖表、真实命中数据与完整画面视频。", "只改 TargetA 的一个 mesh 或把所有命中放在目标中心。"),
                case("negative_receivers", "命中 A 时观察 C/墙地/武器；注入带位置但 target_id=C 的公开负例。", "负对象不显示贴花；不允许的事件不替换当前有效贴花或改变原健康状态。", "receiver 清单、材质身份和事件过滤记录。", "同材质目标一起出现弹孔或错误事件抹掉当前反馈。"),
                case("gameplay", "用原武器执行无遮挡射击、掩体阻挡射击和切换目标，与基线比较。", "伤害次数、生命值和阻挡关系相同；准星、武器显示与控制可用。", "原/新事件和健康状态逐项对照、游戏视频。", "贴花算法修改射线、穿透掩体或多调用一次 damage。"),
                case("lifecycle", "有效命中后等待到期，再 reset 并重复三轮。", "到期/重置只清候选贴花，原资源绑定正确且数量不增长。", "三轮节点/资源/材质差异及完整场景截图。", "到期删了原对象、永久改材质或残留后台贴花。")
            ])
        ]
    ),
    dict(
        id="SA05", title="森林晨雾：高度层次与景观可读性",
        scene="realistic/projects/forest/Main.tscn", project="realistic/projects/forest/project.godot",
        source_ids=["F02", "P01"], algorithms=["SH179"],
        rationale="取 F02 的清晨低洼薄雾，并放入现有森林；SH179 是有限视线段指数高度雾积分，不等同于 P03 的烟雾流体、局部灯光散射或体积阴影。",
        anchors=[("realistic/projects/forest/Main.tscn", "WorldEnvironment、Decorations-Forest、Groundcover、Main Terrain"),
                 ("realistic/README.md", "现有 Forest 自由相机与场景保留说明")],
        target="主相机可见地形、树干、石块及 Alpha 裁切植被对应的相机至表面视线段",
        protect="场景几何/植被分布、材质纹理、天空/原体积云、UI、原相机控制；近景关键对象的可辨识度",
        purpose="通过低处与远处的雾层次表达清晨空间深度，同时能继续辨认近景地形、岩石与植被。",
        scope="有限段高度雾；不求解烟传播、光束遮挡或多重散射。天背景采用显式保留策略，不把无限远深度输入有限段公式。",
        fixture=[],
        impact_path=["世界高度密度参数与当前相机/表面端点", "有限视线段完整积分 tau", "T=exp(-tau)", "线性场景色与雾色合成一次", "真实不透明/裁切植被的前后关系", "完整森林的低处层次和近景可读性"],
        levels=[
            level("指数高度雾积分", "模块是否完整积分了沿视线变化的密度，并稳定处理水平与极限输入？", [
                "实现 SH179：rho(y)=rho_ref*exp(-falloff*(y-reference_height))，完整积分相机到表面的有限直线段。",
                "输出 tau、log_tau、透射、不透明度、线性合成色和深度状态；不能用终点高度乘距离或普通距离雾替代。",
                "零距离、零密度、零 falloff 和近水平视线必须数值稳定；超范围 tau 按契约返回 null 与状态。",
                "原场景子集 和逐射线读回为主要依据，不要求完整森林渲染。"
            ], [
                case("integral", "相同长度取水平、上升和下降视线段，与双精度解析及数值求积比较。", "各输出符合 SH179 容差，端点翻转保持积分一致。", "独立参考、tau/T/颜色读回及三球 viewer。", "仅按终点高度求密度或前后端点不对称。"),
                case("limits", "零长度、零密度、零 falloff 及极薄雾/近水平射线。", "T=1 或均匀介质极限正确；小量不发生相减消失。", "绝对/相对误差及有限性检查。", "除零、雾突然一片白或小雾量全被错误抹掉。"),
                case("range", "极大合法光学厚度，以及契约内的极小参数。", "深度不可表示时 canonical tau=null、log_tau 保留、T=0；不把占位零当透明。", "depth_state、原始槽和 canonical 输出并列。", "溢出 NaN，或用 tau 占位零显示透明。"),
                case("domain", "无效高度/长度、NaN 标记输入和重复静态 step。", "错误原子拒绝；相同输入输出固定，不受 TIME 影响。", "配置/错误返回、前后输出和 reset 记录。", "无效输入夹紧、旧状态被部分覆盖。")
            ]),
            level("高度雾与深度、植被和颜色合成", "正确雾积分接入场景深度后，是否仍作用于正确的视线且只合成一次？", [
                "使用固定 renderer bridge 的相机至实际可见表面端点，不把 reverse-Z 原值当线性距离。",
                "颜色在线性空间按 T*C+(1-T)*Cf 合成，在 tone mapping 之前只做一次；旧高度雾重复项必须由宿主统一处理。",
                "裁切叶片的有效像素结束于叶面，透明空隙看到后方表面；不允许给整张草片矩形统一写近景深度。",
                "相机改变高度或方向时重新求当前射线，密度层仍固定在世界坐标；天空与 UI 采用合同中的保留路径。"
            ], [
                case("world_height", "保持密度场固定，相机上下移动并回到原位；记录同一世界地标。", "每次 T 对应当前两个端点的积分，回原位恢复；雾层不跟随相机平移。", "相机/表面世界坐标、tau/T 和相机路径视频。", "把相机局部 Y 当世界高度或使用旧相机矩阵。"),
                case("occlusion", "观察前景叶片/其透明空隙/后方岩石，移动相机改变重叠。", "三种射线使用实际各自深度，空隙无矩形雾片，前后遮挡一致。", "深度、Alpha coverage、对象 ID、T 诊断。", "草片空白挡雾、雾绕过叶面或穿透前景。"),
                case("linear_once", "在冻结 HDR 灰阶/彩色样本上设置 T=.25/.5/.75，改变曝光仅作诊断。", "tone map 前合成数值正确，曝光不参与积分且候选雾仅合成一次。", "线性输入/输出、pass 顺序、原雾开关快照。", "sRGB 混色、双重雾或先 tone map 再合成。"),
                case("ablation", "rho=0、falloff=0 与正常高度雾三组；冻结光照/云时间。", "rho=0 恢复共同基线，falloff=0 是距离均匀介质；sky/UI 不变。", "三组颜色和透射数据、匹配连续帧。", "雾关后留灰层或为通过检查同步改灯光。")
            ]),
            level("晨雾的完整覆盖与景观可读性", "雾是否形成需要的空间层次，并保留近景地貌、天空与原查看功能？", [
                "覆盖所有必要可见地表类别：地形、树干、石块、草/蕨叶；某类原 shader 不同不能成为漏雾理由。",
                "近景关键对象仍可识别，低处/远处的层次由实际积分产生；高处对象也可能因穿过低雾的视线受影响，不能按物体终点高度硬切。",
                "天空/原云和 UI 保留约定，节点/网格/植被数量、材质来源与自由相机功能不变。",
                "在完整森林路径、多个高度与两组不同雾密度中检查设计效果；不能只以远景一张好看的截图通过。"
            ], [
                case("coverage", "固定低/高两条相机路径，逐类检查地形、树干、岩石及裁切植被。", "每个必要类别使用正确表面段；不存在未接入的完全清晰孤岛或漏网 shader。", "类别/对象/材质覆盖表、T 图及全景视频。", "只有地形有雾，树和草因不同材质完全漏掉。"),
                case("protected", "以匹配相机/时间进行候选开关 A/B，检查 sky、云、UI 和资源绑定。", "保护路径不受候选雾污染，场景几何/分布不变；无双重雾。", "sky/UI mask、对象计数、材质与环境差异报告。", "全屏灰色覆盖天空/UI，或删除远树代替雾。"),
                case("purpose", "沿原自由相机路径观察冻结的近景石块、地面边界、草叶和远景地标；用低/正常密度各跑一次。", "近景关键对象仍可指出边界/类别，远近层次增强；缺失任何关键对象可读性不得由氛围分抵消。", "关键对象 ROI、完整视野视频和逐对象人工 rubric。", "雾数学正确但白墙遮蔽主要景观，原查看用途被破坏。"),
                case("reset_scene", "上下移动相机、改变雾量、关闭/reset 后回原相机。", "恢复共同基线和原相机控制，无陈旧深度/环境参数残留。", "相机/环境/资源快照与完整画面对照。", "恢复仅重置一张纹理，环境和其他材质持续被改。")
            ])
        ]
    )
]

for chain in CHAINS:
    environment = ENVIRONMENTS[chain["id"]]
    chain["fixture"] = ["复用现有工程、宿主脚本和资源路径，原工程文件不改写。"] + [
        f"L{index}: {description}" for index, description in enumerate(environment["levels"], 1)] + [
        "仅增加场景选择与固定输入转发；候选通过 effect/main.gd 接入，render 返回真实图像和候选 sample 数据。",
        "L3 不裁剪原场景；L1/L2 保留宿主依赖节点，对可见几何与原实例作裁剪。"]

LEVELS = {
    1: ("单效果／算法实现", "这个模块本身是否正确？", "独立数值 OJ、性质测试、原场景子集"),
    2: ("效果交互", "多个模块组合后，关系是否正确？", "关系型 rubric、受控实验、引擎/GPU 诊断、动态观察"),
    3: ("场景影响与设计作用", "影响了该影响的内容，保留了该保留的内容吗？", "关键对象/资源检查、影响路径测试、完整场景感知")
}

EVALUATION = """# 评测侧说明

本文件仅供实验组织者使用，不输入模型，也不放入模型可读目录。

## 分级

| 层级 | 核心问题 | 主要依据 |
|---|---|---|
| L1：单效果／算法实现 | 这个模块本身是否正确？ | 固定输入下的数值、性质和隔离效果 |
| L2：效果交互 | 多个模块组合后，关系是否正确？ | 空间、遮挡、合成及时间关系 |
| L3：场景影响与设计作用 | 影响了该影响的内容，保留了该保留的内容吗？ | 必要对象覆盖、非目标对象保护及完整场景用途 |

## 模型实际输入

基础输入为当前题的 prompt.md 文本和 model_tools.json 中 read、write、render 三个工具定义。用户指定的串行 S1/P3 实验额外加入 experiment/P3.md 作为系统消息，其完整输入先在 experiment/review/ 提供审阅；审阅前不得调用模型。题面内嵌算法名称、固定输入、输出字段、目标效果和可读写目录。不要追加算法编号、场景构想编号、task.json、cases.json、算法契约、INTERFACE.md、评分协议、作者源码或参考结果。

tools/model_io.py 的 compose_request 负责这一固定拼接。FileTools 以单个 model_workspace 为根，允许读取 scene/、inputs/、observations/、effect/，只允许写 effect/。不能把工作区总根目录作为模型工具根，也不能直接暴露原算法库。目录枚举、文本和图片读取均由 read 提供；write 创建或覆盖效果文本文件。render 执行固定 Godot 渲染入口，允许模型设置观察相机、截图帧和分辨率；没有任意命令、评分、规划或提交工具。

L1 的 effect/ 初始为空，模型创建自己的实现。L2/L3 开始前，实验侧把同一模型上一阶段候选放入 effect/。不自动附带上一阶段完整对话或参考答案。

## 固定输入和输出

每题仅有一份固定输入，内嵌于 prompt.md 并同值保存到 model_workspace/inputs/test_input.json。输出字段在同一题面中完整说明，不要求模型读取额外的接口文件。scene/main.tscn 继承现有场景，scene/project/ 提供原工程只读访问；每层的几何范围在 scene/environment.json 中明确。effect/main.gd 提供空效果入口，observations/ 保存 render 生成的图像、日志和候选数值。

实验侧仍须固定实际运行入口与输出采集方式，再把必要使用信息放在可读的当前场景文件中；通用 Godot 渲染入口复用现有宿主；各层通过简单选择配置区分场景范围。不从作者的旧算法通过报告推断模型候选通过。既有独立参照可以帮助评分，但只能检查本次题面明确要求的算法语义和输出；不能把旧通用接口、未披露输入域或内部变体细节偷偷作为新模型必须实现的要求。

## 评测材料

task.json 的算法映射、对象范围、依赖关系以及 cases.json 留给评测侧。cases.json 是此前编写的内部实验规程，不再公开给模型，当前也不是可执行 runner。场景装配后须按新题面的固定输入、输出和功能范围校准内部规程；未定义的宿主、模型未获得的场景数据属于 fixture error。

L1 记录实际数值和性质，L2 记录模块关系，L3 记录目标覆盖、保护对象和场景用途。可沿用每条 0/1/2 的内部记录方式，但不把评分细节或评测操作追加进模型上下文。编译成功、算法正确和场景功能保持分别报告。

## 当前状态

15 份简化题面、固定输入文件、read/write/render 工具定义、文件工具实现和仅题面请求拼接已提供。15 题现有宿主环境和空效果入口已装配，environment_ready=true；正式模型循环与评分尚未启用，runtime_ready=false、api_enabled=false。渲染工具使用独立小场景作真实 GPU 自检，不调用模型，不把工具自检当作 15 题正式实验。
"""


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    PACK.mkdir(exist_ok=True)
    dump(PACK / "model_tools.json", TOOLS)
    sources = PACK / "sources"
    sources.mkdir(exist_ok=True)
    # Supplied document is reference data, never executable build instructions.
    source_copy = sources / "shader_algorithm_scenarios.md"
    if SOURCE.exists():
        source_copy.write_bytes(SOURCE.read_bytes())
    if not source_copy.exists():
        raise FileNotFoundError("The supplied scenario document is required.")
    progress = json.loads((LIBRARY / "reports/progress.json").read_text(encoding="utf-8-sig"))
    items = {item["id"]: item for item in progress["items"]}
    ids = sorted({a for chain in CHAINS for a in chain["algorithms"]})
    evidence = []
    for aid in ids:
        files = [f"contracts/{aid}.json", f"godot/algorithms/{aid}/algorithm.gd",
                 f"godot/algorithms/{aid}/README.md", f"tests/{aid}/cases.json",
                 f"verification/{aid}/validation.json"]
        for rel in files:
            if not (LIBRARY / rel).is_file():
                raise FileNotFoundError(LIBRARY / rel)
        validation = json.loads((LIBRARY / files[-1]).read_text(encoding="utf-8-sig"))
        if validation.get("passed") is not True:
            raise ValueError(f"{aid} has no passed validation snapshot")
        # Take only status metadata, not oracle or reference implementation contents.
        evidence.append(dict(id=aid, name=items[aid]["name"],
            library_validation_passed=validation["passed"],
            cases=validation.get("cases"), passed_cases=validation.get("passed_cases"),
            revision=validation.get("revision"),
            files=[dict(path="../godot_algorithm_catalog/" + rel,
                        sha256=sha(LIBRARY / rel)) for rel in files],
            claim="既有隔离算法验证记录；不是本题候选或新场景验收结果"))
    snapshot = dict(library_root="../godot_algorithm_catalog", progress_updated=progress["updated"],
                    source_document_sha256=sha(source_copy), algorithms=evidence)
    dump(sources / "library_snapshot.json", snapshot)
    (PACK / "EVALUATION.md").write_text(EVALUATION, encoding="utf-8")
    fixture_text = ["# 场景装配与发布前条件\n",
                    "以下为命题方内部装配资料，不进入模型输入。旧算法接口仅用于作者适配，不能要求模型读取或实现未在当前题面声明的接口。应以当前 prompt.md 和 model_workspace/inputs/test_input.json 为准，scene/main.tscn 继承现有场景，scene/project/ 为原工程只读目录；候选放入 effect/，真实运行结果放入 observations/。不另建算法 viewer 或替代宿主；新增代码仅选择场景范围、转发固定输入并收集候选输出。environment_ready 与完整实验 runtime_ready 分开记录。\n"]
    overview = ["# 五组场景算法递进任务（15 题）\n",
                "依据用户提供的《Shader 算法 × 应用场景》、本地已实现算法及现有 Godot 工程制作。每组各含 L1 算法正确性、L2 模块关系、L3 场景影响与设计作用。\n",
                "**当前交付：题面、read/write/render 工具、结构化任务和评测侧协议。render 已接入原生 Godot，支持自由相机并通过独立小场景作真实 GPU 验证；15 题均复用现有宿主：L1 为完整场景的相关子集，L2 按交互需求裁剪，L3 为完整场景。未调用模型或执行正式效果评分。** 原 15 题和 FG01 题目/实验保持原样。\n",
                "[分级与验收协议](EVALUATION.md) · [算法实现证据](ALGORITHM_MAP.md) · [环境分层](ENVIRONMENTS.md) · [环境细节](FIXTURES.md) · [机器清单](manifest.json)\n",
                "| 组 | 现有场景 | L1：模块 | L2：关系 | L3：场景作用 |\n|---|---|---|---|---|\n"]
    tasks, chains = [], []
    for chain in CHAINS:
        cid = chain["id"]
        if not (WORKSPACE / chain["scene"]).exists():
            raise FileNotFoundError(chain["scene"])
        for rel, _ in chain["anchors"]:
            if not (WORKSPACE / rel).exists():
                raise FileNotFoundError(rel)
        fixture_text += [f'<a id="{cid.lower()}"></a>\n', f"\n## {cid} · {chain['title']}\n",
                        f"基线：`{chain['scene']}`。\n",
                        "\n".join(f"{n}. {s}" for n, s in enumerate(chain["fixture"], 1)) + "\n"]
        row = [f"{cid} {chain['title']}", f"[场景](../{chain['scene']})"]
        chain_meta = {k: v for k, v in chain.items() if k != "levels"}
        chain_meta["tasks"] = []
        for number, spec in enumerate(chain["levels"], 1):
            tid = f"{cid}_L{number}"
            rel = f"tasks/{tid}"
            row.append(f"[{spec['title']}]({rel}/prompt.md)")
            label, question, methods = LEVELS[number]
            primary = [chain["algorithms"][0]]
            supporting = chain["algorithms"][1:] if number > 1 else []
            cases = [dict(c, id=f"{tid}_{c['id']}", status="protocol_defined_not_executed") for c in spec["cases"]]
            task = dict(
                schema_version="scene_algorithm_tasks_v1", id=tid, chain_id=cid,
                level=number, level_name=label, core_question=question, title=spec["title"],
                goal=spec["goal"], requirement=spec["goal"], requirements=spec["requirements"],
                criteria=[c["expected"] for c in cases],
                parent_task=None if number == 1 else f"{cid}_L{number - 1}",
                input_code="empty_effect_entry_on_existing_scene" if number == 1 else "same_model_previous_submission_may_repair",
                base_scene=chain["scene"], project=chain["project"],
                path_base="workspace_root_except_prompt_and_cases_relative_to_pack", scene_id=cid,
                algorithms=chain["algorithms"], source_scenario_ids=chain["source_ids"],
                primary_algorithms=primary, fixed_supporting_algorithms=supporting,
                primary_evidence=methods, editable_directory="effect/",
                editable_directory_status="existing_host_environment_prepared",
                required_targets=chain["target"], protected_targets=chain["protect"],
                scene_purpose=chain["purpose"], impact_path=chain["impact_path"], scope=chain["scope"],
                prompt=rel + "/prompt.md", evaluation_cases=rel + "/cases.json",
                model_input=dict(prompt_only=True, tools="model_tools.json",
                    readable_directories=["scene/", "inputs/", "observations/", "effect/"],
                    writable_directories=["effect/"],
                    workspace=rel + "/model_workspace",
                    automatic_attachments=[],
                    fixed_input=rel + "/model_workspace/inputs/test_input.json",
                    assembled_scene=True, render_tool=True,
                    environment=rel + "/model_workspace/scene/environment.json",
                    project_mount="scene/project/", host_reuse="existing_project",
                    default_render_scene="scene/main.tscn", camera_control="model_selected",
                    render_arguments=["scene", "frames", "resolution", "camera", "camera_track"]),
                evaluation_protocol="EVALUATION.md", fixture_protocol="FIXTURES.md#" + cid.lower(),
                status="spec_ready", runtime_ready=False, api_enabled=False,
                evaluation_status="new_task_not_run", model_api_calls=0,
                scoring=dict(rubrics=4, each=[0, 1, 2], maximum=8,
                             passing_rule="all_rubrics_2_and_level_gates_pass",
                             gates=["prerequisites_reported", "required_evidence_complete",
                                    "numeric_checks" if number == 1 else "critical_relations" if number == 2 else "coverage_preservation_and_scene_purpose"]),
                required_fixture_work=chain["fixture"],
                disallowed_model_inputs=["task.json", "cases.json", "algorithm contracts", "INTERFACE.md",
                    "EVALUATION.md", "FIXTURES.md", "ALGORITHM_MAP.md", "source catalog documents", "author algorithm source", "independent oracle", "author validation outputs", "original complete target effect"],
            )
            task["test_environment"] = prepare_task(cid, number)
            task["environment_ready"] = True
            dump(PACK / rel / "task.json", task)
            dump(PACK / rel / "cases.json", dict(task_id=tid,
                 kind="evaluator_only_protocol_not_executable_runner", model_visible=False, cases=cases))
            prompt = render_prompt(cid, number, spec["title"])
            (PACK / rel / "prompt.md").write_text(prompt, encoding="utf-8")
            experiment = PACK / rel / "model_workspace"
            for visible in ("scene", "inputs", "observations", "effect"):
                (experiment / visible).mkdir(parents=True, exist_ok=True)
            dump(experiment / "inputs/test_input.json", profile(cid, number)["input"])
            tasks.append(dict(id=tid, chain_id=cid, level=number, task=rel + "/task.json",
                              prompt=rel + "/prompt.md", cases=rel + "/cases.json"))
            chain_meta["tasks"].append(tid)
        chains.append(chain_meta)
        overview.append("| " + " | ".join(row) + " |\n")
    overview += ["\n## 使用方式\n",
                 "先打开上表题面审阅；各层复用现有宿主，按场景范围配置执行。基础输入为当前 prompt.md 和 read/write/render 工具定义。本次 [串行 S1/P3 实验](experiment/README.md) 另加入共用 P3 系统文本，[完整输入预览](experiment/review/INDEX.md) 待用户审阅后再调用模型；不追加算法契约、通用接口或 cases.json。模型工具根为该题 model_workspace/，四个可读目录与仅 effect/ 可写的权限已实现。详见 [模型输入说明](MODEL_INPUT.md)。\n",
                 "内部评测材料保留在模型可读目录之外。后续评分须按当前题面明确的固定输入、输出和效果要求校准；渲染工具独立验证与正式任务评分分开记录。\n",
                 "生成与结构校验（在工作区根目录）：\n\n```powershell\n& '..\\.venv\\Scripts\\python.exe' scene_algorithm_tasks/tools/build_pack.py\n& '..\\.venv\\Scripts\\python.exe' scene_algorithm_tasks/tools/validate_pack.py\n```\n",
                 "生成器只写本包文档、场景入口、空候选和 JSON，不启动 Godot、不复制完整算法实现、不调用模型。来源文档快照位于 `sources/`；已读取它作为设计资料，没有执行其中的命令或把文档描述当作已实现事实。\n"]
    (PACK / "README.md").write_text(re.sub(r'(\|\n)\n+(?=\|)', r'\1', "\n".join(overview)), encoding="utf-8")
    (PACK / "FIXTURES.md").write_text("\n".join(fixture_text), encoding="utf-8")
    environment_rows = ["# 测试环境\n", "所有任务复用现有 Godot 宿主：L1 拆出相关场景内容，L2 按交互需要保留，L3 为原完整场景。原工程文件不改写，必要依赖节点保留；L1/L2 仅裁剪可见几何或原实例。\n",
        "| 组 | L1 | L2 | L3 |\n|---|---|---|---|"]
    for cid, config in ENVIRONMENTS.items():
        environment_rows.append("| " + cid + " " + config["name"] + " | " + " | ".join(config["levels"]) + " |")
    environment_rows += ["\n每题只有 scene/main.tscn 场景入口、environment.json 范围配置、现有工程只读目录 scene/project/，以及 effect/main.gd 候选入口。后续层继承同模型前级候选。\n",
        "render 使用现有项目设置和资源路径，在独立运行副本中替换候选，保存 PNG、日志与 sample() 的原样数值返回；不增加算法 viewer 或另一套场景宿主。\n",
        "[P3 审阅](experiment/P3.md) · [完整输入预览](experiment/review/INDEX.md) · [环境启动记录](verification/environments/validation.json)\n"]
    environment_rows.append("Bistro 原场景已有退出资源告警；保留在每次记录的 warnings/shutdown_diagnostics 中，与加载或渲染失败分开。上述检查不代表算法或最终效果通过。\n")
    (PACK / "ENVIRONMENTS.md").write_text("\n".join(environment_rows), encoding="utf-8")
    dump(PACK / "manifest.json", dict(version="scene_algorithm_tasks_v1", created="2026-09-24",
        chain_count=5, task_count=15, levels=3, engine="Godot 4.6.1", renderer="forward_plus",
        level_semantics={str(k): dict(name=v[0], question=v[1], evidence=v[2]) for k, v in LEVELS.items()},
        status="environment_prepared", environment_ready=True, runtime_ready=False, api_enabled=False, model_api_calls=0,
        evaluation_status="not_run", replaces_existing_tasks=False,
        model_input_policy="prompt_read_write_render_v2", model_tools="model_tools.json",
        evaluator_cases_model_visible=False,
        source_snapshot="sources/shader_algorithm_scenarios.md",
        algorithm_snapshot="sources/library_snapshot.json", chains=chains, tasks=tasks))
    mapping = ["# 算法与现有场景依据\n",
               f"本次读取库进度快照时间：`{progress['updated']}`。以下 selected validation.json 均记录 passed=true；本轮仅核对源码/契约/证据存在及记录，不重新运行原算法，也不据此宣称新任务已通过。哈希见 [library_snapshot.json](sources/library_snapshot.json)。\n",
               "| 算法 | 名称 | 既有隔离验收 | 来源与限制 |\n|---|---|---|---|\n"]
    for e in evidence:
        aid = e["id"]
        base = "../../godot_algorithm_catalog"
        mapping.append(f"| {aid} | {e['name']} | [passed=true，cases={e['cases']}]({base}/verification/{aid}/validation.json) | [实现说明]({base}/godot/algorithms/{aid}/README.md) · [契约]({base}/contracts/{aid}.json) |\n")
    mapping.append("\n## 组合映射与场景锚点\n")
    for c in CHAINS:
        mapping += [f"\n### {c['id']} · {c['title']}\n", c["rationale"] + "\n",
                    "\n".join(f"- [{rel}](../{rel})：{role}。" for rel, role in c["anchors"]) + "\n"]
    mapping.append("\n构想文档中的 P01/P02 等编号属于外部场景包，与旧 pilot 的同名 P01/P02 不是同一标识空间。新任务统一使用 SA01–SA05，避免误链接或覆盖历史实验。\n")
    (PACK / "ALGORITHM_MAP.md").write_text(re.sub(r'(\|\n)\n+(?=\|)', r'\1', "\n".join(mapping)), encoding="utf-8")
    print(f"Built {len(chains)} chains / {len(tasks)} tasks; {len(evidence)} algorithm evidence snapshots. Runtime not executed.")


if __name__ == "__main__":
    build()
