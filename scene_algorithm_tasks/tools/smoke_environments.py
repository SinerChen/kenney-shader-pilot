"""Render existing-host starters serially; never call a model or score an effect."""
import argparse
import hashlib
import json
from pathlib import Path

from environments import PACK, WORKSPACE, PROFILES
from model_io import FileTools

parser = argparse.ArgumentParser()
parser.add_argument("--groups", nargs="+", default=list(PROFILES))
parser.add_argument("--levels", nargs="+", type=int, default=[1, 2, 3])
args = parser.parse_args()
out = PACK / "verification/environments"
out.mkdir(parents=True, exist_ok=True)
records = []
for group in args.groups:
    original = WORKSPACE / PROFILES[group]["project"]
    original_files = [original / "project.godot", original / PROFILES[group]["entry"]]
    original_files += [p for p in original.rglob("*.gd") if ".godot" not in p.parts]
    source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files}
    for level in args.levels:
        task_id = f"{group}_L{level}"
        root = PACK / "tasks" / task_id / "model_workspace"
        tools = FileTools(root)
        mounted = tools.call("read", {"path": "scene/project/project.godot", "max_lines": 12})
        assert mounted["ok"], mounted
        assert not tools.call("write", {"path": "scene/project/project.godot", "content": "bad"})["ok"]
        assert not tools.call("read", {"path": "scene/project/.godot"})["ok"]
        result = tools.call("render", {"frames": [1, 2], "resolution": [640, 480]})
        record = {k: v for k, v in result.items() if k != "images"}
        record["images"] = [{k: v for k, v in image.items() if k != "data"} for image in result.get("images", [])]
        record["task_id"] = task_id
        record["scope"] = "environment_startup_only_not_algorithm_correctness"
        (out / f"{task_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        records.append(record)
        print(json.dumps({"task": task_id, "ok": result["ok"],
            "errors": result.get("errors", result.get("error")),
            "environment": result.get("capture", {}).get("environment"),
            "output": result.get("observation_directory")}, ensure_ascii=False), flush=True)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == value for p, value in source_hashes.items()), "Original host changed"

all_records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("SA*_L*.json"))]
summary = {"checked": len(all_records), "passed": sum(bool(r["ok"]) for r in all_records),
           "model_api_calls": 0, "source_host_files_unchanged": True,
           "shutdown_diagnostics": {r["task_id"]: r.get("phases", {}).get("capture", {}).get("shutdown_diagnostics", []) for r in all_records if r.get("phases", {}).get("capture", {}).get("shutdown_diagnostics")},
           "scope": "environment_startup_only_not_algorithm_correctness",
           "results": [{"task_id": r["task_id"], "ok": r["ok"], "record": r["task_id"] + ".json"} for r in all_records]}
(out / "validation.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
raise SystemExit(0 if all(record["ok"] for record in records) else 1)
