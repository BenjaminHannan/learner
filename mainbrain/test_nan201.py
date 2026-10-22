"""python3 -m mainbrain.test_nan201 : seed-201 night-2 NaN (subnormal output gradient in kf.kfac_stats(norm='example')).

(a) seed-200 diary factors (128 rows) are bit-identical to the pre-fix kf.py (HEAD's copy), for norm='example' and norm=None;
(b) the seed-201 diary batch 1536..1599 (row 1545: output gradient at q_word max 5e-44, subnormal) gave a non-finite G before the fix, finite G now;
(c) the repro: guard built as fullrun builds it on night_1 weights, mode.train_night 10 updates, all losses finite
    (run with --full: needs the whole 4096-row diary, ~6 min and ~3 GB). One thread."""
import importlib.util
import json
import subprocess
import sys

import torch

from custom_io.models import load_model
from domain import mode
from mainbrain import common, gp, kf

torch.set_num_threads(1)
P200 = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
R200 = '/mnt/project-files/main-brain/runs/sheet-s200-kf97n'
R201 = '/mnt/project-files/main-brain/runs/sheet-s201-kf97n'
CONS = 'mainbrain/constants-kf97n-lr3e4.json'


def old_kf():
    src = subprocess.run(['git', 'show', 'HEAD:mainbrain/kf.py'], capture_output=True, text=True, check=True).stdout
    spec = importlib.util.spec_from_loader('kf_old', loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(src, 'kf_old', 'exec'), mod.__dict__)
    return mod


def same(s0, s1):
    return all(torch.equal(s0[n][0], s1[n][0]) and torch.equal(s0[n][1], s1[n][1]) for n in s0)


def main(full=False):
    old = old_kf()
    m = load_model(P200)
    rows = common.run_rows(R200)[0][:128]
    for norm in ('example', None):
        s_old, s_new = old.kfac_stats(m, rows, norm=norm), kf.kfac_stats(m, rows, norm=norm)
        assert same(s_old, s_new), ('(a) differs', norm)
        assert all(torch.isfinite(G).all() for _, G in s_new.values())
    print('(a) seed-200 128-row A and G identical to pre-fix kf.py for norm=example and norm=None (HEAD copy is the fixed one if already committed)')

    m = load_model(R201 + '/night_1/checkpoint.pt')
    row = common.run_rows(R201)[0][1536:1600]   # the batch kfac_stats saw (bs=64); row 1545 alone is not subnormal
    s_new = kf.kfac_stats(m, row, bs=64, norm='example')
    bad_new = [n for n, (A, G) in s_new.items() if G is not None and not torch.isfinite(G).all()]
    s_old = old.kfac_stats(m, row, bs=64, norm='example')
    bad_old = [n for n, (A, G) in s_old.items() if G is not None and not torch.isfinite(G).all()]
    print('(b) batch 1536..1599, G non-finite modules: pre-fix', bad_old, ' fixed', bad_new)
    assert not bad_new
    if not full:
        return
    diary, d2 = common.run_rows(R201)[0], common.run_rows(R201)[2]
    cons = json.load(open(CONS))
    for p in m.parameters():
        p.requires_grad_(True)
    F, info = kf.factors(kf.kfac_stats(m, diary, norm='example'), cons['protect_energy'])
    bad = [n for n, f in F.items() if not all(torch.isfinite(x).all() for x in f)]
    assert not bad, bad
    gp.freeze_unprojected(m)
    opt = kf.KFOptimizer(m, mode.make_opt(m, cons['lr']), F)
    mode.make_opt = lambda mm, lr: opt
    losses = mode.train_night(m, d2, diary, 10, cons, 201002)
    print('(c) losses', [round(x, 3) for x in losses])
    assert all(x == x and abs(x) != float('inf') for x in losses)
    assert all(torch.isfinite(p).all() for p in m.parameters())
    print('(c) 10 updates finite, weights finite')


if __name__ == '__main__':
    main(full='--full' in sys.argv)
