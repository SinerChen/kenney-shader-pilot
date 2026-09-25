extends SceneTree
## Private render driver. Scene roots can optionally expose preview_reset/preview_step.

var request: Dictionary
var output_dir: String
var custom_camera: Camera3D
var captures: Array = []
var environment_setup: RefCounted
var samples: Array = []

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--render-request="):
			request = JSON.parse_string(FileAccess.get_file_as_string(arg.trim_prefix("--render-request=")))
	if request.is_empty():
		push_error("Missing render request")
		quit(2)
		return
	output_dir = str(request.output_dir)
	call_deferred("capture")

func vec(value: Array) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))

func arr(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func set_view(frame: int) -> void:
	if not is_instance_valid(custom_camera):
		return
	var settings: Dictionary = request.camera.duplicate(true)
	var track: Array = request.camera_track
	if not track.is_empty():
		var a: Dictionary = track[0]
		var b: Dictionary = track[0]
		var fraction := 0.0
		if frame >= int(track[-1].frame):
			a = track[-1]
			b = a
		elif frame > int(track[0].frame):
			for index in range(track.size() - 1):
				if frame >= int(track[index].frame) and frame <= int(track[index + 1].frame):
					a = track[index]
					b = track[index + 1]
					fraction = float(frame - int(a.frame)) / float(int(b.frame) - int(a.frame))
					break
		settings.position = arr(vec(a.position).lerp(vec(b.position), fraction))
		settings.look_at = arr(vec(a.look_at).lerp(vec(b.look_at), fraction))
	custom_camera.global_position = vec(settings.position)
	custom_camera.look_at(vec(settings.look_at), vec(settings.up).normalized())
	custom_camera.force_update_transform()
	custom_camera.make_current()

func draw() -> void:
	await process_frame
	await RenderingServer.frame_post_draw

func fail(message: String) -> void:
	push_error(message)
	quit(2)

func capture() -> void:
	root.size = Vector2i(int(request.resolution[0]), int(request.resolution[1]))
	root.content_scale_size = root.size
	paused = true
	if change_scene_to_file("res://" + str(request.scene)) != OK:
		fail("Unable to load entry scene")
		return
	await scene_changed
	var demo := current_scene
	demo.process_mode = Node.PROCESS_MODE_PAUSABLE
	var inputs: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://inputs/test_input.json"))
	# Original hosts may create meshes using deferred calls; finish that setup first.
	if FileAccess.file_exists("res://scene/environment.json") and request.scene == "scene/main.tscn":
		await draw()
		environment_setup = load("res://scene/environment_setup.gd").new()
		var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://scene/environment.json"))
		environment_setup.configure(demo, config, inputs)
	var manual: bool = demo.has_method("preview_step")
	if demo.has_method("preview_reset"):
		demo.call("preview_reset", inputs)
	if request.camera != null:
		custom_camera = Camera3D.new()
		custom_camera.name = "RenderObservationCamera"
		root.add_child(custom_camera)
		custom_camera.projection = Camera3D.PROJECTION_ORTHOGONAL if str(request.camera.projection) == "orthogonal" else Camera3D.PROJECTION_PERSPECTIVE
		custom_camera.fov = float(request.camera.fov_degrees)
		custom_camera.size = float(request.camera.orthogonal_size)
		custom_camera.near = float(request.camera.near)
		custom_camera.far = float(request.camera.far)
		set_view(1)
	await draw()
	if root.get_camera_3d() == null:
		fail("Scene has no active 3D camera; provide camera.position and camera.look_at")
		return
	# JSON numbers are floats; normalize before typed frame membership checks.
	var frames: Array[int] = []
	for value in request.frames:
		frames.append(int(value))
	var initial_frames := Engine.get_process_frames()
	for frame in range(1, frames[-1] + 1):
		set_view(frame)
		if environment_setup:
			environment_setup.step(float(request.dt_seconds))
		if manual:
			demo.call("preview_step", float(request.dt_seconds))
		else:
			paused = false
		await draw()
		paused = true
		if frame in frames:
			if environment_setup:
				samples.append({"frame": frame, "elapsed_s": frame * float(request.dt_seconds), "output": environment_setup.sample()})
			var filename := "frame_%04d.png" % frame
			var rendered := root.get_texture().get_image()
			if rendered.is_empty() or rendered.save_png(output_dir.path_join(filename)) != OK:
				fail("Unable to save actual rendered image")
				return
			var camera := root.get_camera_3d()
			captures.append({"frame": frame, "elapsed_s": frame * float(request.dt_seconds),
				"image": filename, "width": rendered.get_width(), "height": rendered.get_height(),
				"camera": {"position": arr(camera.global_position), "forward": arr(-camera.global_basis.z),
					"up": arr(camera.global_basis.y), "projection": int(camera.projection),
					"fov_degrees": camera.fov, "orthogonal_size": camera.size, "near": camera.near, "far": camera.far}})
	var report := {"completed": true, "captures": captures, "engine": Engine.get_version_info().string,
		"renderer": RenderingServer.get_current_rendering_method(), "display": DisplayServer.get_name(),
		"step_mode": "manual_preview_step" if manual else "native_fixed_fps",
		"dt_seconds": request.dt_seconds, "process_frames": Engine.get_process_frames() - initial_frames,
		"initialization": "paused scene initialization; shader global TIME may include initialization time",
		"scene": request.scene, "visual_quality": "not_scored"}
	if environment_setup:
		report.environment = environment_setup.report
		var sample_file := FileAccess.open(output_dir.path_join("samples.json"), FileAccess.WRITE)
		sample_file.store_string(JSON.stringify({"samples": samples, "source": "candidate_sample", "scored": false}, "  "))
		sample_file.close()
	var file := FileAccess.open(output_dir.path_join("capture.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  "))
	file.close()
	environment_setup = null
	current_scene = null
	demo.queue_free()
	if is_instance_valid(custom_camera):
		custom_camera.queue_free()
	await draw()
	for unused in range(3):
		await process_frame
	# Original demo callbacks may outlive their nodes briefly.
	await create_timer(1.0).timeout
	print("MODEL_RENDER_COMPLETE")
	quit(0)
