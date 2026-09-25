"""Reuse existing HTTP adapters and return native image content for three tools."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

PILOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("scene_existing_providers", PILOT / "forest_grass_lab/experiment/providers.py")
providers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(providers)


class Session(providers.Session):
    def results(self, values):
        """No new instructions: attach images to the actual tool result."""
        for call, result in values:
            clean = copy.deepcopy(result)
            pictures = clean.get("images", [])
            if clean.get("kind") == "image" and clean.get("data"):
                pictures = [clean]
            images = []
            for picture in pictures:
                if picture.get("data"):
                    images.append((picture.get("mime_type", "image/png"), picture.pop("data")))
                    picture.pop("encoding", None)
            text = json.dumps(clean, ensure_ascii=False)
            if self.provider == "openai":
                content = [{"type": "input_text", "text": text}]
                content.extend({"type": "input_image", "image_url": f"data:{mime};base64,{data}",
                                "detail": self.config.get("image_detail", "high")} for mime, data in images)
                self.history.append({"type": "function_call_output", "call_id": call["id"],
                                     "output": content if images else text})
            elif self.provider == "anthropic":
                content = [{"type": "text", "text": text}]
                content.extend({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}
                               for mime, data in images)
                block = {"type": "tool_result", "tool_use_id": call["id"], "content": content,
                         "is_error": not clean.get("ok", True)}
                if self.history and self.history[-1].get("role") == "user":
                    self.history[-1]["content"].append(block)
                else:
                    self.history.append({"role": "user", "content": [block]})
            elif self.provider == "openai_chat":
                self.history.append({"role": "tool", "tool_call_id": call["id"], "content": text})
                if images:
                    self.history.append({"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}
                        for mime, data in images]})
            else:
                raise ValueError("Unsupported experiment provider")


class ImageStore:
    """Deduplicate image bytes in local traces; restore exact native API payloads."""
    def __init__(self, root):
        self.root = Path(root).resolve()

    def pack(self, value):
        if isinstance(value, dict):
            return {key: self.pack(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.pack(item) for item in value]
        if not isinstance(value, str):
            return value
        prefix = ""
        raw = value
        if value.startswith("data:image/") and ";base64," in value:
            prefix, raw = value.split(",", 1)
            prefix += ","
        elif not value.startswith(("iVBORw0KGgo", "/9j/", "UklGR")):
            return value
        try:
            data = base64.b64decode(raw, validate=True)
        except ValueError:
            return value
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            suffix = ".png"
        elif data.startswith(b"\xff\xd8\xff"):
            suffix = ".jpg"
        elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            suffix = ".webp"
        else:
            return value
        digest = hashlib.sha256(data).hexdigest()
        relative = "images/" + digest + suffix
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return {"$image_file": relative, "prefix": prefix, "sha256": digest}

    def restore(self, value):
        if isinstance(value, dict):
            if set(value) == {"$image_file", "prefix", "sha256"}:
                path = (self.root / value["$image_file"]).resolve()
                if not path.is_relative_to(self.root):
                    raise ValueError("Image checkpoint leaves run directory")
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != value["sha256"]:
                    raise ValueError("Image checkpoint hash mismatch")
                return value["prefix"] + base64.b64encode(data).decode("ascii")
            return {key: self.restore(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.restore(item) for item in value]
        return value
