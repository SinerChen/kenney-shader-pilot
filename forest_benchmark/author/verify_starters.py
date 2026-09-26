from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from numeric_backend import ROOT,GODOT,engine_run,write_json
from model import TASK_OPERATIONS

sys.path.insert(0,str(ROOT))
from main import hashes,audit_submission,package_model_task
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import copy_public


def clean_import(project,out):
    # New isolated copy each time: no recursive deletion of an inferred path.
    out.mkdir(parents=True,exist_ok=False)
    shutil.copytree(project,out/"project",ignore=shutil.ignore_patterns(".godot",".git","scratch"))
    copy_public(project,out/"project")
    command=[str(GODOT),"--headless","--editor","--path",str(out/"project"),"--import"]
    result=subprocess.run(command,capture_output=True,timeout=120,creationflags=0x08000000 if os.name=="nt" else 0)
    (out/"import.log").write_bytes(result.stdout+result.stderr)
    text=(result.stdout+result.stderr).decode("utf-8",errors="replace")
    if result.returncode or "SCRIPT ERROR" in text or "Parse Error" in text:raise RuntimeError(text)
    return out/"project"


def run():
    import time
    stamp=str(time.time_ns())
    records=[]
    for task in TASK_OPERATIONS:
        starter=ROOT/"starters"/task
        original=hashes(starter,(".godot","scratch"))
        output=ROOT/"author/reports/clean"/stamp/task
        project=clean_import(starter,output)
        request={"commands":[{"op":"reset","config":{"task_id":task}}]}
        result=engine_run(project,request["commands"],output/"numeric")
        missing=result["responses"][0]["status"]=="NOT_IMPLEMENTED"
        result=engine_run(project,[],output/"visual",script="res://fixture/visual_runner.gd",request_data={"frames":1,"width":320,"height":180})
        unchanged=hashes(starter,(".godot","scratch"))==original
        audit=audit_submission(task,starter)
        packet=package_model_task(task,ROOT/"exports"/stamp/task,review=True)
        packetfiles=hashes(packet["path"],(".godot","scratch"))
        leakfree=not any(any(part in name.lower() for part in ["author/","expected.json","reference_cpu","core.glsl",".git/"]) for name in packetfiles)
        row={"task":task,"clean_import":"PASS","starter":"PASS" if missing and result["status"]=="STARTER_NOT_IMPLEMENTED" else "FAIL",
             "source_unchanged":unchanged,"file_audit":audit["status"],"runtime_protection":result["protection"]["status"],
             "export_whitelist":"PASS" if leakfree else "FAIL","export_files":len(packetfiles),"evidence":str(output.relative_to(ROOT))}
        records.append(row);print(task,row,flush=True)
    write_json(ROOT/"author/reports/starter_validation.json",records)
    return records


if __name__=="__main__":run()
