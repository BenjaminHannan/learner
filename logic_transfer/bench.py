"""Timing and determinism helpers (LT-1 harness).
  python -m logic_transfer.bench det --threads N --parent CKPT --data DIR --mix FILE --work DIR     (same 50 updates twice, compare weights)
  python -m logic_transfer.bench time --jobs J --threads T --parent CKPT --data DIR --mix FILE --work DIR [--updates 40]
"""
import argparse
import json
import os
import subprocess
import sys

import torch


def launch(work, name, a, threads, updates, seed=1):
    out = os.path.join(work, name)
    cmd = [sys.executable, '-m', 'logic_transfer.course', '--parent', a.parent, '--data', a.data, '--mix', a.mix, '--updates', str(updates),
           '--warmup', '10', '--seed', str(seed), '--threads', str(threads), '--out', out, '--log-every', '10', '--slice-every', '0']
    env = dict(os.environ, OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads))
    return subprocess.Popen(cmd, env=env, stdout=open(out + '.log', 'w'), stderr=subprocess.STDOUT), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['det', 'time'])
    ap.add_argument('--threads', type=int, default=1)
    ap.add_argument('--jobs', type=int, default=1)
    ap.add_argument('--updates', type=int, default=40)
    ap.add_argument('--parent', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--mix', required=True)
    ap.add_argument('--work', required=True)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    if a.mode == 'det':
        outs = []
        for i in range(2):
            p, out = launch(a.work, f'det{a.threads}-{i}', a, a.threads, 50)
            p.wait(); outs.append(out)
        w = [torch.load(os.path.join(o, 'checkpoint.pt'), weights_only=True)['model'] for o in outs]
        diff = max(float((w[0][k].float() - w[1][k].float()).abs().max()) for k in w[0])
        ident = all(torch.equal(w[0][k], w[1][k]) for k in w[0])
        print(json.dumps({'threads': a.threads, 'updates': 50, 'bit_identical': ident, 'max_abs_diff': diff}))
    else:
        ps = [launch(a.work, f'time{a.jobs}x{a.threads}-{i}', a, a.threads, a.updates, seed=i + 1) for i in range(a.jobs)]
        meds = []
        for p, out in ps:
            p.wait()
            meds.append(json.load(open(os.path.join(out, 'run.json')))['steady_median_s_per_update'])
        print(json.dumps({'jobs': a.jobs, 'threads': a.threads, 'median_s_per_update_per_job': meds}))


if __name__ == '__main__':
    main()
