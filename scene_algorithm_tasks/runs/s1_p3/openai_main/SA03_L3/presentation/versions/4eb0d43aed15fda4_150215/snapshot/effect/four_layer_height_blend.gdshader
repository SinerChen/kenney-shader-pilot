shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// The material is installed only in surface slots carrying the authored
// Pavement_Cobblestone_Wet region mask. The road texture is the fixed per-point
// source used for both the stone appearance and its height variation.
uniform sampler2D road_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D road_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float transition = 0.25;
uniform vec4 layer_height = vec4(0.8, 0.8, 0.2, 0.0);
uniform vec4 layer_control = vec4(0.4, 0.6, 0.2, 0.0);
uniform vec3 layer0_albedo : source_color = vec3(0.45, 0.42, 0.38);
uniform vec3 layer1_albedo : source_color = vec3(0.25, 0.23, 0.21);
uniform vec3 layer2_albedo : source_color = vec3(0.12, 0.09, 0.06);
uniform vec3 layer3_albedo : source_color = vec3(0.0);
uniform vec3 layer0_normal = vec3(0, 0, 1);
uniform vec3 layer1_normal = vec3(0, 0, 1);
uniform vec3 layer2_normal = vec3(0, 0, 1);
uniform vec3 layer3_normal = vec3(0, 0, 1);
uniform vec4 layer_roughness = vec4(0.8, 0.25, 0.6, 0.5);
uniform vec4 layer_metallic = vec4(0.0);
uniform vec3 detail_normal = vec3(0, 0, 1);
uniform bool detail_enabled = true;

vec3 safe_norm(vec3 value) {
    return length(value) < 0.000001 ? vec3(0, 0, 1) : normalize(value);
}

vec3 rnm(vec3 base, vec3 detail) {
    vec3 t = base + vec3(0, 0, 1);
    vec3 u = detail * vec3(-1, -1, 1);
    return safe_norm(t * dot(t, u) - u * t.z);
}

void fragment() {
    vec4 road = texture(road_albedo, UV);
    float fixed_height = dot(road.rgb, vec3(0.2126, 0.7152, 0.0722));

    // Controls already include wetness distribution: never multiply by the
    // wetness scalar again. Fixed texture height only supplies per-point layer
    // height, with recesses admitting the mud/gap layer.
    vec4 point_height = layer_height;
    point_height.z *= 1.0 - fixed_height;
    vec4 score = point_height * layer_control;
    float highest = max(max(score.x, score.y), max(score.z, score.w));
    float width = max(transition, 0.00001);
    vec4 compete = max(score - vec4(highest) + vec4(width), vec4(0.0));
    vec4 weights = (compete + vec4(0.000001)) * layer_control;
    weights /= max(dot(weights, vec4(1.0)), 0.000001);

    vec3 tint = layer0_albedo * weights.x + layer1_albedo * weights.y
        + layer2_albedo * weights.z + layer3_albedo * weights.w;
    // Preserve the authored cobble map while applying the linear blend tint.
    ALBEDO = tint * mix(vec3(0.78), road.rgb * 1.28, 0.62);
    ROUGHNESS = dot(layer_roughness, weights);
    METALLIC = dot(layer_metallic, weights);

    vec3 base = safe_norm(layer0_normal * weights.x + layer1_normal * weights.y
        + layer2_normal * weights.z + layer3_normal * weights.w);
    vec3 authored_detail = texture(road_normal, UV).rgb * 2.0 - 1.0;
    vec3 detail = safe_norm(authored_detail + detail_normal - vec3(0, 0, 1));
    NORMAL_MAP = detail_enabled ? rnm(base, detail) : base;
    NORMAL_MAP_DEPTH = 0.72;
}
