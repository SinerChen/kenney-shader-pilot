extends SceneTree

var snapshots: Dictionary={}

func fingerprint_resource(r):
	if r==null:return null
	var text=r.get_class()+":"+r.resource_path+":"+str(r.get_instance_id())
	if r is ShaderMaterial:
		text+=r.shader.code
		for u in r.shader.get_shader_uniform_list():text+=str(u.name)+str(r.get_shader_parameter(u.name))
	return text.sha256_text()

func scan(node: Node, root_node: Node, rows: Dictionary):
	var values=[node.get_class()]
	if node is Node3D:values.append_array([node.transform,node.visible])
	if node is GeometryInstance3D:
		values.append_array([node.layers,node.visibility_range_begin,node.visibility_range_end,node.visibility_range_fade_mode])
		values.append(fingerprint_resource(node.material_override))
	if node is MeshInstance3D:
		values.append(fingerprint_resource(node.mesh))
		for s in node.mesh.get_surface_count():values.append(fingerprint_resource(node.get_active_material(s)))
	if node is Camera3D:values.append_array([node.fov,node.near,node.far,node.cull_mask,node.current])
	if node is Light3D:values.append_array([node.light_energy,node.light_color,node.shadow_enabled])
	if node is WorldEnvironment:
		values.append(fingerprint_resource(node.environment))
		if node.environment and node.environment.sky:values.append(fingerprint_resource(node.environment.sky.sky_material))
	rows[str(root_node.get_path_to(node))]=str(values).sha256_text()
	for child in node.get_children():scan(child,root_node,rows)

func snapshot(source: Node) -> Dictionary:
	var rows={}
	scan(source,source,rows)
	return rows

func _initialize():
	root.set_meta("benchmark_manual",true)
	root.set_meta("benchmark_defer_binding",true)
	call_deferred("run")

func run():
	var args=OS.get_cmdline_user_args()
	var request=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var out=args[1]
	root.size=Vector2i(640,360)
	var fixture=load("res://fixture/entry.tscn").instantiate()
	root.add_child(fixture)
	await process_frame
	var camera=fixture.access.camera()
	if request.get("camera") != null:
		var c=request.camera
		camera.global_position=Vector3(c.position[0],c.position[1],c.position[2])
		var target=Vector3(c.look_at[0],c.look_at[1],c.look_at[2])
		var direction=(target-camera.global_position).normalized()
		camera.look_at(target,Vector3.RIGHT if abs(direction.dot(Vector3.UP))>0.999 else Vector3.UP)
	var camera_record={"position":camera.global_position,"basis":camera.global_basis,"fov":camera.fov,"requested":request.get("camera")}
	var before=snapshot(fixture.source)
	fixture.bind_scene()
	var frames=[]
	for frame in int(request.get("frames",30)):
		if frame>0:fixture.step(1.0/15.0,[])
		await process_frame
		await RenderingServer.frame_post_draw
		var name="frame_%05d.png" % frame
		root.get_texture().get_image().save_png(out.path_join(name))
		frames.append({"frame":frame,"tick":fixture.tick,"file":name})
	var after=snapshot(fixture.source)
	var changed=[]
	for path in before:
		if before[path]!=after.get(path):changed.append(path)
	fixture.adapter.detach_scene()
	fixture.access.detach_bindings()
	await process_frame
	var detached=snapshot(fixture.source)
	var restored=detached==before
	var result={"status":"NATIVE_STARTER_RENDERED" if fixture.startup.get("status")=="UNIMPLEMENTED_BINDING" else "CANDIDATE_RENDERED",
		"binding":fixture.startup,"frames":frames,"camera":camera_record,"protected_node_count":before.size(),"changed_source_nodes":changed,
		"source_runtime_unchanged":changed.is_empty(),"detach_restored":restored,"effect_present":false,
		"scope":"Blank inherited starter verification only; this is not a positive L3 integration result.",
		"engine":Engine.get_version_info(),"gpu":RenderingServer.get_video_adapter_name()}
	var f=FileAccess.open(out.path_join("result.json"),FileAccess.WRITE)
	f.store_string(JSON.stringify(result,"  "))
	fixture.queue_free()
	await process_frame
	quit()
