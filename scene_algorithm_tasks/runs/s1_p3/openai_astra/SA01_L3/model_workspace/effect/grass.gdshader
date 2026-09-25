shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx, world_vertex_coords;
uniform sampler2D grass_albedo : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D grass_orm : filter_linear_mipmap, repeat_disable;
uniform float elapsed = 0.0;
uniform float wind_strength = 0.22;
uniform float wind_speed = 1.6;
uniform vec2 wind_direction = vec2(1.0, 0.35);
uniform vec3 player_position = vec3(-4.0, 0.0, 0.0);
uniform float interaction_radius = 0.95;
uniform float interaction_strength = 0.95;
uniform vec4 player_history[32];
uniform bool audit_roots = false;
uniform bool audit_tips = false;
uniform sampler2D interaction_field : filter_nearest, repeat_disable;
uniform vec2 patch_origin = vec2(-4.0);
uniform float patch_size = 8.0;
uniform float bend_m = 0.35;
uniform float flatten_m = 0.1;
uniform vec3 bottom_left;
uniform vec3 bottom_right;
uniform vec3 top_left;
uniform vec3 top_right;
vec3 cell(ivec2 p) {
	ivec2 size = textureSize(interaction_field, 0);
	if (p.x < 0 || p.y < 0 || p.x >= size.x || p.y >= size.y) { return vec3(0.0); }
	return texelFetch(interaction_field, p, 0).rgb;
}
vec3 field_at(vec2 point) {
	vec2 uv = (point - patch_origin) / patch_size;
	if (any(lessThan(uv, vec2(0.0))) || any(greaterThanEqual(uv, vec2(1.0)))) { return vec3(0.0); }
	vec2 grid = uv * vec2(textureSize(interaction_field, 0)) - vec2(0.5);
	ivec2 p = ivec2(floor(grid));
	vec2 f = fract(grid);
	return mix(mix(cell(p), cell(p + ivec2(1, 0)), f.x), mix(cell(p + ivec2(0, 1)), cell(p + ivec2(1, 1)), f.x), f.y);
}
vec3 wind_at(vec2 point) {
	vec2 direction = wind_direction / max(length(wind_direction), 0.000001);
	float phase = elapsed * wind_speed - dot(point, direction) * 1.3;
	float wave = 0.7 * sin(phase) + 0.3 * sin(phase * 2.17 + 0.8);
	return vec3(direction.x, 0.0, direction.y) * wind_strength * wave;
}
void vertex() {
	vec2 root = MODEL_MATRIX[3].xz;
	vec3 field = field_at(root);
	float h = clamp(UV2.y, 0.0, 1.0);
	float s = UV2.x;
	vec3 displacement = vec3(field.x * bend_m, -field.z * flatten_m, field.y * bend_m) + wind_at(root);
	// Shared by camera and shadow passes; no view-dependent deformation or TIME.
	VERTEX += displacement * h * h;
	vec3 ds = mat3(MODEL_MATRIX) * mix(bottom_right - bottom_left, top_right - top_left, h);
	vec3 dh = mat3(MODEL_MATRIX) * mix(top_left - bottom_left, top_right - bottom_right, s);
	dh += displacement * (2.0 * h);
	vec3 n = normalize(cross(ds, dh));
	NORMAL = dot(n, NORMAL) < 0.0 ? -n : n;
}
void fragment() {
	vec4 base = texture(grass_albedo, UV);
	vec3 orm = texture(grass_orm, UV).rgb;
	ALBEDO = base.rgb;
	ROUGHNESS = clamp(orm.g, 0.55, 1.0);
	METALLIC = 0.0;
	AO = mix(0.75, 1.0, orm.r);
	BACKLIGHT = base.rgb * 0.18;
	NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
	ALPHA = base.a;
	ALPHA_SCISSOR_THRESHOLD = 0.45;
	if (audit_roots || audit_tips) {
		bool keep = (audit_roots && UV2.y < 0.01) || (audit_tips && UV2.y > 0.99);
		ALPHA = keep ? 1.0 : 0.0;
		ALBEDO = vec3(0.0);
		EMISSION = audit_roots ? vec3(1.0,0.0,0.5) : vec3(0.0,0.5,1.0);
	}
}
