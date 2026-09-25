extends Node
var scene_root: Node
var test_input: Dictionary
var field
var geometry
var elapsed := 0.0
var current_sample: Dictionary = {}
var record_steps: Array = []
var next_record := 0
var removal_field := PackedFloat32Array()

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs
	elapsed = 0.0
	next_record = 0
	current_sample = {}
	removal_field.clear()
	field = preload("res://effect/interaction_field.gd").new()
	field.configure(inputs)
	root.set_parameters({"wind_strength":inputs.wind.strength, "wind_speed":inputs.wind.speed, "wind_direction":inputs.wind.direction_xz})
	geometry = preload("res://effect/grass_geometry.gd").new()
	geometry.configure(root, inputs, field)
	geometry.update_time(0.0)
	record_steps = inputs.record_after_steps.duplicate()

func step(dt: float) -> void:
	elapsed += dt
	field.step(dt)
	# Each mesh has its own corner uniforms: update every copied material every step.
	geometry.update_time(elapsed)
	if field.frame == 120:
		removal_field = field.values.duplicate()
	if next_record < record_steps.size() and field.frame == int(record_steps[next_record]):
		var result: Dictionary = geometry.evaluate(field)
		current_sample = {"step":field.frame, "elapsed_s":elapsed, "field_rgba":field.as_rows(), "positions":result.positions, "normals":result.normals}
		var peak := 0.0
		for i in range(field.width * field.height):
			peak = maxf(peak, field.values[i * 4 + 2])
		print("FIELD_CHECK step=", field.frame, " texels=", current_sample.field_rgba.size(), " active=", field.active, " peak=", peak, " outside=", field.sample_at(Vector2(5, 0)))
		if field.frame == 240 and not removal_field.is_empty():
			var error := 0.0
			var decay := pow(float(test_input.interaction.persistence_per_60hz_step), 120.0)
			for i in range(removal_field.size()):
				error = maxf(error, absf(field.values[i] - removal_field[i] * decay))
			print("DECAY_CHECK all_channels_error=", error)
		next_record += 1

func sample() -> Dictionary:
	return current_sample
