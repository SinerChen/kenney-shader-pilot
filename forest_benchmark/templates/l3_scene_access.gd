extends Node

var source: Node
var effects: Node3D
var permissions: Dictionary
var bindings: Array=[]
var input_slots: Dictionary={}

func setup(source_root: Node, effect_root: Node3D, rules: Dictionary):
	source=source_root
	effects=effect_root
	permissions=rules

func source_node(path: NodePath) -> Node:
	# Source references expose original inputs. Runtime auditing is independent.
	if str(path).begins_with("/") or ".." in str(path).split("/"):return null
	return source.get_node_or_null(path)

func bind_material(path: String, surface: int, material: Material) -> Dictionary:
	var allowed=false
	for rule in permissions.get("material_bindings",[]):
		if rule.node==path and surface in rule.surfaces:allowed=true
	if not allowed:return {"status":"DENIED","error":"Material surface is not authorized"}
	var node=source_node(NodePath(path))
	if not node is MeshInstance3D:return {"status":"MISSING_BINDING"}
	for previous in bindings:
		if previous.node==node and previous.surface==surface:
			node.set_surface_override_material(surface,material)
			return {"status":"BOUND"}
	bindings.append({"node":node,"surface":surface,"previous":node.get_surface_override_material(surface)})
	node.set_surface_override_material(surface,material)
	return {"status":"BOUND"}

func add_effect(node: Node) -> Dictionary:
	if node.get_parent()!=null:return {"status":"DENIED","error":"Only new local effect nodes may be attached"}
	effects.add_child(node)
	return {"status":"ATTACHED"}

func camera() -> Camera3D:
	return source.get_node("Camera3D")

func input_texture(name: String):
	# In particular, this does not capture or compose the E_L3 background.
	return input_slots.get(name,null)

func publish_input(name: String, resource: Texture) -> Dictionary:
	if name not in permissions.get("input_slots",[]):return {"status":"DENIED"}
	input_slots[name]=resource
	return {"status":"BOUND"}

func detach_bindings() -> void:
	for binding in bindings:
		if is_instance_valid(binding.node):binding.node.set_surface_override_material(binding.surface,binding.previous)
	bindings.clear()
	input_slots.clear()
	for node in effects.get_children():
		effects.remove_child(node)
		node.queue_free()
