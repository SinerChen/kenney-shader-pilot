extends Node3D
var elapsed := 0.0
var object: MeshInstance3D
var material: ShaderMaterial
func _ready() -> void:
    var environment := WorldEnvironment.new()
    var settings := Environment.new()
    settings.background_mode = Environment.BG_COLOR
    settings.background_color = Color(0.08, 0.11, 0.17)
    environment.environment = settings
    add_child(environment)
    material = ShaderMaterial.new()
    material.shader = load("res://effect/color.gdshader")
    object = MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(1.0, 1.4, 1.8)
    object.mesh = mesh
    object.material_override = material
    add_child(object)
    object.position = Vector3(-0.5, 0.7, 0)
    var other := MeshInstance3D.new()
    var sphere := SphereMesh.new()
    sphere.radius = 0.45
    sphere.height = 0.9
    other.mesh = sphere
    var plain := StandardMaterial3D.new()
    plain.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    plain.albedo_color = Color(0.05, 0.8, 0.65)
    other.material_override = plain
    other.position = Vector3(1.1, 0.45, -0.4)
    add_child(other)
    var camera := Camera3D.new()
    camera.position = Vector3(4, 3, 5)
    add_child(camera)
    camera.look_at(Vector3(0, 0.5, 0))
    camera.make_current()
func preview_reset(_inputs: Dictionary) -> void:
    elapsed = 0.0
func preview_step(dt: float) -> void:
    elapsed += dt
    object.rotation.y = elapsed * 0.8
    material.set_shader_parameter("elapsed", elapsed)
