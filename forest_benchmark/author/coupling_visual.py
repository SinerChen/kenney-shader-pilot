"""Paired scene interventions complement the independent numerical coupling cases."""
import copy
import json
import numpy as np
from numeric_backend import ROOT,engine_run,read_resource,write_json
from visual_controls import difference,texture
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir


def check(task,index):
    project=ROOT/"author/references"/task/"gpu_solution"
    demo=json.loads((public_dir(project) / 'demo.json').read_text(encoding="utf-8"))
    a=copy.deepcopy(demo["config"]);b=copy.deepcopy(a)
    ea=copy.deepcopy(demo["events"]);eb=copy.deepcopy(ea)
    invariants=[];camera=None;n=int(np.prod(a["grid_size"]))
    if task=="A_L2":
        if index==1:b["origin_ref"]=[.6,.75,0.]
        if index==2:b["speed"]*=1.7
        if index==3:eb.append({"tick":15,"event":{"type":"set","values":{"enable_emission":False}}})
        if index==4:b["curl_strength"]*=3;invariants=["burn_state"]
        if index==5:b.update(burn_visible=False,embers_visible=False);invariants=["burn_state","particle_state"]
    if task=="B_L2":
        a["wetness"]=[.55]*n;b["wetness"]=[.55]*n
        if index==1:b["depth"]=[.06]*n
        if index==2:
            for event in eb:
                if event["event"]["type"]=="water":event["event"]["contact"][1]+=.8
        if index==3:
            source=np.zeros(n);source[n//2:n//2+8]=2.
            a["source"]=source.tolist();b["source"]=source.tolist()
            ea=[];eb=[{"tick":10,"event":{"type":"set","values":{"source":[0.]*n}}}]
        if index==4:b["diffusion"]=0.
        if index==5:b["lambda0"]=0.
        if index>1:invariants=["depth_field"]
    if task=="C_L2":
        ea=[];eb=[]
        if index==1:b["density"]=[0.]*len(a["density"])
        if index==2:b["fog_density"]=0.;invariants=["cloud_transmittance"]
        if index==3:b["cloud_world_to_local"][12]=1.4
        if index==4:camera={"position":[-3.,2.7,4.5],"look_at":[0.,.3,0.]};invariants=["cloud_transmittance"]
        if index==5:b["light_rgb"]=[0.,0.,0.];invariants=["cloud_transmittance"]
    if task=="D_L2":
        ea=[];eb=[]
        if index==1:b.update(tiling=4.2,phase=.4,period=.8);invariants=["foam_field"]
        if index==2:b["flow"]=(-np.array(a["flow"])).tolist()
        if index==3:b["flow"]=[[0.,0.]]*n
        if index==4:eb=[{"tick":15,"event":{"type":"set","values":{"sources":[]}}}]
        if index==5:eb=[{"tick":15,"event":{"type":"set","values":{"sources":[[.8,.5,.65,2.]]}}}]
    if task=="E_L2":
        if index==1:
            eb=[{"tick":15,"event":{"type":"wave","event_id":"different","source":[.7,.3,.7,.7]}}]
        if index==2:b["eta_t"]=1.7;invariants=["wave_height_current","wave_height_prev"]
        if index==3:
            b["height"]=[0.]*n;b["height_prev"]=[0.]*n;eb=[]
        if index==4:b["front_visible"]=False;invariants=["wave_height_current","wave_height_prev"]
        if index==5:b["rear_visible"]=False;invariants=["wave_height_current","wave_height_prev"]
    outputs=[]
    for label,config,events in [("baseline",a,ea),("intervention",b,eb)]:
        out=ROOT/"author/reports/visual_coupling"/task/f"I{index:02d}"/label
        request={"frames":36,"width":640,"height":360,"dt":1/15,"config":config,"events":events}
        if camera and label=="intervention":request["camera"]=camera
        report=engine_run(project,[],out,180,script="res://fixture/visual_runner.gd",request_data=request)
        outputs.append((out,report))
    (pa,ra),(pb,rb)=outputs
    mae=difference(pa/"frame_00035.png",pb/"frame_00035.png")
    checks={}
    for name in invariants:
        va=read_resource(pa,ra["snapshots"][-1]["state"][name]);vb=read_resource(pb,rb["snapshots"][-1]["state"][name])
        error=float(np.max(np.abs(va-vb))) if va.size else 0.
        checks[name]={"max_abs":error,"pass":error<=2e-5}
    if task=="E_L2" and index in [2,4]:
        err=difference(pa/"RearCapture_00035.png",pb/"RearCapture_00035.png")
        checks["rear_input_unchanged"]={"max_abs":err,"pass":err<1e-6}
    passed=mae>1e-7 and all(item["pass"] for item in checks.values())
    result={"task":task,"group":index,"status":"PASS" if passed else "FAIL","image_response_mae":mae,
            "invariants":checks,"baseline":str(pa.relative_to(ROOT)),"intervention":str(pb.relative_to(ROOT)),
            "meaning":"visible response and specified invariants; aesthetic rubric not scored"}
    return result


if __name__=="__main__":
    results=[]
    for chain in "ABCDE":
        task=chain+"_L2"
        for i in range(1,6):
            try:row=check(task,i)
            except Exception as exc:row={"task":task,"group":i,"status":"INFRA_ERROR","error":str(exc)}
            results.append(row);print(task,i,row["status"],row.get("image_response_mae"),flush=True)
            write_json(ROOT/"author/reports/visual_coupling.json",results)
