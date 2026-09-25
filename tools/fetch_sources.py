"""Download official archives into this pilot only; retain existing snapshots."""
import json
import shutil
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBS = [
    ('platformer', 'https://codeload.github.com/KenneyNL/Starter-Kit-3D-Platformer/zip/refs/heads/main', 'upstream/platformer'),
    ('fps', 'https://codeload.github.com/KenneyNL/Starter-Kit-FPS/zip/refs/heads/main', 'upstream/fps'),
    ('godot-4.6.1', 'https://github.com/godotengine/godot-builds/releases/download/4.6.1-stable/Godot_v4.6.1-stable_win64.exe.zip', 'tools/godot'),
]


def fetch(job):
    name, url, destination = job
    archive = ROOT / 'downloads' / (name + '.zip')
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'KenneyShaderPilot/1.0'})
        with urllib.request.urlopen(request, timeout=90) as response, archive.with_suffix('.part').open('wb') as output:
            shutil.copyfileobj(response, output)
        archive.with_suffix('.part').replace(archive)
    target = ROOT / destination
    if not target.exists():
        target.mkdir(parents=True)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                parts = Path(member.filename).parts
                relative = Path(*parts[1:]) if name in ('platformer', 'fps') else Path(*parts)
                out = (target / relative).resolve()
                if not out.is_relative_to(target.resolve()):
                    raise ValueError('Archive path escapes destination')
                if member.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                else:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(member) as source, out.open('wb') as output:
                        shutil.copyfileobj(source, output)
    result = {'name': name, 'url': url, 'archive': str(archive.relative_to(ROOT)), 'bytes': archive.stat().st_size, 'directory': destination}
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        sources = list(pool.map(fetch, JOBS))
    path = ROOT / 'sources.json'
    if not path.exists():
        path.write_text(json.dumps({'downloaded_at': datetime.now().astimezone().isoformat(), 'note': 'Kenney main-branch archives are retained locally; rebuild uses these saved snapshots, not a new download.', 'sources': sources}, indent=2) + '\n', encoding='utf-8')
