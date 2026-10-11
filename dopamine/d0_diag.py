"""POST-HOC diagnostic of why the D0 guesser (dopamine/d0_guess.py) did not beat chance. Not part of the sealed verdict.

  python -m dopamine.d0_diag --run DIR --out OUT.json [--threads 4]

Features are computed once per day (as d0_guess does) and cached to OUT.npz beside OUT.json.
Reports, pooled over days 2..N: (1) C sweep for G / G_reader (fit on days < d); (2) same-day 2-fold cross-fit;
(3) surface proxies of the prompt text (direct AUC, sign-agnostic, plus a logistic on all proxies fit on days < d);
(4) per-kind table for G_reader at the best C of (1)."""
import argparse
import json
import os
import re
import time

import numpy as np
import torch

from dopamine.d0_guess import load_days, day_features, fit_logistic, auc, within_kind_auc
from custom_io.models import load_model
from domain.mode import guard

CS = [0.001, 0.01, 0.1, 1.0]
PROXY = ['len_chars', 'n_digit_runs', 'n_digits', 'max_number', 'n_cell_refs', 'n_colon_ranges']


def proxies(p):
    runs = re.findall(r'\d+', p)
    return [len(p), len(runs), sum(len(r) for r in runs), max([float(r) for r in runs], default=0.0),
            len(re.findall(r'[A-Z][0-9]+', p)), p.count(':')]


def build(run, npz, threads):
    torch.set_num_threads(threads)
    parent, rows, N = load_days(run)
    arr = {}
    for d in range(1, N + 1):
        ck = parent if d == 1 else os.path.join(run, f'night_{d - 1}', 'checkpoint.pt')
        m = load_model(guard(ck)).eval()
        rs = rows[d]
        ans, A, S, c = day_features(m, [r['prompt'] for r in rs])
        arr[f'y{d}'] = np.array([int(x == r['answer']) for x, r in zip(ans, rs)])
        arr[f'kind{d}'] = np.array([r['kind'] for r in rs])
        arr[f'A{d}'], arr[f'S{d}'], arr[f'c{d}'] = A, S, c
        arr[f'P{d}'] = np.array([proxies(r['prompt']) for r in rs], dtype=float)
        print(f'day {d}: {len(rs)} rows, right {arr[f"y{d}"].mean():.3f}', flush=True)
    arr['N'] = np.array(N)
    np.savez(npz, **arr)
    return arr


def mets(ys, vs, ks, ds):
    y, v, k, d = map(np.concatenate, (ys, vs, ks, ds))
    wk, g, n = within_kind_auc(y, v, k, d)
    return dict(within_kind_auc=wk, groups=g, rows=n, auc=auc(y, v), brier=float(np.mean((y - v) ** 2)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=4)
    a = ap.parse_args(argv)
    torch.set_num_threads(a.threads)
    t0 = time.time()
    npz = os.path.splitext(a.out)[0] + '.npz'
    if os.path.exists(npz):
        Z = np.load(npz, allow_pickle=False)
        arr = {k: Z[k] for k in Z.files}
        print('loaded cached features', npz)
    else:
        arr = build(a.run, npz, a.threads)
    N = int(arr['N'])
    g = lambda k, d: arr[f'{k}{d}']
    cat = lambda k, ds: np.concatenate([g(k, d) for d in ds])
    GA = lambda d: np.hstack([g('A', d), g('S', d)])
    days = range(2, N + 1)
    day_arr = lambda d: np.full(len(g('y', d)), d)

    # 1. regularisation sweep
    sweep = {}
    for name in ('G', 'G_reader'):
        for C in CS:
            ys, vs, ks, ds = [], [], [], []
            for d in days:
                tr = list(range(1, d))
                if name == 'G':
                    f = fit_logistic(np.vstack([GA(x) for x in tr]), cat('y', tr), C)
                    v = f(GA(d))
                else:
                    f = fit_logistic(cat('A', tr), cat('y', tr), C)
                    v = f(g('A', d))
                ys.append(g('y', d)); vs.append(v); ks.append(g('kind', d)); ds.append(day_arr(d))
            sweep[f'{name}_C{C}'] = mets(ys, vs, ks, ds)
            print(name, C, sweep[f'{name}_C{C}']['within_kind_auc'], flush=True)

    # 2. same-day cross-fit
    cross = {}
    for name in ('G_reader', 'G'):
        for C in (0.01, 1.0):
            ys, vs, ks, ds = [], [], [], []
            for d in days:
                X = g('A', d) if name == 'G_reader' else GA(d)
                y = g('y', d)
                perm = np.random.RandomState(0).permutation(len(y))
                h = [perm[:len(y) // 2], perm[len(y) // 2:]]
                v = np.zeros(len(y))
                for i in (0, 1):
                    v[h[1 - i]] = fit_logistic(X[h[i]], y[h[i]], C)(X[h[1 - i]])
                ys.append(y); vs.append(v); ks.append(g('kind', d)); ds.append(day_arr(d))
            cross[f'{name}_C{C}'] = mets(ys, vs, ks, ds)
            print('crossfit', name, C, cross[f'{name}_C{C}']['within_kind_auc'], flush=True)

    # 3. proxies
    y_all, k_all = cat('y', days), cat('kind', days)
    d_all, P_all = np.concatenate([day_arr(d) for d in days]), cat('P', days)
    direct = {}
    for j, nm in enumerate(PROXY):
        wk, gr, n = within_kind_auc(y_all, P_all[:, j], k_all, d_all)
        direct[nm] = dict(within_kind_auc_raw=wk, sign_agnostic=max(wk, 1 - wk), direction='higher=more right' if wk >= 0.5 else 'higher=more wrong')
    ys, vs, ks, ds = [], [], [], []
    for d in days:
        tr = list(range(1, d))
        f = fit_logistic(np.log1p(cat('P', tr)), cat('y', tr), 1.0)
        ys.append(g('y', d)); vs.append(f(np.log1p(g('P', d)))); ks.append(g('kind', d)); ds.append(day_arr(d))
    proxy_logit = mets(ys, vs, ks, ds)

    # 4. per-kind at best C for G_reader
    bestC = max(CS, key=lambda C: sweep[f'G_reader_C{C}']['within_kind_auc'])
    vs = []
    for d in days:
        tr = list(range(1, d))
        vs.append(fit_logistic(cat('A', tr), cat('y', tr), bestC)(g('A', d)))
    v_all = np.concatenate(vs)
    per_kind = {}
    for k in sorted(set(k_all)):
        ix = k_all == k
        tot, n, ng = 0.0, 0, 0
        for d in days:
            jx = ix & (d_all == d)
            yk = y_all[jx]
            if yk.sum() >= 10 and len(yk) - yk.sum() >= 10:
                tot += auc(yk, v_all[jx]) * len(yk); n += len(yk); ng += 1
        per_kind[str(k)] = dict(n=int(ix.sum()), success_rate=float(y_all[ix].mean()),
                                within_kind_auc=(tot / n if n else None), day_groups=ng, rows_in_auc=n)

    out = dict(run=a.run, post_hoc=True, days=N, best_C_G_reader=bestC, sweep=sweep, same_day_crossfit=cross,
               proxy_direct=direct, proxy_logistic=proxy_logit, per_kind_G_reader_bestC=per_kind,
               runtime_seconds=round(time.time() - t0, 1))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    f = lambda x: '  -  ' if x is None else f'{x:.3f}'
    print('\nPOST-HOC; pooled days 2..%d       wkAUC  Brier' % N)
    for t in (sweep, cross):
        for k, r in t.items():
            print(f'  {k:18s} {f(r["within_kind_auc"])}  {f(r["brier"])}')
    for k, r in direct.items():
        print(f'  proxy {k:15s} {f(r["sign_agnostic"])}  {r["direction"]}')
    print(f'  proxy logistic     {f(proxy_logit["within_kind_auc"])}  {f(proxy_logit["brier"])}')
    print(f'per kind, G_reader C={bestC}:')
    for k, r in per_kind.items():
        print(f'  {k:14s} n={r["n"]:5d} succ={r["success_rate"]:.3f} wkAUC={f(r["within_kind_auc"])} ({r["day_groups"]} groups)')
    print(f'runtime {out["runtime_seconds"]}s')


if __name__ == '__main__':
    main()
