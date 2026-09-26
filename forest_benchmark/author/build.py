from pathlib import Path
import copy
import hashlib
import json
import re
import shutil
import numpy as np
from PIL import Image
from model import defaults,TASK_OPERATIONS,OPERATIONS,fields
from reference_cpu import evaluate
from numeric_backend import ROOT,GODOT,write_json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir

TITLES={"A":"灼烧与余烬","B":"脚印与湿润","C":"云影与体积光","D":"流水与泡沫","E":"折射与涟漪"}
TARGETS={"A_L1":["TargetMesh"],"A_L2":["TargetMesh"],"B_L1":["GroundPatch"],"B_L2":["GroundPatch"],
         "C_L1":["GroundReceiver"],"C_L2":["GroundReceiver"],"D_L1":["WaterPatch"],"D_L2":["WaterPatch"],
         "E_L1":["TransparentTarget"],"E_L2":["FrontTarget","RearWater"]}
CONFIG_KEYS={
 "A":["P","points","origin_ref","R0","speed","noise_amplitude","base_frequency","octaves","gain","lacunarity","width","enabled","frequency","epsilon","drift","offsets","up_speed","curl_strength","lifetime","particles","emit_threshold","enable_emission","anchors","instance_transform","burn_visible","embers_visible","wood_color","char_color","ember_color"],
 "B":["depth","mask","mask_size","contacts","pom_rays","d_max","wetness","source","diffusion","lambda0","beta","dry_color","wet_color","dry_roughness","wet_roughness"],
 "C":["points","cloud_world_to_local","cloud_min","cloud_max","density_size","density","cloud_sigma","cloud_steps","light_dir","light_rgb","fog_min","fog_max","fog_density","fog_scatter","fog_absorb","g","view_steps","view_rays","ambient_color","direct_color"],
 "D":["uvs","period","phase","tiling","flow","texture_size","color_texture","normal_texture","normal_encoded","foam","sources","decay"],
 "E":["eta_i","eta_t","ell","sigma_a","optical_rays","view_projection","reflection_color","fallback_color","height","height_prev","force","wave_speed","gamma","front_visible","rear_visible","rear_ell","texture_size","color_texture","sources","decay","flow"],
}


def neutral_stage(task):
    chain=task[0]
    base='''[gd_scene load_steps=12 format=3]
[sub_resource type="Environment" id="Env"]
background_mode = 1
background_color = Color(0.075, 0.11, 0.15, 1)
ambient_light_source = 3
ambient_light_color = Color(0.65, 0.72, 0.8, 1)
ambient_light_energy = 0.5
tonemap_mode = 0
tonemap_exposure = 1.0
[sub_resource type="StandardMaterial3D" id="ControlMat"]
albedo_color = Color(0.48, 0.25, 0.11, 1)
roughness = 0.7
[sub_resource type="StandardMaterial3D" id="TargetMat"]
albedo_color = Color(0.3, 0.36, 0.29, 1)
roughness = 0.65
[sub_resource type="StandardMaterial3D" id="BackdropMat"]
albedo_color = Color(0.18, 0.24, 0.2, 1)
roughness = 1.0
[sub_resource type="BoxMesh" id="ControlMesh"]
material = SubResource("ControlMat")
size = Vector3(0.5, 0.8, 0.5)
[sub_resource type="PlaneMesh" id="GroundMesh"]
material = SubResource("TargetMat")
size = Vector2(4, 3)
subdivide_width = 1
subdivide_depth = 1
[sub_resource type="QuadMesh" id="WoodMesh"]
material = SubResource("TargetMat")
size = Vector2(1.6, 2.4)
[sub_resource type="QuadMesh" id="FrontMesh"]
material = SubResource("TargetMat")
size = Vector2(1.6, 1.3)
[sub_resource type="PlaneMesh" id="FloorMesh"]
material = SubResource("BackdropMat")
size = Vector2(6, 5)
[sub_resource type="CylinderMesh" id="MarkerMesh"]
material = SubResource("ControlMat")
top_radius = 0.12
bottom_radius = 0.12
height = 0.5
[sub_resource type="StandardMaterial3D" id="MarkMat"]
albedo_color = Color(0.85, 0.62, 0.14, 1)
roughness = 0.85
[node name="Stage" type="Node3D"]
[node name="Environment" type="WorldEnvironment" parent="."]
environment = SubResource("Env")
[node name="CameraRig" type="Node3D" parent="."]
[node name="Camera3D" type="Camera3D" parent="CameraRig"]
position = Vector3(3.5, 3.1, 5)
rotation_degrees = Vector3(-22, 34, 0)
current = true
fov = 45.0
near = 0.05
far = 50.0
cull_mask = 7
[node name="Sun" type="DirectionalLight3D" parent="."]
rotation_degrees = Vector3(-55, -20, 0)
light_energy = 1.4
shadow_enabled = true
[node name="ProtectedControl" type="MeshInstance3D" parent="."]
position = Vector3(-2.35, 0.4, 0)
mesh = SubResource("ControlMesh")
[node name="Floor" type="MeshInstance3D" parent="."]
position = Vector3(0, -0.03, 0)
mesh = SubResource("FloorMesh")
[node name="ReferenceMarkers" type="Node3D" parent="."]
'''
    for idx,(x,z) in enumerate([(-1.8,-1.3),(1.8,-1.3),(-1.8,1.3),(1.8,1.3)]):
        base+=f'[node name="Marker{idx}" type="MeshInstance3D" parent="ReferenceMarkers"]\nposition = Vector3({x}, 0.25, {z})\nmesh = SubResource("MarkerMesh")\n'
    for target in TARGETS[task]:
        mesh="WoodMesh" if chain=="A" else "FrontMesh" if target in ("TransparentTarget","FrontTarget") else "GroundMesh"
        position="0, 1.2, 0" if chain=="A" else "0, 1.2, 1.0" if mesh=="FrontMesh" else "0, 0, 0"
        layer=4 if mesh=="FrontMesh" else 2 if target=="RearWater" else 1
        base+=f'[node name="{target}" type="MeshInstance3D" parent="."]\nposition = Vector3({position})\nmesh = SubResource("{mesh}")\nlayers = {layer}\n'
    if chain=="E":
        base=base.replace("layers = 4\n", "layers = 4\ncast_shadow = 0\n")
    if chain=="D" and task.endswith("L2"):
        base+='[node name="ContactMarker" type="MeshInstance3D" parent="."]\nposition = Vector3(-0.5, 0.25, 0)\nmesh = SubResource("MarkerMesh")\n'
    if chain=="C":
        base+='[node name="ProtectedAmbientPatch" type="MeshInstance3D" parent="."]\nposition = Vector3(2.4, 0.4, 0)\nmesh = SubResource("ControlMesh")\n'
    if chain=="E":
        base=base.replace('[gd_scene load_steps=12 format=3]','[gd_scene load_steps=14 format=3]\n[ext_resource type="Shader" path="res://fixture/background.gdshader" id="BackgroundShader"]')
        base=base.replace('[sub_resource type="PlaneMesh" id="FloorMesh"]\nmaterial = SubResource("BackdropMat")',
                          '[sub_resource type="ShaderMaterial" id="CheckerMat"]\nshader = ExtResource("BackgroundShader")\n[sub_resource type="PlaneMesh" id="FloorMesh"]\nmaterial = SubResource("CheckerMat")')
        # Colored fixed geometry is visible both through and outside the front target.
        for i in range(7):
            base+=f'[node name="ColorMark{i}" type="MeshInstance3D" parent="ReferenceMarkers"]\nposition = Vector3({(i-3)*.5}, 0.06, -0.5)\nscale = Vector3(0.65, 0.12, 0.65)\nmesh = SubResource("ControlMesh")\nmaterial_override = SubResource("MarkMat")\n'
    return base


def demo_for(task):
    p=defaults(202);p["task_id"]=task;p["time"]=0.
    events=[]
    if task[0]=="A":
        p.update(origin_ref=[-.55,-.75,0.],R0=.03,speed=.35,width=.15,noise_amplitude=.23,
                 anchors=[[float(x),float(y),0.] for y in np.linspace(-1.2,1.2,14) for x in np.linspace(-.8,.8,10)],
                 lifetime=2.,emit_threshold=.6)
        transform=np.eye(4);transform[1,3]=1.2;p["instance_transform"]=transform.reshape(-1,order="F").tolist()
    if task[0]=="B":
        p["depth"]=[0.]*48;p["wetness"]=[0.]*48
        for tick,x,z,angle in [(1,-.8,-.4,.2),(18,-.2,.4,-.2),(35,.55,-.15,.15)]:
            contact=[tick,x,z,angle,.75,1.1,.055]
            events.append({"tick":tick,"event":{"type":"contact","event_id":f"c{tick}","contact":contact}})
            if task.endswith("L2"):events.append({"tick":tick+5,"event":{"type":"water","event_id":f"w{tick}","contact":contact,"amount":.9}})
    if task[0]=="C":
        events=[{"tick":t,"event":{"type":"set","values":{"cloud_world_to_local":[1,0,0,0,0,1,0,0,0,0,1,0,float(-t*.015),0,0,1]}}} for t in range(1,90)]
    if task[0]=="D":
        p["foam"]=[0.]*48
        events=[{"tick":55,"event":{"type":"set","values":{"sources":[]}}}]
    if task[0]=="E":
        p["height"]=[0.]*48;p["height_prev"]=[0.]*48
        p.update(ell=.32,rear_ell=.35,sigma_a=[.25,.06,.03],gamma=.35)
        events=[{"tick":t,"event":{"type":"wave","event_id":f"r{t}","source":[x,z,.75,8.]}}
                for t,x,z in [(1,-.65,-.3),(23,.65,.4),(45,-.2,.6)]]
    if task[0] in "BDE":
        nx,nz=48,36
        j,i=np.mgrid[:nz,:nx]
        p["grid_size"]=[nx,nz]
        for field in ["depth","wetness","source","foam","height","height_prev","force"]:
            p[field]=[0.]*(nx*nz)
        p["flow"]=np.stack((.45+.13*np.sin(j/nz*6),.16*np.cos(i/nx*5)),axis=-1).reshape(-1,2).tolist()
        p.update(diffusion=.008,lambda0=.2,wave_speed=.65)
        if task[0]=="D":
            p.update(sources=[[-.5,0.,.65,2.]],decay=.3)
        if task[0]=="E":
            for event in events:
                event["event"]["source"][3]=.7
    if task[0]=="C":
        zz,yy,xx=np.mgrid[:12,:8,:16]
        rho=np.exp(-((xx-5.)**2/10+(zz-4.)**2/8+(yy-3.)**2/8))
        rho+=.9*np.exp(-((xx-12.)**2/8+(zz-9.)**2/7+(yy-5.)**2/6))
        p.update(density_size=[16,8,12],density=rho.ravel().tolist(),cloud_sigma=2.5,
                 fog_density=.55,g=-.35,light_rgb=[1.25,1.1,.9])
    shared=["task_id","time","t0","dt","grid_size","domain_min","domain_size"]
    config={k:v for k,v in p.items() if k in shared+CONFIG_KEYS[task[0]]}
    return {"config":config,"events":events,"dt":1/15}


def build_starter(task):
    source=ROOT/"author/specification"
    manifest=json.loads(next(source.glob("04_*/task_manifest.json")).read_text(encoding="utf-8"))
    spec=next(row for row in manifest["tasks"] if row["task_id"]==task)
    path=ROOT/"starters"/task
    for folder in ["fixture","assets","solution","scratch"]: (path/folder).mkdir(parents=True,exist_ok=True)
    (public_dir(path)/"sample_inputs").mkdir(parents=True,exist_ok=True)
    project='config_version=5\n[application]\nconfig/name="Forest '+task+'"\nrun/main_scene="res://fixture/entry.tscn"\n[display]\nwindow/size/viewport_width=640\nwindow/size/viewport_height=360\n[rendering]\nrenderer/rendering_method="forward_plus"\n'
    (path/"project.godot").write_text(project,encoding="utf-8")
    (path/"fixture/base_stage.tscn").write_text(neutral_stage(task),encoding="utf-8")
    if task[0]=="E":
        (path/"fixture/background.gdshader").write_text('shader_type spatial;\nvoid fragment(){float tile=mod(floor(UV.x*24.)+floor(UV.y*20.),2.);ALBEDO=mix(vec3(.06,.16,.22),vec3(.7,.67,.49),tile);ROUGHNESS=1.;}\n',encoding="utf-8")

    for name in ["bridge.gd","adapter_base.gd","runner.gd","visual_runner.gd","evidence.gd"]:
        shutil.copy2(ROOT/"templates"/name,path/"fixture"/name)
    (path/"fixture/entry.tscn").write_text('[gd_scene load_steps=4 format=3]\n[ext_resource type="Script" path="res://fixture/bridge.gd" id="1"]\n[ext_resource type="PackedScene" path="res://fixture/base_stage.tscn" id="2"]\n[ext_resource type="PackedScene" path="res://solution/effect.tscn" id="3"]\n[node name="Fixture" type="Node3D"]\nscript = ExtResource("1")\n[node name="Stage" parent="." instance=ExtResource("2")]\n[node name="EffectRoot" parent="." instance=ExtResource("3")]\n',encoding="utf-8")
    # Never overwrite an existing candidate while rebuilding immutable fixtures.
    if not (path/"solution/adapter.gd").exists():
        (path/"solution/adapter.gd").write_text('extends "res://fixture/adapter_base.gd"\n# Implement this task in solution/. The base class reports NOT_IMPLEMENTED.\n',encoding="utf-8")
    if not (path/"solution/effect.tscn").exists():
        (path/"solution/effect.tscn").write_text('[gd_scene format=3]\n[node name="EffectRoot" type="Node3D"]\n',encoding="utf-8")
    demo=demo_for(task);write_json(public_dir(path) / 'demo.json',demo)
    common=next(source.glob("03_*/*/00_*.md")).read_text(encoding="utf-8")
    own=(source/spec["public_contract"]).read_text(encoding="utf-8")
    previous=(source/spec["public_contract"]).with_name(spec["predecessor"]+".md").read_text(encoding="utf-8") if spec["predecessor"] else ""
    contract=common+"\n"+previous+"\n"+own
    contract=contract.replace("运行环境和预算以已冻结的", "运行环境以").replace("与预算","").replace("和预算","")
    (public_dir(path) / 'contract.md').write_text(contract,encoding="utf-8")
    import sys
    sys.path.insert(0,str(ROOT))
    from prompts import make_prompt
    prompt=make_prompt(task)
    taskdir=ROOT/"tasks"/task;taskdir.mkdir(parents=True,exist_ok=True)
    (taskdir/"prompt.md").write_text(prompt,encoding="utf-8",newline="\n")
    (public_dir(path) / 'prompt.md').write_text(prompt,encoding="utf-8",newline="\n")
    parent=spec["predecessor"]
    names=(TASK_OPERATIONS[parent] if parent else [])+TASK_OPERATIONS[task]
    public={
        "task_id":task,"title":spec["title"],"algorithm":spec["algorithm"],"contract_version":"0.1",
        "contract_sha256":hashlib.sha256(contract.encode()).hexdigest(),"engine_version":"4.6.1.stable.official.14d19694e",
        "renderer":"Forward+","entry_scene":"res://fixture/entry.tscn","adapter":"res://solution/adapter.gd",
        "readonly_paths":["project.godot","fixture/","assets/"],"writable_paths":["solution/","scratch/"],
        "authorized_runtime_bindings":TARGETS[task],"protected_runtime_properties":["geometry","node transforms","visibility","camera","light","environment","non-target materials"],
        "predecessor":{"task_id":parent,"condition":"NOT_INJECTED" if parent else "none"},
        "queries":{name:OPERATIONS[name] for name in names},"numeric_tolerances":{"atol":.0002,"rtol":.0002,"booleans":"exact","status":"PROVISIONAL_PENDING_CONTROLS"},
        "input_limits":{"grid_axis":[2,128],"cloud_steps":[1,128],"view_steps":[1,128],"octaves":[1,8],"time_abs_max":120.,"finite_values_only":True},
        "capture_settings":{"width":640,"height":360,"fps":15,"duration_s":6,"author_camera":{"position":[3.5,3.1,5.],"look_at":[0.,.65,0.]},
                            "debug_camera":"freely chosen through render","simulation_dt":1/15,"exposure":1.,"tonemapper":"linear","aa":"disabled"},
        "status":"STARTER_BUILT_RELEASE_PENDING",
    }
    write_json(public_dir(path) / 'task.json',public)
    p=defaults(202);p.update(demo["config"])
    # Development example is separate from all private seeds and inputs.
    p["time"]=.37
    samples=[]
    for name in TASK_OPERATIONS[task]:
        samples.append({"query":name,"payload":demo["config"] | {"time":.37},
                        "required_fields":fields(name,p),"expected_shape":list(evaluate(name,p).shape),
                        "expected":evaluate(name,p).tolist()})
    write_json(ROOT/"author/development_samples"/task/"sample.json",{"kind":"public_development_sample","samples":samples})
    api="""# 公共 API

adapter.gd 继承 fixture/adapter_base.gd。reset(config) 清空状态并从 t0 开始；advance(dt, events) 在旧时刻处理事件、更新到下一时刻；query(name, payload) 的 payload 覆盖本轮配置，可显式传 time，不改变持续状态。query('state', {}) 或 get_outputs() 读取当前状态。mount(bridge) 安装材质，update_display() 更新显示。

配置字段与固定例子见 demo.json 和 sample_inputs/sample.json。二维字段按行展开，i=X 最快，j=Z 次之。grid_size=[Nx,Nz]，domain_min=[xmin,zmin]，domain_size=[Lx,Lz]。三维密度布局为 [Nz,Ny,Nx] 的展平数组。view_projection 与 cloud_world_to_local 是作用于列向量的列主序 4×4 矩阵；clip.w>0、clip.z/clip.w∈[0,1]，UV=(ndc.xy*(1,-1)+1)/2。

成功的 query 返回 Dictionary：status='OK'、device=真实 RenderingDevice、buffer=同步后的 storage buffer RID、shape=[行数,通道数]、fields=按序字段名。桥从资源读取 little-endian float32，不把普通数组当 GPU 证据。也接受 texture=真实 float32 Texture2D（RF/RGF/RGBF/RGBAF）及同样 shape/fields。布尔字段数值为 0 或 1；空粒子数组返回 status='EMPTY'、shape=[0,6]。未实现须返回 NOT_IMPLEMENTED。get_outputs 可组合资源字典与事件元数据。

纯函数查询：

- burn_query / curl_query / cloud_query：points=[[x,y,z],…]。
- particle_step：particles=[[x,y,z,age],…]，输出每行 position3、age、active、cooling。
- stamp_query：depth、contacts=[[event_id,cx,cz,angle,size_x,size_z,increment],…]；mask 为线性遮罩，mask_size=[宽,高]。
- pom_query：pom_rays=[[x,z,Vx,Vy,Vz],…] 与 depth。
- wet_step：wetness、depth、source；diffusion 对应 D。
- fog_query：view_rays=[[ox,oy,oz,dx,dy,dz,opaque_distance],…]；cloud_steps=N、view_steps=Nv。五个固定输出通道后接 Nv 个 T_cloud_at_samples，再接 Nv 个 T_fog_light。
- flow_query：uvs、flow（每单元 [vx,vz]）、period=P、phase=phi、tiling=K、texture_size、color_texture、normal_texture、normal_encoded。
- foam_step：foam、flow、sources=[[x,z,radius,rate],…]。
- optics_query：optical_rays=[[Ix,Iy,Iz,Nx,Ny,Nz,x,y,z],…]，eta_i/eta_t、ell、sigma_a、view_projection、color_texture、reflection_color、fallback_color。
- wave_step / wave_normal_query：height、height_prev、force，wave_speed=c、gamma；法线查询使用 height。

事件仅有：contact {event_id,contact}；water {event_id,contact,amount}；wave {event_id,source}；set {values}。type 字段指定类型；set 只改变给定算法参数，不自动 reset。wave 的空间核与泡沫源相同，rate 表示本 tick 加速度。重复 event_id 只处理一次。水源与外力的持续场由 source/force 输入。发射锚点顺序即 anchor_id，birth_log、particle_ids、emitted 描述真实记录。

资源接入：bridge.bind_material(target, material) 仅允许 task.json 列出的目标；bridge.add_effect(node) 将新效果放到 EffectRoot。E 题 bridge.background('rear') 给不透明输入，bridge.background('front') 给当前后景输入；后景捕获剔除前景层。绑定节点、纹理和相机由桥组织。不得改 protected 节点或以修改基础场景实现目标。

编辑器启动呈现中性场景和未实现状态。只有完成 mount/reset 后才开始固定 dt 示例推进。调试 render 可选择相机，但不改变正式采集配置。
"""
    (public_dir(path) / 'api.md').write_text(api,encoding="utf-8")
    # Neutral input files, never target state sequences or precomputed solutions.
    a=path/"assets"
    asset_data={}
    if task[0]=="A":
        write_json(a/"noise_permutation.json",{"P":p["P"],"G":"ordered gradient table in contract.md"})
        np.array(p["anchors"],dtype="<f4").tofile(a/"emitter_anchors.bin")
        image=np.zeros((64,64,3),dtype=np.uint8)
        yy,xx=np.mgrid[:64,:64];grain=.8+.2*np.sin(xx*.7+.25*np.sin(yy*.3))
        image[:]=np.uint8(grain[:,:,None]*np.array([133,75,36]))
        Image.fromarray(image).save(a/"wood_base.png")
    if task[0]=="B":
        np.array(p["mask"],dtype="<f4").tofile(a/"sole_mask.f32")
        Image.fromarray(np.uint8(np.array(p["mask"]).reshape(8,6)*255)).save(a/"sole_mask.png")
    if task[0]=="C":np.array(p["density"],dtype="<f4").tofile(a/"cloud_density.f32")
    if task[0]=="D":
        np.array(p["flow"],dtype="<f4").tofile(a/"flow_field.bin")
        np.array(p["color_texture"],dtype="<f4").tofile(a/"base_water_color.f32")
        np.array(p["normal_texture"],dtype="<f4").tofile(a/"base_water_normal.f32")
    if task[0]=="E":
        np.full((8,8),p["ell"],dtype="<f4").tofile(a/"front_path_length.f32")
        np.full((8,8),.35,dtype="<f4").tofile(a/"rear_path_length.f32")
        write_json(a/"environment.json",{"reflection_color":p["reflection_color"],"fallback_color":p["fallback_color"]})
    for file in sorted(a.iterdir()):
        if file.suffix in [".import",".uid"]:continue
        asset_data[file.name]={"path":"assets/"+file.name,"sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"source":"generated_neutral_input","license":"CC0-1.0","status":"CREATED","bytes":file.stat().st_size}
    write_json(a/"metadata.json",{"assets":asset_data,"float_format":"little-endian float32, linear","not_target_solutions":True,
                                "grid_size":p["grid_size"],"density_size":p["density_size"],"mask_size":p["mask_size"],"texture_size":p["texture_size"]})
    from prompt_layout import install_types
    install_types(path,task)
    if not (public_dir(path) / 'scene_inventory.json').exists():write_json(public_dir(path) / 'scene_inventory.json',{})
    prompt=make_prompt(task,path)
    (taskdir/"prompt.md").write_text(prompt,encoding="utf-8",newline="\n")
    (public_dir(path) / 'prompt.md').write_text(prompt,encoding="utf-8",newline="\n")
    inventory=[]
    for file in sorted(path.rglob("*")):
        if file.is_file() and file.relative_to(path).parts[0] in ["fixture","assets"] and file.name!="scene_inventory.json":
            inventory.append({"path":file.relative_to(path).as_posix(),"sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"type":file.suffix,"source":"generated" if file.suffix!=".md" else "provided_specification",
                              "license":"project-authored","status":"CREATED","access":"read_only"})
    write_json(public_dir(path) / 'scene_inventory.json',{"task_id":task,"files":inventory,"source_scene":"constructed_fixture","target_nodes":TARGETS[task]})
    return path


if __name__=="__main__":
    for task in TASK_OPERATIONS:
        print(task,build_starter(task),flush=True)
