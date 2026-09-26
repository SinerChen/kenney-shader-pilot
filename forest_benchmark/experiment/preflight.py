"""No API calls: verify S1 inheritance, hard budgets, image feedback and native rendering."""
import json
from pathlib import Path
import subprocess
import sys
import time

import run as experiment
from shared import ROOT,PILOT,core
from render_worker import ExperimentTools,validate


def check():
    experiment.prepare()
    config=core.read(experiment.RUNTIME/'run_config.json')
    core.load_keys(config['models'])
    test_log=experiment.RUNTIME/'tests.log'
    proc=subprocess.run([sys.executable,'-B','-X','utf8','-m','unittest','discover','-s',str(PILOT/'scene_algorithm_tasks/experiment'),'-p','test_*.py','-v'],capture_output=True,text=True,encoding='utf-8',cwd=PILOT)
    test_log.write_text(proc.stdout+proc.stderr,encoding='utf-8')
    if proc.returncode:raise RuntimeError('Serial runtime tests failed: '+str(test_log))
    original_runs=experiment.RUNS
    trial=experiment.RUNTIME/'preflight_runs'/str(time.time_ns())
    experiment.RUNS=trial
    results=[]
    for task,parent in [('A_L1',None),('A_L2','test/A_L1'),('A_L3','test/A_L2')]:
        out=trial/'test'/task;out.mkdir(parents=True)
        item={'task_id':task,'parent':parent}
        experiment.workspace(out,item)
        root=out/'model_workspace'
        tools=ExperimentTools(root)
        for path in ['../public/model_workspace/task.json','public/task.json',str(ROOT/'author/reference_cpu.py')]:
            assert tools.call('read',{'path':path})['ok'] is False,path
        assert not (root/'solution/plan.json').exists()
        if parent:
            assert (root/'solution/inheritance_marker.txt').read_text()=='model_candidate',task
            assert not (root/'solution/kernel.txt').exists(),'Author reference was injected'
        tools.call('write',{'path':'solution/inheritance_marker.txt','content':'model_candidate'})
        if task!='A_L2':
            camera={'position':[0,8,0],'look_at':[0,0,0]} if task=='A_L1' else {'position':[40,2,-20],'look_at':[43,-3,-26]}
            result=tools.call('render',{'frames':2,'resolution':[320,240],'camera':camera})
            assert result['ok'],result
            assert result['camera']['requested']==camera,result['camera']
            assert len(result['images'])==2 and result['video'],result
            assert tools.call('read',{'path':result['images'][0]['path']})['kind']=='image'
            results.append({'task':task,'render':True,'images':2,'video':result['video'],'camera':result['camera'],'path':str(root)})
            print(task,'actual render, free camera, PNG feedback and MP4 PASS',flush=True)
        # This outcome is only a synthetic preflight parent; never in the real queue.
        core.save(out/'result.json',{'stop_reason':'model_finished'})
        tools.call('write',{'path':'solution/plan.json','content':'{}'})
    experiment.RUNS=original_runs
    for args in [{'frames':0},{'camera':{'position':[0,0,0],'look_at':[0,0,0]}},{'resolution':[50000,50000]}]:
        try:validate(args)
        except ValueError:pass
        else:raise AssertionError('Invalid render request accepted')
    # Exercise the real loop with solution/ instead of effect/, without a model call.
    out=trial/'loop';root=out/'model_workspace';(root/'solution').mkdir(parents=True)
    core.save(out/'input.json',{'messages':[{'role':'system','content':'P3'},{'role':'user','content':'task'}],'tools':[]})
    steps=[{'id':str(i),'goal':'g','expected':'e','counterexample':'c','status':'pending','observations':[],'summary':'','limitations':''} for i in range(4)]
    plan={'status':'in_progress','active_step':'0','steps':steps}
    class FakeSession:
        def __init__(self,*args):self.history=[];self.error_response=None;self.response={};self.key='';self.turn=0
        def payload(self):return '',{},{}
        def next(self):
            self.turn+=1
            return {'finish':'completed','calls':[{'id':'p','name':'write','arguments':{'path':'solution/plan.json','content':json.dumps(plan)}}],'text':''} if self.turn==1 else {'finish':'completed','calls':[],'text':'done'}
        def results(self,values):assert values[0][1]['ok'],values
        def close(self):pass
    result=core.run_task(out,{'model':'test','alias':'test'},config,session_factory=FakeSession,tools_factory=ExperimentTools)
    assert result['stop_reason']=='model_finished' and result['requests']==2 and 'plan.json' in result['candidate_files'],result
    experiment.verify()
    report={'passed':True,'checked':core.stamp(),'model_api_calls':0,'runtime_tests':True,'s1_candidate_inheritance':True,'author_reference_injected':False,
            'native_image_feedback':True,'continuous_video':True,'solution_plan_protocol':True,'actual_renders':results}
    core.save(experiment.RUNTIME/'preflight.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='actual_renders'}))


if __name__=='__main__':check()
