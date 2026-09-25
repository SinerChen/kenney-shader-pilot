shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;
uniform float elapsed_s = 0.0;
uniform vec2 domain_origin = vec2(0.0);
uniform vec2 domain_half_size = vec2(4.0);
uniform int wave_count = 0;
uniform vec4 wave_a_lambda_speed_steep[8];
uniform vec4 wave_direction_phase[8];
uniform bool foam_enabled = true;
uniform float foam_threshold = 1.0;
uniform float foam_grow = 1.0;
uniform float foam_decay = 1.0;
varying float wave_height;
varying float compression;

void vertex() {
    vec2 q = VERTEX.xz + domain_half_size + domain_origin;
    vec3 p = vec3(q.x - domain_half_size.x - domain_origin.x, 0.0, q.y - domain_half_size.y - domain_origin.y);
    vec3 tx = vec3(1.0, 0.0, 0.0);
    vec3 tz = vec3(0.0, 0.0, 1.0);
    for (int i = 0; i < wave_count; i++) {
        float a = wave_a_lambda_speed_steep[i].x;
        float lambda = wave_a_lambda_speed_steep[i].y;
        float speed = wave_a_lambda_speed_steep[i].z;
        float steep = wave_a_lambda_speed_steep[i].w;
        vec2 d = normalize(wave_direction_phase[i].xy);
        float k = TAU / lambda;
        float theta = k * (dot(d, q) - speed * elapsed_s) + wave_direction_phase[i].z;
        float sn = sin(theta); float cs = cos(theta); float h = steep * a;
        p += vec3(h * d.x * cs, a * sn, h * d.y * cs);
        float kas = k * a * sn; float khs = k * h * sn;
        tx += vec3(-khs*d.x*d.x, kas*d.x, -khs*d.y*d.x);
        tz += vec3(-khs*d.x*d.y, kas*d.y, -khs*d.y*d.y);
    }
    VERTEX = p;
    NORMAL = normalize(cross(tz, tx));
    wave_height = p.y;
    float j = tx.x * tz.z - tx.z * tz.x;
    compression = clamp((foam_threshold - j) * 2.2, 0.0, 1.0);
}

void fragment() {
    vec3 deep = vec3(0.015, 0.12, 0.28);
    vec3 shallow = vec3(0.04, 0.42, 0.68);
    float facing = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
    float crest = smoothstep(0.08, 0.28, wave_height);
    ALBEDO = mix(deep, shallow, 0.48 + wave_height * 0.8) + crest * vec3(0.08, 0.12, 0.14);
    ALBEDO = mix(ALBEDO, vec3(0.98, 0.98, 0.92), compression * float(foam_enabled) * 0.72);
    ALBEDO = mix(ALBEDO, vec3(0.22, 0.52, 0.72), facing * 0.45);
    METALLIC = 0.08;
    ROUGHNESS = mix(0.2, 0.08, max(crest, compression));
    SPECULAR = 0.8;
}
