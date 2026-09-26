"""Serial exploratory S1/P3 model experiment, independent of the older scene run."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from shared import ROOT,PILOT,core
from main import TASKS,hashes,tool_definitions
from prompts import make_prompt
from workspace_layout import public_dir,copy_public,refresh_inventory
from render_worker import ExperimentTools,present

HERE=Path(__file__).resolve().parent
RUNTIME=ROOT/'runtime/experiment'
RUNS=ROOT/'runs/s1_p3'
ORDER=[task for chain in 'ABCDE' for task in ([chain+'_L1',chain+'_L2','C_L3_R','C_L3_S'] if chain=='C' else [chain+'_L1',chain+'_L2',chain+'_L3'])]
BLOCKED={'C_L3_S':'Original sky world-space mapping is unresolved; no runnable starter exists.'}


def prepare():
    RUNTIME.mkdir(parents=True,exist_ok=True)
    if (RUNTIME/'approval.json').exists():
        verify()
        return core.read(RUNTIME/'run_config.json')
    prior=core.read(PILOT/'scene_algorithm_tasks/runtime/experiment/run_config.json')
    config={k:copy.deepcopy(prior[k]) for k in ['models','model_order','budget_per_task','retry','scheduling']}
    config.update(experiment='forest_benchmark_s1_p3_v1',mode='S1',variant='P3',task_order=ORDER,
        solution_dir='solution',stop_file=str(RUNTIME/'STOP'),status='authorized_exploratory_run',
        blocked_tasks=BLOCKED,formal_algorithm_scores=False,
        render_isolation='Credential-filtered processes and separate workspace snapshots; not an OS sandbox.',
        inheritance={'directory':'solution','exclude':['plan.json','.godot','__pycache__'],'fresh_conversation':True,'author_reference_injected':False})
    config['retry'].update(wait_seconds=300,http_status_errors='retry_all',transport_errors='retry')
    system=(HERE/'P3.md').read_text(encoding='utf-8')
    definitions=[x['function'] for x in tool_definitions()]
    definitions[0]['description']='Read a visible UTF-8 file, image, or directory.'
    queue=[]
    for alias in config['model_order']:
        for task in ORDER:
            level=task.split('_')[1]
            parent=None if level=='L1' else alias+'/'+task[0]+('_L1' if level=='L2' else '_L2')
            queue.append({'model_alias':alias,'task_id':task,'parent':parent,'blocked':BLOCKED.get(task)})
    frozen_hashes={}
    for task in ORDER:
        if task in BLOCKED:continue
        source=ROOT/'starters'/task
        baseline=core.read(ROOT/'author/baseline'/(task+'.json'))
        destination=RUNTIME/'frozen'/task/'project'
        for name,expected in baseline.items():
            if core.digest(source/name)!=expected:raise ValueError('Starter changed: '+task+'/'+name)
            target=destination/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/name,target)
        # Only L1 begins from a scaffold. Upper levels receive the model's own files.
        if task.endswith('L1'):core.copy_files(source/'solution',destination/'solution',('.godot','__pycache__','plan.json'))
        copy_public(source,destination)
        core.save(RUNTIME/'frozen'/task/'manifest.json',hashes(destination,('.godot','scratch')))
        for p in (RUNTIME/'frozen'/task).rglob('*'):
            if p.is_file():frozen_hashes[p.relative_to(RUNTIME).as_posix()]=core.digest(p)
    core.save(RUNTIME/'run_config.json',config)
    core.save(RUNTIME/'queue.json',{'items':queue})
    (RUNTIME/'P3.md').write_text(system,encoding='utf-8')
    core.save(RUNTIME/'model_tools.json',definitions)
    review=HERE/'review';review.mkdir(exist_ok=True)
    for task in ORDER:
        if task in BLOCKED:continue
        request={'messages':[{'role':'system','content':system},{'role':'user','content':make_prompt(task)}],'tools':definitions}
        core.save(review/(task+'.json'),request)
        (review/(task+'.md')).write_text(system+'\n\n---\n\n'+make_prompt(task),encoding='utf-8')
        # Freeze the exact user text, then substitute only the execution root per model.
        (RUNTIME/'frozen'/task/'prompt.md').write_text(make_prompt(task),encoding='utf-8')
        frozen_hashes[f'frozen/{task}/prompt.md']=core.digest(RUNTIME/'frozen'/task/'prompt.md')
    for name in ['run_config.json','queue.json','P3.md','model_tools.json']:
        frozen_hashes[name]=core.digest(RUNTIME/name)
    implementation=[*HERE.glob('*.py'),HERE/'P3.md',ROOT/'main.py',ROOT/'workspace_layout.py',
                    PILOT/'scene_algorithm_tasks/experiment/run.py',PILOT/'scene_algorithm_tasks/experiment/session.py',PILOT/'forest_grass_lab/experiment/providers.py']
    core.save(RUNTIME/'approval.json',{'approved':True,'time':core.stamp(),'user_instruction':'新测试 forest_benchmark，按照 S1/P3 测试 GPT 两个模型、Claude、Kimi',
        'frozen_hashes':frozen_hashes,'implementation_hashes':{str(p):core.digest(p) for p in implementation}})
    core.save(RUNTIME/'status.json',{'status':'prepared','updated':core.stamp(),'completed_tasks':0,'total_tasks':60,'blocked_tasks':4,'serial':True})
    return config


def verify():
    approval=core.read(RUNTIME/'approval.json')
    for name,digest in approval['frozen_hashes'].items():
        if core.digest(RUNTIME/name)!=digest:raise ValueError('Frozen input changed: '+name)
    for name,digest in approval['implementation_hashes'].items():
        if core.digest(name)!=digest:raise ValueError('Experiment implementation changed: '+name)


def workspace(out,item):
    task=item['task_id'];root=out/'model_workspace'
    if root.exists():raise ValueError('Refusing to overwrite an existing workspace: '+str(root))
    frozen=RUNTIME/'frozen'/task/'project'
    core.copy_files(frozen,root,('.godot','scratch'))
    copy_public(frozen,root)
    parent=RUNS/item['parent'] if item['parent'] else None
    if parent:
        if core.read(parent/'result.json')['stop_reason'] not in core.TERMINAL:raise ValueError('Predecessor is not complete')
        core.copy_files(parent/'model_workspace/solution',root/'solution',('plan.json','.godot','__pycache__'))
    (root/'scratch').mkdir(exist_ok=True)
    (root/'solution').mkdir(exist_ok=True)
    core.copy_files(root/'solution',out/'initial_solution')
    meta=core.read(public_dir(root)/'task.json')
    meta['predecessor']={'condition':'self_predecessor' if parent else 'none','task_id':parent.name if parent else None}
    core.save(public_dir(root)/'task.json',meta)
    refresh_inventory(root)
    prompt=(RUNTIME/'frozen'/task/'prompt.md').read_text(encoding='utf-8')
    prompt=prompt.replace((ROOT/'starters'/task).as_posix(),root.as_posix())
    (public_dir(root)/'prompt.md').write_text(prompt,encoding='utf-8')
    request={'messages':[{'role':'system','content':(RUNTIME/'P3.md').read_text(encoding='utf-8')},{'role':'user','content':prompt}],
             'tools':core.read(RUNTIME/'model_tools.json')}
    core.save(out/'input.json',request)
    core.save(out/'inheritance.json',{'parent':str(parent) if parent else None,'author_reference_injected':False,'files':hashes(root/'solution')})


def worker():
    verify()
    config=core.read(RUNTIME/'run_config.json')
    core.load_keys(config['models'])
    models={m['alias']:m for m in config['models']}
    queue=core.read(RUNTIME/'queue.json')['items']
    completed=0
    with core.file_lock(RUNTIME/'serial.lock',wait=False):
        def publish(current):
            status='paused_error' if current.get('status')=='paused_error' else 'running'
            core.save(RUNTIME/'status.json',{'status':status,'updated':core.stamp(),'pid':os.getpid(),'serial':True,'completed_tasks':completed,'total_tasks':60,'blocked_tasks':4,'current':current})
        for item in queue:
            if (RUNTIME/'STOP').exists():
                core.save(RUNTIME/'status.json',{'status':'paused','updated':core.stamp(),'completed_tasks':completed,'total_tasks':60,'blocked_tasks':4})
                return
            out=RUNS/item['model_alias']/item['task_id']
            if item['blocked']:
                core.save(out/'result.json',{'task_id':item['task_id'],'alias':item['model_alias'],'stop_reason':'blocked_source','error':item['blocked'],'requests':0,'render_calls':0})
                continue
            result_path=out/'result.json'
            if result_path.exists():
                result=core.read(result_path)
                if result['stop_reason'] in core.TERMINAL:
                    completed+=1;continue
                archive=out/'resume_history'/str(time.time_ns());archive.mkdir(parents=True)
                shutil.copy2(result_path,archive/'result.json');result_path.unlink()
            if not (out/'checkpoint.json').exists():
                out.mkdir(parents=True,exist_ok=True)
                workspace(out,item)
            result=core.run_task(out,models[item['model_alias']],config,tools_factory=ExperimentTools,progress=publish)
            print(json.dumps({k:result[k] for k in ['alias','task_id','stop_reason','requests','render_calls']}),flush=True)
            if result['stop_reason'] not in core.TERMINAL:return
            if not (RUNTIME/'STOP').exists():
                publish({'status':'presenting','alias':item['model_alias'],'task_id':item['task_id']})
                present(out/'model_workspace')
            completed+=1
        core.save(RUNTIME/'status.json',{'status':'completed','updated':core.stamp(),'completed_tasks':completed,'total_tasks':60,'blocked_tasks':4,'serial':True})


def launch():
    config=prepare()
    core.load_keys(config['models'])
    if not core.read(RUNTIME/'preflight.json').get('passed'):raise ValueError('Preflight required')
    with core.file_lock(RUNTIME/'serial.lock',wait=False):pass
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    with (RUNTIME/'worker.log').open('a',encoding='utf-8') as stream:
        process=subprocess.Popen([sys.executable,'-B','-X','utf8','-u',str(HERE/'run.py'),'--worker'],cwd=PILOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,
            startupinfo=startup,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.DETACHED_PROCESS,env=dict(os.environ,PYTHONIOENCODING='utf-8'))
    core.save(RUNTIME/'process.json',{'pid':process.pid,'launched':core.stamp(),'command':'forest_benchmark/experiment/run.py --worker'})
    print(json.dumps({'status':'launched','pid':process.pid,'tasks':60,'blocked':4,'serial':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',nargs='?',choices=['prepare','launch','pause','resume']);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:
        try:worker()
        except Exception as error:
            core.save(RUNTIME/'status.json',{'status':'paused_error','updated':core.stamp(),'error':str(error),'pid':os.getpid()})
            raise
    elif args.command=='prepare':prepare();print('Prepared 60 runnable tasks and four source-blocked records.')
    elif args.command=='launch':launch()
    elif args.command=='resume':(RUNTIME/'STOP').unlink(missing_ok=True);launch()
    elif args.command=='pause':RUNTIME.mkdir(parents=True,exist_ok=True);(RUNTIME/'STOP').write_text('user requested pause',encoding='utf-8')
    else:parser.error('Choose prepare, launch or pause')
