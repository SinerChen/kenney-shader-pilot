"""Run the prepared Godot baselines. Does not call any model API."""
import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT/'tools/godot/Godot_v4.6.1-stable_win64.exe'


def run(scene,mode,level=1):
    kit='platformer' if scene.startswith('P') else 'fps'
    env=os.environ.copy()
    env['APPDATA']=str(ROOT/'runtime/AppData')
    Path(env['APPDATA']).mkdir(parents=True,exist_ok=True)
    (ENGINE.parent/'_sc_').touch(exist_ok=True)
    project=ROOT/'projects'/kit
    output=ROOT/'verification'/scene
    output.mkdir(parents=True,exist_ok=True)
    args=[str(ENGINE),'--path',str(project),'--audio-driver','Dummy']
    if mode=='import': args+=['--headless','--editor','--import']
    elif mode=='editor': args+=['--editor','res://pilot/'+scene+'.tscn']
    else:
        args+=['res://pilot/'+scene+'.tscn']
        if mode=='verify': args+=['--headless']
        if mode in ('verify','capture'):
            if mode=='verify': output=ROOT/'verification/logic'/scene
            output.mkdir(parents=True,exist_ok=True)
            args+=['--fixed-fps','60','--','--'+mode,'--output='+output.as_posix(),'--level='+str(level)]
        else:
            args+=['--','--level='+str(level)]
    if mode in ('inspect','editor'):
        subprocess.Popen(args,env=env,cwd=ROOT)
        print('Opened',scene,mode)
        return
    log_path=ROOT/'verification'/f'{mode}-{scene}.log'
    startup=subprocess.STARTUPINFO() if os.name=='nt' else None
    if startup:
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow=0
    with log_path.open('w',encoding='utf-8') as log:
        result=subprocess.run(args,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180,startupinfo=startup)
    text=log_path.read_text(encoding='utf-8',errors='replace')
    errors=[line for line in text.splitlines() if 'ERROR:' in line or 'WARNING:' in line]
    if result.returncode or errors:
        raise RuntimeError(f'{scene} {mode}: exit={result.returncode}; {errors[:6]}; see {log_path}')
    if mode in ('verify','capture'):
        data=json.loads((output/'result.json').read_text(encoding='utf-8'))
        manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        expected=next(s for s in manifest['scenes'] if s['id']==scene)
        assert sorted(data['targets'])==sorted(expected['targets']),scene
        assert data['reset_ok'] and data['frames']==180,scene
        assert [e['before_step'] for e in data['events']]==[e['frame'] for e in expected['events']],scene
        assert data['rendered']==(mode=='capture'),scene
        print(scene,mode,'passed',f"{data['frames']} steps / {len(data['events'])} events",flush=True)
    else: print(scene,'import passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scene',choices=['P01','P02','P03','F01','F02','all'],default='P01')
    parser.add_argument('--mode',choices=['inspect','editor','import','verify','capture'],default='inspect')
    parser.add_argument('--level',type=int,choices=[1,2,3],default=1)
    a=parser.parse_args()
    scenes=['P01','P02','P03','F01','F02'] if a.scene=='all' else [a.scene]
    if a.mode=='import' and a.scene=='all': scenes=['P01','F01']
    if a.mode in ('inspect','editor') and a.scene=='all': parser.error('Open one interactive scene at a time')
    for scene in scenes: run(scene,a.mode,a.level)
