extends SceneTree

func _initialize():call_deferred("run")

func run():
	var out=OS.get_cmdline_user_args()[0]
	var scene=load("res://Main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	var result={}
	var paths=["Main Terrain/Plane_031","Main Terrain/BezierCurve_001","Decorations-Forest/Tree_small_2/Tree small 2","Decorations-Forest/Tree_small_1/Tree small 1"]
	for index in paths.size():
		var node=scene.get_node(paths[index])
		var rows=[]
		for surface in node.mesh.get_surface_count():
			var arrays=node.mesh.surface_get_arrays(surface)
			var info={}
			for pair in [["vertices",Mesh.ARRAY_VERTEX],["normals",Mesh.ARRAY_NORMAL],["uv",Mesh.ARRAY_TEX_UV],["uv2",Mesh.ARRAY_TEX_UV2],["color",Mesh.ARRAY_COLOR],["indices",Mesh.ARRAY_INDEX]]:
				var value=arrays[pair[1]]
				if value==null:continue
				var name="geometry_%d_%d_%s.bin" % [index,surface,pair[0]]
				var f=FileAccess.open(out.path_join(name),FileAccess.WRITE)
				f.store_buffer(value.to_byte_array())
				info[pair[0]]={"file":name,"length":value.size(),"type":type_string(typeof(value))}
			rows.append(info)
		result[paths[index]]=rows
	var f=FileAccess.open(out.path_join("geometry.json"),FileAccess.WRITE)
	f.store_string(JSON.stringify(result,"  "))
	scene.queue_free()
	await process_frame
	quit()
