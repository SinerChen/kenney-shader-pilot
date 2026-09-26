extends SceneTree

func _initialize():
	root.set_meta("benchmark_manual",true)
	call_deferred("run")

func run():
	var args=OS.get_cmdline_user_args()
	var request=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var out=args[1]
	DirAccess.make_dir_recursive_absolute(out)
	root.size=Vector2i(int(request.get("width",640)),int(request.get("height",360)))
	var fixture=load("res://fixture/entry.tscn").instantiate()
	root.add_child(fixture)
	await process_frame
	fixture.set_capture_size(root.size)
	var adapter=fixture.adapter
	if request.has("config"):
		adapter.reset(request.config)
		fixture.startup=adapter.mount(fixture)
	if request.has("camera"):
		var c=request.camera
		fixture.camera.position=Vector3(c.position[0],c.position[1],c.position[2])
		fixture.camera.look_at(Vector3(c.look_at[0],c.look_at[1],c.look_at[2]))
		fixture.sync_cameras()
		# This author/tool camera choice is applied before the protected baseline.
		fixture.baseline=fixture.snapshot()
	var recorder=load("res://fixture/evidence.gd").new()
	recorder.directory=out
	var snapshots: Array=[]
	var frames: Array=[]
	var dt=float(request.get("dt",1.0/30.0))
	var count=int(request.get("frames",90))
	var ready=fixture.startup.get("status","")=="OK"
	var start=Time.get_ticks_usec()
	for frame in count:
		var events: Array=[]
		for item in request.get("events",fixture.demo.events):
			if int(item.tick)==frame:events.append(item.event)
		if ready:
			if frame>0:adapter.advance(dt,events)
			adapter.update_display()
		fixture.sync_cameras()
		await process_frame
		await RenderingServer.frame_post_draw
		var path=out.path_join("frame_%05d.png" % frame)
		root.get_texture().get_image().save_png(path)
		frames.append({"frame":frame,"time":max(0,frame)*dt,"file":path.get_file()})
		if frame in [0,count-1]:
			snapshots.append({"frame":frame,"state":recorder.record(adapter.get_outputs()),"textures":recorder.bound_textures(fixture,frame)})
		if frame in [0,count-1] and not fixture.capture_views.is_empty():
			for name in fixture.capture_views:
				fixture.capture_views[name].get_texture().get_image().save_png(out.path_join(name+"_%05d.png" % frame))
	var capture_masks={}
	for name in fixture.capture_views:capture_masks[name]=fixture.capture_views[name].get_node("Camera3D").cull_mask
	var pixel=fixture.camera.unproject_position(Vector3(0,0,0))
	var report={"snapshots":snapshots,"capture_masks":capture_masks,"ground_center_pixel":[pixel.x,pixel.y],"status":"RENDERED" if ready else "STARTER_NOT_IMPLEMENTED","startup":fixture.startup,"frames":frames,
	            "elapsed_s":float(Time.get_ticks_usec()-start)/1000000.0,"protection":fixture.protection_report(),
	            "engine":Engine.get_version_info(),"gpu":RenderingServer.get_video_adapter_name()}
	var file=FileAccess.open(out.path_join("result.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	fixture.queue_free()
	await process_frame
	quit()
