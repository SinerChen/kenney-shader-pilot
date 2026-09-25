shader_type spatial;
// Binary leaf coverage: the same discard runs for depth, shadows and color.
// No ALPHA output: surviving fragments belong to the opaque screen capture.
render_mode depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;
uniform vec4 albedo : source_color;
uniform sampler2D texture_albedo : source_color, filter_linear_mipmap, repeat_enable;
uniform float alpha_scissor_threshold;
uniform float point_size : hint_range(0,128);
uniform sampler2D texture_orm : hint_roughness_g, filter_linear_mipmap, repeat_enable;
uniform sampler2D texture_normal : hint_roughness_normal, filter_linear_mipmap, repeat_enable;
uniform float normal_scale : hint_range(-16,16);
uniform float ao_light_affect = 0.0;
uniform vec2 uv1_scale;
uniform vec2 uv1_offset;
uniform float wind_speed = 1.0;
uniform float wind_strength = 0.1;
uniform float wind_scale = 2.0;
float sinCombined(float pos, float time, float rand) {
	return sin(time + pos * rand) + cos(time + pos * rand * 0.894341);
}
void vertex() {
	UV = UV * uv1_scale + uv1_offset;
	float speed = TIME * wind_speed;
	vec3 pos = speed + (VERTEX.xyz + COLOR.rgb) * wind_scale;
	float vcolStr = clamp(COLOR.r + COLOR.g, 0.0, 1.0);
	VERTEX.xyz += vec3(sinCombined(pos.z, speed, 1.2), sinCombined(pos.x, speed, 1.78), sinCombined(pos.y, speed, 0.9)) * vcolStr * wind_strength / 10.0;
}
void fragment() {
	vec4 tex = texture(texture_albedo, UV);
	if (albedo.a * tex.a < alpha_scissor_threshold) { discard; }
	ALBEDO = albedo.rgb * tex.rgb;
	vec4 orm = texture(texture_orm, UV);
	ROUGHNESS = orm.g;
	METALLIC = orm.b;
	NORMAL_MAP = texture(texture_normal, UV).rgb;
	NORMAL_MAP_DEPTH = normal_scale;
	AO = orm.r;
	AO_LIGHT_AFFECT = ao_light_affect;
}
