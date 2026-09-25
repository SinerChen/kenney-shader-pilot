import html
import json
import struct
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    data=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    results={}
    for scene in data['scenes']:
        sid=scene['id']
        record=json.loads((ROOT/'verification'/sid/'result.json').read_text(encoding='utf-8'))
        assert record['rendered'] and record['reset_ok'] and record['frames']==180, sid
        assert set(record['targets'])==set(scene['targets']),sid
        for sample in record['samples']:
            path=ROOT/'verification'/sid/sample['image']
            content=path.read_bytes()
            assert content[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',content[16:24])==(960,640),path
        results[sid]=record
        kit=scene['kit']
        launcher='@echo off\r\nsetlocal\r\nset "APPDATA=%~dp0runtime\\AppData"\r\n"%~dp0tools\\godot\\Godot_v4.6.1-stable_win64.exe" --path "%~dp0projects\\'+kit+'" "res://pilot/'+sid+'.tscn"\r\nendlocal\r\n'
        (ROOT/f'{sid}.cmd').write_text(launcher,encoding='ascii',newline='')
    data['verification']=results
    for task in data['tasks']:
        task['prompt']=(ROOT/'tasks'/task['id']/'prompt.md').read_text(encoding='utf-8')
    template=(ROOT/'tools/page.template.html').read_text(encoding='utf-8')
    (ROOT/'index.html').write_text(template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c')),encoding='utf-8')
    summary={'checked_at':datetime.now().astimezone().isoformat(),'scenes':len(results),'prepared_tasks':len(data['tasks']),
             'rendered_scenes':len(results),'screenshots':sum(len(r['samples']) for r in results.values()),
             'total_render_steps':sum(r['frames'] for r in results.values()),'engine':'Godot 4.6.1','renderer':'forward_plus',
             'model_tasks_run':0,'model_api_calls':0,'stage':'baseline_preparation','scope':'Imports, target names, event delivery, 180 steps, reset, and actual 960x640 GPU captures. No shader-task correctness scores.'}
    (ROOT/'verification/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__': main()
