#!/usr/bin/env python3
"""feas-24b: feas-24 with a head fit that converges (creative research thread, 2026-09-25).

Why: feas-24 (VERIFY-feas24.md) did not test its idea. The reused logistic fitter (plain gradient descent, step 0.5)
diverged on the 1,536-number hidden states, so its pair counts were chaotic and changed with the CPU thread count.
ONE change from feas-24: the head is fitted by Newton's method on the same L2-penalised logistic loss (standardised
features, float64, step halved whenever the loss would rise, stop when the largest weight change is below 1e-6 or
after 60 steps), and every fit reports its final gradient size.
Selection is on dev only, and now uses all three seeds: layer (8/12/16/20/24) and l2 (10/100/1,000/10,000) with
the best MEAN dev AUC of the three real-label heads. Everything else is feas-24 (claude_feas24.py): states, text,
features, split rule, pairs, shuffled-label placebo, seeds, marks. The panel is fresh: split seed 792, because the
seed-791 test pairs were already scored once.

  python -B scripts/claude_feas24b.py --model M --out DIR [--feats F.npz]
  python -B scripts/claude_feas24b.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_feas24 as F  # noqa: E402

L2S = [10.0, 100.0, 1000.0, 10000.0]


def loss_of(Z, y, w, b, l2):
    z = Z @ w + b
    return float(np.mean(np.logaddexp(0, z) - y * z) + 0.5 * l2 * (w @ w) / len(y))


def fit_newton(X, y, l2, iters=60, tol=1e-6):
    X = X.astype(np.float64)
    m, s = X.mean(0), X.std(0) + 1e-6
    Z = np.hstack([(X - m) / s, np.ones((len(X), 1))])
    n, d = Z.shape
    reg = np.full(d, l2 / n)
    reg[-1] = 1e-8                                     # the bias is not penalised
    th = np.zeros(d)

    def L(t):
        z = Z @ t
        return float(np.mean(np.logaddexp(0, z) - y * z) + 0.5 * (reg * t) @ t)
    cur = L(th)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(Z @ th)))
        g = Z.T @ (p - y) / n + reg * th
        H = (Z * (p * (1 - p))[:, None]).T @ Z / n + np.diag(reg)
        step = np.linalg.solve(H, g)
        a = 1.0
        while a > 1e-6:
            new = th - a * step
            nl = L(new)
            if nl <= cur:
                break
            a /= 2
        done = np.max(np.abs(new - th)) < tol
        th, cur = new, nl
        if done:
            break
    p = 1 / (1 + np.exp(-(Z @ th)))
    gnorm = float(np.linalg.norm(Z.T @ (p - y) / n + reg * th))
    return {"w": th[:-1], "b": float(th[-1]), "mean": m, "std": s, "loss": cur, "grad": gnorm}


def run(a):
    t0 = time.time()
    train, dev, pairs = F.build(a.seed)
    tstates = sorted({s for k in pairs for _, p, q in pairs[k] for s in (p, q)})
    states = [s for s, _ in train] + [s for s, _ in dev] + tstates
    X = F.features(a, states).astype(np.float64)
    idx = {s: i for i, s in enumerate(states)}
    ntr, ndv = len(train), len(dev)
    ytr = np.array([float(r) for _, r in train])
    ydv = np.array([float(r) for _, r in dev])
    stage_tr = np.array([len(s) for s, _ in train])
    res = {"seed": a.seed, "n_train_pool": ntr, "n_dev": ndv, "n_test_pairs_3": len(pairs[3]),
           "n_test_pairs_2": len(pairs[2]), "test_distinct_reachable": {k: len({p for _, p, _ in pairs[k]})
                                                                        for k in pairs}}

    def sub(seed):
        r = np.random.default_rng(seed)
        take = []
        for k in (2, 3):
            for lab in (0.0, 1.0):
                cell = np.where((stage_tr == k) & (ytr == lab))[0]
                take += r.choice(cell, int(0.85 * len(cell)), replace=False).tolist()
        return np.array(sorted(take))

    def shuffled(seed, rows):
        r = np.random.default_rng(1000 + seed)
        y = ytr[rows].copy()
        for k in (2, 3):
            msk = stage_tr[rows] == k
            y[msk] = r.permutation(y[msk])
        return y

    def score(h, Xs):
        return (((Xs - h["mean"]) / h["std"]) @ h["w"] + h["b"])   # the logit: same order as the probability
    rows = {sd: sub(sd) for sd in (0, 1, 2)}
    cv, grads = {}, []
    for li, L in enumerate(F.LAYERS):
        for l2 in L2S:
            aucs = []
            for sd in (0, 1, 2):
                h = fit_newton(X[rows[sd], li], ytr[rows[sd]], l2)
                grads.append(h["grad"])
                sc = score(h, X[ntr:ntr + ndv, li])
                aucs.append(F.auc(sc[ydv == 1], sc[ydv == 0]))
            cv[f"{L}/{l2}"] = round(float(np.mean(aucs)), 4)
            print(f"[dev] layer {L} l2 {l2}: mean dev AUC {cv[f'{L}/{l2}']} ({[round(x, 3) for x in aucs]})",
                  flush=True)
    best = max(cv, key=cv.get)
    L, l2 = int(best.split("/")[0]), float(best.split("/")[1])
    li = F.LAYERS.index(L)
    res.update({"dev_auc_mean": cv, "layer": L, "l2": l2, "dev_max_final_grad": max(grads)})
    pf = {k: [(idx[p], idx[q]) for _, p, q in pairs[k]] for k in pairs}
    for sd in (0, 1, 2):
        for arm, y in (("real", ytr[rows[sd]]), ("shuffled", shuffled(sd, rows[sd]))):
            h = fit_newton(X[rows[sd], li], y, l2)
            fs = score(h, X[:, li])
            s3, s2 = F.pair_score(fs, pf[3]), F.pair_score(fs, pf[2])
            res[f"{arm}_seed{sd}"] = {"pairs_right": float(s3 + s2), "pairs_right_3": float(s3),
                                      "pairs_right_2": float(s2), "final_grad": h["grad"],
                                      "train_loss": round(h["loss"], 4)}
            print(f"[feas] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "feas24b_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    r = np.random.default_rng(0)
    X = r.normal(size=(400, 50))
    w = r.normal(size=50)
    y = (X @ w + r.normal(size=400) > 0).astype(float)
    h1 = fit_newton(X, y, 10.0)
    h2 = fit_newton(X[::-1].copy(), y[::-1].copy(), 10.0)                 # order must not matter
    assert h1["grad"] < 1e-6 and np.allclose(h1["w"], h2["w"], atol=1e-6), (h1["grad"], h2["grad"])
    Xh = r.normal(size=(300, 1536)).astype(np.float32)                     # wide case like the 1B features
    yh = (Xh[:, :5].sum(1) > 0).astype(float)
    h = fit_newton(Xh, yh, 10.0)
    assert h["grad"] < 1e-5 and h["loss"] < 0.6932, (h["grad"], h["loss"])
    tr, dv, pr = F.build(792)
    assert not ({s for s, _ in tr} & {s for k in pr for _, p, q in pr[k] for s in (p, q)})
    print("selftest ok", round(h1["loss"], 4), f"{h['grad']:.1e}", len(tr), len(dv))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--feats", default="")
    ap.add_argument("--seed", type=int, default=792)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
