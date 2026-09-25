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
uniform vec4 player_history[32]; // x,z,age_seconds,valid; raw input, not a solved bend
uniform bool audit_roots = false;
uniform bool audit_tips = false;

void vertex() {
	// TASK: implement the requested level here. This starter is static.
	// VERTEX is world space; MODEL_MATRIX[3].xz is this card's root center.
	// UV2.y is normalized height: 0 at root, 1 at the top edge.
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
	// Fixed diagnostic display, not an animation implementation.
	if (audit_roots || audit_tips) {
		bool keep = (audit_roots && UV2.y < 0.01) || (audit_tips && UV2.y > 0.99);
		ALPHA = keep ? 1.0 : 0.0;
		ALBEDO = vec3(0.0);
		EMISSION = audit_roots ? vec3(1.0,0.0,0.5) : vec3(0.0,0.5,1.0);
	}
}
