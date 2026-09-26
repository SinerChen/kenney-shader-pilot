extends Node

var adapter
var bridge
var materials: Dictionary = {}
var particle_mesh: MultiMeshInstance3D
const DISPLAY_SIZE = Vector2i(40,32)

const OPTICAL = """
shader_type spatial;
render_mode unshaded, cull_disabled, fog_disabled;
uniform sampler2D optical_uv : filter_linear, repeat_disable;
uniform sampler2D optical_f : filter_linear, repeat_disable;
uniform sampler2D optical_absorb : filter_linear, repeat_disable;
uniform sampler2D background_tex : filter_linear, repeat_disable;
uniform vec3 reflection_color = vec3(.4,.55,.75);
uniform vec3 fallback_color = vec3(.06,.08,.13);
uniform bool front = false;
uniform float visibility = 1.;
void fragment(){
    if(visibility<.5)discard;
    if(front && length((UV-.5)*vec2(1.,1.))>.49)discard;
    vec4 uv=texture(optical_uv,UV);
    float f=texture(optical_f,UV).r;
    vec3 absorb=texture(optical_absorb,UV).rgb;
    vec3 back=uv.z>.5?texture(background_tex,uv.xy).rgb:fallback_color;
    ALBEDO=f*reflection_color+(1.-f)*absorb*back;
}
"""

func setup(owner_adapter, owner_bridge):
	adapter=owner_adapter
	bridge=owner_bridge
	for target in bridge.task.authorized_runtime_bindings:
		var mat=ShaderMaterial.new()
		var shader=Shader.new()
		shader.code=OPTICAL
		mat.shader=shader
		if adapter.task_id.begins_with("E"):
			var front=target != "RearWater"
			mat.set_shader_parameter("front",front)
			mat.set_shader_parameter("background_tex",bridge.background("front" if front else "rear"))
		bridge.bind_material(target,mat)
		materials[target]=mat

func texture(resource: Dictionary, channels: Array, size: Vector2i) -> ImageTexture:
	var rows=adapter._values(resource)
	var data=PackedFloat32Array()
	data.resize(size.x*size.y*4)
	for i in rows.size():
		for k in channels.size(): data[i*4+k]=rows[i][int(channels[k])]
	return ImageTexture.create_from_image(Image.create_from_data(size.x,size.y,false,Image.FORMAT_RGBAF,data.to_byte_array()))

func constant_texture(value: Vector4) -> ImageTexture:
	return ImageTexture.create_from_image(Image.create_from_data(1,1,false,Image.FORMAT_RGBAF,PackedFloat32Array([value.x,value.y,value.z,value.w]).to_byte_array()))

func projection_array() -> Array:
	var projection=bridge.camera.get_camera_projection()*Projection(bridge.camera.global_transform.affine_inverse())
	var out: Array=[]
	for column in 4:
		for row in 4: out.append(projection[column][row])
	return out

func update():
	var p=adapter.config
	var task=adapter.task_id
	var grid_size=Vector2i(int(p.grid_size[0]),int(p.grid_size[1]))
	var n=grid_size.x*grid_size.y
	if true:
		for target in materials:
			var front=true
			var size=DISPLAY_SIZE if front else grid_size
			var rays: Array=[]
			for y in size.y:
				for x in size.x:
					var point=Vector3(-.8+(x+.5)/size.x*1.6,1.85-(y+.5)/size.y*1.3,1.)
					var incident=(point-bridge.camera.global_position).normalized()
					var normal=Vector3(0,0,1)
					if normal.dot(incident)>0.:normal=-normal
					rays.append([incident.x,incident.y,incident.z,normal.x,normal.y,normal.z,point.x,point.y,point.z])
			var optical=adapter._dispatch("optics_query",{"optical_rays":rays,"view_projection":projection_array(),"ell":p.ell if front else p.get("rear_ell",.35),"eta_t":p.eta_t if front else 1.33})
			adapter.state["front_optical_terms" if front else "rear_optical_terms"]=optical
			var mat=materials[target]
			mat.set_shader_parameter("optical_uv",texture(optical,[11,12,13],size))
			mat.set_shader_parameter("optical_f",texture(optical,[0],size))
			mat.set_shader_parameter("optical_absorb",texture(optical,[7,8,9],size))
			mat.set_shader_parameter("reflection_color",Vector3(p.reflection_color[0],p.reflection_color[1],p.reflection_color[2]))
			mat.set_shader_parameter("visibility",1.0 if (p.front_visible if front else p.rear_visible) else 0.0)
