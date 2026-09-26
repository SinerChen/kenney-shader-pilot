"""Author-selected ordinary input domains measured from the imported native mesh."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from l3_source import ROOT,SOURCE,dump,digest,manifest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_layout import public_dir

Image.MAX_IMAGE_PIXELS=None
EVIDENCE=ROOT/"author/source_audit/native_runtime"


def geometry(name,surface=0):
    meta=json.loads((EVIDENCE/"geometry.json").read_text())[name][surface]
    widths={"vertices":3,"normals":3,"uv":2,"uv2":2,"color":4,"indices":1}
    return {key:np.fromfile(EVIDENCE/value["file"],dtype="<i4" if key=="indices" else "<f4").reshape(-1,widths[key]) for key,value in meta.items()}


def sample(image,uv,repeat=False,offset=(0,0),size=None):
    w,h=size or image.size
    q=np.array(uv)*[w,h]-.5;i=np.floor(q).astype(int);f=q-i
    out=np.zeros(len(image.getpixel((0,0))) if isinstance(image.getpixel((0,0)),tuple) else 1)
    for y in (0,1):
        for x in (0,1):
            pos=i+[x,y];pos=pos%[w,h] if repeat else np.clip(pos,0,[w-1,h-1])
            out+=np.atleast_1d(image.getpixel((int(pos[0]+offset[0]),int(pos[1]+offset[1]))))*(f[0] if x else 1-f[0])*(f[1] if y else 1-f[1])/255
    return out


def terrain_interpolate(points):
    geo=geometry("Main Terrain/Plane_031")
    source=json.loads((EVIDENCE/"result.json").read_text())
    node=next(m for m in source["meshes"] if m["path"]=="Main Terrain/Plane_031")
    vertices=geo["vertices"]+node["transform"][-1]
    indices=geo["indices"].reshape(-1,3);tri=vertices[indices];xz=tri[:,:,[0,2]]
    a=xz[:,1]-xz[:,0];b=xz[:,2]-xz[:,0];det=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    rows=[]
    for point in points:
        q=np.array(point)-xz[:,0]
        u=np.divide(q[:,0]*b[:,1]-q[:,1]*b[:,0],det,out=np.full_like(det,-1),where=abs(det)>1e-10)
        v=np.divide(a[:,0]*q[:,1]-a[:,1]*q[:,0],det,out=np.full_like(det,-1),where=abs(det)>1e-10)
        valid=np.where((u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001))[0]
        if not len(valid):raise ValueError("Chart leaves the selected terrain mesh")
        k=valid[0];weights=[1-u[k]-v[k],u[k],v[k]]
        rows.append({"world":(np.array(weights)@tri[k]).tolist(),"uv":(np.array(weights)@geo["uv"][indices[k]]).tolist(),"uv2":(np.array(weights)@geo["uv2"][indices[k]]).tolist()})
    return rows


def effective_weights(splat0,splat1,bumps):
    result=[]
    for group,splat in enumerate([splat0,splat1]):
        blend=np.array([np.prod(1-np.array(splat[:3])),*splat[:3]])
        t=np.clip(blend/.05,0,1);h=(np.array(bumps[group*4:group*4+4])+blend)*t*t*(3-2*t)
        w=np.clip([h[i]+.2-max(np.delete(h,i)) for i in range(4)],0,1)
        result.extend((w/w.sum()*(1-splat1[3] if group==0 else splat1[3])).tolist())
    return np.array(result)


def build():
    # These are public author input choices, not claims about upstream material names.
    atlas=Image.open(SOURCE/"Textures/Terrain/terrain1_ormh.png").convert("RGBA")
    s0=Image.open(SOURCE/"Textures/Splat map 1.png").convert("RGBA")
    s1=Image.open(SOURCE/"Textures/Splat map 2.png").convert("RGBA")
    size=(atlas.width//2,atlas.height//4)
    candidates=[]
    for cx,cz in [(x,z) for x in (-12,-6,0,6,12,18) for z in (-12,-6,0,6,12,18)]:
        points=[[cx+x,cz+z] for z in np.linspace(-3,3,7) for x in np.linspace(-4,4,9)]
        rows=terrain_interpolate(points);allowed=[]
        for row in rows:
            bumps=[sample(atlas,row["uv"],True,((i%2)*size[0],(i//2)*size[1]),size)[3] for i in range(8)]
            weight=effective_weights(sample(s0,row["uv2"]),sample(s1,row["uv2"]),bumps)[0]
            allowed.append(weight>=.55)
        fraction=float(np.mean(allowed));height=np.array([row["world"][1] for row in rows])
        candidates.append({"center_xz":[cx,cz],"allow_fraction":fraction,"height_range":float(np.ptp(height)),"center_y":float(height[len(height)//2])})
    eligible=[x for x in candidates if .1<x["allow_fraction"]<.9]
    chosen=min(eligible or candidates,key=lambda x:abs(x["allow_fraction"]-.5)+x["height_range"]*.02)
    cx,cz=chosen["center_xz"];cy=chosen["center_y"]
    chart={"origin_world":[cx,cy,cz],"axes_world":[[1,0,0],[0,0,1]],"extent_m":[8,6],"grid_size":[64,48],
           "surface_rule":"Vertical intersection with the selected original mesh, interpolate original UV/UV2/TBN; inward depth follows its local surface normal.",
           "sample_at":"cell centers","source_geometry_sha256":digest(EVIDENCE/json.loads((EVIDENCE/"geometry.json").read_text())["Main Terrain/Plane_031"][0]["vertices"]["file"])}
    terrain={"target":"Main Terrain/Plane_031","material":"res://Materials/Terrain 1.tres","shader":"res://Shaders/Blend8 splat.gdshader",
             "semantic_layer_labels":["brown soil","gravel","coarse bare ground","moss","leaf litter","moss and soil","lichen and rock","unused white"],
             "semantic_basis":"Author visual classification of the original 2x4 color array; only layer 0 is authorized in this task.",
             "allowed_layers":[0],"tau_allow":.55,"threshold_margin":.005,"chart":chart,"material_weights":"Original get_depth_blended_weights normalized within each group, then multiply groups by (1-splat1.a) and splat1.a.",
             "state_boundary":"four-neighbor zero flux across H=0 or patch boundary","texture_sampling_for_support":{"lod":0,"filter":"linear","array_repeat":True},
             "calibration":"DRAFT_SOURCE_MEASURED_GPU_TOLERANCE_PENDING"}
    dump(ROOT/"starters/public/B_L3/terrain_task.json",terrain)
    dump(ROOT/"author/source_audit/terrain_domain_search.json",{"candidates":candidates,"selected":chosen,"source":"Original mesh UV/UV2 and source splat/ORMH images; compressed GPU sampling tolerance is not yet calibrated."})
    river=geometry("Main Terrain/BezierCurve_001");vertices=river["vertices"]
    indices=river["indices"].reshape(-1,3);tri=vertices[indices]
    lengths=np.stack([np.linalg.norm(tri[:,1]-tri[:,2],axis=1),np.linalg.norm(tri[:,0]-tri[:,2],axis=1),np.linalg.norm(tri[:,0]-tri[:,1],axis=1)],axis=1)
    normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);double_area=np.linalg.norm(normal,axis=1)
    radius=double_area/np.maximum(lengths.sum(axis=1),1e-12)
    centers=(tri*lengths[:,:,None]).sum(axis=1)/lengths.sum(axis=1)[:,None]
    transform=next(m["transform"] for m in json.loads((EVIDENCE/"result.json").read_text())["meshes"] if m["path"]=="Main Terrain/BezierCurve_001")
    positions=centers+transform[-1]
    valid=np.where((radius>3)&(abs(normal[:,1])/np.maximum(double_area,1e-12)>.98))[0]
    k=min(valid,key=lambda i:np.linalg.norm(positions[i][[0,2]]))
    up=normal[k]/double_area[k]
    if up[1]<0:up=-up
    axis=np.array([1.,0,0]);axis-=up*np.dot(axis,up);axis/=np.linalg.norm(axis);z=np.cross(axis,up)
    domain={"target":"Main Terrain/BezierCurve_001","material":"res://Materials/River.tres","reference_origin_local":centers[k].tolist(),
            "surface_axes_local":[axis.tolist(),z.tolist()],"normal_local":up.tolist(),"reference_extent_m":[4,3],"grid_size":[48,36],
            "valid_region":"Declared rectangle lies inside an original near-horizontal river triangle.","transform_scope":"Fixed source rest transform, then positive axis scaling [0.75,1.5] and rigid transforms between resets; no shear or animated remapping.",
            "contact_distance_m":.12,"physical_flow_units":"m/s along normalized transformed surface axes","status":"SOURCE_GEOMETRY_MEASURED_INTEGRATION_PENDING"}
    for t in ["D_L3","E_L3"]:dump(public_dir(ROOT/"starters"/t) / 'river_domain.json',domain)
    center=positions[k]
    contacts={"sources":[{"id":"contact_1","world_position":center.tolist(),"radius_m":.45,"strength":1.2},{"id":"off_surface","world_position":(center+up*2).tolist(),"radius_m":.45,"strength":1.2}],"source_motion":"Only new injection follows moved world anchors; old foam retains its state."}
    dump(ROOT/"starters/public/D_L3/contact_objects.json",contacts)
    flow=ROOT/"starters/D_L3/assets/task_inputs/D_L3/physical_flow.bin";flow.parent.mkdir(parents=True,exist_ok=True)
    np.tile([.6,.12],(48*36,1)).astype("<f4").tofile(flow)
    dump(flow.with_suffix(".json"),{"file":flow.name,"shape":[36,48,2],"dtype":"<f4","units":"m/s","channels":["axis_0","axis_1"]})
    optical={"water":domain["target"],"front_center_world":(center+up*1.4).tolist(),"front_size_m":[1.1,1.1],"front_geometry":"res://assets/task_inputs/E_L3/front_geometry.tres",
             "layers":"one front, one original water surface, opaque forest","ell":.32,"eta_i":1.,"eta_t":1.33,"sigma_a":[.25,.06,.03],
             "background_inputs":"unimplemented slots; solution must supply current water and opaque content without self feedback","normal_composition":"shortest-arc rotation from chart up to n_wave applied to n_base"}
    dump(ROOT/"starters/public/E_L3/optical_layer_scope.json",optical)
    mesh=ROOT/"starters/E_L3/assets/task_inputs/E_L3/front_geometry.tres";mesh.parent.mkdir(parents=True,exist_ok=True);mesh.write_text('[gd_resource type="QuadMesh" format=3]\n[resource]\nsize = Vector2(1.1, 1.1)\n',encoding="utf-8")
    dump(ROOT/"starters/public/E_L3/wave_region.json",{"chart":"river_domain.json","dt":1/60,"wave_speed":.65,"gamma":.35,"initial_height":0.,"initial_previous_height":0.,"normal_frame":"river chart","amplitude_domain_m":[-.1,.1]})
    cloud={"receiver":terrain["target"],"receiver_chart":chart,"density_coefficients":{"a":.8,"b":.2,"theta":.35},"grid_size":[24,12,24],
           "cloud_bounds_world":[[cx-4,cy+6,cz-3],[cx+4,cy+9,cz+3]],"fog_bounds_world":[[cx-4,cy+.1,cz-3],[cx+4,cy+3,cz+3]],"cloud_sigma":.8,"cloud_steps":32,"view_steps":32,
           "fog_density":.15,"fog_scatter":.8,"fog_absorb":.2,"g":.2,"directional_light":"DirectionalLight3D","lighting_scope":"Only the selected original surface direct-light contribution; preserve native ambient and geometry shadows.","status":"INPUT_DOMAIN_SELECTED_VISUAL_CALIBRATION_PENDING"}
    dump(ROOT/"starters/public/C_L3_R/local_cloud_fog.json",cloud)
    dump(ROOT/"author/source_audit/river_chart_measurement.json",{"triangle":int(k),"inradius_m":float(radius[k]),"origin_world":center.tolist(),"normal":up.tolist(),"reference_domain":domain})
    # Baked source wind mask is exactly zero on these branch vertices.
    objects=[]
    for object_id, root, name, speed in [("tree_1","Decorations-Forest/Tree_small_2","Tree small 2",1.2),("tree_2","Decorations-Forest/Tree_small_1","Tree small 1",1.4)]:
        bark=geometry(root+"/"+name)
        stable=np.where((bark["color"][:,0]+bark["color"][:,1]<1e-7)&(bark["vertices"][:,1]>=0)&(bark["vertices"][:,1]<=4))[0]
        selected=stable[np.linspace(0,len(stable)-1,min(48,len(stable))).astype(int)]
        anchors=np.concatenate([bark["vertices"][selected],bark["normals"][selected]],axis=1).astype("<f4")
        file=ROOT/"starters/A_L3/assets/task_inputs/A_L3"/(object_id+"_anchors.bin")
        file.parent.mkdir(parents=True,exist_ok=True);anchors.tofile(file)
        objects.append({"object_id":object_id,"root":root,"origin_ref":[0,0,0],"propagation_speed":speed,
                        "anchor_inputs":{"file":file.relative_to(ROOT/"starters/A_L3").as_posix(),"dtype":"<f4","shape":list(anchors.shape),"channels":["position.x","position.y","position.z","normal.x","normal.y","normal.z"],"frame":"object rest space","source_vertex_wind_weight":0}})
    dump(ROOT/"starters/public/A_L3/targets.json",{"objects":objects,"transform_scope":"Preserve fixed authored rest transforms, including their non-uniform scale; additional test transforms are rigid with positive uniform scale in [0.75,1.5]."})
    dump(ROOT/"starters/public/A_L3/burn_ember_config.json",{"origin_ref":[0,0,0],"R0":.1,"speed":1.2,"width":.3,"noise_amplitude":.2,"dt":1/60,"lifetime":2.,"emit_threshold":.6,"parameter_base":"development.json"})
    for task in ["A_L3","B_L3","C_L3_R","D_L3","E_L3"]:
        dest=ROOT/"starters"/task
        dump(ROOT/"author/baseline"/(task+".json"),{k:v for k,v in manifest(dest).items() if not k.startswith(("solution/","scratch/"))})
    print("Source-measured input domains written",chosen,"river triangle",k,"stable anchors",len(anchors),flush=True)


if __name__=="__main__":build()
