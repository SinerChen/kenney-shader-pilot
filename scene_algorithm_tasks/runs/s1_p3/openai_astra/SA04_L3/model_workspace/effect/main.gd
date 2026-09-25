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
var hit_start := 0.0
var current_hit: Dictionary = {}
var seen_events: Dictionary = {}
var event_serial := 0
var motion_target: Node3D
var target_base := Transform3D.IDENTITY
var receiver = preload("res://effect/receiver.gd").new()
var sampler = preload("res://effect/sampling.gd")
func v(a) -> Vector3:
    if a is Vector3: return a
    return Vector3(a[0],a[1],a[2])
func logical_name(value) -> String:
    var text := str(value)
    if text == "TargetA": return "target_a"
    if text == "TargetB": return "target_b"
    return text
func configure(root: Node, inputs: Dictionary) -> void:
    clear_decal()
    scene_root = root
    test_input = inputs.duplicate(true)
    elapsed = 0.0
    frame = 0
    current_hit.clear()
    seen_events.clear()
    event_serial = 0
    receiver.collect(root)
    motion_target = root.get_node_or_null("World/" + str(inputs.hit.target).to_pascal_case())
    if motion_target != null: target_base = motion_target.global_transform
    if root.has_signal("benchmark_event") and not root.is_connected("benchmark_event", on_event): root.connect("benchmark_event", on_event)
    inject_hit(inputs.hit)
func clear_decal() -> void:
    for item in originals:
        if is_instance_valid(item.node):
            item.node.material_override = item.override
            for s in item.surfaces.size(): item.node.set_surface_override_material(s,item.surfaces[s])
    originals.clear()
    materials.clear()
    active = false
func inject_hit(event: Dictionary) -> bool:
    if not event.has("event_id"): return false
    var id = event.event_id
    if seen_events.has(id): return false
    seen_events[id] = true
    var name_string := logical_name(event.get("target", ""))
    if name_string not in test_input.allowed_targets: return false
    var next_target: Node3D = scene_root.get_node_or_null("World/" + name_string.to_pascal_case())
    if next_target == null: return false
    var normal := v(event.get("local_normal",[0,0,0]))
    if normal.length_squared() < 0.000001: return false
    clear_decal()
    target = next_target
    current_hit = event.duplicate(true)
    current_hit.target = name_string
    current_hit.local_position = event.get("local_position",[0,0,0])
    current_hit.local_normal = normal.normalized()
    hit_start = float(event.get("time_s",elapsed))
    active = elapsed >= hit_start and elapsed + 0.00000001 < hit_start + float(test_input.lifetime_s)
    if active: install_materials()
    update_projector()
    return true
func install_materials() -> void:
    var shader = load("res://effect/projected.gdshader")
    var meshes: Array = target.find_children("*","MeshInstance3D",true,false)
    if target is MeshInstance3D: meshes.append(target)
    for mesh in meshes:
        if mesh.mesh == null: continue
        var saved: Array = []
        var bases: Array = []
        for s in mesh.mesh.get_surface_count():
            saved.append(mesh.get_surface_override_material(s))
            bases.append(mesh.get_active_material(s))
        originals.append({"node":mesh,"override":mesh.material_override,"surfaces":saved})
        mesh.material_override = null
        for s in bases.size():
            var base: Material = bases[s]
            if base == null: base = StandardMaterial3D.new()
            # Never modify imported/shared resources, including their pass chains.
            var copy: Material = base.duplicate()
            var tail: Material = copy
            var source: Material = base.next_pass
            while source != null:
                tail.next_pass = source.duplicate()
                tail = tail.next_pass
                source = source.next_pass
            var mat := ShaderMaterial.new()
            mat.shader = shader
            if base is BaseMaterial3D:
                mat.set_shader_parameter("base_roughness",base.roughness)
                mat.set_shader_parameter("base_metallic",base.metallic)
                mat.set_shader_parameter("base_specular",base.metallic_specular)
            mat.set_shader_parameter("ink_linear",v(test_input.projector.albedo_linear))
            mat.set_shader_parameter("ink_opacity",test_input.projector.opacity)
            mat.set_shader_parameter("cos_reject",test_input.projector.cos_reject)
            mat.set_shader_parameter("cos_full",test_input.projector.cos_full)
            tail.next_pass = mat
            materials.append(mat)
            mesh.set_surface_override_material(s,copy)
    print("DECAL_BOUND target=",current_hit.target," surfaces=",materials.size())
func on_event(event_name: String, payload: Dictionary = {}, _state: Dictionary = {}) -> void:
    if event_name != "hit": return
    var event := payload.duplicate(true)
    event.target = logical_name(event.get("target", ""))
    if event.target not in test_input.allowed_targets: return
    if not event.has("event_id"):
        event_serial += 1
        event.event_id = "host_%d" % event_serial
    event.time_s = event.get("time_s",elapsed)
    if not event.has("local_position") or not event.has("local_normal"):
        receiver.refresh()
        var camera: Camera3D = scene_root.get_node_or_null("Player/Head/Camera")
        if camera == null: camera = get_viewport().get_camera_3d()
        var receiver_node: Node3D = scene_root.get_node_or_null("World/" + str(event.target).to_pascal_case())
        if camera == null or receiver_node == null: return
        var contact: Dictionary = preload("res://effect/contact.gd").recover(scene_root,receiver,camera,receiver_node)
        if contact.is_empty(): return
        event.merge(contact,true)
    inject_hit(event)
func update_target_motion() -> void:
    if motion_target == null: return
    var motion: Dictionary = test_input.get("target_motion",{})
    var translation := v(motion.get("translation_m_s",[0,0,0]))*elapsed
    var yaw := deg_to_rad(float(motion.get("yaw_degrees_s",0.0))*elapsed)
    motion_target.global_transform = Transform3D(Basis(Vector3.UP,yaw)*target_base.basis,target_base.origin+translation)
func update_projector() -> void:
    if target == null or current_hit.is_empty(): return
    var n := v(current_hit.local_normal).normalized()
    var x := Vector3.UP.cross(n).normalized()
    if x.length_squared() < 0.01: x = Vector3.RIGHT
    var basis := Basis(x,n.cross(x).normalized(),n)
    basis = basis * Basis.from_euler(v(test_input.projector.rotation_degrees)*PI/180.0)
    basis = basis * Basis.from_scale(v(test_input.projector.scale))
    projector = target.global_transform * Transform3D(basis,v(current_hit.local_position)+v(test_input.projector.origin))
    var normal: Vector3 = (projector.basis.inverse().transposed()*Vector3.BACK).normalized()
    for mat in materials:
        mat.set_shader_parameter("world_to_projector",projector.affine_inverse())
        mat.set_shader_parameter("projector_normal",normal)
func step(dt: float) -> void:
    elapsed += dt
    frame += 1
    update_target_motion()
    if not current_hit.is_empty():
        var valid := elapsed >= hit_start and elapsed + 0.00000001 < hit_start + float(test_input.lifetime_s)
        if active and not valid:
            clear_decal()
            print("DECAL_EXPIRED step=",frame," time=",elapsed," material_restored=true")
        elif not active and valid:
            active = true
            install_materials()
    update_projector()
func sample() -> Dictionary:
    receiver.refresh()
    var output: Dictionary = sampler.capture(self)
    output.active_target = current_hit.target if active else null
    return output
