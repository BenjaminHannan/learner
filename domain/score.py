"""Score domain checkpoints on a sealed panel. Scoring only: the model never sees the panel (domain/mode.py never reads it).

  python -m domain.score --ckpt CKPT --panel PATH.jsonl --out OUT.json
  python -m domain.score --all-nights DIR --panel PATH.jsonl --out OUT.json [--ckpt PARENT]

Panel rows (jsonl): id, prompt, answer, kind, split ('near' or 'far'); optional accepted (default [answer]).
Greedy answers with the calculator on (the model's only tool). A row is a hit when the answer, stripped, equals one
of the accepted answers, stripped. Output: per run, accuracy overall, by split, and by kind x split (percent).
"""
import argparse
import glob
import json
import os
import re
from collections import Counter

import torch

from custom_io.models import load_model
from domain.mode import greedy


def load_panel(path):
    rows = [json.loads(line) for line in open(path) if line.strip()]
    for r in rows:
        for k in ('id', 'prompt', 'answer', 'kind', 'split'):
            assert k in r, f'panel row {r.get("id")} has no {k}'
    return rows


def score(ckpt, rows, label, threads=None):
    m = load_model(ckpt).eval()
    res = greedy(m, [r['prompt'] for r in rows])
    out_rows = []
    for r, (_, pred) in zip(rows, res):
        acc = {x.strip() for x in r.get('accepted', [r['answer']])}
        out_rows.append(dict(id=r['id'], kind=r['kind'], split=r['split'], pred=pred, hit=int(pred.strip() in acc)))
    pct = lambda hs: round(100.0 * sum(hs) / len(hs), 2) if hs else None
    by_split = {s: pct([x['hit'] for x in out_rows if x['split'] == s]) for s in sorted({x['split'] for x in out_rows})}
    by_kind_split = {}
    for kind in sorted({x['kind'] for x in out_rows}):
        by_kind_split[kind] = {s: pct([x['hit'] for x in out_rows if x['kind'] == kind and x['split'] == s]) for s in by_split}
    return dict(label=label, ckpt=ckpt, n=len(out_rows), overall=pct([x['hit'] for x in out_rows]), by_split=by_split,
                by_kind_split=by_kind_split, rows=out_rows)


def night_checkpoints(d):
    found = []
    for p in glob.glob(os.path.join(d, 'night_*', 'checkpoint.pt')):
        k = re.search(r'night_(\d+)', p)
        found.append((int(k.group(1)), p))
    return sorted(found)


def main(argv=None):
    a = argparse.ArgumentParser(description='Score domain checkpoints on a sealed panel (scoring only).')
    a.add_argument('--ckpt', help='one checkpoint to score')
    a.add_argument('--all-nights', help='a DIR with night_K/checkpoint.pt files: score every one')
    a.add_argument('--panel', required=True, help='panel jsonl (scoring only)')
    a.add_argument('--out', required=True)
    a.add_argument('--threads', type=int, default=4)
    a = a.parse_args(argv)
    assert a.ckpt or a.all_nights, 'give --ckpt, --all-nights or both'
    torch.set_num_threads(a.threads)
    rows = load_panel(a.panel)
    runs = []
    if a.ckpt:
        runs.append(score(a.ckpt, rows, 'ckpt'))
        print('ckpt', runs[-1]['overall'], runs[-1]['by_split'], flush=True)
    if a.all_nights:
        for k, path in night_checkpoints(a.all_nights):
            runs.append(score(path, rows, f'night_{k}'))
            print(f'night_{k}', runs[-1]['overall'], runs[-1]['by_split'], flush=True)
    out = dict(panel=a.panel, n=len(rows), kinds=dict(Counter(r['kind'] for r in rows)), runs=runs)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
    print('wrote', a.out, flush=True)


if __name__ == '__main__':
    main()
