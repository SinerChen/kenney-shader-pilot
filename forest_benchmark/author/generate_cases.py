from pathlib import Path
import copy
import json
import math
import numpy as np
from model import defaults,TASK_OPERATIONS,merge
from simulation_cpu import Simulator
from numeric_backend import ROOT,write_json


def plain(value):
    if isinstance(value,np.ndarray):return {"numeric":value.tolist(),"shape":list(value.shape)}
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
    if isinstance(value,list):return [plain(v) for v in value]
    return value


def query_commands(task,p,variants,names=None):
    out=[]
    for changed in variants:
        q=merge(p,changed);q["task_id"]=task
        out.append({"op":"reset","config":q})
        for name in names or TASK_OPERATIONS[task]:out.append({"op":"query","name":name,"payload":q})
    return out


def sequence(task,p,frames,repeat=False):
    p=merge(p,{"task_id":task})
    commands=[{"op":"reset","config":p}]
    for events in frames:
        commands += [{"op":"advance","dt":p["dt"],"events":events},{"op":"outputs"}]
    return commands*2 if repeat else commands


def variations(task,p):
    n=int(np.prod(p["grid_size"]));zeros=[0.]*n;ones=[1.]*n
    j,i=np.mgrid[:p["grid_size"][1],:p["grid_size"][0]]
    if task=="A_L1":
        return [
          [{"enabled":False},{"R0":-4.,"noise_amplitude":0.}],
          [{"noise_amplitude":0.,"points":[[.6,0,0],[.8,0,0],[1,0,0]],"origin_ref":[0.,0.,0.],"speed":0.,"R0":.8}],
          [{"octaves":1,"points":[[-1.12,-.42,.67],[2.34,.81,-.99],[0.,0.,0.]]}],
          [{"octaves":5,"gain":.7,"lacunarity":1.8},{"octaves":4,"gain":0.}],
          [{"P":defaults(9343)["P"]}],
          [{"origin_ref":[-.7,.3,.25]},{"origin_ref":[.4,-.3,.8]}],
          [{"noise_amplitude":0.,"R0":1.,"speed":0.,"width":.2,"origin_ref":[0.,0.,0.],"points":[[.8,0,0],[1,0,0],[1.2,0,0],[.80001,0,0],[1.19999,0,0]]}],
          [{"width":.005,"origin_ref":[-1.,-.3,-.2],"points":[[-1.7,-.31,-.2],[-.4,-.2,-.3]]}],
          [{},{}],
          [{"time":t,"camera_position":cam} for t,cam in [(0,[2,3,4]),(.5,[2,3,4]),(1,[2,3,4]),(1,[-3,2,4])]],
        ]
    if task=="A_L2":
        return [
          [{"curl_strength":0.,"up_speed":0.}],
          [{"curl_strength":0.,"up_speed":1.3}],
          [{"points":[[-.23,.41,.82],[.33,-.76,1.12]]}],
          [{"epsilon":.01},{"epsilon":.08}],
          [{"drift":[.32,-.11,.2],"time":.17},{"drift":[.32,-.11,.2],"time":1.12}],
          [{},{},{},{},{},{},{},{},{},{}],
          [{"enable_emission":False}],
          [{"particles":[[.1,.3,.2,2.399],[.1,.3,.2,2.4],[.1,.3,.2,2.5]]}],
          [{}],
          [{},{}],
        ]
    if task=="B_L1":
        ramp=((i+.5)/p["grid_size"][0]*.05).ravel().tolist()
        return [
          [{"contacts":[]}],
          [{"contacts":[[1,0,0,0,1.2,1.7,.045]]}],
          [{"contacts":[[1,-.8,.4,0,1.,1.2,.04]]}],
          [{"contacts":[[1,0,0,a,1.,1.8,.04]]} for a in [0.,.71,1.57]],
          [{"contacts":[[1,0,0,0,.5,1.6,.04]]},{"contacts":[[1,0,0,0,1.4,.8,.04]]}],
          [{"contacts":[[1,0,0,0,1.,1.7,.04],[2,.2,.1,.2,1.,1.7,.04]]}],
          [{"contacts":[[1,1.85,1.3,.4,1.,1.7,.05]]}],
          [{"contacts":[[k,0,0,0,2.,2.4,.06] for k in range(8)]}],
          [{"contacts":[],"depth":[.032]*n},{"contacts":[],"depth":ramp},{"contacts":[],"depth":(.04*((i>1)&(i<5))).ravel().tolist()}],
          [{"contacts":[[4,0,0,0,1.,1.5,.04],[4,0,0,0,1.,1.5,.04]]}],
        ]
    if task=="B_L2":
        impulse=zeros.copy();impulse[2*p["grid_size"][0]+2]=.8
        return [
          [{"wetness":zeros,"source":zeros}],
          [{"diffusion":0.,"lambda0":0.,"wetness":zeros,"source":[2.]*n}],
          [{"lambda0":0.,"source":zeros,"wetness":impulse}],
          [{"diffusion":0.,"source":zeros,"wetness":[.7]*n}],
          [{"depth":(.07*(i>3)).ravel().tolist(),"wetness":[.7]*n,"diffusion":0.}],
          [{"domain_size":[3.,4.],"wetness":impulse}],
          [{"wetness":(.8*(i==0)).ravel().tolist(),"lambda0":0.}],
          [{"source":(60*(i==2)).ravel().tolist(),"wetness":zeros}],
          [{}],
          [{}],
        ]
    if task=="C_L1":
        constant=[.5]*60
        return [
          [{"density":[0.]*60}],
          [{"density":constant,"light_dir":[0.,1.,0.],"points":[[0.,0.,0.],[.5,0.,.3]]}],
          [{"density":np.broadcast_to(np.linspace(.1,.9,4)[None,:,None],(3,4,5)).ravel().tolist()}],
          [{"points":[[-.7,0.,.4],[.8,.3,-.2],[1.1,.8,.7]]}],
          [{"light_dir":[.6,.8,0.]}],
          [{"points":[[0.,3.8,0.],[1.,4.5,-.3]]}],
          [{"points":[[4.,0.,0.],[-8.,0.,-6.]]}],
          [{"light_dir":[0.,1.,0.],"points":[[2.,0.,2.],[2.01,0.,0.],[-2.,3.,0.]]}],
          [{"density":constant,"light_dir":[0.,1.,0.],"points":[[0.,3.,0.],[0.,4.,0.]],"cloud_steps":10}],
          [{}],
        ]
    if task=="C_L2":
        return [
          [{"fog_density":0.}],
          [{"density":[0.]*60}],
          [{"light_rgb":[0.,0.,0.]}],
          [{"g":0.}],
          [{"g":g} for g in [-.7,.7]],
          [{"fog_scatter":0.,"fog_absorb":.9}],
          [{"density":[.5]*60,"light_dir":[0.,1.,0.],"fog_density":.4,"view_steps":12}],
          [{"view_rays":[[0.,1.,0.,0.,0.,-1.,.6],[0.,1.,0.,0.,0.,-1.,8.]]}],
          [{"fog_density":1e-7},{"fog_scatter":0.,"fog_absorb":0.}],
          [{"cloud_steps":n,"view_steps":v} for n,v in [(3,3),(17,11)]],
        ]
    if task=="D_L1":
        return [
          [{"flow":[[0.,0.]]*n,"time":t} for t in [.1,1.4]],
          [{"flow":[[.4,-.1]]*n,"time":t} for t in [.2,.8]],
          [{}],
          [{"flow":(np.array(p["flow"])*2.5).tolist()}],
          [{"time":.24,"phase":.2}],
          [{"normal_encoded":True,"normal_texture":((np.array(p["normal_texture"])+1)*.5).tolist()}],
          [{"time":t,"phase":0.} for t in [p["period"]-1e-5,p["period"],p["period"]+1e-5,p["period"]*.5-1e-5,p["period"]*.5+1e-5]],
          [{"flow":[[3.,2.]]*n,"uvs":[[0.,0.],[1.,1.],[.001,.98]]}],
          [{"phase":ph,"time":t} for ph in [-.3,.63] for t in [.2,.2+p["period"]]],
          [{"time":t} for t in [32.,96.]],
        ]
    if task=="D_L2":
        return [
          [{"foam":zeros,"sources":[]}],
          [{"foam":zeros,"flow":[[0.,0.]]*n,"decay":0.}],
          [{"flow":[[.5,0.]]*n,"sources":[],"decay":0.}],
          [{}],
          [{"flow":[[0.,0.]]*n,"sources":[],"decay":2.,"foam":[.6]*n}],
          [{"sources":[[-.8,.4,.5,2.],[.7,-.5,.9,.8]]}],
          [{"flow":[[25.,0.]]*n,"foam":ones,"sources":[]}],
          [{"sources":[[0.,0.,2.,100.]],"foam":zeros}],
          [{}],
          [{"domain_size":[3.,2.]},{},{}],
        ]
    if task=="E_L1":
        rays=lambda angle:[[math.sin(angle),-math.cos(angle),0.,0.,1.,0.,0.,0.,.5]]
        return [
          [{"eta_i":1.4,"eta_t":1.4}],
          [{"optical_rays":rays(0),"eta_i":1.,"eta_t":1.5}],
          [{"optical_rays":rays(a)} for a in [.3,.8,1.2]],
          [{"eta_i":1.5,"eta_t":1.,"optical_rays":rays(.3)}],
          [{"ell":ell} for ell in [.08,.4]],
          [{"sigma_a":[.3,1.2,2.1]}],
          [{"eta_i":1.5,"eta_t":1.,"optical_rays":rays(math.asin(1/1.5)+d)} for d in [-.003,.003]],
          [{"eta_i":1.5,"eta_t":1.,"optical_rays":rays(1.1)}],
          [{"sigma_a":[0.,0.,0.]},{"ell":0.}],
          [{"optical_rays":[[.3,-math.sqrt(.91),0,0,1,0,x,0,.5]]} for x in [.2,3.]],
        ]
    if task=="E_L2":
        force=zeros.copy();force[3*p["grid_size"][0]+3]=2.
        return [
          [{"height":zeros,"height_prev":zeros,"force":zeros}],
          [{"height":[.01]*n,"height_prev":[.01]*n,"force":zeros}],
          [{"height":zeros,"height_prev":zeros,"force":force}],
          [{"height":(.003*np.exp(-((i-3.5)**2+(j-2.5)**2))).ravel().tolist(),"height_prev":zeros}],
          [{"force":np.array(force).tolist()},{"force":(np.array(force)*2).tolist()}],
          [{"gamma":g} for g in [0.,2.]],
          [{"height":(.003*(i==0)).ravel().tolist()}],
          [{"domain_size":[3.,4.]}],
          [{"height":(.002*i+.003*j).ravel().tolist()}],
          [{}],
        ]
    raise ValueError(task)


def generate():
    manifest=json.loads(next((ROOT/"author/specification").glob("04_*/task_manifest.json")).read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        tid=task["task_id"];p=defaults(417+ord(tid[0]));p["task_id"]=tid
        groups=variations(tid,p)
        for index,(spec,variants) in enumerate(zip(task["cases"],groups),1):
            commands=query_commands(tid,p,variants)
            contact={"type":"contact","event_id":"c1","contact":[1,0.,0.,.3,1.2,1.6,.04]}
            water={"type":"water","event_id":"w1","contact":[2,0.,0.,.3,1.2,1.6,0.],"amount":.35}
            wave={"type":"wave","event_id":"r1","source":[0.,0.,.8,2.]}
            if tid=="A_L2" and index in [6,7,9,10]:
                q=merge(p,{"R0":.45,"noise_amplitude":0.,"width":.35,"emit_threshold":.3})
                frames=[[] for _ in range(12)]
                if index==7:
                    q["enable_emission"]=False
                    frames[3]=[{"type":"set","values":{"enable_emission":True}}]
                if index==9:frames[4]=[{"type":"set","values":{"enable_emission":False}}]
                commands+=sequence(tid,q,frames,repeat=index==10)
            if tid=="A_L1" and index==9:
                commands+=query_commands(tid,p,[{"time":4.},{}])
            if tid=="B_L1" and index==10:
                commands+=sequence(tid,p,[[contact],[contact],[],[],[]],True)
            if tid=="B_L2" and index in [9,10]:
                commands+=sequence(tid,p,[[contact,water],[contact,water],[],[],[],[]],index==10)
            if tid=="C_L1" and index==10:
                angle=.63;c,s=math.cos(angle),math.sin(angle)
                r=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
                translation=np.array([1.2,-.4,.8]);world=np.eye(4);world[:3,:3]=r;world[:3,3]=translation
                q=merge(p,{"points":(np.array(p["points"])@r.T+translation).tolist(),"light_dir":(r@p["light_dir"]).tolist(),
                           "cloud_world_to_local":np.linalg.inv(world).reshape(-1,order="F").tolist()})
                commands+=query_commands(tid,q,[{}])
            if tid=="D_L2" and index in [9,10]:
                frames=[[],[],[{"type":"set","values":{"sources":[[.8,.3,.6,1.]]}}],[],[{"type":"set","values":{"sources":[]}}],[],[]]
                commands+=sequence(tid,p,frames,index==10)
            if tid=="E_L2" and index==10:
                commands+=sequence(tid,p,[[wave],[wave],[],[],[],[]],True)
            expected=plain(Simulator().execute(commands))
            directory=ROOT/"author/cases_private"/tid/spec["id"]
            write_json(directory/"input.json",{"commands":commands})
            write_json(directory/"expected.json",expected)
            write_json(directory/"metadata.json",{**spec,"status":"GENERATED_CPU_REFERENCE","private_seed":417+ord(tid[0]),"variant_count":len(variants)})
        print(tid,len(groups),"groups generated")
    return manifest


if __name__=="__main__":generate()
