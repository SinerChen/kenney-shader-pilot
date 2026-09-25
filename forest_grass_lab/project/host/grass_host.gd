extends Node3D
## Fixed host: assets, replay inputs and display. All grass motion is in effect/.

@export_range(1,3) var level := 1
const SEED := 20260923
const HISTORY_SIZE := 32
const CYCLE_SECONDS := 11.0
var elapsed := 0.0
var frame := 0
var playing := true
var manual_player := false
var manual_step := false
var reference_directory := ""
var use_reference := false
var wind_strength := 0.22
var wind_speed := 1.6
var wind_direction := Vector2(1.0,0.35)
var interaction_radius := 0.95
var interaction_strength := 0.95
var player_position := Vector3(-4,0,0)
var samples: Array[Dictionary] = []
var next_sample_time := 0.0
var material: ShaderMaterial
var grass_nodes: Array[MultiMeshInstance3D] = []
var roots: Array[Vector3] = []
var camera: Camera3D
var environment: WorldEnvironment
var player: Node3D
var hud: CanvasLayer
var status: Label
var description: Label
var mode_button: Button
var pause_button: Button
var ready_for_capture := false
var camera_view := "overview"
var fixed_geometry: Node3D

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--reference-dir="):
			reference_directory = arg.trim_prefix("--reference-dir=")
			use_reference = true
		if arg.begins_with("--level="):
			level = clampi(int(arg.trim_prefix("--level=")),1,3)
		if arg == "--manual-step":
			manual_step = true
	create_environment()
	create_ground()
	material = ShaderMaterial.new()
	load_effect()
	create_grass()
	create_player()
	create_hud()
	reset()
	ready_for_capture = true
	print("GRASS_LAB_READY level=",level," reference=",use_reference," cards=",roots.size())

func create_environment() -> void:
	environment = WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("293c38")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("b6d1d0")
	env.ambient_light_energy = 0.65
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.environment = env
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52,-30,0)
	sun.light_color = Color("fff1cc")
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 30
	add_child(sun)
	camera = Camera3D.new()
	camera.near = 0.04
	camera.far = 40
	add_child(camera)
	camera.make_current()
	set_camera("overview")

func plain_material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.9
	return mat

func box_at(size: Vector3, point: Vector3, color: Color, parent: Node3D) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	node.mesh = mesh
	node.material_override = plain_material(color)
	node.position = point
	parent.add_child(node)
	return node

func create_ground() -> void:
	fixed_geometry = Node3D.new()
	fixed_geometry.name = "FixedGroundAndMarkers"
	add_child(fixed_geometry)
	box_at(Vector3(7.2,0.18,6.8),Vector3(0,-0.10,0),Color("55462e"),fixed_geometry)
	# Sparse grid/edge markers make sliding roots and local influence visible.
	for x in range(-3,4):
		box_at(Vector3(0.018,0.003,6.4),Vector3(x,0.001,0),Color("736747"),fixed_geometry)
	for z in range(-3,4):
		box_at(Vector3(6.8,0.003,0.018),Vector3(0,0.001,z),Color("736747"),fixed_geometry)
	for i in range(5):
		var x := float(i-2)*1.1
		box_at(Vector3(0.07,0.016,0.30),Vector3(x,0.01,2.65),Color("8ccbc4"),fixed_geometry)
	box_at(Vector3(6.8,0.08,0.08),Vector3(0,0.01,-3.3),Color("806543"),fixed_geometry)
	box_at(Vector3(6.8,0.08,0.08),Vector3(0,0.01,3.3),Color("806543"),fixed_geometry)
	add_label("ROOT CHECK",Vector3(0,0.08,3.13),0.003)
	add_label("PLAYER PATH",Vector3(-2.8,0.10,-0.3),0.003)

func add_label(text: String, point: Vector3, pixel: float) -> void:
	var label := Label3D.new()
	label.text = text
	label.position = point
	label.pixel_size = pixel
	label.font_size = 28
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.modulate = Color("d2e8db")
	fixed_geometry.add_child(label)

func source_vector(v: Array) -> Vector3:
	return Vector3(v[0],v[1],v[2])

func make_card(card: Dictionary) -> ArrayMesh:
	var p: Array[Vector3] = []
	var uv: Array[Vector2] = []
	for v in card.positions:
		p.append(source_vector(v))
	for v in card.uv:
		uv.append(Vector2(v[0],v[1]))
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var center := (p[0]+p[1])*0.5
	for y in range(19):
		var h := float(y)/18.0
		for x in range(5):
			var s := float(x)/4.0
			var bottom := p[0].lerp(p[1],s)
			var top := p[3].lerp(p[2],s)
			var position := bottom.lerp(top,h)-center
			position.y -= bottom.y-center.y
			position *= 4.0
			var texture_uv := uv[0].lerp(uv[1],s).lerp(uv[3].lerp(uv[2],s),h)
			surface.set_uv(texture_uv)
			surface.set_uv2(Vector2(s,h))
			surface.set_normal((p[1]-p[0]).cross(top-bottom).normalized())
			surface.add_vertex(position)
	for y in range(18):
		for x in range(4):
			var i := y*5+x
			for idx in [i,i+5,i+1,i+1,i+5,i+6]:
				surface.add_index(idx)
	return surface.commit()

func create_grass() -> void:
	var cards: Array = JSON.parse_string(FileAccess.get_file_as_string("res://assets/grass_cards.json"))
	var groups: Array = [[],[],[],[]]
	var rng := RandomNumberGenerator.new()
	rng.seed = SEED
	for z in range(11):
		for x in range(15):
			var root := Vector3(-2.75+x*0.39+rng.randf_range(-0.10,0.10),0.0,-2.15+z*0.39+rng.randf_range(-0.10,0.10))
			for crossed in range(2):
				var yaw := rng.randf_range(0,TAU)
				var scale := rng.randf_range(0.83,1.20)
				var xf := Transform3D(Basis(Vector3.UP,yaw).scaled(Vector3.ONE*scale),root)
				groups[(x+z+crossed)%4].append({"xf":xf,"phase":rng.randf()})
				roots.append(root)
	for i in range(5):
		var root := Vector3(float(i-2)*1.1,0.0,2.65)
		groups[0].append({"xf":Transform3D(Basis.IDENTITY,root),"phase":float(i)*0.18})
		roots.append(root)
	for i in range(4):
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = make_card(cards[i])
		mm.instance_count = groups[i].size()
		for j in range(groups[i].size()):
			mm.set_instance_transform(j,groups[i][j].xf)
			mm.set_instance_custom_data(j,Color(groups[i][j].phase,0,0,1))
		var node := MultiMeshInstance3D.new()
		node.name = "GrassCards_%d" % i
		node.multimesh = mm
		node.material_override = material
		node.extra_cull_margin = 2.0
		add_child(node)
		grass_nodes.append(node)

func create_player() -> void:
	player = Node3D.new()
	player.name = "PlayerProxy"
	add_child(player)
	var capsule := MeshInstance3D.new()
	var mesh := CapsuleMesh.new()
	mesh.radius = 0.22
	mesh.height = 1.45
	capsule.mesh = mesh
	capsule.position.y = 0.725
	capsule.material_override = plain_material(Color("d87c39"))
	player.add_child(capsule)
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = interaction_radius-0.014
	torus.outer_radius = interaction_radius+0.014
	torus.rings = 48
	torus.ring_segments = 6
	ring.mesh = torus
	ring.position.y = 0.018
	ring.material_override = plain_material(Color("e7ad5a"))
	player.add_child(ring)

func load_effect() -> void:
	if use_reference and not reference_directory.is_empty():
		var path := reference_directory.path_join("L%d.gdshader" % level)
		if not FileAccess.file_exists(path):
			push_error("Missing author reference: " + path)
			return
		var shader := Shader.new()
		shader.code = FileAccess.get_file_as_string(path)
		material.shader = shader
	else:
		material.shader = load("res://effect/grass.gdshader")
	material.set_shader_parameter("grass_albedo",load("res://assets/Grass_BaseColor.png"))
	material.set_shader_parameter("grass_orm",load("res://assets/Grass_ORM.png"))

func reset() -> void:
	elapsed = 0.0
	frame = 0
	samples.clear()
	next_sample_time = 0.0
	player_position = Vector3(-4,0,0)
	if player:
		player.visible = level == 3
	push_inputs()
	update_hud()

func set_level(value: int) -> void:
	level = clampi(value,1,3)
	load_effect()
	reset()

func set_parameters(values: Dictionary) -> void:
	if values.has("wind_strength"):
		wind_strength = clampf(values.wind_strength,0,0.45)
	if values.has("wind_speed"):
		wind_speed = clampf(values.wind_speed,0,3)
	if values.has("wind_direction"):
		wind_direction = Vector2(values.wind_direction[0],values.wind_direction[1])
	if values.has("player_position"):
		player_position = Vector3(values.player_position[0],0,values.player_position[2])
		manual_player = true
	push_inputs()

func step(dt: float) -> void:
	assert(dt > 0 and dt <= 0.1)
	elapsed += dt
	frame += 1
	if level == 3:
		if not manual_player:
			var progress := clampf((elapsed-1.0)/5.5,0,1)
			player_position = Vector3(lerpf(-4.0,4.0,progress),0,0)
		if elapsed >= next_sample_time:
			samples.push_front({"point":player_position,"time":elapsed})
			if samples.size() > HISTORY_SIZE-1:
				samples.pop_back()
			next_sample_time = elapsed+0.1
	push_inputs()
	update_hud()

func push_inputs() -> void:
	if material == null:
		return
	material.set_shader_parameter("elapsed",elapsed)
	material.set_shader_parameter("wind_strength",wind_strength)
	material.set_shader_parameter("wind_speed",wind_speed)
	material.set_shader_parameter("wind_direction",wind_direction)
	material.set_shader_parameter("interaction_radius",interaction_radius)
	material.set_shader_parameter("interaction_strength",interaction_strength)
	material.set_shader_parameter("player_position",player_position)
	var history: Array[Vector4] = []
	history.append(Vector4(player_position.x,player_position.z,0.0,1.0 if level == 3 else 0.0))
	for i in range(HISTORY_SIZE-1):
		if i < samples.size():
			var s := samples[i]
			history.append(Vector4(s.point.x,s.point.z,elapsed-s.time,1))
		else:
			history.append(Vector4.ZERO)
	material.set_shader_parameter("player_history",history)
	if player:
		player.position = player_position

func set_camera(view: String) -> void:
	camera_view = view
	if view == "roots":
		camera.position = Vector3(1.7,1.5,5.5)
		camera.look_at(Vector3(0,0.35,2.65))
		camera.fov = 46
	elif view == "top":
		camera.position = Vector3(0,7,4.2)
		camera.look_at(Vector3.ZERO)
		camera.fov = 48
	else:
		camera.position = Vector3(6.6,5.0,7.5)
		camera.look_at(Vector3(0,0.1,0.2))
		camera.fov = 48

func add_button(row: HBoxContainer, title: String, action: Callable) -> Button:
	var button := Button.new()
	button.text = title
	button.focus_mode = Control.FOCUS_NONE
	button.pressed.connect(action)
	row.add_child(button)
	return button

func create_hud() -> void:
	hud = CanvasLayer.new()
	add_child(hud)
	var panel := PanelContainer.new()
	panel.position = Vector2(15,12)
	hud.add_child(panel)
	var box := VBoxContainer.new()
	panel.add_child(box)
	var title := Label.new()
	title.text = "  FOREST GRASS LAB / L1 > L2 > L3  "
	title.add_theme_font_size_override("font_size",21)
	box.add_child(title)
	status = Label.new()
	box.add_child(status)
	description = Label.new()
	box.add_child(description)
	var row := HBoxContainer.new()
	box.add_child(row)
	for value in [1,2,3]:
		add_button(row,"L%d" % value,set_level.bind(value))
	mode_button = add_button(row,"",func():
		if not reference_directory.is_empty():
			use_reference = not use_reference
			load_effect()
			reset())
	mode_button.disabled = reference_directory.is_empty()
	pause_button = add_button(row,"Pause",func():playing = not playing; update_hud())
	add_button(row,"Reset",reset)
	var cameras := HBoxContainer.new()
	box.add_child(cameras)
	add_button(cameras,"Whole patch",set_camera.bind("overview"))
	add_button(cameras,"Root close-up",set_camera.bind("roots"))
	add_button(cameras,"Top view",set_camera.bind("top"))
	add_button(cameras,"Replay / WASD",func():manual_player = not manual_player; update_hud())
	var wind_row := HBoxContainer.new()
	box.add_child(wind_row)
	add_button(wind_row,"Wind on / off",func():
		wind_strength = 0.0 if wind_strength > 0.0 else 0.22
		push_inputs()
		update_hud())
	add_button(wind_row,"Reverse wind",func():wind_direction = -wind_direction; push_inputs())
	var hint := Label.new()
	hint.text = "  Click buttons here. Keys work in this scene window: 1/2/3, Space, R.  \n  WASD moves the orange player in manual mode. No API connected.  "
	box.add_child(hint)

func update_hud() -> void:
	if not status:
		return
	status.text = "  %s | L%d | %.1fs | wind %.2f | %s  " % ["AUTHOR REFERENCE" if use_reference else "STATIC STARTER",level,elapsed,wind_strength,"WASD player" if manual_player else "Replay"]
	description.text = "  " + ["Wind motion; root anchoring is not yet required.","Keep roots fixed; grass tips sway in the wind.","Keep roots fixed; push away from player; recover after passing."][level-1] + "  "
	mode_button.text = "Show starter" if use_reference else "Show reference"
	pause_button.text = "Resume" if not playing else "Pause"

func _process(dt: float) -> void:
	if not ready_for_capture or manual_step or not playing:
		return
	if manual_player and level == 3:
		var move := Vector3(float(Input.is_physical_key_pressed(KEY_D))-float(Input.is_physical_key_pressed(KEY_A)),0,float(Input.is_physical_key_pressed(KEY_S))-float(Input.is_physical_key_pressed(KEY_W)))
		player_position += move.normalized()*1.6*minf(dt,0.05)
		player_position.x = clampf(player_position.x,-4,4)
		player_position.z = clampf(player_position.z,-3,3)
	if elapsed >= CYCLE_SECONDS and not manual_player:
		reset()
	step(minf(dt,0.05))

func _input(event: InputEvent) -> void:
	if not ready_for_capture or not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.physical_keycode:
		KEY_1: set_level(1)
		KEY_2: set_level(2)
		KEY_3: set_level(3)
		KEY_SPACE: playing = not playing; update_hud()
		KEY_R: reset()
