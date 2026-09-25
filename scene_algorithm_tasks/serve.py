"""Local results viewer; refresh derived metadata without invoking models or Godot."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from dashboard_data import publish


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining_bytes = None
        path = Path(self.translate_path(self.path))
        requested_range = self.headers.get("Range")
        if path.suffix.lower() != ".mp4" or not requested_range or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested_range.strip())
        start, end = 0, size - 1
        if match and any(match.groups()):
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), end) if last else end
            else:
                start = max(0, size - int(last))
        else:
            start = size
        if start >= size or end < start:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        source = path.open("rb")
        source.seek(start)
        self.remaining_bytes = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(self.remaining_bytes))
        self.end_headers()
        return source

    def copyfile(self, source, outputfile):
        remaining = self.remaining_bytes
        if remaining is None:
            return super().copyfile(source, outputfile)
        while remaining:
            block = source.read(min(64 * 1024, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)

    def end_headers(self):
        if not self.path.split("?", 1)[0].endswith((".png", ".jpg", ".webp", ".mp4")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    value = publish()
    if args.build_only:
        print(json.dumps(value["summary"]))
        return
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(ROOT)))
    stopped = threading.Event()

    def update():
        while not stopped.wait(10):
            try:
                publish()
            except Exception as error:
                print("Dashboard metadata refresh failed: " + str(error), flush=True)

    threading.Thread(target=update, daemon=True).start()
    print(f"Scene Algorithm Tasks: http://127.0.0.1:{args.port}/index.html", flush=True)
    try:
        server.serve_forever()
    finally:
        stopped.set()
        server.server_close()


if __name__ == "__main__":
    main()
