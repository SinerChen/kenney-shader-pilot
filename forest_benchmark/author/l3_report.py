"""Keep L3 definition, native starter and actual integration statuses separate."""
import json
from pathlib import Path
from datetime import datetime,timezone
from l3_source import ROOT,TASKS,dump
from l3 import definitions,read,run_integration,validate_release


def assemble():
    specs=definitions();preflight={r["task"]:r for r in read(ROOT/"author/reports/l3/predecessor_regression.json")}
    rows=[];page=[]
    for task in TASKS:
        binding=read(ROOT/"author/source_bindings"/(task+".json"))
        integration=run_integration(task)
        report_path=ROOT/"author/reports/l3"/task/"starter/report.json"
        starter=read(report_path) if report_path.exists() else None
        row={"task":task,"title":specs[task]["title"],"spec":"SPEC_VALIDATED","source_origin":"native_snapshot",
             "source_binding":binding["status"],"source_blockers":binding["blockers"],"predecessor_preflight":preflight[task],
             "starter":starter,"integration":integration,"release":validate_release(task),"native_reference":"NOT_IMPLEMENTED"}
        rows.append(row)
        project=ROOT/"starters"/task
        files=[]
        if project.exists():
            for p in sorted(project.rglob("*")):
                rel=p.relative_to(project).as_posix()
                if p.is_file() and not any(part.startswith(".") for part in Path(rel).parts) and not rel.endswith(".uid"):
                    files.append({"path":rel,"access":"writable" if rel.startswith("solution/") else "read_only"})
        page.append({"id":task,"level":"L3","title":specs[task]["title"],"algorithm":specs[task]["algorithm"],
                     "prompt":(ROOT/"tasks"/task/"prompt.md").read_text(encoding="utf-8"),"numeric":{"pass":preflight[task]["core_regression_pass"],"total":20},
                     "targets":[g["node"] for g in binding["authorized_runtime_bindings"]],"files":files,"reference_files":[],
                     "source_status":binding["status"],"source_blockers":binding["blockers"],"has_starter":bool(starter),
                     "overview":starter["video"] if starter else None,"oblique":None,
                     "evidence":[{"label":"同提交源绑定","result":binding["status"],"path":f"author/source_bindings/{task}.json"},
                                 {"label":"L2 封存产物预检（非 L3 成绩）","result":f'{preflight[task]["core_regression_pass"]}/20 数值 · {preflight[task]["coupling_regression_pass"]}/5 联动',"path":"author/reports/l3/predecessor_regression.json"},
                                 {"label":"本级场景集成","result":"未执行 · 10 组设计","path":f"author/reports/l3/{task}/integration.json"},
                                 {"label":"正式投放","result":"BLOCKED_RELEASE","path":"author/reports/l3/summary.json"}]+
                                ([{"label":"完整森林空接入工程","result":"已导入渲染 · 无新增效果","path":f"author/reports/l3/{task}/starter/report.json"}] if starter else [])})
    summary={"version":"0.2","generated":datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),"task_specs":16,"l3_specs":6,
             "native_starters":sum(bool(r["starter"]) for r in rows),"l3_integration_designs":60,"l3_integration_executed":0,
             "predecessor_preflight_numeric":sum(r["predecessor_preflight"]["core_regression_pass"] for r in rows),
             "predecessor_preflight_coupling":sum(r["predecessor_preflight"]["coupling_regression_pass"] for r in rows),
             "l3_candidate_core_regressions":"NOT_RUN","active_l3_tasks":[],"tasks":rows}
    dump(ROOT/"author/reports/l3/summary.json",summary)
    dump(ROOT/"author/reports/l3/review_data.json",page)
    lines=["# L3 增补状态（v0.2）","","[返回检查页](index.html) · [L1/L2 验证](VALIDATION.md)","",
           "已加入 6 道 L3 题目与 60 组集成覆盖设计；5 个完整原森林起始工程已导入渲染。起始工程继承指定链的 L2 核心，L3 接入保持 UNIMPLEMENTED_BINDING。当前没有合格的 L3 集成参考，也未执行这 60 组集成检测，不可正式投放。","",
           "| 任务 | 前级 | 源绑定 | 起始工程 | 本级集成 |","| --- | --- | --- | --- | --- |"]
    for r in rows:
        task=r["task"]
        lines.append(f"| [{task} · {r['title']}](tasks/{task}/prompt.md) | {task[0]}_L2 | {r['source_binding']} | {'完整森林，空接入已运行' if r['starter'] else '源门禁阻塞，未生成'} | NOT_RUN / 10 |")
    lines += ["","## 已实际完成的检查","",
              "- 原归档来自同一提交 ac523ed97ca1719f517cd3968f3ff49d76274baa，192 个源文件；ZIP 提交注释与逐文件 SHA-256 均已保存。",
              "- 归一化森林加载了 35,273 个节点、23,113 个网格实例；未用合成平面替换原场景。仅分离缺失的编辑器地被生成插件并固定导入兼容设置，保留烘焙植被、TAA 和遮挡剔除。",
              "- 原地形活动材质为 Materials/Terrain 1.tres，实际 Shader 路径已核验；原河流确实挂在 Main Terrain/BezierCurve_001。",
              "- 原天空 perlworlnoise.tga 导入为 128×128×128 的 CompressedTexture3D，weather.bmp 为 512×512 的 CompressedTexture2D。",
              "- 两棵原树各选 48 个原始风权重为零的枝干顶点作为中性锚点；保留源模型缩放、层级、LOD 与风动。",
              "- B 的允许域输入选择原颜色数组第 0 层，阈值 0.55；源图像采样选出的局部片区同时含允许/禁止格点。此为作者输入选择，压缩 GPU 误差及完整边界测试仍待校准。",
              "- D/E 的正交局部片区来自原河流近水平三角形内部，物理流速是单独任务输入；不从原 UV 动画推断速度。",
              "- 每个 L3 分支使用封存 L2 做 20+5 预检，总计 120 次数值和 30 次联动通过。C 两分支前级哈希相同、分别运行；这些不是 L3 候选成绩。","",
              "## 原生阻塞与剩余工作","",
              "C_L3_S：原天空将相机位置按 (0.1, 0.2, 0.1) 缩放，却沿未做同一变换的 EYEDIR 光线采样。当前未证明存在与多相机一致的唯一世界密度映射，因此按原生任务保留 BLOCKED_SOURCE，未另造云场冒充原系统。","",
              "其余任务已有可观察完整工程及公开输入草案，仍需要 L3 合格接入、独立 oracle、实际 GPU 状态与显示一致性、具体私有输入、逐组正反对照和容差校准。60 个目录目前保存 definition.json 设计，尚无可执行 input/expected。run_integration 会明确返回 NOT_RUN。","",
              "正式投放还需要候选的 20+5 回归、运行时保护校准、同源重导入基线、隔离执行器、视觉评分与预算锁定、资产许可逐文件核对。新增命令不会自动调用模型；原实验保持暂停。","",
              "## 命令","","```powershell",
              "python forest_benchmark/main.py inspect_source",
              "python forest_benchmark/main.py resolve_bindings A_L3",
              "python forest_benchmark/main.py build_l3_starter A_L3",
              "python forest_benchmark/main.py audit_runtime A_L3 --frames 30",
              "python forest_benchmark/main.py run_integration A_L3",
              "python forest_benchmark/main.py validate_release all",
              "python forest_benchmark/main.py package_model_task A_L3 --review --output path/to/new/review",
              "```","","audit_runtime 当前只运行哈希封存的空接入起始工程副本，不执行任意候选；视频是原森林基线，不是本级最终效果。宿主通过工程外的 public/<任务>/scene_files.json 确定 read 工具可读取的原文件，只允许 solution/scratch 写入。","",
              "[源锁定](author/forest_source_lock.json) · [绑定与运行证据](author/source_audit/native_runtime/result.json) · [L3 汇总 JSON](author/reports/l3/summary.json) · [集成计划](author/l3_plans/)",""]
    (ROOT/"L3_STATUS.md").write_text("\n".join(lines),encoding="utf-8")
    return page,summary


if __name__=="__main__":
    _,summary=assemble();print({k:v for k,v in summary.items() if k!="tasks"})
