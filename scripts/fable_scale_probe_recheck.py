"""Standard-library re-check of the scale probe's summary counts.

Imports nothing but the standard library (no torch, no project modules): it
re-derives every reported count from the raw per-question records and compares
with the stored per-level counts and with summary.json. Writes recheck.json and
exits non-zero on any disagreement.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def checkout_root():
    override = os.environ.get('FABLE_SCALE_PROBE_REPO')
    if override:
        return Path(override).resolve()
    here = str(Path(__file__).resolve().parents[1])
    return Path(here.split('/.claude/worktrees/')[0])


OUT = checkout_root() / 'artifacts/fable-scale-probe-20260920'
CUTOFF = 461
ENTITY_MIN, ENTITY_MAX = 52, 68


def first_failure(emitted, truth):
    for j, t in enumerate(truth):
        if j >= len(emitted) or emitted[j] != t:
            return j
    return -1


def recompute(level, questions, records):
    n, k = len(questions), level['k']
    by_index = {r['index']: r for r in records}
    assert len(by_index) == n, 'record indices are not unique'
    counts = dict(n=n, R=0, M=0, path=0, abort=0, R_correct_path_wrong=0,
                  stage_oracle=[0] * k, first_fail={})
    splits = {'revisits': dict(n=0, R=0, M=0, path=0), 'simple': dict(n=0, R=0, M=0, path=0)}
    by_distinct = {}
    for q in questions:
        r = by_index[q['index']]
        truth = q['truth_path']
        assert len(truth) == k
        assert q['target'] == truth[-1]
        ok_r = int(r['R'] == q['target'])
        ok_m = int(r['M'] == q['target'])
        ok_path = int(r['emitted'] == truth)
        # structural consistency of the executor trace
        assert len(r['oracle']) == k
        assert len(r['emitted']) <= k
        if len(r['emitted']) < k:
            assert r['R'] == -1, 'short trace without an abort'
            assert not ENTITY_MIN <= r['emitted'][-1] < ENTITY_MAX, 'abort on an entity token'
        else:
            assert r['R'] == r['emitted'][-1], 'R is not the final emission'
        counts['R'] += ok_r
        counts['M'] += ok_m
        counts['path'] += ok_path
        counts['abort'] += int(r['R'] == -1)
        counts['R_correct_path_wrong'] += int(ok_r and not ok_path)
        for j in range(k):
            counts['stage_oracle'][j] += int(r['oracle'][j] == truth[j])
        if not ok_r:
            key = str(first_failure(r['emitted'], truth))
            counts['first_fail'][key] = counts['first_fail'].get(key, 0) + 1
        bucket = splits['revisits' if q['revisits'] else 'simple']
        bucket['n'] += 1
        bucket['R'] += ok_r
        bucket['M'] += ok_m
        bucket['path'] += ok_path
        bucket = by_distinct.setdefault(str(q['distinct_people']), dict(n=0, R=0))
        bucket['n'] += 1
        bucket['R'] += ok_r
    counts['splits'] = splits
    counts['by_distinct_people'] = by_distinct
    product = 1.0
    for c in counts['stage_oracle']:
        product *= c / n
    counts['stage_oracle_rate'] = [c / n for c in counts['stage_oracle']]
    counts['compounding_prediction'] = product * n
    counts['broken'] = counts['R'] < CUTOFF
    return counts


def close(a, b):
    return isinstance(a, float) and isinstance(b, float) and abs(a - b) <= 1e-9 * max(1.0, abs(a))


def differences(path, stored, mine):
    out = []
    keys = set(stored) | set(mine)
    for key in sorted(keys):
        a, b = stored.get(key), mine.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            out += differences(f'{path}.{key}', a, b)
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y and not close(x, y):
                    out.append(f'{path}.{key}[{i}]: {x} != {y}')
        elif a != b and not close(a, b):
            out.append(f'{path}.{key}: {a!r} != {b!r}')
    return out


def main():
    levels_dir = OUT / 'levels'
    files = sorted(levels_dir.glob('*.json'))
    if not files:
        print('no level files found', file=sys.stderr)
        return 1
    problems, checked_levels, checked_records = [], 0, 0
    recomputed = {}
    for path in files:
        payload = json.loads(path.read_text())
        level, questions = payload['level'], payload['questions']
        recomputed[level['id']] = {}
        for seed, block in payload['seeds'].items():
            mine = recompute(level, questions, block['records'])
            recomputed[level['id']][seed] = mine
            problems += differences(f'{level["id"]}/seed{seed}', block['counts'], mine)
            checked_records += len(block['records'])
        checked_levels += 1
    summary_path = OUT / 'summary.json'
    summary_problems = []
    if summary_path.exists():
        summary = json.loads(summary_path.read_text())
        for lid, row in summary['levels'].items():
            for seed, counts in row['counts'].items():
                mine = recomputed.get(lid, {}).get(seed)
                if mine is None:
                    summary_problems.append(f'{lid}/seed{seed}: in summary but not recomputed')
                    continue
                summary_problems += differences(f'summary/{lid}/seed{seed}', counts, mine)
        # independently re-derive the first breaking level per seed and axis
        derived = {}
        for seed in summary['seeds']:
            s = str(seed)
            derived[s] = {}
            for lid, row in summary['levels'].items():
                level = row['level']
                axis = (f"hops/people{level['people']}/{level['relation']}"
                        if level['filler_mult'] == 1 else None)
                if axis and 'hops' in level['axes']:
                    derived[s].setdefault(axis, [])
                if 'distraction' in level['axes']:
                    derived[s].setdefault(f"distraction/k{level['k']}/{level['relation']}", [])
            for lid, row in summary['levels'].items():
                level, counts = row['level'], row['counts'].get(s)
                if not counts:
                    continue
                broken = recomputed[lid][s]['R'] < CUTOFF
                if 'hops' in level['axes'] and level['filler_mult'] == 1:
                    derived[s][f"hops/people{level['people']}/{level['relation']}"].append(
                        (level['k'], broken))
                if 'distraction' in level['axes']:
                    derived[s][f"distraction/k{level['k']}/{level['relation']}"].append(
                        (level['filler_mult'], broken))
            for axis, rows in derived[s].items():
                first = next((x for x, broken in sorted(rows) if broken), None)
                if summary['first_breaking'].get(s, {}).get(axis) != first:
                    summary_problems.append(
                        f'first_breaking/{s}/{axis}: {summary["first_breaking"][s][axis]} != {first}')
    report = dict(levels_checked=checked_levels, records_checked=checked_records,
                  level_count_mismatches=problems, summary_mismatches=summary_problems,
                  cutoff=CUTOFF, stdlib_only=True,
                  passed=not problems and not summary_problems)
    (OUT / 'recheck.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(levels_checked=checked_levels, records_checked=checked_records,
                          level_mismatches=len(problems), summary_mismatches=len(summary_problems),
                          passed=report['passed'])), flush=True)
    for line in (problems + summary_problems)[:40]:
        print('  ' + line, file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
