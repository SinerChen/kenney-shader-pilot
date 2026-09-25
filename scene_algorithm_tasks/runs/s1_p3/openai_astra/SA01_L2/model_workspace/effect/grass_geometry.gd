extends RefCounted
## Geometry and shading share a root-coherent wind + interaction displacement.
var cards: Array = []
var materials: Array = []
var bend_m := 0.35
var flatten_m := 0.1
var wind_strength := 0.22
var wind_speed := 1.6
var wind_direction := Vector2(1.0, 0.35)

func configure(root: Node, inputs: Dictionary, field) -> void:
	cards.clear()
	materials.clear()
	bend_m = float(inputs.interaction.bend_m)
	flatten_m = float(inputs.interaction.flatten_m)
	wind_strength = float(inputs.wind.strength)
	wind_speed = float(inputs.wind.speed)
	wind_direction = Vector2(inputs.wind.direction_xz[0], inputs.wind.direction_xz[1]).normalized()
	for node in root.grass_nodes:
		var mm: MultiMesh = node.multimesh
		var arrays: Array = mm.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var uv2: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var corners: Array[Vector3] = [Vector3.ZERO, Vector3.ZERO, Vector3.ZERO, Vector3.ZERO]
		for v in range(vertices.size()):
			if uv2[v].is_equal_approx(Vector2(0, 0)): corners[0] = vertices[v]
			if uv2[v].is_equal_approx(Vector2(1, 0)): corners[1] = vertices[v]
			if uv2[v].is_equal_approx(Vector2(0, 1)): corners[2] = vertices[v]
			if uv2[v].is_equal_approx(Vector2(1, 1)): corners[3] = vertices[v]
		var mat: ShaderMaterial = root.material.duplicate()
		for key in {"interaction_field":field.texture, "patch_origin":field.origin, "patch_size":field.size_m, "bend_m":bend_m, "flatten_m":flatten_m, "bottom_left":corners[0], "bottom_right":corners[1], "top_left":corners[2], "top_right":corners[3], "wind_strength":wind_strength, "wind_speed":wind_speed, "wind_direction":wind_direction}:
			var params := {"interaction_field":field.texture, "patch_origin":field.origin, "patch_size":field.size_m, "bend_m":bend_m, "flatten_m":flatten_m, "bottom_left":corners[0], "bottom_right":corners[1], "top_left":corners[2], "top_right":corners[3], "wind_strength":wind_strength, "wind_speed":wind_speed, "wind_direction":wind_direction}
			mat.set_shader_parameter(key, params[key])
		materials.append(mat)
		node.material_override = mat
		for i in range(mm.instance_count):
			var transform: Transform3D = node.global_transform * mm.get_instance_transform(i)
			cards.append({"transform":transform, "vertices":vertices, "uv2":uv2, "normals":normals, "corners":corners})

func update_time(time: float) -> void:
	for mat in materials:
		mat.set_shader_parameter("elapsed", time)

func wind_at(point: Vector2, time: float) -> Vector3:
	var phase := time * wind_speed - point.dot(wind_direction) * 1.3
	var wave := 0.7 * sin(phase) + 0.3 * sin(phase * 2.17 + 0.8)
	return Vector3(wind_direction.x, 0.0, wind_direction.y) * wind_strength * wave

func evaluate(field) -> Dictionary:
	var positions: Array = []
	var normals: Array = []
	var root_error := 0.0
	var normal_error := 0.0
	var max_shift := 0.0
	var wind_peak := 0.0
	for card in cards:
		var transform: Transform3D = card.transform
		var origin: Vector3 = transform.origin
		var value: Vector3 = field.sample_at(Vector2(origin.x, origin.z))
		var wind := wind_at(Vector2(origin.x, origin.z), field.elapsed)
		wind_peak = maxf(wind_peak, wind.length())
		var delta := Vector3(value.x * bend_m, -value.z * flatten_m, value.y * bend_m) + wind
		var corners: Array = card.corners
		var normal_basis := transform.basis.inverse().transposed()
		for i in range(card.vertices.size()):
			var h := clampf(card.uv2[i].y, 0.0, 1.0)
			var s: float = card.uv2[i].x
			var original: Vector3 = transform * card.vertices[i]
			var point := original + delta * h * h
			var ds: Vector3 = transform.basis * (corners[1] - corners[0]).lerp(corners[3] - corners[2], h)
			var dh: Vector3 = transform.basis * (corners[2] - corners[0]).lerp(corners[3] - corners[1], s) + delta * (2.0 * h)
			var normal := ds.cross(dh).normalized()
			if normal.dot(normal_basis * card.normals[i]) < 0.0:
				normal = -normal
			positions.append([point.x, point.y, point.z])
			normals.append([normal.x, normal.y, normal.z])
			if h == 0.0: root_error = maxf(root_error, point.distance_to(original))
			normal_error = maxf(normal_error, absf(normal.length() - 1.0))
			max_shift = maxf(max_shift, point.distance_to(original))
	print("GEOMETRY_CHECK frame=", field.frame, " instances=", cards.size(), " vertices=", positions.size(), " root_error=", root_error, " unit_normal_error=", normal_error, " max_shift_m=", max_shift, " wind_peak_m=", wind_peak)
	return {"positions":positions, "normals":normals}
