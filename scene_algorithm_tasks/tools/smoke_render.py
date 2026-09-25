"""Run real GPU verification of the tool on an authored fixture, not task solutions."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from model_io import FileTools

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK / "verification/render_tool/model_workspace"
for folder in ("scene", "inputs", "effect", "observations"):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
(ROOT / "inputs/test_input.json").write_text(json.dumps({"dt_seconds": 1/60, "steps": 60, "record_after_steps": [1, 60]}), encoding="utf-8")
(ROOT / "scene/main.tscn").write_text('''[gd_scene load_steps=2 format=3]
[ext_resource type="Script" path="res://scene/fixture.gd" id="1"]
[node name="Fixture" type="Node3D"]
script = ExtResource("1")
''', encoding="utf-8")
(ROOT / "scene/fixture.gd").write_text('''extends Node3D
var elapsed := 0.0
var object: MeshInstance3D
var material: ShaderMaterial
func _ready() -> void:
    var environment := WorldEnvironment.new()
    var settings := Environment.new()
    settings.background_mode = Environment.BG_COLOR
    settings.background_color = Color(0.08, 0.11, 0.17)
    environment.environment = settings
    add_child(environment)
    material = ShaderMaterial.new()
    material.shader = load("res://effect/color.gdshader")
    object = MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(1.0, 1.4, 1.8)
    object.mesh = mesh
    object.material_override = material
    add_child(object)
    object.position = Vector3(-0.5, 0.7, 0)
    var other := MeshInstance3D.new()
    var sphere := SphereMesh.new()
    sphere.radius = 0.45
    sphere.height = 0.9
    other.mesh = sphere
    var plain := StandardMaterial3D.new()
    plain.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    plain.albedo_color = Color(0.05, 0.8, 0.65)
    other.material_override = plain
    other.position = Vector3(1.1, 0.45, -0.4)
    add_child(other)
    var camera := Camera3D.new()
    camera.position = Vector3(4, 3, 5)
    add_child(camera)
    camera.look_at(Vector3(0, 0.5, 0))
    camera.make_current()
func preview_reset(_inputs: Dictionary) -> void:
    elapsed = 0.0
func preview_step(dt: float) -> void:
    elapsed += dt
    object.rotation.y = elapsed * 0.8
    material.set_shader_parameter("elapsed", elapsed)
''', encoding="utf-8")
tools = FileTools(ROOT)
shader = 'shader_type spatial; render_mode unshaded; uniform float elapsed = 0.0; void fragment(){ALBEDO=vec3(0.85,0.22+0.12*sin(elapsed),0.04);}'
assert tools.call("write", {"path": "effect/color.gdshader", "content": shader})["ok"]
before = hashlib.sha256((ROOT / "inputs/test_input.json").read_bytes()).hexdigest()
requests = [
    {"frames": [1, 60], "resolution": [512, 384], "camera": {"position": [4, 3, 5], "look_at": [0, 0.5, 0]}},
    {"frames": [1], "resolution": [512, 384], "camera": {"position": [0, 8, 0], "look_at": [0, 0, 0],
        "up": [0, 0, -1], "projection": "orthogonal", "orthogonal_size": 5}},
    {"frames": [1, 30], "resolution": [512, 384], "camera": {"position": [0, 3, 5], "look_at": [0, 0.5, 0]},
     "camera_track": [{"frame": 1, "position": [0, 3, 5], "look_at": [0, 0.5, 0]},
                      {"frame": 30, "position": [5, 3, 0], "look_at": [0, 0.5, 0]}]},
]
# Also exercise a model-authored preview with native frame processing and its own camera.
preview_script = (ROOT / "scene/fixture.gd").read_text(encoding="utf-8").replace("func preview_step(dt: float)", "func _process(dt: float)")
tools.call("write", {"path": "effect/preview.gd", "content": preview_script})
preview_scene = (ROOT / "scene/main.tscn").read_text(encoding="utf-8").replace("res://scene/fixture.gd", "res://effect/preview.gd")
tools.call("write", {"path": "effect/preview.tscn", "content": preview_scene})
requests.append({"scene": "effect/preview.tscn", "frames": [1, 60], "resolution": [512, 384]})
records = []
for request in requests:
    result = tools.call("render", request)
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", result.get("error")),
                      "output": result.get("observation_directory")}), flush=True)
    assert result["ok"], {k: v for k, v in result.items() if k != "images"}
    assert len(result["images"]) == len(request["frames"])
    assert result["capture"]["renderer"] == "forward_plus"
    assert result["capture"]["display"] != "headless"
    for image in result["images"]:
        with Image.open(ROOT / image["path"]) as png:
            assert png.size == (512, 384)
            assert max(ImageStat.Stat(png.convert("RGB")).stddev) > 5, "Unexpected blank render"
        assert tools.call("read", {"path": image["path"]})["kind"] == "image"
    records.append({k: v for k, v in result.items() if k != "images"})
    records[-1]["images"] = [{k: v for k, v in image.items() if k != "data"} for image in result["images"]]

first = Image.open(ROOT / records[0]["images"][0]["path"]).convert("RGB")
later = Image.open(ROOT / records[0]["images"][1]["path"]).convert("RGB")
top = Image.open(ROOT / records[1]["images"][0]["path"]).convert("RGB")
assert ImageChops.difference(first, later).getbbox(), "Frame selection did not capture animation"
assert ImageChops.difference(first, top).getbbox(), "Camera override did not change the image"
assert records[1]["capture"]["captures"][0]["camera"]["projection"] == 1
assert records[2]["capture"]["captures"][-1]["camera"]["position"] == [5, 3, 0]
assert records[3]["scene_kind"] == "candidate_preview"
assert records[3]["capture"]["step_mode"] == "native_fixed_fps"
native_first = Image.open(ROOT / records[3]["images"][0]["path"]).convert("RGB")
native_later = Image.open(ROOT / records[3]["images"][1]["path"]).convert("RGB")
assert ImageChops.difference(native_first, native_later).getbbox(), "Native processing did not advance"
missing = tools.call("render", {"scene": "scene/missing.tscn", "frames": [1]})
assert missing["error_kind"] == "scene_not_prepared" and not missing["images"]
assert before == hashlib.sha256((ROOT / "inputs/test_input.json").read_bytes()).hexdigest()

# Invalid candidate must return diagnostics, never reuse PNGs from a previous run.
tools.call("write", {"path": "effect/color.gdshader", "content": "shader_type spatial; THIS_IS_NOT_VALID"})
failure = tools.call("render", {"frames": [1], "resolution": [128, 128]})
assert not failure["ok"] and not failure.get("images"), failure
tools.call("write", {"path": "effect/color.gdshader", "content": shader})
summary = {"passed": True, "scope": "actual GPU render tool fixture, not 15 task integration scores",
           "successful_runs": records, "compile_error_returned": True,
           "error_run": failure.get("observation_directory"), "fixed_input_unchanged": True, "model_api_calls": 0}
(ROOT.parent / "validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("Render GPU smoke checks passed.", flush=True)
