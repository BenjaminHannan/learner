"""Sealed scoring panel for the invoice help tool (domain/tools/invoice.py). The model never sees these rows.

Own generator, own seed (invoice 91022). Nothing here imports the practice maker. The only imports from this project
are the help tool's caps, its vocabulary and its evaluate(). The answers are also re-computed in this file in plain
Python, so a tool bug shows up as a disagreement instead of a silent answer.

Invoice panel (600 rows = 6 kinds x (60 near + 40 far)), kinds in help order:
  near: the help example's row names and question; every qty randint(1, 9) and every price randint(1, 99).
  far:  the help example's three rows plus a fourth row 'Row wagon: qty Q, price P.' after them (same question),
        values drawn as for near.

A candidate is redrawn when the tool answers '?', when this file's own Python answer disagrees with the tool, when the
step count is over 7, when the answer is longer than 8 characters, when the prompt is longer than 208, when the row
count is wrong for the split, when a character is not in the tool's vocabulary, when the prompt repeats, or when the
prompt equals a help example.

Run from the repo root:  python3 -m domain.panel_invoice --out DIR
It writes invoice.v2.jsonl and invoice.v2.jsonl.sha256 into DIR, and refuses to replace existing files unless
main(out_dir, overwrite=True) is called.
"""
import argparse
import hashlib
import json
import os
import random
import re
from collections import Counter

from domain.tools import ASCII, BIG, MAX_ANS, MAX_PROMPT, N_NUM, N_RES
from domain.tools import invoice as invoice_tool

SEED = 91022
OUT_NAME = 'invoice.v2.jsonl'
NEAR_PER_KIND, FAR_PER_KIND = 60, 40
MAX_TRIES = 200000  # a cell not full after this many draws is a bug in the generator, not a slow fill
ROWS = {'near': 3, 'far': 4}
FAR_EXTRA = 'wagon'  # the fourth row in far prompts; no help example uses this name

INVOICE_KINDS = ['price sum', 'two rows cost', 'largest qty', 'smallest price', 'cost difference', 'twice qty sum']
ROW_RE = re.compile(r'Row ([a-z]+): qty [0-9]+, price [0-9]+\.')
# The two-name questions: the panel's own parse of which rows the question compares (a first, then b).
PAIR_RE = {'two rows cost': re.compile(r'What is the total cost of rows ([a-z]+) and ([a-z]+)\?'),
           'cost difference': re.compile(r'How much more is the cost of row ([a-z]+) than row ([a-z]+)\?')}


def help_parts(prompt):
    """The row names and the question of one help example, e.g. (['zipper', 'hammer', 'pocket'], 'What is ...?')."""
    names, rest = [], prompt
    m = ROW_RE.match(rest)
    while m is not None:
        names.append(m.group(1))
        rest = rest[m.end():].lstrip(' ')
        m = ROW_RE.match(rest)
    return names, rest


def draw(kind, split, rng, spec):
    """One candidate: (prompt, rows, question). rows are (name, qty, price) in prompt order."""
    names, question = spec[kind]
    if split == 'far':
        names = names + [FAR_EXTRA]
    rows = [(n, rng.randint(1, 9), rng.randint(1, 99)) for n in names]
    prompt = ' '.join(f'Row {n}: qty {q}, price {p}.' for n, q, p in rows) + ' ' + question
    return prompt, rows, question


def expected(kind, rows, question):
    """This file's own answer, in plain Python: no calculator and no tool."""
    cost = {n: q * p for n, q, p in rows}
    if kind == 'price sum':
        return sum(p for _, _, p in rows)
    if kind == 'largest qty':
        return max(q for _, q, _ in rows)
    if kind == 'smallest price':
        return min(p for _, _, p in rows)
    if kind == 'twice qty sum':
        return 2 * sum(q for _, q, _ in rows)
    a, b = PAIR_RE[kind].fullmatch(question).groups()
    if kind == 'two rows cost':
        return cost[a] + cost[b]
    return cost[a] - cost[b]  # cost difference: a negative value is a '?' from the tool, which is redrawn first


def fill(rng, spec, evaluate, help_prompts):
    """Draw until every (kind, split) cell is full. Returns (rows, per-cell stats)."""
    rows, stats, seen = [], {}, set()
    for ki, kind in enumerate(INVOICE_KINDS, 1):
        for split, target in (('near', NEAR_PER_KIND), ('far', FAR_PER_KIND)):
            st = Counter()
            while st['accepted'] < target:
                st['tries'] += 1
                if st['tries'] > MAX_TRIES:
                    raise RuntimeError(f'invoice {kind} {split}: not full after {MAX_TRIES} draws')
                prompt, row_list, question = draw(kind, split, rng, spec)
                res = evaluate(prompt)
                steps = len(res['steps'])
                if res['value'] == '?':
                    st['tool ?'] += 1
                elif str(expected(kind, row_list, question)) != res['value']:
                    st['python disagrees'] += 1
                elif steps > N_RES:
                    st['steps over 7'] += 1
                elif len(res['value']) > MAX_ANS:
                    st['answer over 8'] += 1
                elif len(prompt) > MAX_PROMPT:
                    st['prompt over cap'] += 1
                elif prompt.count('Row ') != ROWS[split]:
                    st['shape'] += 1
                elif not set(prompt + res['value']) <= ASCII:
                    st['non-vocab character'] += 1
                elif prompt in help_prompts:
                    st['help example'] += 1
                elif prompt in seen:
                    st['duplicate'] += 1
                else:
                    seen.add(prompt)
                    rows.append({'id': f'invoice-{split}-{ki:02d}-{st["accepted"]:03d}', 'domain': 'invoice',
                                 'kind': kind, 'split': split, 'prompt': prompt, 'answer': res['value'],
                                 'n_steps': steps})
                    st['accepted'] += 1
            stats[(kind, split)] = st
    return rows, stats


def build_invoice(seed=SEED, stats=None):
    """The invoice panel rows for one seed (600 rows). Pass a dict as stats to receive the per-cell counts."""
    rng = random.Random(seed)
    help_list = invoice_tool.help()
    assert [h['kind'] for h in help_list] == INVOICE_KINDS
    spec = {}
    for h in help_list:
        names, question = help_parts(h['prompt'])
        assert len(names) == ROWS['near'] and FAR_EXTRA not in names, h['kind']
        spec[h['kind']] = (names, question)
    help_prompts = {h['prompt'] for h in help_list}
    rows, cell_stats = fill(rng, spec, invoice_tool.evaluate, help_prompts)
    if stats is not None:
        stats.update(cell_stats)
    return rows


def hard_checks(rows, help_prompts):
    """Every cap and rule, checked over the whole panel. Returns the counts it checked."""
    bad, seen = Counter(), set()
    for r in rows:
        p, a = r['prompt'], r['answer']
        if len(p) > MAX_PROMPT:
            bad['prompt over MAX_PROMPT'] += 1
        if len(re.findall(r'[0-9]+', p)) > N_NUM:
            bad['over N_NUM numbers'] += 1
        if len(a) > MAX_ANS:
            bad['answer over MAX_ANS'] += 1
        if not 1 <= r['n_steps'] <= N_RES:
            bad['steps outside 1..N_RES'] += 1
        if not set(p + a) <= ASCII:
            bad['non-vocab character'] += 1
        if p in seen:
            bad['duplicate prompt'] += 1
        if p in help_prompts:
            bad['equals a help example'] += 1
        seen.add(p)
    if bad:
        raise RuntimeError(('invoice panel breaks a rule', dict(bad)))
    return {'rows': len(rows), 'unique_prompts': len(seen), 'violations': sum(bad.values())}


def write_panel(out_dir, name, rows):
    path = os.path.join(out_dir, name)
    data = ''.join(json.dumps(r) + '\n' for r in rows).encode('utf-8')
    with open(path, 'wb') as f:
        f.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with open(path, 'rb') as f:
        if hashlib.sha256(f.read()).hexdigest() != digest:
            raise RuntimeError(f'{path} does not read back the same bytes')
    with open(path + '.sha256', 'w') as f:
        f.write(f'{digest}  {name}\n')
    return digest


def report(rows, stats):
    print(f'== invoice: {len(rows)} rows')
    for (kind, split), st in stats.items():
        reasons = ', '.join(f'{k} {v}' for k, v in st.items() if k not in ('tries', 'accepted') and v)
        steps = Counter(r['n_steps'] for r in rows if r['kind'] == kind and r['split'] == split)
        print(f"  {split:4s} {kind:16s} {st['accepted']:3d} rows, {st['tries']:6d} draws, steps {dict(sorted(steps.items()))}"
              + (f'; rejected: {reasons}' if reasons else ''))
    for (kind, split) in stats:
        for r in [r for r in rows if r['kind'] == kind and r['split'] == split][:3]:
            print(f"  sample {split} {kind}: {r['prompt']}  ->  {r['answer']}  [{r['n_steps']} steps]")


def main(out_dir, overwrite=False):
    """Build, check and write the invoice panel into out_dir. Without overwrite=True it refuses to replace existing files."""
    assert (N_NUM, N_RES, MAX_PROMPT, MAX_ANS) == (16, 7, 208, 8)
    for p in (os.path.join(out_dir, OUT_NAME), os.path.join(out_dir, OUT_NAME + '.sha256')):
        if os.path.exists(p) and not overwrite:
            raise SystemExit(f'refusing to overwrite {p}')
    stats = {}
    rows = build_invoice(SEED, stats)
    help_prompts = {h['prompt'] for h in invoice_tool.help()}
    print('hard checks:', hard_checks(rows, help_prompts))
    report(rows, stats)
    os.makedirs(out_dir, exist_ok=True)
    print(f'sha256 {OUT_NAME}', write_panel(out_dir, OUT_NAME, rows))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Write the sealed invoice panel (invoice.v2.jsonl).')
    ap.add_argument('--out', required=True, help='directory to write into')
    args = ap.parse_args()
    main(args.out)
