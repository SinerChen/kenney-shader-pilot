extends SceneTree

var output_dir: String
var scene_path: String
var click_play := false

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output_dir = arg.trim_prefix("--output=")
		if arg.begins_with("--scene="):
			scene_path = arg.trim_prefix("--scene=")
		if arg == "--play":
			click_play = true
	call_deferred("capture_scene")

func capture_scene() -> void:
	if scene_path.is_empty():
		scene_path = ProjectSettings.get_setting("application/run/main_scene", "")
	if change_scene_to_file(scene_path) != OK:
		quit(1)
		return
	await scene_changed
	if click_play:
		var activated := false
		for node in current_scene.get_children():
			if node.has_method("_on_play_pressed"):
				node.call("_on_play_pressed")
				activated = true
		if not activated:
			push_error("TPS Play action unavailable")
			quit(3)
			return
		var entered_level := false
		for loading_frame in range(1800):
			await process_frame
			await RenderingServer.frame_post_draw
			if not current_scene.find_children("*", "CharacterBody3D", true, false).is_empty():
				entered_level = true
				break
		if not entered_level:
			push_error("TPS Play did not enter gameplay")
			quit(4)
			return
	if scene_path == "res://scenes/sponza.scn":
		# Dismiss only the welcome panel, keeping the default High preset.
		for node in current_scene.find_children("*", "Control", true, false):
			if node.has_method("_on_ConfirmButton_pressed"):
				node.call("_on_ConfirmButton_pressed")
	if scene_path == "res://MainScene.tscn":
		for node in current_scene.find_children("*", "Control", true, false):
			if node.has_method("_on_res_selected"):
				# Capture at native resolution instead of the demo's default 720p target.
				node.call("_on_res_selected", 0)
	if scene_path == "res://example/boujie_water_shader/water_shader_examples.tscn":
		# Preview only: the native launcher retains the original help overlay.
		current_scene.get_node("HUD").hide()
	root.mode = Window.MODE_WINDOWED
	root.size = Vector2i(960, 540)
	root.content_scale_size = Vector2i(960, 540)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	DirAccess.make_dir_recursive_absolute(output_dir)
	var captures: Array = []
	for frame in range(1, 121):
		await process_frame
		await RenderingServer.frame_post_draw
		if frame in [30, 120]:
			var file_name := "frame_%03d.png" % frame
			var rendered := root.get_texture().get_image()
			var result := rendered.save_png(output_dir.path_join(file_name))
			if result != OK:
				push_error("Could not save screenshot")
				quit(2)
				return
			captures.append({"frame": frame, "image": file_name, "width": rendered.get_width(), "height": rendered.get_height()})
	var camera := root.get_camera_3d()
	var report := {
		"scene": scene_path, "frames": 120, "engine": Engine.get_version_info().string,
		"renderer": RenderingServer.get_current_rendering_method(),
		"display": DisplayServer.get_name(), "captures": captures,
		"camera": str(camera.get_path()) if camera else "",
		"nodes": get_node_count(), "model_api_calls": 0,
		"entered_via_play": click_play,
		"scope": "Scene loading and GPU rendering only; no model evaluation or shader correctness score."
	}
	var file := FileAccess.open(output_dir.path_join("capture.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t") + "\n")
	file.close()
	print("SCENE_CAPTURE_COMPLETE ", scene_path)
	if is_instance_valid(current_scene):
		current_scene.queue_free()
	for unused in range(3):
		await process_frame
	# Let outstanding demo timers release their callbacks before engine shutdown.
	await create_timer(1.0).timeout
	quit()
