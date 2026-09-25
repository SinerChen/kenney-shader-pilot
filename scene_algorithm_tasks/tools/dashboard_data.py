"""Build a read-only, compact dashboard snapshot from actual experiment artifacts."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile

from case_data import publish_case

PACK = Path(__file__).resolve().parents[1]
TERMINAL = {"model_finished", "model_incomplete", "budget_exhausted", "output_truncated"}
GROUPS = [("SA01", "草地交互", "持久交互场 · 顶点变形"), ("SA02", "海面与泡沫", "Gerstner 波 · 泡沫演化"),
          ("SA03", "湿润材质", "高度混合 · RNM 法线"), ("SA04", "命中贴花", "深度重建 · 投影贴花"),
          ("SA05", "森林高度雾", "视线积分 · 透射合成")]
_json_cache = {}
_hash_cache = {}


def read(path, default=None):
    try:
        stat = path.stat()
        key = (stat.st_mtime_ns, stat.st_size)
        old = _json_cache.get(path)
        if old and old[0] == key:
            return old[1]
        value = json.loads(path.read_text(encoding="utf-8"))
        _json_cache[path] = (key, value)
        return value
    except (OSError, ValueError):
        return default


def sha(path):
    stat = path.stat()
    key = (stat.st_mtime_ns, stat.st_size)
    old = _hash_cache.get(path)
    if old and old[0] == key:
        return old[1]
    value = hashlib.sha256(path.read_bytes()).hexdigest()
    _hash_cache[path] = (key, value)
    return value


def url(path, pack=PACK):
    if path.is_file() and path.resolve().is_relative_to(pack.resolve()):
        return path.relative_to(pack).as_posix()
    return None


def run_data(pack, model, task_id):
    out = pack / "runs/s1_p3" / model["alias"] / task_id
    root = out / "model_workspace"
    state = read(out / "status.json", {})
    result = read(out / "result.json", {})
    plan = read(root / "effect/plan.json", {})
    if not isinstance(plan, dict):
        plan = {}
    files = []
    current_hashes = {}
    for path in sorted((root / "effect").rglob("*")):
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            continue
        name = path.relative_to(root / "effect").as_posix()
        files.append({"name": name, "path": url(path, pack), "bytes": path.stat().st_size})
        if name != "plan.json":
            current_hashes["effect/" + name] = sha(path)
    renders = []
    for folder in sorted((root / "observations").glob("render_*")):
        report = read(folder / "result.json", {})
        capture = report.get("capture") or read(folder / "capture.json", {})
        request = report.get("request") or read(folder / "request.json", {})
        images = []
        for item in capture.get("captures", []):
            path = folder / f"frame_{int(item['frame']):04d}.png"
            if url(path, pack):
                images.append({"path": url(path, pack), "frame": item["frame"], "camera": item.get("camera"),
                               "width": item.get("width"), "height": item.get("height"), "elapsed_s": item.get("elapsed_s")})
        records = read(folder / "files.json", {}).get("files", [])
        rendered_hashes = {r["path"]: r["sha256"] for r in records
                           if r["path"].startswith("effect/") and r["path"] != "effect/plan.json"}
        renders.append({"id": folder.name, "index": len(renders) + 1, "ok": report.get("ok"),
                        "images": images, "errors": report.get("errors", []), "warnings": report.get("warnings", []),
                        "request": request, "scene_kind": report.get("scene_kind", "target"),
                        "matches_current_files": bool(rendered_hashes) and current_hashes == rendered_hashes,
                        "links": {name: url(folder / name, pack) for name in
                                  ("result.json", "request.json", "godot.log", "import.log", "samples.json", "files.json")}})
    video = read(out / "presentation/latest.json", {})
    if video:
        video = dict(video)
        video["matches_current_files"] = video.get("candidate_sha256") == current_hashes
        video["metadata_link"] = url(out / "presentation/latest.json", pack)
    stop = result.get("stop_reason")
    status = "paused_error" if stop in ("api_error", "local_error") else stop or state.get("status", "not_started")
    return {"alias": model["alias"], "task_id": task_id, "status": status,
            "terminal": stop in TERMINAL, "requests": state.get("requests", result.get("requests", 0)),
            "render_calls": state.get("render_calls", result.get("render_calls", 0)),
            "updated": state.get("updated", result.get("finished")), "error": result.get("error") or state.get("error"),
            "retry_at": state.get("retry_at"), "stop_reason": stop, "plan": plan, "renders": renders,
            "final_text": result.get("final_text", ""), "files": files, "video": video,
            "case_details": publish_case(pack, model["alias"], task_id),
            "links": {"status": url(out / "status.json", pack), "result": url(out / "result.json", pack),
                      "plan": url(root / "effect/plan.json", pack), "input": url(out / "input.json", pack),
                      "trajectory": url(out / "trajectory.jsonl", pack), "inheritance": url(out / "inheritance.json", pack),
                      "final": url(out / "final.md", pack)}}


def build(pack=PACK):
    config = read(pack / "runtime/experiment/run_config.json") or read(pack / "experiment/config.json", {})
    state = read(pack / "runtime/experiment/status.json", {"status": "not_started"})
    models = [{"alias": item["alias"], "name": item["model"]} for item in config.get("models", [])]
    tasks = []
    for task_id in config.get("task_order", []):
        task = read(pack / "tasks" / task_id / "task.json", {})
        group, level = task_id.split("_L")
        tasks.append({"id": task_id, "group": group, "level": int(level), "title": task.get("title", task_id),
                      "prompt": f"experiment/review/{task_id}.md", "task_prompt": f"tasks/{task_id}/prompt.md"})
    runs = [run_data(pack, model, task["id"]) for model in models for task in tasks]
    for model in models:
        selected = [run for run in runs if run["alias"] == model["alias"]]
        model["completed"] = sum(run["terminal"] for run in selected)
        model["started"] = sum(run["requests"] > 0 for run in selected)
        model["total"] = len(selected)
    return {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"), "state": state,
            "models": models, "groups": [{"id": g, "title": title, "algorithm": algorithm} for g, title, algorithm in GROUPS],
            "tasks": tasks, "runs": runs,
            "summary": {"total": len(runs), "completed": sum(run["terminal"] for run in runs),
                        "started": sum(run["requests"] > 0 for run in runs),
                        "requests": sum(run["requests"] for run in runs),
                        "render_calls": sum(run["render_calls"] for run in runs),
                        "successful_renders": sum(render["ok"] is True for run in runs for render in run["renders"]),
                        "videos_ready": sum(run["video"].get("status") == "ready" and run["video"].get("matches_current_files") for run in runs),
                        "budget_stops": sum(run["status"] == "budget_exhausted" for run in runs)},
            "video_recording": read(pack / "runtime/video_review/status.json", {}),
            "limits": config.get("budget_per_task", {"requests": 80, "render_calls": 80})}


def publish(pack=PACK):
    value = build(pack)
    path = pack / "runtime/dashboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False, prefix=".dashboard-") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        temp = Path(stream.name)
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    return value


if __name__ == "__main__":
    value = publish()
    print(json.dumps(value["summary"]))
