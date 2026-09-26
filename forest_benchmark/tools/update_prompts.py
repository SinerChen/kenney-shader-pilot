"""Refresh external prompts and schemas without rebuilding model workspaces."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prompts import SPECS, make_prompt
from prompt_layout import install_types
from workspace_layout import public_dir, refresh_inventory


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update():
    report_path = ROOT / "author/reports/prompt_revision.json"
    report = read(report_path) if report_path.exists() else {"files": {}}

    def write(path, text):
        previous = digest(path) if path.exists() else None
        current = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if previous == current:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        key = path.relative_to(ROOT).as_posix()
        first = report["files"].get(key, {}).get("before", previous)
        report["files"][key] = {"before": first, "after": current}

    def project_prompt(project, task):
        install_types(project, task, write)
        write(public_dir(project) / "prompt.md", make_prompt(task, project))
        refresh_inventory(project)

    starters = 0
    for task in SPECS:
        project = ROOT / "starters" / task
        if (public_dir(project) / "task.json").exists():
            project_prompt(project, task)
            starters += 1
        else:
            project = ROOT / "tasks" / task
            install_types(project, task, write)
        write(ROOT / "tasks" / task / "prompt.md", make_prompt(task, project))

    exports = 0
    for folder, dirs, files in os.walk(ROOT / "exports"):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"public", "scratch"}]
        if "project.godot" not in files:
            continue
        dirs.clear()
        project = Path(folder)
        meta = public_dir(project) / "task.json"
        if meta.exists() and (task := read(meta)["task_id"]) in SPECS:
            project_prompt(project, task)
            exports += 1

    # Preserve migration provenance after regenerating the external documents.
    relocation = ROOT / "author/reports/public_relocation.json"
    if relocation.exists():
        moved = read(relocation)
        for row in moved["moves"].values():
            row["after"] = digest(ROOT / row["path"])
        dump(relocation, moved)
    report.update(updated=datetime.now(timezone.utc).isoformat(), task_prompts=len(SPECS),
                  starter_prompts=starters, review_export_prompts=exports,
                  format="effect_algorithm,io_types,workspace_table,tools,render_observation", metadata="external_public")
    dump(report_path, report)
    print({k: v for k, v in report.items() if k != "files"})


if __name__ == "__main__":
    update()
