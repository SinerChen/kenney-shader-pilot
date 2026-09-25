extends Node
# Deterministic four-layer height blend and selective installation on the Bistro wet-road surfaces.
const EPS_COMPETE := 0.000001
const EPS_TRANSITION := 0.00001
const EPS_DENOM := 0.000001
const FALLBACK_NORMAL := Vector3(0.0, 0.0, 1.0)
const WET_MATERIAL_SUFFIX := "Pavement_Cobblestone_Wet.tres"
const ROAD_SHADER := preload("res://effect/four_layer_height_blend.gdshader")
var scene_root: Node
var test_input: Dictionary = {}
var _last_sample: Dictionary = {}
var _material: ShaderMaterial

func configure(root: Node, inputs: Dictionary) -> void:
    scene_root = root
    test_input = inputs
    _last_sample = _evaluate(inputs)
    _install_road_material()

func step(_dt: float) -> void:
    pass

func sample() -> Dictionary:
    return _last_sample.duplicate(true)

func _install_road_material() -> void:
    # The authored Ground scene already provides the outdoor-road region mask by
    # assigning Pavement_Cobblestone_Wet only to road meshes.  Preserve every
    # other surface/material and replace only those masked surface slots.
    var target := scene_root.get_node_or_null("Level Geometry/Ground/Ground") if scene_root != null else null
    if target == null and scene_root != null:
        target = _find_ground(scene_root)
    if target == null:
        return
    _material = ShaderMaterial.new()
    _material.shader = ROAD_SHADER
    _material.set_shader_parameter("road_albedo", load("res://Textures/Ground/Pavement_Cobblestone_Wet_BLENDSHADER_BaseColor.dds"))
    _material.set_shader_parameter("road_normal", load("res://Textures/Ground/Pavement_Cobblestone_Wet_BLENDSHADER_Normal.png"))
    _material.set_shader_parameter("transition", maxf(float(test_input.get("transition", 0.25)), EPS_TRANSITION))
    var layers: Array = test_input.get("layers", [])
    var heights := Vector4.ZERO
    var controls := Vector4.ZERO
    var roughness := Vector4.ZERO
    var metallic := Vector4.ZERO
    for i in range(mini(4, layers.size())):
        var layer: Dictionary = layers[i] if layers[i] is Dictionary else {}
        heights[i] = float(layer.get("height", 0.0))
        controls[i] = maxf(float(layer.get("control", 0.0)), 0.0)
        roughness[i] = float(layer.get("roughness", 0.5))
        metallic[i] = float(layer.get("metallic", 0.0))
    _material.set_shader_parameter("layer_height", heights)
    _material.set_shader_parameter("layer_control", controls)
    _material.set_shader_parameter("layer_roughness", roughness)
    _material.set_shader_parameter("layer_metallic", metallic)
    for i in range(mini(4, layers.size())):
        var layer: Dictionary = layers[i] if layers[i] is Dictionary else {}
        _material.set_shader_parameter("layer%d_albedo" % i, _vec3(layer.get("albedo_linear", [0.0, 0.0, 0.0])))
        _material.set_shader_parameter("layer%d_normal" % i, _vec3(layer.get("normal_ts", [0.0, 0.0, 1.0])))
    _material.set_shader_parameter("detail_normal", _vec3(test_input.get("detail_normal_ts", [0, 0, 1])))
    _material.set_shader_parameter("detail_enabled", bool(test_input.get("detail_enabled", false)))
    _apply_to_authored_wet_surfaces(target)

func _find_ground(root: Node) -> Node:
    if root.name == "Ground":
        return root
    for child in root.get_children():
        var found := _find_ground(child)
        if found != null:
            return found
    return null

func _apply_to_authored_wet_surfaces(node: Node) -> void:
    if node is MeshInstance3D:
        var mesh_node := node as MeshInstance3D
        var mesh := mesh_node.mesh
        if mesh != null:
            for surface in range(mesh.get_surface_count()):
                var authored := mesh_node.get_surface_override_material(surface)
                if authored == null:
                    authored = mesh.surface_get_material(surface)
                if _is_authored_wet_road_material(authored):
                    mesh_node.set_surface_override_material(surface, _material)
    for child in node.get_children():
        _apply_to_authored_wet_surfaces(child)

func _is_authored_wet_road_material(material: Material) -> bool:
    return material != null and material.resource_path.ends_with(WET_MATERIAL_SUFFIX)

func _evaluate(inputs: Dictionary) -> Dictionary:
    var layers: Array = inputs.get("layers", [])
    var weights: Array[float] = [0.0, 0.0, 0.0, 0.0]
    var scores: Array[float] = [0.0, 0.0, 0.0, 0.0]
    var highest := -INF
    for i in range(4):
        var l: Dictionary = layers[i] if i < layers.size() and layers[i] is Dictionary else {}
        scores[i] = float(l.get("height", 0.0)) * maxf(float(l.get("control", 0.0)), 0.0)
        highest = maxf(highest, scores[i])
    if highest == -INF:
        highest = 0.0
    var width := maxf(float(inputs.get("transition", 0.0)), EPS_TRANSITION)
    var total := 0.0
    for i in range(4):
        var l: Dictionary = layers[i] if i < layers.size() and layers[i] is Dictionary else {}
        var control := maxf(float(l.get("control", 0.0)), 0.0)
        weights[i] = (maxf(scores[i] - highest + width, 0.0) + EPS_COMPETE) * control
        total += weights[i]
    for i in range(4):
        weights[i] /= maxf(total, EPS_DENOM)
    var color := Vector3.ZERO
    var roughness := 0.0
    var metallic := 0.0
    var height := 0.0
    var normal := Vector3.ZERO
    for i in range(4):
        var l: Dictionary = layers[i] if i < layers.size() and layers[i] is Dictionary else {}
        var weight := weights[i]
        color += _vec3(l.get("albedo_linear", [0, 0, 0])) * weight
        roughness += float(l.get("roughness", 0.0)) * weight
        metallic += float(l.get("metallic", 0.0)) * weight
        height += float(l.get("height", 0.0)) * weight
        normal += _vec3(l.get("normal_ts", [0, 0, 1])) * weight
    var base := _safe_normalize(normal)
    var final := base
    if bool(inputs.get("detail_enabled", false)):
        final = _rnm(base, _safe_normalize(_vec3(inputs.get("detail_normal_ts", [0, 0, 1]))))
    # Insertion order is the required serialized output order.
    return {
        "weights": weights,
        "albedo_linear": _array3(color),
        "roughness_metallic_height": [roughness, metallic, height],
        "base_normal_ts": _array3(base),
        "final_normal_ts": _array3(final)
    }

func _vec3(value: Variant) -> Vector3:
    if value is Vector3:
        return value
    if value is Array and value.size() >= 3:
        return Vector3(float(value[0]), float(value[1]), float(value[2]))
    return Vector3.ZERO

func _array3(value: Vector3) -> Array[float]:
    return [value.x, value.y, value.z]

func _safe_normalize(value: Vector3) -> Vector3:
    return FALLBACK_NORMAL if value.length_squared() <= EPS_DENOM * EPS_DENOM else value.normalized()

func _rnm(base: Vector3, detail: Vector3) -> Vector3:
    var t := base + Vector3(0, 0, 1)
    var u := detail * Vector3(-1, -1, 1)
    return _safe_normalize(t * t.dot(u) - u * t.z)
