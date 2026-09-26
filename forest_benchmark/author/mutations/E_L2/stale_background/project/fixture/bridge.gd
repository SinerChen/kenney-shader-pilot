extends Node3D

var task: Dictionary
var demo: Dictionary
var adapter: Node
var stage: Node3D
var effect_root: Node3D
var camera: Camera3D
var capture_views: Dictionary = {}
var tick = 0
var startup: Dictionary = {}
var baseline: Dictionary = {}
var bindings: Dictionary = {}

func _ready():
	task = JSON.parse_string(FileAccess.get_file_as_string("res://public/task.json"))
	demo = JSON.parse_string(FileAccess.get_file_as_string("res://public/demo.json"))
	stage = get_node("Stage")
	effect_root = get_node("EffectRoot")
	camera = stage.get_node("CameraRig/Camera3D")
	if task.task_id.begins_with("E"): _create_capture_views()
	baseline = snapshot()
	adapter = load("res://solution/adapter.gd").new()
	effect_root.add_child(adapter)
	startup = adapter.reset(demo.config)
	if startup.get("status","") == "OK": startup = adapter.mount(self)
	set_process(not get_tree().root.has_meta("benchmark_manual"))

func _create_capture_views():
	# One shared world; cull masks separate opaque, rear water and foreground.
	# These passes contain only scene organization, never optical/wave math.
	for name in ["OpaqueCapture","RearCapture"]:
		var view = SubViewport.new()
		view.name = name
		view.size = Vector2i(640,360)
		view.world_3d = get_world_3d()
		view.render_target_update_mode = SubViewport.UPDATE_ONCE
		add_child(view)
		var cam = Camera3D.new()
		cam.name = "Camera3D"
		view.add_child(cam)
		cam.global_transform = camera.global_transform
		cam.fov = camera.fov
		cam.near = camera.near
		cam.far = camera.far
		cam.cull_mask = 1 if name == "OpaqueCapture" else 3
		cam.current = true
		capture_views[name] = view

func set_capture_size(size: Vector2i):
	for view in capture_views.values(): view.size=size
	baseline=snapshot()

func sync_cameras():
	for view in capture_views.values():
		var cam = view.get_node("Camera3D")
		cam.global_transform=camera.global_transform
		cam.fov=camera.fov
		cam.near=camera.near
		cam.far=camera.far

func background(consumer: String) -> Texture2D:
	var name = "OpaqueCapture" if consumer == "rear" else "RearCapture"
	return capture_views[name].get_texture() if capture_views.has(name) else null

func bind_material(target: String, material: Material) -> Dictionary:
	if target not in task.authorized_runtime_bindings:
		return {"status":"ERROR","error":"Target is not authorized: "+target}
	var node = stage.get_node_or_null(target)
	if not node is MeshInstance3D:
		return {"status":"ERROR","error":"Target is not a MeshInstance3D"}
	node.material_override=material
	bindings[target]=material
	return {"status":"OK"}

func add_effect(node: Node3D) -> Dictionary:
	if node.get_parent() != null: return {"status":"ERROR","error":"Effect already has a parent"}
	effect_root.add_child(node)
	return {"status":"OK"}

func _process(_dt):
	if startup.get("status","") != "OK": return
	var events: Array = []
	for event in demo.events:
		if int(event.tick)==tick: events.append(event.event)
	adapter.advance(float(demo.dt),events)
	adapter.update_display()
	sync_cameras()
	tick+=1

func snapshot() -> Dictionary:
	var result = {}
	var nodes: Array = [stage]
	while not nodes.is_empty():
		var node = nodes.pop_back()
		nodes.append_array(node.get_children())
		var path = str(stage.get_path_to(node))
		var data = {"class":node.get_class()}
		if node is Node3D:
			data.transform=var_to_str(node.transform)
			data.visible=node.visible
		if node is MeshInstance3D:
			data.mesh_id=node.mesh.get_instance_id() if node.mesh else 0
			data.layers=node.layers
			data.mesh_aabb=var_to_str(node.mesh.get_aabb())
			var mesh_data=var_to_bytes(node.mesh.surface_get_arrays(0))
			var digest=HashingContext.new()
			digest.start(HashingContext.HASH_SHA256)
			digest.update(mesh_data)
			data.mesh_hash=digest.finish().hex_encode()
			if path not in task.authorized_runtime_bindings:
				data.material=var_to_str(node.get_active_material(0))
				var material=node.get_active_material(0)
				if material is BaseMaterial3D:
					data.albedo=var_to_str(material.albedo_color)
					data.roughness=material.roughness
					data.texture=var_to_str(material.albedo_texture)
		if node is Camera3D:
			data.fov=node.fov
			data.near=node.near
			data.far=node.far
			data.cull_mask=node.cull_mask
		if node is Light3D:
			data.energy=node.light_energy
			data.color=var_to_str(node.light_color)
			data.cull_mask=node.light_cull_mask
			data.shadows=node.shadow_enabled
		if node is WorldEnvironment:
			var env=node.environment
			data.background=var_to_str(env.background_color)
			data.ambient_energy=env.ambient_light_energy
			data.tonemap=env.tonemap_mode
			data.exposure=env.tonemap_exposure
		result[path]=data
	for name in capture_views:
		var view=capture_views[name]
		result["capture/"+name]={"size":var_to_str(view.size),"mask":view.get_node("Camera3D").cull_mask,"camera":var_to_str(view.get_node("Camera3D").global_transform),"mode":view.render_target_update_mode}
	return result

func protection_report() -> Dictionary:
	var after = snapshot()
	var changed: Array = []
	for path in baseline:
		if not after.has(path) or baseline[path] != after[path]: changed.append(path)
	for path in after:
		if not baseline.has(path): changed.append(path)
	return {"status":"PASS" if changed.is_empty() else "FAIL","changed_paths":changed,"baseline":baseline,"actual":after}

func _exit_tree():
	if is_instance_valid(adapter):adapter.dispose()
