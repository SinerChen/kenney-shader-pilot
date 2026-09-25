extends SceneTree
func _initialize() -> void:
	var scene = load("res://Meshes/Plants/Grass1.glb").instantiate()
	var mesh = scene.find_children("*","MeshInstance3D",true,false)[0].mesh
	print("IMPORTED_UV ",mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV])
	scene.free()
	quit()
