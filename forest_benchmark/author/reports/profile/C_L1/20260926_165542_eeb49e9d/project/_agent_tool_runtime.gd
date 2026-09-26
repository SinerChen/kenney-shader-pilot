extends SceneTree
## Runs only in the tool's disposable project copy.

var request: Dictionary
var scene: Node
var out_dir: String
var changes: Array = []
var diagnostic_changes: Array = []

func _initialize() -> void:
	request = JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]))
	out_dir = str(request.output_dir)
	seed(int(request.seed))
	RenderingServer.set_debug_generate_wireframes(true)
	call_deferred("run")

func vec(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))

func encode(value: Variant, depth: int = 0) -> Variant:
	if value == null:
		return null
	if value is bool or value is String or value is int:
		return value
	if value is float:
		return value if is_finite(value) else str(value)
	if value is Vector2 or value is Vector2i:
		return [value.x, value.y]
	if value is Vector3 or value is Vector3i:
		return [value.x, value.y, value.z]
	if value is Color:
		return [value.r, value.g, value.b, value.a]
	if value is Transform3D:
		return [[value.basis.x.x, value.basis.y.x, value.basis.z.x], [value.basis.x.y, value.basis.y.y, value.basis.z.y], [value.basis.x.z, value.basis.y.z, value.basis.z.z], encode(value.origin)]
	if value is Resource:
		var record := {"class": value.get_class(), "path": value.resource_path, "instance_id": value.get_instance_id()}
		if value is CompositorEffect:
			record.enabled = value.enabled
			record.callback_type = value.effect_callback_type
		if value is Texture2D:
			record.size = [value.get_width(), value.get_height()]
		if depth < 2 and (value is Material or value is Environment or value is CameraAttributes or value is Compositor):
			record.properties = properties(value, depth + 1)
			if value is ShaderMaterial and value.shader:
				record.shader = {"path": value.shader.resource_path, "code_sha256": value.shader.code.sha256_text()}
				record.parameters = {}
				for uniform in value.shader.get_shader_uniform_list():
					record.parameters[uniform.name] = encode(value.get_shader_parameter(uniform.name), depth + 1)
		return record
	if value is Array or value is PackedVector3Array or value is PackedVector2Array or value is PackedColorArray or value is PackedInt32Array or value is PackedFloat32Array:
		var items: Array = []
		for item in value:
			items.append(encode(item, depth + 1))
		return items
	return str(value)

func properties(object: Object, depth: int = 0) -> Dictionary:
	var result := {}
	for entry in object.get_property_list():
		if int(entry.usage) & PROPERTY_USAGE_STORAGE and entry.name not in ["script", "owner"]:
			result[entry.name] = encode(object.get(entry.name), depth)
	return result

func target(path: String) -> Node:
	if path == "." or path == str(scene.name):
		return scene
	return scene.get_node_or_null(NodePath(path.trim_prefix(str(scene.name) + "/")))

func mesh_of(node: Node) -> Mesh:
	if node is MeshInstance3D:
		return node.mesh
	if node is MultiMeshInstance3D and node.multimesh:
		return node.multimesh.mesh
	return null

func active_material(node: Node, surface: int) -> Material:
	if node is MeshInstance3D:
		return node.get_active_material(surface)
	if node is MultiMeshInstance3D:
		return node.material_override if node.material_override else node.multimesh.mesh.surface_get_material(surface)
	return null

func describe(node: Node) -> Dictionary:
	var item := {"path": str(scene.get_path_to(node)), "class": node.get_class()}
	if node is Node3D:
		item.transform = encode(node.global_transform)
		item.visible = node.is_visible_in_tree()
	var mesh := mesh_of(node)
	if mesh:
		item.mesh = encode(mesh)
		item.materials = []
		for surface in range(mesh.get_surface_count()):
			item.materials.append({"surface": surface, "material": encode(active_material(node, surface))})
		item.material_overlay = encode(node.material_overlay)
	if node is MultiMeshInstance3D and node.multimesh:
		item.instance_count = node.multimesh.instance_count
		item.visible_instance_count = node.multimesh.visible_instance_count
	if node is Camera3D or node is Light3D or node is WorldEnvironment or node is ReflectionProbe or node is CanvasItem:
		item.properties = properties(node)
	return item

func walk(node: Node, records: Array) -> void:
	records.append(describe(node))
	for child in node.get_children():
		walk(child, records)

func mesh_data(node: Node, surface: int, frame: int) -> Dictionary:
	var mesh := mesh_of(node)
	if mesh == null or surface < 0 or surface >= mesh.get_surface_count():
		return {"status": "unavailable", "reason": "Target/surface has no mesh"}
	var arrays := mesh.surface_get_arrays(surface)
	if arrays.is_empty() or arrays[Mesh.ARRAY_VERTEX] == null:
		return {"status": "unavailable", "reason": "Mesh does not expose CPU arrays"}
	var material := active_material(node, surface)
	var unknown := node is MultiMeshInstance3D
	if node is MeshInstance3D:
		unknown = node.skin != null or node.get_blend_shape_count() > 0
	if material is ShaderMaterial and material.shader:
		unknown = unknown or "vertex" in material.shader.code or "#include" in material.shader.code
	if material is BaseMaterial3D:
		unknown = unknown or material.grow or material.fixed_size or material.billboard_mode != BaseMaterial3D.BILLBOARD_DISABLED
	var result := {"status": "observed", "frame": frame, "time_s": float(frame) / float(request.fps), "surface": surface,
		"primitive": mesh.surface_get_primitive_type(surface) if mesh is ArrayMesh else Mesh.PRIMITIVE_TRIANGLES if mesh is PrimitiveMesh else -1, "transform": encode(node.global_transform),
		"unobserved_deformation": unknown, "source": "runtime_mesh_resource_arrays; not GPU vertex readback"}
	var slots := {"vertices": Mesh.ARRAY_VERTEX, "normals": Mesh.ARRAY_NORMAL, "tangents": Mesh.ARRAY_TANGENT,
		"uv": Mesh.ARRAY_TEX_UV, "uv2": Mesh.ARRAY_TEX_UV2, "colors": Mesh.ARRAY_COLOR, "indices": Mesh.ARRAY_INDEX}
	for key in slots:
		result[key] = encode(arrays[slots[key]]) if arrays[slots[key]] != null else []
	return result

func coerce_value(value: Variant, previous: Variant) -> Variant:
	if previous is int and value is float:
		return int(value)
	if previous is Vector3 and value is Array:
		return vec(value)
	if previous is Vector2 and value is Array:
		return Vector2(value[0], value[1])
	if previous is Color and value is Array:
		return Color(value[0], value[1], value[2], value[3] if value.size() > 3 else 1.0)
	return value

func apply_change(change: Dictionary) -> bool:
	var node := target(str(change.target))
	if node == null:
		return false
	var previous: Variant
	if change.has("shader_parameter"):
		if not (node is MeshInstance3D or node is CanvasItem):
			return false
		var surface := int(change.get("surface", 0))
		var original: Material = active_material(node, surface) if node is MeshInstance3D else node.material
		if not original is ShaderMaterial:
			return false
		var names: Array = []
		for uniform in original.shader.get_shader_uniform_list():
			names.append(str(uniform.name))
		if str(change.shader_parameter) not in names:
			return false
		var material := original.duplicate() as ShaderMaterial
		previous = material.get_shader_parameter(change.shader_parameter)
		if previous == null:
			previous = RenderingServer.shader_get_parameter_default(material.shader.get_rid(), change.shader_parameter)
		material.set_shader_parameter(change.shader_parameter, coerce_value(change.value, previous))
		if node is MeshInstance3D:
			bind_surface(node, surface, material)
		else:
			node.material = material
	else:
		var property := str(change.property)
		previous = node.get_indexed(NodePath(property))
		if previous == null:
			return false
		# Nested Resource properties are duplicated along the path, isolating shared assets.
		var holder: Object = node
		var parts := property.split(":")
		for i in range(parts.size() - 1):
			var resource: Variant = holder.get(parts[i])
			if not resource is Resource:
				return false
			var copy: Resource = resource.duplicate()
			holder.set(parts[i], copy)
			holder = copy
		holder.set(parts[-1], coerce_value(change.value, previous))
	changes.append({"request": change, "before": encode(previous), "after": change.value})
	return true

func bind_surface(node: MeshInstance3D, surface: int, material: Material) -> void:
	if node.material_override:
		for i in range(node.mesh.get_surface_count()):
			node.set_surface_override_material(i, node.material_override)
		node.material_override = null
	node.set_surface_override_material(surface, material)

func instrument(node: Node, channel: String) -> String:
	if not node is MeshInstance3D or node.material_overlay:
		return "Instrumentation requires a MeshInstance3D without a material overlay"
	var surface := int(request.surface)
	if node.mesh == null or surface < 0 or surface >= node.mesh.get_surface_count():
		return "Target surface unavailable"
	var original := active_material(node, surface)
	if original and original.next_pass:
		return "Multi-pass materials require an explicit diagnostic adapter"
	var code := "shader_type spatial; void fragment() {}"
	var material := ShaderMaterial.new()
	if original is ShaderMaterial:
		material = original.duplicate()
		code = original.shader.code
	elif original is BaseMaterial3D:
		if original.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED or original.grow or original.proximity_fade_enabled or original.fixed_size or original.billboard_mode != BaseMaterial3D.BILLBOARD_DISABLED or original.distance_fade_mode != BaseMaterial3D.DISTANCE_FADE_DISABLED:
			return "Material displacement/transparency requires an explicit diagnostic adapter"
		if original.cull_mode == BaseMaterial3D.CULL_DISABLED:
			code += "\nrender_mode cull_disabled;"
		elif original.cull_mode == BaseMaterial3D.CULL_FRONT:
			code += "\nrender_mode cull_front;"
	elif original != null:
		return "Unsupported material type"
	code = RegEx.create_from_string("(?s)/\\*.*?\\*/|//[^\\n]*").sub(code, " ", true)
	if "#" in code or not "shader_type spatial" in code:
		return "Preprocessed/non-spatial shaders require an explicit diagnostic adapter"
	var match_fragment := RegEx.create_from_string("void\\s+fragment\\s*\\(\\s*\\)\\s*\\{").search(code)
	if match_fragment == null:
		code += "\nvoid fragment() {}"
		match_fragment = RegEx.create_from_string("void\\s+fragment\\s*\\(\\s*\\)\\s*\\{").search(code)
	var end := match_fragment.get_end()
	var braces := 1
	while end < code.length() and braces > 0:
		if code[end] == "{": braces += 1
		if code[end] == "}": braces -= 1
		end += 1
	if braces != 0 or RegEx.create_from_string("\\breturn\\b").search(code.substr(match_fragment.get_end(), end-match_fragment.get_end())):
		return "Fragment early returns or unbalanced source require an explicit adapter"
	var expression := "vec3(fract(UV), 0.0)" if channel == "uv" else "COLOR.rgb"
	if channel == "checker":
		expression = "vec3(fract(UV.x * 8.0), fract(UV.y * 8.0), mod(floor(UV.x * 8.0) + floor(UV.y * 8.0), 2.0))"
	if not RegEx.create_from_string("\\bunshaded\\b").search(code):
		code += "\nrender_mode unshaded;"
	code = code.insert(end-1, "\nALBEDO = " + expression + "; EMISSION = vec3(0.0);\n")
	var shader := Shader.new()
	shader.code = code
	material.shader = shader
	bind_surface(node, surface, material)
	diagnostic_changes.append({"target": request.target, "surface": surface, "channel": channel,
		"original_shader_sha256": original.shader.code.sha256_text() if original is ShaderMaterial else null,
		"diagnostic_shader_sha256": code.sha256_text(), "retained": "original vertex/fragment execution including discard; display output overridden"})
	return ""

func set_camera(config: Variant) -> bool:
	if config is String:
		var camera := target(config)
		if not camera is Camera3D:
			return false
		camera.make_current()
	elif config is Dictionary and not config.is_empty():
		var camera: Camera3D = root.get_node_or_null("AgentCamera")
		if camera == null:
			camera = Camera3D.new()
			camera.name = "AgentCamera"
			root.add_child(camera)
		camera.global_position = vec(config.position)
		camera.look_at(vec(config.look_at), vec(config.get("up", [0, 1, 0])))
		camera.fov = float(config.get("fov", 60))
		camera.near = float(config.get("near", 0.05))
		camera.far = float(config.get("far", 1000))
		camera.make_current()
	return true

func draw() -> void:
	await process_frame
	await RenderingServer.frame_post_draw

func finish(data: Dictionary) -> void:
	data.merge({"status": "observed", "verdict": "not_evaluated", "stage": "runtime_observation", "provenance": "godot_runner"}, false)
	data.stage = {"inspect": "live_scene_instances", "mesh": "runtime_mesh_resource_input", "capture": "final_viewport_output", "fixture": "final_canvas_item_output", "profile": "viewport_timing"}.get(request.operation, "runtime_observation")
	data.target = request.target
	data.surface = request.surface
	data.engine = Engine.get_version_info().string
	data.renderer = RenderingServer.get_current_rendering_method()
	data.hardware = {"adapter": RenderingServer.get_video_adapter_name(), "vendor": RenderingServer.get_video_adapter_vendor()}
	data.resolution = [root.size.x, root.size.y]
	data.changes = changes
	data.diagnostic_changes = diagnostic_changes
	data.timing = {"fps": request.fps, "seed": request.seed, "step_method": request.step_method,
		"history_policy": "fresh_process", "shader_TIME": "engine clock includes initialization; use scene-controlled uniforms for exact shader time",
		"clock": "native realtime; fixed dt for explicit scene step only" if request.operation == "profile" else "fixed frame step"}
	var camera := root.get_camera_3d()
	data.camera = describe(camera) if camera else null
	var output := FileAccess.open(out_dir.path_join("data.json"), FileAccess.WRITE)
	output.store_string(JSON.stringify(data, "  "))
	output.close()
	print("AGENT_TOOL_COMPLETE")
	quit(0)

func make_fixture() -> String:
	scene = Node.new()
	scene.name = "Fixture"
	root.add_child(scene)
	var image := Image.load_from_file(str(request.fixture_image))
	var input := TextureRect.new()
	input.texture = ImageTexture.create_from_image(image)
	input.size = root.size
	scene.add_child(input)
	var copy := BackBufferCopy.new()
	copy.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
	scene.add_child(copy)
	var resource := load(str(request.effect))
	var material: ShaderMaterial
	if resource is Shader:
		material = ShaderMaterial.new()
		material.shader = resource
	elif resource is ShaderMaterial:
		material = resource.duplicate()
	else:
		return "effect must be the actual canvas_item Shader or ShaderMaterial"
	if material.shader.get_mode() != Shader.MODE_CANVAS_ITEM:
		return "This fixture adapter only supports canvas_item screen-reading effects"
	var uniforms: Array = []
	for uniform in material.shader.get_shader_uniform_list(): uniforms.append(str(uniform.name))
	for key in request.get("parameters", {}):
		if key not in uniforms:
			return "Unknown effect uniform: " + str(key)
		var previous: Variant = material.get_shader_parameter(key)
		if previous == null: previous = RenderingServer.shader_get_parameter_default(material.shader.get_rid(), key)
		material.set_shader_parameter(key, coerce_value(request.parameters[key], previous))
	var effect := ColorRect.new()
	effect.name = "Effect"
	effect.size = root.size
	effect.material = material
	scene.add_child(effect)
	return ""

func run() -> void:
	paused = true
	root.size = Vector2i(request.resolution[0], request.resolution[1])
	root.content_scale_size = root.size
	if request.operation == "fixture":
		var problem := make_fixture()
		if problem:
			finish({"status": "unsupported", "reason": problem})
			return
	else:
		var path := str(request.get("scene", ""))
		if path.is_empty(): path = str(ProjectSettings.get_setting("application/run/main_scene", ""))
		if path.is_empty() or change_scene_to_file(path) != OK:
			finish({"status": "unavailable", "reason": "Entry scene not found"})
			return
		await scene_changed
		scene = current_scene
	await draw()
	for change in request.get("changes", []):
		if not apply_change(change):
			finish({"status": "unavailable", "reason": "Invalid intervention", "intervention": change})
			return
	if not set_camera(request.get("camera", {})):
		finish({"status": "unavailable", "reason": "Camera not found"})
		return
	var node := target(str(request.target))
	if node == null:
		finish({"status": "unavailable", "reason": "Target not found"})
		return
	var channel := str(request.get("channel", "color"))
	var modes := {"color": Viewport.DEBUG_DRAW_DISABLED, "wireframe": Viewport.DEBUG_DRAW_WIREFRAME,
		"unshaded": Viewport.DEBUG_DRAW_UNSHADED, "lighting": Viewport.DEBUG_DRAW_LIGHTING,
		"overdraw": Viewport.DEBUG_DRAW_OVERDRAW, "normal": Viewport.DEBUG_DRAW_NORMAL_BUFFER}
	if channel == "normal" and RenderingServer.get_current_rendering_method() != "forward_plus":
		finish({"status": "unsupported", "reason": "Normal buffer requires Forward+"})
		return
	if channel in ["uv", "checker", "vertex_color"]:
		var problem := instrument(node, channel)
		if problem:
			finish({"status": "unsupported", "reason": problem})
			return
	else:
		root.debug_draw = modes.get(channel, Viewport.DEBUG_DRAW_DISABLED)
	var frames: Array[int] = []
	for frame in request.frames: frames.append(int(frame))
	var records: Array = []
	var samples: Array = []
	var profiling: bool = request.operation == "profile"
	if profiling: RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	var count: int = int(request.warmup) + int(request.measure_frames) if profiling else frames[-1]
	for frame in range(count + 1):
		for event in request.get("events", []):
			if int(event.frame) == frame:
				if event.has("camera") and not set_camera(event.camera):
					finish({"status": "unavailable", "reason": "Sequence camera not found"})
					return
				for change in event.get("changes", []):
					if not apply_change(change):
						finish({"status": "unavailable", "reason": "Sequence intervention unavailable"})
						return
		var started := Time.get_ticks_usec()
		if frame > 0:
			if request.step_method != "native":
				if not scene.has_method(request.step_method):
					finish({"status": "unavailable", "reason": "Requested scene step method not found"})
					return
				scene.call(request.step_method, 1.0 / float(request.fps))
			else:
				paused = false
		await draw()
		paused = true
		if profiling:
			if frame > int(request.warmup):
				samples.append({"frame": frame, "wall_ms": (Time.get_ticks_usec()-started)/1000.0,
					"render_cpu_ms": RenderingServer.viewport_get_measured_render_time_cpu(root.get_viewport_rid()),
					"render_gpu_ms": RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()),
					"setup_cpu_ms": RenderingServer.get_frame_setup_time_cpu(),
					"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
					"video_memory_bytes": Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED)})
		elif frame in frames:
			if request.operation == "mesh":
				var sample := mesh_data(node, int(request.surface), frame)
				if sample.status != "observed":
					finish(sample)
					return
				samples.append(sample)
			elif request.operation == "inspect":
				var nodes: Array = []
				walk(node, nodes)
				samples.append({"frame": frame, "nodes": nodes})
			else:
				var image := root.get_texture().get_image()
				var filename := "frame_%04d.png" % frame
				if image.is_empty() or image.save_png(out_dir.path_join(filename)) != OK:
					finish({"status": "error", "reason": "GPU image capture failed"})
					return
				records.append({"frame": frame, "time_s": float(frame) / float(request.fps), "path": filename,
					"camera": describe(root.get_camera_3d()) if root.get_camera_3d() else null})
	var limitations: Array = ["Native fixed stepping does not reset shader TIME or external nondeterministic inputs", "SceneTree structure is not an effect influence graph"]
	if channel == "normal": limitations.append("Depth-prepass normal coverage; transparent surfaces are not guaranteed")
	if channel in ["uv", "checker", "vertex_color"]: limitations.append("Interpolated input attribute visualization, not a named texture sampler's effective coordinates; final color processing remains enabled")
	finish({"samples": samples, "images": records, "channel": channel, "coverage": "selected runtime target; native debug views cover the entire viewport",
		"encoding": "display-processed PNG, not raw linear HDR or depth", "limitations": limitations})
