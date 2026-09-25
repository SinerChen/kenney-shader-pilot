"""Audit canonical tool events and compare each run with its own initial_effect."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import posixpath

PACK = Path(__file__).resolve().parents[1]
MODELS = {"openai_astra": "Astra / gpt-6-astra", "openai_main": "Sol / gpt-5.6-sol"}
GROUPS = {"effect": "自身候选文件", "native": "原始 Godot 项目", "scene": "实验场景与环境", "inputs": "固定输入", "observations": "渲染观测", "other": "其他"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def normalized(path):
    return posixpath.normpath(str(path).replace("\\", "/"))


def group(path):
    if path.startswith("scene/project/"):
        return "native"
    return path.split("/")[0] if path.split("/")[0] in GROUPS else "other"


def fingerprint(root):
    result = {}
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                result["effect/" + path.relative_to(root).as_posix()] = hashlib.sha256(data).hexdigest()
    return result


def scan(run, trace, size):
    events, ignored = [], 0
    with trace.open("rb") as stream:
        lines = stream.read(size).splitlines(keepends=True)
    for line in lines:
        if not line.endswith(b"\n"):
            ignored += 1
            continue
        events.append(json.loads(line))
    reads, directories, metadata, writes, failures = [], [], [], [], []
    request = 0
    for number, event in enumerate(events, 1):
        if event.get("type") == "request":
            request = event.get("request_number", request + 1)
        if event.get("type") != "tool":
            continue
        call, output = event.get("call", {}), event.get("result", {})
        name = call.get("name")
        if name not in ("read", "write"):
            continue
        args = call.get("arguments", call.get("input", {}))
        if isinstance(args, str):
            args = json.loads(args)
        entry = {"event": number, "request": request, "time": event.get("time"), "tool": name,
                 "path": normalized(args.get("path", ".")), "requested_path": args.get("path"), "ok": output.get("ok")}
        if output.get("ok") is not True:
            entry["error"] = output.get("error", output.get("errors"))
            failures.append(entry)
            continue
        if name == "write":
            entry.update(sha256=output.get("sha256"), bytes=output.get("bytes"))
            writes.append(entry)
            continue
        kind = output.get("kind")
        entry["kind"] = kind
        if kind == "directory":
            entry["entries"] = output.get("entries", [])
            directories.append(entry)
        elif kind == "binary_metadata":
            metadata.append(entry)
        elif kind in ("text", "image"):
            entry["group"] = group(entry["path"])
            if kind == "text":
                content = output.get("content", "")
                count = len(content.splitlines())
                entry.update(start_line=output.get("start_line", 1), total_lines=output.get("total_lines"),
                             returned_lines=count, next_line=output.get("next_line"),
                             content_truncated=output.get("content_truncated", False))
                entry["end_line"] = entry["start_line"] + count - 1 if count else None
                entry["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            reads.append(entry)
        else:
            raise ValueError(f"Unknown successful read kind: {kind!r}")
    initial = fingerprint(run / "initial_effect")
    current = fingerprint(run / "model_workspace/effect")
    # Recheck the currently running case to identify a concurrent file mutation.
    stable = current == fingerprint(run / "model_workspace/effect")
    file_diff = []
    for path in sorted(initial.keys() | current.keys()):
        before, after = initial.get(path), current.get(path)
        state = "added" if before is None else "deleted" if after is None else "unchanged" if before == after else "modified"
        file_diff.append({"path": path, "state": state, "initial_sha256": before, "current_sha256": after,
                          "successful_writes": sum(w["path"] == path for w in writes)})
    result = read_json(run / "result.json")
    final = result.get("candidate_files")
    final_matches = ({"effect/" + p: h for p, h in final.items()} == current) if final is not None else None
    return {"task": run.name, "state": result.get("stop_reason", "running"), "finished": result.get("finished"),
            "trace": trace.relative_to(PACK).as_posix(), "trace_bytes": size, "events": len(events),
            "last_event_time": events[-1].get("time") if events else None, "ignored_partial_lines": ignored,
            "initial_snapshot_present": (run / "initial_effect").is_dir(), "current_hashes_stable": stable,
            "finished_result_hashes_match": final_matches, "reads": reads, "directories": directories,
            "metadata_only": metadata, "writes": writes, "failures": failures, "files": file_diff}


def list_paths(events):
    return "; ".join(f"`{path}` ×{count}" for path, count in sorted(Counter(e["path"] for e in events).items())) or "无"


def main():
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    status = read_json(PACK / "runtime/experiment/status.json")
    sources = [(alias, p.parent, p, p.stat().st_size) for alias in MODELS
               for p in sorted((PACK / "runs/s1_p3" / alias).glob("*/trajectory.jsonl"))]
    audit = {"started": started, "experiment_status_at_start": status, "scope": "scene_algorithm_tasks/runs/s1_p3",
             "method": "Canonical successful tool events only. Directories and metadata excluded from content reads. File diffs compare each run's own initial_effect.", "models": {}}
    for alias, label in MODELS.items():
        cases = [scan(run, trace, size) for a, run, trace, size in sources if a == alias]
        reads = [e for c in cases for e in c["reads"]]
        writes = [e for c in cases for e in c["writes"]]
        changed = [(c["task"], f) for c in cases for f in c["files"] if f["state"] != "unchanged"]
        summary = {"started_tasks": len(cases), "finished_tasks": sum(c["finished"] is not None for c in cases),
                   "successful_writes": len(writes), "plan_writes": sum(e["path"] == "effect/plan.json" for e in writes),
                   "written_file_instances": sum(len({e["path"] for e in c["writes"]}) for c in cases),
                   "changed_file_instances": len(changed), "changed_nonplan_instances": sum(f["path"] != "effect/plan.json" for _, f in changed),
                   "changed_by_state": dict(Counter(f["state"] for _, f in changed)),
                   "content_read_calls": len(reads), "content_read_file_instances": sum(len({e["path"] for e in c["reads"]}) for c in cases),
                   "content_read_unique_paths": len({e["path"] for e in reads}),
                   "text_reads": sum(e["kind"] == "text" for e in reads), "image_reads": sum(e["kind"] == "image" for e in reads),
                   "directory_reads": sum(len(c["directories"]) for c in cases), "metadata_reads": sum(len(c["metadata_only"]) for c in cases),
                   "failed_reads": sum(e["tool"] == "read" for c in cases for e in c["failures"]),
                   "failed_writes": sum(e["tool"] == "write" for c in cases for e in c["failures"]),
                   "written_paths": sorted({e["path"] for e in writes}),
                   "native_read_paths": sorted({e["path"] for e in reads if e["group"] == "native"})}
        audit["models"][alias] = {"label": label, "summary": summary, "cases": cases}
    audit["finished"] = datetime.now().astimezone().isoformat(timespec="seconds")
    target = PACK / "runtime/experiment/file_access_audit.json"
    target.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# Astra 与 Sol 文件读写审计", "", f"快照开始：{started}；快照完成：{audit['finished']}。实验仍会继续，本报告不自动刷新。", "",
          "范围仅为本次 `scene_algorithm_tasks/runs/s1_p3`。成功 `read` 的文本与图像算作实际读取；目录列表、二进制元数据、失败请求分开列出。提示词直接附带的内容与渲染返回的图像不计入显式文件读取次数。", "",
          "“改动”按每题自己的 `initial_effect/` 与快照时的 `model_workspace/effect/` 比较；S1 继承但未改动的文件不算本题修改。成功写过也可能最后恢复原样。次数不代表质量或实际采用了文件中的算法。", "",
          "完整事件证据（时间、轨迹事件号、返回行段、内容哈希、写入哈希）见 [file_access_audit.json](../runtime/experiment/file_access_audit.json)。行段仅表示该次返回文本，不能推断完整读过文件；截断时末行可能不完整。", "",
          "| 模型 | 已结束/已开始 | 成功写入（计划） | 有差异文件实例（非计划） | 读取文本/图像 | 目录/元数据 | 失败读/写 |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for model in audit["models"].values():
        s = model["summary"]
        md.append(f"| {model['label']} | {s['finished_tasks']}/{s['started_tasks']} | {s['successful_writes']}（{s['plan_writes']}） | {s['changed_file_instances']}（{s['changed_nonplan_instances']}） | {s['text_reads']}/{s['image_reads']} | {s['directory_reads']}/{s['metadata_reads']} | {s['failed_reads']}/{s['failed_writes']} |")
    md += ["", "文件实例按“模型＋题号＋路径”计数；相同 `effect/main.gd` 在不同题中分别计算。已结束表示留有结果，不表示独立验收通过。", ""]
    state_names = {"added": "新增", "modified": "修改", "deleted": "删除", "unchanged": "与初始相同"}
    for alias, model in audit["models"].items():
        md += [f"## {model['label']}", "", "### 改动总览", "", "下表省略每题的 `effect/plan.json`；计划写入与完整文件差异见逐题详情。", "",
               "| 题目 | 状态 | 相对本题初始快照有变化的非计划文件 |", "| --- | --- | --- |"]
        for c in model["cases"]:
            changes = "; ".join(f"`{f['path']}`（{state_names[f['state']]}）" for f in c["files"] if f["state"] != "unchanged" and f["path"] != "effect/plan.json") or "无"
            md.append(f"| {c['task']} | {c['state']} | {changes} |")
        md += ["", "### 读取过的原始 Godot 项目文件（跨题去重）", ""]
        for path in model["summary"]["native_read_paths"]:
            tasks = [c["task"] for c in model["cases"] if any(e["path"] == path for e in c["reads"])]
            md.append(f"- `{path}`：{', '.join(tasks)}")
        md += ["", "### 逐题完整明细", ""]
        for c in model["cases"]:
            md += [f"#### {c['task']}", "", f"状态：`{c['state']}`；最后记录：{c['last_event_time']}；[实际轨迹](../{c['trace']})。", "",
                   "**文件差异与成功写入**", "", "| 文件 | 快照差异 | 成功写入次数 |", "| --- | --- | --- |"]
            for f in c["files"]:
                md.append(f"| `{f['path']}` | {state_names[f['state']]} | {f['successful_writes']} |")
            md += ["", "**成功读取的内容**", ""]
            for category, title in GROUPS.items():
                selected = [e for e in c["reads"] if e["group"] == category]
                if not selected:
                    continue
                md += [f"{title}：", ""]
                by_path = defaultdict(list)
                for e in selected:
                    by_path[e["path"]].append(e)
                for path, entries in sorted(by_path.items()):
                    ranges = []
                    for e in entries:
                        loc = "图像" if e["kind"] == "image" else f"L{e['start_line']}–{e['end_line']}" if e["end_line"] else "空内容"
                        if e.get("content_truncated"):
                            loc += "（截断）"
                        ranges.append(f"{loc} @事件{e['event']}")
                    md.append(f"- `{path}` ×{len(entries)}：" + "; ".join(ranges))
                md.append("")
            md += ["**仅浏览目录**：" + list_paths(c["directories"]), "", "**仅元数据**：" + list_paths(c["metadata_only"]), ""]
            if c["failures"]:
                md += ["**失败调用（未计入成功读写）**", ""]
                for e in c["failures"]:
                    error = str(e["error"]).replace("\n", " ")
                    md.append(f"- 事件 {e['event']}：`{e['tool']} {e['path']}`：{error}")
                md.append("")
            if not c["current_hashes_stable"]:
                md += ["注意：扫描期间候选文件发生变化，本题文件差异是扫描中的快照。", ""]
            if c["finished_result_hashes_match"] is False:
                md += ["注意：当前文件与已保存 result.json 候选哈希不同。", ""]
    report = PACK / "experiment/FILE_ACCESS_AUDIT.md"
    report.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"started": started, "report": str(report), "models": {a: m["summary"] for a, m in audit["models"].items()},
                      "validation": {"all_initial_snapshots_present": all(c["initial_snapshot_present"] for m in audit["models"].values() for c in m["cases"]),
                                     "all_current_hashes_stable": all(c["current_hashes_stable"] for m in audit["models"].values() for c in m["cases"]),
                                     "all_finished_hashes_match": all(c["finished_result_hashes_match"] is not False for m in audit["models"].values() for c in m["cases"]) }}, ensure_ascii=True))


if __name__ == "__main__":
    main()
