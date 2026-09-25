extends Node
## Deterministic projected hit decal; the host scene and its FPS logic stay untouched.

var scene_root: Node
var test_input: Dictionary = {}
var hit_data: Dictionary = {}
var projector: Dictionary = {}
var surface: Dictionary = {}
var elapsed_s: float = 0.0
var event_started_s: float = 0.0
var lifetime_s: float = 2.0
var current_step: int = 0
var event_active: bool = false
var target_name: String = "target_a"
var event_id: int = -1
var samples: Array = []
var visual_decal: Decal
var visual_target: Node3D

func vec3(a: Array) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs.duplicate(true)
	hit_data = test_input.get("hit", {}).duplicate(true)
	projector = test_input.get("projector", {}).duplicate(true)
	surface = test_input.get("surface", {}).duplicate(true)
	lifetime_s = maxf(0.0, float(test_input.get("lifetime_s", 2.0)))
	elapsed_s = 0.0
	current_step = 0
	samples.clear()
	inject_hit(hit_data)

func setup(context: Dictionary) -> void:
	if test_input.is_empty(): configure(context.get("root", self), default_input())

func reset(_state: Dictionary = {}) -> void:
	elapsed_s = 0.0
	current_step = 0
	samples.clear()
	inject_hit(test_input.get("hit", hit_data).duplicate(true))

func step(dt: float, _state: Dictionary = {}) -> void:
	elapsed_s += dt
	current_step += 1
	if event_active and elapsed_s - event_started_s >= lifetime_s: event_active = false
	update_visual()

func on_event(_name: String, payload: Dictionary, _state: Dictionary = {}) -> void:
	var incoming_id: int = int(payload.get("event_id", -1))
	if incoming_id >= 0 and incoming_id == event_id: return
	var merged: Dictionary = hit_data.duplicate(true)
	for key in payload: merged[key] = payload[key]
	inject_hit(merged)

func inject_hit(payload: Dictionary) -> void:
	hit_data = payload.duplicate(true)
	target_name = canonical_target(str(hit_data.get("target", "target_a")))
	event_id = int(hit_data.get("event_id", -1))
	event_started_s = maxf(elapsed_s, float(hit_data.get("time_s", elapsed_s)))
	event_active = target_allowed(target_name) and lifetime_s > 0.0
	install_visual()

func canonical_target(value: String) -> String:
	var key: String = value.to_lower().replace(" ", "").replace("_", "").replace("-", "")
	if key == "targeta": return "target_a"
	if key == "targetb": return "target_b"
	if key == "targetc": return "target_c"
	return value.to_lower()

func target_allowed(value: String) -> bool:
	for allowed in test_input.get("allowed_targets", ["target_a", "target_b"]):
		if canonical_target(str(allowed)) == canonical_target(value): return true
	return false

func target_node() -> Node3D:
	if scene_root == null: return null
	var wanted: String = str({"target_a":"TargetA", "target_b":"TargetB", "target_c":"TargetC"}.get(target_name, target_name))
	return scene_root.find_child(wanted, true, false) as Node3D

func hit_world_position() -> Vector3:
	var node: Node3D = target_node()
	var local: Vector3 = vec3(hit_data.get("local_position", [0,0,0]))
	return node.global_transform * local if node != null else local

func hit_world_normal() -> Vector3:
	var node: Node3D = target_node()
	var normal: Vector3 = vec3(hit_data.get("local_normal", [0,0,1])).normalized()
	return (node.global_transform.basis * normal).normalized() if node != null else normal

func orientation_weight(cosine: float) -> float:
	var low: float = float(projector.get("cos_reject", 0.2))
	var high: float = float(projector.get("cos_full", 0.8))
	if high <= low: return 1.0 if cosine >= high else 0.0
	return smoothstep(low, high, clampf(cosine, 0.0, 1.0))

func default_input() -> Dictionary:
	return {"viewport":[128,128],"record_after_steps":[1,30,60,180],"camera":{"eye":[0,0,4],"target":[0,0,0],"up":[0,1,0],"fov_degrees":60.0},"surface":{"albedo_linear":[0.5,0.5,0.5]},"projector":{"scale":[0.5,0.5,0.2],"cos_reject":0.2,"cos_full":0.8,"albedo_linear":[0.15,0.03,0.01],"opacity":0.8},"hit":{"event_id":1,"target":"target_a","time_s":0.0,"local_position":[0,0,0],"local_normal":[0,0,1]},"lifetime_s":2.0,"allowed_targets":["target_a","target_b"]}

func make_texture() -> Texture2D:
	var image: Image = Image.create(128, 128, false, Image.FORMAT_RGBA8)
	var ink: Array = projector.get("albedo_linear", [0.15,0.03,0.01])
	for y in range(128):
		for x in range(128):
			var q: Vector2 = Vector2(float(x)-63.5, float(y)-63.5) / 63.5
			var alpha: float = clampf((1.0-q.length())/0.12, 0.0, 1.0)*float(projector.get("opacity",0.8))
			image.set_pixel(x,y,Color(float(ink[0]),float(ink[1]),float(ink[2]),alpha))
	image.generate_mipmaps()
	return ImageTexture.create_from_image(image)

func install_visual() -> void:
	var node: Node3D = target_node()
	if node == null or not event_active:
		if is_instance_valid(visual_decal): visual_decal.visible = false
		return
	if is_instance_valid(visual_decal) and visual_target != node:
		visual_decal.queue_free(); visual_decal = null
	visual_target = node
	if visual_decal == null:
		visual_decal = Decal.new()
		visual_decal.name = "HitProjectedDecal"
		visual_decal.texture_albedo = make_texture()
		visual_decal.albedo_mix = 1.0
		visual_decal.size = Vector3(1.0,0.4,1.0)
		node.add_child(visual_decal)
	update_visual()

func update_visual() -> void:
	if not is_instance_valid(visual_decal): return
	visual_decal.position = vec3(hit_data.get("local_position",[0,0,0])) + vec3(hit_data.get("local_normal",[0,0,1])).normalized()*0.03
	visual_decal.rotation_degrees = Vector3(90,0,0)
	visual_decal.visible = event_active and elapsed_s-event_started_s < lifetime_s

func projector_local(world_position: Vector3) -> Vector3:
	var normal: Vector3 = hit_world_normal()
	var up: Vector3 = Vector3.UP if absf(normal.dot(Vector3.UP)) < 0.99 else Vector3.RIGHT
	var frame: Basis = Basis.looking_at(-normal, up)
	var q: Vector3 = frame.inverse()*(world_position-hit_world_position())
	var scale: Vector3 = vec3(projector.get("scale",[0.5,0.5,0.2]))
	return Vector3(q.x/scale.x,q.y/scale.y,q.z/scale.z)

func background_pixel() -> Dictionary:
	return {"visible":false,"world_position":null,"projector_local_position":null,"uv":null,"opacity":0.0,"normal":null,"albedo_linear":null}

func pixel_entry(x: int, y: int, w: int, h: int) -> Dictionary:
	var camera: Dictionary = test_input.get("camera", default_input().camera)
	var eye: Vector3 = vec3(camera.get("eye",[0,0,4]))
	var aim: Vector3 = vec3(camera.get("target",[0,0,0]))
	var forward: Vector3 = (aim-eye).normalized()
	var right: Vector3 = forward.cross(vec3(camera.get("up",[0,1,0]))).normalized()
	var up: Vector3 = right.cross(forward).normalized()
	var nx: float = 2.0*(float(x)+0.5)/float(w)-1.0
	var ny: float = 1.0-2.0*(float(y)+0.5)/float(h)
	var half_fov: float = tan(deg_to_rad(float(camera.get("fov_degrees",60.0)))*0.5)
	var ray: Vector3 = (forward+right*nx*half_fov*float(w)/float(h)+up*ny*half_fov).normalized()
	if absf(ray.z)<0.000001: return background_pixel()
	var distance: float = -eye.z/ray.z
	var position: Vector3 = eye+ray*distance
	if distance<=0.0 or absf(position.x)>1.0 or absf(position.y)>1.0: return background_pixel()
	var local: Vector3 = projector_local(position)
	var normal: Vector3 = hit_world_normal()
	var inside: bool = absf(local.x)<=0.5 and absf(local.y)<=0.5 and absf(local.z)<=0.5
	var opacity: float = 0.0
	var base: Array = surface.get("albedo_linear",[0.5,0.5,0.5])
	var albedo: Array = [float(base[0]),float(base[1]),float(base[2])]
	if event_active and elapsed_s-event_started_s<lifetime_s and inside:
		opacity = float(projector.get("opacity",0.8))*orientation_weight(normal.dot(-ray))
		var ink: Array = projector.get("albedo_linear",[0.15,0.03,0.01])
		albedo = [lerpf(float(base[0]),float(ink[0]),opacity),lerpf(float(base[1]),float(ink[1]),opacity),lerpf(float(base[2]),float(ink[2]),opacity)]
	return {"visible":true,"world_position":[position.x,position.y,position.z],"projector_local_position":[local.x,local.y,local.z],"uv":[local.x+0.5,local.y+0.5],"opacity":opacity,"normal":[normal.x,normal.y,normal.z],"albedo_linear":albedo}

func sample() -> Dictionary:
	var viewport: Array = test_input.get("viewport",[128,128])
	var width: int = int(viewport[0]); var height: int = int(viewport[1])
	var pixels: Array = []; pixels.resize(width*height)
	for y in range(height):
		for x in range(width): pixels[y*width+x] = pixel_entry(x,y,width,height)
	var active: Variant = target_name if event_active and elapsed_s-event_started_s<lifetime_s else null
	var result: Dictionary = {"step":current_step,"elapsed_s":elapsed_s,"active_target":active,"pixel_data":pixels,"background":background_pixel()}
	if current_step in test_input.get("record_after_steps",[1,30,60,180]): samples.append(result.duplicate(true))
	result["samples"] = samples.duplicate(true)
	return result
