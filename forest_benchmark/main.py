"""Forest benchmark author CLI and restricted solver-facing file tools. No model API."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workspace_layout import public_dir, copy_public, refresh_inventory
CORE_TASKS=[f"{chain}_L{level}" for chain in "ABCDE" for level in (1,2)]
L3_TASKS=["A_L3","B_L3","C_L3_R","C_L3_S","D_L3","E_L3"]
TASKS=CORE_TASKS+L3_TASKS
PYTHON=sys.executable


def author_modules():
    path=str(ROOT/"author")
    if path not in sys.path:sys.path.insert(0,path)
    if not (ROOT/"author/build.py").exists():raise RuntimeError("Author files are not included in a model task package.")


def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def hashes(root,exclude=()):
    root=Path(root).resolve()
    if root.is_symlink() or root.is_junction():raise ValueError("Linked workspace is not allowed")
    result={}
    for p in sorted(root.rglob("*")):
        rel=p.relative_to(root)
        if any(part in exclude for part in rel.parts):continue
        if p.is_symlink() or (p.is_dir() and p.is_junction()):raise ValueError("Linked paths are not allowed: "+str(rel))
        if p.is_file():result[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def build_starter(task):
    if task in L3_TASKS:return l3_call("build_l3_starter",task)
    author_modules()
    from build import build_starter as build
    path=build(task)
    baseline=hashes(path,(".godot","solution","scratch"))
    dump(ROOT/"author/baseline"/f"{task}.json",baseline)
    return {"status":"STARTER_BUILT","task":task,"path":str(path)}


def run_reference(task):
    if task in L3_TASKS:return {"task":task,"status":"NOT_IMPLEMENTED","scope":"Native integration reference pending; inherited L2 code is not an L3 reference."}
    author_modules()
    from numeric_backend import reference_project
    dest=ROOT/"author/references"/task/"gpu_solution"
    shutil.copytree(ROOT/"starters"/task,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".godot",".git","scratch"))
    copy_public(ROOT/"starters"/task,dest)
    reference_project(dest,task)
    return {"status":"REFERENCE_BUILT","task":task,"project":str(dest)}


def audit_submission(task,submission):
    submission=Path(submission).resolve()
    baseline_path=ROOT/"author/baseline"/f"{task}.json"
    baseline=json.loads(baseline_path.read_text(encoding="utf-8"))
    if task in L3_TASKS:
        for record_path in sorted((ROOT/"author/exports").glob(task+"_*.json")):
            record=json.loads(record_path.read_text(encoding="utf-8"))
            if Path(record["path"]).resolve()==submission:
                baseline={k:v for k,v in record["file_hashes"].items() if not k.startswith(("solution/","scratch/"))}
    try:
        current=hashes(submission,(".godot","scratch"))
    except ValueError as exc:return {"status":"FAIL","errors":[str(exc)]}
    changed=[name for name,digest in baseline.items() if current.get(name)!=digest]
    extra=[name for name in current if name not in baseline and not name.startswith("solution/")]
    suspicious=[]
    for name in current:
        if not name.startswith("solution/"):continue
        file=submission/name
        if file.suffix.lower() in {".zip",".7z",".exe",".dll",".pck",".so",".pyc"}:suspicious.append(name+": binary/packed dependency")
        if file.suffix.lower() in {".gd",".gdshader",".glsl",".txt",".tscn",".tres"}:
            text=file.read_text(encoding="utf-8",errors="replace")
            for pattern in ("res://../","author/","cases_private","expected.json","OS.execute","OS.create_process","HTTPRequest","TCPServer","TCPStream"):
                if pattern in text:suspicious.append(name+": "+pattern)
    return {"status":"PASS" if not changed and not extra and not suspicious else "FAIL",
            "changed_protected":changed,"unexpected_files":extra,"dependency_review":suspicious,
            "solution_hashes":{k:v for k,v in current.items() if k.startswith("solution/")},
            "scope":"static file audit; runtime protection is reported by capture, OS isolation is a separate gate"}


def _trusted_submission(task,submission):
    path=Path(submission).resolve()
    trusted=ROOT/"author/references"/task/"gpu_solution"
    if path!=trusted.resolve():
        raise RuntimeError("Untrusted candidate execution requires an OS-isolated worker. This local author runner only executes its reference projects; no model experiment has been started.")
    return path


def run_numeric(task,submission=None,inherited=False):
    if task in L3_TASKS:return {"task":task,"status":"NOT_RUN","scope":"L3 candidate core regression is separate from sealed predecessor preflight."}
    author_modules()
    from judge import numeric
    submission=submission or ROOT/"author/references"/task/"gpu_solution"
    path=_trusted_submission(task,submission)
    return numeric(task,path,case_task=task[0]+"_L1" if inherited else task)


def run_interactions(task,submission=None):
    if task in L3_TASKS:return {"task":task,"status":"NOT_RUN","scope":"L3 candidate coupling regression pending."}
    if not task.endswith("L2"):return {"status":"NOT_APPLICABLE","task":task}
    author_modules()
    from interactions import run
    path=_trusted_submission(task,submission or ROOT/"author/references"/task/"gpu_solution")
    return run(task,path)


def capture_visuals(task,submission=None,frames=90,camera=None,config=None,events=None,label="visual"):
    if task in L3_TASKS:
        if submission is not None:raise RuntimeError("Native candidate rendering requires an isolated worker")
        if config is not None or events is not None:
            raise ValueError("audit_runtime checks the sealed blank starter; custom simulation inputs require the integration worker")
        return l3_call("audit_runtime",task,frames=frames,camera=camera)
    author_modules()
    from numeric_backend import engine_run
    path=_trusted_submission(task,submission or ROOT/"author/references"/task/"gpu_solution")
    out=ROOT/"author/reports"/task/label
    request={"frames":frames,"width":640,"height":360,"dt":1/15}
    if camera is not None:request["camera"]=camera
    if config is not None:request["config"]=config
    if events is not None:request["events"]=events
    report=engine_run(path,[],out,timeout=180,script="res://fixture/visual_runner.gd",request_data=request)
    video=encode_video(out,15,frames)
    report["video"]=str(video) if video else None
    dump(out/"report.json",report)
    return {"status":report["status"],"task":task,"protection":report["protection"]["status"],"video":report["video"],"evidence":str(out)}


def encode_video(directory,fps,frames=None):
    exe=shutil.which("ffmpeg")
    if exe is None:
        try:
            import imageio_ffmpeg
            exe=imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:return None
    directory=Path(directory)
    video=directory/"effect.mp4"
    result=subprocess.run([exe,"-y","-loglevel","error","-framerate",str(fps),"-i",str(directory/"frame_%05d.png"),
                           *(["-frames:v",str(frames)] if frames is not None else []),"-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(video)],
                          capture_output=True,timeout=90,creationflags=0x08000000 if os.name=="nt" else 0)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors="replace"))
    return video


def package_model_task(task,destination=None,predecessor=None,condition="self_predecessor",review=False):
    if task in L3_TASKS:return l3_call("package_review",task,destination=destination,predecessor=predecessor,condition=condition,review=review)
    release=validate_release(task)
    if not review and release["status"]!="RELEASE_READY":
        return {"status":"BLOCKED_RELEASE","blockers":release["blockers"],"hint":"--review exports a clearly labelled review workspace, not an experiment-ready package"}
    if task.endswith("L2") and predecessor is None and not review:
        return {"status":"INHERITANCE_REQUIRED","task":task}
    source=ROOT/"starters"/task
    destination=Path(destination) if destination else ROOT/"exports"/task
    destination=destination.resolve()
    if destination.exists():raise ValueError("Destination must be new; refusing to overwrite a candidate.")
    baseline=json.loads((ROOT/"author/baseline"/f"{task}.json").read_text(encoding="utf-8"))
    source_hashes=hashes(source,(".godot","scratch"))
    if any(source_hashes.get(k)!=v for k,v in baseline.items()):raise ValueError("Starter changed after its baseline was sealed.")
    allowed=list(baseline)+["solution/adapter.gd","solution/effect.tscn"]
    for rel in allowed:
        src=source/rel
        if not src.is_file() or src.is_symlink():raise ValueError("Missing or linked whitelist entry: "+rel)
    # Export from a positive whitelist; never copy an author tree and delete names.
    for rel in allowed:
        dst=destination/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,dst)
    copy_public(source,destination)
    (destination/"scratch").mkdir(exist_ok=True)
    inheritance={"condition":"none","source_hashes":{}}
    if task.endswith("L2"):
        inheritance={"condition":"NOT_INJECTED","source_hashes":{}}
        if predecessor is not None:
            parent=Path(predecessor).resolve()
            solution=parent/"solution"
            if not solution.is_dir():raise ValueError("Predecessor must contain solution/")
            predecessor_task=task[0]+"_L1"
            meta=json.loads((public_dir(parent) / 'task.json').read_text(encoding="utf-8"))
            if meta["task_id"]!=predecessor_task:raise ValueError("Wrong predecessor task.")
            if condition=="gold_predecessor":
                certificate_path=ROOT/"author/gold"/(predecessor_task+".json")
                certificate=json.loads(certificate_path.read_text(encoding="utf-8"))
                if parent!=(ROOT/"author/gold"/predecessor_task).resolve() or certificate.get("status")!="L1_ONLY_VALIDATED":
                    raise ValueError("Gold predecessor is not the audited L1-only export.")
                if hashes(solution,(".godot","__pycache__"))!=certificate["solution_hashes"]:
                    raise ValueError("Gold predecessor changed after validation.")
            inherited_hashes=hashes(solution,(".godot","__pycache__"))
            for rel in inherited_hashes:
                target=destination/"solution"/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(solution/rel,target)
            inheritance={"condition":condition,"task_id":predecessor_task,"source_hashes":inherited_hashes,
                         "context":"code plus brief handoff; no conversation or private scores"}
    meta=json.loads((public_dir(destination) / 'task.json').read_text(encoding="utf-8"))
    meta["predecessor"]=inheritance
    meta["status"]="REVIEW_ONLY" if review else "RELEASE_READY"
    dump(public_dir(destination) / 'task.json',meta)
    author_modules()
    if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
    from prompts import make_prompt
    from prompt_layout import install_types
    install_types(destination,task)
    (public_dir(destination) / 'prompt.md').write_text(make_prompt(task,destination),encoding="utf-8",newline="\n")
    refresh_inventory(destination)
    manifest=hashes(destination,(".godot","scratch"))
    dump(ROOT/"author/exports"/f"{task}_{time.time_ns()}.json",{"destination":str(destination),"review_only":review,"files":manifest,"inheritance":inheritance})
    return {"status":"REVIEW_ONLY" if review else "RELEASE_READY","path":str(destination),"file_count":len(manifest),"predecessor":inheritance["condition"]}


def validate_release(task):
    if task in L3_TASKS:return l3_call("validate_release",task)
    path=ROOT/"author/release_lock.json"
    lock=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    gates=lock.get("task_gates",{}).get(task,{})
    required=["cpu_analytic","gpu_numeric","inherited_numeric","causal_interactions","gpu_render_consistency","negative_controls",
              "legal_alternative","clean_starter","clean_reimport","file_protection","runtime_protection","os_isolation","visual_calibration","budgets_frozen"]
    blockers=[name for name in required if gates.get(name) not in [True,"NOT_APPLICABLE"]]
    return {"task":task,"status":"BLOCKED_RELEASE" if blockers else "RELEASE_READY","blockers":blockers,"gates":gates}


def l3_call(command,task=None,**kwargs):
    author_modules()
    import l3
    function=getattr(l3,command)
    return function(task,**kwargs) if task else function(**kwargs)


class ModelTools:
    """read/write are local; rendering must be supplied by an isolated host worker."""
    def __init__(self,workspace,renderer=None):
        self.root=Path(workspace).resolve()
        self.renderer=renderer
        self.calls=0
        self.render_calls=0
        self.ended=False

    def _path(self,value,write=False):
        rel=Path(value)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts or any(":" in part for part in rel.parts):raise ValueError("Expected workspace-relative path.")
        if rel.parts[0]=="public":raise ValueError("Host metadata is outside the workspace.")
        allowed={"solution","scratch"} if write else {"project.godot","fixture","assets","solution","scratch"}
        if rel.parts[0] not in allowed:
            manifest_path=public_dir(self.root) / 'scene_files.json'
            if write or not manifest_path.is_file():raise ValueError("Path is outside the visible directories.")
            source_files=json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
            name=rel.as_posix()
            if name not in source_files and not any(p.startswith(name+"/") for p in source_files):
                raise ValueError("Path is not in the visible source inventory.")
        candidate=self.root/rel
        current=self.root
        for part in rel.parts:
            current=current/part
            if current.exists() and (current.is_symlink() or (current.is_dir() and current.is_junction())):raise ValueError("Links are not allowed.")
        if not candidate.resolve().is_relative_to(self.root):raise ValueError("Path escaped the workspace.")
        return candidate

    def call(self,name,**arguments):
        if self.ended:return {"status":"ENDED"}
        self.calls+=1
        # Host counters are intentionally not included in prompts/tool responses.
        if self.calls>80 or (name=="render" and self.render_calls>=80):
            self.ended=True;return {"status":"ENDED"}
        if name=="read":
            p=self._path(arguments["path"])
            if p.is_dir():
                files=[]
                for x in sorted(p.iterdir()):
                    if x.name.startswith("."):continue
                    try:self._path(x.relative_to(self.root).as_posix())
                    except ValueError:continue
                    files.append(x.name+("/" if x.is_dir() else ""))
                return {"files":files}
            start=max(1,int(arguments.get("start_line",1)));count=min(500,int(arguments.get("line_count",200)))
            import itertools
            with p.open(encoding="utf-8") as stream:
                lines=list(itertools.islice(stream,start-1,start-1+count))
            content="".join(lines).rstrip("\r\n")
            return {"path":arguments["path"],"start_line":start,"text":content[:60000],"truncated":len(content)>60000}
        if name=="write":
            p=self._path(arguments["path"],True)
            content=arguments["content"]
            if len(content.encode("utf-8"))>2_000_000:raise ValueError("File is too large.")
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding="utf-8")
            return {"status":"WRITTEN","path":arguments["path"]}
        if name=="render":
            self.render_calls+=1
            if self.renderer is None:return {"status":"INFRA_ERROR","error":"No isolated rendering worker is attached."}
            return self.renderer(self.root,arguments)
        raise ValueError("Unknown tool")


def tool_definitions():
    return [
      {"type":"function","function":{"name":"read","description":"Read a visible UTF-8 file or list a visible directory.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start_line":{"type":"integer","minimum":1},"line_count":{"type":"integer","minimum":1,"maximum":500}},"required":["path"],"additionalProperties":False}}},
      {"type":"function","function":{"name":"write","description":"Write a UTF-8 source file in solution/ or scratch/.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"],"additionalProperties":False}}},
      {"type":"function","function":{"name":"render","description":"Render the current solution. Choose an observation camera and request a video.","parameters":{"type":"object","properties":{"frames":{"type":"integer","minimum":1,"maximum":180},"resolution":{"type":"array","items":{"type":"integer"},"minItems":2,"maxItems":2},"camera":{"type":"object","properties":{"position":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3},"look_at":{"type":"array","items":{"type":"number"},"minItems":3,"maxItems":3}},"required":["position","look_at"],"additionalProperties":False}},"additionalProperties":False}}}
    ]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["build_starter","run_reference","run_numeric","run_interactions","capture_visuals","audit_submission","package_model_task","validate_release","list_tools","inspect_source","resolve_bindings","build_l3_starter","run_integration","audit_runtime"])
    parser.add_argument("task",nargs="?",choices=TASKS+["all"],default="all")
    parser.add_argument("--submission",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--predecessor",type=Path)
    parser.add_argument("--condition",choices=["self_predecessor","gold_predecessor"],default="self_predecessor")
    parser.add_argument("--review",action="store_true")
    parser.add_argument("--inherited",action="store_true")
    parser.add_argument("--frames",type=int,default=90)
    args=parser.parse_args()
    if args.command=="list_tools":print(json.dumps(tool_definitions(),ensure_ascii=False,indent=2));return
    if args.command=="inspect_source":
        print(json.dumps(l3_call("inspect_source"),ensure_ascii=False,indent=2));return
    native_command=args.command in {"resolve_bindings","build_l3_starter","run_integration","audit_runtime"}
    for task in (L3_TASKS if native_command else TASKS) if args.task=="all" else [args.task]:
        if native_command:
            if task not in L3_TASKS:raise ValueError("This command requires an L3 task")
            result=l3_call(args.command,task,**({"frames":args.frames} if args.command=="audit_runtime" else {}))
            print(json.dumps(result,ensure_ascii=False),flush=True);continue
        if args.command=="build_starter":result=build_starter(task)
        elif args.command=="run_reference":result=run_reference(task)
        elif args.command=="run_numeric":result=run_numeric(task,args.submission,args.inherited)
        elif args.command=="run_interactions":result=run_interactions(task,args.submission)
        elif args.command=="capture_visuals":result=capture_visuals(task,args.submission,args.frames)
        elif args.command=="audit_submission":result=audit_submission(task,args.submission or ROOT/"starters"/task)
        elif args.command=="package_model_task":result=package_model_task(task,args.output,args.predecessor,args.condition,args.review)
        else:result=validate_release(task)
        print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=="__main__":main()
