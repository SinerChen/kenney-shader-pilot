shader_type spatial;
// A receiver-only extra pass: the original material, depth and shading stay intact.
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_burley, specular_schlick_ggx;
uniform float base_roughness = 1.0;
uniform float base_metallic = 0.0;
uniform float base_specular = 0.5;
uniform mat4 world_to_projector;
uniform vec3 projector_normal;
uniform vec3 ink_linear;
uniform float ink_opacity;
uniform float cos_reject;
uniform float cos_full;
varying vec3 geometric_world_normal;
void vertex() {
    geometric_world_normal = MODEL_NORMAL_MATRIX * NORMAL;
}
void fragment() {
    // Reconstruct the actual receiver fragment, with reverse-Z near=1 / far=0.
    vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, FRAGCOORD.z);
    #if CURRENT_RENDERER == RENDERER_COMPATIBILITY
    ndc.z = ndc.z * 2.0 - 1.0;
    #endif
    vec4 view_h = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
    vec3 world = (INV_VIEW_MATRIX * vec4(view_h.xyz / view_h.w, 1.0)).xyz;
    vec3 local = (world_to_projector * vec4(world, 1.0)).xyz;
    if (any(greaterThan(abs(local), vec3(0.5)))) { discard; }
    float cosine = dot(normalize(geometric_world_normal), projector_normal);
    float t = clamp((cosine - cos_reject) / max(cos_full - cos_reject, 0.000001), 0.0, 1.0);
    float weight = ink_opacity * t * t * (3.0 - 2.0 * t);
    if (weight <= 0.0) { discard; }
    ALBEDO = ink_linear;
    ALPHA = weight;
    ROUGHNESS = base_roughness;
    METALLIC = base_metallic;
    SPECULAR = base_specular;
}
