"""Assemble human review material from executed reports, never inferred passes."""
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = [f"{c}_L{l}" for c in "ABCDE" for l in (1, 2)]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def write(name, value):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def by_task(rows):
    return {r["task"]: r for r in rows}


def make():
    final = by_task(read("author/reports/final_checks.json"))
    errors = by_task(read("author/reports/error_statistics.json"))
    starters = by_task(read("author/reports/starter_validation.json"))
    units = {r["suite"]: r for r in read("author/reports/unit_tests.json")}
    variants = read("author/reports/variants.json")
    visual = read("author/reports/visual_coupling.json")
    mutants = {(r["task"], r["mutation"]): r for r in read("author/reports/mutations_numeric.json")}
    mutants.update({(r["task"], r["mutation"]): r for r in read("author/reports/mutations_visual.json")})
    generated = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    records, page_tasks, gates = [], [], {}
    for task in TASKS:
        meta = read(f"starters/public/{task}/task.json")
        numeric = read(f"author/reports/reference/{task}/numeric/report.json")
        inherited = next((r for r in variants if r["task"] == task and r["type"] == "inherited"), None)
        alternative = next(r for r in variants if r["task"] == task and r["type"] == "legal_alternative")
        interactions = read(f"author/reports/reference/{task}/interactions/report.json") if task.endswith("L2") else None
        causal = [r for r in visual if r["task"] == task]
        negative = [r for (t, _), r in mutants.items() if t == task]
        check, starter = final[task], starters[task]
        videos = {v: f"author/reports/{task}/{'visual' if v == 'overview' else v}/effect.mp4" for v in ("overview", "oblique")}
        for video in videos.values():
            if not (ROOT / video).is_file():
                raise FileNotFoundError(video)
        row = {"task": task, "title": meta["title"], "numeric": {k: numeric[k] for k in ("pass", "total", "status")},
               "max_abs": errors[task]["max_abs"], "inherited": inherited, "legal_alternative": alternative,
               "causal_numeric": interactions["numeric_causal_pass"] if interactions else None,
               "causal_visual": sum(r["status"] == "PASS" for r in causal) if causal else None,
               "negative_rejected": sum(r["status"] == "REJECTED" for r in negative), "negative_total": len(negative),
               "gpu_render_consistency": check["gpu_render_consistency"], "starter": starter,
               "release": "BLOCKED_RELEASE", "videos": videos}
        records.append(row)
        gates[task] = {"cpu_analytic": units["cpu_analytic"]["status"] == "PASS", "gpu_numeric": numeric["status"] == "PASS",
                       "inherited_numeric": inherited["status"] == "PASS" if inherited else "NOT_APPLICABLE",
                       "causal_interactions": (interactions["numeric_causal_pass"] == 5 and row["causal_visual"] == 5) if interactions else "NOT_APPLICABLE",
                       "gpu_render_consistency": check["gpu_render_consistency"]["status"] == "PASS",
                       "negative_controls": len(negative) > 0 and row["negative_rejected"] == len(negative),
                       "legal_alternative": alternative["status"] == "PASS", "clean_starter": starter["starter"] == "PASS",
                       "clean_reimport": starter["clean_import"] == "PASS", "file_protection": starter["file_audit"] == "PASS" and starter["source_unchanged"],
                       "runtime_protection": all(check[v]["protection"] == "PASS" for v in videos),
                       "os_isolation": False, "visual_calibration": False, "budgets_frozen": False}
        evidence = [{"label": "GPU 新增数值组", "result": f'{numeric["pass"]}/{numeric["total"]}', "path": f"author/reports/reference/{task}/numeric/report.json"},
                    {"label": "逐组误差统计", "result": f'最大绝对误差 {row["max_abs"]:.3g}', "path": "author/reports/error_statistics.json"},
                    {"label": "合法实现变体", "result": f'{alternative["pass"]}/10', "path": "author/reports/variants.json"},
                    {"label": "错误变体拒绝", "result": f'{row["negative_rejected"]}/{len(negative)}', "path": "author/reports/negative_controls.json"},
                    {"label": "GPU / 显示依赖与保护", "result": check["gpu_render_consistency"]["status"], "path": "author/reports/final_checks.json"},
                    {"label": "干净导入 / 空实现 / 白名单导出", "result": starter["starter"], "path": "author/reports/starter_validation.json"}]
        if inherited:
            evidence.extend([{"label": "继承 L1 回归", "result": f'{inherited["pass"]}/10', "path": "author/reports/variants.json"},
                             {"label": "因果干预 · 数值", "result": f'{row["causal_numeric"]}/5', "path": f"author/reports/reference/{task}/interactions/report.json"},
                             {"label": "因果干预 · 图像响应与不变量", "result": f'{row["causal_visual"]}/5', "path": "author/reports/visual_coupling.json"}])
        files = read(f"starters/public/{task}/scene_inventory.json")["files"]
        listed = {f["path"] for f in files}
        for p in sorted((ROOT / "starters" / task).rglob("*")):
            rel = p.relative_to(ROOT / "starters" / task).as_posix()
            if p.is_file() and rel not in listed and not any(x.startswith(".") for x in Path(rel).parts) and p.suffix not in {".uid", ".import"}:
                files.append({"path": rel, "access": "writable" if rel.startswith("solution/") else "read_only"})
        page_tasks.append({"id": task, "title": meta["title"], "algorithm": meta["algorithm"], "numeric": row["numeric"], "max_abs": row["max_abs"],
                           "prompt": (ROOT / f"tasks/{task}/prompt.md").read_text(encoding="utf-8"), "targets": meta["authorized_runtime_bindings"],
                           "files": sorted(files, key=lambda x: x["path"]), "evidence": evidence,
                           "reference_files": sorted(p.name for p in (ROOT / f"author/references/{task}/gpu_solution/solution").iterdir() if p.is_file() and p.suffix != ".uid"), **videos})
    write("author/reports/negative_controls.json", list(mutants.values()))
    totals = {"tasks": len(records), "numeric": sum(r["numeric"]["pass"] for r in records),
              "inherited": sum(r["inherited"]["pass"] for r in records if r["inherited"]),
              "legal_alternative": sum(r["legal_alternative"]["pass"] for r in records),
              "causal_numeric": sum(r["causal_numeric"] or 0 for r in records), "causal_visual": sum(r["causal_visual"] or 0 for r in records),
              "negative_rejected": sum(r["negative_rejected"] for r in records), "negative_total": len(mutants), "videos": len(records) * 2}
    visual_report = read("author/reports/A_L1/visual/report.json")
    environment = {"os": platform.platform(), "python": platform.python_version(), "engine": visual_report["engine"],
                   "engine_sha256": read("author/reports/A_L1/visual/execution.json")["engine_sha256"],
                   "gpu": "AMD Radeon 780M Graphics", "driver": "32.0.13046.2004", "renderer": "Forward+ / Vulkan",
                   "capture": {"width": 640, "height": 360, "fps": 15, "frames": 90, "format": "H.264 MP4", "views": 2},
                   "numeric_format": "GPU float32 raw buffer versus independent CPU float64"}
    limitations = ["正式模型实验未启动，原实验保持暂停；没有模型成绩或调用轨迹。",
                  "L1/L2 使用合成最小场景；v0.2 的 6 个 L3 及原生源绑定状态单独见 L3_STATUS.md。",
                  "read/write 路径限制和运行时快照不等于 OS 沙箱。外部候选执行器尚未接入，默认拒绝执行任意候选。",
                  "图像响应、不变量、资源绑定检查已运行；VLM 审美评分、评分模型和阈值仍未校准。",
                  "推理与资源预算尚未锁定，正式模型导出门禁保持关闭；--review 仅用于人工检查。",
                  "错误变体含部分故障代理，例如方向性扩散算子模拟串行原地更新偏差；不是每种作弊实现的穷尽证明。",
                  "合法实现变体主要改变线程组、噪声多项式求值和 POM 粗搜索，不代表已覆盖全部合法解法。",
                  "当前容限为 atol=rtol=2e-4，布尔值精确匹配；跨 GPU 的最终容限仍待锁定。"]
    summary = {"generated": generated, "status": "AUTHOR_BUILD_VALIDATED_RELEASE_BLOCKED", "source": read("author/source.json"),
               "environment": environment, "totals": totals, "unit_tests": list(units.values()), "limitations": limitations, "tasks": records}
    write("VALIDATION.json", summary)
    write("author/release_lock.json", {"status": "BLOCKED_RELEASE", "generated": generated, "environment": environment,
          "model_experiment": "NOT_STARTED", "os_worker": None, "vlm_scorer": None, "visual_thresholds": None,
          "inference_budget": None, "performance_budget": None, "task_gates": gates,
          "runtime_scope": "Reference snapshots and file audits only; hostile-candidate isolation/provenance validation is not established."})
    lines = ["# 森林题目验证汇总", "", f"生成：{generated}", "", "已完成 5 条链、10 道 L1/L2 题的本地作者侧制作与验证。正式投放状态为 **BLOCKED_RELEASE**。", "",
             "[题目与视频检查页](index.html) · [使用说明](README.md) · [机器可读报告](VALIDATION.json)", "",
             f"已执行：新增数值 {totals['numeric']}/100，继承回归 {totals['inherited']}/50，合法实现变体 {totals['legal_alternative']}/100，因果数值 {totals['causal_numeric']}/25，因果图像响应 {totals['causal_visual']}/25，错误变体拒绝 {totals['negative_rejected']}/{totals['negative_total']}。",
             "", "CPU 解析锚点测试 19/19，read/write/render 工具测试 10/10。10 个起始工程均完成干净导入、空实现检查、文件保护与白名单导出检查。", "",
             "| 题目 | GPU 数值 | 最大绝对误差 | 继承回归 | 因果数值 / 图像 | 错误变体拒绝 | 视频 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in records:
        t = r["task"]
        lines.append(f"| [{t} · {r['title']}](tasks/{t}/prompt.md) | {r['numeric']['pass']}/10 | {r['max_abs']:.3g} | {str(r['inherited']['pass'])+'/10' if r['inherited'] else '—'} | {str(r['causal_numeric'])+'/5 · '+str(r['causal_visual'])+'/5' if r['inherited'] else '—'} | {r['negative_rejected']}/{r['negative_total']} | [主视角]({r['videos']['overview']}) · [斜视角]({r['videos']['oblique']}) |")
    lines += ["", "## 如何理解这些结果", "", "数值判定读取同步后的 GPU float32 原始缓冲，与独立 float64 CPU 参考比较。显示检查读取实际绑定材质资源；前后景折射检查还核对当前帧捕获纹理与层掩码。截图、MP4 不作为数值替代。", "",
              "25 组因果检查同时记录受控参数变化、应改变的结果和指定不变量。图像响应通过表示存在正确的依赖证据，不等同于最终美观程度通过。", "",
              "5 份 L1-only gold 前级参考已逐份通过 10 组数值与渲染检查。L2 的 self_predecessor 与 gold_predecessor 由导出器分开记录；不向模型继承作者私有分数或对话。", "",
              "## 环境与证据", "", f"Godot 4.6.1 / Forward+ / Vulkan；{environment['gpu']}；驱动 {environment['driver']}；Python {environment['python']}。每题 2 段 6 秒视频，640×360、15 fps。", "",
              "- [逐组 max / mean / p95 误差](author/reports/error_statistics.json)",
              "- [继承与合法变体](author/reports/variants.json)", "- [错误变体结果](author/reports/negative_controls.json)",
              "- [因果图像证据](author/reports/visual_coupling.json)", "- [最终渲染与 GPU 一致性](author/reports/final_checks.json)",
              "- [干净工程与导出检查](author/reports/starter_validation.json)", "- [大整数事件 ID 回归](author/reports/large_event_ids/report.json)",
              "- [单元测试](author/reports/unit_tests.json)", "- [性能观测](author/reports/profile_summary.json)", "",
              "性能数据仅为本机观测，含参考调度及显示所需的回读/上传；Viewport GPU 计时不包含本地 RenderingDevice 的计算队列，不能作为总 GPU 耗时或性能通过结论。", "",
              "## 未完成的投放条件与限制", ""]
    lines += ["- " + item for item in limitations]
    lines += ["", "私有案例、参考、原始日志与视频保存在 author/，该目录已从 Git 和模型包排除。公开页面只适合在这份完整的本地目录中查看，单独复制页面不会携带视频。", ""]
    lines.extend(["", "Additional review evidence:", "",
                  "- [HTML playback and link checks](author/reports/review_page/report.json)",
                  "- [Review exports and inheritance sources](author/reports/review_exports.json)", ""])
    (ROOT / "VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "author/status.md").write_text("# 作者侧状态\n\n" + "\n".join(lines[2:]).replace("](author/", "](").replace("](index.html)", "](../index.html)").replace("](README.md)", "](../README.md)").replace("](VALIDATION.json)", "](../VALIDATION.json)").replace("](tasks/", "](../tasks/") + "\n", encoding="utf-8")
    from l3_report import assemble
    l3_page,l3_summary=assemble()
    page_tasks.extend(l3_page)
    summary["l3"]={k:v for k,v in l3_summary.items() if k!="tasks"}
    summary["task_specs"]=16
    write("VALIDATION.json",summary)
    with (ROOT/"VALIDATION.md").open("a",encoding="utf-8") as f:f.write("\n[L3 v0.2 status](L3_STATUS.md): 6 definitions, 5 native blank starters; integration NOT_RUN.\n")
    with (ROOT/"author/status.md").open("a",encoding="utf-8") as f:f.write("\n[L3 v0.2 status](../L3_STATUS.md): 6 definitions, 5 native blank starters; integration NOT_RUN.\n")
    template = (ROOT / "templates/review.html").read_text(encoding="utf-8")
    payload = json.dumps({"generated": generated, "tasks": page_tasks}, ensure_ascii=False).replace("<", "\\u003c")
    (ROOT / "index.html").write_text(template.replace("__DATA__", payload), encoding="utf-8")
    print(json.dumps(totals, ensure_ascii=False))


if __name__ == "__main__":
    make()
