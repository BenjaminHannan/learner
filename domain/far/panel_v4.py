"""v10 (addendum A30): a fresh draw of the sheet panel, sheet.v4.jsonl: the same near and far splits as v1-v3 (domain/panel.py's
generator, counts and checks, a new seed) plus a join split, the test joins of the far-transfer probes (sheet_probe's F4-two:
a near grid, two of the seven scored kinds joined by + or *, partner kind a different one), 60 rows per scored kind.

  python3 -m domain.far.panel_v4        (refuses to overwrite)

Join rows are built by sheet_probe.candidate (independent of the mode's join-last maker) and checked by sheet_probe.check against the
help prompts, every older sealed panel, the lab probe and eval rows when their files exist, and each other.
"""
import glob
import json
import os
import random

from domain import panel
from domain.far import sheet_probe as SP
from domain.tools import sheet as sheet_tool

V4_SEED, V4_JOIN_SEED, JOIN_PER_KIND = 91031, 91032, 60
NAME = 'sheet.v4.jsonl'
LAB_ROWS = ('/mnt/project-files/far-transfer/diag/sheet-probe.jsonl',
            '/mnt/project-files/far-transfer/learn/eval-rows-l5.jsonl')


def prompts_of(path):
    with open(path) as f:
        return {json.loads(line)['prompt'] for line in f if line.strip()}


def older_prompts():
    out = set()
    for name in ('sheet.jsonl', 'sheet.v2.jsonl', 'sheet.v3.jsonl'):
        out |= prompts_of(os.path.join(panel.OUT_DIR, name))
    for path in LAB_ROWS + tuple(glob.glob('/mnt/project-files/far-transfer/learn/train-rows-l*.jsonl')):
        if os.path.exists(path):
            out |= prompts_of(path)
    return out


def build_join(avoid, rng):
    """-> (rows, stats): JOIN_PER_KIND F4-two rows per scored kind, split 'join'."""
    help_prompts = {h['prompt'] for h in sheet_tool.help()}
    rows, stats, seen = [], {}, set()
    for ki, kind in enumerate(SP.SCORED, 1):
        st = {'accepted': 0, 'tries': 0}
        while st['accepted'] < JOIN_PER_KIND:
            st['tries'] += 1
            if st['tries'] > SP.MAX_TRIES:
                raise RuntimeError(f'{kind}: join split not full after {SP.MAX_TRIES} draws')
            prompt, fn, g, formula = SP.candidate(kind, 'F4-two', rng)
            reason, res = SP.check(prompt, fn(g), help_prompts, avoid, seen)
            if reason:
                st[reason] = st.get(reason, 0) + 1
                continue
            seen.add(prompt)
            rows.append({'id': f'sheet-join-{ki:02d}-{st["accepted"]:03d}', 'domain': 'sheet', 'kind': kind, 'split': 'join',
                         'prompt': prompt, 'answer': res['value'], 'n_steps': len(res['steps'])})
            st['accepted'] += 1
        stats[kind] = st
    return rows, stats


def main():
    for p in (os.path.join(panel.OUT_DIR, NAME), os.path.join(panel.OUT_DIR, NAME + '.sha256')):
        if os.path.exists(p):
            raise SystemExit(f'refusing to overwrite {p}')
    sheet_rows, sheet_stats = panel.build_sheet(V4_SEED)
    old = older_prompts()
    print('v4 near/far prompts also in an older draw or lab file:', sum(r['prompt'] in old for r in sheet_rows))
    join_rows, join_stats = build_join(old | {r['prompt'] for r in sheet_rows}, random.Random(V4_JOIN_SEED))
    help_prompts = {h['prompt'] for h in sheet_tool.help()}
    print('hard checks near/far:', panel.hard_checks('sheet', sheet_rows, help_prompts))
    print('hard checks join:', panel.hard_checks('sheet-join', join_rows, help_prompts))
    panel.report('sheet', sheet_rows, sheet_stats)
    for kind, st in join_stats.items():
        print(f'  join {kind:16s} {st}')
    rows = sheet_rows + join_rows
    assert len({r['prompt'] for r in rows}) == len(rows), 'duplicate prompt across splits'
    print('sha256', NAME, panel.write_panel(NAME, rows), 'rows', len(rows))


if __name__ == '__main__':
    main()
