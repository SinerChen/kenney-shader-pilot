extends "res://effect/main.gd"

func configure(root: Node, inputs: Dictionary) -> void:
	super.configure(root, inputs)
	_overlay.visible = false
	print("FOG_DATUM ", _overlay.material_override.get_shader_parameter("reference_height_m"))
	for node in root.find_children("*", "WorldEnvironment", true, false):
		print("ENV ", node.name, " fog ", node.environment.fog_enabled, " volume ", node.environment.volumetric_fog_enabled)
