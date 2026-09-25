"""Offline checks of actual loop boundaries, inheritance and native image inputs."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

import httpx

from run import FileTools, prepare_workspace, read, run_task, save
from session import ImageStore, Session

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture-image-bytes").decode("ascii")


def plan_text():
    steps = [{"id": f"s{i}", "goal": "g", "expected": "e", "counterexample": "c",
              "status": "in_progress" if i == 1 else "pending", "observations": [],
              "summary": "", "limitations": ""} for i in range(1, 5)]
    return json.dumps({"status": "in_progress", "active_step": "s1", "steps": steps})


def call(name, arguments):
    return {"id": "call_1", "name": name, "arguments": arguments}


class FakeSession:
    def __init__(self, config, prompt, turns):
        self.history = [{"role": "user", "content": prompt["user"]}]
        self.turns = iter(turns)
        self.response = self.error_response = None
        self.key = "test-key-not-for-network"
        self.count = 0
        self.results_seen = []

    def payload(self):
        return "https://test.invalid", {}, {"input": copy.deepcopy(self.history)}

    def next(self):
        self.count += 1
        turn = next(self.turns)
        if isinstance(turn, Exception):
            raise turn
        self.response = copy.deepcopy(turn)
        self.history.append({"role": "assistant", "turn": copy.deepcopy(turn)})
        return turn

    def results(self, values):
        self.results_seen.extend(copy.deepcopy(values))
        self.history.append({"tool_results": copy.deepcopy(values)})

    def close(self):
        pass


def tool_turn(name, arguments):
    return {"calls": [call(name, arguments)], "text": "", "finish": "completed"}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "SA01_L1"
        self.out.mkdir()
        root = self.out / "model_workspace"
        for name in ("scene", "inputs", "effect", "observations"):
            (root / name).mkdir(parents=True)
        save(self.out / "input.json", {"messages": [{"role": "system", "content": "P3"},
                                                     {"role": "user", "content": "task"}], "tools": []})
        self.config = {"budget_per_task": {"requests": 80, "render_calls": 80},
                       "retry": {"wait_seconds": 0}}
        self.model = {"model": "test", "alias": "test", "api_key_env": "NONEXISTENT_TEST_CREDENTIAL"}

    def run_turns(self, turns, tool_class=FileTools, **options):
        holder = []

        def factory(config, prompt):
            session = FakeSession(config, prompt, turns)
            holder.append(session)
            return session

        result = run_task(self.out, self.model, self.config, session_factory=factory, tools_factory=tool_class, **options)
        return result, holder[0]

    def test_request_80_finishes_without_dispatching_new_tool_or_summary(self):
        turns = [tool_turn("write", {"path": "effect/plan.json", "content": plan_text()})]
        turns += [tool_turn("read", {"path": "effect/"}) for _ in range(78)]
        turns += [tool_turn("write", {"path": "effect/unexecuted.gd", "content": "unexpected"})]
        result, session = self.run_turns(turns)
        self.assertEqual((result["stop_reason"], result["requests"], session.count), ("budget_exhausted", 80, 80))
        self.assertEqual(len(session.results_seen), 79)
        self.assertFalse((self.out / "model_workspace/effect/unexecuted.gd").exists())
        self.assertNotIn("budget", json.dumps(session.history))

    def test_render_80_failure_counts_and_ends_without_next_request(self):
        self.config["budget_per_task"]["requests"] = 100

        class RenderFailure(FileTools):
            def render(self, **arguments):
                return {"ok": False, "errors": ["Shader compilation failed"], "images": []}

        turns = [tool_turn("write", {"path": "effect/plan.json", "content": plan_text()})]
        turns += [tool_turn("render", {}) for _ in range(80)]
        result, session = self.run_turns(turns, RenderFailure)
        self.assertEqual(result["stop_reason"], "budget_exhausted")
        self.assertEqual(result["render_calls"], 80)
        self.assertEqual(session.count, 81)
        self.assertEqual(session.results_seen[-1][1]["errors"], ["Shader compilation failed"])

    def test_failed_requests_count_and_do_not_reset_or_prompt(self):
        error = httpx.ConnectError("temporary connection failure")
        result, session = self.run_turns([error] * 80)
        self.assertEqual(result["stop_reason"], "budget_exhausted")
        self.assertEqual(result["requests"], 80)
        self.assertEqual(len(session.history), 1)

    def test_non_http_error_pauses_without_retry(self):
        error = ValueError("Local provider configuration is invalid")
        result, session = self.run_turns([error])
        self.assertEqual((result["stop_reason"], session.count), ("api_error", 1))

    def test_no_mandatory_render_before_normal_final(self):
        turns = [tool_turn("write", {"path": "effect/plan.json", "content": plan_text()}),
                 tool_turn("write", {"path": "effect/main.gd", "content": "extends Node\n"}),
                 {"text": "Saved implementation; no render performed.", "calls": [], "finish": "completed"}]
        result, session = self.run_turns(turns)
        self.assertEqual((result["stop_reason"], result["render_calls"], session.count), ("model_finished", 0, 3))

    def test_truncated_tool_is_not_executed(self):
        turn = tool_turn("write", {"path": "effect/plan.json", "content": plan_text()})
        turn["finish"] = "incomplete"
        result, session = self.run_turns([turn])
        self.assertEqual(result["stop_reason"], "output_truncated")
        self.assertEqual(session.results_seen, [])

    def test_resume_preserves_failed_attempt_counter_and_candidate(self):
        error = ValueError("Local provider configuration is invalid")
        self.run_turns([tool_turn("write", {"path": "effect/plan.json", "content": plan_text()}), error])
        result, session = self.run_turns([{"text": "done", "calls": [], "finish": "completed"}])
        self.assertEqual((result["requests"], session.count), (3, 1))
        self.assertTrue((self.out / "model_workspace/effect/plan.json").exists())

    def test_s1_copies_real_effect_only_and_keeps_level_environment(self):
        frozen = Path(self.temp.name) / "frozen"
        parent = Path(self.temp.name) / "parent"
        target = Path(self.temp.name) / "next"
        for name in ("scene", "inputs", "effect"):
            (frozen / name).mkdir(parents=True)
        save(frozen / "scene/environment.json", {"level": 2})
        save(frozen / ".environment.json", {"group": "SA01", "level": 2})
        save(frozen / "request.json", {"messages": []})
        (frozen / "effect/starter.gd").write_text("starter")
        (parent / "model_workspace/effect").mkdir(parents=True)
        (parent / "model_workspace/effect/main.gd").write_text("actual_candidate")
        save(parent / "model_workspace/effect/plan.json", {"status": "incomplete"})
        (parent / "model_workspace/observations").mkdir()
        (parent / "model_workspace/observations/private.txt").write_text("do not inherit")
        prepare_workspace(target, frozen, parent)
        root = target / "model_workspace"
        self.assertEqual((root / "effect/main.gd").read_text(), "actual_candidate")
        self.assertFalse((root / "effect/plan.json").exists())
        self.assertFalse((root / "effect/starter.gd").exists())
        self.assertEqual(list((root / "observations").iterdir()), [])
        self.assertEqual(read(root / "scene/environment.json"), {"level": 2})


class NativeImageTests(unittest.TestCase):
    def test_each_provider_gets_image_content_and_matching_call_id(self):
        for provider in ("openai", "anthropic", "openai_chat"):
            with self.subTest(provider=provider):
                config = {"provider": provider, "model": "test", "log_api_input": False}
                prompt = {"system": "P3", "user": "task", "images": [], "tools": []}
                session = Session(config, prompt, transport=httpx.MockTransport(lambda request: httpx.Response(500)))
                self.addCleanup(session.close)
                invocation = call("render", {})
                reply = {"ok": True, "images": [{"path": "observations/frame.png", "mime_type": "image/png", "data": PNG}]}
                session.results([(invocation, reply)])
                body = session.payload()[2]
                if provider == "openai":
                    block = body["input"][-1]
                    self.assertEqual(block["call_id"], invocation["id"])
                    self.assertEqual(block["output"][1]["type"], "input_image")
                elif provider == "anthropic":
                    block = body["messages"][-1]["content"][-1]
                    self.assertEqual(block["tool_use_id"], invocation["id"])
                    self.assertEqual(block["content"][1]["source"]["data"], PNG)
                else:
                    self.assertEqual(body["messages"][-2]["tool_call_id"], invocation["id"])
                    self.assertEqual(body["messages"][-1]["content"][0]["type"], "image_url")
                self.assertEqual(reply["images"][0]["data"], PNG)

    def test_read_image_and_checkpoint_exact_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Session({"provider": "openai", "model": "test"},
                              {"system": "P3", "user": "task", "tools": [], "images": []},
                              transport=httpx.MockTransport(lambda request: httpx.Response(500)))
            self.addCleanup(session.close)
            session.results([(call("read", {"path": "observations/frame.png"}),
                              {"ok": True, "kind": "image", "mime_type": "image/png", "data": PNG})])
            store = ImageStore(folder)
            packed = store.pack(session.history)
            self.assertNotIn(PNG, json.dumps(packed))
            self.assertEqual(store.restore(packed), session.history)
            self.assertEqual(len(list((Path(folder) / "images").glob("*.png"))), 1)


if __name__ == "__main__":
    unittest.main()
