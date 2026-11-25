"""Point 5 context check: 2-frame versions of linear_Mact and shift_or_stay baselines on train_dn -> dev.

Strictly follows Point 2 history rules:
  - x_{-1} = x_0 at episode start (never crosses episode or world boundary)
  - Open-loop rollout at k=3, 5 feeds strictly own outputs from step 2 onward (no real future frames)
"""
from __future__ import annotations

import os
import sys
import time
import numpy as np

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer


def prev_idx(split, xi, ti):
    h = np.where(ti > 0, xi - 1, xi)
    assert np.array_equal(split["episode_id"][h], split["episode_id"][xi])
    assert np.array_equal(split["world_id"][h], split["world_id"][xi])
    return h


def fit_linear_action_baseline_2f(train, ridge=1.0):
    xi1, ai1, _, _, ti1 = scorer.windows(train, 1)
    h1 = prev_idx(train, xi1, ti1)
    fr = train["frames"].astype(np.float64)
    Xt = fr[xi1].reshape(len(xi1), -1)
    Xp = fr[h1].reshape(len(xi1), -1)
    Xd = Xt - Xp
    Ya = fr[xi1 + 1].reshape(len(xi1), -1)
    aa = train["actions"][ai1]
    Mact = {}
    eye = ridge * np.eye(1537)
    for q in range(17):
        sel = aa == q
        if sel.sum() == 0:
            Mact[q] = np.vstack([np.eye(768), np.zeros((769, 768))])
        else:
            Xq = np.c_[Xt[sel], Xd[sel], np.ones(sel.sum())]
            Mact[q] = np.linalg.solve(Xq.T @ Xq + eye, Xq.T @ Ya[sel])
    return Mact


def rollout_linear_action_baseline_2f(Mact, x_prev, x0, acts_k):
    xp = np.asarray(x_prev, dtype=np.float64).reshape(len(x0), -1).copy()
    x = np.asarray(x0, dtype=np.float64).reshape(len(x0), -1).copy()
    for j in range(acts_k.shape[1]):
        xd = x - xp
        nx = np.empty_like(x)
        for q in range(17):
            sel = acts_k[:, j] == q
            if sel.any():
                nx[sel] = np.c_[x[sel], xd[sel], np.ones(sel.sum())] @ Mact[q]
        xp, x = x, nx
    return x.reshape(-1, 16, 16, 3)


def fit_shift_or_stay_baseline_2f(train, ridge=1.0, gate_ridge=10.0):
    xi1, ai1, _, _, ti1 = scorer.windows(train, 1)
    h1 = prev_idx(train, xi1, ti1)
    fr = train["frames"].astype(np.float64)
    Xp_img = fr[h1]
    X_img = fr[xi1]
    Y_img = fr[xi1 + 1]
    Xp = Xp_img.reshape(len(xi1), -1)
    Xt = X_img.reshape(len(xi1), -1)
    Xd = Xt - Xp
    Ya = Y_img.reshape(len(xi1), -1)
    aa = train["actions"][ai1]
    valid_mv, is_open_mv, _ = scorer.classify_move_displacement(X_img, Y_img, aa)
    Mact = fit_linear_action_baseline_2f(train, ridge=ridge)
    Mshift = {}
    Wgate = {}
    eye = ridge * np.eye(1537)
    for q in (1, 2, 3, 4):
        sel_val = (aa == q) & valid_mv
        sel_mv = sel_val & is_open_mv
        if sel_mv.sum() >= 20:
            Xq = np.c_[Xt[sel_mv], Xd[sel_mv], np.ones(sel_mv.sum())]
            Mshift[q] = np.linalg.solve(Xq.T @ Xq + eye, Xq.T @ Ya[sel_mv])
        else:
            Mshift[q] = Mact[q]
        if sel_val.sum() == 0:
            Wgate[q] = np.zeros(217, dtype=np.float64)
        else:
            c_t = X_img[sel_val, 3:9, 5:11, :].reshape(int(sel_val.sum()), 108)
            c_p = Xp_img[sel_val, 3:9, 5:11, :].reshape(int(sel_val.sum()), 108)
            Xc = np.c_[c_t, c_t - c_p, np.ones(sel_val.sum())]
            yc = is_open_mv[sel_val].astype(np.float64)
            Wgate[q] = np.linalg.solve(Xc.T @ Xc + gate_ridge * np.eye(Xc.shape[1]), Xc.T @ yc)
    return {"Mact": Mact, "Mshift": Mshift, "Wgate": Wgate}


def rollout_shift_or_stay_2f(sos, x_prev, x0, acts_k):
    xp_img = np.asarray(x_prev, dtype=np.float64).copy()
    x_img = np.asarray(x0, dtype=np.float64).copy()
    for j in range(acts_k.shape[1]):
        xp_flat = xp_img.reshape(len(x_img), -1)
        x_flat = x_img.reshape(len(x_img), -1)
        xd_flat = x_flat - xp_flat
        nx = np.empty_like(x_flat)
        for q in range(17):
            sel = acts_k[:, j] == q
            if not sel.any():
                continue
            if q in (1, 2, 3, 4):
                c_t = x_img[sel, 3:9, 5:11, :].reshape(sel.sum(), -1)
                c_p = xp_img[sel, 3:9, 5:11, :].reshape(sel.sum(), -1)
                p_mv = np.clip(np.c_[c_t, c_t - c_p, np.ones(sel.sum())] @ sos["Wgate"][q], 0.0, 1.0)[:, None]
                x_sh = np.c_[x_flat[sel], xd_flat[sel], np.ones(sel.sum())] @ sos["Mshift"][q]
                nx[sel] = p_mv * x_sh + (1.0 - p_mv) * x_flat[sel]
            else:
                nx[sel] = np.c_[x_flat[sel], xd_flat[sel], np.ones(sel.sum())] @ sos["Mact"][q]
        xp_img, x_img = x_img, nx.reshape(-1, 16, 16, 3)
    return x_img


def main():
    t0 = time.time()
    tr = scorer.load_split(os.path.join(BASE, "wm5/data/train_dn.npz"))
    he = scorer.load_split(os.path.join(BASE, "wm-harness/data/heldout.npz"))
    hfr = he["frames"].astype(np.float64)

    # Compute B_k for dev (exact scorer.py definition)
    xi1_tr = scorer.windows(tr, 1)[0]
    mean_tr = tr["frames"][xi1_tr].astype(np.float64).mean(0)
    Bs = {}
    for k in (1, 3, 5):
        xk_tr = scorer.windows(tr, k)[0]
        xs_tr = tr["frames"][xk_tr].astype(np.float64)
        ys_tr = tr["frames"][xk_tr + k].astype(np.float64)
        dd = xs_tr - mean_tr
        bl = float(((ys_tr - mean_tr) * dd).sum() / float((dd * dd).sum()))
        xi = scorer.windows(he, k)[0]
        x0, yk = hfr[xi], hfr[xi + k]
        cp = float(((x0 - yk) ** 2).sum())
        bs = float(((mean_tr + bl * (x0 - mean_tr) - yk) ** 2).sum())
        Bs[k] = min(cp, bs)

    # 1-frame reference
    Mact1 = scorer.fit_linear_action_baseline(tr)
    sos1 = scorer.fit_shift_or_stay_baseline(tr)
    for name, fn in [
        ("1f_linear_Mact", lambda xp, x0, ak: scorer.rollout_linear_action_baseline(Mact1, x0, ak)),
        ("1f_shift_or_stay", lambda xp, x0, ak: scorer.rollout_shift_or_stay(sos1, x0, ak)),
    ]:
        ebs = {}
        bo = None
        for k in (1, 3, 5):
            xi, ai, wi, _, ti = scorer.windows(he, k)
            ak = scorer.action_values(he["actions"], ai, k)
            h = prev_idx(he, xi, ti)
            P = fn(hfr[h], hfr[xi], ak)
            yk = hfr[xi + k]
            ebs[k] = float(((P - yk) ** 2).sum()) / Bs[k]
            if k == 1:
                bo = scorer.score_block_open(hfr[xi], P, yk, ak[:, 0], wi)
        print(
            f"{name:<22}: E/B={ebs[1]:.4f}/{ebs[3]:.4f}/{ebs[5]:.4f} | "
            f"bo={bo['mean_err']:.4f} (fb={bo['false_block_rate']:.4f}, fo={bo['false_open_rate']:.4f})"
        )

    for ridge in (1.0, 10.0):
        Mact2 = fit_linear_action_baseline_2f(tr, ridge=ridge)
        sos2 = fit_shift_or_stay_baseline_2f(tr, ridge=ridge)
        for name, fn in [
            (f"2f_linear_Mact(l={ridge})", lambda xp, x0, ak, m=Mact2: rollout_linear_action_baseline_2f(m, xp, x0, ak)),
            (f"2f_shift_or_stay(l={ridge})", lambda xp, x0, ak, s=sos2: rollout_shift_or_stay_2f(s, xp, x0, ak)),
        ]:
            ebs = {}
            bo = None
            for k in (1, 3, 5):
                xi, ai, wi, _, ti = scorer.windows(he, k)
                ak = scorer.action_values(he["actions"], ai, k)
                h = prev_idx(he, xi, ti)
                P = fn(hfr[h], hfr[xi], ak)
                yk = hfr[xi + k]
                ebs[k] = float(((P - yk) ** 2).sum()) / Bs[k]
                if k == 1:
                    bo = scorer.score_block_open(hfr[xi], P, yk, ak[:, 0], wi)
            print(
                f"{name:<26}: E/B={ebs[1]:.4f}/{ebs[3]:.4f}/{ebs[5]:.4f} | "
                f"bo={bo['mean_err']:.4f} (fb={bo['false_block_rate']:.4f}, fo={bo['false_open_rate']:.4f})"
            )

    print(f"[2F BASELINES DONE in {time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
