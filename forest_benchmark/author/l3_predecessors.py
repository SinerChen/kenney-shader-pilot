"""Seal chain-specific L2 gold code; do not expose the unified author kernel."""
from pathlib import Path
import json
import shutil
from l3_source import ROOT,TASKS,dump,manifest
from gold import kernel_subset
from model import OPERATIONS
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir, copy_public


def seal(chain):
    task=chain+"_L2"
    original=ROOT/"author/references"/task/"gpu_solution"
    target=ROOT/"author/sealed_l2"/task
    shutil.copytree(original,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".godot","*.uid"))
    copy_public(original,target)
    ops={"A":[0,1,2],"B":[3,4,5,12],"C":[6,7],"D":[8,9],"E":[9,10,11,12]}[chain]
    path=target/"solution/kernel.txt"
    path.write_text(kernel_subset(path.read_text(encoding="utf-8"),ops),encoding="utf-8")
    path=target/"solution/wire.json";wire=json.loads(path.read_text(encoding="utf-8"))
    allowed=[list(OPERATIONS)[i] for i in ops]
    wire["operations"]={key:wire["operations"][key] for key in allowed}
    wire["fields_by_operation"]={key:wire["fields_by_operation"][key] for key in allowed}
    wire["opcodes"]={list(OPERATIONS)[i]:i for i in ops}
    dump(path,wire)
    path=target/"solution/adapter.gd";s=path.read_text(encoding="utf-8")
    s=s.replace('var operation_fields: Dictionary = {}','var operation_fields: Dictionary = {}\nvar opcodes: Dictionary = {}')
    s=s.replace('operation_fields = meta.operations','operation_fields = meta.operations\n\topcodes = meta.opcodes')
    s=s.replace('operation_fields.keys().find(name)','opcodes[name]')
    path.write_text(s,encoding="utf-8")
    hashes=manifest(target/"solution")
    certificate={"task":task,"status":"CHAIN_FILTERED_PENDING_REGRESSION","operations":allowed,"solution_hashes":hashes,
                 "source_solution_hashes":manifest(original/"solution"),"utility_note":"B retains height normals; E retains the shared GPU radial-source helper used by its existing wave event path."}
    dump(ROOT/"author/sealed_l2"/(task+".json"),certificate)
    for l3task in [t for t in TASKS if t[0]==chain]:
        project=ROOT/"starters"/l3task
        if not project.exists():continue
        shutil.copytree(target/"solution",project/"solution",dirs_exist_ok=True)
        adapter=project/"solution/adapter.gd"
        adapter.write_text(adapter.read_text(encoding="utf-8")+'\nfunc bind_scene(_scene_access: Node, _task_config: Dictionary) -> Dictionary:\n\treturn {"status":"UNIMPLEMENTED_BINDING"}\n\nfunc detach_scene() -> Dictionary:\n\treturn {"status":"UNIMPLEMENTED_BINDING"}\n',encoding="utf-8")
        meta=json.loads((public_dir(project) / 'task.json').read_text(encoding="utf-8"))
        meta["predecessor"].update(original_solution_hashes=hashes,migrated_solution_hashes=manifest(project/"solution"),core_operations=allowed)
        dump(public_dir(project) / 'task.json',meta)
        dump(ROOT/"author/l3_migrations"/(l3task+".json"),{"predecessor":str(target),"condition":"gold_predecessor_review","before":hashes,"after":manifest(project/"solution"),
             "patch":"Append empty bind/detach only; no L3 algorithm. Predecessor source first restricted to its chain and required utility helpers.","scene_capture_fixture_inherited":False})
        dump(ROOT/"author/baseline"/(l3task+".json"),{k:v for k,v in manifest(project).items() if not k.startswith(("solution/","scratch/"))})
    return certificate


if __name__=="__main__":
    for chain in "ABCDE":print(seal(chain)["task"],flush=True)
