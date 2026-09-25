extends RefCounted
# Only DeepOcean receives a private material; meshes and exhibit resources stay intact.
var material: ShaderMaterial
var ocean: Node3D
var history_image: Image
var history_texture: ImageTexture
var displacement_margin := 1.0
var bound_counts := {}
const WAVE_UNIFORMS := """
uniform float gerstner_time = 0.0;
uniform int gerstner_count = 0;
uniform vec4 gerstner_shape[8];
uniform vec4 gerstner_motion[8];
uniform sampler2D history_foam : repeat_enable, filter_linear;
uniform vec2 history_origin;
uniform vec2 history_extent;
uniform vec2 history_grid;
varying vec2 material_q;
void gerstner(vec2 q, out vec3 offset, out vec3 tx, out vec3 tz) {
 offset=vec3(0.0); tx=vec3(1.0,0.0,0.0); tz=vec3(0.0,0.0,1.0);
 for (int i=0;i<gerstner_count;i++) {
  vec4 w=gerstner_shape[i]; vec4 m=gerstner_motion[i];
  float theta=m.x*(dot(w.xy,q)-m.y*gerstner_time)+m.z; float s=sin(theta); float c=cos(theta);
  offset+=vec3(w.w*w.x*c,w.z*s,w.w*w.y*c);
  tx+=vec3(-w.w*m.x*w.x*w.x*s,w.z*m.x*w.x*c,-w.w*m.x*w.y*w.x*s);
  tz+=vec3(-w.w*m.x*w.x*w.y*s,w.z*m.x*w.y*c,-w.w*m.x*w.y*w.y*s);
 }
}
vec2 foam_hash(vec2 p) { return fract(sin(vec2(dot(p,vec2(127.1,311.7)),dot(p,vec2(269.5,183.3))))*43758.5453); }
"""
const WAVE_VERTEX := """
 // world_vertex_coords: capture the world parameter BEFORE displacement.
 vec2 q=VERTEX.xz; material_q=q;
 vec3 offset,tx,tz; gerstner(q,offset,tx,tz);
 VERTEX+=offset; NORMAL=normalize(cross(tz,tx)); TANGENT=normalize(tx); BINORMAL=normalize(cross(NORMAL,TANGENT));
"""
const WAVE_FRAGMENT := """
 // Analytic normal avoids vertex-normal undersampling on coarse native LODs.
 vec3 wave_offset,wave_tx,wave_tz; gerstner(material_q,wave_offset,wave_tx,wave_tz);
 NORMAL=normalize((VIEW_MATRIX*vec4(normalize(cross(wave_tz,wave_tx)),0.0)).xyz);
"""
const HISTORY_FRAGMENT := """
 // Half-texel alignment: texel i contains history at q=i*extent/grid.
 vec2 history_uv=(material_q-history_origin)/history_extent+0.5/history_grid;
 float coverage=clamp(texture(history_foam,history_uv).r,0.0,1.0);
 // Display contrast only. No feedback into numerical coverage.
 float foam_opacity=1.0-exp(-8.0*coverage);
 vec2 cell=material_q*14.0; vec2 cell_id=floor(cell); vec2 local=fract(cell); float bubble_distance=2.0;
 for(int by=-1;by<=1;by++) for(int bx=-1;bx<=1;bx++) { vec2 neighbor=vec2(float(bx),float(by)); vec2 seed=foam_hash(cell_id+neighbor); bubble_distance=min(bubble_distance,length(local-neighbor-seed)-mix(0.12,0.32,seed.x)); }
 float aa=max(length(fwidth(cell))*0.6,0.025); float pore=1.0-smoothstep(-aa,aa,bubble_distance);
 float resolved=1.0-smoothstep(0.3,1.0,length(fwidth(cell))); float micro=mix(0.8,mix(1.0,0.35,pore),resolved); float white=foam_opacity*micro;
 EMISSION*=1.0-white; ALBEDO=mix(ALBEDO,vec3(0.91,0.97,0.96),white); ROUGHNESS=mix(ROUGHNESS,0.82,white); SPECULAR=mix(SPECULAR,0.2,white);
"""

func configure(root: Node, waves: Array, _foam_enabled: bool) -> void:
	ocean = root.get_node("DeepOcean")
	material = ocean.material.duplicate() as ShaderMaterial
	var shader := Shader.new()
	var code: String = material.shader.code
	code = code.replace("#define VERTEX_WAVE\n", "// custom vertex waves\n")
	code = code.replace("#define FOAM\n", "// custom foam\n")
	code = code.replace("#define SHORE_FOAM\n", "// custom shore foam\n")
	code = code.replace("void vertex() {", WAVE_UNIFORMS + "\nvoid vertex() {\n" + WAVE_VERTEX)
	code = code.replace("void fragment() {", "void fragment() {\n" + WAVE_FRAGMENT)
	code = code.replace("float time = TIME;", "float time = gerstner_time;")
	var end := code.rfind("}")
	code = code.substr(0, end) + HISTORY_FRAGMENT + code.substr(end)
	shader.code = code
	material.shader = shader
	var shapes := PackedVector4Array()
	var motions := PackedVector4Array()
	shapes.resize(8)
	motions.resize(8)
	displacement_margin = 0.1
	for i in mini(waves.size(), 8):
		var w: Dictionary = waves[i]
		shapes[i] = Vector4(w.d.x, w.d.y, w.a, w.h)
		motions[i] = Vector4(w.k, w.speed, w.phase, 0.0)
		displacement_margin += absf(w.a) + absf(w.h)
	material.set_shader_parameter("gerstner_count", mini(waves.size(), 8))
	material.set_shader_parameter("gerstner_shape", shapes)
	material.set_shader_parameter("gerstner_motion", motions)
	# Setter and future host LOD builds use the same private material.
	ocean.material = material
	ocean.get_node("WaterMaterialDesigner").material = material
	if not ocean.child_entered_tree.is_connected(_bind_mesh):
		ocean.child_entered_tree.connect(_bind_mesh)
	for child in ocean.get_children():
		_bind_mesh(child)

func _bind_mesh(child: Node) -> void:
	if child is MeshInstance3D and (str(child.name).begins_with("_gen_nearplane_") or str(child.name).begins_with("_gen_farplane_")):
		child.set_surface_override_material(0, material)
		child.extra_cull_margin = displacement_margin

func audit() -> void:
	var near_count := 0
	var far_count := 0
	var errors := 0
	for child in ocean.get_children():
		if child is MeshInstance3D and str(child.name).begins_with("_gen_"):
			if str(child.name).begins_with("_gen_nearplane_"):
				near_count += 1
			else:
				far_count += 1
			# Engine property is float32; compare with tolerance.
			if child.get_surface_override_material(0) != material or child.extra_cull_margin + 0.00001 < displacement_margin:
				errors += 1
	var counts = {"near_lod_tiles":near_count, "mid_far_meshes":far_count, "binding_errors":errors}
	if counts != bound_counts:
		bound_counts = counts
		print("OCEAN_BINDING ", counts)

func update(time: float, values: Array, nx: int, nz: int, origin: Vector2, extent: Vector2) -> void:
	material.set_shader_parameter("gerstner_time", time)
	# RF avoids early-frame coverage quantization; one CPU history shared by all LODs.
	var data := PackedFloat32Array(values).to_byte_array()
	if history_texture == null:
		history_image = Image.create_from_data(nx, nz, false, Image.FORMAT_RF, data)
		history_texture = ImageTexture.create_from_image(history_image)
		material.set_shader_parameter("history_foam", history_texture)
		material.set_shader_parameter("history_origin", origin)
		material.set_shader_parameter("history_extent", extent)
		material.set_shader_parameter("history_grid", Vector2(nx, nz))
	else:
		history_image.set_data(nx, nz, false, Image.FORMAT_RF, data)
		history_texture.update(history_image)
	audit()
