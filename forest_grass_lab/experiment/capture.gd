extends SceneTree

var config: Dictionary
var output: String

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--capture="):
			var path := arg.trim_prefix("--capture=")
			config = JSON.parse_string(FileAccess.get_file_as_string(path))
			output = path.get_base_dir()
	call_deferred("capture")

func draw() -> void:
	await process_frame
	await RenderingServer.frame_post_draw

func image(path: String) -> void:
	assert(root.get_texture().get_image().save_png(path) == OK)

func parameters(demo: Node, values: Dictionary) -> void:
	if values.has("camera"):
		demo.set_camera(values.camera)
	demo.set_parameters(values)

func capture() -> void:
	root.size = Vector2i(768,512)
	root.content_scale_size = Vector2i(768,512)
	var results := []
	for item in config.cases:
		assert(change_scene_to_file("res://scenes/L%d.tscn" % int(config.level)) == OK)
		await scene_changed
		await draw()
		var demo = current_scene
		assert(demo.ready_for_capture and not demo.use_reference)
		demo.hud.hide()
		parameters(demo,item.params)
		var folder: String = output.path_join(item.name)
		DirAccess.make_dir_recursive_absolute(folder)
		var frames: Array = []
		for value in item.frames:
			frames.append(int(value))
		var animation: bool = item.get("animation",false)
		if animation:
			DirAccess.make_dir_recursive_absolute(folder.path_join("animation"))
		for n in range(1,int(frames[-1])+1):
			for event in item.get("schedule",[]):
				if int(event.frame) == n:
					parameters(demo,event.set)
			var points: Array = item.get("events",[])
			if not points.is_empty():
				var t := float(n-1)/60.0
				var pos: Array = points[-1].player_position
				for k in range(points.size()-1):
					if t <= float(points[k+1].time):
						var a: Array = points[k].player_position
						var b: Array = points[k+1].player_position
						var f := clampf((t-float(points[k].time))/(float(points[k+1].time)-float(points[k].time)),0.0,1.0)
						pos = [lerpf(a[0],b[0],f),lerpf(a[1],b[1],f),lerpf(a[2],b[2],f)]
						break
				parameters(demo,{"player_position":pos})
			demo.step(1.0/60.0)
			await draw()
			if n in frames:
				image(folder.path_join("%03d.png" % n))
			if animation and n % 8 == 0:
				image(folder.path_join("animation/%03d.png" % n))
		results.append({"name":item.name,"frames":frames,"steps":demo.frame,"elapsed":demo.elapsed})
		print("CASE_COMPLETE ",item.name)
		current_scene = null
		demo.queue_free()
		await draw()
	var file := FileAccess.open(output.path_join("capture.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"cases":results,"renderer":RenderingServer.get_current_rendering_method(),"completed":true},"  "))
	file.close()
	print("GRASS_EVALUATE_COMPLETE")
	quit()
