extends "res://fixture/adapter_base.gd"

var rd: RenderingDevice
var shader: RID
var pipeline: RID
var owned: Array[RID] = []
var config: Dictionary = {}
var state: Dictionary = {}
var emitted: Dictionary = {}
var processed: Dictionary = {}
var births: Array = []
var particle_ids: Array = []
var keys: Array = []
var operation_fields: Dictionary = {}
var opcodes: Dictionary = {}
var query_rows: Dictionary = {}
var fields_by_operation: Dictionary = {}
var task_id = ""
var simulation_time = 0.0
var display = null

func _ready():
	pass

func _ensure_device():
	if rd != null: return true
	rd = RenderingServer.create_local_rendering_device()
	if rd == null: return false
	var meta = JSON.parse_string(FileAccess.get_file_as_string("res://solution/wire.json"))
	keys = meta.keys_order
	operation_fields = meta.operations
	opcodes = meta.opcodes
	query_rows = meta.query_rows
	fields_by_operation = meta.fields_by_operation
	var source = RDShaderSource.new()
	source.source_compute = FileAccess.get_file_as_string("res://solution/kernel.txt")
	var spirv = rd.shader_compile_spirv_from_source(source)
	if spirv.compile_error_compute != "":
		push_error(spirv.compile_error_compute)
		return false
	shader = rd.shader_create_from_spirv(spirv)
	pipeline = rd.compute_pipeline_create(shader)
	return pipeline.is_valid()

func reset(p: Dictionary) -> Dictionary:
	if not _ensure_device(): return {"status":"INFRA_ERROR","error":"GPU compute unavailable"}
	for rid in owned:
		if rid.is_valid(): rd.free_rid(rid)
	owned.clear()
	state.clear()
	emitted.clear()
	processed.clear()
	births.clear()
	particle_ids.clear()
	config = JSON.parse_string(FileAccess.get_file_as_string("res://solution/defaults.json"))
	config.merge(p,true)
	task_id = str(config.get("task_id","A_L1"))
	simulation_time = float(config.t0)
	config.time = simulation_time
	_reset_fields()
	return {"status":"OK"}

func _reset_fields():
	state.depth_field=_dispatch("stamp_query",{"contacts":[]})

func _flat(value, target: Array):
	if value is Array or value is PackedFloat32Array:
		for item in value: _flat(item,target)
	elif value is bool: target.append(1.0 if value else 0.0)
	else: target.append(float(value))

func _dispatch(name: String, values: Dictionary) -> Dictionary:
	if not operation_fields.has(name): return {"status":"ERROR","error":"unknown query: "+name}
	var p = config.duplicate()
	p.merge(values,true)
	if name == "stamp_query":
		var ids: Dictionary = {}
		var remapped: Array = []
		for contact in p.contacts:
			var row = contact.duplicate()
			var key = var_to_str(row[0])
			if not ids.has(key): ids[key] = ids.size()
			row[0] = ids[key]
			remapped.append(row)
		p.contacts = remapped
	p.contact_count = p.contacts.size()
	p.source_count = p.sources.size()
	var count = int(p.grid_size[0])*int(p.grid_size[1])
	if query_rows.has(name): count = p[query_rows[name][0]].size()
	if count == 0: return {"status":"EMPTY","shape":[0,operation_fields[name].size()],"fields":operation_fields[name]}
	var fields: Array = operation_fields[name].duplicate()
	if name == "fog_query":
		for i in int(p.view_steps): fields.append("T_cloud_at_samples."+str(i))
		for i in int(p.view_steps): fields.append("T_fog_light."+str(i))
	var packed: Array = []
	packed.resize(4+keys.size())
	packed.fill(0.0)
	packed[0] = opcodes[name]
	packed[1] = count
	packed[2] = fields.size()
	for k in keys.size():
		if keys[k] not in fields_by_operation[name]: continue
		packed[4+k] = packed.size()
		_flat(p.get(keys[k],0.0),packed)
		if int(packed[4+k]) == packed.size(): packed.append(0.0)
	var bytes = PackedFloat32Array(packed).to_byte_array()
	var input_buffer = rd.storage_buffer_create(bytes.size(),bytes)
	var initial = PackedByteArray()
	initial.resize(count*fields.size()*4)
	var output_buffer = rd.storage_buffer_create(initial.size(),initial)
	var uniforms: Array[RDUniform] = []
	for binding in 2:
		var uniform = RDUniform.new()
		uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
		uniform.binding = binding
		uniform.add_id(input_buffer if binding == 0 else output_buffer)
		uniforms.append(uniform)
	var set_id = rd.uniform_set_create(uniforms,shader,0)
	var list = rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(list,pipeline)
	rd.compute_list_bind_uniform_set(list,set_id,0)
	rd.compute_list_dispatch(list,ceili(float(count)/64.0),1,1)
	rd.compute_list_end()
	rd.submit()
	rd.sync()
	rd.free_rid(set_id)
	rd.free_rid(input_buffer)
	owned.append(output_buffer)
	return {"status":"OK","device":rd,"buffer":output_buffer,"shape":[count,fields.size()],"fields":fields,"time":simulation_time,"origin":"gpu_storage_buffer"}

func _values(resource: Dictionary) -> Array:
	if resource.get("status","") == "EMPTY": return []
	if not resource.has("buffer"): return []
	var a = rd.buffer_get_data(resource.buffer).to_float32_array()
	var out: Array = []
	var width = int(resource.shape[1])
	for i in int(resource.shape[0]): out.append(Array(a.slice(i*width,(i+1)*width)))
	return out

func _column(resource: Dictionary,index: int) -> Array:
	var out: Array = []
	var data = rd.buffer_get_data(resource.buffer).to_float32_array()
	for i in int(resource.shape[0]): out.append(data[i*int(resource.shape[1])+index])
	return out

func query(name: String, payload: Dictionary = {}) -> Dictionary:
	if name == "state":
		return get_outputs()
	return _dispatch(name,payload)

func advance(dt: float, events: Array) -> Dictionary:
	config.time=simulation_time
	config.dt=dt
	var contacts: Array=[]
	for event in events:
		if event.get("type","")=="set":
			config.merge(event.values,true)
			continue
		var id=str(event.get("event_id",""))
		if id=="" or processed.has(id):continue
		processed[id]=true
		if event.type=="contact":contacts.append(event.contact)
	var d=_column(state.depth_field,0) if state.has("depth_field") else config.depth
	state.depth_field=_dispatch("stamp_query",{"depth":d,"contacts":contacts})
	simulation_time+=dt
	config.time=simulation_time
	return {"status":"OK","time":simulation_time}

func get_outputs() -> Dictionary:
	var out = state.duplicate()
	out["status"] = "OK"
	out["simulation_time"] = simulation_time
	out["birth_log"] = births.duplicate(true)
	out["particle_ids"] = particle_ids.duplicate()
	var emitted_ids = emitted.keys()
	emitted_ids.sort()
	out["emitted"] = emitted_ids
	return out

func mount(owner_bridge: Node) -> Dictionary:
	if display != null:
		if is_instance_valid(display.particle_mesh): display.particle_mesh.queue_free()
		display.queue_free()
	display = load("res://solution/display.gd").new()
	add_child(display)
	display.setup(self,owner_bridge)
	return {"status":"OK"}

func update_display() -> void:
	if display != null: display.update()

func dispose():
	if display != null: display.queue_free()
	if rd == null: return
	for rid in owned:
		if rid.is_valid(): rd.free_rid(rid)
	owned.clear()
	if pipeline.is_valid(): rd.free_rid(pipeline)
	if shader.is_valid(): rd.free_rid(shader)
	rd.free()
	rd = null
