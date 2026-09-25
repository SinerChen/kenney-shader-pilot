"""Tests of the model boundary and prompt-only request, without Godot/API calls."""
import json
from pathlib import Path
import tempfile
import unittest

from model_io import FileTools, compose_request


class ModelBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "experiment"
        for name in ("scene", "inputs", "observations", "effect"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        (self.root / "cases.json").write_text("private evaluation", encoding="utf-8")
        (self.root / "inputs/test_input.json").write_text('{"value": 1}', encoding="utf-8")
        self.tools = FileTools(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_visible_root_and_private_files(self):
        result = self.tools.call("read", {"path": "."})
        self.assertEqual({e["name"] for e in result["entries"]}, {"scene", "inputs", "observations", "effect"})
        self.assertFalse(self.tools.call("read", {"path": "cases.json"})["ok"])
        self.assertTrue(self.tools.call("read", {"path": "inputs/test_input.json"})["ok"])

    def test_write_and_readback(self):
        content = "extends Node\n# 草地效果\n"
        self.assertTrue(self.tools.call("write", {"path": "effect/nested/main.gd", "content": content})["ok"])
        result = self.tools.call("read", {"path": "effect/nested/main.gd", "start_line": 2, "max_lines": 1})
        self.assertEqual(result["content"], "# 草地效果\n")

    def test_readonly_and_escape(self):
        for path in ("inputs/test_input.json", "scene/main.gd", "observations/log.txt",
                     "../outside.gd", "effect/../../outside.gd", "D:/outside.gd", "effect/main.gd:stream"):
            self.assertFalse(self.tools.call("write", {"path": path, "content": "wrong"})["ok"], path)
        self.assertEqual((self.root / "inputs/test_input.json").read_text(), '{"value": 1}')
        for path in ("../outside.txt", "/etc/passwd", "effect/../cases.json"):
            self.assertFalse(self.tools.call("read", {"path": path})["ok"], path)

    def test_tool_allowlist_and_argument_validation(self):
        self.assertFalse(self.tools.call("check", {})["ok"])
        self.assertFalse(self.tools.call("read", {"path": ".", "max_lines": 1001})["ok"])
        self.assertFalse(self.tools.call("write", {"path": "effect/main.gd", "content": 42})["ok"])
        self.assertFalse(self.tools.call("read", {"path": ".", "execute": True})["ok"])

    def test_symlink_escape(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("private", encoding="utf-8")
        try:
            (self.root / "effect/link").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("OS does not allow symlink creation for this account")
        self.assertFalse(self.tools.call("read", {"path": "effect/link/secret.txt"})["ok"])
        self.assertFalse(self.tools.call("write", {"path": "effect/link/secret.txt", "content": "wrong"})["ok"])
        self.assertEqual((outside / "secret.txt").read_text(), "private")

    def test_request_contains_only_prompt_and_three_tools(self):
        pack = Path(__file__).resolve().parents[1]
        task = pack / "tasks/SA01_L1"
        request = compose_request(task)
        self.assertEqual(set(request), {"messages", "tools"})
        self.assertEqual(request["messages"], [{"role": "user", "content": (task / "prompt.md").read_text(encoding="utf-8")}])
        self.assertEqual([t["name"] for t in request["tools"]], ["read", "write", "render"])
        self.assertNotIn("SH234", json.dumps(request, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
