"""Exercise external metadata, packaging and both Godot scene hosts."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from main import ModelTools, package_model_task, audit_submission
from prompt_layout import visible_files
from workspace_layout import public_dir
from numeric_backend import GODOT, engine_run, write_json


def check():
    report=ROOT/'author/reports/public_layout'/str(time.time_ns())
    report.mkdir(parents=True)
    checked=0
    for base in [ROOT/'starters',ROOT/'exports']:
        for folder,dirs,files in os.walk(base):
            dirs[:]=[d for d in dirs if d not in {'public','.godot','scratch'}]
            if 'project.godot' not in files:continue
            dirs.clear()
            project=Path(folder)
            assert not (project/'public').exists(),project
            assert (public_dir(project)/'task.json').is_file(),project
            tool=ModelTools(project)
            for name in visible_files(project):assert tool._path(name).is_file()
            for name in ['public/task.json','../public/'+project.name+'/task.json']:
                try:tool._path(name)
                except ValueError:pass
                else:raise AssertionError(name)
            prompt=(public_dir(project)/'prompt.md').read_text(encoding='utf-8')
            assert 'public/' not in prompt,project
            checked+=1
    for path in [*ROOT.glob('*.py'),*ROOT.glob('author/*.py'),*ROOT.glob('tools/*.py')]:
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    results=[]
    for task in ['A_L1','A_L2','A_L3']:
        project=report/'workspaces'/task
        predecessor=report/'workspaces/A_L1' if task=='A_L2' else None
        packet=package_model_task(task,project,predecessor=predecessor,review=True)
        assert packet['status']=='REVIEW_ONLY',packet
        assert not (project/'public').exists()
        assert (public_dir(project)/'task.json').is_file()
        if task=='A_L2':
            assert json.loads((public_dir(project)/'task.json').read_text(encoding='utf-8'))['predecessor']['task_id']=='A_L1'
            results.append({'task':task,'package':'PASS','predecessor_metadata':'PASS'})
            print(task,'package PASS',flush=True)
            continue
        output=report/task
        output.mkdir()
        imported=subprocess.run([str(GODOT),'--headless','--editor','--path',str(project),'--import'],capture_output=True,timeout=600,creationflags=0x08000000 if os.name=='nt' else 0)
        (output/'import.log').write_bytes(imported.stdout+imported.stderr)
        assert imported.returncode==0 and b'SCRIPT ERROR' not in imported.stderr,output
        native=task.endswith('L3')
        result=engine_run(project,[],output/'runtime',timeout=240,
            script='res://fixture/native_runner.gd' if native else 'res://fixture/visual_runner.gd',
            request_data={'frames':2,'width':320,'height':180})
        if native:
            assert result['binding']['status']=='UNIMPLEMENTED_BINDING',result
            assert result['source_runtime_unchanged'] and result['detach_restored'],result
        else:
            assert result['status']=='STARTER_NOT_IMPLEMENTED',result
            assert result['protection']['status']=='PASS',result
        results.append({'task':task,'package':'PASS','clean_import':'PASS','runtime':'PASS'})
        print(task,'import and render PASS',flush=True)
    summary={'status':'PASS','workspaces_checked':checked,'checks':results,'path':str(report)}
    write_json(report/'summary.json',summary)
    write_json(ROOT/'author/reports/public_layout/latest.json',summary)
    return summary


if __name__=='__main__':print(check())
