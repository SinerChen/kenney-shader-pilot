"""Validate specification structure and evidence; this is not a shader evaluator."""
import hashlib
import json
import re
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
WORKSPACE = PACK.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = read(PACK / "manifest.json")
    require(manifest["chain_count"] == len(manifest["chains"]) == 5, "Expected five chains")
    require(manifest["task_count"] == len(manifest["tasks"]) == 15, "Expected fifteen tasks")
    tasks = {item["id"]: read(PACK / item["task"]) for item in manifest["tasks"]}
    require(len(tasks) == 15, "Duplicate task IDs")
    doc = (PACK / manifest["source_snapshot"]).read_text(encoding="utf-8-sig")
    source_ids = set(re.findall(r"(?m)^\| ([A-L]\d\d) \|", doc))
    source_ids.update(re.findall(r"(?m)^### (P\d\d) ", doc))
    case_ids = set()
    for chain in manifest["chains"]:
        cid = chain["id"]
        require(set(chain["source_ids"]) <= source_ids, f"Unknown source: {cid}")
        require((WORKSPACE / chain["scene"]).is_file(), f"Missing scene: {cid}")
        require((WORKSPACE / chain["project"]).is_file(), f"Missing project: {cid}")
        require(len(chain["tasks"]) == 3, f"Wrong chain length: {cid}")
        for number, tid in enumerate(chain["tasks"], 1):
            task = tasks[tid]
            require(task["level"] == number and task["chain_id"] == cid, f"Wrong level: {tid}")
            require(task["parent_task"] == (None if number == 1 else f"{cid}_L{number-1}"), f"Wrong parent: {tid}")
            require(task["status"] == "spec_ready" and not task["runtime_ready"], f"Wrong readiness: {tid}")
            require(task["evaluation_status"] == "new_task_not_run" and task["model_api_calls"] == 0,
                    f"Unsupported evaluation claim: {tid}")
            require(task["editable_directory"] == "effect/", f"Edit scope: {tid}")
            require(len(task["requirements"]) >= 4 and len(task["criteria"]) == 4, f"Incomplete rubric: {tid}")
            require(task["required_targets"] and task["protected_targets"] and task["scene_purpose"], f"Impact scope: {tid}")
            require(len(task["impact_path"]) >= 4 and len(task["required_fixture_work"]) >= 4, f"Missing fixtures: {tid}")
            if "primary_algorithms" in task and number == 1:
                require(not task["fixed_supporting_algorithms"], f"L1 multiple modules: {tid}")
            cases = read(PACK / task["evaluation_cases"])
            require(cases["task_id"] == tid and len(cases["cases"]) == 4, f"Case mapping: {tid}")
            require([c["expected"] for c in cases["cases"]] == task["criteria"], f"Rubric drift: {tid}")
            prompt = (PACK / task["prompt"]).read_text(encoding="utf-8")
            require(task["title"] in prompt, f"Wrong prompt: {tid}")
            require(not re.search(r"\b(?:SH\d{3}|[A-LP]\d{2}|SA\d{2}(?:_L[123])?)\b", prompt), f"Catalog ID leaked: {tid}")
            require(not any(s in prompt for s in ("公开验收", "rubric", "cases.json", "INTERFACE.md", "契约", "评分", "通过条件", "典型失败")), f"Evaluation content leaked: {tid}")
            require(all(s in prompt for s in ("固定测试输入", "输出要求", "需要生成的效果", "read(", "write(", "render(", "自主渲染观察")), f"Incomplete model input: {tid}")
            embedded = re.search(r"```json\n(.*?)\n```", prompt, re.S)
            require(embedded is not None, f"Missing fixed JSON input: {tid}")
            require(json.loads(embedded.group(1)) == read(PACK / task["model_input"]["fixed_input"]), f"Fixed input drift: {tid}")
            require(task["model_input"]["automatic_attachments"] == [], f"Unexpected model attachments: {tid}")
            for visible in task["model_input"]["readable_directories"]:
                require((PACK / task["model_input"]["workspace"] / visible).is_dir(), f"Missing visible directory: {tid}")
            require(task["environment_ready"] is True, f"Environment not prepared: {tid}")
            environment = read(PACK / task["model_input"]["environment"])
            require(environment == task["test_environment"], f"Environment drift: {tid}")
            require(environment["scope"] == ["scene_subset", "interaction_subset", "full_scene"][number-1], f"Wrong scene scope: {tid}")
            experiment = PACK / task["model_input"]["workspace"]
            scene_text = (experiment / "scene/main.tscn").read_text(encoding="utf-8")
            require("res://" + environment["source_entry"] in scene_text, f"Not inheriting original scene: {tid}")
            require((experiment / "effect/main.gd").is_file(), f"Missing candidate entry: {tid}")
            require((experiment / "scene/environment_setup.gd").is_file(), f"Missing selection script: {tid}")
            require(cases["model_visible"] is False, f"Cases exposed: {tid}")
            for case in cases["cases"]:
                require(case["id"] not in case_ids, f"Duplicate case: {case['id']}")
                case_ids.add(case["id"])
                for field in ("intervention", "expected", "evidence", "typical_failure"):
                    require(case[field], f"Missing internal {field}: {case['id']}")
                require(case["status"] == "protocol_defined_not_executed", f"Unsupported pass: {case['id']}")
            fixture_file, _, fixture_anchor = task["fixture_protocol"].partition("#")
            require((PACK / fixture_file).is_file(), f"Missing fixture doc: {tid}")
            require(f'id="{fixture_anchor}"' in (PACK / fixture_file).read_text(encoding="utf-8"), f"Missing fixture anchor: {tid}")
    definitions = read(PACK / "model_tools.json")
    require(len(definitions) == 3 and {d["name"] for d in definitions} == {"read", "write", "render"}, "Unexpected tool")
    snapshot = read(PACK / manifest["algorithm_snapshot"])
    for algorithm in snapshot["algorithms"]:
        require(algorithm["library_validation_passed"] is True, f"Missing evidence: {algorithm['id']}")
        for item in algorithm["files"]:
            path = WORKSPACE / item["path"]
            require(path.is_file(), f"Missing provenance: {path}")
            require(hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], f"Provenance changed: {path}")
    require(hashlib.sha256((PACK / manifest["source_snapshot"]).read_bytes()).hexdigest() == snapshot["source_document_sha256"], "Source document changed")
    link_count = 0
    for path in PACK.rglob("*.md"):
        if "sources" in path.relative_to(PACK).parts:
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target:
                continue
            rel, _, anchor = target.partition("#")
            dest = path.parent / rel if rel else path
            require(dest.is_file(), f"Broken link: {path.name}: {target}")
            if anchor:
                require(f'id="{anchor}"' in dest.read_text(encoding="utf-8"), f"Missing anchor: {target}")
            link_count += 1
    report = dict(status="passed", checks="specification_structure_and_local_evidence_only",
                  chains=5, tasks=15, cases=len(case_ids), local_links_checked=link_count,
                  algorithms=len(snapshot["algorithms"]), godot_started=False,
                  shader_compilation_tested=False, scene_integration_tested=False,
                  model_api_calls=0, runtime_ready=False, environment_ready=True, scene_environments=15, model_prompt_only=True, tools=["read", "write", "render"], evaluator_cases_model_visible=False)
    (PACK / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
