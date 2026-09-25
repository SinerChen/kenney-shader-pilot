extends Node
## Reverse-Z depth reconstruction / box projected decal reference.
## Supports both the scored configure/step/sample API and the original pilot adapter API.

var scene_root: Node
var test_input: Dictionary = {}
var elapsed_s: float = 0.0
var current_step: int = 0
var event_active: bool = false
var hit_data: Dictionary = {}
var projector: Dictionary = {}
var surface: Dictionary = {}
var lifetime_s: float = 2.0
var samples: Array = []
var target_name: String = "target_a"
var _visual_decal: Decal

func _vec3(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root; test_input = inputs; elapsed_s = 0.0; current_step = 0; samples.clear()
	surface = inputs.get("surface", {}); projector = inputs.get("projector", {}); hit_data = inputs.get("hit", {})
	lifetime_s = float(inputs.get("lifetime_s", 2.0)); target_name = str(hit_data.get("target", "target_a")); event_active = true
	_install_visual_decal()

func setup(context: Dictionary) -> void:
	if test_input.is_empty(): configure(context.get("root", self), _default_input())
	else: scene_root = context.get("root", scene_root)

func reset(_state: Dictionary = {}) -> void:
	elapsed_s = 0.0; current_step = 0; samples.clear(); event_active = true
	if is_instance_valid(_visual_decal): _visual_decal.visible = true

func step(dt: float, _state: Dictionary = {}) -> void:
	elapsed_s += dt; current_step += 1
	if elapsed_s >= lifetime_s: event_active = false
	if is_instance_valid(_visual_decal): _visual_decal.visible = event_active

func on_event(_event_name: String, payload: Dictionary, _state: Dictionary = {}) -> void:
	if not payload.is_empty():
		for k in payload: hit_data[k] = payload[k]
	event_active = true; elapsed_s = 0.0
	if is_instance_valid(_visual_decal): _visual_decal.visible = true

func _smooth_orientation(cosine: float) -> float:
	var lo: float = float(projector.get("cos_reject", 0.2)); var hi: float = float(projector.get("cos_full", 0.8))
	return smoothstep(lo, hi, clamp(cosine, 0.0, 1.0))

func _default_input() -> Dictionary:
	return {"viewport":[128,128], "camera":{"eye":[0,0,4],"target":[0,0,0],"up":[0,1,0],"fov_degrees":60.0}, "surface":{"vertices":[[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0]],"triangles":[[0,1,2],[0,2,3]],"albedo_linear":[0.5,0.5,0.5]}, "projector":{"origin":[0,0,0],"rotation_degrees":[0,0,0],"scale":[0.5,0.5,0.2],"cos_reject":0.2,"cos_full":0.8,"albedo_linear":[0.15,0.03,0.01],"opacity":0.8}, "hit":{"target":"target_a","local_position":[0,0,0],"local_normal":[0,0,1]}, "lifetime_s":2.0}

func _make_mark_texture() -> Texture2D:
	var image := Image.create(128, 128, false, Image.FORMAT_RGBA8)
	for y in range(128):
		for x in range(128):
			var q := Vector2(float(x)-63.5, float(y)-63.5) / 63.5
			var r: float = q.length()
			var edge: float = clamp((1.0-r)/0.12, 0.0, 1.0)
			var grain: float = 0.92 + 0.08 * sin(float(x*17+y*29))
			image.set_pixel(x,y,Color(0.15,0.03,0.01,edge*grain*0.8))
	image.generate_mipmaps()
	return ImageTexture.create_from_image(image)

func _install_visual_decal() -> void:
	if scene_root == null or not is_instance_valid(scene_root): return
	var target: Node = scene_root.find_child("TargetA", true, false)
	if target == null or _visual_decal != null: return
	_visual_decal = Decal.new(); _visual_decal.name = "DepthReconstructedDecal"
	# Godot decals project along local -Y. Rotate that axis toward receiver local -Z.
	_visual_decal.position = _vec3(hit_data.get("local_position", [0,0,0])) + Vector3(0,0,0.55)
	_visual_decal.rotation_degrees.x = 90.0; _visual_decal.size = Vector3(1.0, 0.4, 1.0)
	_visual_decal.texture_albedo = _make_mark_texture(); _visual_decal.albedo_mix = 0.8
	_visual_decal.distance_fade_enabled = true; _visual_decal.distance_fade_begin = 8.0; _visual_decal.distance_fade_length = 4.0
	target.add_child(_visual_decal)

func _projector_local(world_position: Vector3) -> Vector3:
	var origin := _vec3(projector.get("origin", [0,0,0])); var scale := _vec3(projector.get("scale", [0.5,0.5,0.2]))
	var degrees := _vec3(projector.get("rotation_degrees", [0,0,0])); var rotation := Basis.from_euler(degrees * PI / 180.0)
	var q: Vector3 = rotation.inverse() * (world_position-origin)
	return Vector3(q.x/scale.x, q.y/scale.y, q.z/scale.z)

func _pixel_entry(x: int, y: int, w: int, h: int) -> Dictionary:
	# Reconstruct world position from the reverse-Z depth of the z=0 receiver.
	# For this fixed planar input, ray/plane intersection is the exact inverse projection.
	var camera: Dictionary = test_input.get("camera", _default_input().camera)
	var eye := _vec3(camera.get("eye", [0,0,4])); var target := _vec3(camera.get("target", [0,0,0])); var up_hint := _vec3(camera.get("up", [0,1,0]))
	var forward: Vector3 = (target-eye).normalized(); var right: Vector3 = forward.cross(up_hint).normalized(); var up: Vector3 = right.cross(forward).normalized()
	var ndc_x: float = (2.0*(float(x)+0.5)/float(w)-1.0); var ndc_y: float = (1.0-2.0*(float(y)+0.5)/float(h))
	var tan_half: float = tan(deg_to_rad(float(camera.get("fov_degrees",60.0)))*0.5)
	var ray: Vector3 = (forward + right*ndc_x*tan_half*float(w)/float(h) + up*ndc_y*tan_half).normalized()
	var t: float = -eye.z/ray.z; var p: Vector3 = eye + ray*t
	var visible: bool = t > 0.0 and abs(p.x) <= 1.0 and abs(p.y) <= 1.0
	if not visible: return {"visible":false,"world_position":null,"projector_local_position":null,"uv":null,"opacity":0.0,"normal":null,"albedo_linear":null}
	var local := _projector_local(p); var uv: Array = [local.x+0.5,local.y+0.5]; var opacity: float = 0.0
	var base: Array = surface.get("albedo_linear",[0.5,0.5,0.5]); var albedo: Array = [float(base[0]),float(base[1]),float(base[2])]
	var normal := Vector3(0,0,1); var inside: bool = abs(local.x)<=0.5 and abs(local.y)<=0.5 and abs(local.z)<=0.5
	var weight: float = _smooth_orientation(normal.dot(Vector3(0,0,1)))
	if event_active and elapsed_s < lifetime_s and inside and weight > 0.0:
		opacity = float(projector.get("opacity",0.8))*weight; var ink: Array = projector.get("albedo_linear",[0.15,0.03,0.01])
		albedo = [lerp(float(base[0]),float(ink[0]),opacity),lerp(float(base[1]),float(ink[1]),opacity),lerp(float(base[2]),float(ink[2]),opacity)]
	return {"visible":true,"world_position":[p.x,p.y,p.z],"projector_local_position":[local.x,local.y,local.z],"uv":uv,"opacity":opacity,"normal":[0.0,0.0,1.0],"albedo_linear":albedo}

func sample() -> Dictionary:
	var vp: Array = test_input.get("viewport",[128,128]); var w: int = int(vp[0]); var h: int = int(vp[1]); var pixels: Array = []; pixels.resize(w*h)
	for y in range(h):
		for x in range(w): pixels[y*w+x] = _pixel_entry(x,y,w,h)
	var result := {"step":current_step,"elapsed_s":elapsed_s,"active_target":target_name if event_active and elapsed_s<lifetime_s else null,"pixel_data":pixels}
	if current_step in [1,30,60,180]: samples.append(result.duplicate(true))
	result["samples"] = samples.duplicate(true); return result
