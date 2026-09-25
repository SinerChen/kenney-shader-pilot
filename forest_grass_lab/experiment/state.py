"""Small local state machine. No agent framework, shell tool, or automatic visual score."""
import difflib
import json
from pathlib import Path
import re


def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def checked_probe(args, variant):
    """Only data-driven set/step; never accept arbitrary URL, path or browser JS."""
    scene = args.get('scene', 'target')
    if not isinstance(scene, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,40}', scene):
        raise ValueError('scene must be target or a safe lowercase slug')
    if variant in ('P1', 'P3') and scene != 'target':
        raise ValueError(f'{variant} permits only the target scene')
    params, frames, schedule = args.get('params', {}), args.get('frames', [1]), args.get('schedule', [])
    if not isinstance(params, dict):
        raise ValueError('params must be an object')
    if (not isinstance(frames, list) or not 1 <= len(frames) <= 3
            or any(type(n) is not int or not 1 <= n <= 90 for n in frames)
            or frames != sorted(set(frames))):
        raise ValueError('frames must contain 1–3 strictly increasing integers in [1,90]')
    if not isinstance(schedule, list) or len(schedule) > 90:
        raise ValueError('schedule must contain at most 90 updates')
    seen = set()
    for item in schedule:
        if (not isinstance(item, dict) or set(item) != {'frame', 'set'}
                or type(item['frame']) is not int or not 1 <= item['frame'] <= max(frames)
                or item['frame'] in seen or not isinstance(item['set'], dict)):
            raise ValueError('schedule needs unique frame numbers within the captured interval and set objects')
        seen.add(item['frame'])
    if len(json.dumps([params, schedule], allow_nan=False)) > 16000:
        raise ValueError('probe parameters exceed the pilot size limit')
    return dict(scene=scene, params=params, frames=frames, schedule=sorted(schedule, key=lambda x: x['frame']))


def compact_report(report):
    def brief(items):
        unique = list(dict.fromkeys(map(str, items)))
        return dict(total=len(items), unique=len(unique), samples=[s[:500] for s in unique[:8]])
    return dict(execution_ok=bool(report.get('execution_ok')),
                errors=brief(report.get('errors', [])), warnings=brief(report.get('warnings', [])),
                cases=[dict(name=c['name'], frames=c.get('frames', [])) for c in report.get('cases', [])],
                note='Execution only. No visual score. Full logs and original PNGs are saved locally.')


class State:
    def __init__(self, out, variant):
        self.out, self.variant = Path(out), variant
        self.main = self.out / 'grass.gdshader'
        self.main.write_text('', encoding='utf-8')
        self.steps, self.index, self.revision, self.checks, self.judgements = [], 0, 0, [], []
        self.submitted = False
        self.persist()

    def code(self):
        return self.main.read_text(encoding='utf-8')

    def current(self):
        return self.steps[self.index] if self.index < len(self.steps) else None

    def view(self):
        return dict(variant=self.variant, current=self.current(), index=self.index, total=len(self.steps),
                    revision=self.revision, submitted=self.submitted)

    def persist(self):
        save_json(self.out / 'state.json', dict(**self.view(), steps=self.steps, checks=self.checks,
                                              judgements=self.judgements))

    def active(self, args):
        step = self.current()
        if not step or args.get('step_id') != step['id']:
            raise ValueError('Tool must address the current unfinished step_id')
        return step

    def plan(self, args):
        if self.steps:
            raise ValueError('Plan is already fixed for this pilot')
        steps = args.get('steps')
        if not isinstance(steps, list) or not 4 <= len(steps) <= 8:
            raise ValueError('Plan must contain 4–8 steps')
        ids = set()
        for s in steps:
            if not isinstance(s, dict) or set(s) != {'id', 'goal', 'acceptance', 'tags'}:
                raise ValueError('Each step needs exactly id, goal, acceptance, tags')
            if not isinstance(s['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', s['id']) or s['id'] in ids:
                raise ValueError('Step ids must be unique safe identifiers')
            if (not isinstance(s['goal'], str) or not s['goal'].strip()
                    or not isinstance(s['acceptance'], list) or not s['acceptance']
                    or any(not isinstance(x, str) or not x.strip() for x in s['acceptance'])
                    or not isinstance(s['tags'], list) or any(not isinstance(x, str) for x in s['tags'])):
                raise ValueError('Invalid goal, acceptance criteria or tags')
            ids.add(s['id'])
        self.steps = json.loads(json.dumps(steps, ensure_ascii=False))
        save_json(self.out / 'plan.json', self.steps)
        return dict(ok=True, state=self.view())

    def update(self, args):
        step = self.active(args)
        before = self.code()
        if type(args.get('base_revision')) is not int or args['base_revision'] != self.revision:
            raise ValueError('Stale base_revision; read_main and rebuild the patch')
        if not isinstance(args.get('reason'), str) or not args['reason'].strip():
            raise ValueError('State the reason for this code change')
        if ('code' in args) == ('edits' in args):
            raise ValueError('Supply exactly one of code or edits')
        if 'code' in args:
            after = args['code']
        else:
            edits, after = args['edits'], before
            if not isinstance(edits, list) or not edits:
                raise ValueError('edits must be nonempty')
            for edit in edits:
                if (not isinstance(edit, dict) or set(edit) != {'old', 'new'}
                        or not isinstance(edit['old'], str) or not edit['old']
                        or not isinstance(edit['new'], str)):
                    raise ValueError('Each edit needs a nonempty old string and a new string')
                if after.count(edit['old']) != 1:
                    raise ValueError('Each old string must match exactly once; no fuzzy replacement')
                after = after.replace(edit['old'], edit['new'], 1)
        if not isinstance(after, str) or not after.strip() or len(after) > 500000 or after == before:
            raise ValueError('Code must be nonempty, changed, and at most 500000 characters')
        # All replacements have been checked before any write; no partial patch application.
        folder = self.out / 'steps' / step['id']
        folder.mkdir(parents=True, exist_ok=True)
        revision = self.revision + 1
        (folder / f'{revision:03d}.gdshader').write_text(after, encoding='utf-8')
        lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                     fromfile='a/grass.gdshader', tofile='b/grass.gdshader')
        # Keep review patches valid even if either source has no trailing newline.
        diff = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
                       for line in lines)
        (folder / f'{revision:03d}.diff').write_text(diff, encoding='utf-8')
        temporary = self.main.with_suffix('.tmp')
        temporary.write_text(after, encoding='utf-8')
        temporary.replace(self.main)
        self.revision = revision
        return dict(ok=True, state=self.view())

    def finish(self, args):
        step = self.active(args)
        verdict = args.get('verdict')
        if verdict not in ('pass', 'fail', 'inconclusive'):
            raise ValueError('verdict must be pass/fail/inconclusive')
        if not isinstance(args.get('summary'), str) or not args['summary'].strip() or not isinstance(args.get('limitations'), str):
            raise ValueError('summary and limitations are required')
        evidence = args.get('evidence')
        if not isinstance(evidence, list) or any(not isinstance(x, str) for x in evidence):
            raise ValueError('evidence must be a list of actual check ids')
        valid = {c['id']: c for c in self.checks
                 if c['step_id'] == step['id'] and c['revision'] == self.revision}
        if any(e not in valid for e in evidence):
            raise ValueError('Evidence must exist and match this step AND the current code version')
        if verdict == 'pass':
            successful = [valid[e] for e in evidence if valid[e]['execution_ok']]
            if not any(c['kind'] == 'step' and c['scene'] == 'target'
                       and (self.variant == 'P1' or c.get('images_sent')) for c in successful):
                raise ValueError('Need a successful target-scene step check for this version')
            if self.variant == 'P2' and not any(c['kind'] == 'step' and c['scene'] != 'target'
                                              and c.get('images_sent') for c in successful):
                raise ValueError('P2 also needs successful minimal-scene evidence with image feedback')
            if self.index == len(self.steps) - 1 and not any(c['kind'] == 'public' for c in successful):
                raise ValueError('The final step also needs current-version public execution evidence')
        self.judgements.append(dict(**args, revision=self.revision))
        if verdict == 'pass':
            self.index += 1
        return dict(ok=True, state=self.view(), note='Stage judgement is model self-assessment, not ground truth.')

    def submit(self):
        if not self.steps or self.current() is not None:
            raise ValueError('Finish the current plan first')
        if not any(c['kind'] == 'public' and c['revision'] == self.revision and c['execution_ok'] for c in self.checks):
            raise ValueError('Current code lacks a successful public execution check')
        self.submitted = True
        return dict(ok=True, state=self.view(), note='Submitted is not visually passed.')
