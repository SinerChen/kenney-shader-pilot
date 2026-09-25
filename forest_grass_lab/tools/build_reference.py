"""Author-only reference shaders. Never copy these into learner inputs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIND = '''
vec2 wind_at(vec2 root, float phase) {
    float direction_length = length(wind_direction);
    vec2 direction = direction_length > 0.00001 ? wind_direction / direction_length : vec2(0.0);
    float wave = sin(elapsed * wind_speed + dot(root, vec2(0.75,0.48)) + phase);
    float ripple = sin(elapsed * wind_speed * 1.87 + root.y * 1.9 + phase * 2.0);
    return direction * wind_strength * (0.72 * wave + 0.22 * ripple);
}
'''
INTERACTION = '''
vec2 player_push(vec2 root) {
    vec2 sum = vec2(0.0);
    float strongest = 0.0;
    for (int i=0; i<32; i++) {
        vec4 sample_point = player_history[i];
        vec2 delta = root - sample_point.xy;
        float distance_to_player = length(delta);
        float footprint = 1.0 - smoothstep(0.12, interaction_radius, distance_to_player);
        float memory = exp(-sample_point.z / 0.85) * (1.0 - smoothstep(2.5,3.2,sample_point.z));
        float weight = footprint * memory * sample_point.w;
        vec2 outward = distance_to_player > 0.001 ? delta / distance_to_player : vec2(0.0,1.0);
        sum += outward * weight;
        strongest = max(strongest, weight);
    }
    return length(sum) > 0.0001 ? normalize(sum) * strongest * interaction_strength : vec2(0.0);
}
'''

def main():
    starter = (ROOT/'project/effect/grass.gdshader').read_text(encoding='utf-8')
    start = starter.index('void vertex()')
    end = starter.index('\nvoid fragment()')
    references = ROOT/'reference'
    references.mkdir(exist_ok=True)
    for level in (1,2,3):
        body = '''void vertex() {
    vec2 root = MODEL_MATRIX[3].xz;
    float h = UV2.y;
    vec2 wind = wind_at(root, INSTANCE_CUSTOM.r * 6.283185);
'''
        if level == 1:
            body += '''    // L1 establishes wind motion only. Anchoring is introduced by L2.
    VERTEX.xz += wind;
'''
        else:
            body += '''    vec2 bend = wind;
'''
            if level == 3:
                body += '''    vec2 push = player_push(root);
    bend = wind * (1.0 - 0.65 * clamp(length(push),0.0,1.0)) + push;
'''
            body += '''    float mask = h * h;
    VERTEX.xz += bend * mask;
    // Shorten vertical projection as the card bends. Every root vertex stays put.
    VERTEX.y -= h * (1.0 - inversesqrt(1.0 + dot(bend,bend) * 1.8)) * 0.55;
    NORMAL = normalize(NORMAL + vec3(-bend.x,0.0,-bend.y) * h * 0.35);
'''
        body += '}\n'
        code = starter[:start] + WIND + (INTERACTION if level == 3 else '') + body + starter[end:]
        (references/f'L{level}.gdshader').write_text(code,encoding='utf-8')
    print('Created L1/L2/L3 author references outside the learner project.')

if __name__ == '__main__':
    main()
