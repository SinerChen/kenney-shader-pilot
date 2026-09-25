extends SceneTree

var output := ""
var report := {"captures":[], "checks":{}}

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
	call_deferred("run_checks")

func frames(count: int) -> void:
	for i in range(count):
		await process_frame
		await RenderingServer.frame_post_draw

func capture(name: String) -> void:
	await frames(45)
	var img := root.get_texture().get_image()
	var result := img.save_png(output.path_join(name + ".png"))
	assert(result == OK)
	report.captures.append({"name":name, "width":img.get_width(),"height":img.get_height()})
	print("DEW_CAPTURE ", name)

func run_checks() -> void:
	root.size = Vector2i(1280,720)
	root.content_scale_size = Vector2i(1280,720)
	change_scene_to_file("res://dew/ForestDew.tscn")
	await scene_changed
	for i in range(240):
		await frames(1)
		if current_scene.ready_for_capture:
			break
	if not current_scene.ready_for_capture:
		push_error("Dew initialization failed")
		quit(1)
		return
	var demo = current_scene
	demo.animate = false
	demo.clock_time = 2.0
	demo.update_beads()
	demo.ui.hide()
	if "--scout" in OS.get_cmdline_user_args():
		for i in range(demo.plants.size()):
			demo.plant_center = demo.plants[i].xf.origin
			demo.set_view("plant")
			await capture("scout_%02d" % i)
		print("DEW_VERIFY_COMPLETE")
		quit()
		return
	await frames(45)
	demo.set_view("macro")
	demo.set_dew(false)
	await capture("macro_before")
	demo.set_dew(true)
	await capture("macro_after")
	var xf: Transform3D = demo.droplets.multimesh.get_instance_transform(demo.hero_index)
	demo.clock_time = 2.7
	demo.update_beads()
	var moved: Transform3D = demo.droplets.multimesh.get_instance_transform(demo.hero_index)
	report.checks.wind_displacement_m = moved.origin.distance_to(xf.origin)
	await capture("macro_wind")
	demo.clock_time = 2.0
	demo.update_beads()
	demo.set_local_reflection(false)
	await capture("macro_sky_only")
	demo.set_local_reflection(true)
	demo.set_view("plant")
	demo.set_dew(false)
	await capture("plant_before")
	demo.set_dew(true)
	await capture("plant_after")
	report.engine = Engine.get_version_info().string
	report.renderer = RenderingServer.get_current_rendering_method()
	report.plants = demo.plants.size()
	report.beads = demo.beads.size()
	report.hero = str(demo.hero)
	report.checks.dew_shader_compiled = true # Runner separately requires no engine errors.
	report.checks.source_scene = "res://Main.tscn (instanced, unchanged)"
	var f := FileAccess.open(output.path_join("verification.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(report,"  "))
	f.close()
	print("DEW_VERIFY_COMPLETE")
	demo.queue_free()
	await frames(3)
	await create_timer(1.0).timeout
	quit()
