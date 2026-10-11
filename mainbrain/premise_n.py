"""Premise check for arm N (per-example normalised G): are the old examples of the four families seq_next, rule_apply,
verify_claim, passage_qa the ones with small loss gradients at the parent?

  python3 -m mainbrain.premise_n --run RUN --seed N --data DATA --out OUT.json [--threads 1] [--limit K]

Per diary row (run_rows(RUN)[0]): the exact L2 norm of d loss_row / d (weights and biases of gp.projected_modules) at the
parent in eval mode, one row per backward pass (as kf.kfac_stats), plus the model's own loss. The row's real family comes
from DATA/train.jsonl by id (fallback: by prompt)."""
import argparse
import json
import os
import statistics
import time

import torch

from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from mainbrain import common, gp

FOUR = ('seq_next', 'rule_apply', 'verify_claim', 'passage_qa')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=1)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    rows = common.run_rows(a.run)[0]
    if a.limit:
        rows = rows[:a.limit]
    by_id, by_prompt = {}, {}
    for line in open(os.path.join(a.data, 'train.jsonl')):
        r = json.loads(line)
        by_id[r['id']] = r['family']
        by_prompt.setdefault(r['prompt'], r['family'])
    n_id = n_pr = 0
    for r in rows:
        if r['id'] in by_id:
            r['family'], n_id = by_id[r['id']], n_id + 1
        elif r['prompt'] in by_prompt:
            r['family'], n_pr = by_prompt[r['prompt']], n_pr + 1
        else:
            r['family'] = 'unmatched'
    print(f'rows {len(rows)}: matched by id {n_id}, by prompt {n_pr}, unmatched {len(rows) - n_id - n_pr}', flush=True)

    m = load_model(common.parent_of(a.seed))
    for p in m.parameters():
        p.requires_grad_(True)
    m.eval()
    params = [p for _, mod in gp.projected_modules(m) for p in (mod.weight, mod.bias) if p is not None]
    ds = Dataset(rows, m.vocab)
    t0 = time.time()
    out = []
    for i, r in enumerate(rows):
        o = m.loss(to_device(collate([ds[i]]), 'cpu'))
        loss = o[0] if isinstance(o, tuple) else o
        gr = torch.autograd.grad(loss, params, allow_unused=True)
        sq = sum(float((g.double() ** 2).sum()) for g in gr if g is not None)
        out.append(dict(id=r['id'], family=r['family'], grad=sq ** 0.5, loss=float(loss.detach())))
        if i in (49, 199) or (i + 1) % 1000 == 0:
            print(f'  {i + 1} rows, {time.time() - t0:.0f}s', flush=True)
    secs = time.time() - t0

    fams = {}
    for r in out:
        fams.setdefault(r['family'], []).append(r)
    table = {f: dict(n=len(v), mean_grad=statistics.fmean(x['grad'] for x in v), median_grad=statistics.median(x['grad'] for x in v),
                     mean_loss=statistics.fmean(x['loss'] for x in v), four=f in FOUR) for f, v in fams.items()}
    order = sorted(table, key=lambda f: table[f]['median_grad'])
    all_med = statistics.median(table[f]['median_grad'] for f in table)
    four_med = statistics.median(table[f]['median_grad'] for f in FOUR if f in table)
    verdict = four_med < all_med
    print(f'{"family":20s} {"n":>5s} {"mean":>10s} {"median":>10s} {"loss":>8s}')
    for f in order:
        t = table[f]
        print(f'{f:20s} {t["n"]:5d} {t["mean_grad"]:10.4g} {t["median_grad"]:10.4g} {t["mean_loss"]:8.4f} {"<-- four" if t["four"] else ""}')
    print(f'median of the four families\' medians {four_med:.4g}; median over all {len(table)} families\' medians {all_med:.4g}')
    print('PREMISE', 'HOLDS' if verdict else 'FAILS', f'(measure: exact parameter-gradient norm, bs=1, {secs:.0f}s for {len(rows)} rows)')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(dict(run=a.run, seed=a.seed, measure='exact L2 norm of d loss_row/d params of projected modules, bs=1, eval, parent',
                   rows=len(rows), matched_id=n_id, matched_prompt=n_pr, secs=secs, four=FOUR, four_median=four_med,
                   all_median=all_med, holds=verdict, order=order, families=table, per_row=out), open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
