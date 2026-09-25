shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;
uniform vec4 base_color : source_color = vec4(1.0);
uniform sampler2D base_texture : source_color, filter_linear_mipmap, repeat_enable;
uniform bool has_texture = false;
uniform float base_roughness = 1.0;
uniform float base_metallic = 0.0;
uniform float base_specular = 0.5;
uniform vec3 uv_scale = vec3(1.0);
uniform vec3 uv_offset = vec3(0.0);
uniform mat4 world_to_projector;
uniform vec3 projector_normal;
uniform vec3 ink_linear;
uniform float ink_opacity;
uniform float cos_reject;
uniform float cos_full;
uniform bool enabled = true;
void fragment() {
    vec4 base = base_color;
    if (has_texture) { base *= texture(base_texture, UV * uv_scale.xy + uv_offset.xy); }
    // Real opaque receiver depth (reverse-Z). Mixed ALBEDO is lit normally.
    vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, FRAGCOORD.z);
    #if CURRENT_RENDERER == RENDERER_COMPATIBILITY
    ndc.z = ndc.z * 2.0 - 1.0;
    #endif
    vec4 view_h = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
    vec3 world = (INV_VIEW_MATRIX * vec4(view_h.xyz / view_h.w, 1.0)).xyz;
    vec3 local = (world_to_projector * vec4(world, 1.0)).xyz;
    vec2 decal_uv = local.xy + 0.5;
    vec3 receiver_normal = FRONT_FACING ? NORMAL : -NORMAL;
    vec3 world_normal = normalize(mat3(INV_VIEW_MATRIX) * receiver_normal);
    float weight = 0.0;
    if (enabled && all(lessThanEqual(abs(local), vec3(0.5)))) {
        weight = ink_opacity * smoothstep(cos_reject, cos_full, dot(world_normal, projector_normal));
    }
    ALBEDO = mix(base.rgb, ink_linear, weight);
    ROUGHNESS = base_roughness;
    METALLIC = base_metallic;
    SPECULAR = base_specular;
}
