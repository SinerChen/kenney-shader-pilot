extends SceneTree

func _initialize() -> void:
	call_deferred("inspect_scene")

func inspect_scene() -> void:
	change_scene_to_file("res://Main.tscn")
	await scene_changed
	await process_frame
	var camera := root.get_camera_3d()
	var candidates: Array = []
	var materials := {}
	for node in current_scene.find_children("*", "MultiMeshInstance3D", true, false):
		if node.global_position.distance_to(camera.global_position) > 70.0:
			continue
		var mm: MultiMesh = node.multimesh
		if mm == null or mm.mesh == null:
			continue
		var mesh: Mesh = mm.mesh
		var mat := mesh.surface_get_material(0)
		var mat_path := mat.resource_path if mat else "null"
		materials[mat_path] = materials.get(mat_path, 0) + mm.instance_count
		if mat == null or not "fern" in mat.resource_path.to_lower():
			continue
		for i in range(mm.instance_count):
			var xf: Transform3D = node.global_transform * mm.get_instance_transform(i)
			var dist: float = xf.origin.distance_to(camera.global_position)
			if dist < 10000.0:
				candidates.append({"path":str(node.get_path()),"instance":i,"distance":dist,"position":str(xf.origin),"transform":str(xf),"aabb":str(mesh.get_aabb()),"mat":mat.resource_path,"surfaces":mesh.get_surface_count(),"vertices":mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size()})
	candidates.sort_custom(func(a,b):return a.distance < b.distance)
	var out := FileAccess.open("res://dew/inspection.json", FileAccess.WRITE)
	out.store_string(JSON.stringify({"camera":str(camera.global_position),"fern_count":candidates.size(),"nearest":candidates.slice(0,30),"materials":materials},"  "))
	print("DEW_INSPECTION_COMPLETE ", candidates.size())
	quit()
