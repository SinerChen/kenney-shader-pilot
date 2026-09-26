// Shared GPU reference-space gradient noise and spatial burn field.
int permute(int i) { return perm[i & 255]; }
vec3 gradient(int h) {
    int k = h % 12;
    if (k == 0) return vec3(1,1,0);
    if (k == 1) return vec3(-1,1,0);
    if (k == 2) return vec3(1,-1,0);
    if (k == 3) return vec3(-1,-1,0);
    if (k == 4) return vec3(1,0,1);
    if (k == 5) return vec3(-1,0,1);
    if (k == 6) return vec3(1,0,-1);
    if (k == 7) return vec3(-1,0,-1);
    if (k == 8) return vec3(0,1,1);
    if (k == 9) return vec3(0,-1,1);
    if (k == 10) return vec3(0,1,-1);
    return vec3(0,-1,-1);
}
float corner(ivec3 i, vec3 d) {
    return dot(gradient(permute(i.x + permute(i.y + permute(i.z)))), d);
}
float noise3(vec3 p) {
    ivec3 i = ivec3(floor(p));
    vec3 f = fract(p);
    vec3 u = f*f*f*(f*(f*6.0-15.0)+10.0);
    return mix(mix(mix(corner(i,f),corner(i+ivec3(1,0,0),f-vec3(1,0,0)),u.x),
                   mix(corner(i+ivec3(0,1,0),f-vec3(0,1,0)),corner(i+ivec3(1,1,0),f-vec3(1,1,0)),u.x),u.y),
               mix(mix(corner(i+ivec3(0,0,1),f-vec3(0,0,1)),corner(i+ivec3(1,0,1),f-vec3(1,0,1)),u.x),
                   mix(corner(i+ivec3(0,1,1),f-vec3(0,1,1)),corner(i+ivec3(1,1,1),f-vec3(1,1,1)),u.x),u.y),u.z);
}
float fbm3(vec3 p, float freq_arg, int oct_arg, float gain_arg, float lac_arg) {
    float sum = 0.0;
    float amp = 1.0;
    float weight = 0.0;
    float freq = freq_arg;
    for (int j=0; j<oct_arg; j++) {
        sum += amp*noise3(p*freq);
        weight += amp;
        amp *= gain_arg;
        freq *= lac_arg;
    }
    return sum / max(weight, 0.000001);
}
vec4 burn_field(vec3 p, vec3 origin_arg, float time_arg, float start_arg, float radius_arg, float speed_arg,
                float amp_arg, float freq_arg, int oct_arg, float gain_arg, float lac_arg,
                float width_arg, bool enabled_arg) {
    float n = fbm3(p, freq_arg, oct_arg, gain_arg, lac_arg);
    float radius = radius_arg + speed_arg*max(time_arg-start_arg,0.0);
    float s = length(p-origin_arg) - radius + amp_arg*n;
    float w = max(width_arg,0.000001);
    float c = 1.0-smoothstep(-w,w,s);
    float e = 1.0-smoothstep(0.0,w,abs(s));
    if (!enabled_arg || time_arg < start_arg) { c=0.0; e=0.0; }
    return vec4(n,s,c,e);
}
