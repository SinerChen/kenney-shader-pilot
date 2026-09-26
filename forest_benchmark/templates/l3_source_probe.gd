extends SceneTree

var resources: Dictionary = {}
var meshes: Array = []
var cameras: Array = []
var environments: Array = []
var lights: Array = []
var count := 0

func vec(v: Vector3) -> Array:
	return [v.x,v.y,v.z]

func xform(t: Transform3D) -> Array:
	return [vec(t.basis.x),vec(t.basis.y),vec(t.basis.z),vec(t.origin)]

func resource_info(r):
	if r==null:return null
	var key=r.resource_path if r.resource_path!="" else "instance:"+str(r.get_instance_id())
	if resources.has(key):return key
	var info={"class":r.get_class(),"path":r.resource_path}
	resources[key]=info
	if r is ShaderMaterial:
		info.shader=resource_info(r.shader)
		info.uniforms={}
		if r.shader:
			for u in r.shader.get_shader_uniform_list():
				var value=r.get_shader_parameter(u.name)
				if value is Resource:info.uniforms[u.name]={"resource":resource_info(value)}
				elif value is Vector2:info.uniforms[u.name]=[value.x,value.y]
				elif value is Vector3:info.uniforms[u.name]=vec(value)
				else:info.uniforms[u.name]=str(value)
	elif r is Texture3D:
		info.dimensions=[r.get_width(),r.get_height(),r.get_depth()]
		info.format=r.get_format()
	elif r is Texture2D:
		info.dimensions=[r.get_width(),r.get_height()]
	elif r is TextureLayered:
		info.dimensions=[r.get_width(),r.get_height(),r.get_layers()]
		info.format=r.get_format()
	return key

func walk(node: Node, scene: Node):
	count+=1
	var path=str(scene.get_path_to(node))
	if node is MeshInstance3D or node is MultiMeshInstance3D:
		var mesh=node.mesh if node is MeshInstance3D else (node.multimesh.mesh if node.multimesh else null)
		var materials: Array=[]
		if mesh:
			for i in mesh.get_surface_count():
				var material=node.get_active_material(i) if node is MeshInstance3D else (node.material_override if node.material_override else mesh.surface_get_material(i))
				materials.append({"surface":i,"active_material":resource_info(material)})
		var row={"path":path,"class":node.get_class(),"scene_file":node.scene_file_path,"transform":xform(node.global_transform),"visible":node.visible,"layers":node.layers,
			"lod_begin":node.visibility_range_begin,"lod_end":node.visibility_range_end,"lod_fade_mode":node.visibility_range_fade_mode,
			"mesh":resource_info(mesh),"materials":materials,"material_override":resource_info(node.material_override)}
		if mesh:row.aabb=[vec(mesh.get_aabb().position),vec(mesh.get_aabb().size)]
		if node is MultiMeshInstance3D:
			row.instance_count=node.multimesh.instance_count if node.multimesh else 0
		meshes.append(row)
	if node is Camera3D:cameras.append({"path":path,"transform":xform(node.global_transform),"fov":node.fov,"near":node.near,"far":node.far,"current":node.current,"cull_mask":node.cull_mask})
	if node is DirectionalLight3D:lights.append({"path":path,"transform":xform(node.global_transform),"energy":node.light_energy,"color":str(node.light_color)})
	if node is WorldEnvironment:
		var e=node.environment
		environments.append({"path":path,"environment":resource_info(e),"sky_material":resource_info(e.sky.sky_material) if e and e.sky else null})
	for child in node.get_children():walk(child,scene)

func _initialize():
	call_deferred("run")

func run():
	var out=OS.get_cmdline_user_args()[0]
	root.size=Vector2i(640,360)
	var scene=load("res://Main.tscn").instantiate()
	root.add_child(scene)
	for frame in 8:
		await process_frame
		await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(out.path_join("baseline.png"))
	walk(scene,scene)
	var result={"status":"RUNTIME_ENUMERATED","node_count":count,"meshes":meshes,"resources":resources,"cameras":cameras,"environments":environments,"lights":lights,
		"engine":Engine.get_version_info(),"gpu":RenderingServer.get_video_adapter_name(),"taa":root.use_taa,"occlusion":root.use_occlusion_culling}
	var f=FileAccess.open(out.path_join("result.json"),FileAccess.WRITE)
	f.store_string(JSON.stringify(result,"  "))
	scene.queue_free()
	await process_frame
	quit()
