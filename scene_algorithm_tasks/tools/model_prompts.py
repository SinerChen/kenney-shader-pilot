"""Model-facing task text. Author catalog IDs are never rendered into prompts."""
import json
from render_spec import RENDER_TOOL
from environments import definition


PROFILES = {
    "SA01": {
        "algorithms": ["持久化交互场、指数时间衰减、双线性场采样及沿草高加权的顶点弯曲",
                       "持久化交互场与根部固定变形，组合程序风动和一致的变形阴影",
                       "持久化交互场、程序风动，以及按实例绑定的草片变形与阴影"],
        "input": {
            "seed": 20260924, "dt_seconds": 0.016666666666666666,
            "steps": 240, "record_after_steps": [1, 60, 120, 240],
            "patch": {"origin_xz_m": [-4, -4], "size_m": 8, "resolution": [64, 64]},
            "interaction": {"radius_m": 0.95, "strength": 0.95,
                            "persistence_per_60hz_step": 0.92, "bend_m": 0.35, "flatten_m": 0.1},
            "player_keyframes": [{"time_s": 0, "position_xz_m": [-3, 0]},
                                 {"time_s": 2, "position_xz_m": [3, 0]},
                                 {"time_s": 4, "position_xz_m": [3, 0]}],
            "interaction_active_until_s": 2,
            "wind": {"strength": 0, "speed": 1.6, "direction_xz": [1, 0.35]},
            "camera": "overview"
        },
        "input_notes": "Y 向上，位置和长度使用米。玩家位置在关键帧间线性插值，速度由该轨迹求得；每步先推进到新时间，再衰减并写入当前交互。到 2 秒时移除交互者，历史继续衰减。场纹素中心均匀分布在固定世界 patch；场外采样为零。草片根部和归一化高度从当前场景读取。",
        "output": {
            "samples": "按 record_after_steps 顺序输出，每项含 step、elapsed_s、field_rgba、positions、normals",
            "field_rgba": "64×64 行优先浮点数组，每点 [方向X×强度, 方向Z×强度, 压低强度, 0]",
            "positions": "按场景提供的实例及顶点顺序排列的世界坐标 [x,y,z] 数组",
            "normals": "与 positions 一一对应的单位世界法线 [x,y,z] 数组"
        },
        "effects": [
            "草在玩家经过的位置局部向外弯倒；根部固定，中上部产生主要位移。玩家离开后保留短时轨迹并平滑恢复；草片持续可见。该阶段风动关闭。",
            "在已有局部压草效果上加入给定风动。远草随风摆动，近处草同时响应玩家；根部固定，草的受光和阴影与实际变形对应。",
            "把风动与压草应用到完整草地中的所有目标草实例。整条经过路径都能留下逐渐恢复的痕迹；作用范围外草保持风动，地面、玩家和 UI 保留原样，原相机与玩家控制继续可用。"
        ]
    },
    "SA02": {
        "algorithms": ["Gerstner 方向波叠加，计算完整水平/垂直位移、切向和几何法线",
                       "Gerstner 波、水平位移 Jacobian 压缩检测、参数附着的泡沫增长与指数衰减",
                       "Gerstner 波与参数附着泡沫，组合固定世界坐标采样和海面 LOD 材质绑定"],
        "input": {
            "dt_seconds": 0.016666666666666666, "steps": 180,
            "record_after_steps": [1, 60, 120, 180],
            "grid": {"size": [64, 64], "length_xz_m": [8, 8], "origin_xz_m": [0, 0]},
            "waves": [
                {"amplitude_m": 0.2, "wavelength_m": 4, "speed_m_s": 1,
                 "direction_xz": [1, 0], "phase_rad": 0, "steepness": 0.4},
                {"amplitude_m": 0.1, "wavelength_m": 8, "speed_m_s": 0.5,
                 "direction_xz": [0, 1], "phase_rad": 0.5, "steepness": 0.3}],
            "foam": {"enabled": False, "threshold": 1, "grow_per_s": 1,
                     "decay_per_s": 1, "initial_value": 0},
            "camera": "overview"
        },
        "input_notes": "Y 向上，XZ 网格为周期参数域；q=(列号×8/64,行号×8/64)，从 0 编号。波相位取 k·(方向·q−速度·时间)+初相位，k=2π/波长。初始时间为 0，每步只推进一次。泡沫开启时，以周期中央差分求水平位移 Jacobian，源项为 max(threshold−J,0)，先指数衰减旧值再加入 grow×dt×源项，结果限制在 [0,1]；泡沫始终附着于同一 q 的变形位置。",
        "output": {
            "samples": "按 record_after_steps 输出；每项含 step、elapsed_s、positions、normals、jacobian、foam",
            "positions": "64×64 行优先的波面世界位置 [x,y,z]",
            "normals": "同顺序的单位世界法线 [x,y,z]",
            "jacobian": "同顺序的水平位移映射行列式，每点一个浮点数",
            "foam": "同顺序的泡沫覆盖度，每点 [0,1]；泡沫关闭时全零"
        },
        "effects": [
            "水面呈现方向明确的几何波浪，波峰具有水平位移；法线和受光跟随真实波面。",
            "波面发生水平压缩的位置生成泡沫，已有泡沫逐渐衰减并随对应波面位置运动。泡沫与波浪共享时间和坐标。",
            "效果覆盖目标海面的近、中、远网格；移动相机时波形与泡沫保持世界位置连续。其他水材质展示球、冰、黑曜石、海床、展台、天空和 UI 保留原效果，相机游览继续可用。"
        ]
    },
    "SA03": {
        "algorithms": ["四层同时竞争的高度驱动材质混合",
                       "四层高度材质混合与重定向法线混合（RNM）",
                       "四层高度材质混合、RNM，以及按表面和区域遮罩限定的湿润材质绑定"],
        "input": {
            "transition": 0.25, "wetness": 0.6,
            "layers": [
                {"height": 0.8, "control": 0.4, "albedo_linear": [0.45, 0.42, 0.38], "roughness": 0.8, "metallic": 0, "normal_ts": [0, 0, 1]},
                {"height": 0.8, "control": 0.6, "albedo_linear": [0.25, 0.23, 0.21], "roughness": 0.25, "metallic": 0, "normal_ts": [0, 0, 1]},
                {"height": 0.2, "control": 0.2, "albedo_linear": [0.12, 0.09, 0.06], "roughness": 0.6, "metallic": 0, "normal_ts": [0, 0, 1]},
                {"height": 0, "control": 0, "albedo_linear": [0, 0, 0], "roughness": 0.5, "metallic": 0, "normal_ts": [0, 0, 1]}],
            "detail_normal_ts": [0, 0, 1], "detail_enabled": False,
            "eligible_region": "outdoor_road_wet", "camera": "road_close"
        },
        "input_notes": "四层依次表示干石材、湿石材、缝隙泥层、备用层；高度采用同一单位，颜色在线性空间。输入 control 已包含 wetness 的分配，不能再次乘 wetness。先比较各层 height×control 得到共同最高值，再按 transition 建立非负竞争量并归一化；竞争量在乘 control 前加 1e-6，transition 下限为 1e-5，归一化分母下限为 1e-6。场景应用时从当前场景的固定高度图和区域遮罩取得逐点输入。",
        "output": {
            "weights": "按四层原顺序输出四个浮点权重",
            "albedo_linear": "同一组权重混合得到的线性 RGB",
            "roughness_metallic_height": "分别输出 roughness、metallic、height 三个浮点字段",
            "base_normal_ts": "混合后归一化的切线空间法线；相消时为 [0,0,1]",
            "final_normal_ts": "细节关闭时等于 base_normal_ts；开启时为 RNM 组合后的单位法线"
        },
        "effects": [
            "材质根据局部高度和控制量形成连续覆盖，颜色、粗糙度、金属度和基础法线使用同一组混合权重。",
            "湿色、粗糙度与法线变化对应同一片湿区，细节法线附着于原石材大结构。光照随真实表面朝向变化，保留石缝和石脊细节。",
            "只湿润指定室外石路区域，完整覆盖其目标表面。干燥路脊、门口、人行区、室内地面、桌椅、招牌、玻璃和角色保留原材质与功能；街道入口与通行边界仍清晰可辨。"
        ]
    },
    "SA04": {
        "algorithms": ["基于深度重建的盒投影贴花、六面裁剪、朝向过滤和材质混合",
                       "投影贴花，组合局部命中锚点变换、当前深度遮挡及单贴花生命周期",
                       "投影贴花、受体白名单和独立材质绑定，保留原射击与遮挡关系"],
        "input": {
            "dt_seconds": 0.016666666666666666, "steps": 180,
            "record_after_steps": [1, 30, 60, 180],
            "viewport": [128, 128],
            "camera": {"eye": [0, 0, 4], "target": [0, 0, 0], "up": [0, 1, 0], "fov_degrees": 60, "near": 0.1, "far": 20},
            "surface": {"vertices": [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]],
                        "triangles": [[0, 1, 2], [0, 2, 3]], "albedo_linear": [0.5, 0.5, 0.5]},
            "projector": {"origin": [0, 0, 0], "rotation_degrees": [0, 0, 0],
                          "scale": [0.5, 0.5, 0.2], "cos_reject": 0.2, "cos_full": 0.8,
                          "albedo_linear": [0.15, 0.03, 0.01], "opacity": 0.8},
            "hit": {"event_id": 1, "target": "target_a", "time_s": 0,
                    "local_position": [0, 0, 0], "local_normal": [0, 0, 1]},
            "lifetime_s": 2, "allowed_targets": ["target_a", "target_b"]
        },
        "input_notes": "世界坐标 Y 向上，角度为度，长度为米；投影盒局部范围为 [-0.5,0.5]³，UV=local.xy+0.5。深度采用近端 1、远端 0 的 reverse-Z。朝向阈值之间平滑过渡。初始事件在首次步进前注入；同时只保留一个贴花，寿命按显式时间计算。场景阶段同名逻辑目标由当前场景绑定；命中位置/法线为目标局部坐标。",
        "output": {
            "samples": "按 record_after_steps 输出；每项含 step、elapsed_s、active_target 和逐像素数据",
            "pixel_data": "按 128×128 行优先输出 visible、world_position、projector_local_position、uv、opacity、normal、albedo_linear",
            "background": "visible=false 时位置/UV/法线填 null，opacity 为 0",
            "active_target": "有效期内为目标名，到期后为 null；到期后材质恢复当前受体的原值"
        },
        "effects": [
            "贴花投射到真实可见受体表面，受投影体和朝向限制，贴花材料参与后续照明。",
            "贴花出现在实际命中的局部位置，目标运动时随目标移动；前景会遮住贴花。新命中替换旧贴花，重复事件不延长寿命，到期恢复原材质。",
            "目标白名单内所有命中表面都能显示局部反馈。其他靶标、掩体、墙地、目标背面、武器和 UI 不被贴花污染；原伤害、碰撞、准星、瞄准和射击流程保留。"
        ]
    },
    "SA05": {
        "algorithms": ["有限视线段的指数高度雾积分与 Beer–Lambert 透射合成",
                       "指数高度雾，组合世界位置重建、植被深度覆盖和线性颜色合成",
                       "指数高度雾与按可见表面应用的场景合成，保留天空及 UI 路径"],
        "input": {
            "reference_height_m": 0, "density_per_m": 0.01, "height_falloff_per_m": 0.15,
            "fog_color_linear": [0.65, 0.72, 0.78],
            "rays": [
                {"start": [0, 0, 0], "end": [10, 0, 0], "background_linear": [0.2, 0.4, 0.1]},
                {"start": [0, 0, 0], "end": [8, 6, 0], "background_linear": [0.2, 0.4, 0.1]},
                {"start": [0, 6, 0], "end": [8, 0, 0], "background_linear": [0.2, 0.4, 0.1]}],
            "camera": "forest_overview", "preserve_sky": True, "preserve_ui": True
        },
        "input_notes": "Y 向上，距离为米，密度为每米，所有颜色在线性空间。密度随世界高度按指数下降：rho(y)=density×exp(−height_falloff×(y−reference_height))。积分使用完整起终点间的有限线段，输出透射率与合成颜色。场景阶段每个有效像素的端点来自当前相机与最近可见表面。",
        "output": {
            "rays": "按输入射线顺序输出 optical_depth、transmittance、opacity、color_linear",
            "optical_depth": "沿有限线段积分得到的非负光学厚度",
            "transmittance_opacity": "分别为 [0,1] 的透射率和不透明度，两者之和为 1",
            "color_linear": "透射率×原颜色 + 不透明度×雾颜色的 RGB"
        },
        "effects": [
            "低处密度较大，射线长度和高度共同决定雾量；同样长度的不同高度视线产生相应的空间层次。",
            "雾跟随世界高度分布。前景叶片及其空隙使用各自实际可见表面的深度，线性颜色只合成一次，天空和 UI 保留。",
            "雾覆盖地形、树干、岩石、草和蕨叶，形成完整森林的远近与高低层次。近景地面边界和关键景物仍可辨识，原天空、云、植被分布和自由相机功能保留。"
        ]
    }
}

TOOLS = [
    {"name": "read", "description": "读取当前实验目录中的 UTF-8 文本、图像，或列出目录内容。",
     "parameters": {"type": "object", "properties": {
         "path": {"type": "string", "description": "相对实验根目录的路径；. 列出可读目录。"},
         "start_line": {"type": "integer", "minimum": 1},
         "max_lines": {"type": "integer", "minimum": 1, "maximum": 1000}},
         "required": ["path"], "additionalProperties": False}},
    {"name": "write", "description": "在 effect/ 内创建或覆盖 UTF-8 文本文件，content 为完整内容。",
     "parameters": {"type": "object", "properties": {
         "path": {"type": "string", "description": "effect/ 内的相对文件路径。"},
         "content": {"type": "string", "description": "文件完整文本。"}},
         "required": ["path", "content"], "additionalProperties": False}}
]


TOOLS.append(RENDER_TOOL)


def profile(chain_id, number):
    data = json.loads(json.dumps(PROFILES[chain_id], ensure_ascii=False))
    inputs = data["input"]
    if number > 1:
        if chain_id == "SA01":
            inputs["wind"]["strength"] = 0.22
        elif chain_id == "SA02":
            inputs["foam"]["enabled"] = True
        elif chain_id == "SA03":
            inputs["detail_enabled"] = True
            inputs["detail_normal_ts"] = [0.3, 0, 0.9539392014169457]
        elif chain_id == "SA04":
            inputs["target_motion"] = {"translation_m_s": [0.1, 0, 0], "yaw_degrees_s": 15}
        elif chain_id == "SA05":
            inputs["scene_density_reference"] = "initial_camera_world_y"
    return data


def readable_json(value, depth=0):
    inline = json.dumps(value, ensure_ascii=False)
    if len(inline) + depth * 2 <= 110 or not isinstance(value, (dict, list)):
        return inline
    indent = "  " * depth
    child_indent = indent + "  "
    if isinstance(value, dict):
        rows = [child_indent + json.dumps(k, ensure_ascii=False) + ": " + readable_json(v, depth + 1) for k, v in value.items()]
        return "{\n" + ",\n".join(rows) + "\n" + indent + "}"
    rows = [child_indent + readable_json(v, depth + 1) for v in value]
    return "[\n" + ",\n".join(rows) + "\n" + indent + "]"


def render_prompt(chain_id, number, title):
    data = profile(chain_id, number)
    parts = [f"# {title}",
        "在当前 Godot 实验中实现以下效果。" + ("在 effect/ 中创建实现。" if number == 1 else "继续修改 effect/ 中上一阶段保留的实现。"),
        "## 测试环境", definition(chain_id, number)["description"],
        "复用现有 Godot 宿主。scene/main.tscn 为本层入口，scene/project/ 可读取原工程，scene/environment.json 说明本层范围。effect/main.gd 是效果入口：configure 接收原场景和固定输入，step 推进效果，sample 返回下述数值输出；可在 effect/ 中添加所需 shader 和辅助文件。",
        "## 使用的算法", data["algorithms"][number - 1] + "。",
        "## 固定测试输入", "本次输入固定如下，inputs/test_input.json 保存同一份数据。",
        "```json\n" + readable_json(data["input"]) + "\n```",
        data["input_notes"], "## 输出要求",
        "将实现保存到 effect/。运行输出采用以下字段和顺序；render 将 sample 返回的数据保存到 observations/ 下的 samples.json：",
        "\n".join(f"- `{key}`：{value}。" for key, value in data["output"].items()),
        "## 需要生成的效果", data["effects"][number - 1],
        "## 可观察和修改的目录",
        "所有路径相对于当前实验根目录。\n\n"
        "| 目录 | 权限 | 内容 |\n|---|---|---|\n"
        "| scene/ | 只读 | 当前实验场景、资产和固定宿主文件 |\n"
        "| inputs/ | 只读 | 本次固定输入 |\n"
        "| observations/ | 只读 | 当前实现运行后产生的图像、日志及数值结果 |\n"
        "| effect/ | 可读写 | 本次需要实现或修改的效果文件 |",
        "## 工具", "- `read(path, start_line=1, max_lines=400)`：读取文件或列出目录；图像以图像数据返回。\n"
        "- `write(path, content)`：在 effect/ 内创建或覆盖文件，content 为完整文本。\n"
        "- `render(scene=\"scene/main.tscn\", camera=..., frames=..., resolution=..., camera_track=...)`：运行当前实现并返回真实 PNG、日志路径和相机记录。",
        "## 自主渲染观察",
        "你可以自行选择观察角度、距离、透视或正交投影、视野、截图帧和图像分辨率，也可以设置相机轨迹。题面中的 camera 仅为默认观察设置；render 的相机参数只用于本次观察，不改写固定输入文件。",
        "例如，从自选位置观察第 1、60、120 帧：\n\n```json\n"
        '{"camera":{"position":[6,4,8],"look_at":[0,0,0],"fov_degrees":50},"frames":[1,60,120],"resolution":[960,640]}\n```',
        "camera.position、look_at 和可选 up 使用世界坐标。俯视可设置 position=[0,8,0]、look_at=[0,0,0]、up=[0,0,-1]；正交视图用 projection=\"orthogonal\" 和 orthogonal_size。省略 camera 时使用场景相机。",
        "camera_track 为按帧递增的 [{frame,position,look_at}, ...]，位置与目标在关键帧之间线性插值。每次可取 1–4 个递增截图帧，范围不超过固定输入 steps，最多 720 帧。resolution 为 [宽,高]，各边 128–1920，总像素最多 2073600。",
        "每次 render 从当前文件的新场景实例开始。返回的图像可直接观察，也可通过 read 再读取 observations/ 下的 PNG、日志、参数与结果。可通过日志定位编译或运行问题。需要隔离预览时，可在 effect/ 中创建 preview.tscn 并指定 scene=\"effect/preview.tscn\"。",
        "根据实现需要自行调用 read、write 和 render，调用顺序及是否渲染由你决定。完成后简要说明修改了哪些文件和实现了什么效果。"]
    return "\n\n".join(parts) + "\n"
