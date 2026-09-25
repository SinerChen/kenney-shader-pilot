"""Build the scene catalog from actual local capture records."""
import html
import json
import re
import struct
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT.parent

DETAILS = {
    'bistro': dict(code='R01', launcher='Bistro', category='写实街区 / 室内外光照',
        description='餐馆、石板路、街灯、玻璃和大量街道道具。原项目提供日夜切换、人物行走、自由飞行与动态物体。',
        directions='适合后续设计材质粗糙度、玻璃、湿地反射、日夜变化和多光源任务。',
        controls='WASD 移动；Shift 冲刺；空格跳跃；V 切换第一/第三人称；~ 自由穿行；H 显示/隐藏面板；Esc 释放鼠标。',
        original_version='4.4', main_scene='MainScene.tscn',
        license='代码 MIT；大部分资产 CC BY 4.0；音乐 CC BY 3.0；部分音效 CC BY-NC 4.0。具体以 ATTRIBUTION 为准。',
        license_file='ATTRIBUTION',
        note='画面完成 120 帧渲染。原项目同时启用 FSR2/TAA，引擎自动关闭重复 TAA；检查退出时仍有资源释放提示。导入时 Bent_Quad.mtl 缺失，场景已正常显示。'),
    'sponza': dict(code='R02', launcher='Sponza', category='写实建筑 / 材质与间接光',
        description='拱廊、石柱、布幔与中庭。可以切换画质预设并自由移动镜头，适合观察遮挡、材质和明暗关系。',
        directions='适合后续设计 AO、间接光、接触阴影、反射与材质分离任务。',
        controls='首次进入选择画质并点击 OK；WASD 移动；空格上升、Shift 下降；右键加速；滚轮调速；Esc 设置；F10 释放鼠标。',
        original_version='4.6', main_scene='scenes/sponza.scn',
        license='代码 MIT；Crytek Sponza 资产按上游说明为 public domain；Noto Sans 字体 SIL OFL 1.1。',
        license_file='LICENSE.md',
        note='使用单线程资源导入后正常加载，运行日志无错误。首次 Collada 导入有多边形和空节点名称提示；截图关闭欢迎面板，保留默认 High 预设。'),
    'forest': dict(code='R03', launcher='Forest', category='自然环境 / 植被与大气',
        description='森林、地形、石块、草木和体积云。保留原有树木、风动材质、地表与已生成的植被分布。',
        directions='适合后续设计植被风动、地表混合、雾、云与交互扰动任务。',
        controls='按住右键转动视角；WASD 移动；Q/E 下降/上升；Shift 加速；R 恢复原始镜头；Esc 释放鼠标。自由相机不带碰撞。',
        original_version='4.0', main_scene='Main.tscn',
        license='仓库 MIT；外部模型与贴图来源见 Asset Credits.txt，保留原有署名文件。',
        license_file='Asset Credits.txt',
        note='上游没有附带 groundcover 编辑器插件。本地解除该插件引用，完整保留 15,869 个节点和 3,709 个 MultiMesh 节点，并加入自由相机。不能用缺失插件重新散布植被；旧网格格式/资源 UID 提示不影响当前画面。'),
    'tps': dict(code='R04', launcher='TPS', category='科幻工业场景 / 动态交互',
        description='官方第三人称射击演示：工业空间、角色、机器人、武器、发光体与动态光照。风格为科幻 PBR，并非现实地点扫描。',
        directions='适合后续设计命中反馈、溶解、护盾、动态阴影与多效果组合任务。',
        controls='主菜单点击 Play；WASD 移动；鼠标转动视角；空格跳跃；右键瞄准后左键射击；Esc 返回菜单；F11 全屏。',
        original_version='4.7', main_scene='main/main.tscn',
        license='代码 MIT；资产与音乐 CC BY 3.0；材质来源与作者见 LICENSE.md。',
        license_file='LICENSE.md',
        note='当前上游 master 标注 4.7；本地隐藏 4.7 专属的 Nearest 3D 缩放选项，以兼容 4.6.1。关卡完成 120 帧渲染；菜单另外检查。首次导入仍有重复动画名、旧纹理引用及空网格提示。'),
    'water': dict(code='R05', launcher='Water', category='水体与透明材质 / Shader 示例',
        description='海面及材质展示场景，包含 Gerstner 波浪、海面泡沫、岸边泡沫、折射、深度雾，以及冰与黑曜石等材质示例。海面网格包含 LOD 并跟随相机。',
        directions='适合后续设计波浪、泡沫、折射、水下过渡及相机移动时的连续性任务。',
        controls='方向键移动；鼠标转动视角；Enter 或空格捕获/释放鼠标；Tab 显示/隐藏帮助；Page Up / Page Down 调整远裁剪距离；Esc 退出。',
        original_version='4.1', main_scene='example/boujie_water_shader/water_shader_examples.tscn',
        license='MIT；Zach Bernal 与贡献者。原始水面 Shader 作者 Tom Langwaldt 等来源署名保留在插件 README 中。',
        license_file='addons/boujie_water_shader/LICENSE.md',
        note='官方 ZIP 通过 export-ignore 排除了 project.godot，已从同一官方 main 分支补齐。核心 Shader 与示例保持原样，完成 120 帧渲染且运行无错误、无警告。首次 OBJ 导入提示 mountains.mtl、subdivcube.mtl 缺失，记录保留。'),
}


def main():
    sources = json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))
    scenes = []
    for source in sources:
        sid = source['id']
        s = source | DETAILS[sid]
        output = ROOT/'verification'/sid
        s['capture'] = json.loads((output/'capture.json').read_text(encoding='utf-8'))
        s['check'] = json.loads((output/'capture-status.json').read_text(encoding='utf-8'))
        s['import_check'] = json.loads((output/'import-status.json').read_text(encoding='utf-8'))
        assert s['check']['capture_completed'] and s['check']['exit_code'] == 0, sid
        if sid == 'tps':
            s['menu_check'] = json.loads((output/'menu/capture-status.json').read_text(encoding='utf-8'))
            assert s['menu_check']['capture_completed'] and not s['menu_check']['errors'], 'TPS menu'
            s['play_check'] = json.loads((output/'play/capture-status.json').read_text(encoding='utf-8'))
            assert s['play_check']['capture_completed'] and not s['play_check']['errors'], 'TPS menu Play'
        for capture in s['capture']['captures']:
            data = (output/capture['image']).read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n'
            assert struct.unpack('>II', data[16:24]) == (960,540)
        s['screenshot'] = f'verification/{sid}/frame_120.png'
        for editor in (False, True):
            filename = ('Edit_' if editor else '') + s['launcher'] + '.cmd'
            args = ' --editor --scene "res://' + s['main_scene'] + '"' if editor else ' --windowed --resolution 1280x720'
            launcher = ('@echo off\r\nsetlocal\r\nset "APPDATA=%~dp0runtime\\AppData"\r\n'
                        'if not exist "%APPDATA%" mkdir "%APPDATA%"\r\n'
                        'start "" "%~dp0tools\\godot\\Godot_v4.6.1-stable_win64.exe" --path "%~dp0realistic\\projects\\' + sid + '"' + args + '\r\nendlocal\r\n')
            (PILOT/filename).write_text(launcher, encoding='ascii', newline='')
        scenes.append(s)
    manifest = {'title':'Godot 扩展场景库', 'engine':'4.6.1', 'updated_at':datetime.now().astimezone().isoformat(),
                'scope':'Native scene installation and inspection. No model tasks or scoring protocols created for these additional scenes.',
                'prepared_model_tasks':0, 'model_api_calls':0, 'scenes':scenes}
    (ROOT/'catalog.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    esc = html.escape
    cards = []
    for s in scenes:
        sid=s['id']
        records = {'import':s['import_check'],'render':s['check']}
        if sid == 'tps':
            records.update(menu=s['menu_check'], menu_to_gameplay=s['play_check'])
        log_detail = esc(json.dumps(records,ensure_ascii=False,indent=2))
        extra = '<p><a href="forest-dew.html">叶面露珠试作：近景、环境反射与风动对比 →</a></p><p><a href="../forest_grass_lab/index.html">草地小场景：L1 风动 → L2 固定草根 → L3 玩家压草（待审核）→</a></p>' if sid == 'forest' else ''
        cards.append(f'''<article id="{sid}" class="scene"><a href="{s['screenshot']}" target="_blank"><img src="{s['screenshot']}" alt="{esc(s['name'])} 本机实际渲染截图" loading="lazy"></a>
<div class="body"><div class="eyebrow">{s['code']} · {esc(s['category'])}</div><h2>{esc(s['name'])}</h2>
<p>{esc(s['description'])}</p><p class="muted">{esc(s['directions'])}</p>{extra}<div class="badge">已实际渲染 120 帧 · Godot 4.6.1</div>
<dl><dt>运行场景</dt><dd>在上一级项目目录双击 <code>{s['launcher']}.cmd</code></dd><dt>编辑工程</dt><dd>双击 <code>Edit_{s['launcher']}.cmd</code></dd><dt>操作</dt><dd>{esc(s['controls'])}</dd><dt>兼容情况</dt><dd>{esc(s['note'])}</dd><dt>许可</dt><dd>{esc(s['license'])}</dd></dl>
<nav><a href="{s['repository']}" target="_blank" rel="noopener">原仓库 ↗</a><a href="projects/{sid}/{s['license_file']}">许可 / 署名</a><a href="verification/{sid}/capture.json">渲染报告</a><a href="verification/{sid}/capture.log">运行日志</a><a href="verification/{sid}/frame_030.png" target="_blank">第 30 帧</a></nav>
<details><summary>展开导入与运行检查记录</summary><pre>{log_detail}</pre></details></div></article>''')
    template=(ROOT/'tools/page.template.html').read_text(encoding='utf-8')
    count = len(scenes)
    preview_count = sum(len(s['capture']['captures']) for s in scenes)
    links = ''.join(f'<a href="#{s["id"]}">{esc(s["name"])}</a>' for s in scenes)
    page = template.replace('__CARDS__','\n'.join(cards)).replace('__SCENE_COUNT__',str(count)).replace('__CAPTURE_COUNT__',str(preview_count)).replace('__SCENE_LINKS__',links)
    (ROOT/'index.html').write_text(page,encoding='utf-8')
    # Keep the original task page connected to the additional scene library.
    pilot_template = PILOT/'tools/page.template.html'
    text = pilot_template.read_text(encoding='utf-8')
    nav_link = f'<a href="realistic/index.html">扩展场景库 · {count} 个工程 ↗</a>'
    if 'href="realistic/index.html"' in text:
        text = re.sub(r'<a href="realistic/index.html">.*?</a>', nav_link, text, count=1)
    else:
        text = text.replace('<nav>', '<nav>'+nav_link, 1)
    extra_cards = ''.join(f'<a class="scene-card" href="realistic/index.html#{s["id"]}"><img src="realistic/{s["screenshot"]}" alt="{esc(s["name"])} 本机实际渲染"><span>{esc(s["name"])}<small>独立 Godot 工程 · 查看操作与兼容说明 ↗</small></span></a>' for s in scenes)
    section = f'<section class="panel section"><h2>扩展场景库 · {count} 个工程</h2><p class="small">与下方 5 个 Kenney 场景合计 {5+count} 个场景。扩展工程已实际运行，尚未编制新的三级模型任务。</p><div class="scene-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">'+extra_cards+'</div></section>'
    pattern = r'<section class="panel section"><h2>[^<]*</h2><p class="small">[^<]*</p><div class="scene-grid"[^>]*>.*?</section>(?=<div id="scene-grid")'
    if re.search(pattern, text, flags=re.S):
        text = re.sub(pattern, lambda match: section, text, count=1, flags=re.S)
    else:
        text = text.replace('<div id="scene-grid"', section+'<div id="scene-grid"', 1)
    if 'href="forest_grass_lab/index.html"' not in text:
        text = text.replace('<nav>', '<nav><a href="forest_grass_lab/index.html">Forest 草地 L1–L3 · 待审核 ↗</a>', 1)
    pilot_template.write_text(text,encoding='utf-8')
    print(f'Built catalog: {count} scenes, {count*2} launchers, {preview_count} scene captures; no model tasks.',flush=True)


if __name__ == '__main__':
    main()
