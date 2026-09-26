"""Versioned native forest intake; preserves original archive and resource paths."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SPEC = ROOT / "author/specification_v0_2"
SOURCE = ROOT / "author/upstream_forest"
BASELINE = ROOT / "author/baselines/native_normalized"
TASKS = ["A_L3", "B_L3", "C_L3_R", "C_L3_S", "D_L3", "E_L3"]
GODOT = Path(os.environ.get("GODOT_BIN", str(REPO / "tools/godot/Godot_v4.6.1-stable_win64_console.exe")))


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def manifest(root):
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(root.rglob("*"))
            if p.is_file() and not any(s in {".godot", ".git", "__pycache__"} for s in p.relative_to(root).parts)}


def inspect_source(archive=None):
    archive = Path(archive or REPO / "realistic/downloads/forest.zip").resolve()
    with zipfile.ZipFile(archive) as z:
        commit = z.comment.decode("ascii")
        if not re.fullmatch("[0-9a-f]{40}", commit):
            raise ValueError("Archive must have a verifiable full commit in its GitHub ZIP comment")
        SOURCE.mkdir(parents=True, exist_ok=True)
        for item in z.infolist():
            rel = Path(*item.filename.split("/")[1:])
            target = (SOURCE / rel).resolve()
            if not target.is_relative_to(SOURCE.resolve()):
                raise ValueError("Archive path escaped source root")
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            elif hashlib.sha256(z.read(item)).hexdigest() != digest(target):
                raise ValueError("Immutable source changed: " + str(rel))
    files = manifest(SOURCE)
    dump(ROOT / "author/source_audit/files.json", files)
    refs = {}
    for rel in files:
        if Path(rel).suffix in {".tscn", ".tres", ".gd", ".gdshader", ".import", ".godot"}:
            text = (SOURCE / rel).read_text(encoding="utf-8", errors="replace")
            refs[rel] = sorted(set(re.findall(r'res://([^"\n]+)', text)))
    missing = sorted({p for refs_ in refs.values() for p in refs_ if p not in files and not p.startswith(".godot/")})
    dump(ROOT / "author/source_audit/dependencies.json", refs)
    report = {"status": "SOURCE_HASHED", "repository": "https://github.com/Rytelier/Godot-4-forest-benchmark",
              "verified_commit": commit, "commit_evidence": "local GitHub archive commit comment",
              "archive": str(archive), "archive_sha256": digest(archive), "file_count": len(files),
              "source_file_manifest_sha256": digest(ROOT / "author/source_audit/files.json"),
              "source_origin": "native_snapshot", "original_entry_scene": "res://Main.tscn",
              "missing_dependencies": missing, "original_run_verified": False,
              "source_directory": str(SOURCE), "lfs_pointer_files": [p for p in files if (SOURCE / p).stat().st_size < 200 and (SOURCE / p).read_bytes().startswith(b"version https://git-lfs")],
              "license_inventory": "author/source_audit/licenses.json", "normalization_patches": []}
    lock_path = ROOT / "author/forest_source_lock.json"
    if lock_path.exists():
        previous = json.loads(lock_path.read_text(encoding="utf-8"))
        if previous.get("archive_sha256") == report["archive_sha256"] and previous.get("source_file_manifest_sha256") == report["source_file_manifest_sha256"]:
            report = {**report, **previous}
    dump(lock_path, report)
    dump(ROOT / "author/source_audit/licenses.json", {"repository_license": "MIT", "license_file": "LICENSE",
          "credits_file": "Asset Credits.txt", "asset_sources": ["https://polyhaven.com/license", "https://docs.ambientcg.com/license/"],
          "asset_source_terms": "CC0 for assets provided by these two listed providers", "checked_date": "2026-09-26",
          "scope": "Preserve upstream license, credits and shader attribution. Per-file attribution closure remains a release check.",
          "public_redistribution_verified": False})
    return report


def normalize_source():
    if not SOURCE.exists():
        inspect_source()
    if not BASELINE.exists():
        shutil.copytree(SOURCE, BASELINE, ignore=shutil.ignore_patterns(".git", ".godot"))
    patches = []
    for rel in ["Main.tscn", "project.godot"]:
        original = (SOURCE / rel).read_text(encoding="utf-8")
        text = original
        if rel == "Main.tscn":
            # Missing editor-only groundcover generator: preserve every baked instance.
            text = re.sub(r'^\[ext_resource[^\n]*id="(?:34_a6vsm|6_lwrrj)"\]\n', "", text, flags=re.M)
            for line in ['script = ExtResource("34_a6vsm")', 'groundcoverMeshes = [ExtResource("6_lwrrj")]',
                         'groundcoverData = "res://Groundcover/Groundcover.txt"', 'updateCover = false', 'clear = false']:
                text = text.replace(line + "\n", "")
            text = text.replace("load_steps=3755", "load_steps=3753", 1)
            assert text.count("[node ") == original.count("[node ")
            assert text.count('type="MultiMeshInstance3D"') == original.count('type="MultiMeshInstance3D"')
            purpose = "Detach absent editor generator; keep baked meshes, instances, transforms and materials."
        else:
            text = text.replace('PackedStringArray("4.0", "Forward Plus")', 'PackedStringArray("4.6", "Forward Plus")')
            text += '\n[animation]\ncompatibility/default_parent_skeleton_in_mesh_instance_3d=true\n'
            purpose = "Pin Godot 4.6 import compatibility; preserve renderer, TAA, occlusion and quality settings."
        (BASELINE / rel).write_text(text, encoding="utf-8")
        patches.append({"path": rel, "before": digest(SOURCE / rel), "after": digest(BASELINE / rel), "purpose": purpose})
    probe = BASELINE / "benchmark_author_probe.gd"
    shutil.copy2(ROOT / "templates/l3_source_probe.gd", probe)
    lock = json.loads((ROOT / "author/forest_source_lock.json").read_text(encoding="utf-8"))
    lock["normalization_patches"] = patches
    lock["engine_binary_sha256"] = digest(GODOT)
    dump(ROOT / "author/forest_source_lock.json", lock)
    return BASELINE


def run_probe(import_project=True):
    project = normalize_source()
    out = ROOT / "author/source_audit/native_runtime"
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["APPDATA"] = str(ROOT / "runs/l3_appdata")
    Path(env["APPDATA"]).mkdir(parents=True, exist_ok=True)
    if import_project:
        command = [str(GODOT), "--headless", "--editor", "--path", str(project), "--import"]
        start = time.monotonic()
        imported = subprocess.run(command, capture_output=True, timeout=600, env=env, creationflags=0x08000000)
        (out / "import.log").write_bytes(imported.stdout + imported.stderr)
        dump(out / "import.json", {"returncode": imported.returncode, "seconds": time.monotonic() - start})
        if imported.returncode:
            raise RuntimeError("Native import failed; see " + str(out / "import.log"))
    command = [str(GODOT), "--path", str(project), "--rendering-method", "forward_plus", "--audio-driver", "Dummy",
               "--position", "-10000,-10000", "--resolution", "640x360", "--script", "res://benchmark_author_probe.gd", "--", str(out)]
    start = time.monotonic()
    run = subprocess.run(command, capture_output=True, timeout=300, env=env, creationflags=0x08000000)
    (out / "godot.log").write_bytes(run.stdout + run.stderr)
    dump(out / "execution.json", {"returncode": run.returncode, "seconds": time.monotonic() - start})
    if run.returncode or not (out / "result.json").exists():
        raise RuntimeError("Native runtime failed; see " + str(out / "godot.log"))
    return json.loads((out / "result.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        r = run_probe(); print(r["status"], r["node_count"], len(r["meshes"]), flush=True)
    else:
        r = inspect_source(); print(r["verified_commit"], r["file_count"], r["missing_dependencies"], flush=True)
