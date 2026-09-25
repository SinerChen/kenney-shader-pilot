extends Node3D
## Isolated Forest variant. Original scene/assets/material resources stay intact.

const WATER = preload("res://dew/water.gdshader")
const MAX_PLANTS := 12
const BEADS_PER_PLANT := 650
const WIND_SPEED := 3.0
const WIND_STRENGTH := 0.03
const WIND_SCALE := 5.0

var beads: Array[Dictionary] = []
var plants: Array[Dictionary] = []
var leaf_material: ShaderMaterial
var droplets: MultiMeshInstance3D
var probe: ReflectionProbe
var camera: Camera3D
var ui: CanvasLayer
var status: Label
var ready_for_capture := false
var animate := true
var clock_time := 2.0
var hero := Vector3.ZERO
var hero_normal := Vector3.UP
var hero_index := 0
var overview_transform: Transform3D
var plant_center := Vector3.ZERO
var local_reflection := true
var current_view := "macro"
var rng := RandomNumberGenerator.new()
@export_range(0,11) var focus_plant_index := 0

func _ready() -> void:
	# MultiMesh instance buffers must first reach the real RenderingServer.
	await get_tree().process_frame
	camera = get_viewport().get_camera_3d()
	overview_transform = camera.global_transform
	camera.set_process(false)
	camera.set_process_unhandled_input(false)
	camera.near = 0.005
	camera.far = 1500.0
	camera.fov = 48.0
	rng.seed = 17331
	prepare_leaf_material()
	collect_plants()
	if plants.is_empty():
		push_error("No fern instances available for dew")
		return
	plant_center = plants[mini(focus_plant_index, plants.size()-1)].xf.origin
	for plant in plants:
		add_leaf_beads(plant)
	if beads.is_empty():
		push_error("No valid opaque leaf positions found")
		return
	choose_hero()
	# Extra condensation around the close-up leaf. Geometry remains in place.
	add_leaf_beads(plants[mini(focus_plant_index,plants.size()-1)],hero,140)
	create_droplets()
	probe = ReflectionProbe.new()
	probe.name = "DewEnvironmentReflection"
	probe.size = Vector3(18, 12, 18)
	probe.position = hero + Vector3.UP * 0.4
	probe.cull_mask = 1 # Capture the original forest, excluding water beads.
	probe.reflection_mask = 2 # Affect droplets only; baseline lighting is unchanged.
	probe.enable_shadows = true
	probe.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
	probe.update_mode = ReflectionProbe.UPDATE_ONCE
	probe.max_distance = 180.0
	add_child(probe)
	create_ui()
	update_beads()
	set_view("macro")
	ready_for_capture = true
	print("DEW_READY plants=", plants.size(), " beads=", beads.size(), " hero=", hero)

func prepare_leaf_material() -> void:
	leaf_material = load("res://Materials/fern_02.tres").duplicate()
	var shader := Shader.new()
	# One shared explicit clock, so each droplet follows the exact interpolated
	# vertex positions used by the leaf shader, including during paused checks.
	shader.code = leaf_material.shader.code.replace("uniform float wind_speed", "uniform float dew_time = 0.0;\nuniform float wind_speed").replace("TIME", "dew_time")
	# This source asset binds a grayscale roughness map to the old ORM slot.
	# It contains no metalness or AO data. Keep roughness, avoid metallic leaves.
	shader.code = shader.code.replace("METALLIC = orm_tex.b;", "METALLIC = 0.0;").replace("AO = orm_tex.r;", "AO = 1.0;")
	leaf_material.shader = shader
	# The legacy .tres stored Vector3 values for these vec2 uniforms.
	leaf_material.set_shader_parameter("uv1_scale", Vector2.ONE)
	leaf_material.set_shader_parameter("uv1_offset", Vector2.ZERO)
	leaf_material.set_shader_parameter("dew_time", clock_time)

func collect_plants() -> void:
	for node in $Forest.find_children("*", "MultiMeshInstance3D", true, false):
		if node.global_position.distance_to(overview_transform.origin) > 70.0:
			continue
		var mm: MultiMesh = node.multimesh
		if mm == null or mm.mesh == null:
			continue
		var mat := mm.mesh.surface_get_material(0)
		if mat == null or not "fern_02" in mat.resource_path:
			continue
		node.material_override = leaf_material
		node.ignore_occlusion_culling = true
		var count := mm.instance_count if mm.visible_instance_count < 0 else mm.visible_instance_count
		for i in range(count):
			var xf: Transform3D = node.global_transform * mm.get_instance_transform(i)
			var distance := xf.origin.distance_to(overview_transform.origin)
			if distance < 80.0:
				plants.append({"xf":xf, "mesh":mm.mesh, "distance":distance, "node":str(node.get_path()), "instance":i})
	plants.sort_custom(func(a,b):return a.distance < b.distance)
	plants = plants.slice(0, MAX_PLANTS)

func alpha_safe(img: Image, uv: Vector2) -> bool:
	var x := int(uv.x * img.get_width())
	var y := int(uv.y * img.get_height())
	for offset in [Vector2i.ZERO, Vector2i(4,0), Vector2i(-4,0), Vector2i(0,4), Vector2i(0,-4)]:
		if img.get_pixel(posmod(x + offset.x,img.get_width()), posmod(y + offset.y,img.get_height())).a < 0.92:
			return false
	return true

func add_leaf_beads(plant: Dictionary, focus := Vector3.INF, limit := BEADS_PER_PLANT) -> void:
	var arrays: Array = plant.mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var colors: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
	var uv: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var texture: Texture2D = leaf_material.get_shader_parameter("texture_albedo")
	var img := texture.get_image()
	if img.is_compressed():
		img.decompress()
	var triangles: Array[Dictionary] = []
	var area_sum := 0.0
	for t in range(0, indices.size(), 3):
		var a := indices[t]
		var b := indices[t+1]
		var c := indices[t+2]
		var p0: Vector3 = plant.xf * vertices[a]
		var p1: Vector3 = plant.xf * vertices[b]
		var p2: Vector3 = plant.xf * vertices[c]
		if focus.is_finite():
			var bounds := AABB(p0,Vector3.ZERO).expand(p1).expand(p2).grow(0.22)
			if not bounds.has_point(focus):
				continue
		var normal := (p1-p0).cross(p2-p0).normalized()
		if normal.y < 0.0:
			normal = -normal
		var area := (p1-p0).cross(p2-p0).length() * 0.5
		if normal.y < 0.18 or area < 0.000001:
			continue
		area_sum += area
		triangles.append({"ids":Vector3i(a,b,c), "area":area_sum, "normal":normal})
	if triangles.is_empty():
		return
	var start := beads.size()
	var accepted_positions: Array[Vector3] = []
	if focus.is_finite():
		for bead in beads:
			if bead.position.distance_to(focus) < 0.24:
				accepted_positions.append(bead.position)
	for attempt in range(limit * 400):
		if beads.size() - start >= limit:
			break
		var area := rng.randf() * area_sum
		var tri: Dictionary = triangles[-1]
		for candidate in triangles:
			if candidate.area >= area:
				tri = candidate
				break
		var ids: Vector3i = tri.ids
		var s := sqrt(rng.randf())
		var weights := Vector3(1.0-s, s*(1.0-rng.randf()), 0.0)
		weights.z = 1.0 - weights.x - weights.y
		var sample_uv := uv[ids.x]*weights.x + uv[ids.y]*weights.y + uv[ids.z]*weights.z
		if not alpha_safe(img, sample_uv):
			continue
		var center: Vector3 = plant.xf * (vertices[ids.x]*weights.x + vertices[ids.y]*weights.y + vertices[ids.z]*weights.z)
		if focus.is_finite() and center.distance_to(focus) > 0.22:
			continue
		var crowded := false
		for existing in accepted_positions:
			if existing.distance_squared_to(center) < 0.00010:
				crowded = true
				break
		if crowded:
			continue
		var cols: Array[Vector3] = []
		for idx in [ids.x, ids.y, ids.z]:
			var color := colors[idx] if colors.size() > idx else Color.BLACK
			cols.append(Vector3(color.r,color.g,color.b))
		beads.append({"p":[vertices[ids.x],vertices[ids.y],vertices[ids.z]], "colors":cols, "weights":weights, "xf":plant.xf,
			"radius":rng.randf_range(0.0020,0.0047), "position":center, "normal":tri.normal})
		accepted_positions.append(center)
	if not focus.is_finite():
		plant["bead_start"] = start
		plant["bead_count"] = beads.size() - start

func create_droplets() -> void:
	var sphere := SphereMesh.new()
	sphere.radius = 1.0
	sphere.height = 2.0
	sphere.radial_segments = 20
	sphere.rings = 12
	var mat := ShaderMaterial.new()
	mat.shader = WATER
	sphere.material = mat
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = sphere
	mm.instance_count = beads.size()
	for i in range(beads.size()):
		mm.set_instance_custom_data(i, Color(beads[i].radius,0,0,1))
	droplets = MultiMeshInstance3D.new()
	droplets.name = "LeafDew"
	droplets.multimesh = mm
	droplets.layers = 2
	droplets.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	droplets.ignore_occlusion_culling = true
	droplets.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	add_child(droplets)

func choose_hero() -> void:
	var target := plant_center + Vector3(0.25, 0.9, 0.85)
	var best := INF
	var plant := plants[mini(focus_plant_index, plants.size()-1)]
	for i in range(int(plant.bead_start), int(plant.bead_start + plant.bead_count)):
		var bead := beads[i]
		var score: float = bead.position.distance_to(target) + (1.0 - bead.normal.y) * 0.2
		if score < best:
			best = score
			hero_index = i
	hero = beads[hero_index].position
	hero_normal = beads[hero_index].normal

func wind_vertex(p: Vector3, color: Vector3) -> Vector3:
	var speed := clock_time * WIND_SPEED
	var q := Vector3.ONE*speed + (p+color)*WIND_SCALE
	var strength := clampf(color.x+color.y, 0.0, 1.0)*WIND_STRENGTH/10.0
	return p + Vector3(sin_combined(q.z,speed,1.2),sin_combined(q.x,speed,1.78),sin_combined(q.y,speed,0.9))*strength

func sin_combined(p: float, t: float, r: float) -> float:
	return sin(t+p*r)+cos(t+p*r*0.894341)

func update_beads() -> void:
	leaf_material.set_shader_parameter("dew_time", clock_time)
	for i in range(beads.size()):
		var bead := beads[i]
		var a: Vector3 = bead.xf * wind_vertex(bead.p[0],bead.colors[0])
		var b: Vector3 = bead.xf * wind_vertex(bead.p[1],bead.colors[1])
		var c: Vector3 = bead.xf * wind_vertex(bead.p[2],bead.colors[2])
		var n := (b-a).cross(c-a).normalized()
		if n.y < 0.0:
			n = -n
		var anchor: Vector3 = a*bead.weights.x+b*bead.weights.y+c*bead.weights.z
		var tangent := n.cross(Vector3.FORWARD).normalized()
		if tangent.length_squared() < 0.1:
			tangent = n.cross(Vector3.RIGHT).normalized()
		var r: float = bead.radius
		var basis := Basis(tangent,n,tangent.cross(n)).scaled_local(Vector3(r,r*0.72,r))
		droplets.multimesh.set_instance_transform(i,Transform3D(basis,anchor+n*r*0.30))

func set_view(view: String) -> void:
	current_view = view
	if view == "overview":
		camera.global_transform = overview_transform
		camera.fov = 70.0
	elif view == "plant":
		camera.fov = 48.0
		camera.global_position = plant_center + Vector3(1.8,2.5,3.0)
		camera.look_at(plant_center + Vector3(0,0.8,0))
	else:
		camera.fov = 42.0
		camera.global_position = hero + hero_normal * 0.29 + Vector3(0.03,0.065,0.20)
		camera.look_at(hero)
	update_status()

func set_dew(enabled: bool) -> void:
	droplets.visible = enabled
	update_status()

func set_local_reflection(enabled: bool) -> void:
	local_reflection = enabled
	# Compare a local forest capture with the original global sky reflection.
	# All direct lighting, geometry, exposure and transmission stay unchanged.
	probe.reflection_mask = 2 if enabled else 0
	update_status()

func create_ui() -> void:
	ui = CanvasLayer.new()
	ui.name = "DewControls"
	add_child(ui)
	var panel := PanelContainer.new()
	panel.position = Vector2(18,18)
	ui.add_child(panel)
	var box := VBoxContainer.new()
	panel.add_child(box)
	var heading := Label.new()
	heading.text = "  FOREST / LEAF DEW  "
	heading.add_theme_font_size_override("font_size",22)
	box.add_child(heading)
	status = Label.new()
	box.add_child(status)
	var row := HBoxContainer.new()
	box.add_child(row)
	for item in [["1  Macro","macro"],["2  Plant","plant"],["3  Forest","overview"]]:
		var button := Button.new()
		button.text = item[0]
		button.pressed.connect(set_view.bind(item[1]))
		row.add_child(button)
	var toggle := Button.new()
	toggle.text = "D  Dew on / off"
	toggle.pressed.connect(func():set_dew(not droplets.visible))
	box.add_child(toggle)
	var light_button := Button.new()
	light_button.text = "L  Local forest / sky reflection"
	light_button.pressed.connect(func():set_local_reflection(not local_reflection))
	box.add_child(light_button)
	var hint := Label.new()
	hint.text = "  Space: pause wind | RMB + WASD: move  \n  Q/E: down/up | Shift: faster | R: reset view  "
	box.add_child(hint)

func update_status() -> void:
	if status:
		status.text = "  %s | %d beads | dew %s | %s  " % [current_view, beads.size(), "ON" if droplets.visible else "OFF", "FOREST reflection" if local_reflection else "SKY reflection"]

func _process(dt: float) -> void:
	if not ready_for_capture:
		return
	if animate:
		clock_time += dt
		update_beads()
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var direction := Vector3(float(Input.is_physical_key_pressed(KEY_D))-float(Input.is_physical_key_pressed(KEY_A)),float(Input.is_physical_key_pressed(KEY_E))-float(Input.is_physical_key_pressed(KEY_Q)),float(Input.is_physical_key_pressed(KEY_S))-float(Input.is_physical_key_pressed(KEY_W)))
		var speed := 0.15 if current_view == "macro" else 3.0
		if Input.is_physical_key_pressed(KEY_SHIFT):
			speed *= 5.0
		camera.position += camera.basis * direction.normalized() * speed * dt

func _unhandled_input(event: InputEvent) -> void:
	if not ready_for_capture:
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		camera.rotation.y -= event.relative.x * 0.002
		camera.rotation.x = clampf(camera.rotation.x-event.relative.y*0.002,-1.5,1.5)
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_1: set_view("macro")
			KEY_2: set_view("plant")
			KEY_3: set_view("overview")
			KEY_D:
				if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
					set_dew(not droplets.visible)
			KEY_L: set_local_reflection(not local_reflection)
			KEY_SPACE: animate = not animate
			KEY_R: set_view(current_view)
			KEY_ESCAPE: Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
