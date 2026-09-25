shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform float elapsed_s = 0.0;
uniform int wave_count = 0;
uniform vec4 wave_a_lambda_speed_steep[8];
uniform vec4 wave_direction_phase[8];
uniform bool foam_enabled = true;
uniform float foam_threshold = 1.0;
uniform vec2 domain_origin = vec2(0.0);
uniform vec2 domain_length = vec2(8.0);
uniform sampler2D foam_history : filter_linear, repeat_enable;

varying float wave_height;
varying float compression;
varying float attached_foam;

void vertex() {
    mat4 inv_model = inverse(MODEL_MATRIX);
    vec3 world_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    vec2 q = world_vertex.xz;
    vec3 p = vec3(q.x, world_vertex.y, q.y);
    vec3 tx = vec3(1.0, 0.0, 0.0);
    vec3 tz = vec3(0.0, 0.0, 1.0);
    for (int i = 0; i < wave_count; i++) {
        float a = wave_a_lambda_speed_steep[i].x;
        float lambda = max(wave_a_lambda_speed_steep[i].y, 0.000001);
        float speed = wave_a_lambda_speed_steep[i].z;
        float steep = wave_a_lambda_speed_steep[i].w;
        vec2 d = normalize(wave_direction_phase[i].xy);
        float k = TAU / lambda;
        float theta = k * (dot(d, q) - speed * elapsed_s) + wave_direction_phase[i].z;
        float sn = sin(theta); float cs = cos(theta); float h = steep * a;
        p += vec3(h * d.x * cs, a * sn, h * d.y * cs);
        float kac = k * a * cs; float khs = k * h * sn;
        tx += vec3(-khs*d.x*d.x, kac*d.x, -khs*d.y*d.x);
        tz += vec3(-khs*d.x*d.y, kac*d.y, -khs*d.y*d.y);
    }
    VERTEX = (inv_model * vec4(p, 1.0)).xyz;
    vec3 world_normal = normalize(cross(tz, tx));
    NORMAL = normalize(inverse(mat3(MODEL_MATRIX)) * world_normal);
    wave_height = p.y - world_vertex.y;
    float j = tx.x * tz.z - tx.z * tz.x;
    compression = clamp((foam_threshold - j) * 2.2, 0.0, 1.0);
    vec2 foam_uv = fract((q - domain_origin) / max(domain_length, vec2(0.000001)));
    attached_foam = textureLod(foam_history, foam_uv, 0.0).r;
}

void fragment() {
    vec3 deep = vec3(0.008, 0.075, 0.20);
    vec3 shallow = vec3(0.025, 0.30, 0.55);
    float facing = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
    float crest = smoothstep(0.06, 0.22, wave_height);
    float foam = max(attached_foam, compression * 0.18) * float(foam_enabled);
    ALBEDO = mix(deep, shallow, clamp(0.42 + wave_height * 0.8, 0.0, 1.0));
    ALBEDO += crest * vec3(0.06, 0.10, 0.13);
    ALBEDO = mix(ALBEDO, vec3(0.96, 0.98, 0.91), clamp(foam * 1.8, 0.0, 0.75));
    ALBEDO = mix(ALBEDO, vec3(0.18, 0.48, 0.70), facing * 0.40);
    METALLIC = 0.08;
    ROUGHNESS = mix(0.2, 0.07, max(crest, foam));
    SPECULAR = 0.8;
}
