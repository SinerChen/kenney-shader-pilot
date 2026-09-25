"""Local Godot checks and animation export. This tool has no model API path."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT.parent

def run(mode):
    output = ROOT/'verification'
    output.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['APPDATA'] = str(PILOT/'runtime/AppData')
    args = [str(PILOT/'tools/godot/Godot_v4.6.1-stable_win64.exe'),
            '--path',str(ROOT/'project'),'--audio-driver','Dummy']
    if mode == 'import':
        args += ['--headless','--editor','--import']
    else:
        args += ['--windowed','--resolution','960x640','--fixed-fps','60',
                 '--script',str(ROOT/'tools/verify.gd'),'--',
                 '--output='+output.as_posix(), '--reference-dir='+(ROOT/'reference').as_posix(), '--manual-step']
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    log = output/(mode+'.log')
    start = time.monotonic()
    with log.open('w',encoding='utf-8') as handle:
        try:
            code = subprocess.run(args,env=env,stdout=handle,stderr=subprocess.STDOUT,startupinfo=startup,timeout=360).returncode
        except subprocess.TimeoutExpired:
            code = -1
    lines = log.read_text(encoding='utf-8',errors='replace').splitlines()
    errors = list(dict.fromkeys(line for line in lines if 'ERROR:' in line))
    report = {'mode':mode,'exit_code':code,'elapsed_seconds':round(time.monotonic()-start,2),
              'errors':errors,'warnings':list(dict.fromkeys(line for line in lines if 'WARNING:' in line)),
              'model_api_calls':0,'completed':code == 0 and (mode == 'import' or any('GRASS_VERIFY_COMPLETE' in line for line in lines))}
    if mode == 'capture' and report['completed'] and not errors:
        for level in (1,2,3):
            paths = sorted((output/f'L{level}/frames').glob('*.png'))
            frames = [Image.open(path).convert('RGB') for path in paths]
            assert frames
            frames[0].save(output/f'L{level}/animation.webp',save_all=True,append_images=frames[1:],duration=125,loop=0,quality=78,method=4)
            for image in frames:
                image.close()
        report['animated_previews'] = ['L1/animation.webp','L2/animation.webp','L3/animation.webp']
    (output/(mode+'-status.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    return 0 if report['completed'] and not errors else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['import','capture'])
    raise SystemExit(run(parser.parse_args().mode))
