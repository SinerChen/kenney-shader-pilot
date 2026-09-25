extends Node
var scene_root: Node
var test_input: Dictionary
var elapsed := 0.0
var frame := 0
var target: Node3D
var projector := Transform3D.IDENTITY
var materials: Array = []
var originals: Array = []
var active := false
var receiver = preload("res://effect/receiver.gd").new()
var sampler = preload("res://effect/sampling.gd")

func v(a) -> Vector3:
    return Vector3(a[0], a[1], a[2])

func configure(root: Node, inputs: Dictionary) -> void:
    scene_root = root
    test_input = inputs
    receiver.collect(root)
    target = root.get_node_or_null("World/" + str(inputs.hit.target).to_pascal_case())
    active = target != null and inputs.hit.target in inputs.allowed_targets
    if not active:
        return
    var shader = load("res://effect/projected.gdshader")
    for mesh in target.find_children("*", "MeshInstance3D", true, false):
        for s in mesh.mesh.get_surface_count():
            var base = mesh.get_active_material(s)
            if not base is StandardMaterial3D:
                continue
            var mat := ShaderMaterial.new()
            mat.shader = shader
            mat.set_shader_parameter("base_color", base.albedo_color)
            mat.set_shader_parameter("has_texture", base.albedo_texture != null)
            if base.albedo_texture:
                mat.set_shader_parameter("base_texture", base.albedo_texture)
            mat.set_shader_parameter("base_roughness", base.roughness)
            mat.set_shader_parameter("base_metallic", base.metallic)
            mat.set_shader_parameter("base_specular", base.metallic_specular)
            mat.set_shader_parameter("uv_scale", base.uv1_scale)
            mat.set_shader_parameter("uv_offset", base.uv1_scale * Vector3.ZERO + base.uv1_offset)
            mat.set_shader_parameter("ink_linear", v(inputs.projector.albedo_linear))
            mat.set_shader_parameter("ink_opacity", inputs.projector.opacity)
            mat.set_shader_parameter("cos_reject", inputs.projector.cos_reject)
            mat.set_shader_parameter("cos_full", inputs.projector.cos_full)
            originals.append([mesh, s, mesh.get_surface_override_material(s), base])
            materials.append(mat)
            mesh.set_surface_override_material(s, mat)
    update_projector()

func update_projector() -> void:
    if target == null:
        return
    var n := v(test_input.hit.local_normal).normalized()
    var x := Vector3.UP.cross(n).normalized()
    if x.length_squared() < 0.01:
        x = Vector3.RIGHT
    var basis := Basis(x, n.cross(x).normalized(), n)
    basis = basis * Basis.from_euler(v(test_input.projector.rotation_degrees) * PI / 180.0)
    projector = target.global_transform * Transform3D(basis.scaled(v(test_input.projector.scale)), v(test_input.hit.local_position) + v(test_input.projector.origin))
    for mat in materials:
        mat.set_shader_parameter("world_to_projector", projector.affine_inverse())
        mat.set_shader_parameter("projector_normal", projector.basis.z.normalized())

func step(dt: float) -> void:
    elapsed += dt
    frame += 1
    update_projector()
    if active and elapsed + 0.00000001 >= float(test_input.hit.time_s) + float(test_input.lifetime_s):
        active = false
        for item in originals:
            item[0].set_surface_override_material(item[1], item[2])

func sample() -> Dictionary:
    return sampler.capture(self)
