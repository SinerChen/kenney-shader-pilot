"""Restore omitted large upstream assets without overwriting project adaptations."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            checksum.update(block)
    return checksum.hexdigest()


def restore(check_only=False):
    manifest = json.loads((ROOT / "external_assets.json").read_text(encoding="utf-8"))
    missing = 0
    restored = 0
    for source in manifest["sources"]:
        pending = []
        for asset in source["assets"]:
            target = (ROOT / asset["path"]).resolve()
            if not target.is_relative_to(ROOT):
                raise ValueError("Asset path escapes repository")
            if target.is_file():
                if digest(target) != asset["sha256"]:
                    raise ValueError("Existing asset differs; left unchanged: " + asset["path"])
            else:
                pending.append((asset, target))
        missing += len(pending)
        if not pending or check_only:
            continue
        archive = ROOT / source["archive"]
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.is_file():
            partial = archive.with_suffix(".part")
            request = urllib.request.Request(source["url"], headers={"User-Agent": "KenneyShaderPilot/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
                shutil.copyfileobj(response, output)
            if digest(partial) != source["archive_sha256"]:
                raise ValueError("Upstream archive changed; original archive required: " + str(archive))
            partial.replace(archive)
        if digest(archive) != source["archive_sha256"]:
            raise ValueError("Archive checksum mismatch: " + str(archive))
        with zipfile.ZipFile(archive) as bundle:
            for asset, target in pending:
                data = bundle.read(asset["member"])
                if hashlib.sha256(data).hexdigest() != asset["sha256"]:
                    raise ValueError("Asset checksum mismatch: " + asset["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                restored += 1
    print(json.dumps({"check_only": check_only, "missing_at_start": missing, "restored": restored}))
    return 1 if check_only and missing else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    raise SystemExit(restore(parser.parse_args().check_only))
