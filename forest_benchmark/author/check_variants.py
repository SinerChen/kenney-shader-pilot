import shutil
from model import TASK_OPERATIONS
from numeric_backend import ROOT,write_json
from judge import numeric
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import copy_public

results=[]
for task in TASK_OPERATIONS:
    if task.endswith("L2"):
        row=numeric(task,ROOT/"author/references"/task/"gpu_solution",tag="reference",case_task=task[0]+"_L1")
        results.append({"task":task,"type":"inherited","pass":row["pass"],"total":row["total"],"status":row["status"]})
        print(task,"inherited",row["pass"],"/",row["total"],flush=True)
for task in TASK_OPERATIONS:
    path=ROOT/"author/references"/task/"alternative_solution"
    shutil.copytree(ROOT/"author/references"/task/"gpu_solution",path,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".godot"))
    copy_public(ROOT/"author/references"/task/"gpu_solution",path)
    kernel=path/"solution/kernel.txt"
    text=kernel.read_text(encoding="utf-8").replace("local_size_x=64","local_size_x=32")
    text=text.replace("step<=2048","step<=1024").replace("/2048.","/1024.")
    text=text.replace("f*f*f*(f*(f*6.-15.)+10.)","6.*pow(f,vec3(5.))-15.*pow(f,vec3(4.))+10.*pow(f,vec3(3.))")
    kernel.write_text(text,encoding="utf-8")
    adapter=path/"solution/adapter.gd";text=adapter.read_text(encoding="utf-8").replace("float(count)/64.0","float(count)/32.0")
    adapter.write_text(text,encoding="utf-8")
    row=numeric(task,path,tag="alternative")
    results.append({"task":task,"type":"legal_alternative","pass":row["pass"],"total":row["total"],"status":row["status"],
                    "differences":["32 invocations/workgroup","different noise polynomial evaluation","1024 POM coarse intervals"]})
    print(task,"alternative",row["pass"],"/",row["total"],flush=True)
write_json(ROOT/"author/reports/variants.json",results)
