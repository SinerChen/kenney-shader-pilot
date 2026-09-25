"""Prepare five baseline scenes and fifteen cumulative task specifications."""
import json
import re
import shutil
import certifi
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
SCENES = [
    dict(id='P01', kit='platformer', title='材质收集庭院', title_en='Material Courtyard', category='材质与表面', tags=['g2s1','g2s4','g7s1'],
         focus='同场景材质差异、收集反馈与状态联动',
         targets=['MaterialA','MaterialB','MaterialC','CollectibleA','CollectibleB','Gate'],
         events=[dict(frame=30,name='focus',payload={'target':'MaterialA'}),dict(frame=60,name='collect',payload={'target':'CollectibleA','count':1}),dict(frame=100,name='collect',payload={'target':'CollectibleB','count':2}),dict(frame=140,name='unlock',payload={'target':'Gate'})],
         levels=[
             ('单一材质效果', '为 MaterialA/B/C 分别实现可辨别的粗糙金属、哑光塑料和带虹彩边缘的材质，保留原模型结构。相机移动时高光随表面与视角变化。', ['三种材质视觉上可区分','保留纹理关联与表面朝向','移动视角后高光不固定在屏幕','其他平台和角色材质不被误改']),
             ('收集与聚焦交互', '保留 L1。focus 事件只高亮指定对象；collect 使对应收集物局部溶解消失，并更新计数。重复事件不重复计数，未指定对象保持原状。', ['保留 L1 材质差异','事件只影响指定对象','溶解连续且完成后正确隐藏','重复收集不会累计两次']),
             ('材质、门与界面组合', '保留 L1/L2。两次独立收集后，unlock 驱动 Gate 的能量材质启动，同时显示同步的进度与解锁状态；切换观察视角和 reset 后状态仍一致。', ['前两级效果继续有效','门与收集进度共享一致状态','界面和三维效果不重复叠亮','reset 恢复初始材质和计数'])]),
    dict(id='P02', kit='platformer', title='水面跳台', title_en='Water Crossing', category='自然与环境', tags=['g1s3','g3s4'],
         focus='水面运动、局部涟漪与岸边组合', targets=['Water','BridgeA','BridgeB','Obstacle'],
         events=[dict(frame=30,name='splash',payload={'position':[0,0.22,1],'strength':0.6}),dict(frame=70,name='splash',payload={'position':[-2,0.22,-1],'strength':1.0}),dict(frame=110,name='rain',payload={'intensity':0.8}),dict(frame=150,name='rain',payload={'intensity':0.0})],
         levels=[
             ('基础水面', '为 Water 实现连续运动的水面法线、颜色与视角相关反射观感。保持水面边界与跳台布局，避免用整张屏幕贴图冒充水面。', ['波纹随时间变化','法线和光照关系一致','效果限制在水面范围','岸边物体保持可见且无明显穿插']),
             ('定点涟漪交互', '保留 L1。根据 splash 的世界坐标与强度生成局部扩散涟漪；多次事件可以同时存在并自然衰减，相机移动不改变波源世界位置。', ['保留 L1 基础波纹','波源对应给定世界位置','不同强度产生可观察差异','多个波源叠加且会消退']),
             ('雨、水面与岸边组合', '保留 L1/L2。rain 平滑控制雨扰动，加入岸边/障碍交界的水面过渡或泡沫，协调反射、透明度和波纹。停止雨后恢复基础水面，reset 清除残留涟漪。', ['前两级仍正确','雨强变化连续且可恢复','交界效果与真实障碍位置相符','透明与反射合成不遮盖整幅场景'])]),
    dict(id='P03', kit='platformer', title='风动草地', title_en='Wind Garden', category='几何与动态模拟', tags=['g6s1','g1s5'],
         focus='锚定顶点形变、方向控制与局部交互', targets=['GrassField','Flag','InteractionMarker'],
         events=[dict(frame=30,name='wind',payload={'direction':[1,0,0],'strength':0.6}),dict(frame=75,name='wind',payload={'direction':[0,0,-1],'strength':1.0}),dict(frame=110,name='bend',payload={'position':[0,0.55,0],'radius':2.0}),dict(frame=150,name='wind',payload={'direction':[1,0,0],'strength':0.0})],
         levels=[
             ('锚定风动形变', '让 GrassField 的草与 Flag 旗面随时间摆动。根部/固定边保持锚定，实例相位有空间变化，不通过整体平移模型制造摇摆。', ['草根和旗固定边稳定','形变连续且无整物漂移','不同实例不是完全同步','法线或明暗变化与形变相容']),
             ('风向和局部避让', '保留 L1。wind 改变世界空间风向与强度，bend 使事件位置附近植被局部弯曲并恢复。强度为零时稳定回到静止状态。', ['保留 L1 锚定','风向切换对应世界坐标','局部影响有空间范围','风停和局部影响结束后可恢复']),
             ('风场、旗面和交互组合', '保留 L1/L2。草与旗共享同一风场但允许不同响应速度；多个局部影响与全局风平滑叠加，避免突然翻转、顶点爆炸或根部脱离。', ['保留前两级','草和旗的整体风向一致','全局与局部形变能同时存在','反复切换、相机运动与 reset 后稳定'])]),
    dict(id='F01', kit='fps', title='靶场命中反馈', title_en='Reactive Target Range', category='风格化与特效', tags=['g4s4','g5s7','g7s3'],
         focus='目标描边、命中消融与遮挡一致性', targets=['TargetA','TargetB','TargetC','Cover'],
         events=[dict(frame=25,name='select',payload={'target':'TargetA'}),dict(frame=55,name='hit',payload={'target':'TargetA','amount':35,'health':0.65}),dict(frame=95,name='hit',payload={'target':'TargetB','amount':80,'health':0.2}),dict(frame=135,name='destroy',payload={'target':'TargetB'}),dict(frame=160,name='select',payload={'target':'TargetC'})],
         levels=[
             ('选中目标描边', 'select 为指定靶标增加清晰的选中描边。保持主体原材质，轮廓随物体投影移动，其他对象不产生同样描边。', ['描边贴合目标轮廓','仅选中目标受影响','保留原有主体材质','移动相机后轮廓仍对齐']),
             ('命中与消隐', '保留 L1。hit 根据目标身份和伤害触发短暂闪烁；destroy 对指定靶标执行连续溶解，结束后移除其可见表面，其他目标与背景不受影响。', ['保留选中逻辑','命中反馈局部且及时','溶解连续并完成','多目标事件不串扰']),
             ('遮挡、状态与反馈组合', '保留 L1/L2。被 Cover 遮挡部分不得错误盖在遮挡物之上；目标血量、选中轮廓、命中和销毁状态协调，HUD 同步显示目标状态，重复销毁保持幂等。', ['前两级仍有效','遵守场景遮挡关系','HUD 与目标状态一致','快速切换与重复事件不留残影'])]),
    dict(id='F02', kit='fps', title='能量走廊', title_en='Energy Corridor', category='光照与光学', tags=['g3s6','g3s7','g4s6'],
         focus='能量发光、供能切换与受遮挡的光照组合', targets=['Emitter','BeamVolume','Occluder','Panel'],
         events=[dict(frame=30,name='power',payload={'value':0.8}),dict(frame=70,name='power',payload={'value':0.2}),dict(frame=105,name='scan',payload={'enabled':True}),dict(frame=145,name='power',payload={'value':0.0}),dict(frame=170,name='scan',payload={'enabled':False})],
         levels=[
             ('基础能量材质', '为 Emitter 和 Panel 实现空间上连续的能量发光纹理，保留表面结构与明暗层次，画面不能整体过曝。', ['发光限制于指定载体','纹理具有空间连续性','基础结构仍可辨识','亮部不过度覆盖其他内容']),
             ('供能与扫描交互', '保留 L1。power 平滑控制能量强度，scan 控制沿走廊推进的扫描效果，关闭后及时退出；快速切换不产生永远残留的效果。', ['保留 L1','供能强度随输入变化','扫描有明确位置与运动','关闭和反复触发均可恢复']),
             ('光束、遮挡与合成', '保留 L1/L2。在 BeamVolume 内组合能量光束/薄雾与局部照明，Occluder 应产生可信遮挡；与发光和扫描合成时保持场景亮度层次，相机移动不把效果变成屏幕贴片。', ['前两级仍正确','光束与遮挡空间关系合理','局部照明不重复累加能量','镜头运动、断电与 reset 后无残留'])])
]


class Scene:
    def __init__(self, spec):
        self.spec, self.ext, self.sub, self.nodes = spec, [], [], []
        self.resource('Script','res://pilot/pilot.gd','host')
        self.resource('Environment','res://scenes/main-environment.tres','env')
        self.resource('PackedScene','res://objects/player.tscn','player')
        self.resource('Script',f'res://effects/{spec["id"]}/effect.gd','effect')
        self.node('Pilot','Node3D',None, f'script = ExtResource("host")\nscene_id = "{spec["id"]}"\nkit = "{spec["kit"]}"')
        self.node('Environment','WorldEnvironment','.', 'environment = ExtResource("env")')
        self.node('Sun','DirectionalLight3D','.', 'rotation_degrees = Vector3(-50, -30, 0)\nlight_energy = 1.2\nshadow_enabled = true')
        self.node('World','Node3D','.')
        self.node('Observer','Camera3D','.', 'position = Vector3(15, 13, 19)\nfov = 48.0\ncurrent = true')
        self.node('EffectAdapter','Node','.', 'script = ExtResource("effect")')
        self.node('HUD','CanvasLayer','.')
        self.node('Instructions','Label','HUD','offset_left = 20.0\noffset_top = 15.0\ntheme_override_font_sizes/font_size = 17')
        self.node('Status','Label','HUD','offset_left = 20.0\noffset_top = 575.0\ntheme_override_font_sizes/font_size = 16')
        self.node('EffectHUD','Control','HUD','layout_mode = 3\nanchors_preset = 15\nanchor_right = 1.0\nanchor_bottom = 1.0\nmouse_filter = 2')
        self.node('Crosshair','TextureRect','HUD','offset_left = 463.0\noffset_top = 303.0\noffset_right = 497.0\noffset_bottom = 337.0\nexpand_mode = 1\nmouse_filter = 2\nvisible = false')
        if spec['kit']=='platformer':
            self.resource('Script','res://scripts/view.gd','view')
            self.nodes.append('[node name="Player" parent="." node_paths=PackedStringArray("view") groups=["player"] instance=ExtResource("player")]\nposition = Vector3(0, 1.0, 5)\nview = NodePath("../View")\n')
            self.node('View','Node3D','.', 'rotation_degrees = Vector3(-25, 40, 0)\nscript = ExtResource("view")\ntarget = NodePath("../Player")', extra=' node_paths=PackedStringArray("target")')
            self.node('Camera','Camera3D','View','position = Vector3(0, 0, 10)\nfov = 40.0')
        else:
            self.nodes.append('[node name="Player" parent="." node_paths=PackedStringArray("crosshair") groups=["player"] instance=ExtResource("player")]\nposition = Vector3(0, 1.0, 5)\ncrosshair = NodePath("../HUD/Crosshair")\n')

    def resource(self, kind, path, key):
        line=f'[ext_resource type="{kind}" path="{path}" id="{key}"]'
        if line not in self.ext: self.ext.append(line)
        return key

    def node(self,name,kind,parent,properties='',extra=''):
        part=f' parent="{parent}"' if parent is not None else ''
        self.nodes.append(f'[node name="{name}" type="{kind}"{part}{extra}]\n{properties}\n')

    def model(self,name,path,pos=(0,0,0),scale=(1,1,1),target=False,parent='World'):
        key='model'+str(len(self.ext));self.resource('PackedScene','res://'+path,key)
        group=' groups=["effect_target"]' if target else ''
        self.nodes.append(f'[node name="{name}" parent="{parent}"{group} instance=ExtResource("{key}")]\nposition = Vector3{pos}\nscale = Vector3{scale}\n')

    def box(self,name,pos,size,color,target=False,collision=True,parent='World'):
        key='box'+str(len(self.sub));self.sub.extend([
            f'[sub_resource type="StandardMaterial3D" id="{key}mat"]\nalbedo_color = Color{color}\nroughness = 0.75',
            f'[sub_resource type="BoxMesh" id="{key}mesh"]\nsize = Vector3{size}\nmaterial = SubResource("{key}mat")'])
        self.node(name,'MeshInstance3D',parent,f'position = Vector3{pos}\nmesh = SubResource("{key}mesh")',extra=' groups=["effect_target"]' if target else '')
        if collision:
            self.sub.append(f'[sub_resource type="BoxShape3D" id="{key}shape"]\nsize = Vector3{size}')
            self.node('Body','StaticBody3D',parent+'/'+name)
            self.node('Collision','CollisionShape3D',parent+'/'+name+'/Body',f'shape = SubResource("{key}shape")')

    def plane(self,name,pos,size,color,target=True):
        key='plane'+str(len(self.sub));self.sub.extend([
            f'[sub_resource type="StandardMaterial3D" id="{key}mat"]\nalbedo_color = Color{color}\ncull_mode = 2\nroughness = 0.6',
            f'[sub_resource type="PlaneMesh" id="{key}mesh"]\nsize = Vector2{size}\nsubdivide_width = 64\nsubdivide_depth = 64\nmaterial = SubResource("{key}mat")'])
        self.node(name,'MeshInstance3D','World',f'position = Vector3{pos}\nmesh = SubResource("{key}mesh")',extra=' groups=["effect_target"]' if target else '')

    def text(self):
        return '[gd_scene format=3]\n\n'+'\n'.join(self.ext)+'\n\n'+'\n\n'.join(self.sub)+'\n\n'+'\n'.join(self.nodes)


def make_scene(spec):
    s=Scene(spec);sid=spec['id']
    s.box('Foundation',(0,-0.4,-1),(18,0.8,17),(0.13,0.21,0.28,1))
    if sid=='P01':
        for i,x in enumerate([-4,0,4]):
            s.model('Pedestal'+str(i),'objects/platform.tscn',(x,0,-2),(1.5,1,1.5))
            s.model('Material'+chr(65+i),'models/brick.glb',(x,0.8,-2),(2,2,2),True)
        s.model('CollectibleA','models/coin.glb',(-3,1.0,3),(2,2,2),True)
        s.model('CollectibleB','models/coin.glb',(3,1.0,3),(2,2,2),True)
        s.box('Gate',(0,2,-6),(3.0,4,0.3),(0.12,0.32,0.44,1),True)
        for x in [-2,2]: s.model('GatePillar'+str(x),'objects/platform_medium.tscn',(x,0,-6),(0.7,6,0.7))
    elif sid=='P02':
        s.plane('Water',(0,0.22,-1),(14,12),(0.10,0.44,0.60,1))
        s.model('BridgeA','objects/platform.tscn',(-3,0,-1),(1.4,2,1.8),True)
        s.model('BridgeB','objects/platform.tscn',(3,0,-1),(1.4,2,1.8),True)
        s.model('StartIsland','objects/platform_medium.tscn',(0,0,5),(1.7,1,1.7))
        s.model('EndIsland','objects/platform_grass_large_round.tscn',(0,0,-6),(1.2,1,1.2))
        s.box('Obstacle',(1,1,-2),(1,2,1),(0.6,0.48,0.28,1),True)
    elif sid=='P03':
        s.model('Garden','objects/platform_grass_large_round.tscn',(0,0,-1),(2.7,1,2.7))
        s.node('GrassField','Node3D','World',extra=' groups=["effect_target"]')
        for x in range(-4,5,2):
            for z in range(-5,4,2): s.model(f'Grass_{x+4}_{z+5}','models/grass.glb',(x,0.55,z),(2.2,2.2,2.2),parent='World/GrassField')
        s.model('FlagPole','models/flag.glb',(4,0.5,-4),(3,3,3))
        s.plane('Flag',(4,3,-4),(2.0,1.4),(0.8,0.28,0.19,1))
        s.nodes[-1]+='rotation_degrees = Vector3(90, 0, 0)\n'
        s.box('InteractionMarker',(0,0.6,0),(0.4,0.1,0.4),(0.9,0.67,0.24,1),True,False)
    else:
        for x in [-6,6]:
            for z in [-5,0,5]: s.model(f'Wall_{x}_{z}','objects/wall_high.tscn',(x,0,z),(1.3,1.5,1.6))
        for x in [-4,0,4]: s.model('Platform'+str(x),'objects/platform.tscn',(x,0,-3),(1.5,1,1.5))
        if sid=='F01':
            s.resource('Script','res://pilot/hit_target.gd','hit')
            s.sub.append('[sub_resource type="SphereShape3D" id="hitshape"]\nradius = 1.0')
            for i,x in enumerate([-4,0,4]):
                name='Target'+chr(65+i)
                s.node(name,'StaticBody3D','World',f'position = Vector3({x}, 2, -3)\nscript = ExtResource("hit")',extra=' groups=["effect_target"]')
                s.model('Model','models/enemy-flying.glb',(0,0,0),(2,2,2),parent='World/'+name)
                s.node('Collision','CollisionShape3D','World/'+name,'shape = SubResource("hitshape")')
            s.box('Cover',(2,1,0),(2,2,0.5),(0.22,0.3,0.39,1),True)
        else:
            s.box('CorridorWallLeft',(-5,1.4,-1),(0.35,2.8,14),(0.2,0.28,0.34,1))
            s.box('CorridorWallRight',(5,1.4,-1),(0.35,2.8,14),(0.2,0.28,0.34,1))
            s.box('EndWall',(0,1.8,-7.6),(10,3.6,0.35),(0.18,0.24,0.30,1))
            s.box('Emitter',(0,2,-6),(2.0,2.0,0.8),(0.1,0.5,0.68,1),True)
            s.box('BeamVolume',(0,2,-2),(2,2,7),(0.18,0.32,0.43,1),True,False)
            s.nodes[-1]+='visible = false\n'
            s.box('Occluder',(-0.8,1.5,-2),(1,3,1),(0.32,0.4,0.46,1),True)
            s.box('Panel',(3,1.6,1),(2,2.5,0.2),(0.12,0.34,0.44,1),True)
            s.model('Console','models/blaster.glb',(3,0.8,2),(2,2,2))
    return s.text()


def main():
    editor_settings=ROOT/'tools/godot/editor_data/editor_settings-4.6.tres'
    editor_settings.parent.mkdir(parents=True,exist_ok=True)
    editor_text=editor_settings.read_text(encoding='utf-8') if editor_settings.exists() else '[gd_resource type="EditorSettings" format=3]\n\n[resource]\n'
    editor_text=re.sub(r'^network/tls/editor_tls_certificates=.*\n','',editor_text,flags=re.M)
    editor_text+='network/tls/editor_tls_certificates="'+Path(certifi.where()).as_posix()+'"\n'
    editor_settings.write_text(editor_text,encoding='utf-8')
    for kit in ['platformer','fps']:
        project=ROOT/'projects'/kit
        if not project.exists(): shutil.copytree(ROOT/'upstream'/kit,project)
        (project/'pilot').mkdir(exist_ok=True)
        for name in ['pilot.gd','hit_target.gd']: shutil.copyfile(TOOLS/name,project/'pilot'/name)
        shutil.copyfile(certifi.where(), project/'pilot/cacert.pem')
        project_file=project/'project.godot'
        text=project_file.read_text(encoding='utf-8')
        text=re.sub(r'config/name="[^"]+"',f'config/name="Kenney Shader Pilot - {kit}"',text)
        first='P01' if kit=='platformer' else 'F01'
        text=re.sub(r'run/main_scene="[^"]+"',f'run/main_scene="res://pilot/{first}.tscn"',text)
        text=text.replace('viewport_width=1280','viewport_width=960').replace('viewport_height=720','viewport_height=640')
        text=re.sub(r'^movie_writer/.*\n','',text,flags=re.M)
        if '[network]' not in text:
            text+='\n[network]\ntls/certificate_bundle_override="res://pilot/cacert.pem"\n'
        project_file.write_text(text,encoding='utf-8')
        player_scene=project/'objects/player.tscn'
        player_text=player_scene.read_text(encoding='utf-8')
        # Inspection/replay starts with the controller disabled. Start footsteps
        # only when TAB activates play, rather than auto-playing during capture.
        player_scene.write_text(player_text.replace('autoplay = true','autoplay = false'),encoding='utf-8')
        if kit=='platformer':
            brick_import=project/'models/brick.glb.import'
            brick_import.write_text(brick_import.read_text(encoding='utf-8').replace('materials/extract=1','materials/extract=0'),encoding='utf-8')
    scene_map={}
    tasks=[]
    for spec in SCENES:
        sid=spec['id'];project=ROOT/'projects'/spec['kit']
        scene_map[sid]={k:v for k,v in spec.items() if k!='levels'}
        scene_map[sid]['event_names']=list(dict.fromkeys(e['name'] for e in spec['events']))
        (project/'pilot'/f'{sid}.tscn').write_text(make_scene(spec),encoding='utf-8')
        effects=project/'effects'/sid;effects.mkdir(parents=True,exist_ok=True)
        if not (effects/'effect.gd').exists(): shutil.copyfile(TOOLS/'effect_adapter.gd',effects/'effect.gd')
        for level,(title,requirement,criteria) in enumerate(spec['levels'],1):
            task=dict(id=f'{sid}_L{level}',scene_id=sid,kit=spec['kit'],level=level,title=title,requirement=requirement,
                      criteria=criteria,parent_task=f'{sid}_L{level-1}' if level>1 else None,
                      base_scene=f'projects/{spec["kit"]}/pilot/{sid}.tscn',editable_directory=f'projects/{spec["kit"]}/effects/{sid}',
                      status='prepared_not_run',carry_forward='previous_model_submission' if level>1 else 'clean_baseline')
            tasks.append(task)
            folder=ROOT/'tasks'/task['id'];folder.mkdir(parents=True,exist_ok=True)
            (folder/'task.json').write_text(json.dumps(task,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            prompt=f'# {task["id"]} · {spec["title"]} · {title}\n\n{requirement}\n\n'
            prompt+='本任务使用固定的 Godot 4.6.1 / Forward+ 场景。先阅读 HOST_API.md 和本题 task.json。只修改分配的 effects/'+sid+'/ 目录，可增加该目录下的 shader 和辅助脚本；保留场景几何、资产、相机、事件协议及测试脚本。\n\n'
            prompt+=('从无目标效果的基线开始。' if level==1 else '在同一模型上一等级提交的文件上继续开发，保留前序要求；不得以参考答案替换上一等级结果。')+'\n\n验收要点：\n'+''.join('- '+c+'\n' for c in criteria)
            prompt+='\nsetup(context)、reset(state)、step(dt,state)、on_event(name,payload,state) 是统一入口。效果时间使用 state.elapsed，不依赖机器墙钟；事件目标名称与坐标以场景合同为准。输出修改后的完整文件，不输出仅说明实现意图的伪代码。\n'
            (folder/'prompt.md').write_text(prompt,encoding='utf-8')
    for kit in ['platformer','fps']:
        (ROOT/'projects'/kit/'pilot/scenes.json').write_text(json.dumps(scene_map,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest={'version':'pilot_v1','engine':'Godot 4.6.1','renderer':'forward_plus','viewport':[960,640],
              'seed':20260923,'scene_count':5,'task_count':15,'levels':3,'chains_per_scene':1,
              'planned_expansion':{'scenes':100,'chains_per_scene':3,'levels':3,'tasks':900},
              'stage':'baseline_and_task_preparation','model_api_calls':0,'scenes':list(scene_map.values()),'tasks':tasks}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared 5 scenes, 15 task prompts, 2 isolated Godot projects; no model experiments started.')


if __name__=='__main__': main()
