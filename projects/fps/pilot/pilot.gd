extends Node3D

signal benchmark_event(event_name: String, payload: Dictionary)
@export var scene_id := "P01"
@export var kit := "platformer"
var state: Dictionary = {}
var targets: Dictionary = {}
var initial_transforms: Dictionary = {}
var event_log: Array = []
var elapsed := 0.0
var frame := 0
var scripted := false
var playing := false
var busy := false
var adapter: Node
var camera: Camera3D
var config: Dictionary
var capture_dir := ""
var status_label: Label
var last_event := "none"
var initial_camera_transform: Transform3D
var initial_player_transform: Transform3D
var active_level := 1

func _ready() -> void:
	config = JSON.parse_string(FileAccess.get_file_as_string("res://pilot/scenes.json"))[scene_id]
	for target in get_tree().get_nodes_in_group("effect_target"):
		if is_ancestor_of(target):
			targets[target.name] = target
			initial_transforms[target.name] = target.transform
	camera = $Observer
	camera.look_at(Vector3(0, 1, -2))
	initial_camera_transform = camera.transform
	initial_player_transform = $Player.transform
	adapter = $EffectAdapter
	status_label = $HUD/Status
	$HUD/Instructions.text = scene_id + "  " + config.title_en + "\nTAB play / inspect | SPACE event | R reset | 1-3 level | arrows orbit"
	$Player.process_mode = Node.PROCESS_MODE_DISABLED
	$Player/SoundFootsteps.stop()
	if has_node("View"):
		$View.process_mode = Node.PROCESS_MODE_DISABLED
	if kit == "fps":
		$Player.mouse_captured = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	camera.make_current()
	adapter.setup({"scene_id": scene_id, "targets": targets, "environment": $Environment.environment,
		"camera": camera, "root": self, "seed": 20260923, "hud": $HUD/EffectHUD})
	reset(20260923)
	var args := OS.get_cmdline_user_args()
	scripted = "--verify" in args or "--capture" in args
	for arg in args:
		if arg.begins_with("--output="):
			capture_dir = arg.substr(9)
		if arg.begins_with("--level="):
			active_level = clampi(int(arg.substr(8)), 1, 3)
	state.level = active_level
	if scripted:
		call_deferred("run_protocol", "--capture" in args)
	else:
		print("PILOT_READY " + scene_id + " targets=" + str(targets.size()))

func reset(seed_value: int = 20260923) -> void:
	seed(seed_value)
	elapsed = 0.0
	frame = 0
	event_log.clear()
	last_event = "none"
	camera.transform = initial_camera_transform
	$Player.transform = initial_player_transform
	$Player.velocity = Vector3.ZERO
	$Player.gravity = 0.0
	if kit == "fps":
		$Player.rotation_target = Vector3.ZERO
		$Player/Head/Camera.rotation = Vector3.ZERO
	state = {"seed": seed_value, "level": active_level, "elapsed": 0.0, "frame": 0, "wind_strength": 0.2,
		"wind_direction": Vector3(1, 0, 0), "wetness": 0.0, "power": 0.2, "health": 1.0, "scan_enabled": false}
	for key in targets:
		targets[key].transform = initial_transforms[key]
		if targets[key].has_method("reset_target"):
			targets[key].reset_target()
	adapter.reset(state.duplicate(true))
	update_status()

func step(dt: float) -> void:
	assert(dt > 0.0 and dt <= 0.1, "dt must be in (0, 0.1]")
	assert(not busy, "step must not overlap")
	busy = true
	elapsed += dt
	frame += 1
	state.elapsed = elapsed
	state.frame = frame
	adapter.step(dt, state.duplicate(true))
	busy = false
	update_status()

func set_parameters(values: Dictionary) -> void:
	for key in values:
		assert(key in ["level", "wind_strength", "wind_direction", "wetness", "power", "health", "scan_enabled"], "Unknown parameter: " + str(key))
		state[key] = values[key]
		if key == "level": active_level = clampi(int(values[key]), 1, 3)

func emit_event(event_name: String, payload: Dictionary = {}) -> void:
	assert(event_name in config.event_names, "Event not declared for this scene")
	last_event = event_name
	var entry := {"before_step": frame + 1, "completed_frames": frame, "time": elapsed, "event": event_name, "payload": payload.duplicate(true)}
	event_log.append(entry)
	benchmark_event.emit(event_name, payload)
	adapter.on_event(event_name, payload.duplicate(true), state.duplicate(true))
	update_status()

func update_status() -> void:
	if status_label:
		status_label.text = "BASELINE / effect slot not implemented\nL%d | frame %d | %.2fs | last: %s" % [int(state.get("level", 1)), frame, elapsed, last_event]

func _process(delta: float) -> void:
	if scripted:
		return
	step(minf(delta, 0.1))
	if not playing:
		var direction := float(int(Input.is_physical_key_pressed(KEY_RIGHT)) - int(Input.is_physical_key_pressed(KEY_LEFT)))
		if direction != 0:
			camera.position = camera.position.rotated(Vector3.UP, direction * delta)
			camera.look_at(Vector3(0, 1, -2))

func _unhandled_key_input(event: InputEvent) -> void:
	if scripted or not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_TAB:
			playing = not playing
			$HUD/Crosshair.visible = playing and kit == "fps"
			$Player.process_mode = Node.PROCESS_MODE_INHERIT if playing else Node.PROCESS_MODE_DISABLED
			if playing: $Player/SoundFootsteps.play()
			else: $Player/SoundFootsteps.stop()
			if kit == "platformer":
				$View.process_mode = $Player.process_mode
				if playing: $View/Camera.make_current()
			else:
				$Player.mouse_captured = playing
				if playing: $Player/Head/Camera.make_current()
			if not playing: camera.make_current()
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if playing and kit == "fps" else Input.MOUSE_MODE_VISIBLE
		KEY_R:
			reset()
		KEY_1, KEY_2, KEY_3:
			set_parameters({"level": event.keycode - KEY_0})
		KEY_SPACE:
			if not playing:
				var e: Dictionary = config.events[event_log.size() % config.events.size()]
				emit_event(e.name, e.get("payload", {}))

func run_protocol(capture: bool) -> void:
	# Baseline verification only: proves the host contract, not shader task success.
	if capture and DisplayServer.get_name() == "headless":
		push_error("A real rendering display is required for canvas capture")
		get_tree().quit(2)
		return
	if capture_dir.is_empty():
		capture_dir = ProjectSettings.globalize_path("res://../../verification/" + scene_id)
	DirAccess.make_dir_recursive_absolute(capture_dir)
	await get_tree().process_frame
	reset()
	var samples: Array = []
	for n in range(1, 181):
		for entry in config.events:
			if int(entry.frame) == n:
				emit_event(entry.name, entry.get("payload", {}))
		if n == 91:
			camera.position.x += 1.0
			camera.look_at(Vector3(0, 1, -2))
		step(1.0 / 60.0)
		if capture:
			await RenderingServer.frame_post_draw
		else:
			await get_tree().process_frame
		if n in [1, 60, 120, 180]:
			var sample := {"frame": n, "time": elapsed, "last_event": last_event}
			if capture:
				var image := get_viewport().get_texture().get_image()
				assert(not image.is_empty())
				var file := "frame_%03d.png" % n
				var error := image.save_png(capture_dir.path_join(file))
				assert(error == OK)
				sample["image"] = file
			samples.append(sample)
	var log_before_reset := event_log.duplicate(true)
	reset()
	var result := {"scene_id": scene_id, "status": "baseline_ready", "target_count": targets.size(), "targets": targets.keys(),
		"frames": 180, "events": log_before_reset, "samples": samples, "reset_ok": frame == 0 and event_log.is_empty(),
		"rendered": capture, "engine": Engine.get_version_info().string, "renderer": RenderingServer.get_current_rendering_method(),
		"display": DisplayServer.get_name(), "level": active_level, "task_status": "not_run", "note": "Baseline environment validation, not model output or shader correctness."}
	var file := FileAccess.open(capture_dir.path_join("result.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t"))
	file.close()
	print("PILOT_VERIFIED " + JSON.stringify(result))
	# Release context references before the SceneTree begins shutdown.
	targets.clear()
	call_deferred("finish_protocol")

func finish_protocol() -> void:
	for audio in get_tree().root.find_children("*", "AudioStreamPlayer", true, false):
		audio.stop()
		audio.stream = null
	await get_tree().process_frame
	get_tree().quit(0)
