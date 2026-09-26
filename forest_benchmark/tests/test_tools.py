import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("forest_tools",ROOT/"main.py")
main=importlib.util.module_from_spec(spec);spec.loader.exec_module(main)


class FileToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/"workspace"
        self.root.mkdir()
        main.public_dir(self.root).mkdir(parents=True);(self.root/"solution").mkdir()
        (main.public_dir(self.root)/"task.json").write_text("{}",encoding="utf-8")
        self.tools=main.ModelTools(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_author_directory_invisible(self):
        for path in ["../author/expected.json","author/expected.json",str(ROOT/"author/reference_cpu.py")]:
            with self.assertRaises(ValueError):self.tools.call("read",path=path)
    def test_protected_write(self):
        with self.assertRaises(ValueError):self.tools.call("write",path="public/task.json",content="bad")
        self.assertEqual((main.public_dir(self.root)/"task.json").read_text(),"{}")
    def test_host_metadata_unreadable(self):
        self.assertFalse((self.root/"public").exists())
        for path in ["public/task.json", "../public/workspace/task.json", str(main.public_dir(self.root)/"task.json")]:
            with self.assertRaises(ValueError):self.tools.call("read",path=path)
    def test_candidate_round_trip(self):
        self.tools.call("write",path="solution/example.gd",content="extends Node\n")
        self.assertEqual(self.tools.call("read",path="solution/example.gd")["text"],"extends Node")
    def test_scratch_only(self):
        self.tools.call("write",path="scratch/check.gd",content="pass")
        self.assertTrue((self.root/"scratch/check.gd").is_file())
    def test_alternate_stream_rejected(self):
        with self.assertRaises(ValueError):self.tools.call("write",path="solution/a.gd:hidden",content="bad")
    def test_budget_ends_without_revealing_count(self):
        for _ in range(80):self.tools.call("read",path="solution")
        self.assertEqual(self.tools.call("read",path="public/task.json"),{"status":"ENDED"})
        self.assertEqual(self.tools.call("write",path="solution/x",content="bad"),{"status":"ENDED"})
    def test_render_requires_worker(self):
        self.assertEqual(self.tools.call("render")["status"],"INFRA_ERROR")
    def test_free_camera_forwarded(self):
        camera={"position":[1,2,3],"look_at":[0,0,0]}
        tools=main.ModelTools(self.root,renderer=lambda root,args:{"workspace":str(root),**args})
        self.assertEqual(tools.call("render",camera=camera)["camera"],camera)
    def test_formal_pack_fails_closed(self):
        self.assertEqual(main.package_model_task("A_L1")["status"],"BLOCKED_RELEASE")
    def test_prompts_do_not_contain_private_labels(self):
        import re
        for task in main.TASKS:
            text=(ROOT/"tasks"/task/"prompt.md").read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"SH\d{3}|\bF0[1-6]\b|\b[A-E]_L[12]-[NI]\d\d\b|cases_private|预算|80\s*次",text),task)


if __name__=="__main__":unittest.main(verbosity=2)
