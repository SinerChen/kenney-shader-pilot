"""Host metadata lives beside, never inside, a model workspace."""
import hashlib
import json
from pathlib import Path
import shutil


def public_dir(project):
    project = Path(project).resolve()
    return project.parent / "public" / project.name


def copy_public(source, destination):
    source = public_dir(source)
    if source.is_dir():
        shutil.copytree(source, public_dir(destination), dirs_exist_ok=True)


def refresh_inventory(project):
    project = Path(project)
    path = public_dir(project) / "scene_inventory.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data.get("files"), list):
        data["files"] = [item for item in data["files"]
                         if not item["path"].startswith("public/")]
        for item in data["files"]:
            item["sha256"] = hashlib.sha256((project / item["path"]).read_bytes()).hexdigest()
    if "source_file_manifest" in data:
        data["source_file_manifest"] = "scene_files.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
