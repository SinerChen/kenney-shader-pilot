from pathlib import Path
import json
import shutil
import numpy as np
from PIL import Image
from model import defaults
from mutations import MUTATIONS,build
from numeric_backend import ROOT,engine_run,read_resource,write_json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir


def image(path):return np.asarray(Image.open(path).convert("RGB"),dtype=float)/255.
def difference(a,b):return float(np.mean(np.abs(image(a)-image(b))))


def capture(task,project,tag,changes=None,frames=3,camera=None):
    config=json.loads((public_dir(project) / 'demo.json').read_text(encoding="utf-8"))["config"]
    config.update(changes or {})
    out=ROOT/"author/reports/visual_controls"/task/tag
    request={"config":config,"frames":frames,"width":640,"height":360,"dt":1/15}
    if camera:request["camera"]=camera
    report=engine_run(project,[],out,180,script="res://fixture/visual_runner.gd",request_data=request)
    if report["status"]!="RENDERED":raise RuntimeError(report)
    return out,report


def texture(out,report,target,uniform):
    info=report["snapshots"][-1]["textures"][target][uniform]
    if info["kind"]=="viewport":return image(out/info["file"])
    return np.frombuffer((out/info["file"]).read_bytes(),dtype="<f4")


def detector(task,project,kind,tag):
    if kind=="camera_state":
        a,ra=capture(task,project,tag+"_a")
        b,rb=capture(task,project,tag+"_b",camera={"position":[-3.,2.8,4.],"look_at":[0.,.8,0.]})
        error=float(np.max(np.abs(texture(a,ra,"TargetMesh","values0")-texture(b,rb,"TargetMesh","values0"))))
        return error<2e-5,{"bound_burn_state_camera_error":error}
    if kind=="display_dependency":
        if task.startswith("A"):ca,cb={"R0":.2},{"R0":1.8}
        elif task.startswith("B"):
            size=json.loads((public_dir(project) / 'demo.json').read_text(encoding="utf-8"))["config"]["grid_size"]
            n=int(np.prod(size));ca,cb={"wetness":[0.]*n},{"wetness":[.8]*n}
        else:ca,cb={"eta_t":1.05},{"eta_t":1.75}
        a,ra=capture(task,project,tag+"_a",ca)
        b,rb=capture(task,project,tag+"_b",cb)
        error=difference(a/"frame_00002.png",b/"frame_00002.png")
        return error>1e-4,{"image_response_mae":error}
    if kind=="ambient_preservation":
        common={"light_rgb":[0.,0.,0.],"density_size":[5,4,3]}
        a,ra=capture(task,project,tag+"_a",common|{"density":[0.]*60})
        b,rb=capture(task,project,tag+"_b",common|{"density":[.8]*60})
        error=difference(a/"frame_00002.png",b/"frame_00002.png")
        return error<1e-5,{"ambient_image_mae":error}
    if kind=="shadow_linearity":
        p={"fog_density":0.,"density_size":[5,4,3],"density":[.5]*60,"cloud_min":[-10.,3.,-10.],"cloud_max":[10.,5.,10.],
           "cloud_sigma":.7,"light_dir":[0.,1.,0.],"light_rgb":[1.,.9,.72],"ambient_color":[.09,.08,.065],"direct_color":[.34,.32,.27]}
        out,report=capture(task,project,tag,p)
        rgb=image(out/"frame_00002.png")
        x,y=map(lambda v:int(round(v)),report["ground_center_pixel"])
        rgb=np.median(rgb[y-2:y+3,x-2:x+3],axis=(0,1))
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        expected=np.array(p["ambient_color"])+np.array(p["direct_color"])*p["light_rgb"]*np.exp(-.7)
        error=float(np.max(np.abs(linear-expected)))
        return error<.015,{"linear_pixel":linear.tolist(),"expected":expected.tolist(),"max_error":error,"pixel":[x,y]}
    if kind in ("layer_current","layer_exclusion"):
        out,report=capture(task,project,tag,frames=28)
        rear=out/"RearCapture_00027.png"
        used=report["snapshots"][-1]["textures"]["FrontTarget"]["background_tex"]["file"]
        binding_error=difference(rear,out/used)
        dynamic=difference(rear,out/"RearCapture_00000.png")
        proper_masks=report["capture_masks"]=={"OpaqueCapture":1,"RearCapture":3}
        return binding_error<1e-6 and dynamic>1e-5 and proper_masks,{"front_input_mae":binding_error,"rear_time_mae":dynamic,"masks":report["capture_masks"]}
    raise ValueError(kind)


def check_bound_resources(task,out):
    """Verify that actual bound float images contain the actual computed resource."""
    report=json.loads((out/"result.json").read_text(encoding="utf-8"))
    state=report["snapshots"][-1]["state"]
    targets={"A":("TargetMesh","material_channels","values0",[0,1,2,3]),
             "B":("GroundPatch","pom_hit","values0",[0,1,2,3]),
             "C":("GroundReceiver","cloud_transmittance","values0",[4]),
             "D":("WaterPatch","flow_phases","values0",[6,7,8]),
             "E":("FrontTarget" if task=="E_L2" else "TransparentTarget","front_optical_terms","optical_uv",[11,12,13])}
    target,key,uniform,channels=targets[task[0]]
    want=read_resource(out,state[key])[:,channels]
    got=texture(out,report,target,uniform).reshape(-1,4)[:,:len(channels)]
    return {"status":"PASS" if np.array_equal(want,got) else "FAIL","max_error":float(np.max(np.abs(want-got))),
            "source":key,"bound_target":target,"bound_uniform":uniform}


def run():
    results=[]
    for task,mutations in MUTATIONS.items():
        for mutation in mutations:
            kind=mutation[-1]
            if kind=="numeric":continue
            name=mutation[0]
            project=ROOT/"author/references"/task/"gpu_solution"
            try:
                good,good_evidence=detector(task,project,kind,"positive_"+name)
                bad_project=build(task,mutation)
                bad,bad_evidence=detector(task,bad_project,kind,"negative_"+name)
                status="REJECTED" if good and not bad else "DETECTOR_FAILED"
                results.append({"task":task,"mutation":name,"status":status,"reference_pass":good,"faulty_pass":bad,"reference":good_evidence,"faulty":bad_evidence})
            except Exception as exc:results.append({"task":task,"mutation":name,"status":"CONTROL_ERROR","error":str(exc)})
            print(task,name,results[-1],flush=True)
    write_json(ROOT/"author/reports/mutations_visual.json",results)
    return results


if __name__=="__main__":run()
