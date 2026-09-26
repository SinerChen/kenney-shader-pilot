import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"author"))
from main import ModelTools,L3_TASKS,validate_release
from workspace_layout import public_dir
from l3_domains import effective_weights
import numpy as np


class L3Tests(unittest.TestCase):
    def test_six_definitions_and_no_private_inputs(self):
        self.assertEqual(len(L3_TASKS),6)
        for task in L3_TASKS:
            prompt=(ROOT/"tasks"/task/"prompt.md").read_text(encoding="utf-8")
            for word in ["SH245","cases_private","author/","-G01"]:self.assertNotIn(word,prompt)
    def test_core_files_match_snapshot_or_prompt_revision(self):
        before=json.loads((ROOT/"author/v0_1_upgrade_baseline.json").read_text())
        revisions=json.loads((ROOT/"author/reports/prompt_revision.json").read_text(encoding="utf-8"))["files"]
        relocation=json.loads((ROOT/"author/reports/public_relocation.json").read_text(encoding="utf-8"))
        for path,digest in before.items():
            if path.startswith(("tasks/","starters/")):
                if path in revisions:
                    self.assertEqual(revisions[path]["before"],digest,path)
                    digest=revisions[path]["after"]
                revision=relocation["moves"].get(path,relocation["changes"].get(path))
                if revision:
                    self.assertEqual(revision["before"],digest,path)
                    digest=revision["after"]
                    path=revision.get("path",path)
                self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
    def test_c_branches_same_core(self):
        # C_S is source-blocked, but its preflight must use exactly C_R's L2 snapshot.
        rows=json.loads((ROOT/"author/reports/l3/predecessor_regression.json").read_text())
        by={r["task"]:r for r in rows}
        self.assertEqual(by["C_L3_R"]["predecessor_hashes"],by["C_L3_S"]["predecessor_hashes"])
    def test_native_permissions_and_empty_binding(self):
        for task in [x for x in L3_TASKS if x!="C_L3_S"]:
            p=ROOT/"starters"/task
            self.assertIn("UNIMPLEMENTED_BINDING",(p/"solution/adapter.gd").read_text())
            self.assertTrue((p/"Main.tscn").is_file())
            self.assertFalse((p/"fixture/base_stage.tscn").exists())
            self.assertFalse((p/"fixture/bridge.gd").exists())
            self.assertFalse((p/"author").exists())
            permissions=json.loads((public_dir(p)/"permissions.json").read_text())
            self.assertEqual(permissions["writable_paths"],["solution/","scratch/"])
    def test_source_inventory_controls_read(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/"workspace";root.mkdir();public_dir(root).mkdir(parents=True);(root/"Shaders").mkdir()
            (root/"Shaders/native.gdshader").write_text("shader_type spatial;")
            (root/"Shaders/secret.txt").write_text("unlisted")
            (public_dir(root)/"scene_files.json").write_text(json.dumps({"files":{"Shaders/native.gdshader":"hash"}}))
            tool=ModelTools(root)
            self.assertIn("spatial",tool.call("read",path="Shaders/native.gdshader")["text"])
            self.assertEqual(tool.call("read",path="Shaders")["files"],["native.gdshader"])
            with self.assertRaises(ValueError):tool.call("read",path="Shaders/secret.txt")
            with self.assertRaises(ValueError):tool.call("write",path="Shaders/native.gdshader",content="bad")
    def test_weight_partition_and_second_group(self):
        w=effective_weights([0,0,0,1],[0,0,0,0],[.5]*8)
        np.testing.assert_allclose(w,[1,0,0,0,0,0,0,0])
        w=effective_weights([.3,.2,.1,1],[.2,.4,.6,.7],[.2,.5,.4,.1,.7,.3,.6,.4])
        self.assertAlmostEqual(w.sum(),1)
        self.assertAlmostEqual(w[:4].sum(),.3)
        self.assertAlmostEqual(w[4:].sum(),.7)
    def test_unexecuted_integrations_are_not_zero_scores(self):
        for task in L3_TASKS:
            from l3 import run_integration
            r=run_integration(task)
            self.assertEqual(r["integration_total"],10)
            self.assertIsNone(r["integration_pass"])
            self.assertEqual(r["executed_groups"],0)
    def test_release_remains_closed(self):
        for task in L3_TASKS:self.assertEqual(validate_release(task)["status"],"BLOCKED_RELEASE")


if __name__=="__main__":unittest.main(verbosity=2)
