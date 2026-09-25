shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx, world_vertex_coords;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D grass_orm : filter_linear_mipmap, repeat_disable;
uniform sampler2D interaction_field : filter_linear, repeat_disable;
uniform vec2 field_origin = vec2(-4.0);
uniform float field_size = 8.0;
uniform float bend_distance = 0.35;
uniform float flatten_distance = 0.1;
uniform float wind_strength = 0.22;
uniform float wind_speed = 1.6;
uniform vec2 wind_direction = vec2(1.0, 0.35);
uniform float elapsed = 0.0;

void vertex() {
	float h = clamp(UV2.y, 0.0, 1.0);
	float height_weight = h * h;
	vec2 field_uv = (VERTEX.xz - field_origin) / field_size;
	vec4 influence = texture(interaction_field, field_uv);
	vec2 wind_dir = normalize(wind_direction);
	// INSTANCE_CUSTOM.r is a stable per-card phase. Use the instance origin so
	// all vertices on one card share one wave and the root remains anchored.
	vec2 root_xz = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xz;
	float phase = dot(root_xz, wind_dir) * 1.7 + elapsed * wind_speed + INSTANCE_CUSTOM.r * 6.2831853;
	float wave = sin(phase);
	vec2 wind = wind_dir * (wave * wind_strength);
	vec2 horizontal = influence.xy * bend_distance + wind;
	VERTEX.xz += horizontal * height_weight;
	VERTEX.y -= influence.z * flatten_distance * height_weight;
	vec3 width_tangent = normalize(cross(vec3(0.0, 1.0, 0.0), NORMAL));
	vec3 vertical_tangent = normalize(vec3(horizontal.x * 2.0 * h,
		1.0 - influence.z * flatten_distance * 2.0 * h,
		horizontal.y * 2.0 * h));
	vec3 bent_normal = normalize(cross(vertical_tangent, width_tangent));
	NORMAL = dot(bent_normal, NORMAL) < 0.0 ? -bent_normal : bent_normal;
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
}
