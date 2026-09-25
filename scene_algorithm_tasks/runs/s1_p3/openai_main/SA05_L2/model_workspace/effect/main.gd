extends Node
## Analytic exponential-height fog output plus the matching native depth-aware
## environment fog for the retained forest scene.
var scene_root: Node
var test_input: Dictionary
var _environment: Environment
var _initial_camera_y := 0.0

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs
	var camera := _find_camera(root)
	if camera:
		_initial_camera_y = camera.global_position.y
	_apply_scene_fog()

func step(_dt: float) -> void:
	# The native fog evaluates the current camera ray against the opaque depth
	# buffer every frame. Alpha-tested plant holes therefore reveal (and use)
	# the depth of the surface behind them rather than the plant's plane depth.
	pass

func sample() -> Dictionary:
	var output_rays: Array = []
	var density := maxf(0.0, float(test_input.get("density_per_m", 0.0)))
	var falloff := maxf(0.0, float(test_input.get("height_falloff_per_m", 0.0)))
	var reference_height := float(test_input.get("reference_height_m", 0.0))
	var fog := _array_color(test_input.get("fog_color_linear", [0.0, 0.0, 0.0]))
	for ray_value in test_input.get("rays", []):
		var ray: Dictionary = ray_value
		var start := _array_vec3(ray.get("start", [0.0, 0.0, 0.0]))
		var end := _array_vec3(ray.get("end", [0.0, 0.0, 0.0]))
		var background := _array_color(ray.get("background_linear", [0.0, 0.0, 0.0]))
		var optical_depth := _height_fog_integral(start, end, density, falloff, reference_height)
		var transmittance := clampf(exp(-optical_depth), 0.0, 1.0)
		var opacity := 1.0 - transmittance
		var composed := background * transmittance + fog * opacity
		output_rays.append({
			"optical_depth": optical_depth,
			"transmittance_opacity": [transmittance, opacity],
			"color_linear": [composed.r, composed.g, composed.b]
		})
	return {"rays": output_rays}

func _height_fog_integral(start: Vector3, end: Vector3, density: float, falloff: float, reference_height: float) -> float:
	var length_m := start.distance_to(end)
	if length_m <= 0.0 or density <= 0.0:
		return 0.0
	var density_at_start := density * exp(-falloff * (start.y - reference_height))
	var height_delta := end.y - start.y
	var integral_factor := 1.0
	var exponent_delta := falloff * height_delta
	# expm1's limiting form, written explicitly because GDScript has no expm1.
	if absf(exponent_delta) > 0.00001:
		integral_factor = (1.0 - exp(-exponent_delta)) / exponent_delta
	else:
		integral_factor = 1.0 - 0.5 * exponent_delta + exponent_delta * exponent_delta / 6.0
	return maxf(0.0, density_at_start * length_m * integral_factor)

func _apply_scene_fog() -> void:
	var world_environment := _find_world_environment(scene_root)
	if world_environment == null or world_environment.environment == null:
		return
	# environment_setup already duplicates the source Environment. Duplicate once
	# more so this effect never mutates a shared project resource.
	_environment = world_environment.environment.duplicate(true)
	world_environment.environment = _environment
	var density := maxf(0.0, float(test_input.get("density_per_m", 0.0)))
	var falloff := maxf(0.0, float(test_input.get("height_falloff_per_m", 0.0)))
	var reference_height := float(test_input.get("reference_height_m", 0.0))
	var fog := _array_color(test_input.get("fog_color_linear", [0.0, 0.0, 0.0]))
	_environment.fog_enabled = density > 0.0
	_environment.fog_light_color = fog
	_environment.fog_light_energy = 1.0
	_environment.fog_density = density
	_environment.fog_height = reference_height
	_environment.fog_height_density = falloff
	# No directional tint: the requested result is a single linear interpolation.
	_environment.fog_sun_scatter = 0.0
	# Sky pixels have no nearest surface endpoint and must remain untouched.
	_environment.fog_aerial_perspective = 0.0 if bool(test_input.get("preserve_sky", true)) else 1.0
	# Keep volumetric fog off to avoid applying a second color integration.
	_environment.volumetric_fog_enabled = false

func _find_world_environment(root: Node) -> WorldEnvironment:
	if root is WorldEnvironment:
		return root
	for node in root.find_children("*", "WorldEnvironment", true, false):
		return node as WorldEnvironment
	return null

func _find_camera(root: Node) -> Camera3D:
	var viewport_camera := root.get_viewport().get_camera_3d()
	if viewport_camera:
		return viewport_camera
	for node in root.find_children("*", "Camera3D", true, false):
		return node as Camera3D
	return null

func _array_vec3(value: Variant) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))

func _array_color(value: Variant) -> Color:
	return Color(float(value[0]), float(value[1]), float(value[2]), 1.0)
