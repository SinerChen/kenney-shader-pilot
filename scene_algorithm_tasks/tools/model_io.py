"""Model read/write/render tools. No arbitrary shell or model API calls."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

VISIBLE = {"scene", "inputs", "observations", "effect"}
TEXT_SUFFIXES = {".gd", ".gdshader", ".glsl", ".tres", ".tscn", ".json", ".txt", ".md", ".godot", ".uid", ".csv", ".log", ".cfg"}
WRITE_SUFFIXES = {".gd", ".gdshader", ".glsl", ".tres", ".tscn", ".json", ".txt", ".md"}
IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_BYTES = 16 * 1024 * 1024


class FileTools:
    def __init__(self, experiment_root):
        self.root = Path(experiment_root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("experiment_root must be a directory")

    def _path(self, raw, write=False):
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            raise ValueError("path must be a nonempty relative string")
        normalized = raw.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if normalized.startswith("/") or ":" in normalized or ".." in parts:
            raise PermissionError("path must stay inside the current experiment")
        if any(p.endswith((" ", ".")) and p != "." for p in parts):
            raise PermissionError("ambiguous path segment")
        if write and (not parts or parts[0] != "effect"):
            raise PermissionError("write requires a path beginning with effect/")
        if not write and len(parts) >= 2 and parts[:2] == ("scene", "project"):
            from environments import visible_source_path
            return visible_source_path(self.root, Path(*parts[2:]))
        path = (self.root / normalized).resolve()
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            raise PermissionError("resolved path leaves the current experiment") from None
        if not relative.parts:
            if write:
                raise PermissionError("write requires a file inside effect/")
            return path
        if relative.parts[0] not in VISIBLE:
            raise PermissionError("path is outside the visible directories")
        if write and (relative.parts[0] != "effect" or path.suffix.lower() not in WRITE_SUFFIXES):
            raise PermissionError("write is limited to effect/ text implementation files")
        return path

    def _label(self, path):
        if path.is_relative_to(self.root):
            return path.relative_to(self.root).as_posix()
        from environments import source_project
        return "scene/project/" + path.relative_to(source_project(self.root)).as_posix()

    def read(self, path, start_line=1, max_lines=400):
        if type(start_line) is not int or start_line < 1 or type(max_lines) is not int or not 1 <= max_lines <= 1000:
            raise ValueError("invalid line range")
        target = self._path(path)
        if target.is_dir():
            entries = []
            for child in sorted(target.iterdir(), key=lambda p: p.name):
                if target == self.root and child.name not in VISIBLE:
                    continue
                try:
                    resolved = self._path(self._label(child))
                except PermissionError:
                    continue
                entries.append({"name": child.name, "kind": "directory" if resolved.is_dir() else "file"})
            if target == self.root / "scene" and (self.root / ".environment.json").exists():
                entries.append({"name": "project", "kind": "directory"})
            return {"ok": True, "kind": "directory", "entries": entries}
        if target.stat().st_size > MAX_BYTES and target.suffix.lower() not in TEXT_SUFFIXES:
            raise ValueError("file exceeds read size limit")
        suffix = target.suffix.lower()
        if suffix in IMAGES:
            return {"ok": True, "kind": "image", "mime_type": IMAGES[suffix],
                    "encoding": "base64", "data": base64.b64encode(target.read_bytes()).decode("ascii")}
        if suffix not in TEXT_SUFFIXES:
            return {"ok": True, "kind": "binary_metadata", "bytes": target.stat().st_size,
                    "message": "Binary asset is listed but not decoded by this tool."}
        lines = target.read_text(encoding="utf-8-sig").splitlines(keepends=True)
        end = min(len(lines), start_line - 1 + max_lines)
        return {"ok": True, "kind": "text", "start_line": start_line,
                "total_lines": len(lines), "next_line": end + 1 if end < len(lines) else None,
                "content": "".join(lines[start_line - 1:end])[:65536],
                "content_truncated": len("".join(lines[start_line - 1:end])) > 65536}

    def write(self, path, content):
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_BYTES:
            raise ValueError("content exceeds write size limit")
        target = self._path(path, write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = self._path(path, write=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".write-", delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(encoded)
            os.replace(temp_path, target)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        return {"ok": True, "path": target.relative_to(self.root).as_posix(),
                "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}

    def render(self, **arguments):
        from model_render import render
        return render(self.root, arguments)

    def call(self, name, arguments):
        try:
            if name not in {"read", "write", "render"}:
                raise ValueError("unknown tool; only read, write and render are available")
            if not isinstance(arguments, dict):
                raise ValueError("arguments must be an object")
            return getattr(self, name)(**arguments)
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            return {"ok": False, "error": str(error)}


def compose_request(task_directory):
    """Return provider-neutral input; do not append author/evaluator metadata."""
    directory = Path(task_directory)
    pack = directory.parents[1]
    definitions = json.loads((pack / "model_tools.json").read_text(encoding="utf-8"))
    if {t["name"] for t in definitions} != {"read", "write", "render"} or len(definitions) != 3:
        raise ValueError("model tools must be exactly read, write and render")
    return {"messages": [{"role": "user", "content": (directory / "prompt.md").read_text(encoding="utf-8")}],
            "tools": definitions}
