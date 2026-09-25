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


vec2 wind_at(vec2 root, float phase) {
    float direction_length = length(wind_direction);
    vec2 direction = direction_length > 0.00001 ? wind_direction / direction_length : vec2(0.0);
    float wave = sin(elapsed * wind_speed + dot(root, vec2(0.75,0.48)) + phase);
    float ripple = sin(elapsed * wind_speed * 1.87 + root.y * 1.9 + phase * 2.0);
    return direction * wind_strength * (0.72 * wave + 0.22 * ripple);
}
void vertex() {
    vec2 root = MODEL_MATRIX[3].xz;
    float h = UV2.y;
    vec2 wind = wind_at(root, INSTANCE_CUSTOM.r * 6.283185);
    vec2 bend = wind;
    float mask = h * h;
    VERTEX.xz += bend * mask;
    // Shorten vertical projection as the card bends. Every root vertex stays put.
    VERTEX.y -= h * (1.0 - inversesqrt(1.0 + dot(bend,bend) * 1.8)) * 0.55;
    NORMAL = normalize(NORMAL + vec3(-bend.x,0.0,-bend.y) * h * 0.35);
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
