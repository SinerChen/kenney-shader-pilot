extends Node
## Persistent interaction field, CPU numerical sampling, and host material bridge.

var scene_root: Node
var test_input: Dictionary = {}
var elapsed_s := 0.0
var step_index := 0
var patch_origin := Vector2(-4.0, -4.0)
var patch_size := 8.0
var field_width := 64
var field_height := 64
var texel_size := Vector2.ONE
var field := PackedFloat32Array()
var radius_m := 0.95
var interaction_strength := 0.95
var persistence_60hz := 0.92
var bend_m := 0.35
var flatten_m := 0.1
var active_until_s := 2.0
var keyframes: Array = []
var player_xz := Vector2(-3, 0)
var player_velocity_xz := Vector2.ZERO
var field_texture: ImageTexture

func configure(root: Node, inputs: Dictionary) -> void:
	scene_root = root
	test_input = inputs
	elapsed_s = 0.0
	step_index = 0
	var p: Dictionary = inputs.get("patch", {})
	var o: Array = p.get("origin_xz_m", [-4,-4])
	var r: Array = p.get("resolution", [64,64])
	patch_origin = Vector2(float(o[0]),float(o[1]))
	patch_size = float(p.get("size_m",8))
	field_width = int(r[0]); field_height = int(r[1])
	texel_size = Vector2(patch_size/field_width,patch_size/field_height)
	field.resize(field_width*field_height*4); field.fill(0)
	var q: Dictionary = inputs.get("interaction", {})
	radius_m=float(q.get("radius_m",.95)); interaction_strength=float(q.get("strength",.95))
	persistence_60hz=float(q.get("persistence_per_60hz_step",.92)); bend_m=float(q.get("bend_m",.35)); flatten_m=float(q.get("flatten_m",.1))
	active_until_s=float(inputs.get("interaction_active_until_s",2)); keyframes=inputs.get("player_keyframes",[]).duplicate(true)
	player_xz=_trajectory(0); _push_visual_state(); _update_texture()

func step(dt: float) -> void:
	if dt <= 0: return
	var old := player_xz
	elapsed_s += dt; step_index += 1; player_xz=_trajectory(elapsed_s); player_velocity_xz=(player_xz-old)/dt
	var decay := pow(clampf(persistence_60hz,0,1),dt*60.0)
	for i in field.size(): field[i]*=decay
	if elapsed_s < active_until_s-0.0000001: _stamp(player_xz)
	_push_visual_state(); _update_texture()

func _trajectory(t: float) -> Vector2:
	if keyframes.is_empty(): return Vector2.ZERO
	for i in keyframes.size()-1:
		var a: Dictionary=keyframes[i]; var b: Dictionary=keyframes[i+1]
		var ta:=float(a.get("time_s",0)); var tb:=float(b.get("time_s",ta))
		if t <= tb:
			var pa:Array=a.get("position_xz_m",[0,0]); var pb:Array=b.get("position_xz_m",[0,0])
			return Vector2(float(pa[0]),float(pa[1])).lerp(Vector2(float(pb[0]),float(pb[1])),clampf((t-ta)/maxf(tb-ta,.000001),0,1))
	var z:Array=keyframes.back().get("position_xz_m",[0,0]); return Vector2(float(z[0]),float(z[1]))

func _stamp(c: Vector2) -> void:
	for y in field_height:
		for x in field_width:
			var w:=patch_origin+Vector2((x+.5)*texel_size.x,(y+.5)*texel_size.y)
			var d:=w-c; var n:=d.length()
			if n>=radius_m: continue
			var t:=n/radius_m; var amount:=interaction_strength*(1-t*t*(3-2*t))
			var direction:=d.normalized() if n>.000001 else (player_velocity_xz.normalized() if player_velocity_xz.length_squared()>.000001 else Vector2.RIGHT)
			var k:=(y*field_width+x)*4
			if amount>=field[k+2]: field[k]=direction.x*amount; field[k+1]=direction.y*amount; field[k+2]=amount; field[k+3]=0

func _push_visual_state() -> void:
	if scene_root==null:return
	var pl:=scene_root.get_node_or_null("PlayerProxy") as Node3D
	if pl: pl.position=Vector3(player_xz.x,0,player_xz.y)

func _update_texture() -> void:
	var image:=Image.create(field_width,field_height,false,Image.FORMAT_RGBAF)
	for y in field_height:
		for x in field_width:
			var k:=(y*field_width+x)*4; image.set_pixel(x,y,Color(field[k],field[k+1],field[k+2],0))
	field_texture=ImageTexture.create_from_image(image)
	if scene_root:
		for i in 4:
			var n:=scene_root.get_node_or_null("GrassCards_%d"%i) as MultiMeshInstance3D
			if n and n.material_override is ShaderMaterial:
				var m:=n.material_override as ShaderMaterial
				m.set_shader_parameter("interaction_field",field_texture); m.set_shader_parameter("field_origin",patch_origin); m.set_shader_parameter("field_size",patch_size)
				m.set_shader_parameter("bend_distance",bend_m); m.set_shader_parameter("flatten_distance",flatten_m); m.set_shader_parameter("wind_strength",0.0)

func _sample_field(xz: Vector2) -> Vector3:
	var u: float=(xz.x-patch_origin.x)/patch_size*field_width-.5
	var v: float=(xz.y-patch_origin.y)/patch_size*field_height-.5
	if u<0 or v<0 or u>field_width-1 or v>field_height-1:return Vector3.ZERO
	var x0:int=clampi(floori(u),0,field_width-1); var y0:int=clampi(floori(v),0,field_height-1)
	var x1:int=min(x0+1,field_width-1); var y1:int=min(y0+1,field_height-1)
	var fx:float=u-x0; var fy:float=v-y0; var result:=Vector3.ZERO
	for yy: int in [y0,y1]:
		for xx: int in [x0,x1]:
			var weight:float=(1.0-fx if xx==x0 else fx)*(1.0-fy if yy==y0 else fy)
			var k:int=(yy*field_width+xx)*4
			result+=Vector3(field[k],field[k+1],field[k+2])*weight
	return result

func sample() -> Dictionary:
	var positions:Array=[]; var normals:Array=[]
	if scene_root==null:return {"step":step_index,"elapsed_s":elapsed_s,"field_rgba":Array(field),"positions":positions,"normals":normals}
	for gi in 4:
		var node:=scene_root.get_node_or_null("GrassCards_%d"%gi) as MultiMeshInstance3D
		if node==null or node.multimesh==null: continue
		var arrays:=node.multimesh.mesh.surface_get_arrays(0)
		var verts:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]; var base_normals:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]; var uv2:PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV2]
		for inst in node.multimesh.instance_count:
			var xf:=node.global_transform*node.multimesh.get_instance_transform(inst)
			for j in verts.size():
				var p:=xf*verts[j]; var f:=_sample_field(Vector2(p.x,p.z)); var h:=clampf(uv2[j].y,0,1); var hw:=h*h
				positions.append(p+Vector3(f.x*bend_m*hw,-f.z*flatten_m*hw,f.y*bend_m*hw))
				var n:Vector3=(xf.basis*base_normals[j]).normalized()
				# For a card, horizontal width tangent and deformed vertical tangent
				# define the geometric normal. This captures the visible lean while
				# preserving the original normal at h=0.
				var width_tangent:=Vector3.UP.cross(n).normalized()
				var vertical_tangent:=Vector3(f.x*bend_m*2*h,1.0-f.z*flatten_m*2*h,f.y*bend_m*2*h).normalized()
				var deformed_normal:=vertical_tangent.cross(width_tangent).normalized()
				if deformed_normal.dot(n)<0: deformed_normal=-deformed_normal
				normals.append(deformed_normal)
	return {"step":step_index,"elapsed_s":elapsed_s,"field_rgba":Array(field),"positions":positions,"normals":normals}
