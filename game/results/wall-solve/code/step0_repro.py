"""Step 0: reproduce A23's held-out top-1 (all views and S) with game.probe.evaluate, the code path of `probe.py eval`.
python step0_repro.py SEED [--root DIR]   (SEED = 200 or 201)"""
import argparse
import json
import os
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from game import probe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('seed', type=int)
    ap.add_argument('--root', default=common.Z)
    ap.add_argument('--threads', type=int, default=2)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    out = common.outdir(a.seed, a.root)
    # probe.evaluate wants DATA/train.jsonl (only for the always-`do` baseline, which we do not use) and DATA/heldout.jsonl
    d = f'{out}/probe_data'
    os.makedirs(d, exist_ok=True)
    open(f'{d}/train.jsonl', 'w').close()
    if not os.path.exists(f'{d}/heldout.jsonl'):
        os.symlink(common.HELD, f'{d}/heldout.jsonl')
    t0 = time.time()
    res = probe.evaluate([common.ckpt(a.seed)], d, 64000, ['student'])
    mine = res['checkpoints']['student']
    with open(common.eval_json(a.seed)) as f:
        ref = json.load(f)['checkpoints']['student']
    rec = dict(seed=a.seed, ckpt=common.ckpt(a.seed), heldout=res['heldout'], subset=res['subset'],
               accuracy_all=mine['accuracy_all'], accuracy_subset=mine['accuracy_subset'],
               a23_accuracy_all=ref['accuracy_all'], a23_accuracy_subset=ref['accuracy_subset'],
               diff_points_all=round(100 * (mine['accuracy_all'] - ref['accuracy_all']), 3),
               diff_points_subset=round(100 * (mine['accuracy_subset'] - ref['accuracy_subset']), 3),
               per_word_subset=mine['per_word_subset'], seconds=round(time.time() - t0, 1))
    rec['pass'] = abs(rec['diff_points_subset']) <= 0.1 and abs(rec['diff_points_all']) <= 0.1
    with open(f'{out}/repro.json', 'w') as f:
        json.dump(rec, f, indent=1)
    print(a.seed, 'S', rec['accuracy_subset'], 'A23', rec['a23_accuracy_subset'], 'all', rec['accuracy_all'], rec['a23_accuracy_all'],
          'diff pts S/all', rec['diff_points_subset'], rec['diff_points_all'], 'PASS' if rec['pass'] else 'FAIL', rec['seconds'], 's', flush=True)


if __name__ == '__main__':
    main()
