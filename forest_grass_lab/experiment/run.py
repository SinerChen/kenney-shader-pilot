"""Four model chains, one small shader file, existing S1/P3 state machine."""
import argparse
import base64
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import httpx
from providers import Session
from state import State, compact_report, save_json
from local_lock import file_lock
from evaluate import ROOT, evaluate, feedback_images, step_case

HERE=Path(__file__).resolve().parent
RUNS=ROOT/'runs/s1_p3'
LIMIT_REQUESTS=80
LIMIT_CHECKS=24

def stamp(): return datetime.now().astimezone().isoformat(timespec='seconds')

def prompt_for(level,code):
    task=json.loads((ROOT/f'tasks/FG01_L{level}/task.json').read_text(encoding='utf-8'))
    system='\n\n'.join((HERE/name).read_text(encoding='utf-8') for name in ('step_plan.md','P3.md'))
    user='\n\n'.join([(ROOT/f'tasks/FG01_L{level}/prompt.md').read_text(encoding='utf-8'),
        (ROOT/'HOST_API.md').read_text(encoding='utf-8'),'公开案例：\n'+json.dumps(task['public_cases'],ensure_ascii=False,indent=2),
        '本次起始候选代码（L1 为静态起点，后续为同一模型上一层实际代码）：\n```glsl\n'+code+'\n```'])
    return dict(system=system,user=user,images=[],tools=json.loads((HERE/'tools.json').read_text(encoding='utf-8')))

def visible(value,images):
    if isinstance(value,dict): return {k:visible(v,images) for k,v in value.items()}
    if isinstance(value,list): return [visible(v,images) for v in value]
    if isinstance(value,str):
        raw=value.removeprefix('data:image/png;base64,')
        if raw in images:
            return dict(image_file=images[raw],encoding='data_url' if raw!=value else 'base64')
    return value

def restore(value,out):
    if isinstance(value,dict):
        if set(value)=={'image_file','encoding'}:
            raw=base64.b64encode((out/value['image_file']).read_bytes()).decode()
            return ('data:image/png;base64,' if value['encoding']=='data_url' else '')+raw
        return {k:restore(v,out) for k,v in value.items()}
    if isinstance(value,list): return [restore(v,out) for v in value]
    return value

def parse_call(text):
    """Accept an explicit registered tool JSON envelope, never infer a tool from prose/code."""
    names={t['name'] for t in json.loads((HERE/'tools.json').read_text(encoding='utf-8'))}
    value=text.strip()
    if value.startswith('```'):
        value=re.sub(r'^```(?:json)?\s*','',value)
        value=re.sub(r'\s*```$','',value)
    try: data=json.loads(value)
    except (ValueError,TypeError): return None
    if not isinstance(data,dict): return None
    name=data.get('name',data.get('tool'))
    args=data.get('arguments',data.get('parameters',data.get('input')))
    if name not in names or not isinstance(args,(dict,str)): return None
    return dict(name=name,arguments=args,id='text_json')

def transient(error):
    if isinstance(error,httpx.HTTPStatusError):
        return error.response.status_code in (408,409,425,429,500,502,503,504,520,521,522,523,524,554)
    return (isinstance(error,httpx.TransportError) or
            isinstance(error,ValueError) and str(error)=='Chat stream ended without finish_reason; output is incomplete')

def wait_if_paused():
    while (HERE/'PAUSE').exists(): time.sleep(2)

def run_one(alias,config,level,initial,parent):
    out=RUNS/alias/f'L{level}'; out.mkdir(parents=True,exist_ok=True)
    if (out/'result.json').exists(): return json.loads((out/'result.json').read_text(encoding='utf-8'))
    prompt=prompt_for(level,initial)
    fresh=not (out/'checkpoint.json').exists()
    if fresh:
        state=State(out,'P3'); state.main.write_text(initial,encoding='utf-8')
        (out/'initial.gdshader').write_text(initial,encoding='utf-8')
        (out/'system.txt').write_text(prompt['system'],encoding='utf-8')
        (out/'prompt.txt').write_text(prompt['user'],encoding='utf-8')
        save_json(out/'input.json',dict(task=f'FG01_L{level}',alias=alias,config=config,mode='S1',variant='P3',
            parent=parent,budget=dict(requests=80,checks=24),reference_images=False,reference_code=False))
        count=0
    else:
        saved=json.loads((out/'state.json').read_text(encoding='utf-8'))
        state=State.__new__(State); state.out=out; state.variant='P3'; state.main=out/'grass.gdshader'
        for key in ('steps','index','revision','checks','judgements','submitted'): setattr(state,key,saved[key])
        prompt['system']=(out/'system.txt').read_text(encoding='utf-8'); prompt['user']=(out/'prompt.txt').read_text(encoding='utf-8')
        count=json.loads((out/'checkpoint.json').read_text(encoding='utf-8'))['requests']
    images={base64.b64encode(p.read_bytes()).decode():p.relative_to(out).as_posix() for p in (out/'checks').glob('*/*/*.png')}
    session=Session(dict(config,log_api_input=False),prompt)
    if fresh: session.observe('初始状态；首次只调用 set_plan。'+json.dumps(state.view(),ensure_ascii=False))
    else: session.history=restore(json.loads((out/'checkpoint.json').read_text(encoding='utf-8'))['history'],out)
    def log(event):
        data=visible(dict(time=stamp(),**event),images)
        text=json.dumps(data,ensure_ascii=False).replace(session.key,'[redacted]')
        with (out/'trajectory.jsonl').open('a',encoding='utf-8') as f: f.write(text+'\n')
        events=out/'events'; events.mkdir(exist_ok=True)
        index=len(list(events.glob('*.json')))+1
        (events/f'{index:04d}.json').write_text(json.dumps(json.loads(text),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def status(name,**extras):
        save_json(out/'status.json',dict(model=config['model'],alias=alias,level=level,status=name,updated=stamp(),requests=count,
            checks=len(state.checks),completed_steps=state.index,total_steps=len(state.steps),revision=state.revision,**extras))
    def checkpoint():
        state.persist()
        save_json(out/'checkpoint.json',dict(requests=count,history=visible(session.history,images)))
    reason='request_budget'; last_error=None
    status('running'); checkpoint()
    try:
        while count<LIMIT_REQUESTS and not state.submitted:
            wait_if_paused(); count+=1; status('requesting'); checkpoint()
            body=session.payload()[2]
            log(dict(type='request',request_number=count,body=body))
            print(f'\n[API INPUT {alias} L{level} request {count}]\n'+json.dumps(visible(body,images),ensure_ascii=False,indent=2),flush=True)
            try:
                turn=session.next()
            except Exception as error:
                last_error=str(error)
                log(dict(type='api_error',message=last_error,response=session.error_response,request_number=count))
                if transient(error) and count<LIMIT_REQUESTS:
                    retry_at=time.time()+300
                    status('retry_wait',error=last_error,retry_at=datetime.fromtimestamp(retry_at).astimezone().isoformat())
                    while time.time()<retry_at: time.sleep(max(0,min(2,retry_at-time.time())))
                    continue
                reason='api_error'; break
            last_error=None  # A recovered HTTP error remains in the trace, not as the final failure.
            log(dict(type='response',request_number=count,response=session.response,usage=turn.get('usage',{})))
            calls=turn.get('calls',[]); text_call=False
            if not calls:
                c=parse_call(turn.get('text',''))
                if c: calls=[c]; text_call=True
            if len(calls)!=1:
                reply=dict(ok=False,error='Exactly one registered tool per reply; none executed.',state=state.view())
                if calls: session.results([(c,reply) for c in calls])
                else: session.observe(json.dumps(reply,ensure_ascii=False))
                log(dict(type='protocol',result=reply)); checkpoint(); continue
            call=calls[0]; pictures=[]; record=None
            try:
                args=call['arguments'] if isinstance(call['arguments'],dict) else json.loads(call['arguments'])
                if not isinstance(args,dict): raise ValueError('arguments must be an object')
                name=call['name']
                if not state.steps and name!='set_plan': raise ValueError('First operation must be set_plan')
                if name=='set_plan': reply=state.plan(args)
                elif name=='read_main': reply=dict(ok=True,code=state.code(),state=state.view())
                elif name=='update_main':
                    # The candidate cannot include files or load external answers.
                    candidate=args.get('code','')
                    if '#include' in candidate: raise ValueError('Only this shader file is allowed; no includes')
                    old=state.code(); old_revision=state.revision
                    reply=state.update(args)
                    if '#include' in state.code():
                        state.main.write_text(old,encoding='utf-8'); state.revision=old_revision
                        raise ValueError('Only this shader file is allowed; no includes')
                elif name=='check':
                    step=state.active(args)
                    if len(state.checks)>=LIMIT_CHECKS: raise ValueError('Check budget exhausted')
                    for field in ('claim','expected','counterexample'):
                        if not isinstance(args.get(field),str) or not args[field].strip(): raise ValueError(f'{field} is required')
                    kind=args.get('kind')
                    if kind=='step': step_case(args)
                    elif kind=='public':
                        if any(k in args for k in ('scene','params','frames','schedule')): raise ValueError('public does not accept overrides')
                    else: raise ValueError('kind must be step/public')
                    cid=f'check_{len(state.checks)+1:03d}'; folder=out/'checks'/cid; folder.mkdir(parents=True)
                    shader=folder/'grass.gdshader'; shader.write_text(state.code(),encoding='utf-8')
                    record=dict(id=cid,step_id=step['id'],revision=state.revision,kind=kind,scene='target',request=args,execution_ok=False,images_sent=False)
                    state.checks.append(record); save_json(folder/'request.json',record); checkpoint(); status('rendering')
                    report=evaluate(level,shader,folder,args if kind=='step' else None)
                    record['execution_ok']=report['execution_ok']; pictures=feedback_images(level,folder,kind)
                    reply=dict(ok=report['execution_ok'],check_id=cid,revision=state.revision,**compact_report(report),images_follow=bool(pictures),state=state.view())
                elif name=='finish_step': reply=state.finish(args)
                elif name=='submit': reply=state.submit()
                else: raise ValueError('Unknown tool')
            except Exception as error:
                reply=dict(ok=False,error=str(error),state=state.view())
            log(dict(type='tool',call=call,result=reply,text_json_compatibility=text_call))
            if text_call: session.observe('工具执行结果：'+json.dumps(reply,ensure_ascii=False))
            else: session.results([(call,reply)])
            if pictures:
                labels=[p.relative_to(out).as_posix() for p in pictures]
                for p,label in zip(pictures,labels): images[base64.b64encode(p.read_bytes()).decode()]=label
                session.observe('本次 Godot 目标场景真实 PNG，顺序如下。执行无错误不等于视觉通过：'+json.dumps(dict(check_id=record['id'],revision=state.revision,images=labels),ensure_ascii=False),pictures)
                record['images_sent']=True
                log(dict(type='observation',check_id=record['id'],images=labels,revision=state.revision))
            checkpoint(); status('running')
        if state.submitted: reason='submitted'
    except Exception as error:
        reason='local_error'; last_error=str(error); log(dict(type='local_error',error=last_error))
    finally:
        checkpoint(); session.close()
    status('final_render')
    try:
        report=evaluate(level,state.main,out/'final',animation=True)
    except Exception as error:
        report=dict(execution_ok=False,errors=[str(error)],cases=[])
    summary=dict(model=config['model'],alias=alias,level=level,submitted=state.submitted,stop_reason=reason,error=last_error,
        requests=count,evaluate_calls=len(state.checks),completed_steps=state.index,total_steps=len(state.steps),execution=report,
        visual_quality='not_independently_evaluated',stage_verdicts='model_self_assessment',finished=stamp())
    save_json(out/'result.json',summary); status('finished',stop_reason=reason,submitted=state.submitted)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return summary

def reopen_failed(out):
    """Keep the interrupted attempt, then resume its original checkpoint and budget."""
    out=Path(out).resolve()
    if not out.is_relative_to(RUNS.resolve()): raise ValueError('Resume path is outside experiment results')
    result_path=out/'result.json'
    if not result_path.exists(): return
    result=json.loads(result_path.read_text(encoding='utf-8'))
    if result.get('submitted') or result.get('stop_reason') not in ('api_error','local_error'): return
    if not (out/'checkpoint.json').exists(): raise ValueError('Cannot resume without a checkpoint')
    checkpoint=json.loads((out/'checkpoint.json').read_text(encoding='utf-8'))
    if checkpoint['requests']>=LIMIT_REQUESTS: raise ValueError('Request budget exhausted; no automatic budget increase')
    archive=(out/'restart_history'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')).resolve()
    if not archive.is_relative_to(out): raise ValueError('Invalid archive path')
    archive.mkdir(parents=True)
    for name in ('checkpoint.json','state.json','grass.gdshader'):
        shutil.copy2(out/name,archive/name)
    for name in ('result.json','status.json','final'):
        source=(out/name).resolve()
        if not source.is_relative_to(out): raise ValueError('Invalid archive source')
        if source.exists(): shutil.move(str(source),str(archive/name))
    save_json(archive/'restart.json',dict(time=stamp(),reason='User requested restart',
        mode='resume_same_checkpoint_and_budget',requests=checkpoint['requests']))

def archive_model(alias):
    source=(RUNS/alias).resolve()
    if not source.is_relative_to(RUNS.resolve()): raise ValueError('Invalid model archive source')
    if not source.exists(): return None
    destination=(RUNS.parent/'archive'/f'{alias}_{datetime.now():%Y%m%d_%H%M%S_%f}').resolve()
    if not destination.is_relative_to(RUNS.parent.resolve()): raise ValueError('Invalid model archive destination')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(source),str(destination))
    source.mkdir(parents=True)
    save_json(source/'restart.json',dict(time=stamp(),reason='User explicitly requested a fresh rerun',
        previous_run=destination.relative_to(ROOT).as_posix(),budget=dict(requests=80,checks=24)))
    return destination

def worker(alias,resume_errors=False,restart_all=False,start_level=1):
    if start_level not in (1,2,3) or restart_all and start_level!=1:
        raise ValueError('Invalid start level or whole-chain restart combination')
    for line in Path(r'D:\threejs_seven_experiments\.env').read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or '=' not in line: continue
        key,value=line.split('=',1)
        os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))
    configs=json.loads((HERE/'models.json').read_text(encoding='utf-8'))
    config=configs[alias]
    if not os.environ.get(config['api_key_env']): raise ValueError('Missing '+config['api_key_env'])
    RUNS.mkdir(parents=True,exist_ok=True)
    with file_lock(ROOT/'runtime'/f'{alias}.lock',wait=False):
        if restart_all: archive_model(alias)
        code=(ROOT/'project/effect/grass.gdshader').read_text(encoding='utf-8'); parent=None
        if start_level>1:
            previous=RUNS/alias/f'L{start_level-1}'
            result=json.loads((previous/'result.json').read_text(encoding='utf-8'))
            path=previous/'grass.gdshader';code=path.read_text(encoding='utf-8')
            parent=dict(task=f'FG01_L{start_level-1}',code=path.relative_to(ROOT).as_posix(),
                        submitted=result['submitted'],stop_reason=result['stop_reason'])
        for level in range(start_level,4):
            if resume_errors: reopen_failed(RUNS/alias/f'L{level}')
            result=run_one(alias,config,level,code,parent)
            if result['stop_reason'] in ('api_error','local_error'): break
            path=RUNS/alias/f'L{level}/grass.gdshader'
            code=path.read_text(encoding='utf-8')
            parent=dict(task=f'FG01_L{level}',code=path.relative_to(ROOT).as_posix(),submitted=result['submitted'],stop_reason=result['stop_reason'])

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--worker'); parser.add_argument('--launch',action='store_true'); parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--models',nargs='+',help='Launch only these configured aliases')
    parser.add_argument('--resume-errors',action='store_true',help='Archive failed summary and continue the same checkpoint/budget')
    args=parser.parse_args()
    if args.dry_run:
        prompt=prompt_for(1,(ROOT/'project/effect/grass.gdshader').read_text(encoding='utf-8'))
        save_json(ROOT/'verification/p3-input-preview.json',prompt); print('Dry run: prompt saved; no API calls.'); return
    if args.worker: worker(args.worker,args.resume_errors); return
    if args.launch:
        logs=ROOT/'runtime/logs'; logs.mkdir(parents=True,exist_ok=True)
        configurations=json.loads((HERE/'models.json').read_text(encoding='utf-8'))
        selected=args.models or list(configurations)
        if len(set(selected))!=len(selected) or any(alias not in configurations for alias in selected): parser.error('Choose unique configured model aliases')
        record=ROOT/'runtime/processes.json'
        processes=json.loads(record.read_text(encoding='utf-8')).get('pids',{}) if record.exists() else {}
        startup=subprocess.STARTUPINFO(); startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=0
        for alias in selected:
            with (logs/f'{alias}.log').open('a',encoding='utf-8') as stream:
                command=[sys.executable,'-u',str(Path(__file__).resolve()),'--worker',alias]
                if args.resume_errors: command.append('--resume-errors')
                p=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,startupinfo=startup,
                    env=dict(os.environ,PYTHONIOENCODING='utf-8'),creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                processes[alias]=p.pid
        save_json(ROOT/'runtime/processes.json',dict(started=stamp(),pids=processes)); print(processes)

if __name__=='__main__': main()
