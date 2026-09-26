from pathlib import Path
import copy
import json
import numpy as np
from model import defaults,merge,TASK_OPERATIONS
from generate_cases import sequence,plain,query_commands
from simulation_cpu import Simulator
from judge import compare
from numeric_backend import ROOT,reference_project,engine_run,write_json


def scenarios(task):
    p=defaults(911);p["task_id"]=task
    empty=[[] for _ in range(10)]
    if task=="A_L2":
        p.update(R0=.45,noise_amplitude=0.,width=.3,emit_threshold=.4)
        return [
          ("origin",p,merge(p,{"origin_ref":[.6,.7,0.]}),empty,empty),
          ("speed",p,merge(p,{"speed":2.}),empty,empty),
          ("stop_emission",p,p,empty,[[]]*3+[[{"type":"set","values":{"enable_emission":False}}]]+[[]]*6),
          ("curl_only",p,merge(p,{"curl_strength":1.2}),empty,empty),
          ("visibility_only",p,merge(p,{"burn_visible":False,"embers_visible":False}),empty,empty),
        ]
    if task=="B_L2":
        p.update(wetness=[.6]*48,depth=[.06]*48)
        source=np.zeros(48);source[18]=3.
        p["source"]=source.tolist()
        source2=np.zeros(48);source2[29]=3.
        return [
          ("depth",p,merge(p,{"depth":[.005]*48}),empty,empty),
          ("source_position",p,merge(p,{"source":source2.tolist()}),empty,empty),
          ("stop_source",p,p,empty,[[]]*3+[[{"type":"set","values":{"source":[0.]*48}}]]+[[]]*6),
          ("diffusion",p,merge(p,{"diffusion":0.}),empty,empty),
          ("drying",p,merge(p,{"lambda0":0.}),empty,empty),
        ]
    if task=="C_L2":
        tr=np.eye(4);tr[0,3]=1.2
        return [
          ("clear_cloud",p,merge(p,{"density":[0.]*60}),None,None),
          ("clear_fog",p,merge(p,{"fog_density":0.}),None,None),
          ("move_cloud",p,merge(p,{"cloud_world_to_local":tr.reshape(-1,order="F").tolist()}),None,None),
          ("camera",p,merge(p,{"view_rays":[[1.,1.,4.,-.2,0.,-np.sqrt(.96),8.]]}),None,None),
          ("sun",p,merge(p,{"light_rgb":[0.,0.,0.]}),None,None),
        ]
    if task=="D_L2":
        return [
          ("pattern_only",p,merge(p,{"tiling":4.,"period":.6,"phase":.8}),empty,empty),
          ("velocity",p,merge(p,{"flow":(-np.array(p["flow"])).tolist()}),empty,empty),
          ("still_water",p,merge(p,{"flow":[[0.,0.]]*48}),empty,empty),
          ("stop_source",p,p,empty,[[]]*3+[[{"type":"set","values":{"sources":[]}}]]+[[]]*6),
          ("move_source",p,p,empty,[[]]*3+[[{"type":"set","values":{"sources":[[1.,.7,.7,1.]]}}]]+[[]]*6),
        ]
    if task=="E_L2":
        wave={"type":"wave","event_id":"a","source":[-.6,0.,.8,2.]}
        frames=[[wave]]+[[]]*9
        frames2=[[]]*3+[[{"type":"wave","event_id":"b","source":[.7,.5,.8,2.]}]]+[[]]*6
        return [
          ("wave_source",p,p,frames,frames2),
          ("front_ior",p,merge(p,{"eta_t":1.6}),frames,frames),
          ("clear_wave",p,merge(p,{"height":[0.]*48,"height_prev":[0.]*48}),empty,empty),
          ("hide_front",p,merge(p,{"front_visible":False}),frames,frames),
          ("hide_rear",p,merge(p,{"rear_visible":False}),frames,frames),
        ]
    raise ValueError(task)


def generate(task):
    metadata=json.loads(next((ROOT/"author/specification").glob("04_*/task_manifest.json")).read_text(encoding="utf-8"))
    spec=next(row for row in metadata["tasks"] if row["task_id"]==task)
    result=[]
    for i,((name,a,b,events_a,events_b),meta) in enumerate(zip(scenarios(task),spec["coupling"]),1):
        def commands(p,events):
            if events is None:return query_commands(task,p,[{}],["cloud_query","fog_query"])
            seq=sequence(task,p,events)
            # Both consumers are queried on the same configuration after state advances.
            for query in TASK_OPERATIONS[task[0]+"_L1"]:
                seq.append({"op":"query","name":query,"payload":{}})
            return seq
        ca,cb=commands(a,events_a),commands(b,events_b)
        ea,eb=plain(Simulator().execute(ca)),plain(Simulator().execute(cb))
        out=ROOT/"author/cases_private"/task/f"{task}-I{i:02d}"
        write_json(out/"input.json",{"commands":ca+cb})
        write_json(out/"expected.json",ea+eb)
        write_json(out/"metadata.json",{**meta,"status":"GENERATED","baseline_length":len(ca),"intervention_name":name})
        result.append((out,ca+cb,ea+eb))
    return result


def run(task,project=None,tag="reference"):
    cases=generate(task)
    project=Path(project) if project else reference_project(ROOT/"author/references"/task/"gpu_solution",task)
    commands=[];expected=[];ranges=[]
    for folder,case,answer in cases:
        begin=len(commands);commands+=case;expected+=answer;ranges.append((folder.name,begin,len(commands)))
    out=ROOT/"author/reports"/tag/task/"interactions"
    result=engine_run(project,commands,out,180)
    report=[]
    for name,start,end in ranges:
        errors=compare(expected[start:end],result["responses"][start:end],out)
        report.append({"case":name,"numeric_causal_status":"PASS" if not errors else "FAIL","errors":errors,
                       "visual_causal_status":"NOT_RUN"})
    summary={"task":task,"numeric_causal_pass":sum(r["numeric_causal_status"]=="PASS" for r in report),
             "total":5,"groups":report,"status":"NUMERIC_CAUSAL_VALIDATED" if all(not r["errors"] for r in report) else "FAIL",
             "scope":"actual GPU states under paired interventions; image dependence recorded separately"}
    write_json(out/"report.json",summary)
    return summary


if __name__=="__main__":
    from pathlib import Path
    for task in [x for x in TASK_OPERATIONS if x.endswith("L2")]:
        result=run(task)
        print(task,result["numeric_causal_pass"],"/ 5",flush=True)
        for item in result["groups"]:
            if item["errors"]:print(item["case"],item["errors"][:2],flush=True)
