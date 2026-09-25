extends StaticBody3D
var health := 100.0

func damage(amount: float) -> void:
	health = maxf(0.0, health - amount)
	var root := get_tree().current_scene
	root.emit_event("hit", {"target": str(name), "amount": amount, "health": health / 100.0})
	if health <= 0.0:
		root.emit_event("destroy", {"target": str(name)})

func reset_target() -> void:
	health = 100.0
