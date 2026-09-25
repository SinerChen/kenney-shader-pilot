extends Node
## Complete, deterministic Gerstner surface implementation for the task harness.
const WATER_SHADER: Shader = preload("res://effect/gerstner_water.gdshader")
var scene_root: Node
var test_input: Dictionary = {}
var elapsed_s: float = 0.0
var current_step: int = 0
var positions: Array = []
var normals: Array = []
var jacobians: Array = []
var foams: Array = []
var nx: int = 64
var nz: int = 64
var lx: float = 8.0
var lz: float = 8.0
var ox: float = 0.0
var oz: float = 0.0
var visual_material: ShaderMaterial

func configure(root: Node, inputs: Dictionary) -> void:
    scene_root = root
    test_input = inputs
    var g: Dictionary = inputs.get("grid", {})
    var sz: Array = g.get("size", [64, 64])
    nx = int(sz[0]); nz = int(sz[1])
    var lengths: Array = g.get("length_xz_m", [8.0, 8.0])
    lx = float(lengths[0]); lz = float(lengths[1])
    var origin: Array = g.get("origin_xz_m", [0.0, 0.0])
    ox = float(origin[0]); oz = float(origin[1])
    positions.resize(nx * nz); normals.resize(nx * nz)
    jacobians.resize(nx * nz); foams.resize(nx * nz)
    _evaluate()
    _install_visual_surface()
    _update_visual_material()

func step(dt: float) -> void:
    var actual_dt: float = dt
    if actual_dt <= 0.0: actual_dt = float(test_input.get("dt_seconds", 1.0 / 60.0))
    elapsed_s += actual_dt
    current_step += 1
    _evaluate()
    _update_visual_material()

func sample() -> Dictionary:
    return {"step": current_step, "elapsed_s": elapsed_s,
        "positions": positions.duplicate(true), "normals": normals.duplicate(true),
        "jacobian": jacobians.duplicate(), "foam": foams.duplicate(true)}

func _wave_value(qx: float, qz: float, t: float) -> Dictionary:
    var p: Vector3 = Vector3(qx, 0.0, qz)
    var tx: Vector3 = Vector3(1, 0, 0)
    var tz: Vector3 = Vector3(0, 0, 1)
    var waves: Array = test_input.get("waves", [])
    for wave_variant: Variant in waves:
        var w: Dictionary = wave_variant
        var a: float = float(w.get("amplitude_m", 0.0))
        var wavelength: float = maxf(float(w.get("wavelength_m", 1.0)), 0.000001)
        var speed: float = float(w.get("speed_m_s", 0.0))
        var phase0: float = float(w.get("phase_rad", 0.0))
        var steep: float = float(w.get("steepness", 0.0))
        var d0: Array = w.get("direction_xz", [1.0, 0.0])
        var d: Vector2 = Vector2(float(d0[0]), float(d0[1]))
        if d.length_squared() < 0.0000001: d = Vector2(1, 0)
        d = d.normalized()
        var k: float = TAU / wavelength
        var theta: float = k * (d.x * qx + d.y * qz - speed * t) + phase0
        var sn: float = sin(theta); var cs: float = cos(theta); var h: float = steep * a
        p.x += h * d.x * cs; p.y += a * sn; p.z += h * d.y * cs
        var ka_s: float = k * a * sn; var kh_s: float = k * h * sn
        tx.x -= kh_s * d.x * d.x; tx.y += ka_s * d.x; tx.z -= kh_s * d.y * d.x
        tz.x -= kh_s * d.x * d.y; tz.y += ka_s * d.y; tz.z -= kh_s * d.y * d.y
    var n: Vector3 = tz.cross(tx).normalized()
    if n.y < 0.0: n = -n
    return {"p": p, "tx": tx, "tz": tz, "n": n}

func _evaluate() -> void:
    for row: int in range(nz):
        for col: int in range(nx):
            var qx: float = ox + float(col) * lx / float(nx)
            var qz: float = oz + float(row) * lz / float(nz)
            var v: Dictionary = _wave_value(qx, qz, elapsed_s)
            var i: int = row * nx + col
            var pp: Vector3 = v["p"]
            positions[i] = [pp.x, pp.y, pp.z]
            var nn: Vector3 = v["n"]
            normals[i] = [nn.x, nn.y, nn.z]
            var tx: Vector3 = v["tx"]; var tz: Vector3 = v["tz"]
            jacobians[i] = tx.x * tz.z - tx.z * tz.x
            foams[i] = 0.0
    _update_foam()

func _update_foam() -> void:
    var f: Dictionary = test_input.get("foam", {})
    if not bool(f.get("enabled", false)):
        for i: int in range(foams.size()): foams[i] = 0.0
        return
    var dt: float = float(test_input.get("dt_seconds", 1.0 / 60.0))
    var decay: float = exp(-float(f.get("decay_per_s", 1.0)) * dt)
    var threshold: float = float(f.get("threshold", 1.0))
    var grow: float = float(f.get("grow_per_s", 1.0))
    var initial: float = float(f.get("initial_value", 0.0))
    if current_step == 0:
        for i: int in range(foams.size()): foams[i] = clampf(initial, 0.0, 1.0)
    var old: Array = foams.duplicate()
    for row: int in range(nz):
        var rm: int = (row - 1 + nz) % nz; var rp: int = (row + 1) % nz
        for col: int in range(nx):
            var cm: int = (col - 1 + nx) % nx; var cp: int = (col + 1) % nx
            var xp: Array = positions[row * nx + cp]; var xm: Array = positions[row * nx + cm]
            var zp: Array = positions[rp * nx + col]; var zm: Array = positions[rm * nx + col]
            var ddx_x: float = (float(xp[0]) - float(xm[0])) * 0.5
            var ddx_z: float = (float(xp[2]) - float(xm[2])) * 0.5
            var ddz_x: float = (float(zp[0]) - float(zm[0])) * 0.5
            var ddz_z: float = (float(zp[2]) - float(zm[2])) * 0.5
            var j: float = ddx_x * ddz_z - ddx_z * ddz_x
            var source: float = maxf(threshold - j, 0.0)
            var idx: int = row * nx + col
            foams[idx] = clampf(float(old[idx]) * decay + grow * dt * source, 0.0, 1.0)

func _install_visual_surface() -> void:
    if scene_root == null or scene_root.get_node_or_null("GerstnerTaskSurface") != null: return
    var mi: MeshInstance3D = MeshInstance3D.new()
    mi.name = "GerstnerTaskSurface"
    var mesh: PlaneMesh = PlaneMesh.new()
    mesh.size = Vector2(lx, lz); mesh.subdivide_width = nx - 1; mesh.subdivide_depth = nz - 1
    mi.mesh = mesh
    visual_material = ShaderMaterial.new()
    visual_material.shader = WATER_SHADER
    mi.material_override = visual_material
    scene_root.add_child(mi)

func _update_visual_material() -> void:
    if visual_material == null: return
    visual_material.set_shader_parameter("elapsed_s", elapsed_s)
    visual_material.set_shader_parameter("domain_origin", Vector2(ox, oz))
    visual_material.set_shader_parameter("domain_half_size", Vector2(lx * 0.5, lz * 0.5))
    var waves: Array = test_input.get("waves", [])
    visual_material.set_shader_parameter("wave_count", mini(waves.size(), 8))
    var params: Array[Vector4] = []; var directions: Array[Vector4] = []
    for wv: Variant in waves:
        var w: Dictionary = wv; var d0: Array = w.get("direction_xz", [1.0, 0.0])
        params.append(Vector4(float(w.get("amplitude_m", 0.0)), float(w.get("wavelength_m", 1.0)), float(w.get("speed_m_s", 0.0)), float(w.get("steepness", 0.0))))
        directions.append(Vector4(float(d0[0]), float(d0[1]), float(w.get("phase_rad", 0.0)), 0.0))
    visual_material.set_shader_parameter("wave_a_lambda_speed_steep", params)
    visual_material.set_shader_parameter("wave_direction_phase", directions)
