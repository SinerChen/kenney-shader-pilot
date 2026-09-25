"""Import or render a requested scene with the existing Godot 4.6.1 editor."""
import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT.parent
ENGINE = PILOT / 'tools/godot/Godot_v4.6.1-stable_win64.exe'


def run(sid, mode, scene, label=''):
    project = ROOT / 'projects' / sid
    out = ROOT / 'verification' / sid
    if label:
        out = out / label
    out.mkdir(parents=True, exist_ok=True)
    # Local editor configuration; source project.godot remains in the archive.
    import certifi
    shutil.copyfile(certifi.where(), project / 'library-ca.pem')
    override = project / 'override.cfg'
    if not override.exists():
        override.write_text('[editor]\nimport/use_multiple_threads=false\n\n[network]\ntls/certificate_bundle_override="res://library-ca.pem"\n', encoding='utf-8')
    env = os.environ.copy()
    env['APPDATA'] = str(PILOT / 'runtime/AppData')
    args = [str(ENGINE), '--path', str(project), '--audio-driver', 'Dummy']
    if mode == 'import':
        args += ['--headless', '--editor', '--import']
    else:
        args += ['--script', str(ROOT / 'tools/probe.gd'), '--windowed', '--resolution', '1280x720', '--fixed-fps', '60', '--', '--output=' + out.as_posix()]
        if scene:
            args += ['--scene=' + scene]
        if label == 'play':
            args += ['--play']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log_path = out / f'{mode}.log'
    if log_path.exists():
        history = out / 'history'
        history.mkdir(exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copyfile(log_path, history / f'{mode}-{stamp}.log')
        status = out / f'{mode}-status.json'
        if status.exists():
            shutil.copyfile(status, history / f'{mode}-{stamp}.json')
    started = time.monotonic()
    print(sid, mode, 'started', flush=True)
    with log_path.open('w', encoding='utf-8') as log:
        try:
            result = subprocess.run(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup, timeout=1200)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = -1
    lines = log_path.read_text(encoding='utf-8', errors='replace').splitlines()
    errors = list(dict.fromkeys(line for line in lines if 'ERROR:' in line or 'SCRIPT ERROR:' in line))
    warnings = list(dict.fromkeys(line for line in lines if 'WARNING:' in line))
    report = {'scene_id': sid, 'mode': mode, 'checked_at': datetime.now().astimezone().isoformat(),
              'exit_code': code, 'elapsed_seconds': round(time.monotonic()-started, 2),
              'errors': errors, 'warnings': warnings, 'log': log_path.relative_to(ROOT).as_posix()}
    if mode == 'capture':
        report['capture_completed'] = any('SCENE_CAPTURE_COMPLETE' in line for line in lines)
    (out / f'{mode}-status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('scene_id', choices=['bistro','sponza','forest','tps','water'])
    parser.add_argument('mode', choices=['import','capture'])
    parser.add_argument('--scene', default='')
    parser.add_argument('--label', choices=['menu', 'play'], default='')
    args = parser.parse_args()
    run(args.scene_id, args.mode, args.scene, args.label)
