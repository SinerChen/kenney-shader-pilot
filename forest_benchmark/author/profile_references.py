from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from godot_agent_tools.main import GodotTools
from numeric_backend import ROOT,write_json
from model import TASK_OPERATIONS

reports=[]
for task in TASK_OPERATIONS:
    try:
        host=GodotTools(project=ROOT/"author/references"/task/"gpu_solution",output=ROOT/"author/reports/profile"/task,timeout=180)
        report=host.call("profile_run",warmup=15,frames=40,test_config={"resolution":[640,360]})
        report["task"]=task
        report["scope"]="Includes reference scheduling and display-required readback/upload. Viewport GPU timer does not include the local RenderingDevice compute queue."
        reports.append(report)
        print(task,report["status"],report.get("statistics",{}).get("wall_ms"),flush=True)
    except Exception as exc:
        reports.append({"task":task,"status":"INFRA_ERROR","error":str(exc)})
        print(task,"INFRA_ERROR",str(exc),flush=True)
write_json(ROOT/"author/reports/profile_summary.json",reports)
