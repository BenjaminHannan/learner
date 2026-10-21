"""Sealed look-alike panel for the stats help tool (domain/tools/stats.py). The model never sees these rows.

Own generator, own seed (stats 91021). Nothing here imports the practice maker. The only imports from this project are the
stats help tool and the caps and vocabulary from domain/tools. evaluate() gives each row's answer and its step count. A
candidate is redrawn when the tool answers '?', when this file's own Python re-computation (plain arithmetic on the list)
disagrees with the tool, when the step count is over 7, when the answer is over 8 characters, when the prompt is over 208
characters or has a character outside ASCII, when the prompt repeats, or when it equals a help example.

Panel (700 rows = 7 kinds x (60 near + 40 far)):
  near: the help example's list length (3 numbers; 4 for twice the largest); values 1-99.
  far:  list length per kind: product 4-5, half the sum 4-6, largest plus smallest 4, largest times smallest 4,
        twice the largest 5-7, twice the smallest 4-6, sum minus largest 4; values 1-99.

Run from the repo root:  python3 -m domain.panel_lookalike --out DIR
It writes stats.v2.jsonl and a .sha256 for it into DIR, and refuses to replace existing files unless
main(overwrite=True) is called.
"""
import argparse
import hashlib
import json
import math
import os
import random
import re
from collections import Counter

from domain.tools import ASCII, MAX_ANS, MAX_PROMPT, N_NUM, N_RES
from domain.tools import stats as stats_tool

STATS_SEED = 91021
OUT_NAME = 'stats.v2.jsonl'
NEAR_PER_KIND, FAR_PER_KIND = 60, 40
MAX_TRIES = 200000  # a cell not full after this many draws is a bug in the generator, not a slow fill
PREFIX = 'Numbers: '


def numbers_of(prompt):
    """The ints in a stats prompt ('Numbers: 6, 3, 4. ...'). Only for prompts the tool has already accepted."""
    return [int(v) for v in prompt[len(PREFIX):].split('. ', 1)[0].split(', ')]


HELP = stats_tool.help()
KINDS = [h['kind'] for h in HELP]
QUESTION = {h['kind']: h['prompt'].split('. ', 1)[1] for h in HELP}
HELP_PROMPTS = {h['prompt'] for h in HELP}
HELP_LEN = {h['kind']: len(numbers_of(h['prompt'])) for h in HELP}
FAR_LEN = {'product': (4, 5), 'half the sum': (4, 6), 'largest plus smallest': (4, 4),
           'largest times smallest': (4, 4), 'twice the largest': (5, 7), 'twice the smallest': (4, 6),
           'sum minus largest': (4, 4)}
assert KINDS == list(FAR_LEN) and set(QUESTION) == set(KINDS)


def expected(kind, xs):
    """The answer by plain arithmetic on the list, not by the tool. None when the answer is not a whole number."""
    total, big, small = sum(xs), max(xs), min(xs)
    if kind == 'product':
        return math.prod(xs)
    if kind == 'half the sum':
        return total // 2 if total % 2 == 0 else None
    if kind == 'largest plus smallest':
        return big + small
    if kind == 'largest times smallest':
        return big * small
    if kind == 'twice the largest':
        return 2 * big
    if kind == 'twice the smallest':
        return 2 * small
    if kind == 'sum minus largest':
        return total - big
    raise KeyError(kind)


def draw(kind, split, rng):
    """One candidate: (prompt, the answer by Python arithmetic on the list)."""
    n = HELP_LEN[kind] if split == 'near' else rng.randint(*FAR_LEN[kind])
    xs = [rng.randint(1, 99) for _ in range(n)]
    prompt = PREFIX + ', '.join(str(x) for x in xs) + '. ' + QUESTION[kind]
    return prompt, expected(kind, xs)


def build_stats(seed=STATS_SEED, stats=None):
    """The 700 rows, drawn from random.Random(seed). If a dict is passed as stats, it is filled with one Counter per
    (kind, split) cell: the draws, the accepted rows, and why each rejected candidate was redrawn."""
    if stats is None:
        stats = {}
    rng = random.Random(seed)
    rows, seen = [], set()
    for ki, kind in enumerate(KINDS, 1):
        for split, target in (('near', NEAR_PER_KIND), ('far', FAR_PER_KIND)):
            st = Counter()
            stats[(kind, split)] = st
            while st['accepted'] < target:
                st['tries'] += 1
                if st['tries'] > MAX_TRIES:
                    raise RuntimeError(f'stats {kind} {split}: not full after {MAX_TRIES} draws')
                prompt, expect = draw(kind, split, rng)
                res = stats_tool.evaluate(prompt)
                n_steps = len(res['steps'])
                if res['value'] == '?':
                    st['tool ?'] += 1
                elif expect is None or str(expect) != res['value']:
                    st['python disagrees'] += 1
                elif n_steps > N_RES:
                    st['steps over 7'] += 1
                elif len(res['value']) > MAX_ANS:
                    st['answer over 8'] += 1
                elif len(prompt) > MAX_PROMPT:
                    st['prompt over cap'] += 1
                elif not set(prompt + res['value']) <= ASCII:
                    st['non-vocab character'] += 1
                elif prompt in seen:
                    st['duplicate'] += 1
                elif prompt in HELP_PROMPTS:
                    st['help example'] += 1
                else:
                    seen.add(prompt)
                    rows.append({'id': f'stats-{split}-{ki:02d}-{st["accepted"]:03d}', 'domain': 'stats',
                                 'kind': kind, 'split': split, 'prompt': prompt, 'answer': res['value'],
                                 'n_steps': n_steps})
                    st['accepted'] += 1
    return rows


def hard_checks(rows):
    """Every cap and rule, asserted over the whole panel, re-checked from the prompt text. Returns the counts checked."""
    bad, seen = Counter(), set()
    for r in rows:
        p, a, kind = r['prompt'], r['answer'], r['kind']
        xs = numbers_of(p)
        res = stats_tool.evaluate(p)
        if len(p) > MAX_PROMPT:
            bad['prompt over MAX_PROMPT'] += 1
        if len(xs) > N_NUM:
            bad['over N_NUM numbers'] += 1
        if len(a) > MAX_ANS:
            bad['answer over MAX_ANS'] += 1
        if not 1 <= r['n_steps'] <= N_RES:
            bad['steps outside 1..N_RES'] += 1
        if not set(p + a) <= ASCII:
            bad['non-vocab character'] += 1
        if p in seen:
            bad['duplicate prompt'] += 1
        if p in HELP_PROMPTS:
            bad['equals a help example'] += 1
        if not p.endswith(QUESTION[kind]):
            bad['question does not match kind'] += 1
        if r['split'] == 'near' and len(xs) != HELP_LEN[kind]:
            bad['near length not the help length'] += 1
        if r['split'] == 'far' and not FAR_LEN[kind][0] <= len(xs) <= FAR_LEN[kind][1]:
            bad['far length outside the range'] += 1
        if str(expected(kind, xs)) != a:
            bad['answer does not match Python'] += 1
        if res['value'] != a:
            bad['tool does not match the answer'] += 1
        if len(res['steps']) != r['n_steps']:
            bad['n_steps does not match the tool'] += 1
        seen.add(p)
    assert not bad, ('stats', dict(bad))
    return {'rows': len(rows), 'unique_prompts': len(seen), 'violations': sum(bad.values())}


def write_panel(out_dir, name, rows):
    path = os.path.join(out_dir, name)
    data = ''.join(json.dumps(r) + '\n' for r in rows).encode('utf-8')
    with open(path, 'wb') as f:
        f.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with open(path, 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == digest
    with open(path + '.sha256', 'w') as f:
        f.write(f'{digest}  {name}\n')
    return digest


def report(rows, stats):
    print(f'== stats: {len(rows)} rows')
    for (kind, split), st in stats.items():
        reasons = ', '.join(f'{k} {v}' for k, v in st.items() if k not in ('tries', 'accepted') and v)
        steps = Counter(r['n_steps'] for r in rows if r['kind'] == kind and r['split'] == split)
        print(f"  {split:4s} {kind:24s} {st['accepted']:3d} rows, {st['tries']:6d} draws, steps {dict(sorted(steps.items()))}"
              + (f'; rejected: {reasons}' if reasons else ''))
    for (kind, split) in stats:
        for r in [r for r in rows if r['kind'] == kind and r['split'] == split][:3]:
            print(f"  sample {split} {kind}: {r['prompt']}  ->  {r['answer']}  [{r['n_steps']} steps]")


def main(out_dir, overwrite=False):
    """Build, check and write the stats panel into out_dir. Without overwrite=True it refuses to replace existing files."""
    assert (N_NUM, N_RES, MAX_PROMPT, MAX_ANS) == (16, 7, 208, 8)
    for p in (os.path.join(out_dir, OUT_NAME), os.path.join(out_dir, OUT_NAME + '.sha256')):
        if os.path.exists(p) and not overwrite:
            raise SystemExit(f'refusing to overwrite {p}')
    stats = {}
    rows = build_stats(STATS_SEED, stats)
    print('hard checks:', hard_checks(rows))
    report(rows, stats)
    os.makedirs(out_dir, exist_ok=True)
    print(f'sha256 {OUT_NAME}', write_panel(out_dir, OUT_NAME, rows))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Write the sealed stats look-alike panel (stats.v2.jsonl).')
    ap.add_argument('--out', required=True, help='directory to write stats.v2.jsonl and its .sha256 into')
    args = ap.parse_args()
    main(args.out)
