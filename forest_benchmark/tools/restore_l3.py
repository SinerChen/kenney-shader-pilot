"""Restore the other L3 starters from the single published A_L3 project."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("B_L3", "C_L3_R", "D_L3", "E_L3")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes project: " + name)
    return path


def restore(task, output_parent):
    overlay = ROOT / "starters/l3_overlays" / task
    spec = json.loads((overlay / "manifest.json").read_text(encoding="utf-8"))
    destination = output_parent.resolve() / task
    base = ROOT / "starters/A_L3"
    sources = {}
    for name, expected in spec["files"].items():
        source = safe_path(overlay / "files" if name in spec["changed"] else base, name)
        if not source.is_file() or sha256(source) != expected:
            raise ValueError("Source hash mismatch: " + name)
        sources[name] = source
    if destination.exists():
        raise FileExistsError("Refusing to overwrite existing project: " + str(destination))
    # All source files are verified before creating the destination.
    for name, source in sources.items():
        target = safe_path(destination, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    public_source = ROOT / "starters/public" / task
    public_target = output_parent.resolve() / "public" / task
    if public_source.resolve() != public_target.resolve():
        shutil.copytree(public_source, public_target, dirs_exist_ok=True)
    print(f"{task}: restored {len(sources)} files to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=(*TASKS, "all"))
    parser.add_argument("--output-parent", type=Path, default=ROOT / "starters")
    args = parser.parse_args()
    for task in TASKS if args.task == "all" else (args.task,):
        restore(task, args.output_parent)
