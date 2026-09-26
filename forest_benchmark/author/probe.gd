extends SceneTree

func _initialize():
	call_deferred("run")

func run():
	var rd = RenderingServer.create_local_rendering_device()
	if rd == null:
		push_error("No RenderingDevice")
		quit(2)
		return
	var source = RDShaderSource.new()
	source.source_compute = "#version 450\nlayout(local_size_x=1) in; layout(set=0,binding=0,std430) buffer Out {float v[];}; void main(){v[0]=1.25; v[1]=-3.5; v[2]=exp(-2.0); v[3]=0.000125;}"
	var spirv = rd.shader_compile_spirv_from_source(source)
	if spirv.compile_error_compute != "":
		push_error(spirv.compile_error_compute)
		quit(3)
		return
	var shader = rd.shader_create_from_spirv(spirv)
	var buffer = rd.storage_buffer_create(16, PackedFloat32Array([0,0,0,0]).to_byte_array())
	var uniform = RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	uniform.binding = 0
	uniform.add_id(buffer)
	var set_id = rd.uniform_set_create([uniform], shader, 0)
	var pipe = rd.compute_pipeline_create(shader)
	var list = rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(list, pipe)
	rd.compute_list_bind_uniform_set(list, set_id, 0)
	rd.compute_list_dispatch(list, 1, 1, 1)
	rd.compute_list_end()
	rd.submit()
	rd.sync()
	var values = rd.buffer_get_data(buffer).to_float32_array()
	var result = {"values":Array(values),"engine":Engine.get_version_info(),"gpu":RenderingServer.get_video_adapter_name(),"vendor":RenderingServer.get_video_adapter_vendor(),"status":"GPU_READBACK_OBSERVED"}
	var f=FileAccess.open("res://probe_result.json",FileAccess.WRITE)
	f.store_string(JSON.stringify(result,"  "))
	for rid in [set_id,pipe,buffer,shader]: rd.free_rid(rid)
	rd.free()
	quit()

