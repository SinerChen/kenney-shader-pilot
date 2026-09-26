from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time
import numpy as np
from model import defaults, KEYS, OPERATIONS, QUERY_ROWS, gpu_header

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
GODOT=Path(os.environ.get("GODOT_BIN",REPO/"tools/godot/Godot_v4.6.1-stable_win64_console.exe"))


def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def reference_project(path,task="A_L1"):
    path=Path(path)
    for sub in ["solution","fixture"]: (path/sub).mkdir(parents=True,exist_ok=True)
    if not (path/"project.godot").exists(): (path/"project.godot").write_text('config_version=5\n[application]\nconfig/name="Forest reference"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding="utf-8")
    for name in ["adapter_base.gd","runner.gd"]:shutil.copy2(ROOT/"templates"/name,path/"fixture"/name)
    shutil.copy2(ROOT/"author/gpu_adapter.gd",path/"solution/adapter.gd")
    shutil.copy2(ROOT/"author/display.gd",path/"solution/display.gd")
    (path/"solution/kernel.txt").write_text(gpu_header()+(ROOT/"author/core.glsl").read_text(encoding="utf-8"),encoding="utf-8")
    write_json(path/"solution/defaults.json",defaults())
    from gold import kernel_subset
    import re
    full_kernel=(path/"solution/kernel.txt").read_text(encoding="utf-8")
    field_map={}
    for opcode,name in enumerate(OPERATIONS):
        subset=kernel_subset(full_kernel,[opcode])
        used=set(re.findall(r"K_(\w+)",subset[subset.index("float at("):]))
        used.update(["time","dt"])
        field_map[name]=sorted(used)
    write_json(path/"solution/wire.json",{"keys_order":KEYS,"operations":OPERATIONS,"query_rows":QUERY_ROWS,"fields_by_operation":field_map})
    return path


def engine_run(project,commands,out,timeout=120,script="res://fixture/runner.gd",request_data=None):
    project,out=Path(project).resolve(),Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if request_data is not None and script.endswith("visual_runner.gd"):
        for old in out.glob("frame_*.png"):
            if old.resolve().parent!=out:raise ValueError("Unexpected capture link")
            old.unlink()
    source_files={}
    for file in sorted(project.rglob("*")):
        relative=file.relative_to(project)
        if any(part in (".godot","scratch","__pycache__") for part in relative.parts):continue
        if file.is_file():source_files[relative.as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    write_json(out/"source_files.json",source_files)
    request=out/"request.json";write_json(request,request_data or {"commands":commands})
    (out/"result.json").unlink(missing_ok=True)
    environment={k:v for k,v in os.environ.items() if not any(w in k.upper() for w in ("TOKEN","SECRET","PASSWORD","API_KEY"))}
    environment["APPDATA"]=str(ROOT/"runs/appdata"/hashlib.sha256(str(out).encode()).hexdigest()[:8])
    command=[str(GODOT),"--path",str(project),"--rendering-method","forward_plus","--rendering-driver","vulkan","--script",script,
             "--resolution","160x120","--position","-10000,-10000","--audio-driver","Dummy","--",str(request),str(out)]
    start=time.monotonic()
    run=subprocess.run(command,capture_output=True,timeout=timeout,env=environment,creationflags=0x08000000 if os.name=="nt" else 0)
    (out/"godot.log").write_bytes(run.stdout+run.stderr)
    write_json(out/"execution.json",{"returncode":run.returncode,"seconds":time.monotonic()-start,"engine_sha256":hashlib.sha256(GODOT.read_bytes()).hexdigest()})
    result=out/"result.json"
    if run.returncode or not result.exists() or b"SCRIPT ERROR" in run.stderr or b"SHADER ERROR" in run.stderr:
        raise RuntimeError((run.stdout+run.stderr).decode("utf-8",errors="replace"))
    return json.loads(result.read_text(encoding="utf-8"))


def read_resource(out,descriptor):
    if descriptor.get("origin") not in ("actual_gpu_readback","actual_gpu_texture_readback"):
        raise ValueError("No actual GPU output: "+str(descriptor))
    path=Path(out)/descriptor["file"]
    if path.resolve().parent!=Path(out).resolve():raise ValueError("Evidence path escaped its capture directory")
    if descriptor.get("dtype")!="<f4":raise ValueError("Unexpected numeric format")

    return np.frombuffer(path.read_bytes(),dtype="<f4").reshape(descriptor["shape"]).astype(float)


if __name__=="__main__":
    from reference_cpu import evaluate
    project=reference_project(ROOT/"author/runtime/probe_project")
    p=defaults()
    commands=[{"op":"reset","config":p}]+[{"op":"query","name":name,"payload":p} for name in OPERATIONS]
    out=ROOT/"author/reports/gpu_core_smoke"
    result=engine_run(project,commands,out)
    report=[]
    for (name,_),res in zip(OPERATIONS.items(),result["responses"][1:]):
        got=read_resource(out,res);want=evaluate(name,p)
        error=float(np.max(np.abs(got-want)))
        ok=bool(np.allclose(got,want,atol=2e-4,rtol=2e-4))
        report.append({"operation":name,"max_error":error,"pass":ok,"shape":list(got.shape)})
        print(name,error,ok)
    write_json(out/"comparison.json",report)
    if not all(row["pass"] for row in report):raise SystemExit(1)
