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
    }else if(mode==1){
        vec2 hit=a.zw;
        float grid=.85+.15*sin(hit.x*100.)*sin(hit.y*85.);
        float wet=b.x;
        ALBEDO=mix(base_color,secondary_color,wet)*grid*(1.-a.y*2.);
        ROUGHNESS=mix(.9,.22,wet);
        NORMAL=normalize((VIEW_MATRIX*vec4(c.xyz,0.)).xyz);
    }else if(mode==2){
        vec3 color=base_color+secondary_color*a.x;
        color=color*b.w+b.rgb;
        ALBEDO=vec3(0.);
        EMISSION=color;
        SPECULAR=0.;
    }else if(mode==3){
        ALBEDO=mix(a.rgb,vec3(.88,.91,.86),c.x);
        NORMAL=normalize((VIEW_MATRIX*vec4(b.xyz,0.)).xyz);
        ROUGHNESS=mix(.27,.65,c.x);
        METALLIC=.1;
    }
}
"""
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
    if(front || visibility<.5)discard;
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
		shader.code=OPTICAL if adapter.task_id.begins_with("E") else SURFACE
		mat.shader=shader
		if adapter.task_id.begins_with("E"):
			var front=target != "RearWater"
			mat.set_shader_parameter("front",front)
			mat.set_shader_parameter("background_tex",bridge.background("front" if front else "rear"))
		bridge.bind_material(target,mat)
		materials[target]=mat
	if adapter.task_id == "A_L2":
		particle_mesh=MultiMeshInstance3D.new()
		particle_mesh.name="Embers"
		var mesh=SphereMesh.new()
		mesh.radius=.025
		mesh.height=.05
		mesh.radial_segments=6
		mesh.rings=3
		var mat=StandardMaterial3D.new()
		mat.vertex_color_use_as_albedo=true
		mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.emission_enabled=true
		mat.emission=Color(1,.24,.01)
		mesh.material=mat
		var multi=MultiMesh.new()
		multi.transform_format=MultiMesh.TRANSFORM_3D
		multi.use_colors=true
		multi.mesh=mesh
		multi.instance_count=adapter.config.anchors.size()
		multi.visible_instance_count=0
		particle_mesh.multimesh=multi
		bridge.add_effect(particle_mesh)

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
	if task.begins_with("A"):
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
		if task.ends_with("L2") and adapter.state.has("particle_state"):
			var parts=adapter._values(adapter.state.particle_state)
			var active=0
			for row in parts:
				if row[4] < .5 or not p.embers_visible:continue
				particle_mesh.multimesh.set_instance_transform(active,Transform3D(Basis.IDENTITY,Vector3(row[0],row[1],row[2])))
				particle_mesh.multimesh.set_instance_color(active,Color(1.,.12+.5*row[5],.02))
				active+=1
			particle_mesh.multimesh.visible_instance_count=active
	elif task.begins_with("B"):
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
		mat.set_shader_parameter("values1",texture(adapter.state.wetness_field,[0,1],grid_size) if adapter.state.has("wetness_field") else constant_texture(Vector4.ZERO))
		mat.set_shader_parameter("values2",texture(normal,[0,1,2],grid_size))
		mat.set_shader_parameter("base_color",Vector3(p.dry_color[0],p.dry_color[1],p.dry_color[2]))
		mat.set_shader_parameter("secondary_color",Vector3(p.wet_color[0],p.wet_color[1],p.wet_color[2]))
	elif task.begins_with("C"):
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
		if task.ends_with("L2"):
			var fog=adapter._dispatch("fog_query",{"view_rays":rays})
			adapter.state.fog_scatter=fog
			mat.set_shader_parameter("values1",texture(fog,[1,2,3,4],DISPLAY_SIZE))
		else:mat.set_shader_parameter("values1",constant_texture(Vector4(0,0,0,1)))
	elif task.begins_with("D"):
		var uvs: Array=[]
		for y in DISPLAY_SIZE.y:
			for x in DISPLAY_SIZE.x:uvs.append([(x+.5)/DISPLAY_SIZE.x,(y+.5)/DISPLAY_SIZE.y])
		var flow=adapter._dispatch("flow_query",{"uvs":uvs})
		adapter.state.flow_phases=flow
		var mat=materials.WaterPatch
		mat.set_shader_parameter("mode",3)
		mat.set_shader_parameter("values0",texture(flow,[6,7,8],DISPLAY_SIZE))
		mat.set_shader_parameter("values1",texture(flow,[9,10,11],DISPLAY_SIZE))
		mat.set_shader_parameter("values2",texture(adapter.state.foam_field,[0,1],grid_size) if adapter.state.has("foam_field") else constant_texture(Vector4.ZERO))
	elif task.begins_with("E"):
		for target in materials:
			var front=target != "RearWater"
			var size=DISPLAY_SIZE if front else grid_size
			var rays: Array=[]
			var normals=adapter._values(adapter.state.wave_normal) if adapter.state.has("wave_normal") else []
			var heights=adapter._column(adapter.state.wave_height_current,0) if adapter.state.has("wave_height_current") else p.height
			for y in size.y:
				for x in size.x:
					var point=Vector3(-.8+(x+.5)/size.x*1.6,1.85-(y+.5)/size.y*1.3,1.) if front else Vector3(-2.+(x+.5)/size.x*4.,heights[y*size.x+x],-1.5+(y+.5)/size.y*3.)
					var incident=(point-bridge.camera.global_position).normalized()
					var normal=Vector3(0,0,1)
					if not front:
						var row=normals[y*size.x+x] if not normals.is_empty() else [0.,1.,0.]
						normal=Vector3(row[0],row[1],row[2])
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
