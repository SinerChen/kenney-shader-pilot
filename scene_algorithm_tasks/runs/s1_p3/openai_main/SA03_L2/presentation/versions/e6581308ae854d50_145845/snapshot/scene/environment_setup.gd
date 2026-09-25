extends RefCounted
## Select original scene content and forward fixed inputs; no effect algorithm here.
var host: Node
var settings: Dictionary
var inputs: Dictionary
var candidate: Node
var elapsed := 0.0
var report: Dictionary

func configure(root: Node, config: Dictionary, fixed_input: Dictionary) -> void:
	host = root
	settings = config
	inputs = fixed_input
	report = {"host": "existing_project", "scope": settings.scope, "level": settings.level,
		"geometry_before": geometry_count(), "source_host_modified": false}
	match settings.kind:
		"grass": setup_grass()
		"water": setup_water()
		"bistro": setup_bistro()
		"fps": setup_fps()
		"forest": setup_forest()
	report.geometry_after = geometry_count()
	report.targets = settings.targets
	candidate = load("res://effect/main.gd").new()
	candidate.name = "CandidateEffect"
	host.add_child(candidate)
	candidate.configure(host, inputs.duplicate(true))

func geometry_count() -> Dictionary:
	var meshes := 0
	var instances := 0
	for node in host.find_children("*", "GeometryInstance3D", true, false):
		if node.is_visible_in_tree():
			meshes += 1
			if node is MultiMeshInstance3D and node.multimesh:
				instances += node.multimesh.instance_count
	return {"visible_geometry": meshes, "multimesh_instances": instances}

func show_node(path: String, value: bool) -> void:
	var node := host.get_node_or_null(path)
	if node is Node3D or node is CanvasItem or node is CanvasLayer:
		node.visible = value

func setup_grass() -> void:
	host.level = 3  # Existing host's interaction/player branch, independent of task level.
	host.manual_step = true
	host.manual_player = true
	host.reset()
	host.set_parameters({"wind_strength": inputs.wind.strength, "wind_speed": inputs.wind.speed,
		"wind_direction": inputs.wind.direction_xz})
	if int(settings.level) < 3:
		var z_limit := 0.12 if int(settings.level) == 1 else 0.62
		for node in host.grass_nodes:
			var original: MultiMesh = node.multimesh
			var selected: Array[int] = []
			for index in original.instance_count:
				if absf(original.get_instance_transform(index).origin.z + 0.2) <= z_limit:
					selected.append(index)
			var subset := MultiMesh.new()
			subset.transform_format = MultiMesh.TRANSFORM_3D
			subset.use_custom_data = true
			subset.mesh = original.mesh
			subset.instance_count = selected.size()
			for index in selected.size():
				subset.set_instance_transform(index, original.get_instance_transform(selected[index]))
				subset.set_instance_custom_data(index, original.get_instance_custom_data(selected[index]))
			node.multimesh = subset
		host.hud.visible = false
	set_grass_player(0.0)

func set_grass_player(time: float) -> void:
	var keys: Array = inputs.player_keyframes
	var position: Array = keys[-1].position_xz_m
	for i in range(keys.size()-1):
		if time <= float(keys[i+1].time_s):
			var alpha := clampf((time-float(keys[i].time_s))/(float(keys[i+1].time_s)-float(keys[i].time_s)),0,1)
			position = [lerpf(keys[i].position_xz_m[0],keys[i+1].position_xz_m[0],alpha), lerpf(keys[i].position_xz_m[1],keys[i+1].position_xz_m[1],alpha)]
			break
	host.set_parameters({"player_position": [position[0],0,position[1]]})
	host.interaction_strength = float(inputs.interaction.strength) if time <= float(inputs.interaction_active_until_s) else 0.0

func setup_water() -> void:
	var ocean = host.get_node("DeepOcean")
	# Keep native material/LOD generation; start target waves and foam unsolved.
	ocean.material = ocean.material.duplicate()
	var designer = ocean.get_node("WaterMaterialDesigner")
	designer.material = ocean.material
	designer.update_when_camera_far_changes = false
	designer.height_waves.clear()
	designer.foam_waves.clear()
	designer._update_wave_params()
	ocean._apply_material()
	if int(settings.level) < 3:
		# Use the original host's mesh generator for a compact 8 m center tile.
		ocean.levels_of_detail = int(settings.level)
		ocean.outermost_resolution = 64 if int(settings.level) == 1 else 32
		ocean.unit_size = 0.125
		ocean.build_meshes()
		for child in ocean.get_children():
			if child is MeshInstance3D and str(child.name).begins_with("_gen"):
				child.visible = child.name == "_gen_nearplane_0_0" if int(settings.level) == 1 else str(child.name).begins_with("_gen_nearplane") and child.position.length() < ocean.region_width * 1.5
		show_node("VisibilityRangeLodGroup", false)
		show_node("DeepOcean/OceanFloor", int(settings.level) == 2)
		show_node("HUD", false)

func setup_bistro() -> void:
	if int(settings.level) == 3:
		return
	for child in host.get_node("Level Geometry").get_children():
		child.visible = child.name == "Ground" or int(settings.level) == 2 and child.name == "Section01"
	for path in ["Props", "Foliage Areas", "Patches"]:
		show_node(path, false)
	# Original UI/light references remain valid; only their display is hidden.
	show_node("UI", false)
	if int(settings.level) == 1:
		show_node("Human-For-Scale", false)

func setup_fps() -> void:
	host.playing = false
	host.scripted = false
	host.set_process(false)
	host.set_parameters({"level": int(settings.level)})
	if int(settings.level) < 3:
		var allowed := ["Foundation", "TargetA"]
		if int(settings.level) == 2:
			allowed.append_array(["TargetB", "Cover"])
		for child in host.get_node("World").get_children():
			if child is Node3D:
				child.visible = str(child.name) in allowed
		show_node("HUD", false)

func setup_forest() -> void:
	# Disable the replaceable built-in fog; the original sky/cloud shader is retained.
	var environment: Environment = host.get_node("WorldEnvironment").environment.duplicate()
	environment.fog_enabled = false
	environment.volumetric_fog_enabled = false
	host.get_node("WorldEnvironment").environment = environment
	if int(settings.level) == 3:
		return
	var origin: Vector3 = host.get_node("Camera3D").global_position
	var radius := 35.0 if int(settings.level) == 1 else 60.0
	for child in host.get_node("Decorations-Forest").get_children():
		if child is Node3D:
			child.visible = distance_to_geometry(child, origin) <= radius and (int(settings.level) == 2 or "rock" in str(child.name).to_lower())
	var vegetation: Array = []
	for node in host.get_node("Groundcover").find_children("*", "MultiMeshInstance3D", true, false):
		if node.is_visible_in_tree():
			vegetation.append({"node": node, "distance": distance_to_geometry(node, origin)})
		node.visible = false
	vegetation.sort_custom(func(a, b): return a.distance < b.distance)
	if int(settings.level) == 2:
		for item in vegetation.slice(0, 12):
			item.node.visible = true
		report.nearest_groundcover_distance = vegetation[0].distance if not vegetation.is_empty() else -1.0
		# Start the interaction view near an actual retained plant, using its original transform.
		var closest := INF
		var focus := origin
		for item in vegetation.slice(0, 12):
			var plant: MultiMeshInstance3D = item.node
			for index in plant.multimesh.instance_count:
				var position: Vector3 = plant.global_transform * plant.multimesh.get_instance_transform(index).origin
				if position.distance_to(origin) < closest:
					closest = position.distance_to(origin)
					focus = position + Vector3.UP * 0.4
		if closest < INF:
			var camera: Camera3D = host.get_node("Camera3D")
			camera.global_position = focus + Vector3(3.5,2.2,4.5)
			camera.look_at(focus)
			report.plant_focus = [focus.x, focus.y, focus.z]

func distance_to_geometry(node: Node3D, origin: Vector3) -> float:
	var distance := INF
	var meshes: Array[Node] = node.find_children("*", "GeometryInstance3D", true, false)
	if node is GeometryInstance3D:
		meshes.append(node)
	for mesh in meshes:
		var bounds: AABB = mesh.global_transform * mesh.get_aabb()
		var nearest := Vector3(clampf(origin.x,bounds.position.x,bounds.end.x),
			clampf(origin.y,bounds.position.y,bounds.end.y), clampf(origin.z,bounds.position.z,bounds.end.z))
		distance = minf(distance, nearest.distance_to(origin))
	return distance

func step(dt: float) -> void:
	elapsed += dt
	if settings.kind == "grass":
		set_grass_player(elapsed)
		host.step(dt)
	elif settings.kind == "fps":
		host.step(dt)
		if inputs.has("target_motion"):
			var target := host.get_node("World/TargetA") as Node3D
			var speed: Array = inputs.target_motion.translation_m_s
			target.position += Vector3(speed[0],speed[1],speed[2]) * dt
			target.rotation.y += deg_to_rad(float(inputs.target_motion.yaw_degrees_s)) * dt
	candidate.step(dt)

func sample() -> Dictionary:
	return candidate.sample()
