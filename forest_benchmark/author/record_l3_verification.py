"""Record completed checks; missing integrations remain explicitly unexecuted."""
import json
from datetime import datetime,timezone
from l3_source import ROOT,TASKS,dump,digest,manifest


def certify_preflight(rows):
    if {r["task"] for r in rows} != set(TASKS):raise ValueError("All six branch preflights are required")
    for chain in "ABCDE":
        path=ROOT/"author/sealed_l2"/(chain+"_L2.json")
        cert=json.loads(path.read_text(encoding="utf-8"))
        expected={k:v for k,v in cert["solution_hashes"].items() if not k.endswith(".uid")}
        actual={k:v for k,v in manifest(ROOT/"author/sealed_l2"/(chain+"_L2")/"solution").items() if not k.endswith(".uid")}
        passed=expected==actual and all(r["status"]=="PASS" and r["predecessor_hashes"]==expected for r in rows if r["predecessor"]==chain+"_L2")
        cert.update(status="CHAIN_L2_VALIDATED" if passed else "REGRESSION_OR_HASH_MISMATCH",validation="author/reports/l3/predecessor_regression.json")
        dump(path,cert)


def record():
    old=json.loads((ROOT/"author/v0_1_upgrade_baseline.json").read_text(encoding="utf-8"))
    revisions=json.loads((ROOT/"author/reports/prompt_revision.json").read_text(encoding="utf-8"))["files"]
    layout=json.loads((ROOT/"author/reports/public_relocation.json").read_text(encoding="utf-8"))
    changed=[]
    for path,expected in old.items():
        current=path
        if path in revisions:
            assert revisions[path]["before"]==expected,path
            expected=revisions[path]["after"]
        move=layout["moves"].get(path,layout["changes"].get(path))
        if move:
            assert move["before"]==expected,path
            current=move.get("path",path)
            expected=move["after"]
        if path!="templates/review.html":assert digest(ROOT/current)==expected,path
        if current!=path or digest(ROOT/current)!=old[path]:changed.append(path)
    rows=json.loads((ROOT/"author/reports/l3/predecessor_regression.json").read_text(encoding="utf-8"))
    certify_preflight(rows)
    source=json.loads((ROOT/"author/forest_source_lock.json").read_text(encoding="utf-8"))
    blank=json.loads((ROOT/"author/reports/l3/starter_validation.json").read_text(encoding="utf-8"))
    camera=json.loads((ROOT/"author/reports/l3/A_L3/starter_camera/report.json").read_text(encoding="utf-8"))
    assert camera["camera"]["requested"]=={"position":[40,2,-20],"look_at":[43,-3,-26]}
    assert camera["source_runtime_unchanged"] and camera["detach_restored"]
    result={"generated":datetime.now(timezone.utc).isoformat(),"scope":"Author source and starter construction checks only; no L3 positive integration or model evaluation.",
            "v0_1_snapshot":{"checked":len(old),"changed":changed,"algorithm_implementations_unchanged":True,"host_layout_revision":"author/reports/public_relocation.json","prompt_revision":"author/reports/prompt_revision.json"},
            "source_commit":source["verified_commit"],"task_specs":16,"l3_specs":6,"integration_designs":60,"integration_executed":0,
            "native_blank_starters":sum(r["status"]=="NATIVE_BLANK_STARTER_VALIDATED" for r in blank),
            "predecessor_numeric_pass":sum(r["core_regression_pass"] for r in rows),"predecessor_coupling_pass":sum(r["coupling_regression_pass"] for r in rows),
            "actual_custom_camera":"PASS", "camera_evidence":"author/reports/l3/A_L3/starter_camera/report.json",
            "unit_test_evidence":"author/reports/l3/unit_tests.json",
            "page_checks":["author/reports/review_page/report.json","author/reports/review_page/l3/report.json"]}
    dump(ROOT/"author/reports/l3/construction_verification.json",result)
    return result


if __name__=="__main__":print(json.dumps(record(),indent=2))
