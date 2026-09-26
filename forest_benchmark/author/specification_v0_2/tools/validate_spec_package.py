#!/usr/bin/env python3
"""Validate the Markdown handoff package, not Godot or algorithm correctness.

Usage: python tools/validate_spec_package.py [--root PATH] [--json]
Exit status 0 indicates package consistency only. No external dependencies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

HISTORICAL = {
    '05_来源与边界/forest_integration_constraints_static_audit.md',
    '05_来源与边界/forest_integration_constraint_candidates.json',
    '05_来源与边界/shader_algorithm_scenarios.md',
}


def contract_body(text: str) -> str:
    return '\n'.join(text.splitlines()[1:]).strip()


def validate(root: Path) -> dict:
    errors: list[str] = []
    checks: list[str] = []
    counts: dict[str, int] = {}

    def require(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    def read_json(rel: str) -> dict:
        return json.loads((root / rel).read_text(encoding='utf-8'))

    try:
        manifest = read_json('04_作者侧流程与评测/task_manifest.json')
        tasks = manifest['tasks']
        ids = [t['task_id'] for t in tasks]
        by_id = {t['task_id']: t for t in tasks}
        require(len(ids) == len(set(ids)) == 16, 'Expected 16 unique task IDs.')
        require(manifest['task_count'] == len(ids), 'Task count mismatch.')
        require(len({t['chain'] for t in tasks}) == 5, 'Expected five algorithm chains.')
        l3 = [t for t in tasks if t['level'] == 'L3']
        require(len(l3) == 6, 'Expected six L3 variants.')
        require(set(manifest['defined_l3_tasks']) == {t['task_id'] for t in l3}, 'Defined L3 list mismatch.')
        require(manifest['active_l3_tasks'] == [], 'Specification package must not claim deployed L3 tasks.')
        require(manifest['deployed_task_count'] == 0, 'Specification package must have zero deployed tasks.')
        numeric = sum(t['formal_numeric_cases'] for t in tasks)
        coupling = sum(t['interaction_groups'] for t in tasks)
        integration = sum(t['integration_groups'] for t in tasks)
        require(numeric == manifest['new_numeric_cases_designed'] == 100, 'Expected 100 existing numeric groups.')
        require(coupling == manifest['interaction_groups_designed'] == 25, 'Expected 25 original coupling groups.')
        require(integration == manifest['l3_integration_groups_designed'] == 60, 'Expected 60 new integration groups.')
        require(sum(t['inherited_numeric_cases'] for t in l3) == 120, 'L3 numeric regression count mismatch.')
        require(sum(t['inherited_interaction_groups'] for t in l3) == 30, 'L3 coupling regression count mismatch.')
        public_dir = root / '03_测试模型Prompt/公开契约'
        l3_common = contract_body((public_dir / '01_L3公共接入契约.md').read_text(encoding='utf-8'))
        private_tokens = ('author/references/', 'cases_private/', 'author/mutations/',
                          'source_bindings/', '必须构造的错误对照', 'source_gap')
        for task in tasks:
            tid = task['task_id']
            for key in ('author_spec', 'scene_spec', 'public_contract', 'assembled_model_prompt'):
                p = root / task[key]
                require(p.is_file(), f'{tid}: missing {key}: {p}')
            parent = task['predecessor']
            if parent is not None:
                require(parent in by_id, f'{tid}: unknown predecessor {parent}')
                require(by_id[parent]['chain'] == task['chain'], f'{tid}: wrong predecessor chain')
            require(len(task['cases']) == task['formal_numeric_cases'], f'{tid}: numeric group count mismatch')
            require(len(task['coupling']) == task['interaction_groups'], f'{tid}: coupling group count mismatch')
            prompt = (root / task['assembled_model_prompt']).read_text(encoding='utf-8')
            own = contract_body((root / task['public_contract']).read_text(encoding='utf-8'))
            require(own in prompt, f'{tid}: own public contract not embedded verbatim')
            current = parent
            visited = {tid}
            while current is not None:
                require(current not in visited, f'{tid}: dependency cycle')
                if current in visited or current not in by_id:
                    break
                visited.add(current)
                parent_task = by_id[current]
                ancestor = contract_body((root / parent_task['public_contract']).read_text(encoding='utf-8'))
                require(ancestor in prompt, f'{tid}: missing inherited contract {current}')
                current = parent_task['predecessor']
            for token in private_tokens:
                require(token not in prompt, f'{tid}: private token in model prompt: {token}')
            require(re.search(r'\b[A-E]_L[123](?:_[RS])?-[NGI]\d{2}\b', prompt) is None,
                    f'{tid}: private test ID in prompt')
            if task['level'] == 'L3':
                require(by_id[parent]['level'] == 'L2', f'{tid}: must inherit L2')
                require(l3_common in prompt, f'{tid}: missing common L3 contract')
                require(task['can_deploy'] is False, f'{tid}: source-unverified task marked deployable')
                require(len(task['integration_cases']) == task['integration_groups'] == 10,
                        f'{tid}: must have ten integration groups')
                require(re.search(r'\bF0[1-6]\b', prompt) is None, f'{tid}: diagnostic F-label in public prompt')
                author_spec = (root / task['author_spec']).read_text(encoding='utf-8')
                case_ids = [c['id'] for c in task['integration_cases']]
                require(len(case_ids) == len(set(case_ids)), f'{tid}: duplicate integration IDs')
                for case in task['integration_cases']:
                    require(case['id'] in author_spec, f'{tid}: case missing from author Markdown')
                    require(case['thresholds'] is None, f'{tid}: uncalibrated package contains fabricated thresholds')
                binding = read_json(task['source_binding_template'])
                require(binding['runtime_verified'] is False and binding['can_export_native_task'] is False,
                        f'{tid}: unverified binding incorrectly marked verified')
        checks.append('16 task paths, dependency graph, per-task contracts, prompt embedding and private-field checks')
        checks.append('100 numeric / 25 L2 coupling / 60 L3 integration designs; 120+30 L3 regression executions separated')
        require(by_id['C_L3_R']['predecessor'] == by_id['C_L3_S']['predecessor'] == 'C_L2',
                'C variants must share C_L2 directly.')
        paired = read_json('04_作者侧流程与评测/l3_integration_matrix.json')
        for record in paired['tasks']:
            require(record['integration_groups'] == by_id[record['task_id']]['integration_cases'],
                    f'{record["task_id"]}: integration matrix out of sync')
        compatibility = read_json('04_作者侧流程与评测/v0_1_compatibility_hashes.json')
        for item in compatibility['files']:
            p = root / item['path']
            require(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'],
                    f'v0.1 immutable content changed: {item["path"]}')
        checks.append(f'{len(compatibility["files"])} v0.1 public/snapshot files preserved byte-for-byte')
        release = read_json('04_作者侧流程与评测/release_lock.template.json')
        require(release['status'] == 'BLOCKED_RELEASE', 'Release lock must stay blocked.')
        require(release['benchmark']['active_tasks'] == release['benchmark']['active_l3_tasks'] == [],
                'Release template must not invent active tasks.')
        require(all(v is False for v in release['release_gates'].values()), 'Unexecuted runtime gate marked passed.')
        source = read_json('04_作者侧流程与评测/forest_source_lock.template.json')
        require(not source['original_run_verified'] and source['verified_commit'] is None,
                'Source template must remain unverified.')
        checks.append('Source, runtime and release gates remain explicitly unverified/blocked')
        all_files = [p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        for p in all_files:
            rel = p.relative_to(root).as_posix()
            require(not p.is_symlink(), f'Unexpected symlink: {rel}')
            if p.suffix == '.json':
                json.loads(p.read_text(encoding='utf-8'))
            if p.suffix != '.md' or rel in HISTORICAL:
                continue
            text = p.read_text(encoding='utf-8')
            fence_lines = [ln for ln in text.splitlines() if re.match(r'^\s*```', ln)]
            require(len(fence_lines) % 2 == 0, f'Unbalanced Markdown fences: {rel}')
            without_code = re.sub(r'```.*?```', '', text, flags=re.S)
            for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', without_code):
                target = target.strip().strip('<>')
                if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                path_part = unquote(target.split('#', 1)[0])
                if not path_part:
                    continue
                require((p.parent / path_part).exists(), f'Broken relative link in {rel}: {target}')
        checks.append('JSON syntax, new/maintained Markdown fences and relative links')
        index_path = root / 'PACKAGE_INDEX.json'
        if index_path.exists():
            index = read_json('PACKAGE_INDEX.json')
            for item in index['files']:
                p = root / item['path']
                require(p.is_file(), f'Index file missing: {item["path"]}')
                if p.is_file():
                    require(hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'],
                            f'Index digest mismatch: {item["path"]}')
            actual = {p.relative_to(root).as_posix() for p in all_files if p != index_path}
            require(actual == {item['path'] for item in index['files']}, 'Package index coverage mismatch')
            checks.append('Package index coverage and SHA-256 digests')
        counts = dict(tasks=len(tasks),l3_tasks=len(l3),numeric_design_groups=numeric,
                      l2_coupling_design_groups=coupling,l3_integration_design_groups=integration,
                      markdown_files=sum(p.suffix == '.md' for p in all_files),
                      json_files=sum(p.suffix == '.json' for p in all_files),files=len(all_files))
    except (OSError, KeyError, ValueError, TypeError) as exc:
        errors.append(f'Validation could not finish: {type(exc).__name__}: {exc}')
    return dict(status='PASS' if not errors else 'FAIL',scope='STATIC_PACKAGE_ONLY_NOT_GODOT_OR_NUMERIC_VALIDATION',
                counts=counts,checks=checks,errors=errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--json', action='store_true', help='Emit JSON to stdout; no files are modified.')
    args = parser.parse_args()
    result = validate(args.root.resolve())
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f'{result["status"]}: static package consistency only')
        print(json.dumps(result['counts'], ensure_ascii=False))
        for line in result['checks']:
            print('CHECK:', line)
        for line in result['errors']:
            print('ERROR:', line, file=sys.stderr)
        print('Godot, source bindings, numerical tests, renders and release calibration were NOT run.')
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
