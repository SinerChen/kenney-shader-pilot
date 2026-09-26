"""Author data generation and public wire-format descriptions."""
import copy
import numpy as np

OPERATIONS = {
    "burn_query": ["noise","signed_front","char_fraction","front_strength"],
    "curl_query": ["curl.x","curl.y","curl.z","velocity.x","velocity.y","velocity.z"],
    "particle_step": ["next_position.x","next_position.y","next_position.z","age","active","cooling"],
    "stamp_query": ["depth_field"],
    "pom_query": ["valid","hit_depth","hit_uv.x","hit_uv.y","hit_xz.x","hit_xz.z"],
    "wet_step": ["wetness_field","drying_rate_field"],
    "cloud_query": ["valid_interval","s0","s1","optical_depth","transmittance"],
    "fog_query": ["phase","L_scatter.r","L_scatter.g","L_scatter.b","T_view"],
    "flow_query": ["uv_phase0.x","uv_phase0.y","uv_phase1.x","uv_phase1.y","weight0","weight1","sampled_color.r","sampled_color.g","sampled_color.b","blended_normal.x","blended_normal.y","blended_normal.z"],
    "foam_step": ["foam_field","source_field"],
    "optics_query": ["F","Tdir.x","Tdir.y","Tdir.z","R.x","R.y","R.z","A.r","A.g","A.b","has_transmission","background_uv.x","background_uv.y","valid","color.r","color.g","color.b"],
    "wave_step": ["height"],
    "wave_normal_query": ["normal.x","normal.y","normal.z"],
}
TASK_OPERATIONS = {
    "A_L1":["burn_query"],"A_L2":["curl_query","particle_step"],
    "B_L1":["stamp_query","pom_query"],"B_L2":["wet_step"],
    "C_L1":["cloud_query"],"C_L2":["fog_query"],
    "D_L1":["flow_query"],"D_L2":["foam_step"],
    "E_L1":["optics_query"],"E_L2":["wave_step","wave_normal_query"],
}
QUERY_ROWS={"burn_query":("points",3),"curl_query":("points",3),"particle_step":("particles",4),
            "pom_query":("pom_rays",5),"cloud_query":("points",3),"fog_query":("view_rays",7),
            "flow_query":("uvs",2),"optics_query":("optical_rays",9)}


def defaults(seed=202):
    rng=np.random.default_rng(seed)
    nx,nz=8,6
    j,i=np.mgrid[:nz,:nx]
    z,x=np.mgrid[:8,:8]
    colors=np.stack((.12+.14*((x+z)%2),.28+.12*np.sin(x*.9)**2,.4+.18*np.cos(z*.7)**2),axis=-1)
    normals=np.stack((.13*np.sin(x),np.ones_like(x),.13*np.cos(z)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    p={
      "P":rng.permutation(256).tolist(),"time":.65,"t0":0.,"dt":.025,
      "points":[[-.63,.28,-.31],[.11,.82,.27],[.8,-.23,-.7],[1.3,.4,.2]],
      "origin_ref":[0.,.3,0.],"R0":.7,"speed":.22,"noise_amplitude":.3,
      "base_frequency":1.7,"octaves":3,"gain":.5,"lacunarity":2.,"width":.17,"enabled":True,
      "frequency":.8,"epsilon":.025,"drift":[.11,-.09,.04],"offsets":[[1.13,2.42,-.6],[-2.3,5.7,.8],[6.1,-.7,3.4]],
      "up_speed":.65,"curl_strength":.35,"lifetime":2.4,
      "particles":[[-.7,.2,.1,.1],[.5,.6,-.3,.9],[.2,.1,.8,2.39]],
      "emit_threshold":.4,"enable_emission":True,
      "anchors":[[0.,-.4,0.],[.5,0.,0.],[0.,.4,.2],[-.4,.8,0.],[0.,1.2,0.]],
      "instance_transform":np.eye(4).reshape(-1,order="F").tolist(),
      "grid_size":[nx,nz],"domain_min":[-2.,-1.5],"domain_size":[4.,3.],
      "d_max":.08,"depth":np.zeros(nx*nz).tolist(),
      "mask_size":[6,8],"mask":np.clip(((x[:,:6]-2.1)**2/6+(z[:,:6]-3.8)**2/15<1)*(.55+.45*(z[:,:6]>3)),0,1).ravel().tolist(),
      "contacts":[[11,-.25,.1,.35,.9,1.4,.04]],
      "pom_rays":[[0.,0.,.6,.8,0.],[.3,.1,0.,1.,0.],[-1.99,0.,.6,.8,0.]],
      "wetness":(.12+.25*rng.random(nx*nz)).tolist(),"source":np.zeros(nx*nz).tolist(),
      "diffusion":.2,"lambda0":.8,"beta":2.,
      "cloud_world_to_local":np.eye(4).reshape(-1,order="F").tolist(),
      "cloud_min":[-2.,3.,-2.],"cloud_max":[2.,5.,2.],"density_size":[5,4,3],
      "density":(.1+.9*rng.random(60)).tolist(),"cloud_sigma":.7,"cloud_steps":12,
      "light_dir":[.2,.96,.1959591794226543],"light_rgb":[1.,.9,.72],
      "fog_min":[-2.,0.,-2.],"fog_max":[2.,2.,2.],"fog_density":.22,"fog_scatter":.7,"fog_absorb":.1,"g":.35,"view_steps":8,
      "view_rays":[[0.,1.,4.,0.,0.,-1.,8.],[0.,1.,0.,0.,0.,-1.,1.5]],
      "uvs":[[.2,.3],[.51,.68],[.01,.99]],"period":1.6,"phase":.12,"tiling":2.3,
      "flow":np.stack((.35+.16*np.sin(j),.12*np.cos(i)),axis=-1).reshape(-1,2).tolist(),
      "texture_size":[8,8],"color_texture":colors.reshape(-1,3).tolist(),"normal_texture":normals.reshape(-1,3).tolist(),"normal_encoded":False,
      "foam":(.2*np.exp(-((i-2)**2+(j-2)**2)/3)).ravel().tolist(),"sources":[[-.5,0.,.8,1.1]],"decay":.6,
      "eta_i":1.,"eta_t":1.33,"ell":.22,"sigma_a":[.12,.03,.015],
      "optical_rays":[[.6,-.8,0.,0.,1.,0.,0.,0.,.5],[0.,-1.,0.,0.,1.,0.,.3,.1,.5]],
      "view_projection":np.eye(4).reshape(-1,order="F").tolist(),"reflection_color":[.4,.55,.75],"fallback_color":[.06,.08,.13],
      "height":(.008*np.exp(-((i-3)**2+(j-3)**2)/2)).ravel().tolist(),"height_prev":np.zeros(nx*nz).tolist(),
      "force":np.zeros(nx*nz).tolist(),"wave_speed":1.2,"gamma":.6,
      "front_visible":True,"rear_visible":True,"burn_visible":True,"embers_visible":True,
      "ambient_color":[.09,.08,.065],"direct_color":[.34,.32,.27],
      "dry_color":[.32,.2,.1],"wet_color":[.13,.08,.045],"dry_roughness":.9,"wet_roughness":.22,
      "wood_color":[.36,.16,.06],"char_color":[.025,.016,.009],"ember_color":[1.,.22,.02],
    }
    p["light_dir"]=(np.array(p["light_dir"])/np.linalg.norm(p["light_dir"])).tolist()
    return p


KEYS=list(defaults())+["contact_count","source_count"]


def gpu_header():
    return ("#version 450\nlayout(local_size_x=64) in;\n"
      "layout(set=0,binding=0,std430) readonly buffer Input { float input_data[]; };\n"
      "layout(set=0,binding=1,std430) writeonly buffer Output { float output_data[]; };\n"+
      "\n".join(f"#define K_{key} {index}" for index,key in enumerate(KEYS))+"\n")


def merge(p,changes):
    q=copy.deepcopy(p);q.update(copy.deepcopy(changes));return q


def fields(name,p):
    out=OPERATIONS[name].copy()
    if name=="fog_query":out += [f"T_cloud_at_samples.{i}" for i in range(p["view_steps"])]+[f"T_fog_light.{i}" for i in range(p["view_steps"])]
    return out


def rows(name,p):
    return len(p[QUERY_ROWS[name][0]]) if name in QUERY_ROWS else int(np.prod(p["grid_size"]))
