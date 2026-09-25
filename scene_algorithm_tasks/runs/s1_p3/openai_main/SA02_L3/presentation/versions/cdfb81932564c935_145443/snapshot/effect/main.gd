extends Node
## Deterministic Gerstner surface, periodic horizontal compression, and foam attached to q.
const WATER_SHADER: Shader = preload("res://effect/gerstner_water.gdshader")
var scene_root: Node
var test_input: Dictionary = {}
var elapsed_s := 0.0
var current_step := 0
var positions: Array = []
var normals: Array = []
var jacobians: Array = []
var foams: Array = []
var nx := 64
var nz := 64
var lx := 8.0
var lz := 8.0
var ox := 0.0
var oz := 0.0
var last_dt := 1.0 / 60.0
var visual_material: ShaderMaterial
var foam_texture: ImageTexture

func configure(root: Node, inputs: Dictionary) -> void:
    scene_root = root
    test_input = inputs
    elapsed_s = 0.0
    current_step = 0
    var g: Dictionary = inputs.get("grid", {})
    var sz: Array = g.get("size", [64, 64])
    nx = int(sz[0]); nz = int(sz[1])
    var lengths: Array = g.get("length_xz_m", [8.0, 8.0])
    lx = float(lengths[0]); lz = float(lengths[1])
    var origin: Array = g.get("origin_xz_m", [0.0, 0.0])
    ox = float(origin[0]); oz = float(origin[1])
    last_dt = float(inputs.get("dt_seconds", 1.0 / 60.0))
    positions.resize(nx * nz); normals.resize(nx * nz)
    jacobians.resize(nx * nz); foams.resize(nx * nz)
    var fc: Dictionary = inputs.get("foam", {})
    var initial := clampf(float(fc.get("initial_value", 0.0)), 0.0, 1.0) if bool(fc.get("enabled", false)) else 0.0
    for i in range(foams.size()): foams[i] = initial
    _evaluate(false)
    _install_visual_surface()
    _update_visual_material()

func step(dt: float) -> void:
    last_dt = dt if dt > 0.0 else float(test_input.get("dt_seconds", 1.0 / 60.0))
    elapsed_s += last_dt
    current_step += 1
    _evaluate(true)
    _update_visual_material()

func sample() -> Dictionary:
    return {"step": current_step, "elapsed_s": elapsed_s,
        "positions": positions.duplicate(true), "normals": normals.duplicate(true),
        "jacobian": jacobians.duplicate(), "foam": foams.duplicate()}

func _wave_value(qx: float, qz: float, t: float) -> Dictionary:
    var p := Vector3(qx, 0.0, qz)
    var tx := Vector3(1, 0, 0)
    var tz := Vector3(0, 0, 1)
    for wave_variant: Variant in test_input.get("waves", []):
        var w: Dictionary = wave_variant
        var a := float(w.get("amplitude_m", 0.0))
        var wavelength := maxf(float(w.get("wavelength_m", 1.0)), 0.000001)
        var d0: Array = w.get("direction_xz", [1.0, 0.0])
        var d := Vector2(float(d0[0]), float(d0[1]))
        if d.length_squared() < 0.0000001: d = Vector2(1, 0)
        d = d.normalized()
        var k := TAU / wavelength
        var theta := k * (d.x*qx + d.y*qz - float(w.get("speed_m_s", 0.0))*t) + float(w.get("phase_rad", 0.0))
        var sn := sin(theta); var cs := cos(theta); var h := float(w.get("steepness", 0.0)) * a
        p += Vector3(h*d.x*cs, a*sn, h*d.y*cs)
        var kac := k*a*cs; var khs := k*h*sn
        tx += Vector3(-khs*d.x*d.x, kac*d.x, -khs*d.y*d.x)
        tz += Vector3(-khs*d.x*d.y, kac*d.y, -khs*d.y*d.y)
    var n := tz.cross(tx).normalized()
    if n.y < 0.0: n = -n
    return {"p": p, "n": n}

func _evaluate(advance_foam: bool) -> void:
    for row in range(nz):
        for col in range(nx):
            var qx := ox + float(col) * lx / float(nx)
            var qz := oz + float(row) * lz / float(nz)
            var v: Dictionary = _wave_value(qx, qz, elapsed_s)
            var i := row * nx + col
            var pp: Vector3 = v.p; var nn: Vector3 = v.n
            positions[i] = [pp.x, pp.y, pp.z]
            normals[i] = [nn.x, nn.y, nn.z]
    _compute_jacobian()
    if advance_foam: _update_foam()

func _horizontal_displacement(row: int, col: int) -> Vector2:
    var i := row * nx + col
    var p: Array = positions[i]
    var qx := ox + float(col) * lx / float(nx)
    var qz := oz + float(row) * lz / float(nz)
    return Vector2(float(p[0])-qx, float(p[2])-qz)

func _compute_jacobian() -> void:
    var dx := lx / float(nx); var dz := lz / float(nz)
    for row in range(nz):
        var rm := (row-1+nz)%nz; var rp := (row+1)%nz
        for col in range(nx):
            var cm := (col-1+nx)%nx; var cp := (col+1)%nx
            var du_dqx := (_horizontal_displacement(row, cp)-_horizontal_displacement(row, cm))/(2.0*dx)
            var du_dqz := (_horizontal_displacement(rp, col)-_horizontal_displacement(rm, col))/(2.0*dz)
            jacobians[row*nx+col] = (1.0+du_dqx.x)*(1.0+du_dqz.y)-du_dqz.x*du_dqx.y

func _update_foam() -> void:
    var f: Dictionary = test_input.get("foam", {})
    if not bool(f.get("enabled", false)):
        for i in range(foams.size()): foams[i] = 0.0
        return
    var decay := exp(-float(f.get("decay_per_s", 1.0))*last_dt)
    var threshold := float(f.get("threshold", 1.0))
    var grow := float(f.get("grow_per_s", 1.0))
    for i in range(foams.size()):
        var source := maxf(threshold-float(jacobians[i]), 0.0)
        foams[i] = clampf(float(foams[i])*decay + grow*last_dt*source, 0.0, 1.0)

func _install_visual_surface() -> void:
    visual_material = ShaderMaterial.new()
    visual_material.shader = WATER_SHADER
    # The Ocean add-on creates all near/middle/far patches under DeepOcean.
    # Override only those generated meshes, leaving floor, samples, terrain and HUD intact.
    var ocean := scene_root.get_node_or_null("DeepOcean")
    var bound := 0
    if ocean != null: bound = _bind_ocean_meshes(ocean)
    if bound == 0:
        var mi := MeshInstance3D.new(); mi.name = "GerstnerTaskSurface"
        var mesh := PlaneMesh.new(); mesh.size = Vector2(1024.0, 1024.0)
        mesh.subdivide_width = 255; mesh.subdivide_depth = 255
        mi.mesh = mesh; mi.material_override = visual_material
        scene_root.add_child(mi)

func _bind_ocean_meshes(node: Node) -> int:
    var count := 0
    for child in node.get_children():
        if child is MeshInstance3D:
            (child as MeshInstance3D).material_override = visual_material
            count += 1
        count += _bind_ocean_meshes(child)
    return count

func _update_foam_texture() -> void:
    var image := Image.create(nx, nz, false, Image.FORMAT_RF)
    for row in range(nz):
        for col in range(nx):
            image.set_pixel(col, row, Color(float(foams[row*nx+col]), 0, 0, 1))
    if foam_texture == null: foam_texture = ImageTexture.create_from_image(image)
    else: foam_texture.update(image)

func _update_visual_material() -> void:
    if visual_material == null: return
    _update_foam_texture()
    visual_material.set_shader_parameter("elapsed_s", elapsed_s)
    visual_material.set_shader_parameter("domain_origin", Vector2(ox, oz))
    visual_material.set_shader_parameter("domain_length", Vector2(lx, lz))
    visual_material.set_shader_parameter("foam_history", foam_texture)
    var foam_cfg: Dictionary = test_input.get("foam", {})
    visual_material.set_shader_parameter("foam_enabled", bool(foam_cfg.get("enabled", false)))
    visual_material.set_shader_parameter("foam_threshold", float(foam_cfg.get("threshold", 1.0)))
    var waves: Array = test_input.get("waves", [])
    visual_material.set_shader_parameter("wave_count", mini(waves.size(), 8))
    var params: Array[Vector4] = []; var directions: Array[Vector4] = []
    for wv: Variant in waves.slice(0, 8):
        var w: Dictionary = wv; var d0: Array = w.get("direction_xz", [1.0, 0.0])
        var d := Vector2(float(d0[0]), float(d0[1])).normalized()
        params.append(Vector4(float(w.get("amplitude_m", 0.0)), float(w.get("wavelength_m", 1.0)), float(w.get("speed_m_s", 0.0)), float(w.get("steepness", 0.0))))
        directions.append(Vector4(d.x, d.y, float(w.get("phase_rad", 0.0)), 0.0))
    visual_material.set_shader_parameter("wave_a_lambda_speed_steep", params)
    visual_material.set_shader_parameter("wave_direction_phase", directions)
