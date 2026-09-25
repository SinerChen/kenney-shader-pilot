shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
uniform sampler2D road_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D road_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float transition = 0.25;
uniform vec4 layer_height = vec4(0.8,0.8,0.2,0.0);
uniform vec4 layer_control = vec4(0.4,0.6,0.2,0.0);
uniform vec3 layer0_albedo : source_color = vec3(0.45,0.42,0.38);
uniform vec3 layer1_albedo : source_color = vec3(0.25,0.23,0.21);
uniform vec3 layer2_albedo : source_color = vec3(0.12,0.09,0.06);
uniform vec3 layer3_albedo : source_color = vec3(0.0);
uniform vec3 layer0_normal = vec3(0,0,1);
uniform vec3 layer1_normal = vec3(0,0,1);
uniform vec3 layer2_normal = vec3(0,0,1);
uniform vec3 layer3_normal = vec3(0,0,1);
uniform vec4 layer_roughness = vec4(0.8,0.25,0.6,0.5);
uniform vec4 layer_metallic = vec4(0.0);
uniform vec3 detail_normal = vec3(0,0,1);
uniform bool detail_enabled = true;
varying vec3 world_pos;
void vertex(){ world_pos=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz; }
vec3 safe_norm(vec3 n){ return length(n)<0.000001 ? vec3(0,0,1) : normalize(n); }
vec3 rnm(vec3 base,vec3 detail){ vec3 t=base+vec3(0,0,1); vec3 u=detail*vec3(-1,-1,1); return safe_norm(t*dot(t,u)-u*t.z); }
void fragment(){
 vec4 road=texture(road_albedo,UV); float source_height=dot(road.rgb,vec3(0.2126,0.7152,0.0722));
 float puddle=smoothstep(-0.18,0.24,sin(world_pos.x*0.31)*0.55+cos(world_pos.z*0.27)*0.45);
 float gap=smoothstep(0.48,0.18,source_height);
 // Controls are the already wetness-distributed inputs; the mask only selects the eligible road region.
 vec4 control=layer_control; control.x*=mix(1.28,0.45,puddle); control.y*=mix(0.35,1.38,puddle); control.z*=mix(0.35,1.65,gap)*(0.72+0.28*puddle);
 vec4 score=layer_height*control; float highest=max(max(score.x,score.y),max(score.z,score.w)); float width=max(transition,0.00001);
 vec4 compete=max(score-vec4(highest)+vec4(width),vec4(0)); vec4 weights=(compete+vec4(0.000001))*control; weights/=max(dot(weights,vec4(1)),0.000001);
 vec3 tint=layer0_albedo*weights.x+layer1_albedo*weights.y+layer2_albedo*weights.z+layer3_albedo*weights.w;
 ALBEDO=tint*mix(vec3(0.72),road.rgb*1.35,0.58); ROUGHNESS=dot(layer_roughness,weights); METALLIC=dot(layer_metallic,weights);
 vec3 base=safe_norm(layer0_normal*weights.x+layer1_normal*weights.y+layer2_normal*weights.z+layer3_normal*weights.w);
 vec3 detail=safe_norm(texture(road_normal,UV).rgb*2.0-1.0+detail_normal-vec3(0,0,1));
 NORMAL_MAP=detail_enabled ? rnm(base,detail) : base; NORMAL_MAP_DEPTH=0.72;
}
