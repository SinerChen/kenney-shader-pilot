"""Local experiment viewer; never calls a model or the rendering engine."""
import argparse
import difflib
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime/experiment'
RUNS=ROOT/'runs/s1_p3'


def read(path,default=None):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default


def state():
    config=read(RUNTIME/'run_config.json',{})
    rows=[]
    for item in read(RUNTIME/'queue.json',{'items':[]})['items']:
        out=RUNS/item['model_alias']/item['task_id']
        result=read(out/'result.json',{})
        status=read(out/'status.json',{})
        rows.append({'alias':item['model_alias'],'task':item['task_id'],
                     'status':result.get('stop_reason',status.get('status','blocked_source' if item.get('blocked') else 'pending')),
                     'requests':result.get('requests',status.get('requests',0)),'renders':result.get('render_calls',status.get('render_calls',0))})
    return {'status':read(RUNTIME/'status.json',{}),'models':[{k:m[k] for k in ['alias','model']} for m in config.get('models',[])],'rows':rows}


def case(alias,task):
    if any('/' in v or '\\' in v or '..' in v for v in [alias,task]):raise ValueError('Invalid case')
    out=RUNS/alias/task
    if not out.resolve().is_relative_to(RUNS.resolve()):raise ValueError('Invalid path')
    request=read(out/'input.json',{})
    current=out/'model_workspace/solution';initial=out/'initial_solution'
    files=[]
    paths={p.relative_to(base).as_posix() for base in [current,initial] if base.exists() for p in base.rglob('*') if p.is_file() and not p.name.endswith('.uid')}
    for name in sorted(paths):
        a,b=initial/name,current/name
        old=a.read_text(encoding='utf-8',errors='replace') if a.exists() else ''
        new=b.read_text(encoding='utf-8',errors='replace') if b.exists() else ''
        if len(new)>300000:new=new[:300000]+'\n[preview truncated]'
        files.append({'path':name,'changed':old!=new,'text':new,'diff':''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='initial/'+name,tofile='solution/'+name))})
    events=[]
    log=out/'trajectory.jsonl'
    if log.exists():
        for line in log.read_text(encoding='utf-8').splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            # Full native requests remain available through the raw trajectory link.
            if event['type']=='request':event.pop('body',None)
            events.append(event)
    render=read(out/'presentation.json') or read(out/'latest_render.json',{})
    if render.get('video'):render['video_url']='/'+(out/'model_workspace'/render['video']).relative_to(ROOT).as_posix()
    for image in render.get('images',[]):image['url']='/'+(out/'model_workspace'/image['path']).relative_to(ROOT).as_posix()
    base='/'+out.relative_to(ROOT).as_posix()
    return {'input':request,'result':read(out/'result.json',{}),'status':read(out/'status.json',{}),'plan':read(current/'plan.json',{}),
            'files':files,'events':events,'render':render,'links':{'input':base+'/input.json','trajectory':base+'/trajectory.jsonl','result':base+'/result.json'}}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        request=urlsplit(self.path)
        if request.path.startswith('/api/'):
            try:
                params=parse_qs(request.query)
                data=state() if request.path=='/api/state' else case(params['alias'][0],params['task'][0])
                body=json.dumps(data,ensure_ascii=False).encode('utf-8')
                self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            except (KeyError,ValueError,OSError) as error:self.send_error(400,str(error))
            return
        return super().do_GET()
    def log_message(self,*args):pass


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8772);args=parser.parse_args()
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
