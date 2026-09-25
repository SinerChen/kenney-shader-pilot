"""Record dense native Godot frames from saved candidates for human review only."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from environments import stage_project
from model_render import ENGINE, PILOT, execute, file_lock, snapshot
from render_spec import validate_request

PACK = Path(__file__).resolve().parents[1]
RUNTIME = PACK / "runtime/video_review"
MAX_GPU_SECONDS = 110
VERSION = "continuous-video-v1"
TERMINAL = {"model_finished", "model_incomplete", "budget_exhausted", "output_truncated"}


def read(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def effect_hashes(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted((root / "effect").rglob("*"))
            if p.is_file() and p.name != "plan.json"}


def gpu_window():
    state = read(PACK / "runtime/experiment/status.json", {})
    if state.get("status") in ("completed", "paused_error", "not_started"):
        return True
    current = state.get("current", {})
    return current.get("status") == "retry_wait" and current.get("retry_at", 0) - time.time() > MAX_GPU_SECONDS + 20


def settings(root, task):
    inputs = read(root / "inputs/test_input.json")
    environment = read(root / "scene/environment.json", {})
    reports = [read(p, {}) for p in sorted((root / "observations").glob("*/result.json"))]
    candidates = [r for r in reports if r.get("ok") and r.get("request", {}).get("scene") == "scene/main.tscn"]
    # Preserve the last model view; prefer its preceding detail view over a very distant overhead diagnostic.
    camera = None
    camera_track = []
    origin = "host_default"
    for report in reversed(candidates):
        proposed = report["request"].get("camera")
        if proposed:
            delta = [a-b for a,b in zip(proposed["position"], proposed["look_at"])]
            distance = math.sqrt(sum(value*value for value in delta))
            if distance > 80 and abs(delta[1])/max(distance, .001) > .95:
                continue
        camera = proposed
        camera_track = report["request"].get("camera_track", [])
        origin = report.get("observation_directory", "model_target_view")
        break
    if camera is None and environment.get("camera"):
        camera = environment["camera"]
    steps = inputs.get("steps", 360)
    args = {"scene": "scene/main.tscn", "frames": [steps], "resolution": [1280, 720]}
    if camera:
        args.update(camera=camera, camera_track=camera_track)
    request = validate_request(args, inputs)
    stride = max(1, round(request["fixed_fps"] / 30))
    request["frames"] = list(range(stride, steps+1, stride))
    request["video_fps"] = request["fixed_fps"] / stride
    request["orbit"] = task.startswith(("SA03", "SA05")) and not camera_track
    request["view_source"] = origin
    return request


def video_driver():
    """Use the same native stepping path; export every second frame without numeric sampling."""
    source = (PACK / "tools/render_capture.gd").read_text(encoding="utf-8")
    old = '\t\t\tif environment_setup:\n\t\t\t\tsamples.append('
    assert source.count(old) == 1
    source = source.replace(old, '\t\t\tif false and environment_setup:\n\t\t\t\tsamples.append(')
    source = source.replace('var filename := "frame_%04d.png" % frame', 'var filename := "frame_%06d.png" % (captures.size() + 1)')
    source = source.replace('var initial_frames := Engine.get_process_frames()', '''var video_camera := root.get_camera_3d()
	var video_start := video_camera.global_position
	var video_focus := video_start - video_camera.global_basis.z * 8.0
	if request.camera != null:
		video_focus = vec(request.camera.look_at)
	var initial_frames := Engine.get_process_frames()''')
    source = source.replace('\t\tset_view(frame)\n', '''		set_view(frame)
		if bool(request.get("orbit", false)):
			var angle := sin(float(frame - 1) / float(frames[-1] - 1) * TAU) * deg_to_rad(7.0)
			video_camera.global_position = video_focus + (video_start - video_focus).rotated(Vector3.UP, angle)
			video_camera.look_at(video_focus)
			video_camera.force_update_transform()
''')
    return source


def record(out, *, force=False):
    root = out / "model_workspace"
    candidate = effect_hashes(root)
    request = settings(root, out.name)
    fingerprint = hashlib.sha256(json.dumps({"version": VERSION, "effect": candidate, "inputs": sha(root / "inputs/test_input.json"),
                                           "request": request}, sort_keys=True).encode()).hexdigest()
    presentation = out / "presentation"
    previous = read(presentation / "latest.json", {})
    if previous.get("fingerprint") == fingerprint and previous.get("status") in ("ready", "failed") and not force:
        return previous
    if not gpu_window():
        return None
    folder = presentation / "versions" / (fingerprint[:16] + "_" + datetime.now().strftime("%H%M%S"))
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"status": "recording", "created": stamp(), "version": VERSION, "fingerprint": fingerprint,
            "task_id": out.name, "alias": out.parent.name, "candidate_sha256": candidate,
            "input_sha256": sha(root / "inputs/test_input.json"), "model_api_calls": 0,
            "purpose": "human_review_only", "fed_to_model": False, "counts_toward_model_budget": False,
            "request": request, "errors": [], "warnings": [], "directory": folder.relative_to(PACK).as_posix()}
    save(presentation / "latest.json", meta)
    save(RUNTIME / "status.json", {"status": "recording", "updated": stamp(), "current": f"{out.parent.name}/{out.name}"})
    overlay = folder / "snapshot"
    overlay.mkdir()
    records = snapshot(root, overlay)
    shutil.copy2(root / ".environment.json", overlay / ".environment.json")
    captured_candidate = {r["path"]: r["sha256"] for r in records if r["path"].startswith("effect/") and r["path"] != "effect/plan.json"}
    if captured_candidate != candidate:
        raise RuntimeError("Candidate changed while taking video snapshot")
    (overlay / "_render_capture.gd").write_text(video_driver(), encoding="utf-8")
    save(folder / "files.json", {"files": records, "driver_sha256": sha(overlay / "_render_capture.gd")})
    capture_request = dict(request, output_dir=folder.as_posix())
    save(folder / "request.json", capture_request)
    env = {key: value for key, value in os.environ.items() if not any(word in key.upper() for word in ("API_KEY", "TOKEN", "PASSWORD", "SECRET"))}
    env["APPDATA"] = str(PILOT / "runtime/AppData")
    try:
        with file_lock(PILOT / "forest_grass_lab/runtime/render.lock", wait=False):
            if not gpu_window():
                meta["status"] = "queued"
                save(presentation / "latest.json", meta)
                return None
            deadline = time.monotonic() + MAX_GPU_SECONDS
            project = stage_project(overlay, overlay)
            meta["import"] = execute([str(ENGINE), "--path", str(project), "--headless", "--editor", "--import"],
                                     folder / "import.log", env, max(1, deadline-time.monotonic()))
            meta["errors"].extend(meta["import"]["errors"])
            meta["warnings"].extend(meta["import"]["warnings"])
            if not meta["errors"]:
                meta["capture"] = execute([str(ENGINE), "--path", str(project), "--audio-driver", "Dummy", "--rendering-method", "forward_plus",
                    "--windowed", "--resolution", "1280x720", "--fixed-fps", str(request["fixed_fps"]), "--script", "res://_render_capture.gd",
                    "--", "--render-request=" + (folder / "request.json").as_posix()], folder / "godot.log", env, max(1, deadline-time.monotonic()))
                meta["errors"].extend(meta["capture"]["errors"])
                meta["warnings"].extend(meta["capture"]["warnings"])
    except OSError as error:
        meta.update(status="queued", errors=[str(error)])
        save(presentation / "latest.json", meta)
        return None
    capture = read(folder / "capture.json", {})
    actual = sorted(folder.glob("frame_*.png"))
    if not capture.get("completed") or len(actual) != len(request["frames"]):
        meta["errors"].append("Continuous capture did not finish every requested frame")
    if not meta["errors"]:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise RuntimeError("ffmpeg and ffprobe are required for real video export")
        meta["status"] = "encoding"
        save(presentation / "latest.json", meta)
        video = folder / "effect.mp4"
        command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(request["video_fps"]),
                   "-start_number", "1", "-i", str(folder / "frame_%06d.png"), "-c:v", "libx264", "-preset", "fast",
                   "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        encoded = subprocess.run(command, capture_output=True, text=True, timeout=120, creationflags=creationflags)
        (folder / "encode.log").write_text(encoded.stderr, encoding="utf-8")
        if encoded.returncode:
            meta["errors"].append("Video encoding failed: " + encoded.stderr[-1500:])
        else:
            probe = subprocess.run([ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                "stream=codec_name,width,height,avg_frame_rate,nb_read_frames,duration", "-of", "json", str(video)],
                capture_output=True, text=True, check=True, timeout=60, creationflags=creationflags)
            stream = json.loads(probe.stdout)["streams"][0]
            if int(stream["nb_read_frames"]) != len(actual):
                raise RuntimeError("Encoded video frame count mismatch")
            save(folder / "probe.json", stream)
            shutil.copy2(actual[len(actual)//2], folder / "poster.png")
            meta.update(video=video.relative_to(PACK).as_posix(), poster=(folder / "poster.png").relative_to(PACK).as_posix(),
                        fps=request["video_fps"], frame_count=len(actual), duration_seconds=float(stream["duration"]),
                        resolution=[stream["width"], stream["height"]], video_sha256=sha(video), codec=stream["codec_name"])
            # Remove only the frame files just encoded, after verifying their absolute containment.
            for frame in actual:
                resolved = frame.resolve()
                if not resolved.is_relative_to(folder.resolve()) or resolved.parent != folder.resolve():
                    raise RuntimeError("Invalid temporary frame path")
                resolved.unlink()
    meta["status"] = "failed" if meta["errors"] else "ready"
    meta["finished"] = stamp()
    meta["matches_current_files"] = effect_hashes(root) == candidate
    save(folder / "video.json", meta)
    save(presentation / "latest.json", meta)
    print(json.dumps({"run": f"{out.parent.name}/{out.name}", "status": meta["status"], "frames": meta.get("frame_count"),
                      "errors": meta["errors"]}, ensure_ascii=False), flush=True)
    return meta


def candidates():
    config = read(PACK / "runtime/experiment/run_config.json")
    state = read(PACK / "runtime/experiment/status.json", {})
    current = state.get("current", {})
    result = []
    for model in config["models"]:
        for task in config["task_order"]:
            out = PACK / "runs/s1_p3" / model["alias"] / task
            end = read(out / "result.json", {})
            if end.get("stop_reason") in TERMINAL:
                result.append(out)
    if current.get("status") in ("retry_wait", "paused_error"):
        out = PACK / "runs/s1_p3" / current["alias"] / current["task_id"]
        if out not in result and (out / "model_workspace/effect/main.gd").is_file():
            result.append(out)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--task", help="alias/task_id")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with file_lock(RUNTIME / "worker.lock", wait=False):
        while True:
            pending = 0
            outputs = candidates()
            if args.task:
                outputs = [out for out in outputs if f"{out.parent.name}/{out.name}" == args.task]
                if not outputs:
                    raise ValueError("Task has no stable saved candidate")
            for out in outputs:
                try:
                    result = record(out, force=args.force)
                    pending += result is None
                except Exception as error:
                    pending += 1
                    save(RUNTIME / "last_error.json", {"time": stamp(), "task": str(out), "error": str(error)})
                    print("Video review error: " + str(error), flush=True)
            states = [read(out / "presentation/latest.json", {}) for out in outputs]
            save(RUNTIME / "status.json", {"updated": stamp(), "status": "waiting_for_gpu_window" if pending else "watching" if args.watch else "finished",
                "eligible": len(outputs), "ready": sum(s.get("status") == "ready" for s in states),
                "failed": sum(s.get("status") == "failed" for s in states), "pending": pending, "model_api_calls": 0})
            if not args.watch:
                break
            time.sleep(10)


if __name__ == "__main__":
    main()
