"""Prepare the exact provider-neutral P3 inputs and serial queue. No API imports."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
sys.path.insert(0, str(PACK / "tools"))
from model_io import compose_request

MODEL_ORDER = ["openai_astra", "openai_main", "claude_main", "kimi_retry_128k"]
MODEL_FIELDS = {"provider", "model", "api_key_env", "base_url", "max_output_tokens",
                "timeout_seconds", "transport_retries", "parameters", "responses_replay",
                "supports_images", "image_detail", "max_tokens_field", "parallel_tool_calls", "stream"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def p3_request(task_id):
    if not re.fullmatch(r"SA0[1-5]_L[1-3]", task_id):
        raise ValueError("Unknown task")
    request = compose_request(PACK / "tasks" / task_id)
    request["messages"].insert(0, {"role": "system", "content": (HERE / "P3.md").read_text(encoding="utf-8")})
    return request


def validate_model_input(request):
    assert [message["role"] for message in request["messages"]] == ["system", "user"]
    assert [tool["name"] for tool in request["tools"]] == ["read", "write", "render"]
    text = json.dumps(request, ensure_ascii=False)
    assert not re.search(r"\b(?:SH\d{3}|[A-LP]\d{2}|SA\d{2}(?:_L[123])?)\b", text)
    assert not any(s in text for s in ("公开验收", "cases.json", "INTERFACE.md", "rubric", "set_plan", "finish_step", "submit("))
    assert not re.search(r"预算|budget|render_calls|请求上限|剩余次数", text, re.IGNORECASE)


def main():
    source = PACK.parent / "forest_grass_lab/experiment/models.json"
    previous = read_json(source)
    models = []
    for alias in MODEL_ORDER:
        original = previous[alias]
        assert not set(original) - MODEL_FIELDS, "Unexpected source model fields; review before copying"
        config = {key: value for key, value in original.items() if key in MODEL_FIELDS}
        config["transport_retries"] = 0
        models.append({"alias": alias, **config})
    config = {
        "experiment": "scene_algorithm_tasks_s1_p3_three_tools_v1",
        "status": "awaiting_user_prompt_review", "api_enabled": False, "model_api_calls": 0,
        "prompt_review_approved": False, "mode": "S1", "variant": "P3",
        "p3_implementation": "plan_json_via_read_write_render",
        "model_order": MODEL_ORDER, "models": models,
        "task_order": [f"SA{group:02}_L{level}" for group in range(1, 6) for level in range(1, 4)],
        "scheduling": {"strategy": "model_then_group_then_level", "max_active_tasks": 1,
                       "max_inflight_model_requests": 1, "max_inflight_renders": 1,
                       "advance_during_retry": False},
        "budget_per_task": {"requests": 80, "render_calls": 80, "failed_attempts_count": True,
                            "auto_increase": False, "expose_to_model": False},
        "budget_exhaustion": {"action": "end_current_task", "trigger": "any_limit_reached",
                              "finish_inflight_operation": True, "allow_new_operations": False,
                              "preserve_candidate_and_observations": True,
                              "host_status": "budget_exhausted",
                              "notify_model": False, "request_final_response": False,
                              "continue_serial_queue": True},
        "retry": {"wait_seconds": 300, "preserve_history_and_candidate": True,
                  "http_status_errors": "retry_all", "transport_errors": "retry",
                  "non_http_config_environment_errors": "pause_queue"},
        "inheritance": {"same_model_and_group_only": True, "files": "effect/",
                        "exclude": ["plan.json"], "fresh_conversation_per_level": True,
                        "inherit_observations": False, "inherit_scores": False,
                        "on_budget_stop": "inherit_actual_candidate_with_incomplete_status"},
        "model_input": {"system": "experiment/P3.md", "user": "tasks/<task_id>/prompt.md",
                        "tools": "model_tools.json", "automatic_attachments": []},
        "run_directory": "runs/s1_p3/<alias>/<task_id>/model_workspace/",
        "source_models": str(source.relative_to(PACK.parent)).replace("\\", "/"),
        "runtime_ready": False,
        "environment_policy": "existing_hosts_L1_subset_L2_as_needed_L3_full",
        "environment_ready": True,
        "required_before_launch": ["user_prompt_review",
            "three_tool_p3_state_machine", "host_budget_termination", "provider_image_feedback",
            "local_runtime_preflight", "reviewed_input_hash_check"]}
    save(HERE / "config.json", config)

    review = HERE / "review"
    review.mkdir(exist_ok=True)
    entries, hashes, readiness = [], {}, []
    system_file = HERE / "P3.md"
    hashes["experiment/P3.md"] = digest(system_file)
    hashes["model_tools.json"] = digest(PACK / "model_tools.json")
    for task_id in config["task_order"]:
        request = p3_request(task_id)
        validate_model_input(request)
        task = read_json(PACK / "tasks" / task_id / "task.json")
        prompt_path = PACK / "tasks" / task_id / "prompt.md"
        hashes[prompt_path.relative_to(PACK).as_posix()] = digest(prompt_path)
        fixed_path = PACK / task["model_input"]["fixed_input"]
        hashes[fixed_path.relative_to(PACK).as_posix()] = digest(fixed_path)
        for name in ("main.tscn", "environment.json", "environment_setup.gd"):
            env_path = PACK / task["model_input"]["workspace"] / "scene" / name
            hashes[env_path.relative_to(PACK).as_posix()] = digest(env_path)
        save(review / f"{task_id}.json", request)
        content = f"# {task_id} · 本次 P3 输入审阅\n\n"
        content += "本页标题和分隔说明仅供人工审阅，不属于模型消息。四个模型使用相同系统文本、题面和工具定义。初始图像附件为空。\n\n"
        content += "## system（完整文本）\n\n" + request["messages"][0]["content"] + "\n\n"
        content += "## user（完整文本）\n\n" + request["messages"][1]["content"] + "\n\n"
        content += "## tools（完整定义）\n\n```json\n" + json.dumps(request["tools"], ensure_ascii=False, indent=2) + "\n```\n"
        (review / f"{task_id}.md").write_text(content, encoding="utf-8")
        entries.append(f"| {task_id} | {task['title']} | [完整文本]({task_id}.md) · [请求 JSON]({task_id}.json) |")
        readiness.append({"task_id": task_id, "runtime_ready": task["runtime_ready"],
                          "environment_ready": task.get("environment_ready", False),
                          "scene_entry_exists": (PACK / task["model_input"]["workspace"] / "scene/main.tscn").is_file()})
    index = "# P3 输入审阅索引\n\n[共用系统 prompt](../P3.md) · [实验说明](../README.md)\n\n"
    index += "以下 15 份输入适用于配置中的全部四个模型。S1 的前级候选通过每题独立的 effect/ 提供，当前预览不伪造尚未产生的候选。\n\n"
    index += "| 题目 | 内容 | 审阅材料 |\n|---|---|---|\n" + "\n".join(entries) + "\n"
    (review / "INDEX.md").write_text(index, encoding="utf-8")

    queue = []
    for model in models:
        for task_id in config["task_order"]:
            group, level_text = task_id.split("_L")
            level = int(level_text)
            parent_task = f"{group}_L{level-1}" if level > 1 else None
            queue.append({"position": len(queue)+1, "model_alias": model["alias"], "model": model["model"],
                          "task_id": task_id, "parent": f"{model['alias']}/{parent_task}" if parent_task else None,
                          "status": "not_started", "request_preview": f"review/{task_id}.json"})
    save(HERE / "queue.json", {"mode": "serial", "max_active_tasks": 1, "count": len(queue), "items": queue})
    for name in ("config.json", "queue.json"):
        hashes[f"experiment/{name}"] = digest(HERE / name)
    save(review / "input_hashes.json", {"approved": False, "algorithm": "sha256", "files": hashes})
    report = {"status": "review_prepared", "requests_validated": len(entries), "models": len(models),
              "queued_tasks": len(queue), "serial": True, "model_api_calls": 0, "network_used": False,
              "godot_started": False, "user_review_pending": True, "runtime_ready": False,
              "model_budget_disclosure": False,
              "tools": ["read", "write", "render"], "task_readiness": readiness}
    save(review / "validation.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "task_readiness"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
