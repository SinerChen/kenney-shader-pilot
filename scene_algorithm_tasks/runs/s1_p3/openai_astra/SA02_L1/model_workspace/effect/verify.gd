extends RefCounted
# Independent fixed-input regression: separable X and Z waves have closed forms.
static func check(output: Dictionary) -> void:
	var t: float = output.elapsed_s
	assert(output.positions.size() == 4096)
	assert(output.normals.size() == 4096)
	assert(output.jacobian.size() == 4096)
	assert(output.foam.size() == 4096)
	assert(absf(t - int(output.step) / 60.0) < 1e-10)
	var max_position_error := 0.0
	var max_normal_error := 0.0
	var max_j_error := 0.0
	var max_unit_error := 0.0
	var kx := TAU / 4.0
	var kz := TAU / 8.0
	var h := 0.125
	for row in 64:
		for col in 64:
			var i := row * 64 + col
			var x := col * h
			var z := row * h
			var a := kx * (x - t)
			var b := kz * (z - 0.5 * t) + 0.5
			var p := Vector3(x + 0.08*cos(a), 0.2*sin(a) + 0.1*sin(b), z + 0.03*cos(b))
			var xx := 1.0 - 0.08*kx*sin(a)
			var zz := 1.0 - 0.03*kz*sin(b)
			var n := Vector3(-0.2*kx*cos(a)*zz, xx*zz, -0.1*kz*cos(b)*xx).normalized()
			var j := (1.0 - 0.08*sin(kx*h)/h*sin(a)) * (1.0 - 0.03*sin(kz*h)/h*sin(b))
			var actual_p := Vector3(output.positions[i][0], output.positions[i][1], output.positions[i][2])
			var actual_n := Vector3(output.normals[i][0], output.normals[i][1], output.normals[i][2])
			max_position_error = maxf(max_position_error, actual_p.distance_to(p))
			max_normal_error = maxf(max_normal_error, actual_n.distance_to(n))
			max_unit_error = maxf(max_unit_error, absf(actual_n.length() - 1.0))
			max_j_error = maxf(max_j_error, absf(output.jacobian[i] - j))
			assert(output.foam[i] == 0.0)
	assert(max_position_error < 2e-6)
	assert(max_normal_error < 2e-6)
	assert(max_unit_error < 2e-6)
	assert(max_j_error < 2e-6)
	print("GERSTNER_VERIFY step=%d count=4096 position_error=%.9f normal_error=%.9f unit_error=%.9f jacobian_error=%.9f foam=0" % [output.step, max_position_error, max_normal_error, max_unit_error, max_j_error])
