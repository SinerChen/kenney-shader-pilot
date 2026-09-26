extends Node

func reset(_config: Dictionary) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED","error":"Implement reset(config)"}

func advance(_dt: float, _events: Array) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED","error":"Implement advance(dt, events)"}

func query(_name: String, _payload: Dictionary = {}) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED","error":"Implement GPU query(name, payload)"}

func get_outputs() -> Dictionary:
	return {"status":"NOT_IMPLEMENTED","error":"Expose actual GPU resources"}

func mount(_bridge: Node) -> Dictionary:
	return {"status":"NOT_IMPLEMENTED","error":"Bind your effect through the fixture bridge"}

func update_display() -> void:
	pass

func dispose() -> void:
	pass
