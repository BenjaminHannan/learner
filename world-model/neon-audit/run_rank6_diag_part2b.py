"""Read-only CPU diagnostic Part 2b: Sleep-screen recoverability & exact std_ratio ceilings for actions 5, 8, 9."""
import os
import sys
import numpy as np

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer

tr = scorer.load_split(os.path.join(BASE, "wm5/data/train_dn.npz"))
he = scorer.load_split(os.path.join(BASE, "wm-harness/data/heldout.npz"))

xi1_tr, ai1_tr, _, ei1_tr, ti1_tr = scorer.windows(tr, 1)
a1_tr = tr["actions"][ai1_tr]
x0_tr = tr["frames"][xi1_tr].astype(np.float64)
x1_tr = tr["frames"][xi1_tr + 1].astype(np.float64)
dY_tr = x1_tr - x0_tr

xi1_he, ai1_he, _, ei1_he, ti1_he = scorer.windows(he, 1)
a1_he = he["actions"][ai1_he]
x0_he = he["frames"][xi1_he].astype(np.float64)
x1_he = he["frames"][xi1_he + 1].astype(np.float64)
dY_he = x1_he - x0_he

# 1. Inspect sleep-screen physics: when sleeping (terrStd < 0.08), how does x_t relate to awake x_{t+1}?
# Specifically on wake-up transitions: terrStd(x0) < 0.08 and terrStd(x1) > 0.10 and rms > 0.08
def get_sleep_masks(x0, x1):
    s0 = x0[:, :12].std((1, 2, 3))
    s1 = x1[:, :12].std((1, 2, 3))
    rms = np.sqrt(((x1 - x0) ** 2).mean((1, 2, 3)))
    is_asleep = s0 < 0.08
    is_wake = is_asleep & (s1 > 0.10) & (rms > 0.08)
    is_stay_asleep = is_asleep & (~is_wake)
    return is_asleep, is_wake, is_stay_asleep

asl_tr, wk_tr, sta_tr = get_sleep_masks(x0_tr, x1_tr)
asl_he, wk_he, sta_he = get_sleep_masks(x0_he, x1_he)
print("=== PART 2B-1: SLEEP-SCREEN PIXEL PHYSICS & WAKE-UP RECOVERABILITY ===")
print(f"TRAIN: asleep={int(asl_tr.sum())}, wake={int(wk_tr.sum())} ({100*wk_tr.sum()/max(asl_tr.sum(),1):.1f}%), stay={int(sta_tr.sum())}")
print(f"DEV  : asleep={int(asl_he.sum())}, wake={int(wk_he.sum())} ({100*wk_he.sum()/max(asl_he.sum(),1):.1f}%), stay={int(sta_he.sum())}")

# On actual wake-up frames, measure pixel-wise correlation between sleeping x0[:12] and awake x1[:12]!
corrs = []
ratios = []
for i in np.flatnonzero(wk_he):
    u = x0_he[i, :12].reshape(-1)
    v = x1_he[i, :12].reshape(-1)
    uc, vc = u - u.mean(), v - v.mean()
    corrs.append(float((uc * vc).sum() / max(np.sqrt((uc**2).sum() * (vc**2).sum()), 1e-12)))
    ratios.append(float(u.std() / max(v.std(), 1e-12)))
print(f"DEV wake frames (n={len(corrs)}): spatial corr(x_asleep, x_awake) median={np.median(corrs):.3f} min={np.min(corrs):.3f} max={np.max(corrs):.3f}")
print(f"DEV wake frames: std(x_asleep)/std(x_awake) median={np.median(ratios):.3f} (sleep contrast attenuation)")

# Fit a simple action-INDEPENDENT sleep-wake predictor on ALL sleeping frames (asleep_tr -> dY_tr)
# Compare:
#   (1) pixelwise affine scaling of x0[:, :12] conditioned on HUD (linear ridge on all 768 dims -> 768 dims, fitted ONLY on asleep_tr!)
#   (2) oracle wake-up probability * linear reconstruction from x_asleep
Xt_a = x0_tr[asl_tr].reshape(-1, 768)
Yt_a = dY_tr[asl_tr].reshape(-1, 768)
Xh_a = x0_he[asl_he].reshape(-1, 768)
Yh_a = dY_he[asl_he].reshape(-1, 768)
mu, sd = Xt_a.mean(0), Xt_a.std(0) + 1e-6
Xtn = np.c_[(Xt_a - mu) / sd, np.ones(len(Xt_a))]
Xhn = np.c_[(Xh_a - mu) / sd, np.ones(len(Xh_a))]

# Also test on WAKE-ONLY frames: given you ARE waking up, how well can you reconstruct x1 from x0_asleep?
# Per-pixel linear recovery: x1(y,x,c) = a * (x0(y,x,c) - mean(x0)) + b + c*mean(x0)
u_tr = x0_tr[wk_tr, :12]
v_tr = x1_tr[wk_tr, :12]
u_he = x0_he[wk_he, :12]
v_he = x1_he[wk_he, :12]
# Fit per-channel affine map [u, mean(u), 1] -> v
um_tr = u_tr.mean((1, 2), keepdims=True) * np.ones_like(u_tr)
um_he = u_he.mean((1, 2), keepdims=True) * np.ones_like(u_he)
A_tr = np.stack([u_tr.reshape(-1, 3), um_tr.reshape(-1, 3), np.ones((u_tr.size // 3, 3))], axis=-1)  # [M, 3, 3]
v_pred_he = np.zeros_like(v_he)
for ch in range(3):
    Xch = np.c_[u_tr[..., ch].reshape(-1), um_tr[..., ch].reshape(-1), np.ones(u_tr[..., ch].size)]
    ych = v_tr[..., ch].reshape(-1)
    wch = np.linalg.lstsq(Xch, ych, rcond=None)[0]
    Xh_ch = np.c_[u_he[..., ch].reshape(-1), um_he[..., ch].reshape(-1), np.ones(u_he[..., ch].size)]
    v_pred_he[..., ch] = (Xh_ch @ wch).reshape(v_he[..., ch].shape)
    print(f"  ch={ch} wake recovery weights [x0, mean(x0), 1]: {[round(float(x), 3) for x in wch]}")
r2_wake_rec = 1.0 - float(((v_pred_he - v_he) ** 2).sum()) / float(((u_he - v_he) ** 2).sum())
print(f"  [IF wake known]: 3-param per-channel affine from sleeping x0 recovers awake terrain with R2={r2_wake_rec:+.3f} vs copy!")

# Now combine HUD wake-prob p_wake(HUD) * affine_wake_delta on ALL sleeping frames (action-independent!)
# Fit logistic / ridge wake-prob from HUD_12_16 on asleep_tr
Ht_a = x0_tr[asl_tr, 12:].reshape(-1, 192)
Hh_a = x0_he[asl_he, 12:].reshape(-1, 192)
mu_h, sd_h = Ht_a.mean(0), Ht_a.std(0) + 1e-6
Htn = np.c_[(Ht_a - mu_h) / sd_h, np.ones(len(Ht_a))]
Hhn = np.c_[(Hh_a - mu_h) / sd_h, np.ones(len(Hh_a))]
yw_tr = wk_tr[asl_tr].astype(np.float64)
yw_he = wk_he[asl_he].astype(np.float64)
# Fit ridge wake probability
w_prob = np.linalg.solve(Htn.T @ Htn + 50.0 * np.eye(Htn.shape[1]), Htn.T @ yw_tr)
p_wk_he = np.clip(Hhn @ w_prob, 0.0, 1.0)
# Predict delta on ALL asleep_he frames as p_wk * (affine_awake - x0)
d_pred_asleep = np.zeros_like(dY_he[asl_he])
for ch in range(3):
    Xch = np.c_[u_tr[..., ch].reshape(-1), um_tr[..., ch].reshape(-1), np.ones(u_tr[..., ch].size)]
    wch = np.linalg.lstsq(Xch, v_tr[..., ch].reshape(-1), rcond=None)[0]
    u_all = x0_he[asl_he, :12, :, ch]
    um_all = u_all.mean((1, 2), keepdims=True) * np.ones_like(u_all)
    Xh_all = np.c_[u_all.reshape(-1), um_all.reshape(-1), np.ones(u_all.size)]
    awake_est = (Xh_all @ wch).reshape(u_all.shape)
    d_pred_asleep[:, :12, :, ch] = p_wk_he[:, None, None] * (awake_est - u_all)

r2_asleep_all = 1.0 - float(((d_pred_asleep - dY_he[asl_he]) ** 2).sum()) / float((dY_he[asl_he] ** 2).sum())
sr_asleep_all = float(d_pred_asleep.std() / dY_he[asl_he].std())
print(f"  [Action-independent HUD_prob * affine_wake on ALL DEV asleep frames (n={int(asl_he.sum())})]: R2={r2_asleep_all:+.3f}, std_ratio={sr_asleep_all:.3f}")

# Check how well saved Rank 6 s42 & s43 predicted on ALL asleep_he frames!
fc42 = np.load(os.path.join(BASE, "wm6/run_r6_s42/forecasts_dev.npz"))["pred_k1"].astype(np.float64) - x0_he
fc43 = np.load(os.path.join(BASE, "wm6/run_r6_s43/forecasts_dev.npz"))["pred_k1"].astype(np.float64) - x0_he
for sname, dp in [("s42", fc42), ("s43", fc43)]:
    r2_a = 1.0 - float(((dp[asl_he] - dY_he[asl_he]) ** 2).sum()) / float((dY_he[asl_he] ** 2).sum())
    sr_a = float(dp[asl_he].std() / dY_he[asl_he].std())
    # Also check specifically on asleep_he & non-move actions!
    m_anm = asl_he & (~np.isin(a1_he, [1, 2, 3, 4, 6]))
    r2_anm = 1.0 - float(((dp[m_anm] - dY_he[m_anm]) ** 2).sum()) / float((dY_he[m_anm] ** 2).sum())
    sr_anm = float(dp[m_anm].std() / dY_he[m_anm].std())
    print(f"  [Saved {sname} on ALL DEV asleep (n={int(asl_he.sum())})]: R2={r2_a:+.3f}, std_r={sr_a:.3f} | non-move asleep (n={int(m_anm.sum())}): R2={r2_anm:+.3f}, std_r={sr_anm:.3f}")

# 2. EXACT ORACLE & RIDGE STD_RATIO CEILINGS FOR ACTIONS 5, 8, 9 ON ALL DEV WINDOWS!
print("\n=== PART 2B-2: EXACT STD_RATIO CEILINGS ON ALL DEV WINDOWS FOR ACTIONS 5, 8, 9 ===")
# Build combined action-independent sleep-wake pred array across all DEV windows
d_sleep_pred_he = np.zeros_like(dY_he)
d_sleep_pred_he[asl_he] = d_pred_asleep

for q in [0, 5, 7, 8, 9, 10]:
    sel = a1_he == q
    dy = dY_he[sel]
    std_real = float(dy.std())
    # Oracle 1: PERFECT Ctr6x6 + HUD on non-wake frames, 0 on OuterTerr & 0 on wake frames
    p_or_local = np.zeros_like(dy)
    non_wk = ~wk_he[sel]
    p_or_local[non_wk, 12:, :, :] = dy[non_wk, 12:, :, :]
    p_or_local[non_wk, 3:9, 5:11, :] = dy[non_wk, 3:9, 5:11, :]
    # Oracle 2: PERFECT Sleep-Wake only (0 on non-wake frames)
    p_or_wake = np.zeros_like(dy)
    p_or_wake[wk_he[sel]] = dy[wk_he[sel]]
    # Oracle 3: PERFECT Ctr6x6 + HUD + Action-independent Ridge Sleep-Wake predictor!
    p_or_loc_plus_r_wk = p_or_local.copy()
    p_or_loc_plus_r_wk[asl_he[sel]] = d_sleep_pred_he[sel][asl_he[sel]]
    # Pure action-independent Ridge Sleep-Wake predictor ONLY (zero local interaction!)
    p_r_wk_only = d_sleep_pred_he[sel]
    # Realizable Ridge(x_t) for Ctr6x6+HUD (non-asleep) + Action-independent Ridge Sleep-Wake (asleep)!
    mt = (a1_tr == q) & (~asl_tr)
    mh = sel & (~asl_he)
    p_realizable = d_sleep_pred_he[sel].copy()
    if mt.sum() >= 20 and mh.any():
        Ft = np.c_[x0_tr[mt, 3:9, 5:11, :].reshape(int(mt.sum()), -1), x0_tr[mt, 12:, :, :].reshape(int(mt.sum()), -1)]
        Fh = np.c_[x0_he[mh, 3:9, 5:11, :].reshape(int(mh.sum()), -1), x0_he[mh, 12:, :, :].reshape(int(mh.sum()), -1)]
        muf, sdf = Ft.mean(0), Ft.std(0) + 1e-6
        Xtf = np.c_[(Ft - muf) / sdf, np.ones(len(Ft))]
        Xhf = np.c_[(Fh - muf) / sdf, np.ones(len(Fh))]
        # Predict Ctr6x6 + HUD only (lam=200)
        Yt_c = dY_tr[mt, 3:9, 5:11, :].reshape(int(mt.sum()), -1)
        Yt_h = dY_tr[mt, 12:, :, :].reshape(int(mt.sum()), -1)
        Wc = np.linalg.solve(Xtf.T @ Xtf + 200.0 * np.eye(Xtf.shape[1]), Xtf.T @ Yt_c)
        Wh = np.linalg.solve(Xtf.T @ Xtf + 200.0 * np.eye(Xtf.shape[1]), Xtf.T @ Yt_h)
        loc_idx = ~asl_he[sel]
        p_realizable[loc_idx, 3:9, 5:11, :] = (Xhf @ Wc).reshape(-1, 6, 6, 3)
        p_realizable[loc_idx, 12:, :, :] = (Xhf @ Wh).reshape(-1, 4, 16, 3)

    def _sr_r2(p):
        sr = float(p.std() / (std_real + 1e-12))
        r2 = 1.0 - float(((p - dy) ** 2).sum()) / max(float((dy ** 2).sum()), 1e-12)
        return sr, r2

    s1, r1 = _sr_r2(p_or_local)
    s2, r2 = _sr_r2(p_or_wake)
    s3, r3 = _sr_r2(p_or_loc_plus_r_wk)
    s4, r4 = _sr_r2(p_r_wk_only)
    s5, r5 = _sr_r2(p_realizable)
    s42_sr, s42_r2 = _sr_r2(fc42[sel])
    s43_sr, s43_r2 = _sr_r2(fc43[sel])
    print(
        f"a={q:2d} n={int(sel.sum()):3d} (asleep={int(asl_he[sel].sum()):2d}, wake={int(wk_he[sel].sum()):1d}) std_real={std_real:.4f}:\n"
        f"   Saved s42/s43                  : std_r={s42_sr:.3f}/{s43_sr:.3f}  R2={s42_r2:+.3f}/{s43_r2:+.3f}\n"
        f"   Oracle(Ctr6x6+HUD only, no wk) : std_r={s1:.3f}  R2={r1:+.3f}\n"
        f"   Oracle(Wake only)              : std_r={s2:.3f}  R2={r2:+.3f}\n"
        f"   Ridge(SleepWake only)          : std_r={s4:.3f}  R2={r4:+.3f}\n"
        f"   Oracle(Local) + Ridge(Wake)    : std_r={s3:.3f}  R2={r3:+.3f}\n"
        f"   Realizable Ridge(Local+Wake)   : std_r={s5:.3f}  R2={r5:+.3f}"
    )

# 3. Compare OuterTerr RMS on non-asleep frames: noop vs do vs place_table vs place_furnace!
print("\n=== PART 2B-3: NON-ASLEEP OUTER-TERRAIN MOTION (MOBS/DAYLIGHT) ACROSS NON-MOVE ACTIONS ===")
for q in [0, 5, 7, 8, 9, 10, 11]:
    m = (a1_he == q) & (~asl_he)
    dy = dY_he[m]
    mask_out = np.zeros((16, 16), dtype=bool)
    mask_out[:12, :] = True
    mask_out[3:9, 5:11] = False
    out_rms = float(np.sqrt((dy[:, mask_out, :] ** 2).mean()))
    ctr_rms = float(np.sqrt((dy[:, 3:9, 5:11, :] ** 2).mean()))
    hud_rms = float(np.sqrt((dy[:, 12:, :, :] ** 2).mean()))
    print(f"  a={q:2d} (n={int(m.sum()):3d}): OuterTerr_rms={out_rms:.4f} | Ctr6x6_rms={ctr_rms:.4f} | HUD_rms={hud_rms:.4f}")
