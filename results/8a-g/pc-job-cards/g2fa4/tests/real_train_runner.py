#!/usr/bin/env python3
"""A stand-in for local_runner + g8a.job that runs the REAL overlay train.py on a tiny b3g2 on the CPU (tests/test_supervisor_real.py only).
real_train_runner.py --work W --queue QPATH --job J --tree TREE --accum A --steps N --ckpt-every K  -> OUT=W/results/<queue>/<job>/B3G2 (like g8a.job --local)."""
import argparse, json, os, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--work'); ap.add_argument('--queue'); ap.add_argument('--job'); ap.add_argument('--tree'); ap.add_argument('--accum', type=int)
ap.add_argument('--steps', type=int); ap.add_argument('--ckpt-every', type=int); ap.add_argument('--busy', default='')
a = ap.parse_args()
sys.path.insert(0, a.tree)
from custom_io.tests import test_ckpt as T
from custom_io.tests import test_ckpt_b3g2 as B
out = Path(a.work) / 'results' / Path(a.queue).stem / a.job
arm = out / 'B3G2'
arm.mkdir(parents=True, exist_ok=True)
if (out / 'RESULT.json').exists():
    sys.exit(0)
data = Path(a.work) / 'tinydata'
if not data.exists():
    T.TMP = str(a.work)
    T.make_data('tinydata', 48)
args = B.argv(str(data), str(arm), a.steps, a.accum, ['--ckpt-every', str(a.ckpt_every), '--resume'])
env = dict(os.environ, OMP_NUM_THREADS='1', PYTHONPATH=a.tree)
with open(arm / 'stdout.txt', 'w') as so:
    rc = subprocess.call([sys.executable, '-m', 'custom_io.train'] + args, cwd=a.tree, env=env, stdout=so, stderr=subprocess.STDOUT)
res = json.load(open(arm / 'RESULT.json')) if (arm / 'RESULT.json').exists() else {}
json.dump(dict(status='ok' if rc == 0 else 'arm_failed'), open(out / 'RESULT.json', 'w'))
