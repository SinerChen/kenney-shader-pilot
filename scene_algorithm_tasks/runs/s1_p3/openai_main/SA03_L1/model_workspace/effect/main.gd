extends Node
# Four-way height blend entry. The host scene stays in charge of simulation; this
# node reports deterministic CPU values and installs the blend on Ground meshes.

const EPS_COMPETE := 0.000001
const EPS_TRANSITION := 0.00001
const EPS_DENOM := 0.000001
const FALLBACK_NORMAL := Vector3(0.0, 0.0, 1.0)
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
    if _last_sample.is_empty() and not test_input.is_empty():
        _last_sample = _evaluate(test_input)
    return _last_sample.duplicate(true)

func _install_road_material() -> void:
    if scene_root == null:
        return
    var target := _find_ground(scene_root)
    if target == null:
        return
    _material = ShaderMaterial.new()
    _material.shader = ROAD_SHADER
    # Reuse the original wet-road fixed maps supplied by the Bistro project.
    _material.set_shader_parameter("road_albedo", load("res://Textures/Ground/Pavement_Cobblestone_Wet_BLENDSHADER_BaseColor.dds"))
    _material.set_shader_parameter("road_normal", load("res://Textures/Ground/Pavement_Cobblestone_Wet_BLENDSHADER_Normal.png"))
    _material.set_shader_parameter("transition", maxf(float(test_input.get("transition", 0.25)), EPS_TRANSITION))
    var layers_value: Variant = test_input.get("layers", [])
    var layers: Array = layers_value if layers_value is Array else []
    var heights := Vector4.ZERO
    var controls := Vector4.ZERO
    var roughness := Vector4.ZERO
    var metallic := Vector4.ZERO
    for i in range(mini(4, layers.size())):
        if not layers[i] is Dictionary:
            continue
        var layer: Dictionary = layers[i]
        heights[i] = float(layer.get("height", 0.0))
        controls[i] = maxf(float(layer.get("control", 0.0)), 0.0)
        roughness[i] = float(layer.get("roughness", 0.0))
        metallic[i] = float(layer.get("metallic", 0.0))
    _material.set_shader_parameter("layer_height", heights)
    _material.set_shader_parameter("layer_control", controls)
    _material.set_shader_parameter("layer_roughness", roughness)
    _material.set_shader_parameter("layer_metallic", metallic)
    if layers.size() >= 4:
        _material.set_shader_parameter("layer0_albedo", _vec3(layers[0].get("albedo_linear", [0.45, 0.42, 0.38])))
        _material.set_shader_parameter("layer1_albedo", _vec3(layers[1].get("albedo_linear", [0.25, 0.23, 0.21])))
        _material.set_shader_parameter("layer2_albedo", _vec3(layers[2].get("albedo_linear", [0.12, 0.09, 0.06])))
        _material.set_shader_parameter("layer3_albedo", _vec3(layers[3].get("albedo_linear", [0.0, 0.0, 0.0])))
    _apply_material_recursive(target)

func _find_ground(root: Node) -> Node:
    if root.name == "Ground":
        return root
    for child in root.get_children():
        var found := _find_ground(child)
        if found != null:
            return found
    return null

func _apply_material_recursive(node: Node) -> void:
    if node is MeshInstance3D:
        (node as MeshInstance3D).material_override = _material
    for child in node.get_children():
        _apply_material_recursive(child)

func _evaluate(inputs: Dictionary) -> Dictionary:
    var layers_value: Variant = inputs.get("layers", [])
    var layers: Array = layers_value if layers_value is Array else []
    var weights: Array[float] = [0.0, 0.0, 0.0, 0.0]
    var scores: Array[float] = [0.0, 0.0, 0.0, 0.0]
    var highest := -INF
    for i in range(4):
        var layer: Dictionary = layers[i] if i < layers.size() and layers[i] is Dictionary else {}
        var control := maxf(float(layer.get("control", 0.0)), 0.0)
        scores[i] = float(layer.get("height", 0.0)) * control
        highest = maxf(highest, scores[i])
    if highest == -INF:
        highest = 0.0
    var transition := maxf(float(inputs.get("transition", 0.0)), EPS_TRANSITION)
    var weight_sum := 0.0
    for i in range(4):
        var layer: Dictionary = layers[i] if i < layers.size() and layers[i] is Dictionary else {}
        var control := maxf(float(layer.get("control", 0.0)), 0.0)
        var competition := maxf(scores[i] - highest + transition, 0.0)
        weights[i] = (competition + EPS_COMPETE) * control
        weight_sum += weights[i]
    var divisor := maxf(weight_sum, EPS_DENOM)
    for i in range(4):
        weights[i] /= divisor

    var albedo := Vector3.ZERO
    var roughness := 0.0
    var metallic := 0.0
    var blended_height := 0.0
    var normal_sum := Vector3.ZERO
    for i in range(4):
        var layer: Dictionary = layers[i] if i < layers.size() and layers[i] is Dictionary else {}
        var w := weights[i]
        albedo += _vec3(layer.get("albedo_linear", [0.0, 0.0, 0.0])) * w
        roughness += float(layer.get("roughness", 0.0)) * w
        metallic += float(layer.get("metallic", 0.0)) * w
        blended_height += float(layer.get("height", 0.0)) * w
        normal_sum += _vec3(layer.get("normal_ts", [0.0, 0.0, 1.0])) * w
    var base_normal := _safe_normalize(normal_sum)
    var final_normal := base_normal
    if bool(inputs.get("detail_enabled", false)):
        final_normal = _rnm(base_normal, _safe_normalize(_vec3(inputs.get("detail_normal_ts", [0.0, 0.0, 1.0]))))
    return {
        "weights": weights,
        "albedo_linear": _array3(albedo),
        "roughness_metallic_height": [roughness, metallic, blended_height],
        "base_normal_ts": _array3(base_normal),
        "final_normal_ts": _array3(final_normal)
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
    if value.length_squared() <= EPS_DENOM * EPS_DENOM:
        return FALLBACK_NORMAL
    return value.normalized()

func _rnm(base: Vector3, detail: Vector3) -> Vector3:
    var t := base + Vector3(0.0, 0.0, 1.0)
    var u := detail * Vector3(-1.0, -1.0, 1.0)
    return _safe_normalize(t * t.dot(u) - u * t.z)
