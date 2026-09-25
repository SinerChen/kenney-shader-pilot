extends Node
## Finite-ray exponential height fog; CPU test reference and scene datum are separate.
var scene_root: Node
var test_input: Dictionary = {}
var _sample_cache: Dictionary = {}
var _overlay: MeshInstance3D
var _patched_materials: Dictionary = {}

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs
	# Replace the host's unrelated distance/volumetric fog, not its sky,
	# clouds, lighting, tonemapping or camera controls. Avoid double extinction.
	for node in scene_root.find_children("*", "WorldEnvironment", true, false):
		if node.environment != null:
			var environment: Environment = node.environment.duplicate()
			environment.fog_enabled = false
			environment.volumetric_fog_enabled = false
			node.environment = environment
	_install_plant_coverage()
	_install_screen_fog()
	_sample_cache = _compute_samples()

func _patch_plant(material: Material) -> void:
	if material == null or _patched_materials.has(material.get_instance_id()):
		return
	_patched_materials[material.get_instance_id()] = true
	if material is ShaderMaterial and material.shader != null and material.shader.resource_path.ends_with("/Plant.gdshader"):
		# Runtime resources only; retain source textures, wind and lighting.
		var parameters: Dictionary = {}
		for parameter in material.shader.get_shader_uniform_list():
			parameters[parameter.name] = material.get_shader_parameter(parameter.name)
		material.shader = load("res://effect/plant_depth.gdshader")
		for key in parameters:
			material.set_shader_parameter(key, parameters[key])
	if material.next_pass != null:
		_patch_plant(material.next_pass)

func _install_plant_coverage() -> void:
	for node in scene_root.find_children("*", "GeometryInstance3D", true, false):
		_patch_plant(node.material_override)
		_patch_plant(node.material_overlay)
		var mesh: Mesh = null
		if node is MeshInstance3D:
			mesh = node.mesh
			if mesh != null:
				for surface in mesh.get_surface_count():
					_patch_plant(node.get_surface_override_material(surface))
		elif node is MultiMeshInstance3D and node.multimesh != null:
			mesh = node.multimesh.mesh
		if mesh != null:
			for surface in mesh.get_surface_count():
				_patch_plant(mesh.surface_get_material(surface))

func _install_screen_fog() -> void:
	_overlay = MeshInstance3D.new()
	_overlay.name = "FiniteHeightFog"
	_overlay.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_overlay.extra_cull_margin = 100000.0
	_overlay.ignore_occlusion_culling = true
	var quad := QuadMesh.new()
	quad.size = Vector2(2.0, 2.0)
	_overlay.mesh = quad
	var material := ShaderMaterial.new()
	material.shader = load("res://effect/height_fog.gdshader")
	material.render_priority = 127
	material.set_shader_parameter("density_per_m", float(test_input["density_per_m"]))
	material.set_shader_parameter("height_falloff_per_m", float(test_input["height_falloff_per_m"]))
	var reference := float(test_input["reference_height_m"])
	var camera := get_viewport().get_camera_3d()
	# Capture ONCE; subsequent movement changes rays, never moves the fog layer.
	if test_input.get("scene_density_reference", "") == "initial_camera_world_y" and camera != null:
		reference = camera.global_position.y
	material.set_shader_parameter("reference_height_m", reference)
	var fog: Array = test_input["fog_color_linear"]
	material.set_shader_parameter("fog_color_linear", Vector3(float(fog[0]), float(fog[1]), float(fog[2])))
	_overlay.material_override = material
	add_child(_overlay)
	_follow_camera()

func _follow_camera() -> void:
	var camera := get_viewport().get_camera_3d()
	if camera != null and is_instance_valid(_overlay):
		_overlay.global_position = camera.global_position

func step(_dt: float) -> void:
	_follow_camera()

func _compute_optical_depth(start: Array, end: Array) -> float:
	var delta := Vector3(float(end[0])-float(start[0]), float(end[1])-float(start[1]), float(end[2])-float(start[2]))
	var length_m := delta.length()
	var density := maxf(0.0, float(test_input.get("density_per_m", 0.0)))
	if length_m == 0.0 or density == 0.0:
		return 0.0
	var falloff := float(test_input.get("height_falloff_per_m", 0.0))
	var reference := float(test_input.get("reference_height_m", 0.0))
	var e0 := -falloff * (float(start[1]) - reference)
	var e1 := -falloff * (float(end[1]) - reference)
	var x := absf(e1 - e0)
	var factor: float
	if x < 0.001:
		factor = 1.0 - x * 0.5 + x * x / 6.0 - x * x * x / 24.0
	else:
		factor = (1.0 - exp(-x)) / x
	return density * length_m * exp(maxf(e0, e1)) * factor

func _compute_samples() -> Dictionary:
	var rays: Array = []
	var depths: Array = []
	var weights: Array = []
	var colors: Array = []
	var fog: Array = test_input["fog_color_linear"]
	for ray: Dictionary in test_input["rays"]:
		var depth := _compute_optical_depth(ray["start"], ray["end"])
		var transmittance := exp(-depth)
		var opacity := 1.0 - transmittance
		var background: Array = ray["background_linear"]
		var color: Array = []
		for channel in 3:
			color.append(transmittance * float(background[channel]) + opacity * float(fog[channel]))
		rays.append({"optical_depth": depth, "transmittance": transmittance, "opacity": opacity, "color_linear": color})
		depths.append(depth)
		weights.append([transmittance, opacity])
		colors.append(color)
	return {"rays": rays, "optical_depth": depths, "transmittance_opacity": weights, "color_linear": colors}

func sample() -> Dictionary:
	return _sample_cache
