extends Node

func reset(_config: Dictionary) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED"}
func advance(_dt: float, _events: Array) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED"}
func query(_name: String, _payload: Dictionary = {}) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED"}
func get_outputs() -> Dictionary:
	return {"status":"NOT_IMPLEMENTED"}
func bind_scene(_scene_access: Node, _task_config: Dictionary) -> Dictionary:
	return {"status":"UNIMPLEMENTED_BINDING"}
func detach_scene() -> Dictionary:
	return {"status":"UNIMPLEMENTED_BINDING"}
func mount(_legacy_bridge: Node) -> Dictionary:
	return {"status":"UNIMPLEMENTED_BINDING","error":"L2 stage bridge is not provided in L3. Implement bind_scene."}
func update_display() -> void:pass
func dispose() -> void:pass
