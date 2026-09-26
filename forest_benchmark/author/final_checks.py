import json
import subprocess
import sys
import time
from pathlib import Path
from model import defaults,TASK_OPERATIONS
from numeric_backend import ROOT,reference_project,engine_run,read_resource,write_json
from reference_cpu import evaluate
from visual_controls import check_bound_resources
from judge import numeric
import numpy as np
sys.path.insert(0,str(ROOT))
from main import build_starter,run_reference,capture_visuals


def run():
    records=[]
    for task in TASK_OPERATIONS:
        build_starter(task);run_reference(task)
    # New integer-ID packing is checked independently at the float32 precision boundary.
    p=defaults()
    p.update(mask=[1.]*48,d_max=.1,contacts=[[16777216,0,0,0,4,3,.02],[16777217,0,0,0,4,3,.02]])
    out=ROOT/"author/reports/large_event_ids"
    result=engine_run(ROOT/"author/references/B_L1/gpu_solution",[{"op":"reset","config":p},{"op":"query","name":"stamp_query","payload":p}],out)
    got=read_resource(out,result["responses"][1])
    assert np.allclose(got,evaluate("stamp_query",p),atol=1e-7)
    write_json(out/"report.json",{"status":"PASS","minimum_depth":float(got.min()),"expected_depth":.04})
    for task in TASK_OPERATIONS:
        row=numeric(task,ROOT/"author/references"/task/"gpu_solution")
        if row["status"]!="PASS":raise RuntimeError(row)
        print(task,"numeric",row["pass"],flush=True)
        first=capture_visuals(task,frames=90)
        consistency=check_bound_resources(task,ROOT/"author/reports"/task/"visual")
        camera={"position":[-2.2,1.8,4.],"look_at":[0.,1.,0.]} if task.startswith("A") else {"position":[2.6,1.45,3.7],"look_at":[0.,.15,0.]}
        second=capture_visuals(task,frames=90,camera=camera,label="oblique")
        records.append({"task":task,"numeric":row["status"],"overview":first,"oblique":second,"gpu_render_consistency":consistency})
        print(task,"videos",first["status"],second["status"],consistency["status"],flush=True)
        write_json(ROOT/"author/reports/final_checks.json",records)
    return records


if __name__=="__main__":run()
