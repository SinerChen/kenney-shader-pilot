"""Model-controlled observation settings, separate from fixed task inputs."""
import math
from pathlib import PurePosixPath

VECTOR = {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}
RENDER_TOOL = {
    "name": "render",
    "description": "运行当前 Godot 场景或效果预览，返回真实 PNG、日志和相机记录。可自行设定视角、截图帧、分辨率及相机轨迹；固定测试输入不变。",
    "parameters": {
        "type": "object", "properties": {
            "scene": {"type": "string", "description": "默认 scene/main.tscn；也可指定 effect/ 内自行编写的 .tscn 预览。"},
            "frames": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 720},
                       "minItems": 1, "maxItems": 4, "description": "递增、不重复；不得超过固定输入 steps。省略时采用固定输入的记录帧。"},
            "resolution": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2,
                           "description": "[宽,高]，各为 128–1920，总像素不超过 2073600，默认 [960,640]。"},
            "camera": {"type": "object", "properties": {
                "position": VECTOR, "look_at": VECTOR, "up": VECTOR,
                "projection": {"type": "string", "enum": ["perspective", "orthogonal"]},
                "fov_degrees": {"type": "number", "minimum": 5, "maximum": 150},
                "orthogonal_size": {"type": "number", "minimum": 0.01, "maximum": 100000},
                "near": {"type": "number", "minimum": 0.001, "maximum": 1000},
                "far": {"type": "number", "minimum": 0.01, "maximum": 100000}},
                "required": ["position", "look_at"], "additionalProperties": False,
                "description": "世界坐标。省略时使用场景相机；俯视时 up 不可与观察方向平行。"},
            "camera_track": {"type": "array", "minItems": 1, "maxItems": 8, "items": {
                "type": "object", "properties": {"frame": {"type": "integer", "minimum": 1, "maximum": 720},
                    "position": VECTOR, "look_at": VECTOR},
                "required": ["frame", "position", "look_at"], "additionalProperties": False},
                "description": "需同时传 camera；位置与观察目标按帧线性插值，首尾之外保持端点。"}
        }, "required": [], "additionalProperties": False
    }
}


def finite(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be finite in [{low},{high}]")
    return float(value)


def vector(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} needs three numbers")
    return [finite(v, -100000, 100000, label) for v in value]


def check_basis(position, target, up):
    direction = [b - a for a, b in zip(position, target)]
    dl = sum(v*v for v in direction)
    ul = sum(v*v for v in up)
    cross = [direction[1]*up[2]-direction[2]*up[1], direction[2]*up[0]-direction[0]*up[2], direction[0]*up[1]-direction[1]*up[0]]
    if dl < 1e-10 or ul < 1e-10 or sum(v*v for v in cross) < 1e-10 * dl * ul:
        raise ValueError("camera position/look_at/up must define a nondegenerate view")


def camera_at(camera, track, frame):
    result = dict(camera)
    if not track:
        return result
    a = b = track[0]
    weight = 0.0
    if frame >= track[-1]["frame"]:
        a = b = track[-1]
    elif frame > track[0]["frame"]:
        for left, right in zip(track, track[1:]):
            if left["frame"] <= frame <= right["frame"]:
                a, b = left, right
                weight = (frame-a["frame"]) / (b["frame"]-a["frame"])
                break
    for key in ("position", "look_at"):
        result[key] = [x+(y-x)*weight for x, y in zip(a[key], b[key])]
    return result


def validate_request(arguments, inputs):
    allowed = {"scene", "frames", "resolution", "camera", "camera_track"}
    if not isinstance(arguments, dict) or set(arguments) - allowed:
        raise ValueError("unsupported render arguments")
    scene = arguments.get("scene", "scene/main.tscn")
    if not isinstance(scene, str) or ":" in scene or "\\" in scene:
        raise ValueError("scene must be a relative scene/ or effect/ .tscn path")
    parts = PurePosixPath(scene).parts
    if not parts or parts[0] not in {"scene", "effect"} or ".." in parts or not scene.endswith(".tscn"):
        raise ValueError("scene must stay inside scene/ or effect/")
    upper = min(720, inputs.get("steps", 720))
    if type(upper) is not int or upper < 1:
        raise ValueError("fixed input steps must be positive")
    defaults = inputs.get("record_after_steps", [1, min(60, upper), min(120, upper)])
    defaults = sorted(set(defaults))[:4]
    frames = arguments.get("frames", defaults)
    if not isinstance(frames, list) or not 1 <= len(frames) <= 4 or any(type(f) is not int or not 1 <= f <= upper for f in frames) or frames != sorted(set(frames)):
        raise ValueError(f"frames must be 1–4 increasing unique integers in [1,{upper}]")
    resolution = arguments.get("resolution", [960, 640])
    if not isinstance(resolution, list) or len(resolution) != 2 or any(type(v) is not int or not 128 <= v <= 1920 for v in resolution) or resolution[0]*resolution[1] > 2073600:
        raise ValueError("invalid render resolution")
    dt = finite(inputs.get("dt_seconds", 1.0/60.0), 0.001, 0.1, "fixed dt_seconds")
    camera = arguments.get("camera")
    if camera is not None:
        fields = {"position", "look_at", "up", "projection", "fov_degrees", "orthogonal_size", "near", "far"}
        if not isinstance(camera, dict) or set(camera)-fields or not {"position", "look_at"} <= set(camera):
            raise ValueError("camera needs position/look_at and only documented fields")
        camera = dict(camera)
        for key in ("position", "look_at"):
            camera[key] = vector(camera[key], key)
        camera["up"] = vector(camera.get("up", [0, 1, 0]), "up")
        camera["projection"] = camera.get("projection", "perspective")
        if camera["projection"] not in {"perspective", "orthogonal"}:
            raise ValueError("unsupported projection")
        for key, default, low, high in (("fov_degrees", 50, 5, 150), ("orthogonal_size", 8, .01, 100000),
                                        ("near", .05, .001, 1000), ("far", 1000, .01, 100000)):
            camera[key] = finite(camera.get(key, default), low, high, key)
        if camera["far"] <= camera["near"]:
            raise ValueError("far must be greater than near")
        check_basis(camera["position"], camera["look_at"], camera["up"])
    track = arguments.get("camera_track", [])
    if not isinstance(track, list) or len(track) > 8 or (track and camera is None):
        raise ValueError("camera_track needs a camera and at most 8 keyframes")
    previous = 0
    for point in track:
        if not isinstance(point, dict) or set(point) != {"frame", "position", "look_at"}:
            raise ValueError("camera_track keyframe fields are frame/position/look_at")
        f = point["frame"]
        if type(f) is not int or not previous < f <= frames[-1]:
            raise ValueError("camera_track frames must increase within the requested duration")
        previous = f
        vector(point["position"], "position")
        vector(point["look_at"], "look_at")
    if camera:
        for frame in range(1, frames[-1] + 1):
            view = camera_at(camera, track, frame)
            check_basis(view["position"], view["look_at"], view["up"])
    return {"scene": scene, "frames": frames, "resolution": resolution,
            "camera": camera, "camera_track": track, "dt_seconds": dt,
            "fixed_fps": max(1, round(1/dt))}
