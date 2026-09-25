"""Fixed Godot target capture. Only data parameters and candidate shader are accepted."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from PIL import Image
from local_lock import file_lock
from state import save_json

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT.parent
RUNTIME = ROOT/'runtime'
ENGINE = PILOT/'tools/godot/Godot_v4.6.1-stable_win64.exe'

def check_params(values):
    if not isinstance(values,dict):
        raise ValueError('params/set must be an object')
    for key,value in values.items():
        if key == 'camera':
            if value not in ('overview','roots','top'):
                raise ValueError('camera must be overview/roots/top')
        elif key in ('wind_strength','wind_speed'):
            maximum = .45 if key == 'wind_strength' else 3
            if type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= maximum:
                raise ValueError(f'{key} must be in [0,{maximum}]')
        elif key in ('wind_direction','player_position'):
            size = 2 if key == 'wind_direction' else 3
            if not isinstance(value,list) or len(value)!=size or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>10 for x in value):
                raise ValueError(f'{key} must have {size} finite components in [-10,10]')
        else:
            raise ValueError(f'Unknown host parameter: {key}')

def step_case(args):
    if args.get('scene','target') != 'target':
        raise ValueError('P3 only allows scene=target')
    params=args.get('params',{}); check_params(params)
    frames=args.get('frames',[1,120,240])
    if not isinstance(frames,list) or not 1<=len(frames)<=3 or any(type(n)!=int or not 1<=n<=720 for n in frames) or frames!=sorted(set(frames)):
        raise ValueError('frames: 1–3 increasing integers in [1,720], dt=1/60')
    schedule=args.get('schedule',[])
    if not isinstance(schedule,list) or len(schedule)>720:
        raise ValueError('schedule must contain at most 720 events')
    seen=set()
    for item in schedule:
        if not isinstance(item,dict) or set(item)!={'frame','set'} or type(item['frame'])!=int or not 1<=item['frame']<=max(frames) or item['frame'] in seen:
            raise ValueError('schedule requires unique frame numbers and set objects')
        seen.add(item['frame']); check_params(item['set'])
    return [dict(name='target',params=dict(camera='overview')|params,frames=frames,schedule=schedule)]

def public_cases(level,animation=False):
    task=json.loads((ROOT/f'tasks/FG01_L{level}/task.json').read_text(encoding='utf-8'))
    result=[]
    for item in task['public_cases']:
        end=round(item['seconds']*60)
        frames=[1,end//2,end] if end<=240 else [225,420,end]
        result.append(dict(name=item['id'],params=dict(camera=item['camera'])|item.get('parameters',{}),
                           frames=frames,events=item.get('events',[]),
                           animation=animation and item['id']==('player_pass_recover' if level==3 else 'wind_default')))
    return result

def execute(args,log,timeout=240):
    env=os.environ.copy(); env['APPDATA']=str(PILOT/'runtime/AppData')
    startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
    with log.open('w',encoding='utf-8') as f:
        try:
            code=subprocess.run([str(ENGINE),*args],stdout=f,stderr=subprocess.STDOUT,env=env,startupinfo=startup,timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code=-1
    lines=log.read_text(encoding='utf-8',errors='replace').splitlines()
    errors=list(dict.fromkeys(x for x in lines if 'ERROR:' in x or 'Error at line' in x))
    if code:
        errors.append(f'Godot exit code {code}')
    return errors,lines

def evaluate(level,shader,out,args=None,animation=False):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    cases=step_case(args) if args else public_cases(level,animation)
    save_json(out/'capture-request.json',dict(level=level,cases=cases))
    with file_lock(RUNTIME/'render.lock'):
        project=RUNTIME/'project'
        if not project.exists():
            shutil.copytree(ROOT/'project',project,ignore=shutil.ignore_patterns('.godot','*.import','*.uid'))
        (project/'effect/grass.gdshader').write_text(Path(shader).read_text(encoding='utf-8'),encoding='utf-8')
        if not (project/'.godot/imported').exists():
            errors,_=execute(['--path',str(project),'--headless','--editor','--import'],out/'import.log')
            if errors:
                report=dict(execution_ok=False,errors=errors,cases=[],warnings=[])
                save_json(out/'result.json',report); return report
        errors,lines=execute(['--path',str(project),'--audio-driver','Dummy','--windowed','--resolution','768x512',
            '--fixed-fps','60','--script',str(ROOT/'experiment/capture.gd'),'--','--manual-step',
            '--capture='+(out/'capture-request.json').as_posix()],out/'godot.log')
    capture=json.loads((out/'capture.json').read_text()) if (out/'capture.json').exists() else {}
    if not capture.get('completed'):
        errors.append('Godot capture did not complete')
    for case in cases:
        for frame in case['frames']:
            if not (out/case['name']/f'{frame:03d}.png').exists():
                errors.append(f'Missing image {case["name"]}/{frame:03d}.png')
    if capture and not errors and animation:
        for case in cases:
            paths=sorted((out/case['name']/'animation').glob('*.png'))
            if paths:
                frames=[Image.open(p).convert('RGB') for p in paths]
                frames[0].save(out/case['name']/'animation.webp',save_all=True,append_images=frames[1:],duration=133,loop=0,quality=78)
                for f in frames: f.close()
    report=dict(execution_ok=not errors,errors=errors,warnings=list(dict.fromkeys(x for x in lines if 'WARNING:' in x)),
                cases=capture.get('cases',[]),renderer=capture.get('renderer'),visual_quality='not_independently_evaluated')
    save_json(out/'result.json',report)
    return report

def feedback_images(level,folder,kind):
    folder=Path(folder)
    if kind=='step':
        return sorted((folder/'target').glob('*.png'))[:3]
    selection=[('wind_default','240.png'),('wind_off','120.png'),('strong_crosswind','240.png')]
    if level==3:
        selection=[('player_without_wind',f'{n:03d}.png') for n in (225,420,660)]
    return [folder/c/f for c,f in selection if (folder/c/f).is_file()]
