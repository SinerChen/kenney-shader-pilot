"""Summarize canonical saved response usage; distinguish list-rate valuation from billing."""
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
RUNTIME = PACK / "runtime/experiment"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    config = read(RUNTIME / "run_config.json")
    pricing = read(RUNTIME / "pricing_check.json")
    prices = {p["model_name"]: p for p in pricing["selected"]}
    models = {m["alias"]: m["model"] for m in config["models"]}
    by_model = defaultdict(Counter)
    by_task, traces, response_events = [], [], set()
    first, last = None, None
    duplicate_responses = 0
    for path in sorted((PACK / "runs/s1_p3").glob("*/*/trajectory.jsonl")):
        alias, task = path.parent.parent.name, path.parent.name
        totals = Counter()
        with path.open("rb") as stream:
            for raw in stream:
                if not raw.endswith(b"\n"):
                    totals["incomplete_lines"] += 1
                    break
                event = json.loads(raw)
                kind = event.get("type")
                if kind == "request":
                    totals["requests"] += 1
                elif kind in ("api_error", "local_error"):
                    totals[kind] += 1
                elif kind == "response":
                    response = event.get("response", {})
                    # The relay reuses placeholder response IDs (e.g. resp_0) for
                    # distinct calls. Deduplicate only identical canonical events.
                    event_key = (str(path), hashlib.sha256(raw).hexdigest())
                    if event_key in response_events:
                        duplicate_responses += 1
                        continue
                    response_events.add(event_key)
                    totals["responses"] += 1
                    usage = event.get("usage") or response.get("usage")
                    if not usage:
                        totals["responses_without_usage"] += 1
                        continue
                    timestamp = event.get("time")
                    if timestamp:
                        first = min(first, timestamp) if first else timestamp
                        last = max(last, timestamp) if last else timestamp
                    totals["usage_records"] += 1
                    for name in ("input_tokens", "output_tokens", "total_tokens"):
                        totals[name] += usage.get(name, 0)
                    details = usage.get("input_tokens_details") or {}
                    totals["cached_input_tokens"] += details.get("cached_tokens", 0)
                    totals["cache_write_input_tokens"] += details.get("cache_write_tokens", 0)
                    totals["input_detail_missing"] += "input_tokens_details" not in usage
                    totals["reasoning_tokens_included_in_output"] += (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        by_model[models[alias]].update(totals)
        by_task.append({"alias": alias, "task_id": task, "usage": dict(totals)})
        traces.append({"path": path.relative_to(PACK).as_posix(), "bytes": path.stat().st_size})
    valuations = []
    total = Decimal(0)
    for model in models.values():
        usage = by_model[model]
        price = prices.get(model)
        value = Decimal(0)
        rates = None
        if usage["usage_records"]:
            if not price or price["quota_type"] != 0:
                raise ValueError("Missing compatible public pricing for " + model)
            input_rate = Decimal(str(price["model_ratio"])) * 2
            output_rate = input_rate * Decimal(str(price["completion_ratio"]))
            value = (Decimal(usage["input_tokens"]) * input_rate + Decimal(usage["output_tokens"]) * output_rate) / Decimal(1000000)
            rates = {"input_usd_per_million": str(input_rate), "output_usd_per_million": str(output_rate)}
        total += value
        valuations.append({"model": model, "usage": dict(usage), "public_rates": rates,
                           "nominal_usd_all_input_at_standard_rate": str(value)})
    historical_path = Path(r"D:\threejs_seven_experiments\reports\spend_20260921_115023.json")
    historical = read(historical_path)
    previous = historical["billing"]["billing"][0]
    report = {"checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
              "scope": "scene_algorithm_tasks/runs/s1_p3 only", "first_saved_response": first,
              "last_saved_response": last, "models": valuations, "tasks": by_task,
              "total_nominal_usd_all_input_at_standard_rate": str(total),
              "actual_billed_usd": None,
              "actual_billing_status": "HTTP 401: token quota exhausted; current ledger unavailable",
              "nominal_assumptions": ["Current published model/completion ratios", "Group ratio = 1",
                                      "All input tokens valued at standard input rate; no cache read discount or cache write premium",
                                      "Output already includes reasoning tokens; do not add them again"],
              "limitations": ["This is a list-rate valuation, not confirmed money deducted or an upper/lower bound.",
                              "Historical rates, token group and cache-specific rates are not available.",
                              "Unsaved interrupted calls and errors may have charges missing from local usage.",
                              "Other projects and local Godot/video processing are excluded."],
              "pricing_source": "https://api.shubiaobiao.cn/api/pricing",
              "formula_source": "https://docs.newapi.pro/zh/docs/guide/feature-guide/admin/system-setting-advanced",
              "pricing_snapshot_sha256": hashlib.sha256((RUNTIME / "pricing_check.json").read_bytes()).hexdigest(),
              "current_api_checks": read(RUNTIME / "cost_api_checks.json"),
              "last_available_historical_account_snapshot": {"checked_at": historical["billing"]["checked_at"],
                  "used_usd": previous["used_usd"], "remaining_usd": previous["remaining_usd"],
                  "total_quota_usd": previous["total_quota_usd"], "source": str(historical_path),
                  "note": "Historical whole-key totals; not current and not attributable solely to this experiment."},
              "traces": traces, "duplicate_response_events_skipped": duplicate_responses, "model_api_calls": 0}
    path = RUNTIME / "spend_check.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("checked_at", "total_nominal_usd_all_input_at_standard_rate", "models", "duplicate_response_events_skipped")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
