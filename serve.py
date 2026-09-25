from functools import partial
from http.server import ThreadingHTTPServer
from scene_algorithm_tasks.serve import Handler
from pathlib import Path

root = Path(__file__).resolve().parent
print('Kenney Shader Pilot: http://127.0.0.1:8770/index.html', flush=True)
ThreadingHTTPServer(('127.0.0.1', 8770), partial(Handler, directory=str(root))).serve_forever()
