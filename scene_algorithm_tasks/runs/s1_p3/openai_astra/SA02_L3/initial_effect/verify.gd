extends RefCounted
# Independent closed-form reference for this experiment's two separable waves.
# Rebuild history from t=0; never reuse the candidate's Jacobian or foam values.
static func check(output: Dictionary, foam_enabled: bool = false) -> void:
	var t: float = output.elapsed_s
	for key in ["positions", "normals", "jacobian", "foam"]:
		assert(output[key].size() == 4096)
	assert(absf(t - int(output.step) / 60.0) < 1e-10)
	var ep := 0.0
	var en := 0.0
	var ej := 0.0
	var eu := 0.0
	var ef := 0.0
	var fmax := 0.0
	var trail_count := 0
	var kx := TAU / 4.0
	var kz := TAU / 8.0
	var h := 0.125
	var jx := 0.08 * sin(kx*h) / h
	var jz := 0.03 * sin(kz*h) / h
	for row in 64:
		for col in 64:
			var i := row * 64 + col
			var x := col * h
			var z := row * h
			var a := kx * (x - t)
			var b := kz * (z - 0.5*t) + 0.5
			var p := Vector3(x + 0.08*cos(a), 0.2*sin(a) + 0.1*sin(b), z + 0.03*cos(b))
			var xx := 1.0 - 0.08*kx*sin(a)
			var zz := 1.0 - 0.03*kz*sin(b)
			var n := Vector3(-0.2*kx*cos(a)*zz, xx*zz, -0.1*kz*cos(b)*xx).normalized()
			var j := (1.0-jx*sin(a)) * (1.0-jz*sin(b))
			var reference_foam := 0.0
			if foam_enabled:
				for s in range(1, int(output.step)+1):
					var time := s / 60.0
					var jt := (1.0-jx*sin(kx*(x-time))) * (1.0-jz*sin(kz*(z-0.5*time)+0.5))
					reference_foam = clampf(reference_foam * exp(-1.0/60.0) + maxf(1.0-jt,0.0)/60.0,0.0,1.0)
			var actual_p := Vector3(output.positions[i][0],output.positions[i][1],output.positions[i][2])
			var actual_n := Vector3(output.normals[i][0],output.normals[i][1],output.normals[i][2])
			ep = maxf(ep,actual_p.distance_to(p))
			en = maxf(en,actual_n.distance_to(n))
			eu = maxf(eu,absf(actual_n.length()-1.0))
			ej = maxf(ej,absf(output.jacobian[i]-j))
			ef = maxf(ef,absf(output.foam[i]-reference_foam))
			fmax = maxf(fmax,output.foam[i])
			assert(output.foam[i] >= 0.0 and output.foam[i] <= 1.0)
			if j >= 1.0 and output.foam[i] > 0.005:
				trail_count += 1
	assert(maxf(maxf(ep,en),maxf(eu,ej)) < 2e-6)
	assert(ef < 2e-6)
	print("WAVE_HISTORY_VERIFY step=%d count=4096 position_error=%.9f normal_error=%.9f unit_error=%.9f jacobian_error=%.9f foam_error=%.9f foam_max=%.6f uncompressed_history_points=%d" % [output.step,ep,en,eu,ej,ef,fmax,trail_count])
