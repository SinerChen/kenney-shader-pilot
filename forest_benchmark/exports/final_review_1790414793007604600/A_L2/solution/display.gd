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
    if(mode==0){
        float grain=.8+.2*sin(UV.x*80.+sin(UV.y*11.));
        ALBEDO=mix(base_color*grain,secondary_color,a.z*show_effect);
        EMISSION=glow_color*a.w*show_effect*2.;
        ROUGHNESS=.85;
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
		var points: Array=[]
		for y in DISPLAY_SIZE.y:
			for x in DISPLAY_SIZE.x:
				points.append([(float(x)+.5)/DISPLAY_SIZE.x*1.6-.8,1.2-(float(y)+.5)/DISPLAY_SIZE.y*2.4,0.])
		var burn=adapter._dispatch("burn_query",{"points":points})
		adapter.state.material_channels=burn
		var mat=materials.TargetMesh
		mat.set_shader_parameter("mode",0)
		mat.set_shader_parameter("values0",texture(burn,[0,1,2,3],DISPLAY_SIZE))
		mat.set_shader_parameter("base_color",Vector3(p.wood_color[0],p.wood_color[1],p.wood_color[2]))
		mat.set_shader_parameter("secondary_color",Vector3(p.char_color[0],p.char_color[1],p.char_color[2]))
		mat.set_shader_parameter("show_effect",1.0 if p.burn_visible else 0.0)
