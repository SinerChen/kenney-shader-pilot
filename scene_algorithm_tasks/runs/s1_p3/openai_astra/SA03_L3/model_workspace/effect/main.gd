extends Node
## Only surface-local overrides: no geometry, collision, lighting or controller edits.
var scene_root: Node
var test_input: Dictionary = {}
var cached: Dictionary = {}
const WET_MATERIAL = "res://Materials/Ground/Pavement_Cobblestone_Wet.tres"

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs
	cached = _evaluate(test_input)
	_apply_road()

func step(_dt: float) -> void:
	pass

func _vector(values: Array) -> Vector3:
	return Vector3(float(values[0]), float(values[1]), float(values[2]))

func _evaluate(data: Dictionary) -> Dictionary:
	var layers: Array = data["layers"]
	var scores: Array[float] = []
	var peak := -INF
	for layer in layers:
		var score := float(layer.height) * float(layer.control)
		scores.append(score)
		peak = maxf(peak, score)
	var transition := maxf(float(data.transition), 1.0e-5)
	var raw: Array[float] = []
	var total := 0.0
	for i in layers.size():
		var competition := maxf(0.0, scores[i] - peak + transition)
		var value := (competition + 1.0e-6) * float(layers[i].control)
		raw.append(value)
		total += value
	var denom := maxf(total, 1.0e-6)
	var weights: Array[float] = []
	for value in raw:
		weights.append(value / denom)
	var albedo := [0.0, 0.0, 0.0]
	var roughness := 0.0
	var metallic := 0.0
	var height := 0.0
	var normal := Vector3.ZERO
	for i in layers.size():
		var layer: Dictionary = layers[i]
		var w := weights[i]
		for channel in 3:
			albedo[channel] += float(layer.albedo_linear[channel]) * w
		roughness += float(layer.roughness) * w
		metallic += float(layer.metallic) * w
		height += float(layer.height) * w
		normal += _vector(layer.normal_ts) * w
	var base := _unit_or_up(normal)
	var final_normal := base
	if bool(data.detail_enabled):
		final_normal = _rnm(base, _unit_or_up(_vector(data.detail_normal_ts)))
	return {
		"weights": weights,
		"albedo_linear": albedo,
		"roughness_metallic_height": {"roughness": roughness, "metallic": metallic, "height": height},
		"base_normal_ts": [base.x, base.y, base.z],
		"final_normal_ts": [final_normal.x, final_normal.y, final_normal.z]
	}

func _unit_or_up(value: Vector3) -> Vector3:
	return value.normalized() if value.length_squared() > 1.0e-12 else Vector3(0, 0, 1)

func _rnm(base: Vector3, detail: Vector3) -> Vector3:
	var t := base + Vector3(0, 0, 1)
	var u := detail * Vector3(-1, -1, 1)
	if t.z < 1.0e-6:
		return _unit_or_up(Vector3(detail.x, -detail.y, -detail.z))
	return _unit_or_up(t * (t.dot(u) / t.z) - u)

func _layer_property(key: String) -> Vector4:
	var layers: Array = test_input.layers
	return Vector4(float(layers[0][key]), float(layers[1][key]), float(layers[2][key]), float(layers[3][key]))

func _apply_road() -> void:
	if test_input.get("eligible_region", "") != "outdoor_road_wet":
		return
	var ground := scene_root.get_node_or_null("Level Geometry/Ground")
	if ground == null:
		push_warning("Four-layer road: Ground not found")
		return
	var shader := load("res://effect/road.gdshader") as Shader
	var height_map := load("res://Textures/Height/Pavement_Cobblestone_Wet_BLENDSHADER_Height_height.png") as Texture2D
	var count := 0
	for node in ground.find_children("*", "MeshInstance3D", true, false):
		var mesh_node := node as MeshInstance3D
		if mesh_node.mesh == null or mesh_node.material_override != null:
			continue
		for surface in mesh_node.mesh.get_surface_count():
			var original := mesh_node.get_active_material(surface) as StandardMaterial3D
			# Ground.tscn's authored material domains are the fixed region mask.
			# Exact material identity, not a texture substring or global replacement.
			if original == null or original.resource_path != WET_MATERIAL:
				continue
			var material := ShaderMaterial.new()
			material.shader = shader
			material.set_shader_parameter("stone_color", original.albedo_texture)
			material.set_shader_parameter("stone_normal", original.normal_texture)
			material.set_shader_parameter("stone_height", height_map)
			material.set_shader_parameter("uv_scale", original.uv1_scale)
			material.set_shader_parameter("uv_offset", original.uv1_offset)
			material.set_shader_parameter("normal_strength", original.normal_scale)
			material.set_shader_parameter("original_roughness", original.roughness)
			material.set_shader_parameter("original_metallic", original.metallic)
			for key in ["height", "control", "roughness", "metallic"]:
				material.set_shader_parameter("layer_" + key, _layer_property(key))
			var colors := PackedVector3Array()
			var normals := PackedVector3Array()
			for layer in test_input.layers:
				colors.append(_vector(layer.albedo_linear))
				normals.append(_vector(layer.normal_ts))
			material.set_shader_parameter("layer_color", colors)
			material.set_shader_parameter("layer_normal", normals)
			material.set_shader_parameter("transition", float(test_input.transition))
			material.set_shader_parameter("detail_enabled", bool(test_input.detail_enabled))
			material.set_shader_parameter("detail_normal", _vector(test_input.detail_normal_ts))
			mesh_node.set_surface_override_material(surface, material)
			print("Wet region: ", ground.get_path_to(mesh_node), " surface ", surface)
			count += 1
	print("Four-layer road: ", count, " / 10 authored wet-region surfaces; all other materials untouched.")
	if count != 10:
		push_warning("Wet-region coverage differs from Ground.tscn's 10 authored surfaces")

func sample() -> Dictionary:
	return cached
