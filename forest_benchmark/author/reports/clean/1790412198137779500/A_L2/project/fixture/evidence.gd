extends RefCounted

var directory: String
var counter=0

func record(value):
	if value is Dictionary:
		if value.has("device") and value.has("buffer") and value.device is RenderingDevice:
			counter+=1
			var filename="state_%04d.f32" % counter
			var bytes=value.device.buffer_get_data(value.buffer)
			FileAccess.open(directory.path_join(filename),FileAccess.WRITE).store_buffer(bytes)
			return {"status":"OK","origin":"actual_gpu_readback","file":filename,"shape":value.shape,"fields":value.fields,"dtype":"<f4"}
		var result={}
		for key in value:
			if key not in ["device","buffer","texture"]:result[key]=record(value[key])
		return result
	if value is Array:
		var result: Array=[]
		for item in value:result.append(record(item))
		return result
	if value is Object or value is RID:return str(value)
	return value

func bound_textures(fixture,frame):
	var result={}
	for target in fixture.task.authorized_runtime_bindings:
		var mesh=fixture.stage.get_node(target)
		var material=mesh.get_active_material(0)
		if not material is ShaderMaterial:continue
		var textures={}
		for uniform in material.shader.get_shader_uniform_list():
			var texture=material.get_shader_parameter(uniform.name)
			if not texture is Texture2D:continue
			var image=texture.get_image()
			if image==null:continue
			var prefix="%05d_%s_%s" % [frame,target,uniform.name]
			if texture is ViewportTexture:
				image.save_png(directory.path_join(prefix+".png"))
				textures[uniform.name]={"kind":"viewport","file":prefix+".png","viewport_path":str(texture.viewport_path)}
			else:
				FileAccess.open(directory.path_join(prefix+".bin"),FileAccess.WRITE).store_buffer(image.get_data())
				textures[uniform.name]={"kind":"image","file":prefix+".bin","width":image.get_width(),"height":image.get_height(),"format":image.get_format()}
		result[target]=textures
	return result
