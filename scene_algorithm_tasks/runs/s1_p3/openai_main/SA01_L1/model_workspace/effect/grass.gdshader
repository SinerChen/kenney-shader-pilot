shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx, world_vertex_coords;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D grass_orm : filter_linear_mipmap, repeat_disable;
uniform sampler2D interaction_field : filter_linear, repeat_disable;
uniform vec2 field_origin = vec2(-4.0);
uniform float field_size = 8.0;
uniform float bend_distance = 0.35;
uniform float flatten_distance = 0.1;
uniform float wind_strength = 0.0;
uniform float elapsed = 0.0;

void vertex() {
	float h = UV2.y;
	float height_weight = h * h;
	vec2 field_uv = (VERTEX.xz - field_origin) / field_size;
	vec4 influence = texture(interaction_field, field_uv);
	// RG already stores direction * strength; B is flatten strength.
	VERTEX.xz += influence.xy * bend_distance * height_weight;
	VERTEX.y -= influence.z * flatten_distance * height_weight;
	// Approximate the bent card normal from the derivative along blade height.
	vec3 width_tangent = normalize(cross(vec3(0.0, 1.0, 0.0), NORMAL));
	vec3 vertical_tangent = normalize(vec3(influence.x * bend_distance * 2.0 * h,
		1.0 - influence.z * flatten_distance * 2.0 * h,
		influence.y * bend_distance * 2.0 * h));
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
