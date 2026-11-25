"""Read-only CPU diagnostic Part 2 for PROBLEM-7 Rank 6 (saved checkpoints s42 & s43).

Zero training, zero MPS, zero writes to M3 or model/data directories.
Probes:
  2A. Sleep-wake history check for top-change windows of actions 5, 8, 9 (and all actions).
  2B. Single-frame observability / Bayes probes on 16x16 pixels:
      - Can 16x16 player sprite decode facing direction (last move 1..4)?
      - Can x_t alone vs (x_t + last_move_dir) predict do (a=5) & place_table (a=8) changes
        (total, HUD, center 6x6, sleep-wake)?
      - What is the Ridge / kNN upper bound on non-sleep-wake do & place_table?
  2C. Saved model (s42 & s43) on TRAIN vs DEV per action (overfitting vs underfitting/Bayes).
  2D. Action-embedding geometry, counterfactual swap ||f(x, a) - f(x, noop)||, and per-action
      loss & gradient norm share at step 5000 (pure CPU backward, zero opt.step).
  2E. Exact k=1..5 open-loop rollout trajectory on ALL 4,874 dev k=5 windows (s42 & s43):
      - Step-by-step E/B, E/E_sos, block_open accuracy at step 1..5, shift alpha & lag drift
      - Newly revealed off-screen pixels vs still-in-view terrain pixels vs HUD!
      - Latent off-manifold drift ||z_k - encode(x_{t+k})|| and ||z_k||
      - Zero-training counterfactual: re-encoding snap `z <- encode(decode(z))` at each step!
      - Zero-training counterfactual: latent damping / residual snap!
"""
import os
import sys
import time
import json
import numpy as np
import torch

torch.set_grad_enabled(False)
t_global = time.time()

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer
from model_v6 import SpatialWorldModelV6

try:
    import crafter
    ACTION_NAMES = list(crafter.constants.actions)
except Exception:
    ACTION_NAMES = [f"act_{i}" for i in range(17)]

tr = scorer.load_split(os.path.join(BASE, "wm5/data/train_dn.npz"))
he = scorer.load_split(os.path.join(BASE, "wm-harness/data/heldout.npz"))
Mact = scorer.fit_linear_action_baseline(tr)
sos = scorer.fit_shift_or_stay_baseline(tr)

xi1_tr, ai1_tr, wi1_tr, ei1_tr, ti1_tr = scorer.windows(tr, 1)
a1_tr = tr["actions"][ai1_tr]
x0_tr = tr["frames"][xi1_tr].astype(np.float64)
x1_tr = tr["frames"][xi1_tr + 1].astype(np.float64)
dY_tr = x1_tr - x0_tr

xi1_he, ai1_he, wi1_he, ei1_he, ti1_he = scorer.windows(he, 1)
a1_he = he["actions"][ai1_he]
x0_he = he["frames"][xi1_he].astype(np.float64)
x1_he = he["frames"][xi1_he + 1].astype(np.float64)
dY_he = x1_he - x0_he

# ============================================================================
# 2A. TRACE SLEEP HISTORY FOR TOP-CHANGE WINDOWS OF ACTIONS 5, 8, 9
# ============================================================================
print("=== PART 2A: SLEEP-WAKE HISTORY TRACE FOR TOP WINDOWS OF ACTIONS 5, 8, 9 ===")
starts_he, ends_he, aoffs_he = scorer.episode_index(he)
# Build per-window episode start lookup
ep_info_he = {}
for s, e, ao in zip(starts_he, ends_he, aoffs_he):
    ep_info_he[int(he["episode_id"][s])] = (int(s), int(e), int(ao))

def trace_window(split, ep_info, idx, xi_arr, ai_arr, ei_arr, ti_arr):
    ep = int(ei_arr[idx])
    t = int(ti_arr[idx])
    s, e, ao = ep_info[ep]
    t_lo = max(0, t - 12)
    hist_a = split["actions"][ao + t_lo : ao + t + 1].tolist()
    hist_m = [round(float(split["frames"][s + k, :12].mean()), 3) for k in range(t_lo, t + 2)]
    # Check most recent sleep action (a=6) before t
    prev_acts = split["actions"][ao : ao + t]
    sleep_pos = np.flatnonzero(prev_acts == 6)
    steps_since_sleep = int(t - sleep_pos[-1]) if len(sleep_pos) else -1
    # Check sleep-screen signature: in Crafter sleeping turns terrain noisy/dark or low contrast
    x0 = split["frames"][s + t, :12]
    x1 = split["frames"][s + t + 1, :12]
    std0 = float(x0.std())
    std1 = float(x1.std())
    return steps_since_sleep, hist_a, hist_m, std0, std1

for q in [5, 8, 9]:
    sel = np.flatnonzero(a1_he == q)
    sse = (dY_he[sel] ** 2).sum((1, 2, 3))
    top = np.argsort(sse)[::-1][:8]
    print(f"\n--- DEV Action {q} ({ACTION_NAMES[q]}) top-8 SSE windows ---")
    for r, ki in enumerate(top):
        idx = sel[ki]
        sss, ha, hm, s0, s1 = trace_window(he, ep_info_he, idx, xi1_he, ai1_he, ei1_he, ti1_he)
        rms = float(np.sqrt(sse[ki] / 768.0))
        print(
            f"  #{r+1} t={int(ti1_he[idx]):3d} rms={rms:.4f} steps_since_sleep={sss:3d} "
            f"terrStd {s0:.3f}->{s1:.3f} | last_acts={ha[-8:]} | terrMean={hm[-6:]}"
        )

# Detect ALL sleep-wake events across train and dev!
# In Crafter, when sleeping, terrain contrast/std drops dramatically (check exact threshold from above)
# AND a=6 occurred recently. Let's inspect all rms > 0.10 non-move, non-sleep windows!
print("\n--- ALL DEV non-move, non-sleep windows with rms > 0.08 ---")
rms_he = np.sqrt((dY_he ** 2).mean((1, 2, 3)))
big_nm = np.flatnonzero((~np.isin(a1_he, [1, 2, 3, 4, 6])) & (rms_he > 0.08))
print(f"Total non-move non-sleep dev windows with rms > 0.08: {len(big_nm)}")
for idx in big_nm:
    sss, ha, hm, s0, s1 = trace_window(he, ep_info_he, idx, xi1_he, ai1_he, ei1_he, ti1_he)
    print(
        f"  a={int(a1_he[idx]):2d} ({ACTION_NAMES[int(a1_he[idx])]:<13}) w={int(wi1_he[idx])} ep={int(ei1_he[idx]):2d} "
        f"t={int(ti1_he[idx]):3d} rms={rms_he[idx]:.4f} since_sleep={sss:3d} terrStd {s0:.3f}->{s1:.3f} terrMean {hm[-2]:.3f}->{hm[-1]:.3f}"
    )

# Also check how many steps in DEV & TRAIN are while sleeping (terrStd < 0.08 and recent sleep)
print("\n--- Sleep-state anatomy (frames immediately after a=6 until wake) ---")
def analyze_sleep_episodes(split, name):
    starts, ends, aoffs = scorer.episode_index(split)
    sleep_starts = 0
    sleep_durations = []
    wake_actions = []
    still_asleep_hud_energy = []
    wake_next_hud_energy = []
    # Check HUD rows 12:16 diff between sleeping-stays-asleep vs sleeping-wakes-up
    sleep_frames_stay = []
    sleep_frames_wake = []
    for s, e, ao in zip(starts, ends, aoffs):
        L = e - s - 1
        fr = split["frames"][s:e].astype(np.float64)
        ac = split["actions"][ao:ao + L]
        t = 0
        while t < L:
            if ac[t] == 6:
                # Check if sleep actually took effect (large drop in terr std or big rms)
                d0 = np.sqrt(((fr[t + 1, :12] - fr[t, :12]) ** 2).mean())
                s0 = fr[t, :12].std()
                s1 = fr[t + 1, :12].std()
                if d0 > 0.08 and s1 < s0 * 0.6:
                    sleep_starts += 1
                    # Scan forward for wake-up (terr std jumps back up)
                    k = t + 1
                    while k < L:
                        dk = np.sqrt(((fr[k + 1, :12] - fr[k, :12]) ** 2).mean())
                        sk1 = fr[k + 1, :12].std()
                        if dk > 0.08 and sk1 > fr[k, :12].std() * 1.5:
                            sleep_durations.append(k - t)
                            wake_actions.append(int(ac[k]))
                            sleep_frames_wake.append(fr[k])
                            t = k
                            break
                        else:
                            sleep_frames_stay.append(fr[k])
                        k += 1
                    else:
                        t = k
            t += 1
    print(
        f"  {name}: detected sleep_episodes={sleep_starts}, wakes={len(wake_actions)}, "
        f"dur pcts={np.percentile(sleep_durations, [0,25,50,75,100]).tolist() if sleep_durations else []}"
    )
    if wake_actions:
        vals, cnts = np.unique(wake_actions, return_counts=True)
        print(f"     wake action counts: { {int(v): int(c) for v, c in zip(vals, cnts)} }")
    return np.array(sleep_frames_stay), np.array(sleep_frames_wake)

stay_tr, wake_tr = analyze_sleep_episodes(tr, "TRAIN")
stay_he, wake_he = analyze_sleep_episodes(he, "DEV")

# Test if HUD (or full x_t) predicts wake-up on the next step while asleep!
if len(stay_tr) > 10 and len(wake_tr) > 10 and len(stay_he) > 5 and len(wake_he) > 5:
    Xtr_sw = np.vstack([stay_tr, wake_tr]).reshape(-1, 768)
    ytr_sw = np.r_[np.zeros(len(stay_tr)), np.ones(len(wake_tr))]
    Xhe_sw = np.vstack([stay_he, wake_he]).reshape(-1, 768)
    yhe_sw = np.r_[np.zeros(len(stay_he)), np.ones(len(wake_he))]
    # Ridge classifier on full frame vs HUD-only
    for tag, sl in [("full_16x16", slice(None)), ("HUD_12_16", None)]:
        if tag == "HUD_12_16":
            Xt = np.vstack([stay_tr[:, 12:], wake_tr[:, 12:]]).reshape(-1, 192)
            Xh = np.vstack([stay_he[:, 12:], wake_he[:, 12:]]).reshape(-1, 192)
        else:
            Xt, Xh = Xtr_sw, Xhe_sw
        mu, sd = Xt.mean(0), Xt.std(0) + 1e-6
        Xtn, Xhn = np.c_[(Xt - mu) / sd, np.ones(len(Xt))], np.c_[(Xh - mu) / sd, np.ones(len(Xh))]
        w = np.linalg.solve(Xtn.T @ Xtn + 100.0 * np.eye(Xtn.shape[1]), Xtn.T @ ytr_sw)
        p_tr = Xtn @ w
        p_he = Xhn @ w
        # AUROC via rank
        def auroc(y, s):
            pos = s[y == 1]
            neg = s[y == 0]
            return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())
        print(
            f"  [Sleep->Wake predictability from x_t ({tag})]: "
            f"n_tr=({len(stay_tr)} stay, {len(wake_tr)} wake) n_dev=({len(stay_he)}, {len(wake_he)}) | "
            f"AUROC tr={auroc(ytr_sw, p_tr):.3f} dev={auroc(yhe_sw, p_he):.3f} | "
            f"mean_pred stay={p_he[yhe_sw==0].mean():.3f} wake={p_he[yhe_sw==1].mean():.3f}"
        )

# ============================================================================
# 2B. OBSERVABILITY / BAYES PROBES ON 16x16 PIXELS (FACING DIR, DO, PLACE_TABLE)
# ============================================================================
print("\n=== PART 2B: SINGLE-FRAME 16x16 OBSERVABILITY & BAYES PROBES ===")

def compute_last_move(split, xi_arr, ai_arr, ti_arr):
    """For each k=1 window, return last move action in {1,2,3,4} strictly before t (0 if none)."""
    starts, ends, aoffs = scorer.episode_index(split)
    # Build per-step last_move across full action array
    lm_all = np.zeros(len(split["actions"]), dtype=np.int64)
    for s, e, ao in zip(starts, ends, aoffs):
        L = e - s - 1
        last_m = 4  # Crafter default facing is down (0, 1) -> move_down = 4
        for t in range(L):
            lm_all[ao + t] = last_m
            a = int(split["actions"][ao + t])
            if a in (1, 2, 3, 4):
                last_m = a
    return lm_all[ai_arr]

lm_tr = compute_last_move(tr, xi1_tr, ai1_tr, ti1_tr)
lm_he = compute_last_move(he, xi1_he, ai1_he, ti1_he)

# Probe 1: Can the 16x16 center sprite [5:7, 7:9] (or 4x4 [4:8, 6:10]) decode facing direction (1..4)?
for tag, ys, xs in [("sprite_2x2 [5:7,7:9]", slice(5, 7), slice(7, 9)),
                    ("crop_4x4   [4:8,6:10]", slice(4, 8), slice(6, 10))]:
    # Use non-sleep frames where player moved at least once (t > 5)
    m_tr = (ti1_tr > 5) & (x0_tr[:, :12].std((1, 2, 3)) > 0.08)
    m_he = (ti1_he > 5) & (x0_he[:, :12].std((1, 2, 3)) > 0.08)
    Xt = x0_tr[m_tr, ys, xs, :].reshape(int(m_tr.sum()), -1)
    Xh = x0_he[m_he, ys, xs, :].reshape(int(m_he.sum()), -1)
    yt = lm_tr[m_tr] - 1
    yh = lm_he[m_he] - 1
    # One-hot ridge linear classifier + 15-NN
    Yoh = np.eye(4)[yt]
    mu, sd = Xt.mean(0), Xt.std(0) + 1e-6
    Xtn, Xhn = np.c_[(Xt - mu) / sd, np.ones(len(Xt))], np.c_[(Xh - mu) / sd, np.ones(len(Xh))]
    W = np.linalg.solve(Xtn.T @ Xtn + 10.0 * np.eye(Xtn.shape[1]), Xtn.T @ Yoh)
    acc_tr = float(((Xtn @ W).argmax(1) == yt).mean())
    acc_he = float(((Xhn @ W).argmax(1) == yh).mean())
    # Quadratic features (captures nonlinear color interactions inside 2x2 sprite)
    if Xt.shape[1] <= 12:
        idx_i, idx_j = np.triu_indices(Xt.shape[1])
        Xt2 = np.c_[Xtn[:, :-1], Xtn[:, idx_i] * Xtn[:, idx_j], np.ones(len(Xt))]
        Xh2 = np.c_[Xhn[:, :-1], Xhn[:, idx_i] * Xhn[:, idx_j], np.ones(len(Xh))]
        W2 = np.linalg.solve(Xt2.T @ Xt2 + 10.0 * np.eye(Xt2.shape[1]), Xt2.T @ Yoh)
        acc2_he = float(((Xh2 @ W2).argmax(1) == yh).mean())
    else:
        acc2_he = float("nan")
    print(f"  [Facing-dir from {tag}]: linear acc tr={acc_tr*100:.1f}% dev={acc_he*100:.1f}% | quad dev={acc2_he*100:.1f}% (chance=25%)")

# Probe 2: For a=5 (do) and a=8 (place_table), excluding sleep-wake (rms < 0.08),
# how predictable are dY_full, dY_ctr6x6, dY_hud from x_t alone vs (x_t + true facing dir)?
print("\n  [Predictability of non-sleep-wake interactions (rms < 0.08) from x_t vs x_t+facing_dir]")
for q in [5, 8]:
    mt = (a1_tr == q) & (np.sqrt((dY_tr ** 2).mean((1, 2, 3))) < 0.08)
    mh = (a1_he == q) & (np.sqrt((dY_he ** 2).mean((1, 2, 3))) < 0.08)
    # Also check how often a REAL interaction happens (HUD change or center 6x6 change > 0.015)
    hud_rms_t = np.sqrt((dY_tr[mt, 12:, :, :] ** 2).mean((1, 2, 3)))
    ctr_rms_t = np.sqrt((dY_tr[mt, 3:9, 5:11, :] ** 2).mean((1, 2, 3)))
    hud_rms_h = np.sqrt((dY_he[mh, 12:, :, :] ** 2).mean((1, 2, 3)))
    ctr_rms_h = np.sqrt((dY_he[mh, 3:9, 5:11, :] ** 2).mean((1, 2, 3)))
    print(
        f"  a={q} ({ACTION_NAMES[q]}): n_tr={int(mt.sum())} n_dev={int(mh.sum())} | "
        f"HUD_rms>0.01: tr={(hud_rms_t>0.01).mean()*100:.1f}% dev={(hud_rms_h>0.01).mean()*100:.1f}% | "
        f"Ctr6x6_rms>0.015: tr={(ctr_rms_t>0.015).mean()*100:.1f}% dev={(ctr_rms_h>0.015).mean()*100:.1f}%"
    )
    # Build features: center 6x6 + HUD 4x16 (108 + 192 = 300 dims)
    Ft_x = np.c_[x0_tr[mt, 3:9, 5:11, :].reshape(int(mt.sum()), -1), x0_tr[mt, 12:, :, :].reshape(int(mt.sum()), -1)]
    Fh_x = np.c_[x0_he[mh, 3:9, 5:11, :].reshape(int(mh.sum()), -1), x0_he[mh, 12:, :, :].reshape(int(mh.sum()), -1)]
    # Facing-direction interaction features: one-hot facing (4) + facing * center6x6
    oh_t = np.eye(4)[lm_tr[mt] - 1]
    oh_h = np.eye(4)[lm_he[mh] - 1]
    # Also separate per-facing Ridge (so each facing dir gets its own linear map!)
    for region_name, r_fn in [
        ("full_16x16", lambda d: d.reshape(len(d), -1)),
        ("ctr_6x6   ", lambda d: d[:, 3:9, 5:11, :].reshape(len(d), -1)),
        ("hud_12_16 ", lambda d: d[:, 12:, :, :].reshape(len(d), -1)),
    ]:
        Yt = r_fn(dY_tr[mt])
        Yh = r_fn(dY_he[mh])
        # Pooled Ridge on x_t only (sweep lambda cleanly on small val? report best & fixed lam=100)
        mu, sd = Ft_x.mean(0), Ft_x.std(0) + 1e-6
        Xtn = np.c_[(Ft_x - mu) / sd, np.ones(len(Ft_x))]
        Xhn = np.c_[(Fh_x - mu) / sd, np.ones(len(Fh_x))]
        best_r2_x = -1e9
        best_sr_x = 0.0
        for lam in [10.0, 100.0, 500.0, 2000.0]:
            W = np.linalg.solve(Xtn.T @ Xtn + lam * np.eye(Xtn.shape[1]), Xtn.T @ Yt)
            Ph = Xhn @ W
            r2 = 1.0 - float(((Ph - Yh) ** 2).sum()) / max(float((Yh ** 2).sum()), 1e-12)
            if r2 > best_r2_x:
                best_r2_x = r2
                best_sr_x = float(Ph.std() / (Yh.std() + 1e-12))
        # Per-facing-direction Ridge (uses true facing dir!)
        Ph_face = np.zeros_like(Yh)
        for fd in range(1, 5):
            st_f = lm_tr[mt] == fd
            sh_f = lm_he[mh] == fd
            if st_f.sum() >= 10 and sh_f.any():
                W = np.linalg.solve(Xtn[st_f].T @ Xtn[st_f] + 200.0 * np.eye(Xtn.shape[1]), Xtn[st_f].T @ Yt[st_f])
                Ph_face[sh_f] = Xhn[sh_f] @ W
        r2_f = 1.0 - float(((Ph_face - Yh) ** 2).sum()) / max(float((Yh ** 2).sum()), 1e-12)
        sr_f = float(Ph_face.std() / (Yh.std() + 1e-12))
        # 25-NN on center6x6+HUD (nonlinear probe on x_t alone!)
        # Normalize center6x6 only for local similarity
        Ct = x0_tr[mt, 3:9, 5:11, :].reshape(int(mt.sum()), -1)
        Ch = x0_he[mh, 3:9, 5:11, :].reshape(int(mh.sum()), -1)
        dists = ((Ch[:, None, :] - Ct[None, :, :]) ** 2).sum(axis=2)
        knn_k = min(20, len(Ct))
        nn_idx = np.argpartition(dists, knn_k, axis=1)[:, :knn_k]
        Ph_knn = Yt[nn_idx].mean(axis=1)
        r2_knn = 1.0 - float(((Ph_knn - Yh) ** 2).sum()) / max(float((Yh ** 2).sum()), 1e-12)
        sr_knn = float(Ph_knn.std() / (Yh.std() + 1e-12))
        print(
            f"    {region_name}: Ridge(x_t) R2={best_r2_x:+.3f} (std_r={best_sr_x:.3f}) | "
            f"Ridge(x_t+face) R2={r2_f:+.3f} (std_r={sr_f:.3f}) | "
            f"20-NN(ctr6x6) R2={r2_knn:+.3f} (std_r={sr_knn:.3f})"
        )

# ============================================================================
# LOAD SAVED MODELS s42 AND s43 ON CPU
# ============================================================================
models = {}
for seed in (42, 43):
    m = SpatialWorldModelV6(size="R6conv")
    ck = torch.load(os.path.join(BASE, f"wm6/run_r6_s{seed}/model.pt"), map_location="cpu", weights_only=False)
    m.load_state_dict(ck["model"], strict=True)
    m.eval()
    models[seed] = m
print(f"\n[Loaded s42 & s43 on CPU at t={time.time()-t_global:.1f}s]")

# ============================================================================
# 2C. MODEL s42 & s43 ON TRAIN vs DEV PER ACTION (k=1)
# ============================================================================
print("\n=== PART 2C: MODEL s42 & s43 ON TRAIN SPLIT PER ACTION (OVERFIT vs UNDERFIT/BAYES) ===")
# Build a stratified train subset: ALL windows of actions with <= 400 samples, plus 800 of do and 400 each of moves 1..4
rng = np.random.default_rng(123)
tr_sub_idx = []
for q in range(17):
    idxs = np.flatnonzero(a1_tr == q)
    cap = 800 if q == 5 else (400 if q in (1, 2, 3, 4) else len(idxs))
    if len(idxs) > cap:
        idxs = rng.choice(idxs, size=cap, replace=False)
    tr_sub_idx.append(idxs)
tr_sub_idx = np.concatenate(tr_sub_idx)

def eval_k1_model(model, frames_x0, acts_1, batch=256):
    out_list = []
    for b in range(0, len(acts_1), batch):
        sl = slice(b, min(b + batch, len(acts_1)))
        x = torch.from_numpy(frames_x0[sl].astype(np.float32))
        a = torch.from_numpy(acts_1[sl, None].astype(np.int64))
        out = model.rollout(x, a, wm_grad=False)["pred_res"].double().numpy()
        out_list.append(out)
    return np.concatenate(out_list, axis=0)

P42_tr = eval_k1_model(models[42], x0_tr[tr_sub_idx], a1_tr[tr_sub_idx])
P43_tr = eval_k1_model(models[43], x0_tr[tr_sub_idx], a1_tr[tr_sub_idx])
dP42_tr = P42_tr - x0_tr[tr_sub_idx]
dP43_tr = P43_tr - x0_tr[tr_sub_idx]
dY_tr_sub = dY_tr[tr_sub_idx]
a_tr_sub = a1_tr[tr_sub_idx]

# Load dev predictions too for side-by-side comparison
fc42 = dict(np.load(os.path.join(BASE, "wm6/run_r6_s42/forecasts_dev.npz")))
fc43 = dict(np.load(os.path.join(BASE, "wm6/run_r6_s43/forecasts_dev.npz")))
dP42_dev = fc42["pred_k1"].astype(np.float64) - x0_he
dP43_dev = fc43["pred_k1"].astype(np.float64) - x0_he

print(f"{'a':>2} {'name':<16} | {'TRAIN s42':^26} | {'DEV s42':^26} | {'TRAIN s43':^13} {'DEV s43':^13}")
print(f"{'':>19} | {'n':>4} {'R2':>6} {'std_r':>6} {'slope':>6} | {'n':>4} {'R2':>6} {'std_r':>6} {'slope':>6} | {'R2':>6} {'std_r':>6} {'R2':>6} {'std_r':>6}")
for q in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    st = a_tr_sub == q
    sh = a1_he == q
    def _m(dp, dy):
        y, p = dy.reshape(-1), dp.reshape(-1)
        r2 = 1.0 - float(((p - y) ** 2).mean()) / max(float((y ** 2).mean()), 1e-12)
        sr = float(p.std() / (y.std() + 1e-12))
        sl = float(((p - p.mean()) * (y - y.mean())).mean() / max(float(((p - p.mean()) ** 2).mean()), 1e-12))
        return r2, sr, sl
    t42 = _m(dP42_tr[st], dY_tr_sub[st])
    d42 = _m(dP42_dev[sh], dY_he[sh])
    t43 = _m(dP43_tr[st], dY_tr_sub[st])
    d43 = _m(dP43_dev[sh], dY_he[sh])
    print(
        f"{q:2d} {ACTION_NAMES[q]:<16} | {int(st.sum()):4d} {t42[0]:+6.3f} {t42[1]:6.3f} {t42[2]:6.2f} | "
        f"{int(sh.sum()):4d} {d42[0]:+6.3f} {d42[1]:6.3f} {d42[2]:6.2f} | "
        f"{t43[0]:+6.3f} {t43[1]:6.3f} {d43[0]:+6.3f} {d43[1]:6.3f}"
    )

# Also break down TRAIN & DEV a=5 (do) and a=8 (place_table) into HUD vs Ctr6x6 vs OuterTerr!
print("\n--- Spatial breakdown of model predictions on a=5 (do) & a=8 (place_table), non-sleep-wake (rms<0.08) ---")
for q in [5, 8]:
    for sname, dp, dy, a_arr in [
        ("TR s42", dP42_tr, dY_tr_sub, a_tr_sub),
        ("DV s42", dP42_dev, dY_he, a1_he),
        ("TR s43", dP43_tr, dY_tr_sub, a_tr_sub),
        ("DV s43", dP43_dev, dY_he, a1_he),
    ]:
        m = (a_arr == q) & (np.sqrt((dy ** 2).mean((1, 2, 3))) < 0.08)
        parts = []
        for rname, rfn in [
            ("HUD", lambda x: x[:, 12:, :, :]),
            ("Ctr6x6", lambda x: x[:, 3:9, 5:11, :]),
            ("Outer", lambda x: x[:, :12, :, :]),
        ]:
            yy = rfn(dy[m]).reshape(-1)
            pp = rfn(dp[m]).reshape(-1)
            r2 = 1.0 - float(((pp - yy) ** 2).mean()) / max(float((yy ** 2).mean()), 1e-12)
            sr = float(pp.std() / (yy.std() + 1e-12))
            parts.append(f"{rname}:R2={r2:+.3f},sr={sr:.3f}")
        print(f"  a={q} {sname} (n={int(m.sum()):3d}): " + " | ".join(parts))

# ============================================================================
# 2D. ACTION EMBEDDING GEOMETRY, COUNTERFACTUAL SWAP & GRADIENT SHARE
# ============================================================================
print("\n=== PART 2D: ACTION EMBEDDINGS, COUNTERFACTUAL ACTION-SWAP & GRADIENT SHARE ===")
x_probe = torch.from_numpy(x0_he[:256].astype(np.float32))
for seed in (42, 43):
    m = models[seed]
    emb = m.action_emb.weight.detach()  # [17, 128]
    cond = m.dynamics.act_mlp(emb).detach()  # [17, 128]
    cond_n = cond / (cond.norm(dim=1, keepdim=True) + 1e-8)
    cos0 = (cond_n @ cond_n[0]).numpy()
    norms = cond.norm(dim=1).numpy()

    # Counterfactual: compare imagine(x_probe, a) vs imagine(x_probe, 0) AND vs x_probe!
    z0 = m.encode(x_probe)
    dec0 = m.decode(z0)
    a0_t = torch.zeros(len(x_probe), dtype=torch.long)
    p0 = x_probe + (m.decode(m.imagine_step(z0, a0_t, wm_grad=False)) - dec0)
    print(f"\n--- Seed {seed}: cond_norm, cos(cond[a], cond[noop]), RMS(f(x,a)-x), RMS(f(x,a)-f(x,noop)) ---")
    for q in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
        aq = torch.full((len(x_probe),), q, dtype=torch.long)
        pq = x_probe + (m.decode(m.imagine_step(z0, aq, wm_grad=False)) - dec0)
        rms_vs_x = float(((pq - x_probe) ** 2).mean().sqrt())
        rms_vs_0 = float(((pq - p0) ** 2).mean().sqrt())
        # Also check specifically on HUD and center 6x6
        rms_hud_vs_0 = float(((pq[:, 12:] - p0[:, 12:]) ** 2).mean().sqrt())
        rms_ctr_vs_0 = float(((pq[:, 3:9, 5:11] - p0[:, 3:9, 5:11]) ** 2).mean().sqrt())
        print(
            f"  a={q:2d} ({ACTION_NAMES[q]:<16}): ||cond||={norms[q]:5.2f} cos_noop={cos0[q]:+.3f} | "
            f"rms_vs_x={rms_vs_x:.5f} rms_vs_noop={rms_vs_0:.5f} (HUD={rms_hud_vs_0:.5f}, Ctr={rms_ctr_vs_0:.5f})"
        )

# Gradient norm share by action group on training data (zero optimizer step!)
print("\n--- Seed 42: Exact per-action loss & dynamics gradient norm share on TRAIN (pure CPU backward, zero opt.step) ---")
with torch.enable_grad():
    m42 = models[42]
    m42.zero_grad(set_to_none=True)
    # Sample 512 random train transitions (natural mix) and compute total loss + per-group partial grads
    j_nat = rng.choice(len(xi1_tr), size=512, replace=False)
    xt_n = torch.from_numpy(x0_tr[j_nat].astype(np.float32))
    xn_n = torch.from_numpy(x1_tr[j_nat].astype(np.float32))
    ac_n = torch.from_numpy(a1_tr[j_nat].astype(np.int64))
    z_t = m42.encode(xt_n).detach()
    x_rec_t = m42.decode(z_t).detach()
    z_pred = m42.imagine_step(z_t, ac_n, wm_grad=True)
    x_abs = m42.decode(z_pred)
    x_res = xt_n + (x_abs - x_rec_t)
    per_ex_loss = ((x_res - xn_n) ** 2).mean(dim=(1, 2, 3))  # [512]
    tot_l = float(per_ex_loss.sum())
    groups = [
        ("moves (1..4)", np.isin(a1_tr[j_nat], [1, 2, 3, 4])),
        ("sleep (6)",    a1_tr[j_nat] == 6),
        ("do (5)",       a1_tr[j_nat] == 5),
        ("place89 (8,9)", np.isin(a1_tr[j_nat], [8, 9])),
        ("other (0,7,10-16)", np.isin(a1_tr[j_nat], [0, 7, 10, 11, 12, 13, 14, 15, 16])),
    ]
    for gname, gmask in groups:
        m42.zero_grad(set_to_none=True)
        gm = torch.from_numpy(gmask)
        if not gm.any():
            continue
        # Contribution to mean batch loss (sum over group / N_total)
        lg = per_ex_loss[gm].sum() / float(len(j_nat))
        lg.backward(retain_graph=True)
        gn_dyn = float(np.sqrt(sum(float(p.grad.pow(2).sum()) for p in m42.dynamics.parameters() if p.grad is not None)))
        gn_act = float(m42.action_emb.weight.grad.norm()) if m42.action_emb.weight.grad is not None else 0.0
        print(
            f"  {gname:<18}: n={int(gmask.sum()):3d} ({100*gmask.mean():4.1f}%) | "
            f"loss_share={100*float(per_ex_loss[gm].sum())/tot_l:5.2f}% | "
            f"dyn_grad_norm={gn_dyn:.5f} | act_emb_grad_norm={gn_act:.5f}"
        )
    m42.zero_grad(set_to_none=True)

# ============================================================================
# 2E. EXACT k=1..5 OPEN-LOOP ROLLOUT TRAJECTORY & COUNTERFACTUALS (ALL 4,874 DEV k=5 WINDOWS)
# ============================================================================
print(f"\n=== PART 2E: EXACT k=1..5 OPEN-LOOP TRAJECTORY & SNAP COUNTERFACTUALS (t={time.time()-t_global:.1f}s) ===")
xi5, ai5, wi5, ei5, ti5 = scorer.windows(he, 5)
acts5 = scorer.action_values(he["actions"], ai5, 5)  # [4874, 5]
N5 = len(xi5)
hfr = he["frames"].astype(np.float64)

# Compute B_k for k=1..5 on the exact same N5=4874 windows (plus official B_5 for k=5!)
mean_tr = x0_tr.mean(0)
B_on_5 = {}
sos_preds_step = {}
x_sos_cur = hfr[xi5].copy()
for stp in range(1, 6):
    # Fit blend_a on train for horizon stp
    xk_tr = scorer.windows(tr, stp)[0]
    xs_tr = tr["frames"][xk_tr].astype(np.float64)
    ys_tr = tr["frames"][xk_tr + stp].astype(np.float64)
    dd_tr = xs_tr - mean_tr
    bl = float(((ys_tr - mean_tr) * dd_tr).sum() / float((dd_tr * dd_tr).sum()))
    x0 = hfr[xi5]
    yk = hfr[xi5 + stp]
    cp = float(((x0 - yk) ** 2).sum())
    bs = float(((mean_tr + bl * (x0 - mean_tr) - yk) ** 2).sum())
    B_on_5[stp] = min(cp, bs)
    # Advance shift_or_stay 1 step
    x_sos_cur = scorer.rollout_shift_or_stay(sos, x_sos_cur, acts5[:, stp - 1 : stp])
    sos_preds_step[stp] = x_sos_cur.copy()

# Compute exact per-window net pixel displacement from true open moves (to split in-view vs newly-revealed off-screen!)
# Each open move shifts the world by (dy, dx) in terrain coordinates:
#   move_left (1): dy=0, dx=-1.75 (pixels sample from x-1.75 -> left edge x < 1.75 is newly revealed!)
#   Wait: check scorer._bilinear_terrain_shift: f1(y, x) ~ f0(y+dy, x+dx)
#   So pixel (y, x) at t+k came from (y + sum_dy, x + sum_dx) in x0!
#   It is "in-view" if 0 <= y + sum_dy <= 11 and 0 <= x + sum_dx <= 15; otherwise "newly revealed off-screen"!
cum_dy = np.zeros(N5, dtype=np.float64)
cum_dx = np.zeros(N5, dtype=np.float64)
true_open_mat = np.zeros((N5, 5), dtype=bool)
true_valid_mat = np.zeros((N5, 5), dtype=bool)
for stp in range(5):
    vm, op, _ = scorer.classify_move_displacement(hfr[xi5 + stp], hfr[xi5 + stp + 1], acts5[:, stp])
    true_valid_mat[:, stp] = vm
    true_open_mat[:, stp] = op
    for q, (dy, dx) in scorer.MOVE_DIRS.items():
        m = vm & op & (acts5[:, stp] == q)
        cum_dy[m] += dy
        cum_dx[m] += dx

# Build [N5, 12, 16] boolean mask: True if pixel (y, x) at t+5 came from INSIDE terrain [0, 11] x [0, 15] of x0
yy_g = np.arange(12, dtype=np.float64)[None, :, None] + cum_dy[:, None, None]
xx_g = np.arange(16, dtype=np.float64)[None, None, :] + cum_dx[:, None, None]
# Also require pixel stayed inside during intermediate steps? Using cumulative net displacement is clean & exact for linear scroll:
# Even stricter: track min/max along path? Actually Crafter keeps out-of-view terrain unseen until scrolled in;
# wait: if you move right then left, the pixels that scrolled off-screen are STILL visible in x0!
# Only pixels whose origin (y + cum_dy, x + cum_dx) falls outside [0, 11] x [0, 15] were NEVER in x0!
in_view_mask_5 = (yy_g >= 0.0) & (yy_g <= 11.0) & (xx_g >= 0.0) & (xx_g <= 15.0)  # [N5, 12, 16]
offscreen_mask_5 = ~in_view_mask_5

def run_rollout_probe(model, mode="normal", batch=256):
    """Run open-loop k=1..5 on all N5 windows.
    mode:
      'normal': standard Rank 6 rollout (z <- imagine_step(z, a))
      'reencode': zero-training manifold snap `z <- encode(decode(z))` after every step 1..4!
      'reencode_res': snap via residual image `z <- encode(clip(x0 + (decode(z) - dec0), 0, 1))`!
    Returns per-step metrics & final k=5 predictions.
    """
    preds_step = {k: [] for k in range(1, 6)}
    z_norm_step = {k: [] for k in range(0, 6)}
    z_err_step = {k: [] for k in range(1, 6)}
    z_offman_step = {k: [] for k in range(1, 6)}  # ||z_k - encode(decode(z_k))||

    for b in range(0, N5, batch):
        sl = slice(b, min(b + batch, N5))
        idx = xi5[sl]
        x0 = torch.from_numpy(hfr[idx].astype(np.float32))
        ak = torch.from_numpy(acts5[sl].astype(np.int64))
        z0 = model.encode(x0)
        dec0 = model.decode(z0)
        z = z0
        z_norm_step[0].append(float(z0.pow(2).mean().sqrt()))
        for stp in range(1, 6):
            z = model.imagine_step(z, ak[:, stp - 1], wm_grad=False)
            dec_k = model.decode(z)
            pred_res = x0 + (dec_k - dec0)
            preds_step[stp].append(pred_res.double().numpy())

            # Measure latent stats vs real encode(x_{t+stp}) and off-manifold distance ||z - encode(decode(z))||
            z_norm_step[stp].append(float(z.pow(2).mean().sqrt()))
            if mode == "normal":
                x_true_k = torch.from_numpy(hfr[idx + stp].astype(np.float32))
                z_true_k = model.encode(x_true_k)
                z_reenc = model.encode(dec_k)
                z_err_step[stp].append(float(((z - z_true_k) ** 2).mean().sqrt()))
                z_offman_step[stp].append(float(((z - z_reenc) ** 2).mean().sqrt()))

            if stp < 5:
                if mode == "reencode":
                    z = model.encode(dec_k.clamp(0.0, 1.0))
                elif mode == "reencode_res":
                    z = model.encode(pred_res.clamp(0.0, 1.0))
                    # Note: after snapping to pred_res, keep dec0 = dec0 (or decode(z)?) — keep pred_abs = decode(z)
                    # Actually for reencode_res, z represents the full frame pred_res, so dec0 still cancels static AE error

    preds_step = {k: np.concatenate(preds_step[k], axis=0) for k in range(1, 6)}
    summary = {
        "z_norm": {k: float(np.mean(z_norm_step[k])) for k in range(0, 6)},
        "z_err": {k: float(np.mean(z_err_step[k])) for k in range(1, 6)} if mode == "normal" else {},
        "z_offman": {k: float(np.mean(z_offman_step[k])) for k in range(1, 6)} if mode == "normal" else {},
    }
    return preds_step, summary

for seed in (42, 43):
    print(f"\n================ SEED {seed} ================")
    m = models[seed]
    t0 = time.time()
    p_norm, sum_norm = run_rollout_probe(m, mode="normal")
    print(f"  [normal rollout done in {time.time()-t0:.1f}s]")

    # Step-by-step table: E/B, E/E_sos, block_open err at open-loop step stp, mean alpha on true open vs true blocked, latent metrics
    print(f"  {'k':>2} | {'E/B':>6} {'sos':>6} {'E/sos':>6} | {'bo_err':>6} {'fb':>6} {'fo':>6} {'al_op':>6} {'al_bl':>6} | {'||z||':>6} {'z_err':>6} {'offman':>6}")
    # Also compute true z norm at k=0
    z_real_norm = sum_norm["z_norm"][0]
    prev_P = hfr[xi5]
    for stp in range(1, 6):
        Pk = p_norm[stp]
        yk = hfr[xi5 + stp]
        e_m = float(((Pk - yk) ** 2).sum())
        e_s = float(((sos_preds_step[stp] - yk) ** 2).sum())
        # Step-by-step block_open on open-loop transition prev_P -> Pk!
        vm, p_op, p_al = scorer.classify_move_displacement(prev_P, Pk, acts5[:, stp - 1])
        # Use ground-truth valid_move & true_open from real frame transition!
        tv = true_valid_mat[:, stp - 1]
        to = true_open_mat[:, stp - 1]
        fb = float((~p_op[tv] & to[tv]).sum() / max(int(to[tv].sum()), 1))
        fo = float((p_op[tv] & ~to[tv]).sum() / max(int((~to[tv]).sum()), 1))
        bo = 0.5 * (fb + fo)
        al_op = float(p_al[tv & to].mean()) if (tv & to).any() else 0.0
        al_bl = float(p_al[tv & ~to].mean()) if (tv & ~to).any() else 0.0
        print(
            f"  {stp:2d} | {e_m/B_on_5[stp]:6.4f} {e_s/B_on_5[stp]:6.4f} {e_m/e_s:6.3f} | "
            f"{bo:6.4f} {fb:6.4f} {fo:6.4f} {al_op:6.3f} {al_bl:6.3f} | "
            f"{sum_norm['z_norm'][stp]:6.4f} {sum_norm['z_err'][stp]:6.4f} {sum_norm['z_offman'][stp]:6.4f}"
        )
        prev_P = Pk
    # Reference: ||z_real - encode(decode(z_real))|| on real frames
    x_ref = torch.from_numpy(hfr[xi5[:512]].astype(np.float32))
    zr = m.encode(x_ref)
    z_real_offman = float(((zr - m.encode(m.decode(zr))) ** 2).mean().sqrt())
    print(f"  [Ref real frames: ||z_real||={z_real_norm:.4f}, ||z_real - enc(dec(z_real))||={z_real_offman:.4f}]")

    # CRITICAL k=5 PIXEL ORIGIN DECOMPOSITION: In-view terrain vs Off-screen newly revealed vs HUD!
    P5 = p_norm[5]
    S5 = sos_preds_step[5]
    Y5 = hfr[xi5 + 5]
    e_m_px = ((P5 - Y5) ** 2).sum(axis=3)  # [N5, 16, 16]
    e_s_px = ((S5 - Y5) ** 2).sum(axis=3)
    in_m = float(e_m_px[:, :12, :][in_view_mask_5].sum())
    in_s = float(e_s_px[:, :12, :][in_view_mask_5].sum())
    off_m = float(e_m_px[:, :12, :][offscreen_mask_5].sum())
    off_s = float(e_s_px[:, :12, :][offscreen_mask_5].sum())
    hud_m = float(e_m_px[:, 12:, :].sum())
    hud_s = float(e_s_px[:, 12:, :].sum())
    frac_off = float(offscreen_mask_5.mean())
    # Also compute pixel variance on off-screen newly revealed pixels!
    var_y_off = float(Y5[:, :12, :, :][offscreen_mask_5].var())
    var_m_off = float(P5[:, :12, :, :][offscreen_mask_5].var())
    var_s_off = float(S5[:, :12, :, :][offscreen_mask_5].var())
    var_y_in = float(Y5[:, :12, :, :][in_view_mask_5].var())
    var_m_in = float(P5[:, :12, :, :][in_view_mask_5].var())
    var_s_in = float(S5[:, :12, :, :][in_view_mask_5].var())
    print(f"\n  [k=5 EXACT PIXEL-ORIGIN DECOMPOSITION (off-screen share = {frac_off*100:.1f}% of terrain px)]")
    print(f"    In-view terrain     : model={in_m:8.1f}  sos={in_s:8.1f}  gap={in_m-in_s:+8.1f} (ratio={in_m/in_s:.3f}) | var true={var_y_in:.4f} mod={var_m_in:.4f} sos={var_s_in:.4f}")
    print(f"    Off-screen revealed : model={off_m:8.1f}  sos={off_s:8.1f}  gap={off_m-off_s:+8.1f} (ratio={off_m/off_s:.3f}) | var true={var_y_off:.4f} mod={var_m_off:.4f} sos={var_s_off:.4f}")
    print(f"    HUD (rows 12..15)   : model={hud_m:8.1f}  sos={hud_s:8.1f}  gap={hud_m-hud_s:+8.1f} (ratio={hud_m/hud_s:.3f})")
    print(f"    TOTAL CHECK         : model={in_m+off_m+hud_m:8.1f}  sos={in_s+off_s+hud_s:8.1f}  gap={(in_m+off_m+hud_m)-(in_s+off_s+hud_s):+8.1f}")

    # Sub-break in-view vs off-screen on pure_moves with open_moves >= 3!
    m_35 = true_open_mat.sum(axis=1) >= 3
    in_m35 = float(e_m_px[m_35, :12, :][in_view_mask_5[m_35]].sum())
    in_s35 = float(e_s_px[m_35, :12, :][in_view_mask_5[m_35]].sum())
    off_m35 = float(e_m_px[m_35, :12, :][offscreen_mask_5[m_35]].sum())
    off_s35 = float(e_s_px[m_35, :12, :][offscreen_mask_5[m_35]].sum())
    hud_m35 = float(e_m_px[m_35, 12:, :].sum())
    hud_s35 = float(e_s_px[m_35, 12:, :].sum())
    print(f"  [Same split on open_moves >= 3 ONLY (n={int(m_35.sum())}, offscreen={offscreen_mask_5[m_35].mean()*100:.1f}%)]")
    print(f"    In-view terrain     : model={in_m35:8.1f}  sos={in_s35:8.1f}  gap={in_m35-in_s35:+8.1f} (ratio={in_m35/in_s35:.3f})")
    print(f"    Off-screen revealed : model={off_m35:8.1f}  sos={off_s35:8.1f}  gap={off_m35-off_s35:+8.1f} (ratio={off_m35/off_s35:.3f})")
    print(f"    HUD (rows 12..15)   : model={hud_m35:8.1f}  sos={hud_s35:8.1f}  gap={hud_m35-hud_s35:+8.1f} (ratio={hud_m35/hud_s35:.3f})")

    # Check if in-view error on open_moves>=3 is SHIFT MISALIGNMENT (subpixel lag) or BLUR or WRONG BLOCK!
    # Compare best 2D subpixel shift of x0 vs P5 on in-view terrain for pure 5-open-move windows!
    # Also check step-by-step sos block_open vs model block_open on open_moves>=3!
    m_sos_bo_errs = []
    prev_S = hfr[xi5]
    for stp in range(1, 6):
        _, s_op, _ = scorer.classify_move_displacement(prev_S, sos_preds_step[stp], acts5[:, stp - 1])
        tv = true_valid_mat[:, stp - 1]
        to = true_open_mat[:, stp - 1]
        s_fb = float((~s_op[tv] & to[tv]).sum() / max(int(to[tv].sum()), 1))
        s_fo = float((s_op[tv] & ~to[tv]).sum() / max(int((~to[tv]).sum()), 1))
        m_sos_bo_errs.append(f"k{stp}:{0.5*(s_fb+s_fo):.3f}(fb={s_fb:.3f},fo={s_fo:.3f})")
        prev_S = sos_preds_step[stp]
    if seed == 42:
        print(f"  [Ref sos step-by-step block_open]: " + " | ".join(m_sos_bo_errs))

    # ZERO-TRAINING MANIFOLD-SNAP COUNTERFACTUALS!
    for snap_mode in ("reencode", "reencode_res"):
        t1 = time.time()
        p_snap, _ = run_rollout_probe(m, mode=snap_mode)
        eb1 = float(((p_snap[1] - hfr[xi5 + 1]) ** 2).sum()) / B_on_5[1]
        eb3 = float(((p_snap[3] - hfr[xi5 + 3]) ** 2).sum()) / B_on_5[3]
        eb5 = float(((p_snap[5] - hfr[xi5 + 5]) ** 2).sum()) / B_on_5[5]
        e5_px = ((p_snap[5] - Y5) ** 2).sum(axis=3)
        print(
            f"  [Counterfactual '{snap_mode}' ({time.time()-t1:.1f}s)]: "
            f"E/B k1={eb1:.4f} k3={eb3:.4f} k5={eb5:.4f} (vs normal {float(((P5-Y5)**2).sum())/B_on_5[5]:.4f}, bar 0.4977) | "
            f"k5 in={e5_px[:,:12,:][in_view_mask_5].sum():.1f} off={e5_px[:,:12,:][offscreen_mask_5].sum():.1f} hud={e5_px[:,12:,:].sum():.1f}"
        )

print(f"\n[PART 2 DONE in {time.time()-t_global:.1f}s]")
