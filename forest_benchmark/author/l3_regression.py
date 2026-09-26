"""Repeat old core contracts against sealed L2 code before L3 integration."""
from pathlib import Path
import hashlib
import json
from judge import numeric
from interactions import run
from numeric_backend import ROOT,write_json
from l3_source import TASKS


def run_all():
    rows=[]
    for task in TASKS:
        predecessor=task[0]+"_L2"
        project=ROOT/"author/sealed_l2"/predecessor
        hashes={p.relative_to(project/"solution").as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (project/"solution").rglob("*") if p.is_file() and p.suffix!=".uid"}
        tag="v0_2_regression/"+task
        low=numeric(predecessor,project,tag=tag,case_task=task[0]+"_L1")
        high=numeric(predecessor,project,tag=tag)
        coupled=run(predecessor,project,tag=tag)
        row={"task":task,"predecessor":predecessor,"predecessor_hashes":hashes,
             "core_regression_pass":low["pass"]+high["pass"],"core_total":20,
             "coupling_regression_pass":coupled["numeric_causal_pass"],"coupling_total":5,
             "status":"PASS" if low["status"]==high["status"]=="PASS" and coupled["numeric_causal_pass"]==5 else "FAIL",
             "scope":"Sealed L2 preflight only; does not prove L3 candidate integration or L3 display regressions."}
        rows.append(row);write_json(ROOT/"author/reports/l3/predecessor_regression.json",rows)
        print(task,row["core_regression_pass"],row["coupling_regression_pass"],flush=True)
    from record_l3_verification import certify_preflight
    certify_preflight(rows)
    return rows


if __name__=="__main__":run_all()
