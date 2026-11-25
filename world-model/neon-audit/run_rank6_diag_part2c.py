"""Read-only CPU diagnostic Part 2c: Can 16x16 HUD pixels cleanly separate energy==9 wake-ups from stay-asleep?"""
import os
import sys
import numpy as np

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer

tr = scorer.load_split(os.path.join(BASE, "wm5/data/train_dn.npz"))
he = scorer.load_split(os.path.join(BASE, "wm-harness/data/heldout.npz"))

xi1_tr, ai1_tr, _, _, _ = scorer.windows(tr, 1)
a1_tr = tr["actions"][ai1_tr]
x0_tr = tr["frames"][xi1_tr].astype(np.float64)
x1_tr = tr["frames"][xi1_tr + 1].astype(np.float64)
dY_tr = x1_tr - x0_tr

xi1_he, ai1_he, _, _, _ = scorer.windows(he, 1)
a1_he = he["actions"][ai1_he]
x0_he = he["frames"][xi1_he].astype(np.float64)
x1_he = he["frames"][xi1_he + 1].astype(np.float64)
dY_he = x1_he - x0_he

fc42 = np.load(os.path.join(BASE, "wm6/run_r6_s42/forecasts_dev.npz"))["pred_k1"].astype(np.float64) - x0_he
fc43 = np.load(os.path.join(BASE, "wm6/run_r6_s43/forecasts_dev.npz"))["pred_k1"].astype(np.float64) - x0_he

def get_sleep_masks(x0, x1):
    s0 = x0[:, :12].std((1, 2, 3))
    s1 = x1[:, :12].std((1, 2, 3))
    rms = np.sqrt(((x1 - x0) ** 2).mean((1, 2, 3)))
    is_asleep = s0 < 0.08
    is_wake = is_asleep & (s1 > 0.10) & (rms > 0.08)
    return is_asleep, is_wake

asl_tr, wk_tr = get_sleep_masks(x0_tr, x1_tr)
asl_he, wk_he = get_sleep_masks(x0_he, x1_he)

# 1. Which HUD pixel(s) differ most between wake and stay-asleep?
H_tr = x0_tr[asl_tr, 12:, :, :]  # [N, 4, 16, 3]
y_tr = wk_tr[asl_tr].astype(np.float64)
H_he = x0_he[asl_he, 12:, :, :]
y_he = wk_he[asl_he].astype(np.float64)

diff_map = np.abs(H_tr[y_tr == 1].mean(0) - H_tr[y_tr == 0].mean(0)).mean(axis=2)  # [4, 16]
print("=== HUD |mean(wake) - mean(stay)| map (rows 12..15, cols 0..15) ===")
for r in range(4):
    print(f"  row {12+r}: " + " ".join(f"{diff_map[r, c]:.3f}" for c in range(16)))

# Find top-8 most discriminative HUD pixels
flat_idx = np.argsort(diff_map.reshape(-1))[::-1][:8]
top_coords = [(12 + int(i // 16), int(i % 16), float(diff_map.reshape(-1)[i])) for i in flat_idx]
print("Top-8 HUD pixels separating wake vs stay:", top_coords)

# 2. Check nonlinear kNN wake-probability predictor on:
#    (a) full HUD [12:16, :]
#    (b) top-4 HUD pixels (energy icon + digit!)
#    (c) energy icon region rows 12:14, cols 4:9 (find exact cols from top_coords)
top_r = [c[0] - 12 for c in top_coords[:6]]
top_c = [c[1] for c in top_coords[:6]]
r0, r1 = min(top_r), max(top_r) + 1
c0, c1 = min(top_c), max(top_c) + 1
print(f"Auto energy HUD box: rows {12+r0}..{12+r1-1}, cols {c0}..{c1-1}")

def auroc(y, s):
    pos = s[y == 1]
    neg = s[y == 0]
    return float((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean())

# Build affine wake recovery map (fit on train wake frames)
u_tr = x0_tr[wk_tr, :12]
v_tr = x1_tr[wk_tr, :12]
um_tr = u_tr.mean((1, 2), keepdims=True) * np.ones_like(u_tr)
w_ch = []
for ch in range(3):
    Xch = np.c_[u_tr[..., ch].reshape(-1), um_tr[..., ch].reshape(-1), np.ones(u_tr[..., ch].size)]
    w_ch.append(np.linalg.lstsq(Xch, v_tr[..., ch].reshape(-1), rcond=None)[0])

awake_est_he = np.zeros_like(x0_he[asl_he, :12])
for ch in range(3):
    u = x0_he[asl_he, :12, :, ch]
    um = u.mean((1, 2), keepdims=True) * np.ones_like(u)
    Xh = np.c_[u.reshape(-1), um.reshape(-1), np.ones(u.size)]
    awake_est_he[..., ch] = (Xh @ w_ch[ch]).reshape(u.shape)
wake_delta_he = np.zeros_like(dY_he[asl_he])
wake_delta_he[:, :12] = awake_est_he - x0_he[asl_he, :12]

for feat_name, Ft, Fh in [
    ("full_HUD_192", H_tr.reshape(len(H_tr), -1), H_he.reshape(len(H_he), -1)),
    (f"energy_box_{r1-r0}x{c1-c0}", H_tr[:, r0:r1, c0:c1, :].reshape(len(H_tr), -1), H_he[:, r0:r1, c0:c1, :].reshape(len(H_he), -1)),
    ("top4_HUD_px", H_tr[:, [c[0]-12 for c in top_coords[:4]], [c[1] for c in top_coords[:4]], :].reshape(len(H_tr), -1),
                    H_he[:, [c[0]-12 for c in top_coords[:4]], [c[1] for c in top_coords[:4]], :].reshape(len(H_he), -1)),
]:
    dists = ((Fh[:, None, :] - Ft[None, :, :]) ** 2).sum(axis=2)
    for kk in (5, 15, 30):
        nn = np.argpartition(dists, kk, axis=1)[:, :kk]
        p_wk = y_tr[nn].mean(axis=1)
        au = auroc(y_he, p_wk)
        # Apply p_wk * wake_delta_he on ALL asleep dev frames -> check R2 & std_r on asleep, and on a=5, 8, 9!
        d_full = np.zeros_like(dY_he)
        d_full[asl_he] = p_wk[:, None, None, None] * wake_delta_he
        r2_asl = 1.0 - float(((d_full[asl_he] - dY_he[asl_he]) ** 2).sum()) / float((dY_he[asl_he] ** 2).sum())
        sr_asl = float(d_full[asl_he].std() / dY_he[asl_he].std())
        sr_by_a = {}
        r2_by_a = {}
        for q in (5, 8, 9):
            sel = a1_he == q
            sr_by_a[q] = float(d_full[sel].std() / dY_he[sel].std())
            r2_by_a[q] = 1.0 - float(((d_full[sel] - dY_he[sel]) ** 2).sum()) / float((dY_he[sel] ** 2).sum())
        print(
            f"  {feat_name:<15} {kk:2d}-NN: AUROC={au:.3f} mean_p(stay={p_wk[y_he==0].mean():.3f}, wake={p_wk[y_he==1].mean():.3f}) | "
            f"asleep R2={r2_asl:+.3f} sr={sr_asl:.3f} | "
            f"a5(sr={sr_by_a[5]:.3f},R2={r2_by_a[5]:+.3f}) a8(sr={sr_by_a[8]:.3f},R2={r2_by_a[8]:+.3f}) a9(sr={sr_by_a[9]:.3f},R2={r2_by_a[9]:+.3f})"
        )

# 3. Check what saved s42 & s43 predicted on ALL 25 DEV WAKE frames vs 679 STAY-ASLEEP frames, split by move vs non-move!
print("\n=== SAVED s42 & s43 ON DEV ASLEEP FRAMES: WAKE (n=25) vs STAY (n=679), SPLIT BY MOVE vs NON-MOVE ===")
for sname, dp in [("s42", fc42), ("s43", fc43)]:
    rms_p = np.sqrt((dp ** 2).mean((1, 2, 3)))
    for grp, gmask in [("moves(1..4)", np.isin(a1_he, [1, 2, 3, 4])),
                       ("do(5)", a1_he == 5),
                       ("place89(8,9)", np.isin(a1_he, [8, 9])),
                       ("other_nm", np.isin(a1_he, [0, 7, 10, 11, 12, 13, 14, 15, 16]))]:
        m_w = wk_he & gmask
        m_s = (asl_he & (~wk_he)) & gmask
        mw_val = float(rms_p[m_w].mean()) if m_w.any() else float("nan")
        ms_val = float(rms_p[m_s].mean()) if m_s.any() else float("nan")
        # Also mean signed terrain brightness change predicted
        db_w = float(dp[m_w, :12].mean()) if m_w.any() else float("nan")
        db_s = float(dp[m_s, :12].mean()) if m_s.any() else float("nan")
        print(
            f"  {sname} {grp:<12}: wake(n={int(m_w.sum()):2d}) rms={mw_val:.4f} dBright={db_w:+.4f} | "
            f"stay(n={int(m_s.sum()):3d}) rms={ms_val:.4f} dBright={db_s:+.4f}"
        )

# 4. Also check: on the 25 DEV wake frames, what is the TRUE wake-up mechanism (full-rested vs hurt)?
# Inspect HUD pixels at energy box for each of the 25 dev wake frames vs 15-NN prob!
Ft_e = H_tr[:, r0:r1, c0:c1, :].reshape(len(H_tr), -1)
Fh_e = H_he[:, r0:r1, c0:c1, :].reshape(len(H_he), -1)
dists_e = ((Fh_e[:, None, :] - Ft_e[None, :, :]) ** 2).sum(axis=2)
nn15 = np.argpartition(dists_e, 15, axis=1)[:, :15]
p_wk_e = y_tr[nn15].mean(axis=1)
asl_idx = np.flatnonzero(asl_he)
print("\n=== ALL 25 DEV WAKE FRAMES: ACTION, 15-NN ENERGY-BOX WAKE PROB, AND SAVED s42/s43 RMS ===")
for i_local, idx in enumerate(asl_idx):
    if wk_he[idx]:
        a = int(a1_he[idx])
        rms_t = float(np.sqrt((dY_he[idx] ** 2).mean()))
        rms_42 = float(np.sqrt((fc42[idx] ** 2).mean()))
        rms_43 = float(np.sqrt((fc43[idx] ** 2).mean()))
        print(
            f"  a={a:2d} ({'move' if a in (1,2,3,4) else ('do' if a==5 else f'a{a}'):<4}) "
            f"p_wk(energy15NN)={p_wk_e[i_local]:.2f} | true_rms={rms_t:.4f} s42_rms={rms_42:.4f} s43_rms={rms_43:.4f}"
        )
