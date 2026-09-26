"""Render candidate snapshots, returning native images, logs and a continuous video."""
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

from shared import ROOT,PILOT,core
from main import ModelTools, encode_video, hashes
from workspace_layout import copy_public,public_dir
from numeric_backend import GODOT,engine_run


def validate(arguments):
    if set(arguments)-{'camera','frames','resolution'}:raise ValueError('Unknown render arguments')
    result=dict(arguments)
    frames=result.setdefault('frames',90)
    if type(frames) is not int or not 1<=frames<=180:raise ValueError('frames must be an integer in [1,180]')
    resolution=result.setdefault('resolution',[960,640])
    if not isinstance(resolution,list) or len(resolution)!=2 or any(type(v) is not int or not 128<=v<=1920 for v in resolution) or math.prod(resolution)>2073600:
        raise ValueError('resolution needs two integers, 128-1920 per edge, at most 2073600 pixels')
    camera=result.get('camera')
    if camera is not None:
        if not isinstance(camera,dict) or set(camera)!={'position','look_at'}:raise ValueError('camera needs position and look_at')
        for value in camera.values():
            if not isinstance(value,list) or len(value)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>100000 for v in value):raise ValueError('camera needs finite world-coordinate vectors')
        if sum((a-b)**2 for a,b in zip(camera['position'],camera['look_at']))<1e-10:raise ValueError('Camera position and target must differ')
    return result


def candidate_audit(project):
    # This is a dependency check, not an OS security boundary.
    blocked=['OS.execute','OS.create_process','HTTPRequest','HTTPClient','TCPServer','TCPStream',
             'res://../','user://','author/','cases_private','expected.json','OS.get_environment']
    for name in hashes(project/'solution',('.godot','__pycache__')):
        path=project/'solution'/name
        if path.suffix.lower() in {'.exe','.dll','.pck','.zip','.so','.pyc'}:raise ValueError('Unsupported candidate dependency: '+name)
        if path.suffix.lower() in {'.gd','.gdshader','.glsl','.txt','.tscn','.tres'}:
            text=path.read_text(encoding='utf-8')
            if any(word in text for word in blocked):raise ValueError('Candidate accesses files/processes outside the task: '+name)


def synchronize(source,target):
    """Reuse large imported assets; refresh changed source files for a new process."""
    current=hashes(source,('.godot','scratch','__pycache__'))
    for name in current:
        destination=target/name
        if not destination.is_file() or core.digest(destination)!=current[name]:
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/name,destination)
    for path in (target/'solution').rglob('*'):
        if path.is_file() and path.relative_to(target).as_posix() not in current:
            if not path.resolve().is_relative_to((target/'solution').resolve()):raise ValueError('Unexpected stage path')
            path.unlink()
    copy_public(source,target)
    return current


def capture_script(native):
    text=(ROOT/'templates'/('l3_native_runner.gd' if native else 'visual_runner.gd')).read_text(encoding='utf-8')
    if native:
        text=text.replace('root.size=Vector2i(640,360)','root.size=Vector2i(int(request.get("width",960)),int(request.get("height",640)))')
    else:
        text=text.replace('fixture.camera.position=','fixture.camera.global_position=')
        text=text.replace('fixture.camera.look_at(Vector3(c.look_at[0],c.look_at[1],c.look_at[2]))',
            'var target=Vector3(c.look_at[0],c.look_at[1],c.look_at[2])\n\t\tvar direction=(target-fixture.camera.global_position).normalized()\n\t\tfixture.camera.look_at(target,Vector3.RIGHT if abs(direction.dot(Vector3.UP))>0.999 else Vector3.UP)')
        text=text.replace('"snapshots":snapshots,','"camera":{"position":fixture.camera.global_position,"basis":fixture.camera.global_basis,"requested":request.get("camera")},"snapshots":snapshots,')
    return text


def render(root,arguments):
    root=Path(root).resolve()
    request=validate(arguments)
    candidate_audit(root)
    # The model sees observations in scratch; worker caches remain outside its root.
    output=root/'scratch/observations'/str(time.time_ns())
    output.mkdir(parents=True)
    stage=root.parent/'render_runtime/project'
    stage.mkdir(parents=True,exist_ok=True)
    errors=[]
    try:
        with core.file_lock(PILOT/'forest_grass_lab/runtime/render.lock',wait=False):
            inputs=synchronize(root,stage)
            native=(stage/'fixture/native_runner.gd').exists()
            (stage/'fixture/model_runner.gd').write_text(capture_script(native),encoding='utf-8')
            core.save(output/'source_files.json',inputs)
            core.save(output/'request.json',request)
            env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','PASSWORD','API_KEY'))}
            env['APPDATA']=str(ROOT/'runs/render_appdata')
            imported=subprocess.run([str(GODOT),'--headless','--editor','--path',str(stage),'--import'],capture_output=True,timeout=600,env=env,creationflags=0x08000000 if os.name=='nt' else 0)
            (output/'import.log').write_bytes(imported.stdout+imported.stderr)
            log=(imported.stdout+imported.stderr).decode('utf-8',errors='replace')
            if imported.returncode or 'SCRIPT ERROR' in log or 'Parse Error' in log:raise ValueError(log[-14000:])
            native_request={**request,'width':request['resolution'][0],'height':request['resolution'][1],'dt':1/15}
            report=engine_run(stage,[],output,timeout=240,script='res://fixture/model_runner.gd',request_data=native_request)
            video=encode_video(output,15,request['frames'])
            chosen=sorted({0,(request['frames']-1)//2,request['frames']-1})
            images=[]
            for frame in chosen:
                path=output/f'frame_{frame:05d}.png'
                images.append({'path':path.relative_to(root).as_posix(),'frame':frame,'mime_type':'image/png','encoding':'base64','data':base64.b64encode(path.read_bytes()).decode('ascii')})
            result={'ok':True,'images':images,'camera':report.get('camera'),'runtime_status':report.get('status'),
                    'startup':report.get('startup',report.get('binding')),'video':video.relative_to(root).as_posix() if video else None,
                    'logs':[(output/n).relative_to(root).as_posix() for n in ['import.log','godot.log','result.json'] if (output/n).exists()],
                    'observation_directory':output.relative_to(root).as_posix()}
    except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired) as error:
        message=str(error)
        if isinstance(error,OSError):message='Renderer could not start or GPU is busy: '+message
        errors.append(message[-16000:])
        result={'ok':False,'errors':errors,'images':[],
                'logs':[p.relative_to(root).as_posix() for p in output.glob('*.log')],
                'observation_directory':output.relative_to(root).as_posix()}
    result['request']=request
    result['candidate_files']=solution_files(root)
    saved={k:v for k,v in result.items() if k!='images'}
    saved['images']=[{k:v for k,v in image.items() if k!='data'} for image in result['images']]
    core.save(output/'tool_result.json',saved)
    core.save(root.parent/'latest_render.json',saved)
    # Continuous video and selected PNGs are sufficient for presentation and feedback.
    if result['ok'] and result.get('video'):
        keep={root/image['path'] for image in result['images']}
        for path in output.glob('frame_*.png'):
            if path not in keep:
                if path.resolve().parent!=output.resolve():raise ValueError('Unexpected frame path')
                path.unlink()
    return result


def solution_files(root):
    return {name:digest for name,digest in hashes(Path(root)/'solution',('.godot','__pycache__')).items() if name!='plan.json' and not name.endswith('.uid')}


def present(root):
    root=Path(root)
    latest=root.parent/'latest_render.json'
    previous=core.read(latest) if latest.exists() else {}
    current=solution_files(root)
    if previous.get('candidate_files')!=current or not previous.get('video'):
        args=previous.get('request',{'frames':90,'resolution':[960,640]})
        # Final human review needs a continuous clip even if the model requested one frame.
        args=dict(args,frames=max(60,args.get('frames',90)))
        try:
            render(root,args)
            previous=core.read(latest)
        except Exception as error:
            previous={'ok':False,'errors':[str(error)],'images':[],'candidate_files':current}
    previous=dict(previous,presentation='final_candidate',returned_to_model=False)
    core.save(root.parent/'presentation.json',previous)
    return previous


class ExperimentTools:
    def __init__(self,root):self.tools=ModelTools(root,renderer=render)

    def call(self,name,arguments):
        try:
            if name=='read':
                path=self.tools._path(arguments['path'])
                if path.suffix.lower() in {'.png','.jpg','.jpeg','.webp'} and path.is_file():
                    mime='image/jpeg' if path.suffix.lower() in {'.jpg','.jpeg'} else 'image/'+path.suffix[1:].lower()
                    return {'ok':True,'kind':'image','path':arguments['path'],'mime_type':mime,'encoding':'base64','data':base64.b64encode(path.read_bytes()).decode('ascii')}
            result=self.tools.call(name,**arguments)
            result.setdefault('ok',result.get('status') not in {'INFRA_ERROR','ENDED'})
            return result
        except (OSError,ValueError,TypeError,UnicodeError,KeyError) as error:
            return {'ok':False,'error':str(error)}
