"""Public type contracts only: no examples, defaults, thresholds or answers."""
from copy import deepcopy

GRID = {"grid_size": "Vector2i", "domain_min": "Vector2", "domain_size": "Vector2"}
NOISE = {"P": "Array[int]"}
CURL = dict(NOISE, frequency="float", epsilon="float", drift="Vector3", offsets="Array[Vector3]", up_speed="float", curl_strength="float")
CLOUD = {"cloud_world_to_local": "Matrix4", "cloud_min": "Vector3", "cloud_max": "Vector3", "density_size": "Vector3i", "density": "float[Nz,Ny,Nx]", "cloud_sigma": "float", "cloud_steps": "int", "light_dir": "Vector3"}

QUERIES = {
    "burn_query": (dict(NOISE, points="Vector3[N]", time="float", t0="float", origin_ref="Vector3", R0="float", speed="float", noise_amplitude="float", base_frequency="float", octaves="int", gain="float", lacunarity="float", width="float", enabled="bool"),
                   {"noise":"float", "signed_front":"float", "char_fraction":"float", "front_strength":"float"}),
    "curl_query": (dict(CURL, points="Vector3[N]", time="float"), {"curl":"Vector3", "velocity":"Vector3"}),
    "particle_step": (dict(CURL, particles="Tuple[x:float,y:float,z:float,age:float][N]", time="float", dt="float", lifetime="float"),
                      {"next_position":"Vector3", "age":"float", "active":"bool", "cooling":"float"}),
    "stamp_query": (dict(GRID, depth="float[Nz,Nx]", mask="float[H,W]", mask_size="Vector2i", contacts="Tuple[event_id:int,cx:float,cz:float,angle:float,size_x:float,size_z:float,increment:float][N]", d_max="float"), {"depth_field":"float"}),
    "pom_query": (dict(GRID, depth="float[Nz,Nx]", pom_rays="Tuple[x:float,z:float,Vx:float,Vy:float,Vz:float][N]", d_max="float"),
                  {"valid":"bool", "hit_depth":"float", "hit_uv":"Vector2", "hit_xz":"Vector2"}),
    "wet_step": (dict(GRID, wetness="float[Nz,Nx]", depth="float[Nz,Nx]", source="float[Nz,Nx]", dt="float", diffusion="float", lambda0="float", beta="float"),
                 {"wetness_field":"float", "drying_rate_field":"float"}),
    "cloud_query": (dict(CLOUD, points="Vector3[N]"), {"valid_interval":"bool", "s0":"float", "s1":"float", "optical_depth":"float", "transmittance":"float"}),
    "fog_query": (dict(CLOUD, view_rays="Tuple[ox:float,oy:float,oz:float,dx:float,dy:float,dz:float,opaque_distance:float][N]", light_rgb="Vector3", fog_min="Vector3", fog_max="Vector3", fog_density="float", fog_scatter="float", fog_absorb="float", g="float", view_steps="int"),
                  {"phase":"float", "L_scatter":"Vector3", "T_view":"float", "T_cloud_at_samples":"float[Nv]", "T_fog_light":"float[Nv]"}),
    "flow_query": (dict(GRID, uvs="Vector2[N]", flow="Vector2[Nz,Nx]", time="float", period="float", phase="float", tiling="float", texture_size="Vector2i", color_texture="Vector3[H,W]", normal_texture="Vector3[H,W]", normal_encoded="bool"),
                   {"uv_phase0":"Vector2", "uv_phase1":"Vector2", "weight0":"float", "weight1":"float", "sampled_color":"Vector3", "blended_normal":"Vector3"}),
    "foam_step": (dict(GRID, foam="float[Nz,Nx]", flow="Vector2[Nz,Nx]", sources="Tuple[x:float,z:float,radius:float,rate:float][N]", dt="float", decay="float"), {"foam_field":"float", "source_field":"float"}),
    "optics_query": ({"optical_rays":"Tuple[Ix:float,Iy:float,Iz:float,Nx:float,Ny:float,Nz:float,x:float,y:float,z:float][N]", "eta_i":"float", "eta_t":"float", "ell":"float", "sigma_a":"Vector3", "view_projection":"Matrix4", "texture_size":"Vector2i", "color_texture":"Vector3[H,W]", "reflection_color":"Vector3", "fallback_color":"Vector3"},
                     {"F":"float", "Tdir":"Vector3", "R":"Vector3", "A":"Vector3", "has_transmission":"bool", "background_uv":"Vector2", "valid":"bool", "color":"Vector3"}),
    "wave_step": (dict(GRID, height="float[Nz,Nx]", height_prev="float[Nz,Nx]", force="float[Nz,Nx]", dt="float", wave_speed="float", gamma="float"), {"height":"float"}),
    "wave_normal_query": (dict(GRID, height="float[Nz,Nx]"), {"normal":"Vector3"}),
}
CHAIN_QUERIES = {
    "A": (["burn_query"], ["curl_query", "particle_step"]),
    "B": (["stamp_query", "pom_query"], ["wet_step"]),
    "C": (["cloud_query"], ["fog_query"]),
    "D": (["flow_query"], ["foam_step"]),
    "E": (["optics_query"], ["wave_step", "wave_normal_query"]),
}
SCENE_TYPES = {
    "A_L3": ({"object_id":"String", "points_ref":"Vector3[N]", "time":"float", "instance_transform":"Matrix4", "anchors":"Tuple[position:Vector3,normal:Vector3][N]"},
             {"burn_state":"Dictionary[String,GPUField]", "emitter_history":"Array[Dictionary{object_id:String,anchor_id:int,birth_time:float}]", "particle_state":"Dictionary[String,GPUField]", "display_resources":"Dictionary[String,Resource]"}),
    "B_L3": ({"surface_points":"Vector3[N]", "material_weights":"float[N,L]", "allowed_layers":"Array[int]", "tau_allow":"float", "chart":"Dictionary", "events":"Array[Dictionary]"},
             {"effective_allowed_weight":"GPUField", "support_domain":"GPUField", "depth_field":"GPUField", "wetness_field":"GPUField"}),
    "C_L3_R": ({"uvw":"Vector3[N]", "U":"Texture3D", "V":"Texture2D", "density_parameters":"Dictionary[String,float]", "cloud_bounds":"AABB", "fog_bounds":"AABB", "camera":"Camera3D", "time":"float"},
               {"density_resource_query":"GPUField", "rho_grid":"GPUField", "source_resources":"Dictionary[String,Resource]", "source_hash":"String"}),
    "C_L3_S": ({"world_points":"Vector3[N]", "source_transform":"Matrix4", "source_time":"float", "source_tick":"int", "camera":"Camera3D"},
               {"native_cloud_samples":"GPUField", "rho_grid":"GPUField", "source_tick":"int", "source_time":"float", "source_version":"String"}),
    "D_L3": ({"contact_world_positions":"Vector3[N]", "surface_transform":"Matrix4", "surface_axes":"Array[Vector3]", "physical_flow":"Vector2[Nz,Nx]", "sources":"Array[Dictionary]", "dt":"float"},
             {"projected_source_coordinates":"Vector2[N]", "projected_source_valid":"bool[N]", "surface_chart":"Dictionary", "source_field":"GPUField", "foam_field":"GPUField", "flow_uv":"GPUField"}),
    "E_L3": ({"surface_transform":"Matrix4", "base_normal":"Texture2D", "wave_events":"Array[Dictionary]", "front_background":"Texture2D", "water_background":"Texture2D", "camera":"Camera3D", "tick":"int"},
             {"wave_height":"GPUField", "wave_normal":"GPUField", "composed_normal":"GPUField", "front_input":"Texture2D", "water_input":"Texture2D", "capture_tick":"int", "capture_camera":"Dictionary"}),
}


def io_schema(task):
    low, high = CHAIN_QUERIES[task[0]]
    names = low if task.endswith("L1") else low + high
    schema = {
        "kind": "input_output_types",
        "query_input": "query(name:String, payload:Dictionary)",
        "state_input": ["reset(config:Dictionary)", "advance(dt:float, events:Array[Dictionary])"],
        "query_output": "Dictionary{status:String, device:RenderingDevice, buffer:RID, shape:Array[int], fields:Array[String]}",
        "texture_output": "Dictionary{status:String, texture:Texture2D, shape:Array[int], fields:Array[String]}",
        "state_output": "get_outputs() -> Dictionary[String,Variant]",
        "layout": {"scalar_storage":"float32", "vector_storage":"Array[float]", "matrix_storage":"column-major Array[float]", "grid_axes":"[Nz,Nx], X fastest", "volume_axes":"[Nz,Ny,Nx], X fastest", "dimensions":"N,Nx,Ny,Nz,H,W,L,Nv are symbolic dimensions"},
        "queries": {name:{"input":deepcopy(QUERIES[name][0]), "output_fields":deepcopy(QUERIES[name][1])} for name in names},
    }
    if task in SCENE_TYPES:
        schema["scene_input"] = deepcopy(SCENE_TYPES[task][0])
        schema["scene_output"] = deepcopy(SCENE_TYPES[task][1])
    return schema


def schema_markdown(task):
    schema = io_schema(task)
    rows = ["输入接口：`query(name: String, payload: Dictionary)`；状态输入：`reset(config: Dictionary)`、`advance(dt: float, events: Array[Dictionary])`。",
            "", "查询输出类型：`"+schema["query_output"]+"`，或 `"+schema["texture_output"]+"`。状态输出：`get_outputs() -> Dictionary[String, Variant]`。",
            "", "标量存储类型为 float32，向量为浮点数组，矩阵为列主序浮点数组；N、Nx、Ny、Nz、H、W、L、Nv 为尺寸符号。二维场按 Z、X 排列，三维场按 Z、Y、X 排列，X 维最快。",
            "", "| 查询 | 输入字段与类型 | 输出字段与类型 |", "| --- | --- | --- |"]
    fmt = lambda fields: "；".join(f"`{name}: {kind}`" for name,kind in fields.items())
    for name,entry in schema["queries"].items():
        rows.append(f"| `{name}` | {fmt(entry['input'])} | {fmt(entry['output_fields'])} |")
    if "scene_input" in schema:
        rows += ["", "场景输入类型："+fmt(schema["scene_input"])+"。", "", "场景输出类型："+fmt(schema["scene_output"])+"。"]
    return "\n".join(rows)
