"""Export audited L1-only gold predecessors, not the unified private development code."""
import json
import re
import shutil
import hashlib
from model import OPERATIONS,QUERY_ROWS
from numeric_backend import ROOT,write_json,engine_run
from judge import numeric
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import copy_public


def braced(text,start):
    opening=text.index("{",start);depth=1;end=opening+1
    while depth:
        depth+=(text[end]=="{")-(text[end]=="}");end+=1
    return end


def kernel_subset(text,ops):
    main=text.index("void main()")
    pre=text[:main];body=text[main:]
    functions={}
    for match in re.finditer(r"^(?:void|float|bool|int|vec[234]|ivec[23]|mat4)\s+(\w+)\s*\([^;\n]*\)\s*\{",pre,re.M):
        functions[match[1]]=pre[match.start():braced(pre,match.start())]
    branches=[]
    for match in re.finditer(r"(?:else )?if\(op==(\d+)\)\s*\{",body):
        if int(match[1]) in ops:
            chunk=body[match.start():braced(body,match.start())]
            branches.append(chunk.removeprefix("else "))
    entry=body[:body.index("if(op==0)")]+("\n    else ".join(branches))+"\n}\n"
    used=set()
    def visit(source):
        for name in re.findall(r"\b(\w+)\s*\(",source):
            if name in functions and name not in used:
                used.add(name);visit(functions[name])
    visit(entry)
    prefix=pre[:pre.index("float at(")]
    constants=next((line for line in pre.splitlines() if line.startswith("const vec3 gradients")),"") if "noise3" in used else ""
    return prefix+constants+"\n"+"\n".join(code for name,code in functions.items() if name in used)+"\n"+entry


def display_subset(text,chain):
    if chain=="E":
        text=re.sub(r'const SURFACE = """.*?"""\n', "",text,flags=re.S)
        text=text.replace('OPTICAL if adapter.task_id.begins_with("E") else SURFACE',"OPTICAL")
    else:
        text=re.sub(r'const OPTICAL = """.*?"""\n', "",text,flags=re.S)
        text=text.replace('OPTICAL if adapter.task_id.begins_with("E") else SURFACE',"SURFACE")
        match=re.search(r'const SURFACE = """(.*?)"""',text,re.S)
        shader=match[1];mode="ABCD".index(chain);start=shader.index("if(mode==0)")
        branch=re.search(r"(?:else )?if\(mode=="+str(mode)+r"\)\s*\{",shader)
        fragment=shader[branch.start():braced(shader,branch.start())].removeprefix("else ")
        shader=shader[:start]+fragment+"\n}\n"
        text=text[:match.start(1)]+shader+text[match.end(1):]
    start=text.index('\tif adapter.task_id == "A_L2":')
    end=text.index("\nfunc texture(",start)
    text=text[:start]+text[end:]
    begin=text.index('\tif task.begins_with("A"):')
    starts=[(m[1],m.start(),m.end()) for m in re.finditer(r'\t(?:if|elif) task.begins_with\("([ABCDE])"\):\n',text)]
    index=next(i for i,x in enumerate(starts) if x[0]==chain)
    stop=starts[index+1][1] if index+1<len(starts) else len(text)
    selected=text[starts[index][2]:stop]
    if chain=="A":selected=selected[:selected.index('\t\tif task.ends_with("L2")')]
    if chain=="B":
        selected=re.sub(r'texture\(adapter.state.wetness_field,\[0,1\],grid_size\) if adapter.state.has\("wetness_field"\) else ',"",selected)
    if chain=="C":
        selected=selected[:selected.index('\t\tif task.ends_with("L2")')]+'\t\tmat.set_shader_parameter("values1",constant_texture(Vector4(0,0,0,1)))\n'
    if chain=="D":
        selected=re.sub(r'texture\(adapter.state.foam_field,\[0,1\],grid_size\) if adapter.state.has\("foam_field"\) else ',"",selected)
    if chain=="E":
        selected=selected.replace('var front=target != "RearWater"','var front=true')
        selected=re.sub(r'\t\t\tvar normals=.*\n|\t\t\tvar heights=.*\n',"",selected)
        selected=re.sub(r'(var point=.*?) if front else .*?\n',r'\1\n',selected)
        selected=re.sub(r'\t\t\t\t\tif not front:\n.*?(?=\t\t\t\t\tif normal.dot)',"",selected,flags=re.S)
    return text[:begin]+"\tif true:\n"+selected


def build(task):
    assert task.endswith("L1")
    source=ROOT/"author/references"/task/"gpu_solution"
    destination=ROOT/"author/gold"/task
    shutil.copytree(source,destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".godot"))
    copy_public(source,destination)
    ops={"A":[0],"B":[3,4,12],"C":[6],"D":[8],"E":[10]}[task[0]]
    path=destination/"solution/kernel.txt"
    path.write_text(kernel_subset(path.read_text(encoding="utf-8"),ops),encoding="utf-8")
    path=destination/"solution/display.gd"
    path.write_text(display_subset(path.read_text(encoding="utf-8"),task[0]),encoding="utf-8")
    path=destination/"solution/adapter.gd";text=path.read_text(encoding="utf-8")
    a=text.index("func _reset_fields(");b=text.index("func _flat(",a)
    init="func _reset_fields():\n"
    if task[0]=="A":init+='\tstate.burn_state=_dispatch("burn_query",{"points":config.anchors})\n'
    elif task[0]=="B":init+='\tstate.depth_field=_dispatch("stamp_query",{"contacts":[]})\n'
    else:init+="\tpass\n"
    text=text[:a]+init+"\n"+text[b:]
    start=text.index("func advance(");stop=text.index("func get_outputs()",start)
    advance='''func advance(dt: float, events: Array) -> Dictionary:
\tconfig.time=simulation_time
\tconfig.dt=dt
\tvar contacts: Array=[]
\tfor event in events:
\t\tif event.get("type","")=="set":
\t\t\tconfig.merge(event.values,true)
\t\t\tcontinue
\t\tvar id=str(event.get("event_id",""))
\t\tif id=="" or processed.has(id):continue
\t\tprocessed[id]=true
\t\tif event.type=="contact":contacts.append(event.contact)
'''
    if task[0]=="A":advance+='\tstate.burn_state=_dispatch("burn_query",{"points":config.anchors})\n'
    if task[0]=="B":advance+='\tvar d=_column(state.depth_field,0) if state.has("depth_field") else config.depth\n\tstate.depth_field=_dispatch("stamp_query",{"depth":d,"contacts":contacts})\n'
    advance+='\tsimulation_time+=dt\n\tconfig.time=simulation_time\n\treturn {"status":"OK","time":simulation_time}\n\n'
    text=text[:start]+advance+text[stop:]
    text=text.replace('var operation_fields: Dictionary = {}','var operation_fields: Dictionary = {}\nvar opcodes: Dictionary = {}')
    text=text.replace('operation_fields = meta.operations','operation_fields = meta.operations\n\topcodes = meta.opcodes')
    text=text.replace('operation_fields.keys().find(name)','opcodes[name]')
    path.write_text(text,encoding="utf-8")
    path=destination/"solution/wire.json";wire=json.loads(path.read_text(encoding="utf-8"))
    allowed=[list(OPERATIONS)[i] for i in ops]
    wire["operations"]={name:OPERATIONS[name] for name in allowed}
    wire["fields_by_operation"]={name:wire["fields_by_operation"][name] for name in allowed}
    wire["opcodes"]={list(OPERATIONS)[i]:i for i in ops}
    wire["query_rows"]={name:QUERY_ROWS[name] for name in allowed if name in QUERY_ROWS}
    write_json(path,wire)
    # Keep only generic inputs and the fields actually read by this L1 implementation.
    path=destination/"solution/defaults.json";p=json.loads(path.read_text(encoding="utf-8"))
    kernel=(destination/"solution/kernel.txt").read_text(encoding="utf-8")
    source_text=text+(destination/"solution/display.gd").read_text(encoding="utf-8")
    used=set(re.findall(r"K_(\w+)",kernel[kernel.index("float at("):]))
    used.update(re.findall(r"\b(?:p|config)\.(\w+)",source_text))
    used.update(["contacts","sources","grid_size","time","t0","dt","task_id"])
    write_json(path,{k:v for k,v in p.items() if k in used})
    return destination


def validate(task):
    project=build(task)
    report=numeric(task,project,tag="gold")
    out=ROOT/"author/reports/gold"/task/"visual"
    visual=engine_run(project,[],out,script="res://fixture/visual_runner.gd",request_data={"frames":3,"width":640,"height":360})
    files={p.relative_to(project/"solution").as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (project/"solution").rglob("*") if p.is_file() and p.suffix!=".uid"}
    success=report["status"]=="PASS" and visual["status"]=="RENDERED" and visual["protection"]["status"]=="PASS"
    certificate={"task":task,"status":"L1_ONLY_VALIDATED" if success else "FAIL","numeric_pass":report["pass"],"visual":visual["status"],"solution_hashes":files,"no_new_level_algorithm":True}
    write_json(ROOT/"author/gold"/f"{task}.json",certificate)
    return certificate


if __name__=="__main__":
    for chain in "ABCDE":
        task=chain+"_L1"
        try:print(task,validate(task),flush=True)
        except Exception as exc:print(task,"ERROR",str(exc),flush=True)
