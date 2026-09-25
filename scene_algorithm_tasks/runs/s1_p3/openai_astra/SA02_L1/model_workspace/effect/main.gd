extends Node
# q is a world XZ parameter, not the already displaced position.
var scene_root: Node
var test_input: Dictionary
var elapsed := 0.0
var current_step := 0
var nx := 64
var nz := 64
var extent := Vector2(8, 8)
var origin := Vector2.ZERO
var waves: Array = []
var positions: Array = []
var normals: Array = []
var displacements: Array = []
var jacobian: Array = []
var foam: Array = []
var surface = preload("res://effect/ocean_surface.gd").new()

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs
	elapsed = 0.0
	current_step = 0
	nx = int(inputs.grid.size[0])
	nz = int(inputs.grid.size[1])
	extent = Vector2(inputs.grid.length_xz_m[0], inputs.grid.length_xz_m[1])
	origin = Vector2(inputs.grid.origin_xz_m[0], inputs.grid.origin_xz_m[1])
	waves.clear()
	for w in inputs.waves:
		waves.append({"a":float(w.amplitude_m), "h":float(w.steepness) * float(w.amplitude_m),
			"k":TAU / float(w.wavelength_m), "speed":float(w.speed_m_s),
			"phase":float(w.phase_rad), "d":Vector2(w.direction_xz[0], w.direction_xz[1]).normalized()})
	for array in [positions, normals, displacements, jacobian, foam]:
		array.resize(nx * nz)
	foam.fill(clampf(float(inputs.foam.initial_value), 0.0, 1.0) if inputs.foam.enabled else 0.0)
	_recompute(0.0)
	surface.configure(root, waves, bool(inputs.foam.enabled))
	surface.update(elapsed)

# Full derivatives: dP/dqx and dP/dqz. tz cross tx points upward.
func evaluate(q: Vector2) -> Dictionary:
	var displacement := Vector3.ZERO
	var tx := Vector3.RIGHT
	var tz := Vector3.BACK
	for w in waves:
		var d: Vector2 = w.d
		var theta: float = w.k * (d.dot(q) - w.speed * elapsed) + w.phase
		var s := sin(theta)
		var c := cos(theta)
		var h: float = w.h
		var ak: float = w.a * w.k
		var hk: float = h * w.k
		displacement += Vector3(h * d.x * c, w.a * s, h * d.y * c)
		tx += Vector3(-hk * d.x * d.x * s, ak * d.x * c, -hk * d.y * d.x * s)
		tz += Vector3(-hk * d.x * d.y * s, ak * d.y * c, -hk * d.y * d.y * s)
	return {"p":Vector3(q.x, 0, q.y) + displacement, "n":tz.cross(tx).normalized(), "u":displacement}

func _recompute(dt: float) -> void:
	var dx := extent.x / nx
	var dz := extent.y / nz
	for row in nz:
		for col in nx:
			var i := row * nx + col
			var value := evaluate(origin + Vector2(col * dx, row * dz))
			var p: Vector3 = value.p
			var n: Vector3 = value.n
			positions[i] = [p.x, p.y, p.z]
			normals[i] = [n.x, n.y, n.z]
			displacements[i] = value.u
	# Differentiate periodic displacement, not wrapped absolute positions.
	var f: Dictionary = test_input.foam
	for row in nz:
		for col in nx:
			var i := row * nx + col
			var ux: Vector3 = (displacements[row * nx + (col + 1) % nx] - displacements[row * nx + (col + nx - 1) % nx]) / (2.0 * dx)
			var uz: Vector3 = (displacements[((row + 1) % nz) * nx + col] - displacements[((row + nz - 1) % nz) * nx + col]) / (2.0 * dz)
			var j := (1.0 + ux.x) * (1.0 + uz.z) - ux.z * uz.x
			jacobian[i] = j
			if f.enabled:
				foam[i] = clampf(float(foam[i]) * exp(-float(f.decay_per_s) * dt) + float(f.grow_per_s) * dt * maxf(float(f.threshold) - j, 0.0), 0.0, 1.0)
			else:
				foam[i] = 0.0

func step(dt: float) -> void:
	elapsed += dt
	current_step += 1
	_recompute(dt)
	surface.update(elapsed)

func sample() -> Dictionary:
	# Snapshot arrays so later steps cannot mutate a previously recorded sample.
	var result := {"step":current_step, "elapsed_s":elapsed, "positions":positions.duplicate(true),
		"normals":normals.duplicate(true), "jacobian":jacobian.duplicate(), "foam":foam.duplicate()}
	# Regression diagnostics are independent and do not modify inputs or results.
	if nx == 64 and nz == 64 and not test_input.foam.enabled and waves.size() == 2:
		preload("res://effect/verify.gd").check(result)
	return result
