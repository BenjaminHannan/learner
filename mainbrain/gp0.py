"""GP-0: free feasibility check for null-space learning (no training, no panel, no DEV row).

For the parent, per layer and per energy share: how many input directions the old questions use (protected), how much of
the new subject's input energy lies outside them, and how much of the new subject's gradient survives the projection.

  python -m mainbrain.gp0 --run RUNS/sheet-s200-v4 --seed 200 --out OUT.json [--threads 4] [--diary-n 4096]
"""
import argparse
import json
import time

import torch

from custom_io.data import Dataset, collate, to_device
from custom_io.models import load_model
from mainbrain import gp
from mainbrain.common import parent_of, run_rows

ENERGIES = (0.9, 0.95, 0.97, 0.99, 0.995, 0.999)


def grads(m, rows, bs=64):
    """Summed gradient of the training loss over rows, per projected module, as [out, in(*k) + 1] (train mode, as a night)."""
    m.train()
    m.zero_grad(set_to_none=True)
    ds = Dataset(rows, m.vocab)
    for s in range(0, len(rows), bs):
        idx = range(s, min(s + bs, len(rows)))
        out = m.loss(to_device(collate([ds[i] for i in idx]), 'cpu'))
        loss = out[0] if isinstance(out, tuple) else out
        (loss * len(idx) / len(rows)).backward()
    G = {}
    for n, mod in gp.projected_modules(m):
        if mod.weight.grad is None:
            continue
        g = mod.weight.grad.reshape(mod.weight.shape[0], -1)
        b = mod.bias.grad if mod.bias is not None and mod.bias.grad is not None else torch.zeros(g.shape[0])
        G[n] = torch.cat([g, b[:, None]], 1).detach().clone()
    m.zero_grad(set_to_none=True)
    m.eval()
    return G


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
    print('diary', len(diary), 'night-1 rows', len(new), flush=True)
    c_old = gp.covariances(m, diary)
    print('old covs', round(time.time() - t0), 's', flush=True)
    c_new = gp.covariances(m, new)
    print('new covs', round(time.time() - t0), 's', flush=True)
    G = grads(m, new)
    print('grads', round(time.time() - t0), 's', flush=True)
    res = {}
    for e in ENERGIES:
        per, tot_g, tot_gp, tot_new, tot_new_out = {}, 0.0, 0.0, 0.0, 0.0
        for n, (C, N) in c_old.items():
            if C is None:
                continue
            U, lam, k = gp.basis(C, e)
            Pm = torch.eye(C.shape[0]) - U @ U.T
            Cn = c_new[n][0]
            new_out = float(torch.trace(Pm @ Cn @ Pm) / torch.trace(Cn)) if Cn is not None else None
            g = G.get(n)
            gs = float((g @ Pm).norm() / g.norm()) if g is not None and g.norm() > 0 else None
            per[n] = dict(dim=C.shape[0], protected=k, new_energy_outside=None if new_out is None else round(new_out, 4),
                          grad_kept=None if gs is None else round(gs, 4))
            if g is not None:
                tot_g += float(g.norm() ** 2)
                tot_gp += float((g @ Pm).norm() ** 2)
        res[str(e)] = dict(layers=per, grad_kept_all=round((tot_gp / tot_g) ** 0.5, 4) if tot_g else None)
        print(e, 'grad kept (all layers, norm)', res[str(e)]['grad_kept_all'], flush=True)
    json.dump(dict(run=a.run, seed=a.seed, diary=len(diary), new=len(new), energies=res,
                   secs=round(time.time() - t0, 1)), open(a.out, 'w'), indent=1)
    print('wrote', a.out, flush=True)


if __name__ == '__main__':
    main()
