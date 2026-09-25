shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform sampler2D stone_color : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone_height : filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 uv_scale = vec3(1.0);
uniform vec3 uv_offset = vec3(0.0);
uniform vec4 layer_height;
uniform vec4 layer_control;
uniform vec4 layer_roughness;
uniform vec4 layer_metallic;
uniform vec3 layer_color[4];
uniform vec3 layer_normal[4];
uniform float transition = 0.25;
uniform bool detail_enabled = false;
uniform vec3 detail_normal = vec3(0.0, 0.0, 1.0);
uniform float normal_strength = 1.0;
uniform float original_roughness = 0.73;
uniform float original_metallic = 0.0;

vec3 unit_normal(vec3 n) {
	return dot(n,n) > 1e-12 ? normalize(n) : vec3(0.0,0.0,1.0);
}
vec3 rnm(vec3 base, vec3 detail) {
	vec3 t = base + vec3(0.0,0.0,1.0);
	vec3 u = detail * vec3(-1.0,-1.0,1.0);
	if (t.z < 1e-6) { return unit_normal(vec3(detail.x,-detail.y,-detail.z)); }
	return unit_normal(t * dot(t,u) / t.z - u);
}
vec4 competition(vec4 h, vec4 c) {
	vec4 score = h * c;
	float peak = max(max(score.x,score.y),max(score.z,score.w));
	vec4 raw = (max(score - vec4(peak) + vec4(max(transition,1e-5)),vec4(0.0)) + vec4(1e-6)) * c;
	return raw / max(dot(raw,vec4(1.0)),1e-6);
}
void fragment() {
	vec2 uv = UV * uv_scale.xy + uv_offset.xy;
	float h = texture(stone_height,uv).r;
	// The original material domain gates the whole surface, including well surrounds.
	// Native relief protects high dry crowns; no world-space stripe or camera mask.
	float wet_region = 1.0 - smoothstep(0.48,0.68,h);
	vec4 heights = layer_height * vec4(h,h,1.0-h,1.0);
	// Controls already contain wetness. Transfer excluded wet control to dry stone.
	vec4 controls = layer_control * vec4(1.0,wet_region,1.0-h,1.0);
	controls.x += layer_control.y * (1.0-wet_region);
	vec4 w = competition(heights,controls);
	vec3 tex_color = texture(stone_color,uv).rgb;
	// Reconstruct positive Z for RGTC normal imports.
	vec2 xy = texture(stone_normal,uv).rg * 2.0 - 1.0;
	vec3 stone_n = unit_normal(vec3(xy * normal_strength,sqrt(max(1.0-dot(xy,xy),0.0))));
	float ridge = smoothstep(0.12,0.5,length(stone_n.xy));
	vec3 color = vec3(0.0);
	vec3 n = vec3(0.0);
	for (int i=0; i<4; i++) {
		color += w[i] * layer_color[i] * tex_color / vec3(0.45,0.42,0.38);
		float strength = 1.0;
		if (i == 1) { strength = mix(0.75,1.0,ridge); }
		if (i == 2) { strength = mix(0.4,1.0,ridge); }
		vec3 relief = unit_normal(vec3(stone_n.xy * strength,stone_n.z));
		n += w[i] * rnm(relief,unit_normal(layer_normal[i]));
	}
	vec3 base = unit_normal(n);
	vec3 final_n = base;
	if (detail_enabled) { final_n = rnm(base,unit_normal(detail_normal)); }
	// At protected crowns all original PBR channels, not merely normal relief, return.
	ALBEDO = mix(tex_color,color,wet_region);
	ROUGHNESS = mix(original_roughness,dot(w,layer_roughness),wet_region);
	METALLIC = mix(original_metallic,dot(w,layer_metallic),wet_region);
	NORMAL_MAP = unit_normal(mix(stone_n,final_n,wet_region)) * 0.5 + 0.5;
	NORMAL_MAP_DEPTH = 1.0;
}
