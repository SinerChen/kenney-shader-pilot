shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_draw_never, depth_test_disabled, shadows_disabled;

uniform sampler2D scene_color : hint_screen_texture, repeat_disable, filter_nearest;
uniform sampler2D scene_depth : hint_depth_texture, repeat_disable, filter_nearest;
uniform float density_per_m = 0.01;
uniform float height_falloff_per_m = 0.15;
uniform float reference_height_m = 0.0;
// Already linear: deliberately no source_color conversion.
uniform vec3 fog_color_linear = vec3(0.65, 0.72, 0.78);

void vertex() {
	// Godot 4.6 reverse-Z near plane. Independent of mesh transform.
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

void fragment() {
	float depth = textureLod(scene_depth, SCREEN_UV, 0.0).r;
	// Clear depth has no finite visible surface; retain original sky/clouds.
	if (depth <= 0.0) {
		discard;
	}
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth);
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	ndc.z = depth * 2.0 - 1.0;
#endif
	vec4 view_h = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	vec3 view_position = view_h.xyz / view_h.w;
	vec3 endpoint = (INV_VIEW_MATRIX * vec4(view_position, 1.0)).xyz;
	vec3 startpoint = INV_VIEW_MATRIX[3].xyz;
	float ray_length = length(endpoint - startpoint);
	float e0 = -height_falloff_per_m * (startpoint.y - reference_height_m);
	float e1 = -height_falloff_per_m * (endpoint.y - reference_height_m);
	float x = abs(e1 - e0);
	float factor;
	if (x < 0.001) {
		factor = 1.0 - 0.5*x + x*x/6.0 - x*x*x/24.0;
	} else {
		factor = (1.0 - exp(-x)) / x;
	}
	// Log domain prevents overflow at very low elevations. Clamping only
	// occurs after tau is large enough that T is visually indistinguishable from 0.
	float tau = 0.0;
	if (density_per_m > 0.0 && ray_length > 0.0) {
		float log_tau = log(density_per_m) + log(ray_length) + max(e0,e1) + log(factor);
		tau = exp(min(log_tau, log(80.0)));
	}
	float transmittance = exp(-tau);
	vec3 background = textureLod(scene_color, SCREEN_UV, 0.0).rgb;
	ALBEDO = transmittance * background + (1.0 - transmittance) * fog_color_linear;
	ALPHA = 1.0;
}
