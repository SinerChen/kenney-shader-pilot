shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, specular_schlick_ggx, fog_disabled;

// Forward+ supplies the opaque scene in linear HDR. The engine performs the
// final exposure / tonemapping once, after transmission and PBR reflections.
uniform sampler2D scene_color : hint_screen_texture, repeat_disable, filter_linear_mipmap;
uniform sampler2D scene_depth : hint_depth_texture, repeat_disable, filter_nearest;
uniform float water_ior : hint_range(1.0, 1.6) = 1.333;
uniform float water_roughness : hint_range(0.01, 0.3) = 0.055;
varying float bead_radius;

void vertex() {
	bead_radius = INSTANCE_CUSTOM.r;
}

void fragment() {
	vec3 n = normalize(NORMAL);
	float ndv = clamp(dot(n, VIEW), 0.0, 1.0);
	float f0 = pow((water_ior - 1.0) / (water_ior + 1.0), 2.0);
	float fresnel = f0 + (1.0 - f0) * pow(1.0 - ndv, 5.0);
	vec3 ray = refract(-VIEW, n, 1.0 / water_ior);
	// A thin water cap approximation, not a second virtual camera or ray tracer.
	float travel = bead_radius * 1.4 * max(ndv, 0.15);
	vec4 projected = PROJECTION_MATRIX * vec4(VERTEX + ray * travel, 1.0);
	vec2 target_uv = projected.xy / projected.w * 0.5 + 0.5;
	bool in_screen = all(greaterThan(target_uv, vec2(0.002))) && all(lessThan(target_uv, vec2(0.998)));
	vec4 hit = INV_PROJECTION_MATRIX * vec4(target_uv * 2.0 - 1.0, textureLod(scene_depth, target_uv, 0.0).r, 1.0);
	float hit_z = hit.z / hit.w;
	// Reject a foreground leaf or a screen border instead of refracting it
	// into a droplet behind it. Only opaque objects occur in this buffer.
	if (!in_screen || hit_z > VERTEX.z + 0.0005) {
		target_uv = SCREEN_UV;
	}
	vec3 transmitted = textureLod(scene_color, target_uv, 0.0).rgb;
	ALBEDO = vec3(0.0);
	METALLIC = 0.0;
	// Godot 4.6 uses F0 = 0.16 * SPECULAR^2 (scene_forward_lights_inc.glsl).
	// Water F0 is about 0.0204, therefore SPECULAR is about 0.357.
	SPECULAR = sqrt(f0 / 0.16);
	ROUGHNESS = water_roughness;
	// EMISSION transports the already-lit background; it is not a light source.
	// No constant emission/tint is added. Direct sun and environment reflections
	// come from Godot's normal PBR lighting, including shadow/probe response.
	EMISSION = transmitted * (1.0 - fresnel);
	ALPHA = 1.0;
}
