extends RefCounted
# Retain all native water shading and assets. Replace only the wave stage.
var material: ShaderMaterial
const WAVE_UNIFORMS := """
uniform float gerstner_time = 0.0;
uniform int gerstner_count = 0;
uniform vec4 gerstner_shape[8]; // normalized direction.xy, amplitude, Q*A
uniform vec4 gerstner_motion[8]; // k, speed, phase, unused
"""
const WAVE_VERTEX := """
	vec2 q = VERTEX.xz;
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

func configure(root: Node, waves: Array, foam_enabled: bool) -> void:
	var ocean: Node3D = root.get_node("DeepOcean")
	material = ocean.material.duplicate() as ShaderMaterial
	var shader := Shader.new()
	var code: String = material.shader.code
	code = code.replace("#define VERTEX_WAVE\n", "// Wave displacement supplied by the candidate.\n")
	# The native foam accumulator divides by zero when FoamWaveCount is zero.
	code = code.replace("#define FOAM\n", "// Native procedural foam disabled.\n")
	if not foam_enabled:
		code = code.replace("#define SHORE_FOAM\n", "// No foam in this input.\n")
	code = code.replace("void vertex() {", WAVE_UNIFORMS + "\nvoid vertex() {\n" + WAVE_VERTEX)
	code = code.replace("float time = TIME;", "float time = gerstner_time;")
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
	# Designer retains its original material reference but must use the new copy.
	var designer: Node = ocean.get_node("WaterMaterialDesigner")
	designer.material = material
	for child in ocean.get_children():
		if child is MeshInstance3D and str(child.name).begins_with("_gen_nearplane"):
			# GPU deformation must not be culled against the original flat AABB.
			child.extra_cull_margin = 1.0

func update(time: float) -> void:
	material.set_shader_parameter("gerstner_time", time)
