"""Small level selections over the five existing Godot projects."""
from pathlib import Path
import json
import shutil

PACK = Path(__file__).resolve().parents[1]
WORKSPACE = PACK.parent
PROFILES = {
    "SA01": {
        "name": "草地", "project": "forest_grass_lab/project", "entry": "scenes/GrassPatch.tscn",
        "kind": "grass", "targets": ["GrassCards_0", "GrassCards_1", "GrassCards_2", "GrassCards_3"],
        "levels": [
            "从原草地拆出通行路径附近的一排草，保留原草片网格、地面、玩家、光照和相机；关闭风动。",
            "扩大为路径附近的三排草，使用原风参数、玩家回放和阴影，观察风动与压草的组合。",
            "使用原完整草地，保留全部 335 张草片、地面标记、玩家、相机和 UI。"],
        "cameras": [([4, 3, 5], [0, .4, 0]), ([5, 4, 6], [0, .4, 0]), None]},
    "SA02": {
        "name": "海面", "project": "realistic/projects/water",
        "entry": "example/boujie_water_shader/water_shader_examples.tscn", "kind": "water",
        "targets": ["DeepOcean"],
        "levels": [
            "从原海面展示中拆出 DeepOcean 的中心网格，用原网格生成器设置 8 米、64 格子区域，保留原水材质、光照和相机；只实现波面。",
            "保留中心及相邻 LOD 网格、海床，观察波面与泡沫的时空关系；隐藏无关展示物。",
            "使用原完整海面展示，保留全部海面 LOD、海床、地形、独立材质样品、HUD 和相机控制。"],
        "cameras": [([6, 4, 8], [0, 0, 0]), ([12, 7, 16], [0, 0, 0]), None]},
    "SA03": {
        "name": "Bistro 路面", "project": "realistic/projects/bistro", "entry": "MainScene.tscn",
        "kind": "bistro", "targets": ["Level Geometry/Ground/Ground"],
        "levels": [
            "从原 Bistro 拆出 Ground 路面，保留原地面网格、材质、光照和相机；只观察四层材质混合。",
            "保留 Ground 与相邻 Section01 街区，观察湿区、细节法线、受光和干湿边界的关系。",
            "使用原完整 Bistro 街景，保留各街区、室内入口、道具、碰撞、日夜控制和相机。"],
        "cameras": [([-3, 5, 8], [-3, 0, 0]), ([-3, 3, 8], [-3, 1, -2]), None]},
    "SA04": {
        "name": "FPS 靶场", "project": "projects/fps", "entry": "pilot/F01.tscn",
        "kind": "fps", "targets": ["World/TargetA", "World/TargetB"],
        "levels": [
            "从原靶场拆出 TargetA 和地面，保留原靶标网格、材质、光照和观察相机；验证表面投影。",
            "保留 TargetA、TargetB、Cover、地面与射击控制，观察移动受体、命中、遮挡和寿命。",
            "使用原完整靶场，保留全部靶标、掩体、墙地、角色、武器、准星、碰撞和射击流程。"],
        "cameras": [([-1, 4, 3], [-4, 2, -3]), ([8, 7, 12], [0, 1, -2]), None]},
    "SA05": {
        "name": "森林", "project": "realistic/projects/forest", "entry": "Main.tscn",
        "kind": "forest", "targets": ["Main Terrain", "Decorations-Forest", "Groundcover"],
        "levels": [
            "从原森林拆出地形及原视点附近的岩石，保留原空间坐标、天空、云、光照和自由相机；观察高度雾。",
            "加入同一区域的树木、草和蕨叶，观察真实遮挡、植被空隙与雾的颜色合成。",
            "使用原完整森林，保留全部地形、树木、岩石、Groundcover、天空、云和自由相机。"],
        "cameras": [None, None, None]},
}

SKIP_PARTS = {".git", "__pycache__", "reference", "verification", "dew"}


def source_project(root):
    """Only author-created environment IDs can resolve a native project mount."""
    marker = Path(root) / ".environment.json"
    if not marker.is_file():
        return None
    data = json.loads(marker.read_text(encoding="utf-8"))
    return WORKSPACE / PROFILES[data["group"]]["project"]


def visible_source_path(root, relative):
    project = source_project(root)
    if project is None:
        raise FileNotFoundError("No existing project is mounted")
    relative = Path(relative)
    if any(p in SKIP_PARTS or p.startswith(".") for p in relative.parts):
        raise PermissionError("Project cache and private files are not model-visible")
    result = (project / relative).resolve()
    if not result.is_relative_to(project.resolve()):
        raise PermissionError("Path leaves the mounted project")
    return result


def definition(group, level):
    profile = PROFILES[group]
    camera = profile["cameras"][level-1]
    return {"host": "existing_project", "name": profile["name"], "kind": profile["kind"],
            "level": level, "scope": ["scene_subset", "interaction_subset", "full_scene"][level-1],
            "description": profile["levels"][level-1], "source_entry": profile["entry"],
            "targets": profile["targets"], "project_directory": "scene/project/",
            "candidate_entry": "effect/main.gd", "source_host_modified": False,
            "camera": {"position": camera[0], "look_at": camera[1]} if camera else None,
            "selection": "Preserve host dependency nodes; restrict visible geometry and original instances for L1/L2. L3 has no scene selection."}


def prepare_task(group, level):
    root = PACK / "tasks" / f"{group}_L{level}" / "model_workspace"
    for directory in ("scene", "effect", "inputs", "observations"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    data = definition(group, level)
    (root / ".environment.json").write_text(json.dumps({"group": group, "level": level}) + "\n", encoding="utf-8")
    (root / "scene/environment.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The original root keeps its host script, child nodes, resources and controls.
    scene = '[gd_scene load_steps=2 format=3]\n[ext_resource type="PackedScene" path="res://' + data["source_entry"] + '" id="source"]\n[node name="TaskScene" instance=ExtResource("source")]\n'
    if group == "SA01":
        scene += "level = 3\n"
    (root / "scene/main.tscn").write_text(scene, encoding="utf-8")
    shutil.copyfile(PACK / "tools/environment_setup.gd", root / "scene/environment_setup.gd")
    (root / "scene/README.md").write_text(
        "# 当前测试环境\n\n" + data["description"] + "\n\n"
        "main.tscn 直接继承原场景。project/ 是现有工程的只读目录，可用 read 列出和读取；其中 res:// 路径相对于该工程根。\n\n"
        "effect/main.gd 是效果入口；后续层级继承同模型前一级文件：configure(scene_root, test_input) 接收原场景与固定输入；step(dt) 在每个截图帧步进前调用；sample() 返回题面要求的数值字典。入口提供空实现，算法由你完成。可在 effect/ 中添加 shader、资源与辅助脚本。\n\n"
        "场景裁剪仅用于当前层；必要的宿主依赖节点保留。数值结果由 render 写入 observations/ 下的 samples.json；默认视角适合本层，也可自行指定相机。\n",
        encoding="utf-8")
    entry = root / "effect/main.gd"
    if not entry.exists():
        entry.write_text('''extends Node
# Candidate entry; the existing scene host remains unchanged.
var scene_root: Node
var test_input: Dictionary

func configure(root: Node, inputs: Dictionary) -> void:
    scene_root = root
    test_input = inputs

func step(_dt: float) -> void:
    pass

func sample() -> Dictionary:
    return {}  # Implement the numerical output requested by the task.
''', encoding="utf-8")
    if group == "SA01":
        shader = root / "effect/grass.gdshader"
        if not shader.exists():
            shutil.copyfile(WORKSPACE / PROFILES[group]["project"] / "effect/grass.gdshader", shader)
    return data


def stage_project(root, overlay):
    """Reuse one native project copy per group; called only under the shared GPU lock."""
    root, overlay = Path(root), Path(overlay)
    marker = json.loads((root / ".environment.json").read_text(encoding="utf-8"))
    group = marker["group"]
    source = source_project(root)
    cache = PACK / "runtime/host_projects" / group
    project = cache / "project"
    cache.mkdir(parents=True, exist_ok=True)
    if not (cache / "prepared.json").exists():
        def ignore(folder, names):
            return [n for n in names if n in SKIP_PARTS or n in {"editor", "shader_cache"} and Path(folder).name == ".godot"]
        shutil.copytree(source, project, dirs_exist_ok=True, ignore=ignore)
        (cache / "prepared.json").write_text(json.dumps({"source": PROFILES[group]["project"], "host": "unchanged_copy"}), encoding="utf-8")
    # Restore any native source file changed by the previous candidate before reuse.
    for original in source.rglob("*"):
        relative = original.relative_to(source)
        if not original.is_file() or any(p in SKIP_PARTS or p == ".godot" for p in relative.parts):
            continue
        target = project / relative
        if not target.exists() or (target.stat().st_size, target.stat().st_mtime_ns) != (original.stat().st_size, original.stat().st_mtime_ns):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
    old = cache / "overlay.json"
    # Remove only files that this staging function recorded, then restore originals.
    for name in json.loads(old.read_text(encoding="utf-8")) if old.exists() else []:
        target = (project / name).resolve()
        if not target.is_relative_to(project.resolve()):
            raise PermissionError("Invalid cached overlay path")
        if target.is_file():
            target.unlink()
        original = source / name
        if original.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
    paths = []
    for item in overlay.rglob("*"):
        if not item.is_file() or item.name == "project.godot":
            continue
        relative = item.relative_to(overlay)
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, target)
        paths.append(relative.as_posix())
    old.write_text(json.dumps(paths), encoding="utf-8")
    return project
