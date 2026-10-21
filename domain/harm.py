"""Old-skills harm check for domain mode (design DM3): the parent (ref) against the after-model, on the skills DEV in_dist file.

  python -m domain.harm --ref PARENT --ckpt AFTER --out OUT.json [--dev PATH] [--threads N]

Copied from origin/claude/project-thread-2kevpk (branch of this repo, read with git show):
- harm_measure: creative/harm_look.py, commit 4607c64adbcd1f94b75bedd0816ef3534e0497ca
  ("creative: harm_measure (roadmap e9e0bd2aeb ...)"). Defaults unchanged: family_drop=5.0, in_dist_drop=1.5.
- boot (the paired bootstrap that harm_measure uses): creative/c2_pilot.py, last commit a7fd1e666a9c3461beca712b0b43f7a8c63f9443.
The per-row scoring is harm_look.py's skills_hits: evaluate(..., return_preds=True) and is_hit per row.
Only the DEV in_dist file is read here (the sealed panel is never read by this module).
"""
import argparse
import json
import os
import random

import torch

from custom_io.data import DEFAULT_DATA, load_rows
from custom_io.evalx import evaluate, is_hit
from custom_io.models import load_model


def boot(a, b, iters=2000, seed=0):
    """Paired bootstrap over questions of mean(a) - mean(b), in points. -> (diff, lo, hi) 95%."""
    rng = random.Random(seed)
    n = len(a)
    d = [x - y for x, y in zip(a, b)]
    ms = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(iters))
    return 100 * sum(d) / n, 100 * ms[int(0.025 * iters)], 100 * ms[int(0.975 * iters)]


def harm_measure(hits_a, hits_b, rows, family_drop=5.0, in_dist_drop=1.5):
    """The sleep harm measure (roadmap e9e0bd2aeb): model b against reference a on the same in_dist rows. A family fires when it drops more than `family_drop` points
    AND the paired 95% interval of b - a over its rows is below 0; passes = in_dist drop <= `in_dist_drop` and no family fires."""
    fams = {}
    for i, r in enumerate(rows):
        fams.setdefault(r['family'], []).append(i)
    pct = lambda h, ix: 100 * sum(h[i] for i in ix) / len(ix)
    out, fired = {}, []
    for f, ix in sorted(fams.items()):
        d, lo, hi = boot([hits_b[i] for i in ix], [hits_a[i] for i in ix])
        fires = -d > family_drop and hi < 0
        out[f] = dict(a=pct(hits_a, ix), b=pct(hits_b, ix), drop=-d, lo=lo, hi=hi, fires=fires)
        if fires:
            fired.append(f)
    allix = range(len(rows))
    ia, ib = pct(hits_a, allix), pct(hits_b, allix)
    return dict(in_dist_a=ia, in_dist_b=ib, in_dist_drop=ia - ib, families=out, fired=fired, passes=ia - ib <= in_dist_drop and not fired,
                rule=f'in_dist drop <= {in_dist_drop} and no family with drop > {family_drop} and paired 95% interval below 0')


def in_dist_hits(ckpt, rows):
    """Per-row greedy hits (1 = right) on the DEV in_dist rows, as harm_look.py's skills_hits does it."""
    m = load_model(ckpt).eval()
    e = evaluate(m, rows, 128, 'cpu', return_preds=True)
    return [int(is_hit(e['preds'][r['id']], r)) for r in rows], e['exact']


def main(argv=None):
    a = argparse.ArgumentParser(description='Domain mode DM3: harm check of the after-model against the parent on skills DEV in_dist.')
    a.add_argument('--ref', required=True, help='the parent checkpoint')
    a.add_argument('--ckpt', required=True, help='the after-model checkpoint')
    a.add_argument('--out', required=True)
    a.add_argument('--dev', default=None, help='skills DEV in_dist.jsonl (default: $CUSTOM_IO_DATA or DEFAULT_DATA, dev/in_dist.jsonl)')
    a.add_argument('--threads', type=int, default=4)
    a = a.parse_args(argv)
    torch.set_num_threads(a.threads)
    dev = a.dev or os.path.join(os.environ.get('CUSTOM_IO_DATA', DEFAULT_DATA), 'dev', 'in_dist.jsonl')
    rows = load_rows(dev)
    ref_h, ref_acc = in_dist_hits(a.ref, rows)
    aft_h, aft_acc = in_dist_hits(a.ckpt, rows)
    per_family = {}
    for f in sorted({r['family'] for r in rows}):
        ix = [i for i, r in enumerate(rows) if r['family'] == f]
        per_family[f] = dict(n=len(ix), ref=round(100 * sum(ref_h[i] for i in ix) / len(ix), 2),
                             after=round(100 * sum(aft_h[i] for i in ix) / len(ix), 2))
    harm = harm_measure(ref_h, aft_h, rows, family_drop=5.0, in_dist_drop=1.5)
    out = dict(ref=a.ref, ckpt=a.ckpt, dev=dev, n=len(rows), in_dist_ref_exact=ref_acc, in_dist_after_exact=aft_acc,
               per_family=per_family, per_row=dict(ids=[r['id'] for r in rows], ref=ref_h, after=aft_h), harm=harm)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
    print('in_dist ref', round(harm['in_dist_a'], 2), 'after', round(harm['in_dist_b'], 2), 'drop', round(harm['in_dist_drop'], 2),
          'fired', harm['fired'], 'passes', harm['passes'], flush=True)


if __name__ == '__main__':
    main()
