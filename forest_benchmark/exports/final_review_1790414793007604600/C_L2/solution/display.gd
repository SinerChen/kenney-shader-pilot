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
    if(mode==2){
        vec3 color=base_color+secondary_color*a.x;
        color=color*b.w+b.rgb;
        ALBEDO=vec3(0.);
        EMISSION=color;
        SPECULAR=0.;
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
		var rays: Array=[]
		for y in DISPLAY_SIZE.y:
			for x in DISPLAY_SIZE.x:
				var point=Vector3(-2.+(x+.5)/DISPLAY_SIZE.x*4.,0.,-1.5+(y+.5)/DISPLAY_SIZE.y*3.)
				var direction=point-bridge.camera.global_position
				var unit=direction.normalized()
				points.append([point.x,point.y,point.z])
				var origin=bridge.camera.global_position
				rays.append([origin.x,origin.y,origin.z,unit.x,unit.y,unit.z,direction.length()])
		var cloud=adapter._dispatch("cloud_query",{"points":points})
		adapter.state.cloud_transmittance=cloud
		var mat=materials.GroundReceiver
		mat.set_shader_parameter("mode",2)
		mat.set_shader_parameter("values0",texture(cloud,[4],DISPLAY_SIZE))
		mat.set_shader_parameter("base_color",Vector3(p.ambient_color[0],p.ambient_color[1],p.ambient_color[2]))
		var light=Vector3(p.light_rgb[0],p.light_rgb[1],p.light_rgb[2])
		mat.set_shader_parameter("secondary_color",Vector3(p.direct_color[0],p.direct_color[1],p.direct_color[2])*light)
		mat.set_shader_parameter("values1",constant_texture(Vector4(0,0,0,1)))
