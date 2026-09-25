extends SceneTree

var output := ""
var report := {"stage":"author_preview_not_model_evaluation","model_api_calls":0,"levels":[]}

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):
			output = arg.trim_prefix("--output=")
	call_deferred("verify")

func draw_frame() -> void:
	await process_frame
	await RenderingServer.frame_post_draw

func save_image(path: String) -> void:
	await draw_frame()
	var img := root.get_texture().get_image()
	assert(img.save_png(output.path_join(path)) == OK)

func verify() -> void:
	root.size = Vector2i(960,640)
	root.content_scale_size = Vector2i(960,640)
	assert(change_scene_to_file("res://scenes/L1.tscn") == OK)
	await scene_changed
	await draw_frame()
	var demo = current_scene
	assert(demo.ready_for_capture)
	report.engine = Engine.get_version_info().string
	report.renderer = RenderingServer.get_current_rendering_method()
	report.grass_cards = demo.roots.size()
	report.mesh_vertices_per_card = demo.grass_nodes[0].multimesh.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size()
	demo.hud.hide()
	for level in [1,2,3]:
		DirAccess.make_dir_recursive_absolute(output.path_join("L%d/frames" % level))
		demo.set_level(level)
		demo.set_camera("overview")
		if level == 3:
			demo.set_camera("top")
		for warm in range(12):
			await draw_frame()
		await save_image("L%d/start.png" % level)
		var duration := 11.0 if level == 3 else 4.0
		var captures := int(duration*8)
		for sample in range(captures):
			# Advance exactly 0.125 seconds per animation sample, in bounded steps.
			for substep in range(5):
				demo.step(0.025)
			await save_image("L%d/frames/%03d.png" % [level,sample])
			if sample == 13:
				await save_image("L%d/wind.png" % level)
			if level == 3 and sample in [29,41,55,79,87]:
				await save_image("L3/time_%03d.png" % int(round(demo.elapsed*10)))
		var entry := {"level":level,"effect_steps":demo.frame,"elapsed":demo.elapsed,"animation_frames":captures,"history_samples":demo.samples.size(),"player":str(demo.player_position)}
		demo.reset()
		entry.reset_clears_time_and_history = demo.elapsed == 0 and demo.samples.is_empty() and demo.frame == 0
		assert(entry.reset_clears_time_and_history)
		demo.set_camera("roots")
		for substep in range(70):
			demo.step(0.025)
		await save_image("L%d/roots.png" % level)
		demo.set_parameters({"wind_strength":0.0})
		await save_image("L%d/no_wind.png" % level)
		demo.wind_strength = 0.22
		if level == 2:
			demo.set_parameters({"wind_strength":0.4,"wind_direction":[-0.3,1]})
			await save_image("L2/strong_crosswind.png")
			demo.set_parameters({"wind_strength":0.22,"wind_direction":[1,0.35]})
		report.levels.append(entry)
		print("GRASS_LEVEL_CAPTURED ",level)
	demo.set_level(3)
	demo.set_camera("top")
	demo.set_parameters({"wind_strength":0.0})
	for step_index in range(400):
		demo.step(0.025)
		if step_index == 149:
			await save_image("L3/interaction_without_wind.png")
	await save_image("L3/recovered_without_wind.png")
	report.extra_cases = ["L2 strong crosswind","L3 interaction without wind","L3 recovered without wind"]
	demo.wind_strength = 0.22
	# The starter must be a separate, genuinely static material, not L1 reference.
	demo.use_reference = false
	demo.load_effect()
	demo.reset()
	demo.set_level(1)
	demo.set_camera("overview")
	await save_image("starter.png")
	report.starter_shader = demo.material.shader.resource_path
	demo.hud.show()
	await save_image("controls.png")
	var file := FileAccess.open(output.path_join("report.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	file.close()
	print("GRASS_VERIFY_COMPLETE")
	demo.queue_free()
	await draw_frame()
	quit()
