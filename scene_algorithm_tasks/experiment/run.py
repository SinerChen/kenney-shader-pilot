"""One serial S1/P3 worker. Reviewed prompts only; host-owned hard budgets."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import httpx

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
PILOT = PACK.parent
RUNTIME = PACK / "runtime/experiment"
RUNS = PACK / "runs/s1_p3"
sys.path.insert(0, str(PACK / "tools"))
from model_io import FileTools
from model_render import ENGINE, file_lock
from session import ImageStore, Session

TERMINAL = {"model_finished", "model_incomplete", "budget_exhausted", "output_truncated"}


def stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".save-", delete=False) as stream:
        temp = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_keys(models):
    names = {model["api_key_env"] for model in models}
    source = Path(r"D:\threejs_seven_experiments\.env")
    if source.exists():
        for line in source.read_text(encoding="utf-8-sig").splitlines():
            if line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() in names:
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    missing = sorted(name for name in names if not os.environ.get(name))
    if missing:
        raise ValueError("Missing credential environment variables: " + ", ".join(missing))


def verify_review():
    from prepare_review import p3_request, validate_model_input
    manifest = read(HERE / "review/input_hashes.json")
    for relative, expected in manifest["files"].items():
        path = (PACK / relative).resolve()
        if not path.is_relative_to(PACK.resolve()) or digest(path) != expected:
            raise ValueError("Reviewed input changed: " + relative)
    config = read(HERE / "config.json")
    for task_id in config["task_order"]:
        request = read(HERE / "review" / (task_id + ".json"))
        validate_model_input(request)
        if request != p3_request(task_id):
            raise ValueError("Preview differs from current model input: " + task_id)
    assert config["scheduling"]["max_active_tasks"] == 1
    assert config["budget_per_task"]["requests"] == 80
    assert config["budget_per_task"]["render_calls"] == 80
    assert config["budget_per_task"]["expose_to_model"] is False
    return config


def copy_files(source, destination, excluded=()):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in excluded for part in relative.parts):
            continue
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Candidate snapshot cannot contain links")
        if not path.resolve().is_relative_to(source):
            raise ValueError("Candidate file leaves source directory")
        if path.is_file():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def freeze(config):
    """Record authorization separately, preserving the reviewed manifest unchanged."""
    approval_path = RUNTIME / "approval.json"
    if approval_path.exists():
        approval = read(approval_path)
        for relative, expected in approval["frozen_hashes"].items():
            if digest(RUNTIME / relative) != expected:
                raise ValueError("Frozen input changed: " + relative)
        return read(RUNTIME / "run_config.json")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for task_id in config["task_order"]:
        source = PACK / "tasks" / task_id / "model_workspace"
        target = RUNTIME / "frozen_tasks" / task_id
        for directory in ("scene", "inputs", "effect"):
            copy_files(source / directory, target / directory, (".godot", "__pycache__"))
        shutil.copy2(source / ".environment.json", target / ".environment.json")
        save(target / "request.json", read(HERE / "review" / (task_id + ".json")))
    effective = dict(config, api_enabled=True, prompt_review_approved=True,
                     runtime_ready=True, status="authorized")
    save(RUNTIME / "run_config.json", effective)
    save(RUNTIME / "queue.json", read(HERE / "queue.json"))
    hashes = {p.relative_to(RUNTIME).as_posix(): digest(p)
              for p in (RUNTIME / "frozen_tasks").rglob("*") if p.is_file()}
    hashes["run_config.json"] = digest(RUNTIME / "run_config.json")
    hashes["queue.json"] = digest(RUNTIME / "queue.json")
    save(approval_path, {"approved": True, "time": stamp(), "user_instruction": "进行实验",
                         "review_manifest_sha256": digest(HERE / "review/input_hashes.json"),
                         "frozen_hashes": hashes})
    return effective


def prepare_workspace(out, frozen, parent=None):
    root = out / "model_workspace"
    if root.exists():
        raise ValueError("Refusing to overwrite an existing task workspace")
    root.mkdir(parents=True)
    for directory in ("scene", "inputs"):
        copy_files(frozen / directory, root / directory)
    (root / "effect").mkdir()
    if parent:
        copy_files(parent / "model_workspace/effect", root / "effect", ("plan.json", ".godot", "__pycache__"))
    else:
        copy_files(frozen / "effect", root / "effect", ("plan.json",))
    shutil.copy2(frozen / ".environment.json", root / ".environment.json")
    (root / "observations").mkdir()
    copy_files(root / "effect", out / "initial_effect")
    save(out / "input.json", read(frozen / "request.json"))
    save(out / "inheritance.json", {"parent": str(parent) if parent else None,
                                    "files": {p.relative_to(root / "effect").as_posix(): digest(p)
                                              for p in (root / "effect").rglob("*") if p.is_file()}})


def transient(error):
    # User policy: every HTTP/transport error retries, including 400/401/403/404.
    return isinstance(error, httpx.HTTPError) or (
        isinstance(error, ValueError) and "stream ended without finish_reason" in str(error))


def validate_plan(arguments):
    plan = json.loads(arguments["content"])
    if not isinstance(plan, dict) or not {"status", "active_step", "steps"} <= plan.keys():
        raise ValueError("plan.json requires status, active_step and steps")
    if not isinstance(plan["steps"], list) or not 4 <= len(plan["steps"]) <= 8:
        raise ValueError("plan.json requires 4 to 8 steps")
    required = {"id", "goal", "expected", "counterexample", "status", "observations", "summary", "limitations"}
    if any(not isinstance(step, dict) or not required <= step.keys() for step in plan["steps"]):
        raise ValueError("Plan steps must contain the fields specified in the prompt")


def run_task(out, model, config, *, session_factory=Session, tools_factory=FileTools,
             progress=lambda value: None, sleeper=time.sleep, now=time.time):
    out = Path(out)
    root = out / "model_workspace"
    solution_dir = config.get("solution_dir", "effect")
    plan_name = solution_dir + "/plan.json"
    request = read(out / "input.json")
    prompt = {"system": request["messages"][0]["content"], "user": request["messages"][1]["content"],
              "tools": request["tools"], "images": []}
    session = session_factory(dict(model, log_api_input=False), prompt)
    images = ImageStore(out)
    counters = {"requests": 0, "render_calls": 0}
    phase, pending, planned = "ready", None, False
    retry_at, saved_error = None, None
    checkpoint_path = out / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = read(checkpoint_path)
        counters = checkpoint["counters"]
        retry_at = checkpoint.get("retry_at")
        saved_error = checkpoint.get("last_error")
        session.history = images.restore(checkpoint["history"])
        phase, pending, planned = checkpoint["phase"], checkpoint.get("pending"), checkpoint["planned"]
        if phase in ("request_inflight", "tool_inflight"):
            session.close()
            raise RuntimeError("Interrupted operation requires inspection before resume; counters are preserved")
    tools = tools_factory(root)
    secrets = [os.environ.get(model.get("api_key_env", ""), ""), getattr(session, "key", "")]

    def clean(value):
        text = json.dumps(images.pack(value), ensure_ascii=False)
        for secret in secrets:
            if secret:
                text = text.replace(secret, "[redacted]")
        return json.loads(text)

    def log(kind, **value):
        event = clean({"time": stamp(), "type": kind, **value})
        with (out / "trajectory.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def checkpoint():
        save(checkpoint_path, clean({"counters": counters, "phase": phase, "pending": pending,
                                     "planned": planned, "history": session.history,
                                     "retry_at": retry_at, "last_error": error_text}))

    def status(name, **extra):
        value = clean({"status": name, "updated": stamp(), "model": model["model"],
                       "alias": model.get("alias"), "task_id": out.name, **counters, **extra})
        save(out / "status.json", value)
        progress(value)

    def exhausted():
        return [key for key, count in counters.items() if count >= config["budget_per_task"][key]]

    def pause_requested():
        return bool(config.get("stop_file") and Path(config["stop_file"]).exists())

    reason, final_text, error_text = None, "", saved_error
    checkpoint()
    try:
        while True:
            if pause_requested():
                reason = "user_paused"
                break
            if exhausted():
                reason = "budget_exhausted"
                break
            if retry_at is not None:
                status("retry_wait", error=error_text, retry_at=retry_at)
                while now() < retry_at and not pause_requested():
                    sleeper(min(2, max(0, retry_at - now())))
                if pause_requested():
                    reason = "user_paused"
                    break
                retry_at = None
                checkpoint()
            if phase != "response_ready":
                counters["requests"] += 1
                phase = "request_inflight"
                checkpoint()
                status("requesting")
                log("request", request_number=counters["requests"], body=session.payload()[2])
                before = list(session.history)
                try:
                    pending = session.next()
                except Exception as error:
                    session.history = before
                    error_text = str(error)
                    log("api_error", error=error_text, response=session.error_response)
                    phase = "ready"
                    if exhausted():
                        reason = "budget_exhausted"
                        break
                    if not transient(error):
                        reason = "api_error"
                        break
                    retry_at = now() + config["retry"]["wait_seconds"]
                    checkpoint()
                    log("retry_scheduled", retry_at=retry_at, wait_seconds=config["retry"]["wait_seconds"],
                        http_status=getattr(getattr(error, "response", None), "status_code", None))
                    continue
                error_text = None
                log("response", request_number=counters["requests"], response=session.response,
                    usage=pending.get("usage", {}))
                phase = "response_ready"
                checkpoint()
            if pause_requested():
                reason = "user_paused"
                break
            calls = pending.get("calls", [])
            if pending.get("finish") in ("incomplete", "length", "max_tokens", "failed", "cancelled"):
                reason = "output_truncated"
                final_text = pending.get("text", "")
                break
            if not calls:
                final_text = pending.get("text", "")
                reason = "model_finished" if final_text.strip() else "model_incomplete"
                break
            # The last allowed HTTP request may finish, but cannot start another operation.
            if exhausted():
                reason = "budget_exhausted"
                log("unexecuted_calls", calls=calls, reason=reason)
                break
            if len(calls) != 1:
                reply = {"ok": False, "error": "At most one tool call per reply; none executed."}
                session.results([(call, reply) for call in calls])
                log("protocol", result=reply)
            else:
                call = calls[0]
                name = call["name"]
                if name == "render":
                    counters["render_calls"] += 1
                phase = "tool_inflight"
                checkpoint()
                status("rendering" if name == "render" else "executing_tool", tool=name)
                try:
                    args = call["arguments"] if isinstance(call["arguments"], dict) else json.loads(call["arguments"])
                    if not isinstance(args, dict):
                        raise ValueError("arguments must be an object")
                    plan_write = name == "write" and args.get("path", "").replace("\\", "/") == plan_name
                    if not planned and not plan_write:
                        raise ValueError("First operation must write " + plan_name + " as specified in the prompt")
                    if plan_write:
                        validate_plan(args)
                    reply = tools.call(name, args)
                    if plan_write and reply.get("ok"):
                        planned = True
                except (ValueError, TypeError, KeyError) as error:
                    reply = {"ok": False, "error": str(error)}
                log("tool", call=call, result=reply)
                session.results([(call, reply)])
                # Candidate compile errors are task feedback; missing infrastructure pauses the queue.
                infrastructure_error = any("Renderer could not start or GPU is busy:" in item
                                           for item in reply.get("errors", []))
                if infrastructure_error:
                    error_text = "Renderer infrastructure unavailable; inspect the saved tool result"
                    reason = "local_error"
            phase, pending = "ready", None
            checkpoint()
            status("running")
            if reason:
                break
    except Exception as error:
        reason, error_text = "local_error", str(error)
        log("local_error", error=error_text)
    finally:
        checkpoint()
        session.close()
    plan_path = root / plan_name
    try:
        plan = read(plan_path) if plan_path.exists() else {}
    except (OSError, ValueError):
        plan = {}
    result = clean({"finished": stamp(), "model": model["model"], "alias": model.get("alias"),
                    "task_id": out.name, "stop_reason": reason, "error": error_text,
                    **counters, "exhausted_limits": exhausted(), "final_text": final_text,
                    "model_plan_status": plan.get("status"),
                    "model_completed_steps": sum(step.get("status") == "passed" for step in plan.get("steps", []) if isinstance(step, dict)),
                    "algorithm_quality": "not_independently_evaluated",
                    "candidate_files": {p.relative_to(root / solution_dir).as_posix(): digest(p)
                                        for p in (root / solution_dir).rglob("*") if p.is_file()}})
    save(out / "result.json", result)
    if final_text:
        (out / "final.md").write_text(final_text, encoding="utf-8")
    status("finished" if reason in TERMINAL else "paused_error", stop_reason=reason, error=error_text)
    return result


def preflight():
    config = verify_review()
    load_keys(config["models"])
    assert ENGINE.is_file(), "Godot executable missing"
    environments = read(PACK / "verification/environments/validation.json")
    assert environments["checked"] == environments["passed"] == 15
    for task_id in config["task_order"]:
        root = PACK / "tasks" / task_id / "model_workspace"
        assert FileTools(root).call("read", {"path": "scene/project/project.godot", "max_lines": 1})["ok"]
    with file_lock(RUNTIME / "serial.lock", wait=False):
        with file_lock(PILOT / "forest_grass_lab/runtime/render.lock", wait=False):
            pass
    command = [sys.executable, "-B", "-X", "utf8", "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py", "-v"]
    checked = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", cwd=PILOT)
    (RUNTIME / "tests.log").write_text(checked.stdout + checked.stderr, encoding="utf-8")
    if checked.returncode or "Ran 0 tests" in checked.stderr:
        raise RuntimeError("Runtime tests failed; see runtime/experiment/tests.log")
    report = {"status": "passed", "checked": stamp(), "model_api_calls": 0,
              "reviewed_hashes": len(read(HERE / "review/input_hashes.json")["files"]),
              "environment_baselines_passed": 15, "credentials_present": True,
              "tests_passed": True, "native_image_feedback": True, "serial_lock_available": True,
              "hard_budget_termination": True}
    save(RUNTIME / "preflight.json", report)
    return config


def worker():
    config = read(RUNTIME / "run_config.json")
    load_keys(config["models"])
    freeze(config)  # Verify frozen hashes without regenerating inputs.
    queue = read(RUNTIME / "queue.json")["items"]
    models = {item["alias"]: item for item in config["models"]}
    with file_lock(RUNTIME / "serial.lock", wait=False):
        completed = 0

        def publish(current):
            value = {"updated": stamp(), "pid": os.getpid(), "serial": True,
                     "completed_tasks": completed, "total_tasks": len(queue), "current": current,
                     "status": "paused_error" if current.get("status") == "paused_error" else "running"}
            save(RUNTIME / "status.json", value)

        for item in queue:
            out = RUNS / item["model_alias"] / item["task_id"]
            if (out / "result.json").exists():
                prior = read(out / "result.json")
                if prior["stop_reason"] in TERMINAL:
                    completed += 1
                    continue
                if prior["stop_reason"] not in ("api_error", "local_error"):
                    raise ValueError("Unknown saved task outcome")
                archive = out / "resume_history" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                archive.mkdir(parents=True)
                shutil.copy2(out / "result.json", archive / "result.json")
                (out / "result.json").unlink()
            if not (out / "checkpoint.json").exists():
                out.mkdir(parents=True, exist_ok=True)
                parent = RUNS / item["parent"] if item["parent"] else None
                if parent and read(parent / "result.json")["stop_reason"] not in TERMINAL:
                    raise ValueError("Previous S1 level is not ready")
                prepare_workspace(out, RUNTIME / "frozen_tasks" / item["task_id"], parent)
            result = run_task(out, models[item["model_alias"]], config, progress=publish)
            print(json.dumps({key: result[key] for key in ("alias", "task_id", "stop_reason", "requests", "render_calls")}), flush=True)
            if result["stop_reason"] not in TERMINAL:
                return
            completed += 1
        save(RUNTIME / "status.json", {"status": "completed", "updated": stamp(), "pid": os.getpid(),
                                        "serial": True, "completed_tasks": completed, "total_tasks": len(queue)})


def launch():
    config = preflight()
    freeze(config)
    startup = None
    flags = 0
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with (RUNTIME / "worker.log").open("a", encoding="utf-8") as stream:
        process = subprocess.Popen([sys.executable, "-B", "-X", "utf8", "-u", str(HERE / "run.py"), "--worker"],
            cwd=PILOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
            startupinfo=startup, creationflags=flags, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    save(RUNTIME / "process.json", {"pid": process.pid, "launched": stamp(), "serial": True,
                                    "command": "scene_algorithm_tasks/experiment/run.py --worker"})
    print(json.dumps({"status": "launched", "pid": process.pid, "tasks": 60, "serial": True}))


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        preflight()
        print(json.dumps(read(RUNTIME / "preflight.json")))
    elif args.launch:
        launch()
    else:
        try:
            worker()
        except Exception as error:
            save(RUNTIME / "status.json", {"status": "paused_error", "updated": stamp(),
                                            "pid": os.getpid(), "error": str(error)})
            raise


if __name__ == "__main__":
    main()
