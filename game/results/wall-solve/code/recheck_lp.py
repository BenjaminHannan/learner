"""Optional end check (not part of result.json): re-run play.move_logprobs over an evenly spaced sample of recorded views and compare the argmax
with the log-probs recorded during play. python recheck_lp.py SEED [--root DIR] [--n 4000]"""
import argparse, gzip, json, os, sys
import numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from game import play
from custom_io.models import load_model

ap = argparse.ArgumentParser()
ap.add_argument('seed', type=int)
ap.add_argument('--root', default=common.Z)
ap.add_argument('--n', type=int, default=4000)
a = ap.parse_args()
torch.set_num_threads(2)
out = common.outdir(a.seed, a.root)
views, lps = [], []
for d in common.DAYS:
    if not os.path.exists(f'{out}/play-d{d}.json.gz'):
        continue
    with gzip.open(f'{out}/play-d{d}.json.gz', 'rt') as f:
        gs = json.load(f)
    views += [v for g in gs for v in g['views']]
    lps.append(np.load(f'{out}/play-d{d}.lp.npz')['lp'])
lp1 = np.concatenate(lps).astype(np.float64)
ix = np.linspace(0, len(views) - 1, min(a.n, len(views))).astype(int)
lp2 = play.move_logprobs(load_model(common.ckpt(a.seed)).eval(), [views[i] for i in ix])
res = dict(n=len(ix), total=len(views), argmax_equal=float((lp1[ix].argmax(1) == lp2.argmax(1)).mean()), max_abs_lp_diff=float(np.abs(lp1[ix] - lp2).max()))
print(res)
json.dump(res, open(f'{out}/recheck_lp.json', 'w'))
