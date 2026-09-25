"""Fetch the requested scene archives; keep the originals for reproducibility."""
import concurrent.futures
import json
import shutil
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('bistro', 'Bistro', 'Jamsers/Bistro-Demo-Tweaked', 'main'),
    ('sponza', 'Sponza', 'Calinou/godot-sponza', 'master'),
    ('forest', 'Open Forest Benchmark', 'Rytelier/Godot-4-forest-benchmark', 'main'),
    ('tps', 'Official TPS Demo', 'godotengine/tps-demo', 'master'),
    ('water', 'Boujie Water Shader', 'Chrisknyfe/boujie_water_shader', 'main'),
]


def fetch(source):
    sid, title, repo, branch = source
    url = f'https://codeload.github.com/{repo}/zip/refs/heads/{branch}'
    archive = ROOT / 'downloads' / f'{sid}.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        partial = archive.with_suffix('.part')
        for attempt in range(1, 4):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'GodotSceneLibrary/1.0'})
                print(f'{sid}: downloading attempt {attempt}', flush=True)
                with urllib.request.urlopen(request, timeout=120) as response, partial.open('wb') as output:
                    total = 0
                    last = time.monotonic()
                    while block := response.read(1024 * 1024):
                        output.write(block)
                        total += len(block)
                        if time.monotonic() - last > 20:
                            print(f'{sid}: {total / 1048576:.1f} MiB downloaded', flush=True)
                            last = time.monotonic()
                with zipfile.ZipFile(partial) as bundle:
                    # Opening the directory checks that the HTTP response is a ZIP.
                    if not bundle.namelist():
                        raise ValueError('Empty archive')
                partial.replace(archive)
                break
            except Exception as exc:
                print(f'{sid}: {type(exc).__name__}: {exc}', flush=True)
                if attempt == 3:
                    raise
    target = ROOT / 'projects' / sid
    marker = ROOT / 'downloads' / f'{sid}.json'
    if not marker.exists():
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                parts = Path(member.filename).parts
                relative = Path(*parts[1:])
                out = (target / relative).resolve()
                if not out.is_relative_to(target.resolve()):
                    raise ValueError('Archive path escapes destination')
                if member.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                else:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(member) as src, out.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
        supplements = []
        if sid == 'water' and not (target / 'project.godot').is_file():
            # Upstream export-ignore packages addons/example, excluding the project.
            config_url = f'https://raw.githubusercontent.com/{repo}/{branch}/project.godot'
            saved_config = ROOT / 'downloads' / 'water-project.godot'
            if not saved_config.exists():
                with urllib.request.urlopen(config_url, timeout=60) as response:
                    saved_config.write_bytes(response.read())
            shutil.copyfile(saved_config, target / 'project.godot')
            supplements.append({'url': config_url, 'file': 'downloads/water-project.godot', 'reason': 'Excluded from upstream ZIP by export-ignore.'})
        if not (target / 'project.godot').is_file():
            raise ValueError(f'{sid}: missing project.godot')
        record = {
            'id': sid, 'name': title, 'repository': 'https://github.com/' + repo,
            'branch': branch, 'archive_url': url, 'archive_bytes': archive.stat().st_size,
            'downloaded_at': datetime.now().astimezone().isoformat(),
            'directory': f'projects/{sid}', 'archive': f'downloads/{sid}.zip',
        }
        if supplements:
            record['supplemental_sources'] = supplements
        marker.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    record = json.loads(marker.read_text(encoding='utf-8'))
    print(f'{sid}: extracted ({archive.stat().st_size / 1048576:.1f} MiB archive)', flush=True)
    return record


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(fetch, SOURCES))
    (ROOT / 'sources.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
