"""Native Godot renderer. Only observation controls are accepted from model tools."""
from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from render_spec import validate_request

HERE = Path(__file__).resolve().parent
PILOT = HERE.parents[1]
ENGINE = PILOT / "tools/godot/Godot_v4.6.1-stable_win64.exe"
_spec = importlib.util.spec_from_file_location("scene_render_lock", PILOT / "forest_grass_lab/experiment/local_lock.py")
_lock_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lock_module)
file_lock = _lock_module.file_lock


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def under(root, path):
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise PermissionError("render file path leaves the experiment")
    return resolved


def snapshot(root, project):
    records = []
    for directory in ("scene", "effect", "inputs"):
        folder = under(root, root / directory)
        if not folder.is_dir():
            raise FileNotFoundError(f"Missing experiment directory: {directory}/")
        for source in sorted(folder.rglob("*")):
            if any(p in {".godot", ".git", "__pycache__"} for p in source.relative_to(root).parts):
                continue
            if source.is_symlink() or (hasattr(source, "is_junction") and source.is_junction()):
                raise PermissionError("render snapshots require ordinary files, not links")
            under(root, source)
            if not source.is_file():
                continue
            relative = source.relative_to(root)
            target = project / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            with target.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            records.append({"path": relative.as_posix(), "sha256": digest})
    return records


def execute(command, log, environment, timeout):
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as stream:
        try:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                env=environment, startupinfo=startup, timeout=timeout, shell=False,
                cwd=str(log.parent))
            code, timed_out = result.returncode, False
        except subprocess.TimeoutExpired:
            code, timed_out = -1, True
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    errors = list(dict.fromkeys(line for line in lines if "ERROR:" in line or "Error at line" in line or "SHADER ERROR" in line))
    # Keep exact native shutdown diagnostics separate from execution failures.
    # In particular, the original Bistro probe also reports resources at shutdown.
    shutdown = []
    if code == 0 and "MODEL_RENDER_COMPLETE" in lines:
        completion = lines.index("MODEL_RENDER_COMPLETE")
        shutdown = [line for line in lines[completion+1:]
                    if re.match(r"ERROR: \d+ resources still in use at exit", line)]
        errors = [line for line in errors if line not in shutdown]
    if code:
        errors.append("Godot timed out" if timed_out else f"Godot exit code {code}")
    return {"exit_code": code, "seconds": round(time.monotonic() - started, 3), "errors": errors,
            "warnings": list(dict.fromkeys(line for line in lines if "WARNING:" in line)) + shutdown,
            "shutdown_diagnostics": shutdown}


def render(experiment_root, arguments, *, engine=ENGINE, timeout=180):
    root = Path(experiment_root).resolve(strict=True)
    inputs_path = under(root, root / "inputs/test_input.json")
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    environment_file = root / "scene/environment.json"
    arguments = dict(arguments)
    if environment_file.exists() and arguments.get("scene", "scene/main.tscn") == "scene/main.tscn" and "camera" not in arguments:
        default_camera = json.loads(environment_file.read_text(encoding="utf-8")).get("camera")
        if default_camera:
            arguments["camera"] = default_camera
    request = validate_request(arguments, inputs)
    scene = under(root, root / request["scene"])
    if not scene.is_file():
        return {"ok": False, "error_kind": "scene_not_prepared", "error":
                "Entry scene does not exist. Read scene/ for the current scene, or create effect/preview.tscn for an isolated preview.",
                "scene": request["scene"], "images": []}
    engine = Path(engine).resolve(strict=True)
    run_id = datetime.now().strftime("render_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    observation_base = under(root, root / "observations")
    private_base = under(root, root / ".render_runs")
    out = observation_base / run_id
    out.mkdir(parents=True)
    project = private_base / run_id / "project"
    project.mkdir(parents=True)
    records = snapshot(root, project)
    (project / "project.godot").write_text('''config_version=5

[application]
config/name="Model Effect Preview"

[display]
window/size/viewport_width=960
window/size/viewport_height=640

[rendering]
renderer/rendering_method="forward_plus"
''', encoding="utf-8")
    shutil.copyfile(HERE / "render_capture.gd", project / "_render_capture.gd")
    request["output_dir"] = out.as_posix()
    save(project.parent / "request.json", request)
    save(out / "request.json", {k: v for k, v in request.items() if k != "output_dir"})
    save(out / "files.json", {"files": records, "input_sha256": hashlib.sha256(inputs_path.read_bytes()).hexdigest()})
    environment = {key: val for key, val in os.environ.items()
                   if not any(word in key.upper() for word in ("API_KEY", "TOKEN", "PASSWORD", "SECRET"))}
    environment["APPDATA"] = str(PILOT / "runtime/AppData")
    errors, warnings, phases = [], [], {}
    try:
        # Nonblocking acquisition avoids hidden indefinite waiting behind another experiment.
        with file_lock(PILOT / "forest_grass_lab/runtime/render.lock", wait=False):
            runtime_project = project
            if (root / ".environment.json").exists():
                from environments import stage_project
                runtime_project = stage_project(root, project)
            phases["import"] = execute([str(engine), "--path", str(runtime_project), "--headless", "--editor", "--import"],
                                       out / "import.log", environment, timeout)
            errors.extend(phases["import"]["errors"])
            warnings.extend(phases["import"]["warnings"])
            if not errors:
                width, height = request["resolution"]
                phases["capture"] = execute([str(engine), "--path", str(runtime_project), "--audio-driver", "Dummy",
                    "--rendering-method", "forward_plus", "--windowed", "--resolution", f"{width}x{height}",
                    "--fixed-fps", str(request["fixed_fps"]), "--script", "res://_render_capture.gd",
                    "--", "--render-request=" + (project.parent / "request.json").as_posix()],
                    out / "godot.log", environment, timeout)
                errors.extend(phases["capture"]["errors"])
                warnings.extend(phases["capture"]["warnings"])
    except (OSError, RuntimeError) as error:
        errors.append(f"Renderer could not start or GPU is busy: {error}")
    capture_path = out / "capture.json"
    capture = json.loads(capture_path.read_text(encoding="utf-8")) if capture_path.exists() else {}
    if not capture.get("completed"):
        errors.append("Render did not complete")
    captured_frames = [item.get("frame") for item in capture.get("captures", [])]
    if captured_frames != request["frames"]:
        errors.append("Requested frames were not all captured")
    images = []
    for item in capture.get("captures", []):
        expected_name = f"frame_{int(item['frame']):04d}.png"
        path = under(out, out / expected_name)
        if not path.is_file():
            errors.append(f"Missing PNG: {expected_name}")
            continue
        data = path.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append(f"Invalid PNG: {expected_name}")
            continue
        images.append({"path": path.relative_to(root).as_posix(), "mime_type": "image/png", "encoding": "base64",
                       "data": base64.b64encode(data).decode("ascii"), "frame": item["frame"],
                       "camera": item["camera"], "width": item["width"], "height": item["height"]})
    metadata = {"ok": not errors, "errors": errors, "warnings": warnings,
                "observation_directory": out.relative_to(root).as_posix(),
                "scene_kind": "target" if request["scene"].startswith("scene/") else "candidate_preview",
                "request": {k: v for k, v in request.items() if k != "output_dir"},
                "phases": phases, "capture": capture, "model_api_calls": 0, "visual_quality": "not_scored"}
    samples_file = out / "samples.json"
    if samples_file.is_file():
        metadata["samples_file"] = samples_file.relative_to(root).as_posix()
    save(out / "result.json", metadata)
    return {**metadata, "images": images if not errors else [],
            "logs": [p.relative_to(root).as_posix() for p in (out / "import.log", out / "godot.log") if p.exists()]}
