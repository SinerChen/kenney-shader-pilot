"""Render a self-contained local review page from task and capture records."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    data = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    check = json.loads((ROOT/'verification/capture-status.json').read_text(encoding='utf-8'))
    assert check['completed'] and not check['errors']
    for task in data['tasks']:
        task['prompt_text'] = (ROOT/task['prompt']).read_text(encoding='utf-8')
        assert (ROOT/f"verification/L{task['level']}/animation.webp").exists()
    template = (ROOT/'tools/page.template.html').read_text(encoding='utf-8')
    if data.get('api_enabled'):
        template = template.replace('REVIEW BEFORE API','TASK PREVIEW / S1 P3')
        template = template.replace('未接入 API，未运行模型实验。','已授权 S1/P3 模型实验；本页保留作者参考，模型输出见结果页。')
        template = template.replace('API：<strong>关闭</strong>，等待本轮审核','API：<strong>已授权 S1/P3</strong> · <a href="results.html">查看模型结果</a>')
        template = template.replace('<main>','<main><nav><a href="results.html">→ Astra / Sol / Claude / Kimi 实验进度与结果</a></nav>',1)
    status = f"Godot 实际渲染完成：{len(check['errors'])} 个错误，{len(check['warnings'])} 个警告。"
    text = template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c')).replace('__CHECK_STATUS__',status)
    (ROOT/'index.html').write_text(text,encoding='utf-8')
    print('Built task preview HTML with current prompts and experiment link.')

if __name__ == '__main__':
    main()
