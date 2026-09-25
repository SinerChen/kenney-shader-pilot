extends Node
# Empty model-editable slot. The baseline does not implement any scored effect.
var context: Dictionary

func setup(host_context: Dictionary) -> void:
	context = host_context

func reset(_state: Dictionary) -> void:
	pass

func step(_dt: float, _state: Dictionary) -> void:
	pass

func on_event(_event_name: String, _payload: Dictionary, _state: Dictionary) -> void:
	pass
