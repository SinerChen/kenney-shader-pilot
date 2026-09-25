"""Run the dew variant on the real GPU, retaining the verification log."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT.parent

def run(mode, scout=False):
    out = ROOT / 'verification/forest/dew'
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['APPDATA'] = str(PILOT / 'runtime/AppData')
    args = [str(PILOT / 'tools/godot/Godot_v4.6.1-stable_win64.exe'),
            '--path', str(ROOT / 'projects/forest'), '--audio-driver', 'Dummy',
            '--windowed', '--resolution', '1280x720', '--fixed-fps', '60',
            '--script', 'res://dew/' + ('inspect.gd' if mode == 'inspect' else 'verify.gd'),
            '--', '--output=' + out.as_posix()]
    if scout:
        args.append('--scout')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    started = time.monotonic()
    log_path = out / (mode + '.log')
    with log_path.open('w', encoding='utf-8') as log:
        try:
            code = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT,
                                  startupinfo=startup, timeout=480).returncode
        except subprocess.TimeoutExpired:
            code = -1
    lines = log_path.read_text(encoding='utf-8', errors='replace').splitlines()
    report = {'mode': mode, 'exit_code': code, 'elapsed_seconds': round(time.monotonic()-started, 2),
              'errors': list(dict.fromkeys(x for x in lines if 'ERROR:' in x)),
              'warnings': list(dict.fromkeys(x for x in lines if 'WARNING:' in x)),
              'completed': any('DEW_' + ('INSPECTION' if mode == 'inspect' else 'VERIFY') + '_COMPLETE' in x for x in lines)}
    (out / (mode + '-status.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if code == 0 and report['completed'] and not report['errors'] else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['inspect', 'capture'])
    parser.add_argument('--scout', action='store_true')
    options = parser.parse_args()
    raise SystemExit(run(options.mode, options.scout))
