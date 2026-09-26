extends Node

var adapter
var bridge
var materials: Dictionary = {}
var particle_mesh: MultiMeshInstance3D
const DISPLAY_SIZE = Vector2i(40,32)

const SURFACE = """
shader_type spatial;
render_mode cull_disabled, fog_disabled;
uniform sampler2D values0 : filter_linear, repeat_disable;
uniform sampler2D values1 : filter_linear, repeat_disable;
uniform sampler2D values2 : filter_linear, repeat_disable;
uniform sampler2D height_field : filter_linear, repeat_disable;
uniform int mode = 0;
uniform vec3 base_color = vec3(.36,.2,.08);
uniform vec3 secondary_color = vec3(.06,.035,.02);
uniform vec3 glow_color = vec3(1,.2,.01);
uniform float show_effect = 1.;
void fragment() {
    vec4 a=texture(values0,UV),b=texture(values1,UV),c=texture(values2,UV);
    if(mode==1){
        vec2 hit=a.zw;
        float grid=.85+.15*sin(hit.x*100.)*sin(hit.y*85.);
        float wet=b.x;
        ALBEDO=mix(base_color,secondary_color,wet)*grid*(1.-a.y*2.);
        ROUGHNESS=mix(.9,.22,wet);
        NORMAL=normalize((VIEW_MATRIX*vec4(c.xyz,0.)).xyz);
    }
}
"""

func setup(owner_adapter, owner_bridge):
	adapter=owner_adapter
	bridge=owner_bridge
	for target in bridge.task.authorized_runtime_bindings:
		var mat=ShaderMaterial.new()
		var shader=Shader.new()
		shader.code=SURFACE
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
		var depth=adapter._column(adapter.state.depth_field,0) if adapter.state.has("depth_field") else p.depth
		var rays: Array=[]
		for y in grid_size.y:
			for x in grid_size.x:
				var point=Vector3(p.domain_min[0]+(x+.5)/grid_size.x*p.domain_size[0],0,p.domain_min[1]+(y+.5)/grid_size.y*p.domain_size[1])
				var v=(bridge.camera.global_position-point).normalized()
				rays.append([point.x,point.z,v.x,v.y,v.z])
		var hit=adapter._dispatch("pom_query",{"depth":depth,"pom_rays":rays})
		var negative: Array=[]
		for d in depth:negative.append(-d)
		var normal=adapter._dispatch("wave_normal_query",{"height":negative})
		adapter.state.pom_hit=hit
		var mat=materials.GroundPatch
		mat.set_shader_parameter("mode",1)
		mat.set_shader_parameter("values0",texture(hit,[0,1,2,3],grid_size))
		mat.set_shader_parameter("values1",constant_texture(Vector4.ZERO))
		mat.set_shader_parameter("values2",texture(normal,[0,1,2],grid_size))
		mat.set_shader_parameter("base_color",Vector3(p.dry_color[0],p.dry_color[1],p.dry_color[2]))
		mat.set_shader_parameter("secondary_color",Vector3(p.wet_color[0],p.wet_color[1],p.wet_color[2]))
