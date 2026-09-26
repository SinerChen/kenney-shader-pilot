from pathlib import Path
import json
import math
import numpy as np
from model import TASK_OPERATIONS
from numeric_backend import ROOT,reference_project,engine_run,read_resource,write_json

TOLERANCES={"atol":0.0002,"rtol":0.0002}
EXACT={"valid","valid_interval","has_transmission","active"}


def compare(expected,actual,out,path="",errors=None):
    errors=[] if errors is None else errors
    if isinstance(expected,dict) and "numeric" in expected:
        want=np.array(expected["numeric"]).reshape(expected["shape"])
        if want.size==0 and actual.get("status")=="EMPTY":return errors
        try:got=read_resource(out,actual)
        except (ValueError,KeyError,OSError) as exc:
            errors.append({"path":path,"error":str(exc)});return errors
        if got.shape!=want.shape:
            errors.append({"path":path,"shape":list(got.shape),"expected_shape":list(want.shape)});return errors
        if expected.get("fields") is not None and actual.get("fields")!=expected["fields"]:
            errors.append({"path":path,"error":"output field order/names mismatch"})
            return errors
        tolerance=TOLERANCES["atol"]+TOLERANCES["rtol"]*np.abs(want)
        for col,name in enumerate(actual["fields"]):
            if name in EXACT:tolerance[:,col]=0
        delta=np.abs(got-want)
        if not np.all(np.isfinite(got)) or np.any(delta>tolerance):
            idx=np.unravel_index(np.argmax(np.nan_to_num(delta,nan=float("inf"))-tolerance),got.shape)
            errors.append({"path":path,"max_error":float(np.nanmax(delta)),"index":list(map(int,idx)),
                           "actual":float(got[idx]),"expected":float(want[idx]),"allowed":float(tolerance[idx])})
    elif isinstance(expected,dict):
        if not isinstance(actual,dict):errors.append({"path":path,"error":"not an object"})
        else:
            for key,value in expected.items():
                if key not in actual:errors.append({"path":path+"/"+key,"error":"missing field"})
                else:compare(value,actual[key],out,path+"/"+key,errors)
    elif isinstance(expected,list):
        if not isinstance(actual,list) or len(expected)!=len(actual):errors.append({"path":path,"error":"array length mismatch"})
        else:
            for i,(want,got) in enumerate(zip(expected,actual)):compare(want,got,out,path+f"/{i}",errors)
    elif isinstance(expected,(int,float)) and not isinstance(expected,bool):
        if not isinstance(actual,(int,float)) or not math.isclose(expected,actual,abs_tol=1e-6,rel_tol=1e-6):
            errors.append({"path":path,"actual":actual,"expected":expected})
    elif expected!=actual:errors.append({"path":path,"actual":actual,"expected":expected})
    return errors


def numeric(task,project=None,tag="reference",case_task=None):
    case_task=case_task or task
    project=Path(project) if project else reference_project(ROOT/"author/references"/task/"gpu_solution",task)
    cases=sorted((ROOT/"author/cases_private"/case_task).glob(case_task+"-N*"))
    commands=[];expected=[];ranges=[]
    for folder in cases:
        request=json.loads((folder/"input.json").read_text(encoding="utf-8"))
        # Regression retains the L1 contract, while running the L2 submission.
        for cmd in request["commands"]:
            if cmd["op"]=="reset":cmd["config"]["task_id"]=task
        begin=len(commands);commands+=request["commands"]
        expected+=json.loads((folder/"expected.json").read_text(encoding="utf-8"))
        ranges.append((folder.name,begin,len(commands)))
    out=ROOT/"author/reports"/tag/task/("inherited" if case_task!=task else "numeric")
    result=engine_run(project,commands,out,timeout=180)
    report=[]
    for name,start,end in ranges:
        errors=compare(expected[start:end],result["responses"][start:end],out)
        report.append({"case":name,"status":"PASS" if not errors else "FAIL","errors":errors})
    summary={"task":task,"case_task":case_task,"pass":sum(x["status"]=="PASS" for x in report),"total":len(report),
             "status":"PASS" if all(x["status"]=="PASS" for x in report) else "FAIL","groups":report,
             "tolerance":TOLERANCES,"evidence":str(out.relative_to(ROOT)),"scope":"numeric_only"}
    write_json(out/"report.json",summary)
    return summary


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--task",choices=list(TASK_OPERATIONS))
    args=parser.parse_args()
    summaries=[]
    for task in [args.task] if args.task else TASK_OPERATIONS:
        summary=numeric(task);summaries.append(summary)
        print(task,summary["pass"],"/",summary["total"],flush=True)
        for group in summary["groups"]:
            if group["errors"]:print(group["case"],group["errors"][:2],flush=True)
    write_json(ROOT/"author/reports/numeric_summary.json",summaries)
    if any(row["status"]!="PASS" for row in summaries):raise SystemExit(1)
