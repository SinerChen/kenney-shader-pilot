extends RefCounted
## Read-only geometry cache in host node / instance / surface vertex order.
var cards: Array = []
var bend_m := 0.35
var flatten_m := 0.1

func configure(root: Node, inputs: Dictionary, field) -> void:
	cards.clear()
	bend_m = float(inputs.interaction.bend_m)
	flatten_m = float(inputs.interaction.flatten_m)
	for node in root.grass_nodes:
		var mm: MultiMesh = node.multimesh
		var arrays: Array = mm.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var uv2: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		# Recover parametric card corners from actual geometry, never from asset constants.
		var corners: Array[Vector3] = [Vector3.ZERO, Vector3.ZERO, Vector3.ZERO, Vector3.ZERO]
		for v in range(vertices.size()):
			if uv2[v].is_equal_approx(Vector2(0, 0)): corners[0] = vertices[v]
			if uv2[v].is_equal_approx(Vector2(1, 0)): corners[1] = vertices[v]
			if uv2[v].is_equal_approx(Vector2(0, 1)): corners[2] = vertices[v]
			if uv2[v].is_equal_approx(Vector2(1, 1)): corners[3] = vertices[v]
		var mat: ShaderMaterial = root.material.duplicate()
		mat.set_shader_parameter("interaction_field", field.texture)
		mat.set_shader_parameter("patch_origin", field.origin)
		mat.set_shader_parameter("patch_size", field.size_m)
		mat.set_shader_parameter("bend_m", bend_m)
		mat.set_shader_parameter("flatten_m", flatten_m)
		mat.set_shader_parameter("bottom_left", corners[0])
		mat.set_shader_parameter("bottom_right", corners[1])
		mat.set_shader_parameter("top_left", corners[2])
		mat.set_shader_parameter("top_right", corners[3])
		mat.set_shader_parameter("wind_strength", 0.0)
		node.material_override = mat
		for i in range(mm.instance_count):
			var transform: Transform3D = node.global_transform * mm.get_instance_transform(i)
			cards.append({"transform": transform, "vertices": vertices, "uv2": uv2, "normals": normals, "corners": corners})

func evaluate(field) -> Dictionary:
	var positions: Array = []
	var normals: Array = []
	var root_error := 0.0
	var normal_error := 0.0
	var max_shift := 0.0
	for card in cards:
		var transform: Transform3D = card.transform
		var origin: Vector3 = transform.origin
		var value: Vector3 = field.sample_at(Vector2(origin.x, origin.z))
		var delta := Vector3(value.x * bend_m, -value.z * flatten_m, value.y * bend_m)
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
	print("GEOMETRY_CHECK frame=", field.frame, " instances=", cards.size(), " vertices=", positions.size(), " root_error=", root_error, " unit_normal_error=", normal_error, " max_shift_m=", max_shift)
	return {"positions": positions, "normals": normals}
