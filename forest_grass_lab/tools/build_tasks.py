"""Prepare three progressive task specifications; no experiment scheduling."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = [
    dict(level=1,title='让草随风动',adds='平滑风动、方向与强度控制、草丛相位差',
         criteria=['草网格产生连续可见的运动，相机和地面不跟着移动','风向、幅度、速度响应对应输入','相邻草丛有变化，不是整块场地机械同步平移','风强归零时静止；暂停和重置有效'],
         not_required=['根部固定','玩家交互']),
    dict(level=2,title='根部固定，顶部随风摆动',adds='固定草根、沿高度弯曲、保留 L1 风动',
         criteria=['继承 L1 的风动与参数响应','草根不滑动、不浮起、不沉入地面','顶部可见摆动，中段过渡连续，不整体平移','强风和不同风向下根部仍固定；风强归零恢复'],
         not_required=['玩家交互']),
    dict(level=3,title='玩家经过后向外倒伏并恢复',adds='局部交互、路径两侧向外、短时记忆与恢复',
         criteria=['保留 L2 根部固定与风动','路径两侧的草朝各自外侧弯倒','影响只在玩家和近期轨迹附近，远处草不受交互影响','离开后保留短暂痕迹，约 1–3 秒恢复','停留、再次经过、反向经过连续稳定','无风时交互仍有效，reset 后无残留'],
         not_required=['刚体物理模拟','草叶断裂或永久折断']),
]

def main():
    tasks = []
    for item in LEVELS:
        level = item['level']
        tid = f'FG01_L{level}'
        common = [
            {'id':'wind_default','camera':'overview','seconds':4,'parameters':{'wind_strength':0.22,'wind_speed':1.6,'wind_direction':[1,0.35]}},
            {'id':'wind_off','camera':'roots','seconds':2,'parameters':{'wind_strength':0}},
            {'id':'strong_crosswind','camera':'roots','seconds':4,'parameters':{'wind_strength':0.4,'wind_direction':[-0.3,1]}}
        ]
        if level == 3:
            common += [
                {'id':'player_pass_recover','camera':'top','seconds':11,'replay':'x=-4 to 4, z=0; wait outside after 6.5s'},
                {'id':'player_without_wind','camera':'top','seconds':11,'parameters':{'wind_strength':0},'replay':'same path'},
                {'id':'reverse_and_pause','camera':'top','seconds':12,'events':[{'time':0,'player_position':[-2,0,0.7]},{'time':3,'player_position':[2,0,0.7]},{'time':5,'player_position':[2,0,0.7]},{'time':8,'player_position':[-2,0,0.7]},{'time':9,'player_position':[-4,0,0.7]}], 'interpolation':'linear between movement endpoints; 3–5s stationary'}
            ]
        task = item | {'id':tid,'scene_id':'FG01','status':'authorized_s1_p3','api_enabled':True,
                       'parent_task':f'FG01_L{level-1}' if level > 1 else None,
                       'input_code':'static starter' if level == 1 else 'same model previous level submission; may repair failures',
                       'editable_files':['project/effect/grass.gdshader'],
                       'fixed_scene':f'project/scenes/L{level}.tscn',
                       'prompt':f'tasks/{tid}/prompt.md','host_contract':'HOST_API.md',
                       'public_cases':common,'step_seconds':1/60,
                       'evaluation_status':'observable criteria prepared; full automatic scoring not implemented',
                       'disallowed_model_inputs':['reference/','tools/build_reference.py'],
                       'reference_media_policy':'S1 P3: candidate PNG feedback only; no author reference input'}
        (ROOT/'tasks'/tid/'task.json').write_text(json.dumps(task,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        tasks.append(task)
    manifest = {'id':'FG01','title':'Forest 草地递进题','status':'authorized_s1_p3','api_enabled':True,
                'run_status':'runs/s1_p3/<model>/L<level>/status.json','base_micro_scenes':1,'level_entries':3,'engine':'Godot 4.6.1 / Forward+',
                'clarification':'L2 已由用户确认：根部固定，顶部随风摆动。',
                'project':'project/','starter':'project/effect/grass.gdshader','reference':'reference/',
                'chain_policy':'L1 -> L2 -> L3 carries each model own prior code; never inject author reference',
                'tasks':tasks}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared 3 user-authorized S1 P3 task definitions.')

if __name__ == '__main__':
    main()
