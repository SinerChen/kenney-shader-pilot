extends "res://fixture/adapter_base.gd"

const FIELDS = ["noise", "signed_front", "char_fraction", "front_strength"]
var settings: Dictionary = {}
var clock: float = 0.0
var rd: RenderingDevice
var compute_shader: RID
var pipeline: RID
var retained: Array[RID] = []
var latest: Dictionary = {"status":"EMPTY"}
var material: ShaderMaterial
var permutation: Array = []

func defaults() -> Dictionary:
	return {"t0":0.0,"origin_ref":[-0.45,-0.8,0.0],"R0":0.15,"speed":0.3,"noise_amplitude":0.22,"base_frequency":3.0,"octaves":5,"gain":0.5,"lacunarity":2.0,"width":0.07,"enabled":true}

func reset(config: Dictionary) -> Dictionary:
	settings = defaults()
	settings.merge(config,true)
	clock = float(config.get("time",0.0))
	permutation = JSON.parse_string(FileAccess.get_file_as_string("res://assets/noise_permutation.json"))["P"]
	if config.has("P"): permutation = Array(config.P)
	if rd == null:
		rd = RenderingServer.create_local_rendering_device()
		if rd == null: return {"status":"ERROR","error":"RenderingDevice unavailable"}
		var source = RDShaderSource.new()
		source.source_compute = """#version 450
layout(local_size_x=64) in;
layout(set=0,binding=0,std430) readonly buffer Permutation { int perm[]; };
layout(set=0,binding=1,std430) readonly buffer Points { vec4 points[]; };
layout(set=0,binding=2,std430) readonly buffer Parameters { float v[]; };
layout(set=0,binding=3,std430) writeonly buffer Result { vec4 result[]; };
""" + FileAccess.get_file_as_string("res://solution/burn_math.gdshaderinc") + """
void main() {
 uint i=gl_GlobalInvocationID.x;
 if(i>=uint(v[14])) return;
 result[i]=burn_field(points[i].xyz,vec3(v[0],v[1],v[2]),v[3],v[4],v[5],v[6],v[7],v[8],int(v[9]),v[10],v[11],v[12],v[13]>0.5);
}
"""
		var spirv = rd.shader_compile_spirv_from_source(source)
		if not spirv.compile_error_compute.is_empty(): return {"status":"ERROR","error":spirv.compile_error_compute}
		compute_shader = rd.shader_create_from_spirv(spirv)
		pipeline = rd.compute_pipeline_create(compute_shader)
	latest = {"status":"EMPTY"}
	update_display()
	return {"status":"OK"}

func vec(value: Variant) -> Vector3:
	if value is Vector3: return value
	if value is Dictionary: return Vector3(value.get("x",0),value.get("y",0),value.get("z",0))
	if value is Array or value is PackedFloat32Array or value is PackedFloat64Array:
		if value.size() >= 3: return Vector3(value[0],value[1],value[2])
	return Vector3.ZERO

func advance(dt: float, events: Array) -> Dictionary:
	clock += maxf(dt,0.0)
	for event in events:
		if not event is Dictionary: continue
		var values: Dictionary = event.get("config",event.get("params",event))
		for key in defaults():
			if values.has(key): settings[key] = values[key]
		if event.get("type","") in ["ignite","start_burn"]:
			settings.t0 = clock
			settings.enabled = true
		if event.get("type","") in ["disable","stop_burn"]: settings.enabled = false
	update_display()
	return {"status":"OK","time":clock}

func query(name: String, payload: Dictionary = {}) -> Dictionary:
	if name != "burn_query": return {"status":"ERROR","error":"Unknown query: "+name}
	if rd == null:
		var initialized = reset({})
		if initialized.status != "OK": return initialized
	var cfg = settings.duplicate()
	cfg.merge(payload,true)
	var raw = payload.get("points",[])
	var points: Array[Vector3] = []
	if raw.size() > 0 and (raw[0] is float or raw[0] is int):
		for i in range(0,raw.size()-2,3): points.append(Vector3(raw[i],raw[i+1],raw[i+2]))
	else:
		for p in raw: points.append(vec(p))
	if points.is_empty(): return {"status":"EMPTY"}
	var p_data = PackedFloat32Array()
	for p in points: p_data.append_array(PackedFloat32Array([p.x,p.y,p.z,0.0]))
	var p_table = PackedInt32Array(payload.get("P",permutation))
	if p_table.size() < 256: return {"status":"ERROR","error":"P needs 256 entries"}
	var origin = vec(cfg.origin_ref)
	var parameters = PackedFloat32Array([origin.x,origin.y,origin.z,float(cfg.get("time",clock)),float(cfg.t0),float(cfg.R0),float(cfg.speed),float(cfg.noise_amplitude),float(cfg.base_frequency),float(cfg.octaves),float(cfg.gain),float(cfg.lacunarity),float(cfg.width),1.0 if cfg.enabled else 0.0,float(points.size()),0.0])
	var buffers: Array[RID] = [rd.storage_buffer_create(p_table.to_byte_array().size(),p_table.to_byte_array()),rd.storage_buffer_create(p_data.to_byte_array().size(),p_data.to_byte_array()),rd.storage_buffer_create(parameters.to_byte_array().size(),parameters.to_byte_array()),rd.storage_buffer_create(points.size()*16)]
	var uniforms: Array[RDUniform] = []
	for i in range(4):
		var u = RDUniform.new()
		u.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
		u.binding = i
		u.add_id(buffers[i])
		uniforms.append(u)
	var uniform_set = rd.uniform_set_create(uniforms,compute_shader,0)
	var list = rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(list,pipeline)
	rd.compute_list_bind_uniform_set(list,uniform_set,0)
	rd.compute_list_dispatch(list,ceili(points.size()/64.0),1,1)
	rd.compute_list_end()
	rd.submit()
	rd.sync()
	rd.free_rid(uniform_set)
	for i in range(3): rd.free_rid(buffers[i])
	retained.append(buffers[3])
	latest = {"status":"OK","device":rd,"buffer":buffers[3],"shape":[points.size(),4],"fields":FIELDS,"time":float(cfg.get("time",clock))}
	return latest

func get_outputs() -> Dictionary:
	return {"status":"OK","time":clock,"enabled":settings.get("enabled",true),"burn":latest}

func mount(bridge: Node) -> Dictionary:
	material = ShaderMaterial.new()
	material.shader = load("res://solution/wood_burn.gdshader")
	material.set_shader_parameter("wood_base",load("res://assets/wood_base.png"))
	update_display()
	return bridge.bind_material("TargetMesh",material)

func update_display() -> void:
	if material == null: return
	material.set_shader_parameter("perm",PackedInt32Array(permutation))
	material.set_shader_parameter("burn_time",clock)
	for key in defaults():
		material.set_shader_parameter(key,vec(settings[key]) if key == "origin_ref" else settings[key])

func dispose() -> void:
	if rd == null: return
	for rid in retained: rd.free_rid(rid)
	retained.clear()
	if pipeline.is_valid(): rd.free_rid(pipeline)
	if compute_shader.is_valid(): rd.free_rid(compute_shader)
	rd.free()
	rd = null
