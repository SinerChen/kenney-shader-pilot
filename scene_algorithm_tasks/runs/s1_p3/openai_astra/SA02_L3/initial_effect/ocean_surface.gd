extends RefCounted
# Keep native LOD geometry, water lighting/refraction and seabed assets.
# Only wave displacement and the foam source are replaced.
var material: ShaderMaterial
var history_image: Image
var history_texture: ImageTexture
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

vec2 foam_hash(vec2 p) {
	return fract(sin(vec2(dot(p,vec2(127.1,311.7)),dot(p,vec2(269.5,183.3)))) * 43758.5453);
}
"""
const WAVE_VERTEX := """
	vec2 q = VERTEX.xz; // native shader uses world_vertex_coords
	material_q = q; // BEFORE displacement, shared by every LOD
	vec3 offset = vec3(0.0);
	vec3 tx = vec3(1.0, 0.0, 0.0);
	vec3 tz = vec3(0.0, 0.0, 1.0);
	for (int i = 0; i < gerstner_count; i++) {
		vec4 w = gerstner_shape[i];
		vec4 m = gerstner_motion[i];
		vec2 d = w.xy;
		float theta = m.x * (dot(d, q) - m.y * gerstner_time) + m.z;
		float s = sin(theta);
		float c = cos(theta);
		offset += vec3(w.w*d.x*c, w.z*s, w.w*d.y*c);
		tx += vec3(-w.w*m.x*d.x*d.x*s, w.z*m.x*d.x*c, -w.w*m.x*d.y*d.x*s);
		tz += vec3(-w.w*m.x*d.x*d.y*s, w.z*m.x*d.y*c, -w.w*m.x*d.y*d.y*s);
	}
	VERTEX += offset;
	NORMAL = normalize(cross(tz, tx));
	TANGENT = normalize(tx);
	BINORMAL = normalize(cross(NORMAL, TANGENT));
"""
const HISTORY_FRAGMENT := """
	// Texel i stores q=i*extent/grid: half-texel offset aligns samples exactly.
	vec2 history_uv = (material_q-history_origin)/history_extent + 0.5/history_grid;
	float coverage = clamp(texture(history_foam, history_uv).r, 0.0, 1.0);
	// Optical contrast only; never feed this display mapping back into history.
	float foam_opacity = 1.0-exp(-8.0*coverage);
	// Jittered bubble pores attached to q; no scrolling UV or extra time.
	vec2 cell = material_q*14.0;
	vec2 cell_id = floor(cell);
	vec2 local = fract(cell);
	float bubble_distance = 2.0;
	for (int by=-1; by<=1; by++) {
		for (int bx=-1; bx<=1; bx++) {
			vec2 neighbor = vec2(float(bx),float(by));
			vec2 seed = foam_hash(cell_id+neighbor);
			bubble_distance = min(bubble_distance,length(local-neighbor-seed)-mix(0.12,0.32,seed.x));
		}
	}
	float aa = max(length(fwidth(cell))*0.6,0.025);
	float pore = 1.0-smoothstep(-aa,aa,bubble_distance);
	float resolved = 1.0-smoothstep(0.3,1.0,length(fwidth(cell)));
	float micro = mix(0.8,mix(1.0,0.35,pore),resolved);
	float white = foam_opacity*micro;
	EMISSION *= 1.0-white;
	ALBEDO = mix(ALBEDO,vec3(0.91,0.97,0.96),white);
	ROUGHNESS = mix(ROUGHNESS,0.82,white);
	SPECULAR = mix(SPECULAR,0.2,white);
"""

func configure(root: Node, waves: Array, _foam_enabled: bool) -> void:
	var ocean: Node3D = root.get_node("DeepOcean")
	material = ocean.material.duplicate() as ShaderMaterial
	var shader := Shader.new()
	var code: String = material.shader.code
	code = code.replace("#define VERTEX_WAVE\n", "// Candidate Gerstner displacement.\n")
	code = code.replace("#define FOAM\n", "// Compression history replaces native foam.\n")
	code = code.replace("#define SHORE_FOAM\n", "// No unrelated depth-based foam source.\n")
	code = code.replace("void vertex() {", WAVE_UNIFORMS + "\nvoid vertex() {\n" + WAVE_VERTEX)
	code = code.replace("float time = TIME;", "float time = gerstner_time;")
	var end := code.rfind("}")
	code = code.substr(0,end) + HISTORY_FRAGMENT + code.substr(end)
	shader.code = code
	material.shader = shader
	var shapes := PackedVector4Array()
	var motions := PackedVector4Array()
	shapes.resize(8)
	motions.resize(8)
	for i in mini(waves.size(), 8):
		var w: Dictionary = waves[i]
		shapes[i] = Vector4(w.d.x, w.d.y, w.a, w.h)
		motions[i] = Vector4(w.k, w.speed, w.phase, 0.0)
	material.set_shader_parameter("gerstner_count", mini(waves.size(), 8))
	material.set_shader_parameter("gerstner_shape", shapes)
	material.set_shader_parameter("gerstner_motion", motions)
	ocean.material = material
	var designer: Node = ocean.get_node("WaterMaterialDesigner")
	designer.material = material
	for child in ocean.get_children():
		if child is MeshInstance3D and str(child.name).begins_with("_gen_nearplane"):
			child.extra_cull_margin = 1.0

func update(time: float, values: Array, nx: int, nz: int, origin: Vector2, extent: Vector2) -> void:
	material.set_shader_parameter("gerstner_time", time)
	# RF avoids 8-bit quantization of the small early-frame coverage values.
	var data := PackedFloat32Array(values).to_byte_array()
	if history_texture == null:
		history_image = Image.create_from_data(nx,nz,false,Image.FORMAT_RF,data)
		history_texture = ImageTexture.create_from_image(history_image)
		material.set_shader_parameter("history_foam",history_texture)
		material.set_shader_parameter("history_origin",origin)
		material.set_shader_parameter("history_extent",extent)
		material.set_shader_parameter("history_grid",Vector2(nx,nz))
	else:
		history_image.set_data(nx,nz,false,Image.FORMAT_RF,data)
		history_texture.update(history_image)
