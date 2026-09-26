"""Reproducible source-input, sealed starter, export and import review."""
from datetime import datetime,timezone
from pathlib import Path
import json
import sys
from l3_source import ROOT,TASKS,dump,manifest
from l3_domains import build
from l3 import audit_runtime,package_review


def verify():
    build()
    sys.path.insert(0,str(ROOT));from main import audit_submission
    rows=[]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for task in TASKS:
        project=ROOT/"starters"/task
        if not project.exists():
            rows.append({"task":task,"status":"BLOCKED_SOURCE"});continue
        dump(ROOT/"author/baseline"/(task+".json"),{k:v for k,v in manifest(project).items() if not k.startswith(("solution/","scratch/"))})
        static=audit_submission(task,project)
        assert static["status"]=="PASS",static
        runtime=audit_runtime(task,frames=30)
        export=package_review(task,ROOT/"exports"/stamp/task,review=True)
        exported_audit=audit_submission(task,export["path"])
        assert exported_audit["status"]=="PASS",exported_audit
        rows.append({"task":task,"status":"NATIVE_BLANK_STARTER_VALIDATED","runtime":runtime,"static":static,"export":export,"export_audit":exported_audit})
        dump(ROOT/"author/reports/l3/starter_validation.json",rows)
        print(task,rows[-1]["status"],flush=True)
    dump(ROOT/"author/reports/l3/starter_validation.json",rows)
    from l3_report import assemble
    assemble()
    return rows


if __name__=="__main__":verify()
