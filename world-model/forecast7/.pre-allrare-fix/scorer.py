"""PROBLEM-7 Forecast5 Fixed Scorer (Rung 0 Ruler Fix + Rung 1 Physics Bars).

Preserves 100% of the Rung-0 fixed ruler (Bugs A2, A2b, A10, A11 fixed; legacy thresholds
unchanged: E/B <= 0.80/0.90/0.95, worlds_both >= 12, std_ok, pcs_ok, ceiling <= 0.70) AND adds
Rung-1 real-physics pass marks:
  1. Beat BOTH per-action linear ridge (M_a [x_t, 1]) AND shift-or-stay baseline on E_k / B_k
     at all of k = 1, 3, 5.
  2. Visual HUD-masked terrain-displacement blocked-vs-open move readout (100% prediction-blind,
     zero game-memory cheats, exact same function run on ground truth and every predictor):
     cut mean(false_block, false_open) by >= 25% vs the stronger baseline (shift_or_stay) with
     NEITHER false_block_rate NOR false_open_rate worse.
  3. Paired 95% bootstrap CIs across worlds for E/B, E/E_strongest_baseline, shuffle_pooled,
     and block-vs-open error.
"""
import argparse
import json
import numpy as np

# Exact Crafter 16x16 pooled 1-tile shift: 64x64 has 9x7 world tiles (~7 px/tile -> 7/4 = 1.75 px).
# Player moving left (1) shifts world pixels right -> f1(y, x) ~ f0(y, x - 1.75).
TILE_SHIFT_PX = 1.75
MOVE_DIRS = {
    1: (0.0, -TILE_SHIFT_PX),   # move_left
    2: (0.0, +TILE_SHIFT_PX),   # move_right
    3: (-TILE_SHIFT_PX, 0.0),   # move_up
    4: (+TILE_SHIFT_PX, 0.0),   # move_down
}
# HUD-masked interior terrain crop: rows 2..9 (strictly above Crafter HUD rows 12..15), cols 2..13.
# Player sprite occupies global 16x16 rows 5..6, cols 7..8 (local rows 3..4, cols 5..6).
# Direction-specific masks built below exclude BOTH the destination sprite footprint [5:7, 7:9]
# AND every crop pixel whose bilinear shift samples from [5:7, 7:9] with positive weight.
_PLAYER_SPRITE_GLOBAL = np.zeros((1, 16, 16, 1), dtype=np.float64)
_PLAYER_SPRITE_GLOBAL[0, 5:7, 7:9, 0] = 1.0
BLOCK_OPEN_ALPHA_THRESH = 0.40
BLOCK_OPEN_MIN_SHIFT_ENERGY = 5e-4


def load_split(path):
    with np.load(path) as d:
        return {k: d[k] for k in d.files}


def episode_index(d):
    eid = d["episode_id"]
    n = len(eid)
    cuts = np.flatnonzero(np.r_[True, eid[1:] != eid[:-1]])
    if len(cuts) != len(np.unique(eid)):
        raise ValueError("episodes are not contiguous")
    ends = np.r_[cuts[1:], n]
    lengths = ends - cuts
    action_offsets = np.r_[0, np.cumsum(lengths - 1)[:-1]]
    return cuts, ends, action_offsets


def windows(d, k):
    starts, ends, aoffs = episode_index(d)
    xi, ai, world, episode, t = [], [], [], [], []
    for s, e, ao in zip(starts, ends, aoffs):
        n = (e - s) - k
        if n <= 0:
            continue
        xi.append(np.arange(s, s + n))
        ai.append(np.arange(ao, ao + n))
        world.append(np.full(n, d["world_id"][s], dtype=np.int64))
        episode.append(np.full(n, d["episode_id"][s], dtype=np.int64))
        t.append(np.arange(n, dtype=np.int64))
    cat = np.concatenate
    return cat(xi), cat(ai), cat(world), cat(episode), cat(t)


def action_values(actions, ai, k):
    return actions[ai[:, None] + np.arange(k)[None, :]]


def shuffle_actions_per_step(d, seed=43):
    """Fix Bug A11a: permute individual per-step actions within each world (not k-step tuples)."""
    a = d["actions"].copy()
    starts, ends, aoffs = episode_index(d)
    aw = np.empty(len(a), dtype=np.int64)
    for s, e, ao in zip(starts, ends, aoffs):
        aw[ao:ao + (e - s - 1)] = d["world_id"][s]
    rng = np.random.default_rng(seed)
    for w in np.unique(aw):
        idx = np.flatnonzero(aw == w)
        a[idx] = a[idx][rng.permutation(len(idx))]
    return a


def pcs90(x):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean(0)
    cov = x.T @ x / max(len(x) - 1, 1)
    ev = np.clip(np.linalg.eigvalsh(cov)[::-1], 0.0, None)
    total = ev.sum()
    if total <= 1e-18:
        return 1
    return int(np.searchsorted(np.cumsum(ev) / total, 0.90) + 1)


def residual_decode(x0, pred_rt_k, start_rt_0):
    """Fix Bug A2: open-loop residual-change decoding initialized ONCE from x0.
    Never peeks at intermediate true frames: P_k = x0 + (RT(imagined_rows_k) - RT(start_rows_0)).
    """
    return np.asarray(x0, dtype=np.float64) + (
        np.asarray(pred_rt_k, dtype=np.float64) - np.asarray(start_rt_0, dtype=np.float64)
    )


def _bilinear_terrain_shift(img, dy, dx):
    """Sample img [..., 16, 16, 3] at interior terrain coords y=2..9 + dy, x=2..13 + dx."""
    ys = np.arange(2, 10, dtype=np.float64) + dy
    xs = np.arange(2, 14, dtype=np.float64) + dx
    y0 = np.floor(ys).astype(int)
    wy = (ys - y0)[:, None, None]
    x0 = np.floor(xs).astype(int)
    wx = (xs - x0)[None, :, None]
    top = (1.0 - wx) * img[..., y0[:, None], x0[None, :], :] + wx * img[..., y0[:, None], x0[None, :] + 1, :]
    bot = (1.0 - wx) * img[..., y0[:, None] + 1, x0[None, :], :] + wx * img[..., y0[:, None] + 1, x0[None, :] + 1, :]
    return (1.0 - wy) * top + wy * bot


def _build_terrain_masks_by_dir():
    """Mask BOTH destination player sprite [5:7, 7:9] AND every crop pixel whose bilinear shift
    touches [5:7, 7:9] with positive weight (8 masked / 88 clean terrain pixels per direction)."""
    dest_sprite = _PLAYER_SPRITE_GLOBAL[0, 2:10, 2:14, 0] > 0.0
    masks = {}
    for q, (dy, dx) in MOVE_DIRS.items():
        src_sprite = _bilinear_terrain_shift(_PLAYER_SPRITE_GLOBAL, dy, dx)[0, :, :, 0] > 0.0
        keep = ~(dest_sprite | src_sprite)
        masks[q] = np.repeat(keep[:, :, None], 3, axis=2)
    return masks


_TERRAIN_MASK_BY_DIR = _build_terrain_masks_by_dir()


def classify_move_displacement(x_start, x_next, act_arr,
                               alpha_thresh=BLOCK_OPEN_ALPHA_THRESH,
                               min_shift_energy=BLOCK_OPEN_MIN_SHIFT_ENERGY):
    """100% visual, prediction-blind terrain-displacement readout for move actions (1..4).

    Projects (x_next - x_start) onto the expected 1-tile shift vector s = shift(x_start, dir) - x_start
    over the HUD-masked interior terrain, masking BOTH the destination 2x2 player sprite [5:7, 7:9]
    and the bilinear-shifted source footprint of [5:7, 7:9] so the static centered sprite never bleeds
    phantom shift energy into adjacent terrain.
    Returns:
      valid_move: bool [N] (act in 1..4 AND shift energy mean(s^2) >= min_shift_energy)
      is_open:    bool [N] (alpha = <df, s> / <s, s> >= alpha_thresh)
      alpha:      float64 [N]
    """
    x_start = np.asarray(x_start, dtype=np.float64)
    x_next = np.asarray(x_next, dtype=np.float64)
    act_arr = np.asarray(act_arr, dtype=np.int64)
    n = len(act_arr)
    valid_move = np.zeros(n, dtype=bool)
    is_open = np.zeros(n, dtype=bool)
    alpha = np.zeros(n, dtype=np.float64)

    for q, (dy, dx) in MOVE_DIRS.items():
        sel = act_arr == q
        if not sel.any():
            continue
        xs = x_start[sel]
        xn = x_next[sel]
        x0c = xs[:, 2:10, 2:14, :]
        x1c = xn[:, 2:10, 2:14, :]
        sh = _bilinear_terrain_shift(xs, dy, dx)
        m3 = _TERRAIN_MASK_BY_DIR[q]
        df = (x1c - x0c)[:, m3]
        s = (sh - x0c)[:, m3]
        sn = (s * s).mean(axis=1)
        dot = (df * s).mean(axis=1)
        al = dot / np.maximum(sn, 1e-12)
        v = sn >= min_shift_energy
        valid_move[sel] = v
        alpha[sel] = al
        is_open[sel] = v & (al >= alpha_thresh)
    return valid_move, is_open, alpha


def score_block_open(x0, pred_k1, true_k1, acts_k1, world_ids):
    """Compute false-block, false-open, mean_err, and world bootstrap CI using the exact same
    visual displacement readout on ground truth (x0 -> true_k1) and predictor (x0 -> pred_k1).
    """
    valid, true_open, _ = classify_move_displacement(x0, true_k1, acts_k1)
    _, pred_open, _ = classify_move_displacement(x0, pred_k1, acts_k1)
    to = true_open[valid]
    po = pred_open[valid]
    wi = np.asarray(world_ids, dtype=np.int64)[valid]

    n_valid = int(valid.sum())
    n_open = int(to.sum())
    n_blocked = int((~to).sum())
    n_fb = int((~po & to).sum())
    n_fo = int((po & ~to).sum())
    fb = float(n_fb / max(n_open, 1))
    fo = float(n_fo / max(n_blocked, 1))
    mean_err = 0.5 * (fb + fo)

    # World-level paired bootstrap CI (exclude undefined replicates with 0 open or 0 blocked)
    worlds = np.unique(wi)
    if len(worlds) >= 2 and n_open > 0 and n_blocked > 0:
        w_fb = np.array([(~po & to)[wi == w].sum() for w in worlds], dtype=np.float64)
        w_op = np.array([to[wi == w].sum() for w in worlds], dtype=np.float64)
        w_fo = np.array([(po & ~to)[wi == w].sum() for w in worlds], dtype=np.float64)
        w_bl = np.array([(~to)[wi == w].sum() for w in worlds], dtype=np.float64)
        rng = np.random.default_rng(103)
        idx = rng.integers(0, len(worlds), size=(1000, len(worlds)))
        op_s = w_op[idx].sum(axis=1)
        bl_s = w_bl[idx].sum(axis=1)
        valid_rep = (op_s > 0.0) & (bl_s > 0.0)
        if valid_rep.any():
            b_fb = w_fb[idx][valid_rep].sum(axis=1) / op_s[valid_rep]
            b_fo = w_fo[idx][valid_rep].sum(axis=1) / bl_s[valid_rep]
            b_me = 0.5 * (b_fb + b_fo)
            ci95 = [float(np.percentile(b_me, 2.5)), float(np.percentile(b_me, 97.5))]
        else:
            ci95 = [mean_err, mean_err]
    else:
        ci95 = [mean_err, mean_err]

    return {
        "valid_moves": n_valid,
        "true_open": n_open,
        "true_blocked": n_blocked,
        "false_block_rate": fb,
        "false_open_rate": fo,
        "mean_err": mean_err,
        "mean_err_ci95_worlds": ci95,
    }


def fit_linear_action_baseline(train):
    xi1, ai1, _, _, _ = windows(train, 1)
    Xa = train["frames"][xi1].astype(np.float64).reshape(len(xi1), -1)
    Ya = train["frames"][xi1 + 1].astype(np.float64).reshape(len(xi1), -1)
    aa = train["actions"][ai1]
    Mact = {}
    for q in range(17):
        sel = aa == q
        if sel.sum() == 0:
            Mact[q] = np.vstack([np.eye(768), np.zeros((1, 768))])
        else:
            Xq = np.c_[Xa[sel], np.ones(sel.sum())]
            Mact[q] = np.linalg.solve(Xq.T @ Xq + 1.0 * np.eye(769), Xq.T @ Ya[sel])
    return Mact


def rollout_linear_action_baseline(Mact, x0, acts_k):
    x = np.asarray(x0, dtype=np.float64).reshape(len(x0), -1).copy()
    for j in range(acts_k.shape[1]):
        nx = np.empty_like(x)
        for q in range(17):
            sel = acts_k[:, j] == q
            if sel.any():
                nx[sel] = np.c_[x[sel], np.ones(sel.sum())] @ Mact[q]
        x = nx
    return x.reshape(-1, 16, 16, 3)


def fit_shift_or_stay_baseline(train):
    """Cheap physics baseline (Astra Rung-1 bar):
    For 4-way moves (1..4), fits strictly on train data using the fixed visual displacement labels:
      (a) a linear shift model on valid open-move transitions, and
      (b) a ridge probability predictor from the player-centered 6x6 crop (rows 3:9, cols 5:11,
          symmetrically spanning 2 rows/cols around the [5:7, 7:9] player sprite) predicting whether
          the move shifts or stays blocked; blends p_move * shift + (1 - p_move) * x.
    Non-move actions fall back to per-action linear ridge.
    """
    xi1, ai1, _, _, _ = windows(train, 1)
    fr = train["frames"].astype(np.float64)
    X_img = fr[xi1]
    Y_img = fr[xi1 + 1]
    Xa = X_img.reshape(len(xi1), -1)
    Ya = Y_img.reshape(len(xi1), -1)
    aa = train["actions"][ai1]
    valid_mv, is_open_mv, _ = classify_move_displacement(X_img, Y_img, aa)
    Mact = fit_linear_action_baseline(train)
    Mshift = {}
    Wgate = {}
    for q in (1, 2, 3, 4):
        sel_val = (aa == q) & valid_mv
        sel_mv = sel_val & is_open_mv
        if sel_mv.sum() >= 20:
            Xq = np.c_[Xa[sel_mv], np.ones(sel_mv.sum())]
            Mshift[q] = np.linalg.solve(Xq.T @ Xq + 1.0 * np.eye(769), Xq.T @ Ya[sel_mv])
        else:
            Mshift[q] = Mact[q]
        if sel_val.sum() == 0:
            Wgate[q] = np.zeros(109, dtype=np.float64)
        else:
            crop = X_img[sel_val, 3:9, 5:11, :].reshape(int(sel_val.sum()), 108)
            Xc = np.c_[crop, np.ones(sel_val.sum())]
            yc = is_open_mv[sel_val].astype(np.float64)
            Wgate[q] = np.linalg.solve(Xc.T @ Xc + 10.0 * np.eye(Xc.shape[1]), Xc.T @ yc)
    return {"Mact": Mact, "Mshift": Mshift, "Wgate": Wgate}


def rollout_shift_or_stay(sos, x0, acts_k):
    x_img = np.asarray(x0, dtype=np.float64).copy()
    for j in range(acts_k.shape[1]):
        x_flat = x_img.reshape(len(x_img), -1)
        nx = np.empty_like(x_flat)
        for q in range(17):
            sel = acts_k[:, j] == q
            if not sel.any():
                continue
            if q in (1, 2, 3, 4):
                crop = x_img[sel, 3:9, 5:11, :].reshape(sel.sum(), -1)
                p_mv = np.clip(np.c_[crop, np.ones(sel.sum())] @ sos["Wgate"][q], 0.0, 1.0)[:, None]
                x_sh = np.c_[x_flat[sel], np.ones(sel.sum())] @ sos["Mshift"][q]
                nx[sel] = p_mv * x_sh + (1.0 - p_mv) * x_flat[sel]
            else:
                nx[sel] = np.c_[x_flat[sel], np.ones(sel.sum())] @ sos["Mact"][q]
        x_img = nx.reshape(-1, 16, 16, 3)
    return x_img


def world_bootstrap_ci(world_ids, num_per_sample, den_per_sample, n_boot=1000, seed=101):
    """Paired 95% bootstrap CI across unique worlds for sum(num) / sum(den)."""
    worlds = np.unique(world_ids)
    w_num = np.array([num_per_sample[world_ids == w].sum() for w in worlds], dtype=np.float64)
    w_den = np.array([den_per_sample[world_ids == w].sum() for w in worlds], dtype=np.float64)
    if len(worlds) < 2:
        val = float(w_num.sum() / max(w_den.sum(), 1e-12))
        return [val, val]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(worlds), size=(n_boot, len(worlds)))
    num_s = w_num[idx].sum(axis=1)
    den_s = w_den[idx].sum(axis=1)
    valid = den_s > 1e-12
    if not valid.any():
        val = float(w_num.sum() / max(w_den.sum(), 1e-12))
        return [val, val]
    ratios = num_s[valid] / den_s[valid]
    lo, hi = np.percentile(ratios, [2.5, 97.5])
    return [float(lo), float(hi)]


def summarize_std_by_action(dP, dY, a0, active_std_threshold=0.02):
    """Summarize per-action change scale, variance, and Kish effective event count."""
    dP = np.asarray(dP, dtype=np.float64)
    dY = np.asarray(dY, dtype=np.float64)
    a0 = np.asarray(a0, dtype=np.int64)
    per_win_e = (dY * dY).mean(axis=1)
    out = {}
    for q in range(17):
        sel = a0 == q
        cnt = int(sel.sum())
        if cnt < 20:
            continue
        sp = float(dP[sel].std())
        sr = float(dY[sel].std())
        ratio = 1.0 if (sr < 1e-12 and sp < 1e-12) else float(sp / (sr + 1e-12))
        e_q = per_win_e[sel]
        sum_e = float(e_q.sum())
        sumsq_e = float((e_q * e_q).sum())
        neff = 0.0 if sumsq_e == 0.0 else float((sum_e * sum_e) / sumsq_e)
        out[str(q)] = {
            "n": cnt,
            "std_pred": sp,
            "std_real": sr,
            "ratio": ratio,
            "active": bool(sr >= active_std_threshold),
            "kish_neff": neff,
            "sum_pred": float(dP[sel].sum()),
            "sumsq_pred": float((dP[sel] * dP[sel]).sum()),
            "sum_real": float(dY[sel].sum()),
            "sumsq_real": float((dY[sel] * dY[sel]).sum()),
            "sum_change_energy": sum_e,
            "sumsq_change_energy": sumsq_e,
        }
    return out


def decide_std_gate(std_by_action, active_std_threshold=0.02):
    """Apply the adopted n200_or_neff10 gate while retaining the old-ruler result."""
    active = {q: v["ratio"] for q, v in std_by_action.items() if v["active"]}
    tot_n = sum(v["n"] for v in std_by_action.values())
    fw = float(sum(v["n"] * v["ratio"] for v in std_by_action.values()) / max(tot_n, 1))
    fw_ok = bool(0.25 <= fw <= 2.0)
    old_ok = bool(active and all(0.25 <= r <= 2.0 for r in active.values()) and fw_ok)

    individual = {}
    pooled_qs = []
    for q, v in std_by_action.items():
        if v["n"] >= 200 or v["kish_neff"] >= 10.0:
            if v["active"]:
                individual[q] = v["ratio"]
        elif v["active"]:
            pooled_qs.append(int(q))

    pool = None
    if pooled_qs:
        vals = [std_by_action[str(q)] for q in pooled_qs]
        n = sum(v["n"] for v in vals)
        entries = sum(v["n"] for v in vals) * 768
        sum_pred = sum(v["sum_pred"] for v in vals)
        sumsq_pred = sum(v["sumsq_pred"] for v in vals)
        sum_real = sum(v["sum_real"] for v in vals)
        sumsq_real = sum(v["sumsq_real"] for v in vals)
        sum_e = sum(v["sum_change_energy"] for v in vals)
        sumsq_e = sum(v["sumsq_change_energy"] for v in vals)
        std_pred = float(np.sqrt(max(sumsq_pred / entries - (sum_pred / entries) ** 2, 0.0)))
        std_real = float(np.sqrt(max(sumsq_real / entries - (sum_real / entries) ** 2, 0.0)))
        ratio = 1.0 if (std_real < 1e-12 and std_pred < 1e-12) else float(std_pred / (std_real + 1e-12))
        neff = 0.0 if sumsq_e == 0.0 else float((sum_e * sum_e) / sumsq_e)
        energy_shares = {
            str(q): float(std_by_action[str(q)]["sum_change_energy"] / sum_e) if sum_e > 0.0 else 0.0
            for q in pooled_qs
        }
        dominant_collapse = sorted(
            q for q in pooled_qs
            if std_by_action[str(q)]["ratio"] < 0.25 and energy_shares[str(q)] >= 0.25
        )
        pool = {
            "actions": pooled_qs,
            "n": int(n),
            "std_pred": std_pred,
            "std_real": std_real,
            "ratio": ratio,
            "kish_neff": neff,
            "active": bool(std_real >= active_std_threshold),
            "energy_shares": energy_shares,
            "dominant_collapse_actions": dominant_collapse,
        }

    amended_ok = bool(
        individual
        and all(0.25 <= r <= 2.0 for r in individual.values())
        and (pool is None or not pool["active"] or 0.25 <= pool["ratio"] <= 2.0)
        and (pool is None or not pool["dominant_collapse_actions"])
        and fw_ok
    )
    return {
        "version": "n200_or_neff10",
        "old_ok": old_ok,
        "old_active_actions": sorted(int(q) for q in active),
        "old_fail_actions": sorted(int(q) for q, r in active.items() if not (0.25 <= r <= 2.0)),
        "amended_ok": amended_ok,
        "individual_ratios": individual,
        "individual_fail_actions": sorted(int(q) for q, r in individual.items() if not (0.25 <= r <= 2.0)),
        "pool": pool,
        "freq_weighted_std_ratio": fw,
        "freq_weighted_ok": fw_ok,
    }


def classify_strike(
    verdict,
    *,
    ok1,
    r1_b1,
    ok3,
    r1_b3,
    r1_bo,
    okS1,
    okSb,
    r1_shuf_pool1,
    okstd,
    okpc,
    okceil,
    proves_wrong,
    std_gate,
):
    """Classify a scored verdict as LINE, VARIANT, or NONE with explicit reasons."""
    if verdict in ("PASS", "PARTIAL"):
        return "NONE", []
    reasons = []
    if not ok1 or not r1_b1:
        reasons.append("k1_accuracy_or_baseline")
    if not ok3 or not r1_b3:
        reasons.append("k3_accuracy_or_baseline")
    if not r1_bo:
        reasons.append("block_open")
    if not okS1 or not okSb or not r1_shuf_pool1 or proves_wrong:
        reasons.append("shuffle_or_worlds")
    if not okceil:
        reasons.append("ceiling")
    if not okpc:
        reasons.append("pcs")
    if std_gate["individual_fail_actions"]:
        reasons.append("std_high_count_or_concentrated")
    if not std_gate["freq_weighted_ok"]:
        reasons.append("std_frequency_weighted")
    if reasons:
        return "LINE", reasons

    rare_reasons = []
    pool = std_gate["pool"]
    if pool is not None and pool["active"] and not (0.25 <= pool["ratio"] <= 2.0):
        rare_reasons.append("std_rare_pool_ratio")
    if pool is not None and pool["dominant_collapse_actions"]:
        rare_reasons.append("std_rare_pool_energy_dominance")
    if not std_gate["individual_ratios"]:
        rare_reasons.append("std_no_individual_active")
    if not okstd:
        return "VARIANT", rare_reasons or ["std_gate"]
    return "LINE", ["unclassified_fail"]


def score_predictions(
    train,
    held,
    preds_by_k,
    shuf_preds_by_k,
    ceiling_abs_pred_k1=None,
    ceiling_res_pred_k1=None,
    active_std_threshold=0.02,
    extra_meta=None,
):
    """Score predictions on held-out worlds using fixed forecast5 rules (Rung 0 + Rung 1)."""
    xi1_tr = windows(train, 1)[0]
    mean_tr = train["frames"][xi1_tr].astype(np.float64).mean(0)
    hfr = held["frames"].astype(np.float64)

    Mact = fit_linear_action_baseline(train)
    sos = fit_shift_or_stay_baseline(train)

    res = {
        "scorer_version": "forecast7-v2-rung1-n200_or_neff10",
        "active_std_threshold": active_std_threshold,
        "block_open_alpha_thresh": BLOCK_OPEN_ALPHA_THRESH,
        "block_open_min_shift_energy": BLOCK_OPEN_MIN_SHIFT_ENERGY,
    }
    if extra_meta:
        res.update(extra_meta)

    for k in (1, 3, 5):
        xk_tr = windows(train, k)[0]
        xs_tr = train["frames"][xk_tr].astype(np.float64)
        ys_tr = train["frames"][xk_tr + k].astype(np.float64)
        dd_tr = xs_tr - mean_tr
        den_tr = float((dd_tr * dd_tr).sum())
        bl = float(((ys_tr - mean_tr) * dd_tr).sum() / den_tr) if den_tr > 0 else 0.0

        xi, ai, wi, _, _ = windows(held, k)
        acts_k = action_values(held["actions"], ai, k)
        x0 = hfr[xi]
        yk = hfr[xi + k]
        P = np.asarray(preds_by_k[k], dtype=np.float64)
        Ps = np.asarray(shuf_preds_by_k[k], dtype=np.float64)
        assert P.shape == yk.shape and Ps.shape == yk.shape, f"shape mismatch at k={k}"

        pe = ((P - yk) ** 2).sum((1, 2, 3))
        pse = ((Ps - yk) ** 2).sum((1, 2, 3))
        cpe = ((x0 - yk) ** 2).sum((1, 2, 3))
        bse = ((mean_tr + bl * (x0 - mean_tr) - yk) ** 2).sum((1, 2, 3))

        E = float(pe.sum())
        cp = float(cpe.sum())
        bs = float(bse.sum())
        B = min(cp, bs)
        be = cpe if cp <= bs else bse

        mv_k = ((yk - x0) ** 2).mean((1, 2, 3)) > 1e-6
        mv_step1 = ((hfr[xi + 1] - x0) ** 2).mean((1, 2, 3)) > 1e-6

        wr = {}
        for w in np.unique(wi):
            m_w = mv_k & (wi == w)
            if m_w.any():
                wr[str(int(w))] = float(pse[m_w].sum() / max(pe[m_w].sum(), 1e-12))

        P_act = rollout_linear_action_baseline(Mact, x0, acts_k)
        P_sos = rollout_shift_or_stay(sos, x0, acts_k)
        pe_act = ((P_act - yk) ** 2).sum((1, 2, 3))
        pe_sos = ((P_sos - yk) ** 2).sum((1, 2, 3))
        E_act = float(pe_act.sum())
        E_sos = float(pe_sos.sum())
        best_base_is = "shift_or_stay" if E_sos <= E_act else "linear_Mact"
        pe_best_base = pe_sos if E_sos <= E_act else pe_act
        E_best_base = min(E_act, E_sos)

        dP_sq = float(((P - x0) ** 2).sum())
        dY_sq = float(((yk - x0) ** 2).sum())

        r = {
            "windows": int(len(xi)),
            "moved_k_windows": int(mv_k.sum()),
            "moved_step1_windows": int(mv_step1.sum()),
            "E": E,
            "copy_SSE": cp,
            "blend_SSE": bs,
            "B": B,
            "B_is": "copy" if cp <= bs else "blend",
            "blend_a": bl,
            "E_over_B": E / max(B, 1e-12),
            "E_over_B_ci95_worlds": world_bootstrap_ci(wi, pe, be),
            "moved_E_over_B": float(pe[mv_k].sum() / max(min(cpe[mv_k].sum(), bse[mv_k].sum()), 1e-12)),
            "shuffle_pooled": float(pse[mv_k].sum() / max(pe[mv_k].sum(), 1e-12)),
            "shuffle_pooled_ci95_worlds": world_bootstrap_ci(wi[mv_k], pse[mv_k], pe[mv_k]),
            "shuffle_world_ratios": wr,
            "act_baseline_E_over_B": E_act / max(B, 1e-12),
            "act_baseline_E_over_E": E / max(E_act, 1e-12),
            "shift_or_stay_E_over_B": E_sos / max(B, 1e-12),
            "shift_or_stay_E_over_E": E / max(E_sos, 1e-12),
            "strongest_baseline_is": best_base_is,
            "strongest_baseline_E_over_B": E_best_base / max(B, 1e-12),
            "E_over_strongest_baseline": E / max(E_best_base, 1e-12),
            "E_over_strongest_baseline_ci95_worlds": world_bootstrap_ci(wi, pe, pe_best_base, seed=107 + k),
            "copy_ness": dP_sq / max(dY_sq, 1e-12),
            "mean_signed_bias": float((P - yk).mean()),
            "rmse": float(np.sqrt(np.mean((P - yk) ** 2))),
        }

        if k == 1:
            if ceiling_abs_pred_k1 is not None:
                c_abs = float(((np.asarray(ceiling_abs_pred_k1, dtype=np.float64) - yk) ** 2).sum() / max(B, 1e-12))
            else:
                c_abs = 0.0
            if ceiling_res_pred_k1 is not None:
                c_res = float(((np.asarray(ceiling_res_pred_k1, dtype=np.float64) - yk) ** 2).sum() / max(B, 1e-12))
            else:
                c_res = c_abs
            r["ceiling_provided"] = bool(ceiling_abs_pred_k1 is not None)
            r["ceiling_abs_E_over_B"] = c_abs
            r["ceiling_res_E_over_B"] = c_res
            r["ceiling_real_board_E_over_B"] = c_abs

            dP = (P - x0).reshape(len(P), -1)
            dY = (yk - x0).reshape(len(yk), -1)
            r["pcs90_pred"] = int(pcs90(dP))
            r["pcs90_real"] = int(pcs90(dY))

            a0 = acts_k[:, 0]
            std_by_action = summarize_std_by_action(dP, dY, a0, active_std_threshold)
            active_ratios = [v["ratio"] for v in std_by_action.values() if v["active"]]
            tot_n = sum(v["n"] for v in std_by_action.values())
            fw_ratio = float(sum(v["n"] * v["ratio"] for v in std_by_action.values()) / max(tot_n, 1))
            gate = decide_std_gate(std_by_action, active_std_threshold)
            r["std_ratio_by_action"] = std_by_action
            r["active_std_ratios"] = active_ratios
            r["freq_weighted_std_ratio"] = fw_ratio
            r["std_ratio_all_n20_ok"] = bool(std_by_action and all(0.25 <= v["ratio"] <= 2.0 for v in std_by_action.values()))
            r["std_ratio_old_active_and_fw_ok"] = gate["old_ok"]
            r["std_gate"] = gate
            r["std_ratio_active_and_fw_ok"] = gate["amended_ok"]

            # Rung-1 blocked-vs-open visual terrain-displacement readout (blind to predictors)
            bo_model = score_block_open(x0, P, yk, a0, wi)
            bo_copy = score_block_open(x0, x0, yk, a0, wi)
            bo_act = score_block_open(x0, P_act, yk, a0, wi)
            bo_sos = score_block_open(x0, P_sos, yk, a0, wi)
            bo_best_name = "shift_or_stay" if bo_sos["mean_err"] <= bo_act["mean_err"] else "linear_Mact"
            bo_best = bo_sos if bo_sos["mean_err"] <= bo_act["mean_err"] else bo_act
            both_classes = (bo_model["true_open"] > 0) and (bo_model["true_blocked"] > 0)
            if both_classes and bo_best["mean_err"] > 0.0:
                cut_frac = 1.0 - (bo_model["mean_err"] / bo_best["mean_err"])
                bo_ok = bool(
                    bo_model["mean_err"] <= 0.75 * bo_best["mean_err"]
                    and bo_model["false_block_rate"] <= bo_best["false_block_rate"]
                    and bo_model["false_open_rate"] <= bo_best["false_open_rate"]
                )
            else:
                cut_frac = 0.0
                bo_ok = False
            r["block_open"] = {
                "model": bo_model,
                "copy": bo_copy,
                "linear_Mact": bo_act,
                "shift_or_stay": bo_sos,
                "strongest_baseline_is": bo_best_name,
                "strongest_baseline_mean_err": bo_best["mean_err"],
                "mean_err_reduction_frac": float(cut_frac),
                "cut_ge_25pct_neither_worse": bo_ok,
            }
        res[f"k{k}"] = r

    k1, k3, k5 = res["k1"], res["k3"], res["k5"]
    n1 = sum(v >= 1.25 for v in k1["shuffle_world_ratios"].values())
    n5 = sum(v >= 1.10 for v in k5["shuffle_world_ratios"].values())
    nboth = sum(
        1 for w, v1 in k1["shuffle_world_ratios"].items()
        if v1 >= 1.25 and k5["shuffle_world_ratios"].get(w, 0.0) >= 1.10
    )

    ceil_gate = k1["ceiling_abs_E_over_B"]
    ok1 = k1["E_over_B"] <= 0.80
    ok3 = k3["E_over_B"] <= 0.90
    ok5 = k5["E_over_B"] <= 0.95
    okS1 = n1 >= 12
    okSb = nboth >= 12
    okstd = k1["std_ratio_active_and_fw_ok"]
    okpc = k1["pcs90_pred"] >= 0.5 * k1["pcs90_real"]
    okceil = ceil_gate <= 0.70
    proves_wrong = bool(ok1 and k1["shuffle_pooled"] < 1.05)

    # Legacy verdict (unchanged from Rung 0)
    full = ok1 and ok3 and ok5 and okS1 and okSb and okstd and okpc and okceil and (not proves_wrong)
    partial = (
        (not full) and ok1 and ok3 and okS1 and okSb and okstd and okpc and okceil
        and (not proves_wrong) and (not ok5)
    )
    if ceil_gate > 0.95 or proves_wrong:
        verdict = "FAIL"
    elif full:
        verdict = "PASS"
    elif partial:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    # Rung-1 strict physics verdict (beats linear_Mact AND shift_or_stay at k=1/3/5 + >=25% block/open cut + legacy gates)
    r1_b1 = bool(k1["E_over_B"] < k1["strongest_baseline_E_over_B"])
    r1_b3 = bool(k3["E_over_B"] < k3["strongest_baseline_E_over_B"])
    r1_b5 = bool(k5["E_over_B"] < k5["strongest_baseline_E_over_B"])
    r1_bo = bool(k1["block_open"]["cut_ge_25pct_neither_worse"])
    r1_shuf_pool1 = bool(k1["shuffle_pooled"] >= 1.25)
    r1_full = (
        ok1 and ok3 and ok5 and r1_b1 and r1_b3 and r1_b5 and r1_bo
        and okS1 and okSb and r1_shuf_pool1 and okstd and okpc and okceil and (not proves_wrong)
    )
    r1_partial = (
        (not r1_full) and ok1 and ok3 and r1_b1 and r1_b3 and r1_bo
        and okS1 and okSb and r1_shuf_pool1 and okstd and okpc and okceil
        and (not proves_wrong) and ((not ok5) or (not r1_b5))
    )
    if ceil_gate > 0.95 or proves_wrong:
        r1_verdict = "FAIL"
    elif r1_full:
        r1_verdict = "PASS"
    elif r1_partial:
        r1_verdict = "PARTIAL"
    else:
        r1_verdict = "FAIL"

    # Explicit PLAN-AMENDMENT.md §6.3 Rank-3 stop trigger
    bo_m_err = k1["block_open"]["model"]["mean_err"]
    bo_sos_err = k1["block_open"]["shift_or_stay"]["mean_err"]
    rank3_proved_wrong = bool(
        (ceil_gate > 0.95)
        or proves_wrong
        or (k1["E_over_B"] >= k1["act_baseline_E_over_B"])
        or (k1["shuffle_pooled"] < 1.25)
        or (not okS1)
        or (k1["ceiling_provided"] and ceil_gate <= 0.25 and bo_m_err >= bo_sos_err)
    )
    strike_class, strike_reasons = classify_strike(
        r1_verdict,
        ok1=ok1,
        r1_b1=r1_b1,
        ok3=ok3,
        r1_b3=r1_b3,
        r1_bo=r1_bo,
        okS1=okS1,
        okSb=okSb,
        r1_shuf_pool1=r1_shuf_pool1,
        okstd=okstd,
        okpc=okpc,
        okceil=okceil,
        proves_wrong=proves_wrong,
        std_gate=k1["std_gate"],
    )

    res.update({
        "worlds_k1_shuffle": int(n1),
        "worlds_k5_shuffle": int(n5),
        "worlds_both": int(nboth),
        "strike_class": strike_class,
        "strike_reasons": strike_reasons,
        "marks": {
            "ceiling_le_0.70": bool(okceil),
            "ceiling_gt_0.95": bool(ceil_gate > 0.95),
            "k1_E_over_B_le_0.80": bool(ok1),
            "k3_E_over_B_le_0.90": bool(ok3),
            "k5_E_over_B_le_0.95": bool(ok5),
            "worlds_k1_ge_12": bool(okS1),
            "worlds_both_ge_12": bool(okSb),
            "std_ok": bool(okstd),
            "pcs_ok": bool(okpc),
            "proves_wrong": bool(proves_wrong),
        },
        "rung1_marks": {
            "ceiling_le_0.70": bool(okceil),
            "k1_beats_baselines": r1_b1,
            "k3_beats_baselines": r1_b3,
            "k5_beats_baselines": r1_b5,
            "block_open_cut_ge_25pct_neither_worse": r1_bo,
            "k1_shuffle_pooled_ge_1.25": r1_shuf_pool1,
            "worlds_k1_ge_12": bool(okS1),
            "worlds_both_ge_12": bool(okSb),
            "std_ok": bool(okstd),
            "pcs_ok": bool(okpc),
            "proves_wrong": bool(proves_wrong),
            "rank3_proved_wrong": rank3_proved_wrong,
        },
        "pcs_ok": bool(okpc),
        "std_ok": bool(okstd),
        "proves_wrong": bool(proves_wrong),
        "rank3_proved_wrong": rank3_proved_wrong,
        "verdict": verdict,
        "rung1_verdict": r1_verdict,
    })
    return res


def _synthetic_shift_full(img, dy, dx):
    """Exact wrap-padded bilinear shift of a full 16x16x3 synthetic frame."""
    ys = (np.arange(16, dtype=np.float64) + dy) % 16.0
    xs = (np.arange(16, dtype=np.float64) + dx) % 16.0
    y0 = np.floor(ys).astype(int)
    wy = (ys - y0)[:, None, None]
    x0 = np.floor(xs).astype(int)
    wx = (xs - x0)[None, :, None]
    y1 = (y0 + 1) % 16
    x1 = (x0 + 1) % 16
    top = (1.0 - wx) * img[y0[:, None], x0[None, :], :] + wx * img[y0[:, None], x1[None, :], :]
    bot = (1.0 - wx) * img[y1[:, None], x0[None, :], :] + wx * img[y1[:, None], x1[None, :], :]
    return (1.0 - wy) * top + wy * bot


def make_synthetic_split(worlds, steps_per_world, seed):
    """Synthetic Crafter-like worlds with both OPEN (1.75px terrain shift) and BLOCKED moves
    (determined nonlinearly by center-neighbor brightness so linear baselines make errors while
    a true physics predictor gets 0 error)."""
    rng = np.random.default_rng(seed)
    frames, actions, eid, wid, tid = [], [], [], [], []
    for j, w in enumerate(worlds):
        f = np.zeros((steps_per_world + 1, 16, 16, 3), dtype=np.float64)
        # Smoothly textured terrain on rows 0..11 + static HUD on rows 12..15
        base = rng.uniform(0.15, 0.85, size=(16, 16, 3))
        base[12:, :, :] = 0.2
        f[0] = base
        acts = rng.integers(0, 17, size=steps_per_world)
        for t in range(steps_per_world):
            a = int(acts[t])
            if a in MOVE_DIRS:
                # Nonlinear obstacle test on center-adjacent pixel (blocked ~35% of moves)
                dy, dx = MOVE_DIRS[a]
                ny = int(np.clip(round(6 + np.sign(dy) * 2), 0, 11))
                nx = int(np.clip(round(8 + np.sign(dx) * 2), 0, 15))
                # Blocked if XOR of R>0.5 and B>0.5 at adjacent tile (~50% -> clamp to ~35% via G<0.7)
                c = f[t, ny, nx]
                blocked = ((c[0] > 0.5) ^ (c[2] > 0.5)) and (c[1] < 0.72)
                if blocked:
                    f[t + 1] = f[t].copy()
                else:
                    nxt = _synthetic_shift_full(f[t], dy, dx)
                    nxt[12:, :, :] = 0.2
                    f[t + 1] = nxt
            elif a == 5:
                nxt = np.clip(f[t] + rng.normal(0, 0.03, size=(16, 16, 3)), 0.0, 1.0)
                nxt[12:, :, :] = 0.2
                f[t + 1] = nxt
            else:
                nxt = np.clip(f[t] + rng.normal(0, 0.004, size=(16, 16, 3)), 0.0, 1.0)
                nxt[12:, :, :] = 0.2
                f[t + 1] = nxt
        frames.append(f)
        actions.append(acts)
        eid.append(np.full(steps_per_world + 1, j, dtype=np.int64))
        wid.append(np.full(steps_per_world + 1, w, dtype=np.int64))
        tid.append(np.arange(steps_per_world + 1, dtype=np.int64))
    return {
        "frames": np.concatenate(frames).astype(np.float32),
        "actions": np.concatenate(actions).astype(np.int64),
        "episode_id": np.concatenate(eid),
        "world_id": np.concatenate(wid),
        "t_index": np.concatenate(tid),
    }


def run_selftest():
    """Run all 5 Rung-0 synthetic drift & Bug A10/A11 checks + Rung-1 block-open & baseline checks."""
    tr = make_synthetic_split(list(range(8)), 100, seed=1)
    he = make_synthetic_split([1000 + i for i in range(16)], 100, seed=2)
    hfr = he["frames"].astype(np.float64)
    sh_acts = shuffle_actions_per_step(he, seed=43)

    def open_loop_sim(mode, bias_c=0.0):
        preds, shuf_preds = {}, {}
        for k in (1, 3, 5):
            xi, ai, _, _, _ = windows(he, k)
            x0 = hfr[xi]
            if mode == "perfect":
                delta_sum = np.zeros_like(x0)
                for step in range(k):
                    delta_sum += (hfr[xi + step + 1] - hfr[xi + step]) + bias_c
                P = x0 + delta_sum
                a_sh = action_values(sh_acts, ai, k)
                Ps = x0.copy()
                for step in range(k):
                    nxt = Ps.copy()
                    for q, (dy, dx) in MOVE_DIRS.items():
                        sel = a_sh[:, step] == q
                        if sel.any():
                            for idx_s in np.flatnonzero(sel):
                                shf = _synthetic_shift_full(Ps[idx_s], dy, dx)
                                shf[12:, :, :] = 0.2
                                nxt[idx_s] = shf
                    Ps = nxt
            elif mode == "zero":
                P = x0.copy()
                Ps = x0.copy()
            elif mode == "action_blind_perfect":
                P = hfr[xi + k].copy()
                Ps = P.copy()
            else:
                raise ValueError(mode)
            preds[k] = P
            shuf_preds[k] = Ps
        return preds, shuf_preds

    # Check 1: Perfect deltas -> zero absolute error at k=1,3,5, PASS both legacy & Rung 1, 0% block/open err
    p1, ps1 = open_loop_sim("perfect", bias_c=0.0)
    r_perf = score_predictions(tr, he, p1, ps1)
    for k in (1, 3, 5):
        assert r_perf[f"k{k}"]["E"] < 1e-12, f"Check 1 failed at k={k}: E={r_perf[f'k{k}']['E']}"
    assert r_perf["verdict"] == "PASS", f"Check 1 legacy verdict expected PASS, got {r_perf['verdict']}"
    assert r_perf["rung1_verdict"] == "PASS", f"Check 1 rung1 verdict expected PASS, got {r_perf['rung1_verdict']}"
    bo_p = r_perf["k1"]["block_open"]["model"]
    assert bo_p["mean_err"] == 0.0 and bo_p["true_open"] > 50 and bo_p["true_blocked"] > 20, f"Check 1 bo: {bo_p}"
    assert r_perf["k1"]["block_open"]["copy"]["false_block_rate"] == 1.0
    assert r_perf["k1"]["block_open"]["copy"]["false_open_rate"] == 0.0
    assert abs(r_perf["k1"]["block_open"]["copy"]["mean_err"] - 0.5) < 1e-12

    # Check 2: Zero deltas -> exact copy baseline at k=1,3,5, copy_ness=0, pcs=1, FAIL both
    p0, ps0 = open_loop_sim("zero")
    r_zero = score_predictions(tr, he, p0, ps0)
    for k in (1, 3, 5):
        assert abs(r_zero[f"k{k}"]["E"] - r_zero[f"k{k}"]["copy_SSE"]) < 1e-10, f"Check 2 failed at k={k}"
        assert r_zero[f"k{k}"]["copy_ness"] == 0.0, f"Check 2 copy_ness nonzero at k={k}"
    assert r_zero["k1"]["pcs90_pred"] == 1, f"Check 2 pcs90_pred expected 1, got {r_zero['k1']['pcs90_pred']}"
    assert r_zero["std_ok"] is False and r_zero["pcs_ok"] is False
    assert r_zero["verdict"] == "FAIL" and r_zero["rung1_verdict"] == "FAIL"
    assert r_zero["k1"]["block_open"]["cut_ge_25pct_neither_worse"] is False

    # Check 3: Constant per-step bias c=0.01 -> endpoint bias == k * c at k=1,3,5 (no intermediate peeking!)
    c = 0.01
    pb, psb = open_loop_sim("perfect", bias_c=c)
    r_bias = score_predictions(tr, he, pb, psb)
    for k in (1, 3, 5):
        mb = r_bias[f"k{k}"]["mean_signed_bias"]
        rm = r_bias[f"k{k}"]["rmse"]
        assert abs(mb - k * c) < 1e-12, f"Check 3 bias failed at k={k}: {mb} vs {k*c}"
        assert abs(rm - k * c) < 1e-12, f"Check 3 rmse failed at k={k}: {rm} vs {k*c}"

    # Check 4: Action-blind accurate predictor -> proves_wrong=True, FAIL both
    pab, psab = open_loop_sim("action_blind_perfect")
    r_ab = score_predictions(tr, he, pab, psab)
    assert r_ab["proves_wrong"] is True and r_ab["verdict"] == "FAIL" and r_ab["rung1_verdict"] == "FAIL"

    # Check 5: Bug A10 fix — k1, k3, k5 E/B all pass & k1 shuffle passes, k5 shuffle fails -> FAIL (not PARTIAL)
    ps_k5_blind = {1: ps1[1], 3: ps1[3], 5: p1[5]}
    r_a10 = score_predictions(tr, he, p1, ps_k5_blind)
    assert r_a10["worlds_k1_shuffle"] >= 12 and r_a10["worlds_both"] == 0
    assert r_a10["verdict"] == "FAIL" and r_a10["rung1_verdict"] == "FAIL"

    report = {
        "selftest": "ALL_PASS",
        "scorer_version": r_perf["scorer_version"],
        "check1_perfect_E": {k: r_perf[f"k{k}"]["E"] for k in (1, 3, 5)},
        "check1_verdict": r_perf["verdict"],
        "check1_rung1_verdict": r_perf["rung1_verdict"],
        "check1_block_open": {
            "model_mean_err": bo_p["mean_err"],
            "copy_mean_err": r_perf["k1"]["block_open"]["copy"]["mean_err"],
            "sos_mean_err": r_perf["k1"]["block_open"]["shift_or_stay"]["mean_err"],
            "act_mean_err": r_perf["k1"]["block_open"]["linear_Mact"]["mean_err"],
            "true_open": bo_p["true_open"],
            "true_blocked": bo_p["true_blocked"],
        },
        "check2_zero_diff_from_copy": {k: abs(r_zero[f"k{k}"]["E"] - r_zero[f"k{k}"]["copy_SSE"]) for k in (1, 3, 5)},
        "check2_zero_pcs90_pred": r_zero["k1"]["pcs90_pred"],
        "check2_zero_copy_ness": r_zero["k1"]["copy_ness"],
        "check2_verdict": r_zero["verdict"],
        "check2_rung1_verdict": r_zero["rung1_verdict"],
        "check3_drift_bias": {k: r_bias[f"k{k}"]["mean_signed_bias"] for k in (1, 3, 5)},
        "check3_drift_rmse": {k: r_bias[f"k{k}"]["rmse"] for k in (1, 3, 5)},
        "check4_proves_wrong": r_ab["proves_wrong"],
        "check4_verdict": r_ab["verdict"],
        "check5_bugA10_verdict": r_a10["verdict"],
    }
    print(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        run_selftest()
    else:
        print("Use --selftest or import score_predictions from scorer.py")


if __name__ == "__main__":
    main()
