"""Positive-whitelist review export; never enables a blocked native experiment."""
import json
from pathlib import Path
import shutil
import time
from l3_source import ROOT,digest,dump,manifest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir, copy_public, refresh_inventory


def package_review(task,destination=None,predecessor=None,condition="self_predecessor",review=False):
    from l3 import validate_release,read
    if not review:return validate_release(task)
    source=ROOT/"starters"/task
    if not source.exists():return {"task":task,"status":"BLOCKED_SOURCE"}
    baseline=read(ROOT/"author/baseline"/(task+".json"))
    for rel,h in baseline.items():
        if digest(source/rel)!=h:raise ValueError("Sealed native starter changed: "+rel)
    target=Path(destination or ROOT/"exports"/task).resolve()
    if target.exists():raise ValueError("Destination must be new")
    solution=source/"solution"
    if predecessor:
        parent=Path(predecessor).resolve()
        if read(public_dir(parent) / 'task.json')["task_id"]!=task[0]+"_L2":raise ValueError("L3 must inherit its own L2, including both C branches")
        solution=parent/"solution"
    from main import hashes
    files=hashes(solution,(".godot","__pycache__"))
    if predecessor:
        original_assets=manifest(parent/"assets")
        for rel,h in original_assets.items():
            if rel.endswith(".uid"):continue
            if not (source/"assets"/rel).is_file() or digest(source/"assets"/rel)!=h:
                raise ValueError("Predecessor has additional/changed asset dependencies; declare and review their migration first: "+rel)
        if condition=="gold_predecessor":
            cert=read(ROOT/"author/sealed_l2"/(task[0]+"_L2.json"))
            expected={k:v for k,v in cert["solution_hashes"].items() if not k.endswith(".uid")}
            actual={k:v for k,v in files.items() if not k.endswith(".uid")}
            if cert["status"]!="CHAIN_L2_VALIDATED" or actual!=expected:
                raise ValueError("Gold predecessor must match the validated, chain-filtered L2 certificate")
    for rel in files:
        p=solution/rel
        if p.is_symlink() or any(part in {".git",".env","author"} for part in Path(rel).parts):raise ValueError("Forbidden predecessor dependency")
    if not predecessor:
        expected=read(ROOT/"author/l3_migrations"/(task+".json"))["after"]
        if {k:v for k,v in files.items() if not k.endswith(".uid")} != {k:v for k,v in expected.items() if not k.endswith(".uid")}:
            raise ValueError("Blank starter solution changed; cannot label it gold predecessor")
    for rel in baseline:
        dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,dst)
    for rel in files:
        if rel.endswith(".uid"):continue
        dst=target/"solution"/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(solution/rel,dst)
    adapter=target/"solution/adapter.gd"
    text=adapter.read_text(encoding="utf-8")
    if "func bind_scene(" not in text:
        text+='\nfunc bind_scene(_scene_access: Node, _task_config: Dictionary) -> Dictionary:\n\treturn {"status":"UNIMPLEMENTED_BINDING"}\n\nfunc detach_scene() -> Dictionary:\n\treturn {"status":"UNIMPLEMENTED_BINDING"}\n'
        adapter.write_text(text,encoding="utf-8")
    (target/"scratch").mkdir(exist_ok=True)
    copy_public(source,target)
    meta=read(public_dir(target) / 'task.json')
    meta["predecessor"].update(condition=condition if predecessor else "gold_predecessor_review",migrated_solution_hashes=manifest(target/"solution"))
    if predecessor:meta["predecessor"]["original_solution_hashes"]=files
    dump(public_dir(target) / 'task.json',meta)
    from prompts import make_prompt
    from prompt_layout import install_types
    install_types(target,task)
    (public_dir(target) / 'prompt.md').write_text(make_prompt(task,target),encoding="utf-8",newline="\n")
    refresh_inventory(target)
    record={"task":task,"path":str(target),"status":"REVIEW_ONLY","source_origin":"native_snapshot","predecessor":meta["predecessor"],"file_hashes":manifest(target)}
    dump(ROOT/"author/exports"/(task+"_"+str(time.time_ns())+".json"),record)
    return {k:v for k,v in record.items() if k not in {"file_hashes","predecessor"}}
