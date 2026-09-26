import json
import numpy as np
from numeric_backend import ROOT,write_json,read_resource
from model import OPERATIONS

STATE={"burn_state":"burn_query","particle_state":"particle_step","depth_field":"stamp_query","wetness_field":"wet_step",
       "foam_field":"foam_step","wave_height_current":"wave_step","wave_height_prev":"wave_step","wave_normal":"wave_normal_query"}


def label(value,name=None):
    if isinstance(value,dict) and "numeric" in value:
        if name in OPERATIONS:
            fields=OPERATIONS[name].copy()
            if name=="fog_query":
                n=(value["shape"][1]-5)//2
                fields += [f"T_cloud_at_samples.{i}" for i in range(n)]+[f"T_fog_light.{i}" for i in range(n)]
            value["fields"]=fields
    elif isinstance(value,dict):
        for key,child in value.items():label(child,STATE.get(key))
    return value


def label_cases():
    for directory in (ROOT/"author/cases_private").glob("*/*"):
        if not (directory/"expected.json").exists():continue
        commands=json.loads((directory/"input.json").read_text(encoding="utf-8"))["commands"]
        expected=json.loads((directory/"expected.json").read_text(encoding="utf-8"))
        for command,response in zip(commands,expected):label(response,command.get("name"))
        write_json(directory/"expected.json",expected)


def differences(expected,actual,out,values):
    if isinstance(expected,dict) and "numeric" in expected:
        want=np.array(expected["numeric"]).reshape(expected["shape"])
        if want.size:values.extend(np.abs(read_resource(out,actual)-want).ravel().tolist())
    elif isinstance(expected,dict):
        for key,value in expected.items():differences(value,actual[key],out,values)
    elif isinstance(expected,list):
        for e,a in zip(expected,actual):differences(e,a,out,values)


def summarize():
    result=[]
    for task in (ROOT/"author/reports/reference").iterdir():
        out=task/"numeric"
        if not (out/"result.json").exists():continue
        actual=json.loads((out/"result.json").read_text(encoding="utf-8"))["responses"]
        cases=sorted((ROOT/"author/cases_private"/task.name).glob(task.name+"-N*"))
        offset=0;groups=[]
        for case in cases:
            expected=json.loads((case/"expected.json").read_text(encoding="utf-8"))
            data=[];differences(expected,actual[offset:offset+len(expected)],out,data);offset+=len(expected)
            groups.append({"case":case.name,"values":len(data),"max_abs":max(data,default=0),"mean_abs":float(np.mean(data)) if data else 0,
                           "p95_abs":float(np.percentile(data,95)) if data else 0})
        result.append({"task":task.name,"groups":groups,"max_abs":max(g["max_abs"] for g in groups)})
    write_json(ROOT/"author/reports/error_statistics.json",result)
    return result


if __name__=="__main__":
    label_cases()
    for row in summarize():print(row["task"],row["max_abs"])
