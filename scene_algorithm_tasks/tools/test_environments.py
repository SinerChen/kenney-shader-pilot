"""Check original-host isolation and serial overlay replacement without Godot."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import environments
from model_io import FileTools


class ExistingHostTests(unittest.TestCase):
    def test_serial_overlay_restores_host_and_removes_previous_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            pack = base / "pack"
            source = base / "forest_grass_lab/project"
            source.mkdir(parents=True)
            (source / "host.gd").write_text("original host", encoding="utf-8")
            root = pack / "task"
            root.mkdir(parents=True)
            (root / ".environment.json").write_text('{"group":"SA01"}', encoding="utf-8")
            first, second = pack / "first", pack / "second"
            for overlay in (first, second):
                (overlay / "effect").mkdir(parents=True)
            (first / "effect/old.gd").write_text("candidate one", encoding="utf-8")
            (second / "effect/main.gd").write_text("candidate two", encoding="utf-8")
            with patch.object(environments, "PACK", pack), patch.object(environments, "WORKSPACE", base):
                runtime = environments.stage_project(root, first)
                (runtime / "host.gd").write_text("accidental write by previous candidate", encoding="utf-8")
                environments.stage_project(root, second)
            self.assertEqual((runtime / "host.gd").read_text(), "original host")
            self.assertFalse((runtime / "effect/old.gd").exists())
            self.assertEqual((runtime / "effect/main.gd").read_text(), "candidate two")
            self.assertEqual((source / "host.gd").read_text(), "original host")

    def test_original_project_mount_readonly_and_private_cache_hidden(self):
        root = environments.PACK / "tasks/SA01_L1/model_workspace"
        tools = FileTools(root)
        listing = tools.call("read", {"path": "scene"})
        self.assertIn("project", [entry["name"] for entry in listing["entries"]])
        self.assertTrue(tools.call("read", {"path": "scene/project/project.godot"})["ok"])
        for path in ("scene/project/.godot", "scene/project/../../experiment/models.json"):
            self.assertFalse(tools.call("read", {"path": path})["ok"])
        self.assertFalse(tools.call("write", {"path": "scene/project/host/grass_host.gd", "content": "bad"})["ok"])


if __name__ == "__main__":
    unittest.main()
