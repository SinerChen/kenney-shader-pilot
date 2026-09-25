"""HTTP retry policy and durable five-minute wait, using an injected local clock."""
import unittest

import httpx

from run import read, transient
import test_runtime as runtime_tests
from test_runtime import plan_text, tool_turn


def http_error(code):
    request = httpx.Request("POST", "https://test.invalid")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError(f"HTTP {code}", request=request, response=response)


class FakeClock:
    def __init__(self):
        self.value = 1000.0
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds


class HttpRetryTests(unittest.TestCase):
    setUp = runtime_tests.RuntimeTests.setUp
    run_turns = runtime_tests.RuntimeTests.run_turns

    def test_all_status_errors_retry(self):
        for code in (301, 400, 401, 403, 404, 408, 422, 429, 500, 502, 503, 504, 599):
            with self.subTest(code=code):
                self.assertTrue(transient(http_error(code)))
        self.assertTrue(transient(httpx.ConnectError("network unavailable")))
        self.assertFalse(transient(ValueError("invalid local configuration")))

    def test_401_waits_300_seconds_then_continues_same_task(self):
        self.config["retry"]["wait_seconds"] = 300
        clock = FakeClock()
        states = []
        turns = [tool_turn("write", {"path": "effect/plan.json", "content": plan_text()}),
                 http_error(401), {"text": "done", "calls": [], "finish": "completed"}]
        result, session = self.run_turns(turns, sleeper=clock.sleep, now=clock.now, progress=states.append)
        self.assertEqual(sum(clock.sleeps), 300)
        self.assertEqual(max(clock.sleeps), 2)
        self.assertEqual((result["stop_reason"], result["requests"], session.count), ("model_finished", 3, 3))
        waiting = next(state for state in states if state["status"] == "retry_wait")
        self.assertEqual((waiting["requests"], waiting["retry_at"]), (2, 1300))
        self.assertIsNone(result["error"])
        self.assertTrue((self.out / "model_workspace/effect/plan.json").exists())
        self.assertNotIn("HTTP 401", str(session.history))

    def test_resume_keeps_retry_deadline_and_failed_attempt_count(self):
        self.config["retry"]["wait_seconds"] = 300
        clock = FakeClock()

        def interrupt(seconds):
            raise KeyboardInterrupt("simulated process interruption")

        turns = [tool_turn("write", {"path": "effect/plan.json", "content": plan_text()}), http_error(403)]
        with self.assertRaises(KeyboardInterrupt):
            self.run_turns(turns, sleeper=interrupt, now=clock.now)
        saved = read(self.out / "checkpoint.json")
        self.assertEqual((saved["phase"], saved["retry_at"], saved["counters"]["requests"]), ("ready", 1300, 2))
        clock.value = 1120
        result, session = self.run_turns([{"text": "done", "calls": [], "finish": "completed"}], sleeper=clock.sleep, now=clock.now)
        self.assertEqual(sum(clock.sleeps), 180)
        self.assertEqual((result["requests"], session.count), (3, 1))
        self.assertIsNone(read(self.out / "checkpoint.json")["retry_at"])

    def test_repeated_auth_errors_stop_at_budget_without_final_wait(self):
        self.config["retry"]["wait_seconds"] = 300
        self.config["budget_per_task"]["requests"] = 3
        clock = FakeClock()
        result, session = self.run_turns([http_error(401)] * 3, sleeper=clock.sleep, now=clock.now)
        self.assertEqual((result["stop_reason"], session.count), ("budget_exhausted", 3))
        self.assertEqual(sum(clock.sleeps), 600)
        self.assertEqual(len(session.history), 1)


if __name__ == "__main__":
    unittest.main()
