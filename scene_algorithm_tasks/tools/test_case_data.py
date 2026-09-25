import json
from pathlib import Path
import tempfile
import unittest

from case_data import assistant_text, publish_case


class CaseDataTests(unittest.TestCase):
    def test_provider_text(self):
        self.assertEqual(assistant_text({"output": [{"type": "reasoning", "encrypted_content": "opaque", "summary": []},
                         {"type": "message", "content": [{"type": "output_text", "text": "saved"}]}]}), "saved")
        self.assertIn("write", assistant_text({"content": [{"type": "tool_use", "name": "write", "input": {"path": "effect/main.gd"}}]}))
        self.assertEqual(assistant_text({"choices": [{"message": {"content": "finished"}}]}), "finished")

    def test_snapshot_diff_write_history_and_incomplete_log(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder)
            out = pack / "runs/s1_p3/model/SA01_L2"
            (out / "initial_effect").mkdir(parents=True)
            current = out / "model_workspace/effect"
            current.mkdir(parents=True)
            (out / "initial_effect/main.gd").write_text("old\n")
            (out / "initial_effect/keep.gd").write_text("keep\n")
            (current / "main.gd").write_text("new\n")
            (current / "keep.gd").write_text("keep\n")
            (current / "extra.gd").write_text("extra\n")
            (out / "input.json").write_text(json.dumps({"messages": [{"role": "user", "content": "actual"}], "tools": []}))
            (out / "inheritance.json").write_text(json.dumps({"parent": str(pack / "SA01_L1")}))
            failed = {"type": "tool", "call": {"name": "write", "arguments": '{"path":"effect/main.gd","content":"bad"}'}, "result": {"ok": False}}
            good = {"type": "tool", "call": {"name": "write", "arguments": '{"path":"effect/main.gd","content":"new"}'}, "result": {"ok": True, "path": "effect/main.gd"}}
            partial = json.dumps({"type": "api_error", "error": "retry"})
            trace = out / "trajectory.jsonl"
            trace.write_text(json.dumps(failed) + "\n" + json.dumps(good) + "\n" + partial[:-3])
            value = publish_case(pack, "model", "SA01_L2")
            detail = json.loads((pack / value["path"]).read_text())
            self.assertTrue(detail["partial_trace"])
            self.assertEqual(detail["parent_task"], "SA01_L1")
            by_name = {f["name"]: f for f in detail["files"]}
            self.assertEqual(by_name["main.gd"]["writes"], [2])
            self.assertEqual(by_name["main.gd"]["status"], "modified")
            self.assertEqual(by_name["keep.gd"]["status"], "unchanged")
            self.assertEqual(by_name["extra.gd"]["status"], "added")
            content = json.loads((pack / by_name["main.gd"]["detail"]).read_text())
            self.assertIn("-old", content["diff"])
            self.assertIn("+new", content["diff"])
            self.assertEqual((current / "main.gd").read_text(), "new\n")
            with trace.open("a") as stream:
                stream.write(partial[-3:] + "\n")
            updated = publish_case(pack, "model", "SA01_L2")
            self.assertNotEqual(value["version"], updated["version"])
            self.assertEqual(updated["events"], 3)
            unchanged = publish_case(pack, "model", "SA01_L2")
            self.assertEqual(updated, unchanged)

    def test_queued_case_is_labeled_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder)
            frozen = pack / "runtime/experiment/frozen_tasks/SA01_L1/request.json"
            frozen.parent.mkdir(parents=True)
            frozen.write_text('{"messages":[],"tools":[]}')
            value = publish_case(pack, "waiting_model", "SA01_L1")
            detail = json.loads((pack / value["path"]).read_text())
            self.assertEqual(detail["input_source"], "frozen_preview")
            self.assertEqual(detail["events"], [])
            self.assertEqual(detail["files"], [])


if __name__ == "__main__":
    unittest.main()
