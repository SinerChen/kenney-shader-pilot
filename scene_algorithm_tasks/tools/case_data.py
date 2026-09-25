"""Derive case inspection pages from preserved inputs, events and initial_effect."""
from collections import Counter
import difflib
import hashlib
import json
import os
from pathlib import Path

VERSION = 1


def read(path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, path)


def link(path, pack):
    return path.relative_to(pack).as_posix() if path.is_file() and path.resolve().is_relative_to(pack.resolve()) else None


def files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*")
            if p.is_file() and p.resolve().is_relative_to(root.resolve())}


def arguments(call):
    value = call.get("arguments", call.get("input", {}))
    try:
        return json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return {"unparsed": value}


def assistant_text(response):
    """Visible response text only; encrypted provider state remains in raw records."""
    result = []
    for item in response.get("output", []):
        if item.get("type") == "message":
            result.extend(block.get("text", "") for block in item.get("content", []) if block.get("text"))
        elif item.get("type") == "reasoning":
            result.extend(block.get("text", "") for block in item.get("summary", []) if block.get("text"))
        elif item.get("type") == "function_call":
            result.append("→ " + item.get("name", "tool") + " " + str(arguments(item).get("path", "")))
    for item in response.get("content", []):
        if isinstance(item, dict):
            if item.get("text"):
                result.append(item["text"])
            elif item.get("type") == "tool_use":
                result.append("→ " + item.get("name", "tool") + " " + str(item.get("input", {}).get("path", "")))
    for choice in response.get("choices", []):
        message = choice.get("message", {})
        if message.get("content"):
            result.append(message["content"] if isinstance(message["content"], str) else json.dumps(message["content"], ensure_ascii=False))
        for call in message.get("tool_calls", []):
            function = call.get("function", {})
            result.append("→ " + function.get("name", "tool") + " " + str(arguments(function).get("path", "")))
    return "\n\n".join(result)


def normalize(event, number, request_number):
    kind = event.get("type", "unknown")
    result = {"id": number, "type": kind, "time": event.get("time"),
              "request_number": event.get("request_number", request_number), "ok": None,
              "title": kind, "preview": "", "text": "", "tool": None, "path": None}
    if kind == "request":
        body = event.get("body", {})
        result.update(title="模型请求", preview=body.get("model", ""),
                      metadata={k: v for k, v in body.items() if k not in ("input", "messages", "instructions", "system", "tools")})
    elif kind == "response":
        response = event.get("response", {})
        text = assistant_text(response)
        result.update(title="模型响应", text=text, preview=text[:240], usage=event.get("usage") or response.get("usage"),
                      response_status=response.get("status", response.get("stop_reason", "")))
    elif kind == "tool":
        call, output = event.get("call", {}), event.get("result", {})
        args = arguments(call)
        name = call.get("name", "tool")
        errors = output.get("error") or output.get("errors") or ""
        result.update(title=name, tool=name, path=args.get("path"), ok=output.get("ok"),
                      preview=str(args.get("path") or args.get("scene") or ("scene/main.tscn" if name == "render" else "")),
                      error=errors, argument_keys=list(args), observation=output.get("observation_directory"))
    else:
        result.update(title=kind, preview=str(event.get("error") or event.get("reason") or "")[:500],
                      ok=False if "error" in kind else None)
    return result


def text_file(path):
    if path is None:
        return ""
    try:
        value = path.read_text(encoding="utf-8")
        return None if "\0" in value else value
    except (OSError, UnicodeError):
        return None


def publish_case(pack, alias, task):
    out = pack / "runs/s1_p3" / alias / task
    target = pack / "runtime/cases" / alias / task
    source = out / "input.json"
    actual = source.is_file()
    if not actual:
        source = pack / "runtime/experiment/frozen_tasks" / task / "request.json"
    if not source.is_file():
        source = pack / "experiment/review" / (task + ".json")
    initial = files(out / "initial_effect")
    current = files(out / "model_workspace/effect")
    trace = out / "trajectory.jsonl"
    watched = [source, trace, out / "inheritance.json", *initial.values(), *current.values()]
    signature = hashlib.sha256(json.dumps([VERSION, [(str(p), p.stat().st_size, p.stat().st_mtime_ns)
                                                    for p in watched if p.is_file()]], sort_keys=True).encode()).hexdigest()
    cache = read(target / "manifest.json", {})
    if cache.get("signature") == signature and (target / "detail.json").is_file():
        return {"path": link(target / "detail.json", pack), "version": signature, **cache["summary"]}
    events, writes = [], {}
    request_number, partial = 0, False
    if trace.is_file():
        with trace.open("rb") as stream:
            while raw := stream.readline():
                # A running worker can still be appending the final JSONL line.
                if not raw.endswith(b"\n"):
                    partial = True
                    break
                try:
                    event = json.loads(raw)
                except ValueError:
                    partial = True
                    continue
                if event.get("type") == "request":
                    request_number = event.get("request_number", request_number + 1)
                number = len(events) + 1
                row = normalize(event, number, request_number)
                event_path = target / "events" / f"{number:06d}.json"
                save(event_path, event)
                row["raw"] = link(event_path, pack)
                if row["tool"] == "write" and row["ok"] is True:
                    written = event["result"].get("path", row["path"] or "")
                    if written.startswith("effect/"):
                        writes.setdefault(written[7:], []).append(number)
                events.append(row)
    changes = []
    for name in sorted(set(initial) | set(current)):
        before_path, after_path = initial.get(name), current.get(name)
        before, after = text_file(before_path), text_file(after_path)
        before_hash = hashlib.sha256(before_path.read_bytes()).hexdigest() if before_path else None
        after_hash = hashlib.sha256(after_path.read_bytes()).hexdigest() if after_path else None
        state = "added" if before_path is None else "deleted" if after_path is None else "unchanged" if before_hash == after_hash else "modified"
        diff = [] if before is None or after is None else list(difflib.unified_diff(
            before.splitlines(), after.splitlines(), fromfile="initial/effect/" + name, tofile="current/effect/" + name, lineterm=""))
        row = {"name": name, "status": state, "before": link(before_path, pack) if before_path else None,
               "current": link(after_path, pack) if after_path else None,
               "bytes": after_path.stat().st_size if after_path else 0,
               "before_sha256": before_hash, "sha256": after_hash, "writes": writes.get(name, []),
               "added_lines": sum(line.startswith("+") and not line.startswith("+++") for line in diff),
               "removed_lines": sum(line.startswith("-") and not line.startswith("---") for line in diff)}
        content = target / "files" / (hashlib.sha256(name.encode()).hexdigest()[:20] + ".json")
        save(content, {**row, "before_text": before, "current_text": after, "diff": diff,
                       "binary": before is None or after is None})
        changes.append({**row, "detail": link(content, pack)})
    inheritance = read(out / "inheritance.json", {})
    parent = inheritance.get("parent")
    counts = dict(Counter(row["type"] for row in events))
    change_counts = dict(Counter(row["status"] for row in changes))
    summary = {"events": len(events), "changes": sum(row["status"] != "unchanged" for row in changes),
               "input_actual": actual}
    detail = {"alias": alias, "task_id": task, "version": signature, "input": read(source, {}),
              "input_source": "actual" if actual else "frozen_preview", "input_link": link(source, pack),
              "events": events, "event_counts": counts, "partial_trace": partial, "files": changes,
              "change_counts": change_counts, "initial_source": "initial_effect" if (out / "initial_effect").is_dir() else None,
              "parent_task": Path(parent).name if parent else None, "workspace": out.relative_to(pack).as_posix() + "/model_workspace/",
              "trajectory": link(trace, pack)}
    save(target / "detail.json", detail)
    save(target / "manifest.json", {"signature": signature, "summary": summary})
    return {"path": link(target / "detail.json", pack), "version": signature, **summary}
