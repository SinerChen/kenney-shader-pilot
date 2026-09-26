"""Native L3 task construction and explicit source/evaluation gates."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from l3_package import package_review
from l3_source import ROOT, SPEC, SOURCE, BASELINE, GODOT, TASKS, dump, digest, manifest, inspect_source, run_probe
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir, copy_public


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def definitions():
    return {x["task_id"]: x for x in read(next(SPEC.rglob("task_manifest.json")))["tasks"] if x["task_id"] in TASKS}


def resolve_bindings(task=None):
    runtime = ROOT / "author/source_audit/native_runtime/result.json"
    if not runtime.exists():run_probe()
    data=read(runtime);lock=read(ROOT/"author/forest_source_lock.json")
    resources=data["resources"];meshes=data["meshes"]
    chosen={
        "A_L3":[m for m in meshes if any(m["path"].startswith(p+"/") for p in ["Decorations-Forest/Tree_small_2","Decorations-Forest/Tree_small_1"])],
        "B_L3":[m for m in meshes if m["path"]=="Main Terrain/Plane_031"],
        "C_L3_R":[m for m in meshes if m["path"]=="Main Terrain/Plane_031"],
        "C_L3_S":[m for m in meshes if m["path"]=="Main Terrain/Plane_031"],
        "D_L3":[m for m in meshes if any(s["active_material"]=="res://Materials/River.tres" for s in m["materials"])],
        "E_L3":[m for m in meshes if any(s["active_material"]=="res://Materials/River.tres" for s in m["materials"])]}
    records=[]
    for tid in [task] if task else TASKS:
        binding=read(next(SPEC.rglob(tid+".template.json")))
        actual=chosen[tid]
        protected=["original source bytes", "geometry", "transforms", "visibility", "LOD ranges", "wind and alpha cutout", "shared materials", "camera", "lighting", "environment", "TAA", "occlusion"]
        grants=[{"node":m["path"],"surfaces":[s["surface"] for s in m["materials"]],"operation":"local surface override preserving original responsibilities"} for m in actual]
        blocked=[]
        if not actual:blocked.append("Required active source instance was not found")
        if tid=="C_L3_S":
            blocked.append("Original sky maps camera position with scales (0.1, 0.2, 0.1) but traces untransformed EYEDIR; a single camera-independent world-space density mapping is not established. Native mapping and clock calibration are required.")
        binding.update(status="BLOCKED_SOURCE" if blocked else "SOURCE_RUNTIME_ENUMERATED",source_origin="native_snapshot",verified_commit=lock["verified_commit"],
                       checkout_sha256=lock["source_file_manifest_sha256"],engine_binary_sha256=digest(GODOT),original_entry_scene="res://Main.tscn",
                       real_target_bindings=actual,authorized_runtime_bindings=grants,protected_runtime_properties=protected,
                       source_context_keep=["original non-target source code, assets, imported resources and scene hierarchy"],
                       new_target_solution_exclusions=["author references and cases", "previous model experiments", "L2 fixture stage and completed background captures"],
                       author_normalization_patches=lock["normalization_patches"],runtime_verified=bool(actual),can_export_native_task=False,
                       blockers=blocked,source_binding_scope="Loaded instances, active materials and resources verified; full integration feasibility and calibration remain separate gates.",
                       evidence_files=["author/source_audit/native_runtime/result.json","author/source_audit/native_runtime/baseline.png","author/source_audit/native_runtime/godot.log"])
        if tid.startswith("C_"):
            paths=["res://Shaders/Sky/perlworlnoise.tga","res://Shaders/Sky/weather.bmp","res://Shaders/Sky/worlnoise.bmp"]
            binding["native_resources"]={p:resources[p] for p in paths}
            binding["sky_consumer"]=data["environments"][0]
        if tid=="A_L3":
            binding["instance_transform_note"]="Original instances have fixed positive non-uniform source scaling. Additional rigid/uniform test transforms must be distinguished from this source rest transform; public domain requires calibration."
            binding["shared_material_consumers"]={s["active_material"]:sum(any(z["active_material"]==s["active_material"] for z in m["materials"]) for m in meshes) for m in actual for s in m["materials"]}
        dump(ROOT/"author/source_bindings"/(tid+".json"),binding);records.append(binding)
    lock.update(status="NORMALIZED_NATIVE_RUNTIME_ENUMERATED",normalized_run_verified=True,original_run_verified=False,
                original_run_note="Missing upstream editor generator required a recorded patch. Runtime evidence is for the normalized complete scene, not an unmodified upstream run.",
                native_node_count=data["node_count"],native_mesh_instances=len(meshes),gpu=data["gpu"],engine_version=data["engine"]["string"],renderer="Forward+ / Vulkan")
    dump(ROOT/"author/forest_source_lock.json",lock)
    return records[0] if task else records


def _public_text(text):
    text=re.sub(r"\n## (?:评价范围|评价边界)[\s\S]*$","",text)
    lines=[s for s in text.splitlines() if not any(term in s for term in ["前级20例", "前级20个", "前级 20", "分别检查前级", "预算", "正式测试编号", "G01"])]
    return "\n".join(lines).strip()


def prepare_specs():
    matrix=read(next(SPEC.rglob("l3_integration_matrix.json")))
    specs=definitions()
    for task in TASKS:
        d=specs[task]
        contract=_public_text((SPEC/d["public_contract"]).read_text(encoding="utf-8"))
        contract=contract.replace("optical_query", "optics_query")
        sys.path.insert(0,str(ROOT))
        from prompts import make_prompt
        prompt=make_prompt(task)
        path=ROOT/"tasks"/task;path.mkdir(parents=True,exist_ok=True)
        (path/"prompt.md").write_text(prompt,encoding="utf-8",newline="\n")
        (path/"contract.md").write_text(contract+"\n",encoding="utf-8")
        plan=next(x for x in matrix["tasks"] if x["task_id"]==task)
        dump(ROOT/"author/l3_plans"/(task+".json"),plan)
        for group in plan["integration_groups"]:
            dump(ROOT/"author/cases_private"/task/group["id"]/"definition.json",{**group,"source_binding":f"author/source_bindings/{task}.json","status":"DESIGNED_NOT_CALIBRATED","runtime_input":None,"oracle":None})
        dump(path/"task.json",{"task_id":task,"title":d["title"],"algorithm":d["algorithm"],"level":"L3","predecessor":d["predecessor"],"status":"DEFINED_RELEASE_BLOCKED","contract_version":"0.2","source_origin":"native_snapshot"})
    return {"status":"SPEC_ADDED","tasks":TASKS,"integration_designs":60}


def _copy_context(destination):
    files=read(ROOT/"author/source_audit/files.json")
    for rel in files:
        if rel in {".gitattributes",".gitignore"}:continue
        src=BASELINE/rel
        if not src.is_file():raise ValueError("Missing normalized source "+rel)
        dst=destination/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)


def build_l3_starter(task, predecessor=None):
    if task not in TASKS:raise ValueError(task)
    prepare_specs()
    binding=resolve_bindings(task)
    if binding["blockers"]:return {"task":task,"status":"BLOCKED_SOURCE","blockers":binding["blockers"]}
    dest=ROOT/"starters"/task
    if (public_dir(dest) / 'task.json').exists():return {"task":task,"status":"STARTER_EXISTS","path":str(dest)}
    parent_check=Path(predecessor or ROOT/"author/sealed_l2"/(task[0]+"_L2"))
    if not (parent_check/"solution/adapter.gd").is_file() or read(public_dir(parent_check) / 'task.json')["task_id"] != task[0]+"_L2":
        raise ValueError("Prepare the task's sealed L2 predecessor before creating the L3 starter")
    dest.mkdir(parents=True,exist_ok=True)
    _copy_context(dest)
    for name in ["fixture","solution","scratch"]:(dest/name).mkdir(exist_ok=True)
    public_dir(dest).mkdir(parents=True,exist_ok=True)
    predecessor_id=task[0]+"_L2"
    parent=Path(predecessor or ROOT/"author/sealed_l2"/predecessor_id).resolve()
    if read(public_dir(parent) / 'task.json')["task_id"]!=predecessor_id:raise ValueError("Wrong L2 predecessor")
    before=manifest(parent/"solution")
    certificate=read(ROOT/"author/sealed_l2"/(predecessor_id+".json"))
    if predecessor is None and (certificate["status"] != "CHAIN_L2_VALIDATED" or before != certificate["solution_hashes"]):
        raise ValueError("Default L2 predecessor must pass its recorded regressions")
    for rel in before:
        if rel.endswith(".uid"):continue
        target=dest/"solution"/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(parent/"solution"/rel,target)
    # Preserve predecessor neutral inputs, without copying its solved stage or captures.
    shutil.copytree(parent/"assets",dest/"assets",dirs_exist_ok=True)
    for source,target in [("l3_adapter_base.gd","adapter_base.gd"),("l3_scene_access.gd","scene_access.gd"),("l3_entry.gd","entry.gd"),("l3_native_runner.gd","native_runner.gd")]:
        shutil.copy2(ROOT/"templates"/source,dest/"fixture"/target)
    (dest/"fixture/entry.tscn").write_text('[gd_scene load_steps=2 format=3]\n[ext_resource type="Script" path="res://fixture/entry.gd" id="1"]\n[node name="ForestTask" type="Node3D"]\nscript = ExtResource("1")\n',encoding="utf-8")
    project=dest/"project.godot"
    project.write_text(project.read_text(encoding="utf-8").replace('run/main_scene="res://Main.tscn"','run/main_scene="res://fixture/entry.tscn"'),encoding="utf-8")
    src=dest/"solution/adapter.gd";adapter=src.read_text(encoding="utf-8")
    if "func bind_scene(" not in adapter:
        adapter+='\nfunc bind_scene(_scene_access: Node, _task_config: Dictionary) -> Dictionary:\n\treturn {"status":"UNIMPLEMENTED_BINDING"}\n\nfunc detach_scene() -> Dictionary:\n\treturn {"status":"UNIMPLEMENTED_BINDING"}\n'
    src.write_text(adapter,encoding="utf-8")
    d=definitions()[task]
    permissions={"default_file_access":"readonly","writable_paths":["solution/","scratch/"],"material_bindings":binding["authorized_runtime_bindings"],
                 "effect_root":"EffectRoot","input_slots":["front_background","water_background"] if task=="E_L3" else [],"protected_properties":binding["protected_runtime_properties"]}
    dump(public_dir(dest) / 'permissions.json',permissions)
    demo=read(public_dir(parent) / 'demo.json')
    dump(public_dir(dest) / 'development.json',{"core_config":demo["config"],"events":[],"dt":1/15,"status":"CORE_INPUT_FIXED_SCENE_DOMAIN_PENDING_CALIBRATION"})
    (public_dir(dest) / 'predecessor_contract.md').write_text((ROOT/"tasks"/predecessor_id/"prompt.md").read_text(encoding="utf-8"),encoding="utf-8")
    shutil.copytree(public_dir(parent) / 'sample_inputs',public_dir(dest) / 'sample_inputs')
    shutil.copy2(ROOT/"tasks"/task/"prompt.md",public_dir(dest) / 'prompt.md')
    shutil.copy2(ROOT/"tasks"/task/"contract.md",public_dir(dest) / 'contract.md')
    (public_dir(dest) / 'api.md').write_text("# L3 接口\n\n保留前级 reset(config)、advance(dt, events)、query(name, payload)、get_outputs()。新增 bind_scene(scene_access, task_config) 与 detach_scene()。空接入返回 UNIMPLEMENTED_BINDING。\n\nscene_access 提供 source_node(path)、bind_material(path, surface, material)、add_effect(node)、camera()、input_texture(name)、publish_input(name, texture) 和 detach_bindings()。源节点和资源用于读取；允许修改的表面由 permissions.json 限定。输入槽不生成背景捕获。\n\n原 L2 舞台及其节点不再存在，不能调用继承的 mount() 来假定它们存在。前级核心仍在 solution 中。外层 io_schema.json 描述输入输出类型；场景接入的配置尚未校准时不能正式投放。\n",encoding="utf-8")
    meta={"task_id":task,"title":d["title"],"algorithm":d["algorithm"],"level":"L3","contract_version":"0.2","core_contract_version":"0.1",
          "original_entry_scene":"res://Main.tscn","entry_scene":"res://fixture/entry.tscn","source_origin":"native_snapshot","source_commit":binding["verified_commit"],
          "source_native_binding_enumerated":True,"source_native_feasibility_verified":False,"engine_version":"4.6.1","renderer":"Forward+",
          "predecessor":{"task_id":predecessor_id,"condition":"gold_predecessor_review","original_solution_hashes":before,"migrated_solution_hashes":manifest(dest/"solution")},
          "readonly_paths":["project.godot","fixture/",*sorted({Path(p).parts[0]+"/" for p in read(ROOT/"author/source_audit/files.json") if len(Path(p).parts)>1})],
          "writable_paths":["solution/","scratch/"],"authorized_runtime_bindings":binding["authorized_runtime_bindings"],"integration_config_status":"PENDING_CALIBRATION",
          "status":"REVIEW_ONLY_BINDING_UNIMPLEMENTED"}
    dump(public_dir(dest) / 'task.json',meta)
    source_files={p:digest(dest/p) for p in read(ROOT/"author/source_audit/files.json") if (dest/p).is_file()}
    dump(public_dir(dest) / 'scene_files.json',{"files":source_files,"default":"readonly"})
    dump(public_dir(dest) / 'source_context.json',{"source_origin":"native_snapshot","commit":binding["verified_commit"],"files":[{"path":p,"role":"source_context"} for p in source_files],"normalization":binding["author_normalization_patches"],"excluded":["author/",".git/","previous runs","L2 capture fixture"]})
    dump(public_dir(dest) / 'scene_inventory.json',{"task_id":task,"original_entry_scene":"res://Main.tscn","target_bindings":binding["real_target_bindings"],"source_nodes_count":read(ROOT/"author/source_audit/native_runtime/result.json")["node_count"],"source_file_manifest":"scene_files.json"})
    if task=="A_L3":dump(public_dir(dest) / 'targets.json',{"objects":[{"object_id":"tree_1","root":"Decorations-Forest/Tree_small_2"},{"object_id":"tree_2","root":"Decorations-Forest/Tree_small_1"}],"anchor_inputs":"PENDING_STABLE_BRANCH_CALIBRATION"})
    if task.startswith("C_"):dump(public_dir(dest) / 'resource_inputs.json',{"U":{"path":"res://Shaders/Sky/perlworlnoise.tga","class":"CompressedTexture3D","size":[128,128,128],"channel":0},"V":{"path":"res://Shaders/Sky/weather.bmp","class":"CompressedTexture2D","size":[512,512],"channel":0},"addressing":"repeat","filter":"linear","lod":0,"data_space":"linear numerical samples","normalization":"8-bit source components / 255"})
    if task=="B_L3":dump(public_dir(dest) / 'terrain_task.json',{"target":"Main Terrain/Plane_031","material":"res://Materials/Terrain 1.tres","shader":"res://Shaders/Blend8 splat.gdshader","semantic_layer_labels":None,"tau_allow":None,"chart":None,"status":"DOMAIN_NOT_FROZEN"})
    if task in ["D_L3","E_L3"]:dump(public_dir(dest) / 'river_domain.json',{"target":"Main Terrain/BezierCurve_001","material":"res://Materials/River.tres","reference_chart":None,"status":"DOMAIN_NOT_FROZEN","physical_velocity_source":"task input, not the original UV animation"})
    public_inputs=ROOT/"tasks"/task/"scene_inputs"
    if public_inputs.exists():
        shutil.copytree(public_inputs,public_dir(dest),dirs_exist_ok=True)
        meta["input_files"]=[p.name for p in sorted(public_inputs.glob("*.json"))]
        dump(public_dir(dest) / 'task.json',meta)
    neutral=ROOT/"tasks"/task/"inputs"
    if neutral.exists():shutil.copytree(neutral,dest/"assets/task_inputs"/task,dirs_exist_ok=True)
    sys.path.insert(0,str(ROOT))
    from prompt_layout import install_types
    from prompts import make_prompt
    install_types(dest,task)
    prompt=make_prompt(task,dest)
    (public_dir(dest) / 'prompt.md').write_text(prompt,encoding="utf-8",newline="\n")
    (ROOT/"tasks"/task/"prompt.md").write_text(prompt,encoding="utf-8",newline="\n")
    dump(ROOT/"author/baseline"/(task+".json"),{k:v for k,v in manifest(dest).items() if not k.startswith(("solution/","scratch/"))})
    dump(ROOT/"author/l3_migrations"/(task+".json"),{"predecessor":str(parent),"condition":"gold_predecessor_review","before":before,"after":manifest(dest/"solution"),"patch":"Append empty bind/detach; preserve core and neutral assets; remove L2 fixture dependencies from scene entry.","scene_capture_fixture_inherited":False})
    return {"task":task,"status":meta["status"],"path":str(dest),"files":len(manifest(dest))}


def audit_runtime(task,frames=30,camera=None):
    if not isinstance(frames,int) or not 1 <= frames <= 180:raise ValueError("frames must be in [1,180]")
    if camera is not None:
        import math
        if set(camera) != {"position","look_at"} or any(len(camera[k]) != 3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in camera[k]) for k in camera):
            raise ValueError("camera needs finite position and look_at vectors")
        if camera["position"] == camera["look_at"]:raise ValueError("Camera direction cannot be zero")
    project=ROOT/"starters"/task
    if not project.exists():return {"task":task,"status":"BLOCKED_SOURCE"}
    migration=read(ROOT/"author/l3_migrations"/(task+".json"))
    current={k:v for k,v in manifest(project/"solution").items() if not k.endswith(".uid")}
    expected={k:v for k,v in migration["after"].items() if not k.endswith(".uid")}
    if current!=expected:raise RuntimeError("This command only executes the sealed review starter; candidate execution needs an isolated worker.")
    out=ROOT/"author/reports/l3"/task/("starter_camera" if camera is not None else "starter")
    out.mkdir(parents=True,exist_ok=True)
    # Import and execute a fresh copy, never mutate the sealed model starter.
    run_project=out/("project_"+str(time.time_ns()))
    shutil.copytree(project,run_project,ignore=shutil.ignore_patterns(".godot","*.uid"))
    copy_public(project,run_project)
    project=run_project
    env=dict(os.environ);env["APPDATA"]=str(ROOT/"runs/l3_appdata")
    imported=subprocess.run([str(GODOT),"--headless","--editor","--path",str(project),"--import"],capture_output=True,env=env,timeout=600,creationflags=0x08000000)
    (out/"import.log").write_bytes(imported.stdout+imported.stderr)
    if imported.returncode:raise RuntimeError("Starter import failed")
    dump(out/"request.json",{"frames":frames,"camera":camera})
    args=[str(GODOT),"--path",str(project),"--rendering-method","forward_plus","--audio-driver","Dummy","--position","-10000,-10000","--resolution","640x360","--script","res://fixture/native_runner.gd","--",str(out/"request.json"),str(out)]
    start=time.monotonic();run=subprocess.run(args,capture_output=True,env=env,timeout=300,creationflags=0x08000000)
    (out/"godot.log").write_bytes(run.stdout+run.stderr)
    if run.returncode or not (out/"result.json").exists():raise RuntimeError("Starter runtime failed: "+str(out))
    result=read(out/"result.json")
    if result["binding"].get("status") != "UNIMPLEMENTED_BINDING":raise RuntimeError("Sealed blank binding changed")
    if not result["source_runtime_unchanged"] or not result["detach_restored"]:raise RuntimeError("Blank starter modified protected source")
    if "ERROR:" in (imported.stdout+imported.stderr+run.stdout+run.stderr).decode("utf-8",errors="replace"):
        raise RuntimeError("Godot reported an error; inspect import.log and godot.log")
    sys.path.insert(0,str(ROOT));from main import encode_video
    video=encode_video(out,15,frames)
    result.update(task=task,video=video.relative_to(ROOT).as_posix() if video else None,seconds=time.monotonic()-start,clean_import_exit=imported.returncode)
    dump(out/"report.json",result)
    return result


def run_integration(task):
    plan=read(ROOT/"author/l3_plans"/(task+".json"))
    binding=read(ROOT/"author/source_bindings"/(task+".json"))
    report={"task":task,"status":"BLOCKED_SOURCE" if binding["blockers"] else "NOT_RUN","integration_pass":None,"integration_total":10,
            "executed_groups":0,"groups":[{"id":g["id"],"status":"NOT_RUN","reason":"Native integration reference, concrete source-domain cases, independent oracle and tolerances have not been calibrated."} for g in plan["integration_groups"]],
            "source_blockers":binding["blockers"],"scope":"The imported 10-group design is not an executable positive integration judge. Unexecuted groups do not count as model failures."}
    dump(ROOT/"author/reports/l3"/task/"integration.json",report)
    return report


def validate_release(task):
    binding_path=ROOT/"author/source_bindings"/(task+".json")
    binding=read(binding_path) if binding_path.exists() else {}
    return {"task":task,"status":"BLOCKED_RELEASE","source_status":binding.get("status","SOURCE_UNVERIFIED"),"blockers":
            binding.get("blockers",[])+["source_domain_and_semantics_calibration","native_positive_integration_reference","60_group_private_oracles_and_controls",
                                      "candidate_core_and_coupling_regressions","runtime_protection_calibration","os_isolation","visual_calibration","budgets_frozen","asset_license_closure"]}


if __name__=="__main__":
    command=sys.argv[1] if len(sys.argv)>1 else "prepare_specs"
    tasks=TASKS if len(sys.argv)<3 or sys.argv[2]=="all" else [sys.argv[2]]
    if command=="prepare_specs":print(prepare_specs())
    else:
        for task in tasks:
            result=globals()[command](task)
            print(task,result.get("status"),result.get("binding"),flush=True)
