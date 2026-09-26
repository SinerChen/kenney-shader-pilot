shader_type spatial;
render_mode cull_disabled;
uniform int perm[256];
uniform sampler2D wood_base : source_color, filter_linear_mipmap, repeat_enable;
uniform float burn_time = 0.0;
uniform vec3 origin_ref = vec3(-0.45,-0.8,0.0);
uniform float t0 = 0.0;
uniform float R0 = 0.15;
uniform float speed = 0.3;
uniform float noise_amplitude = 0.22;
uniform float base_frequency = 3.0;
uniform int octaves = 5;
uniform float gain = 0.5;
uniform float lacunarity = 2.0;
uniform float width = 0.07;
uniform bool enabled = true;
varying vec3 reference_position;
#include "res://solution/burn_math.gdshaderinc"
void vertex() {
    reference_position = VERTEX;
}
void fragment() {
    vec3 p = reference_position;
    vec4 field = burn_field(p,origin_ref,burn_time,t0,R0,speed,noise_amplitude,base_frequency,octaves,gain,lacunarity,width,enabled);
    float warp = noise3(vec3(p.x*3.0,p.y*0.8,2.3));
    float grain_phase = p.x*125.0+warp*12.0+sin(p.y*2.5)*1.3;
    float grain = sin(grain_phase)*(1.0-smoothstep(0.6,3.0,fwidth(grain_phase)));
    float fine = noise3(vec3(p.x*45.0,p.y*5.0,5.4));
    vec3 wood = texture(wood_base,UV).rgb * (0.87+0.11*grain+0.08*fine);
    float cells = noise3(vec3(p.x*13.0,p.y*7.0,1.8));
    float aa = max(fwidth(cells),0.015);
    float cracks = smoothstep(0.025,0.055+aa,abs(cells));
    float ash = noise3(p*5.0+vec3(3.2,4.1,1.8))*0.5+0.5;
    vec3 coal = mix(vec3(0.003,0.0025,0.002),vec3(0.019,0.016,0.014),cracks);
    coal *= 0.65+0.45*ash+0.08*grain;
    float charred = smoothstep(0.0,0.85,field.z);
    ALBEDO = mix(wood,coal,charred);
    float hot = pow(field.w,2.5);
    vec3 embers = mix(vec3(1.7,0.065,0.005),vec3(4.0,1.25,0.12),hot);
    EMISSION = embers*field.w;
    ROUGHNESS = mix(0.7,0.98,charred);
    SPECULAR = mix(0.28,0.12,charred);
}
