"""KF-0: free check (no training) comparing input-only protection (GP) with Kronecker-factored protection (KF).

For the parent: the new subject's gradient (night-1 rows of a finished run), and per energy share, how much of it each
projection keeps, and how much of a K-FAC estimate of the old-answer harm of a small step along it is left
(harm(D) = sum_ij (V^T D U)_ij^2 g_j a_i; lower = safer). No panel or DEV row is read.

  python -m mainbrain.kf0 --run RUNS/sheet-s200-v4 --seed 200 --out OUT.json [--threads 4]
"""
import argparse
import json
import time

import torch

from custom_io.models import load_model
from mainbrain import gp, kf
from mainbrain.common import parent_of, run_rows
from mainbrain.gp0 import grads

ENERGIES = (0.9, 0.97, 0.99, 0.999)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--run', required=True)
    a.add_argument('--seed', type=int, required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--threads', type=int, default=4)
    a.add_argument('--diary-n', type=int, default=4096)
    a = a.parse_args(argv)
    torch.set_num_threads(a.threads)
    t0 = time.time()
    torch.manual_seed(a.seed)
    m = load_model(parent_of(a.seed)).eval()
    rows = run_rows(a.run)
    diary, new = rows[0][:a.diary_n], rows[1]
    st = kf.kfac_stats(m, diary)
    print('kfac stats', round(time.time() - t0), 's', flush=True)
    Gn = grads(m, new)
    print('grads', round(time.time() - t0), 's', flush=True)
    eigs = {n: (kf.eig(A), kf.eig(G)) for n, (A, G) in st.items() if A is not None and G is not None}
    res = {}
    for e in ENERGIES:
        tot = dict(g=0.0, g_gp=0.0, g_kf=0.0, h=0.0, h_gp=0.0, h_kf=0.0)
        per = {}
        for n, ((av, U), (gv, V)) in eigs.items():
            D = Gn.get(n)
            if D is None or float(D.norm()) == 0.0:
                continue
            W = gv[:, None] * av[None, :]
            harm = lambda X: float(((V.T @ X @ U) ** 2 * W).sum())
            # GP: input-only, top `e` of input energy
            cum = torch.cumsum(av, 0) / av.sum()
            k = int((cum < e).sum().item()) + 1
            Ug = U[:, :k]
            Dg = D - D @ Ug @ Ug.T
            M, kk = kf.mask_for(av, gv, e)
            Dk = kf.project(D, (U, V, M))
            r = dict(g=float(D.norm() ** 2), g_gp=float(Dg.norm() ** 2), g_kf=float(Dk.norm() ** 2),
                     h=harm(D), h_gp=harm(Dg), h_kf=harm(Dk))
            for key in tot:
                tot[key] += r[key]
            per[n] = dict(grad_kept_gp=round((r['g_gp'] / r['g']) ** 0.5, 4), grad_kept_kf=round((r['g_kf'] / r['g']) ** 0.5, 4),
                          harm_left_gp=round(r['h_gp'] / r['h'], 5) if r['h'] else None,
                          harm_left_kf=round(r['h_kf'] / r['h'], 5) if r['h'] else None,
                          kf_free_share=round(1 - kk / M.numel(), 4))
        res[str(e)] = dict(grad_kept_gp=round((tot['g_gp'] / tot['g']) ** 0.5, 4), grad_kept_kf=round((tot['g_kf'] / tot['g']) ** 0.5, 4),
                           harm_left_gp=round(tot['h_gp'] / tot['h'], 5), harm_left_kf=round(tot['h_kf'] / tot['h'], 5), layers=per)
        print(e, {k: v for k, v in res[str(e)].items() if k != 'layers'}, flush=True)
    json.dump(dict(run=a.run, seed=a.seed, diary=len(diary), new=len(new), energies=res, secs=round(time.time() - t0, 1)),
              open(a.out, 'w'), indent=1)
    print('wrote', a.out, flush=True)


if __name__ == '__main__':
    main()
