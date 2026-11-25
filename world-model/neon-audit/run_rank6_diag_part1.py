"""Read-only CPU diagnostic Part 1 for PROBLEM-7 Rank 6 (data & saved forecasts_dev.npz).

Runs strictly on CPU with zero writes to M3 or model/data directories.
"""
import os
import sys
import json
import numpy as np

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer

# 1. Crafter action names
try:
    import crafter
    ACTION_NAMES = list(crafter.constants.actions)
except Exception as e:
    ACTION_NAMES = [f"act_{i}" for i in range(17)]
    print(f"[WARN] could not import crafter: {e}")

print("=== CRAFTER ACTIONS (17) ===")
for i, name in enumerate(ACTION_NAMES):
    print(f"  {i:2d}: {name}")

tr = scorer.load_split(os.path.join(BASE, "wm5/data/train_dn.npz"))
he = scorer.load_split(os.path.join(BASE, "wm-harness/data/heldout.npz"))

fc42 = dict(np.load(os.path.join(BASE, "wm6/run_r6_s42/forecasts_dev.npz")))
fc43 = dict(np.load(os.path.join(BASE, "wm6/run_r6_s43/forecasts_dev.npz")))
with open(os.path.join(BASE, "wm6/run_r6_s42/score_dev.json")) as f:
    sc42 = json.load(f)
with open(os.path.join(BASE, "wm6/run_r6_s43/score_dev.json")) as f:
    sc43 = json.load(f)

Mact = scorer.fit_linear_action_baseline(tr)
sos = scorer.fit_shift_or_stay_baseline(tr)

# Precompute k=1 windows for train and dev
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

P42_1 = fc42["pred_k1"].astype(np.float64)
P43_1 = fc43["pred_k1"].astype(np.float64)
dP42_1 = P42_1 - x0_he
dP43_1 = P43_1 - x0_he

P_mact_1 = scorer.rollout_linear_action_baseline(Mact, x0_he, a1_he[:, None])
P_sos_1 = scorer.rollout_shift_or_stay(sos, x0_he, a1_he[:, None])
dP_mact_1 = P_mact_1 - x0_he
dP_sos_1 = P_sos_1 - x0_he

print("\n=== PART 1A: PER-ACTION ANATOMY (TRAIN vs DEV, k=1) ===")
tot_sse_tr = float((dY_tr ** 2).sum())
tot_sse_he = float((dY_he ** 2).sum())
tot_err42_he = float(((P42_1 - x1_he) ** 2).sum())
tot_err43_he = float(((P43_1 - x1_he) ** 2).sum())
tot_errsos_he = float(((P_sos_1 - x1_he) ** 2).sum())

hdr = (
    f"{'a':>2} {'name':<16} | {'tr_n':>5} {'tr_%':>5} {'tr_dY%':>6} {'tr_std':>6} | "
    f"{'dv_n':>4} {'dv_%':>5} {'dv_dY%':>6} {'dv_std':>6} | "
    f"{'s42_r':>5} {'s43_r':>5} {'mact_r':>6} | {'s42_E/c':>7} {'s43_E/c':>7} {'sos_E/c':>7} | {'s42_E%':>6}"
)
print(hdr)
print("-" * len(hdr))
for q in range(17):
    st = a1_tr == q
    sh = a1_he == q
    nt, nh = int(st.sum()), int(sh.sum())
    dy_t = dY_tr[st]
    dy_h = dY_he[sh]
    sse_t = float((dy_t ** 2).sum())
    sse_h = float((dy_h ** 2).sum())
    std_t = float(dy_t.std()) if nt else 0.0
    std_h = float(dy_h.std()) if nh else 0.0

    dp42 = dP42_1[sh]
    dp43 = dP43_1[sh]
    dpm = dP_mact_1[sh]
    r42 = float(dp42.std() / (std_h + 1e-12)) if nh else 0.0
    r43 = float(dp43.std() / (std_h + 1e-12)) if nh else 0.0
    rm = float(dpm.std() / (std_h + 1e-12)) if nh else 0.0

    e42 = float(((P42_1[sh] - x1_he[sh]) ** 2).sum())
    e43 = float(((P43_1[sh] - x1_he[sh]) ** 2).sum())
    esos = float(((P_sos_1[sh] - x1_he[sh]) ** 2).sum())
    print(
        f"{q:2d} {ACTION_NAMES[q]:<16} | {nt:5d} {100*nt/len(a1_tr):5.1f} {100*sse_t/tot_sse_tr:6.2f} {std_t:6.4f} | "
        f"{nh:4d} {100*nh/len(a1_he):5.1f} {100*sse_h/tot_sse_he:6.2f} {std_h:6.4f} | "
        f"{r42:5.3f} {r43:5.3f} {rm:6.3f} | {e42/max(sse_h,1e-12):7.3f} {e43/max(sse_h,1e-12):7.3f} {esos/max(sse_h,1e-12):7.3f} | "
        f"{100*e42/tot_err42_he:6.2f}"
    )

print("\n=== PART 1B: CORRELATION, CALIBRATION SLOPE & R^2 PER ACTION (DEV k=1) ===")
print(f"{'a':>2} {'name':<16} | {'n':>4} | {'s42_R2':>7} {'sqrtR2':>6} {'std_r':>6} {'slope':>6} {'corr':>6} | {'s43_R2':>7} {'std_r':>6} {'slope':>6} {'corr':>6}")
for q in range(17):
    sh = a1_he == q
    if not sh.any():
        continue
    y = dY_he[sh].reshape(-1)
    p42 = dP42_1[sh].reshape(-1)
    p43 = dP43_1[sh].reshape(-1)
    yc = y - y.mean()
    vy = float((yc ** 2).mean())

    def stats(p):
        pc = p - p.mean()
        vp = float((pc ** 2).mean())
        cov = float((pc * yc).mean())
        mse = float(((p - y) ** 2).mean())
        r2 = 1.0 - mse / max(float((y ** 2).mean()), 1e-12)
        corr = cov / max(np.sqrt(vp * vy), 1e-12)
        slope = cov / max(vp, 1e-12)
        sr = np.sqrt(vp / max(vy, 1e-12))
        return r2, np.sqrt(max(r2, 0.0)), sr, slope, corr

    r2_42, sq_42, sr_42, sl_42, co_42 = stats(p42)
    r2_43, sq_43, sr_43, sl_43, co_43 = stats(p43)
    print(
        f"{q:2d} {ACTION_NAMES[q]:<16} | {int(sh.sum()):4d} | "
        f"{r2_42:7.3f} {sq_42:6.3f} {sr_42:6.3f} {sl_42:6.2f} {co_42:6.3f} | "
        f"{r2_43:7.3f} {sr_43:6.3f} {sl_43:6.2f} {co_43:6.3f}"
    )

print("\n=== PART 1C: DEEP ANATOMY OF INTERACTION ACTIONS (0, 5, 6, 7, 8, 9, 10) ===")
def spatial_energy_split(delta):
    # delta: [N, 16, 16, 3]
    tot = (delta ** 2).sum((1, 2, 3))
    hud = (delta[:, 12:16, :, :] ** 2).sum((1, 2, 3))
    ctr = (delta[:, 3:9, 5:11, :] ** 2).sum((1, 2, 3))
    ter = (delta[:, 0:12, :, :] ** 2).sum((1, 2, 3))
    outer = ter - ctr
    # Global brightness shift component vs zero-mean spatial pattern
    gmean = delta.mean((1, 2, 3), keepdims=True)
    glob = ((gmean ** 2) * np.ones_like(delta)).sum((1, 2, 3))
    return tot, hud, ctr, outer, glob

for split_name, a_arr, x0_arr, x1_arr, dy_arr, ei_arr, ti_arr, wi_arr in [
    ("TRAIN", a1_tr, x0_tr, x1_tr, dY_tr, ei1_tr, ti1_tr, wi1_tr),
    ("DEV",   a1_he, x0_he, x1_he, dY_he, ei1_he, ti1_he, wi1_he),
]:
    print(f"\n--- {split_name} per-window RMS distribution & spatial energy breakdown ---")
    for q in [0, 5, 6, 7, 8, 9, 10]:
        sel = a_arr == q
        dy = dy_arr[sel]
        rms = np.sqrt((dy ** 2).mean((1, 2, 3)))
        tot, hud, ctr, outer, glob = spatial_energy_split(dy)
        qs = np.percentile(rms, [0, 25, 50, 75, 90, 95, 99, 100])
        frac_gt01 = float((rms > 0.01).mean())
        frac_gt02 = float((rms > 0.02).mean())
        frac_gt05 = float((rms > 0.05).mean())
        frac_gt10 = float((rms > 0.10).mean())
        # Concentration: share of total SSE in top 1, top 3, top 5, top 10% windows
        order = np.argsort(tot)[::-1]
        ts = max(float(tot.sum()), 1e-12)
        top1 = float(tot[order[:1]].sum() / ts)
        top3 = float(tot[order[:3]].sum() / ts)
        top5 = float(tot[order[:5]].sum() / ts)
        top10p = float(tot[order[:max(1, len(order)//10)]].sum() / ts)
        # std_real without top 1 / top 3 / top 5
        std_all = float(dy.std())
        std_no1 = float(dy[order[1:]].std()) if len(order) > 2 else 0.0
        std_no3 = float(dy[order[3:]].std()) if len(order) > 4 else 0.0
        std_no5 = float(dy[order[5:]].std()) if len(order) > 6 else 0.0
        print(
            f"  a={q:2d} ({ACTION_NAMES[q]:<13}) n={int(sel.sum()):4d} std={std_all:.4f} "
            f"(noTop1={std_no1:.4f}, noTop3={std_no3:.4f}, noTop5={std_no5:.4f}) | "
            f"SSE share: top1={top1*100:4.1f}% top3={top3*100:4.1f}% top5={top5*100:4.1f}% top10%={top10p*100:4.1f}%"
        )
        print(
            f"     RMS pcts [0,25,50,75,90,95,99,100]: {[round(float(v), 4) for v in qs]} "
            f"|>0.01:{frac_gt01*100:.1f}% >0.02:{frac_gt02*100:.1f}% >0.05:{frac_gt05*100:.1f}% >0.10:{frac_gt10*100:.1f}%"
        )
        print(
            f"     Spatial SSE share: HUD={100*hud.sum()/ts:5.1f}% Center6x6={100*ctr.sum()/ts:5.1f}% "
            f"OuterTerr={100*outer.sum()/ts:5.1f}% GlobalBright={100*glob.sum()/ts:5.1f}%"
        )

print("\n=== PART 1D: TOP-10 LARGEST-CHANGE DEV WINDOWS FOR ACTIONS 5, 8, 9 (INSPECT EXACT CAUSE!) ===")
starts_he, ends_he, aoffs_he = scorer.episode_index(he)
# Map each frame index to episode length and position
ep_len_map = {}
for s, e in zip(starts_he, ends_he):
    ep_len_map[int(he["episode_id"][s])] = int(e - s)

for q in [5, 8, 9]:
    sel_idx = np.flatnonzero(a1_he == q)
    dy = dY_he[sel_idx]
    tot, hud, ctr, outer, glob = spatial_energy_split(dy)
    order = np.argsort(tot)[::-1][:10]
    print(f"\n--- DEV Action {q} ({ACTION_NAMES[q]}), total n={len(sel_idx)}, total SSE={tot.sum():.2f} ---")
    for rank, k_i in enumerate(order):
        idx = sel_idx[k_i]
        xi = int(xi1_he[idx])
        ai = int(ai1_he[idx])
        ep = int(ei1_he[idx])
        t = int(ti1_he[idx])
        w = int(wi1_he[idx])
        ep_len = ep_len_map[ep]
        prev_a = int(he["actions"][ai - 1]) if t > 0 else -1
        next_a = int(he["actions"][ai + 1]) if t + 2 < ep_len else -1
        m0 = float(x0_he[idx].mean())
        m1 = float(x1_he[idx].mean())
        rms = float(np.sqrt((dY_he[idx] ** 2).mean()))
        rms_p42 = float(np.sqrt((dP42_1[idx] ** 2).mean()))
        rms_p43 = float(np.sqrt((dP43_1[idx] ** 2).mean()))
        # Max changed pixel coordinate
        px_err = (dY_he[idx] ** 2).mean(axis=2)
        my, mx = np.unravel_index(np.argmax(px_err), (16, 16))
        # Check if frame is dark/sleeping (x0 terrain dark -> x1 bright, or vice versa)
        t0_m = float(x0_he[idx, :12].mean())
        t1_m = float(x1_he[idx, :12].mean())
        print(
            f"  #{rank+1:2d} w={w} ep={ep:2d} t={t:3d}/{ep_len:3d} prev_a={prev_a:2d} next_a={next_a:2d} | "
            f"SSE={tot[k_i]:6.2f} ({100*tot[k_i]/tot.sum():4.1f}%) rms={rms:.4f} (s42={rms_p42:.4f}, s43={rms_p43:.4f}) | "
            f"HUD={100*hud[k_i]/tot[k_i]:4.1f}% Ctr={100*ctr[k_i]/tot[k_i]:4.1f}% Out={100*outer[k_i]/tot[k_i]:4.1f}% "
            f"Glob={100*glob[k_i]/tot[k_i]:4.1f}% | terrMean {t0_m:.3f}->{t1_m:.3f} maxPx=({my:2d},{mx:2d})"
        )

print("\n=== PART 1E: CHECK SLEEP-WAKE / BRIGHTNESS-JUMP CONTAMINATION ON ALL ACTIONS! ===")
# Check if prev_a == 6 (sleep) or dark terrain waking up happens on actions 5, 8, 9!
prev_a_he = np.full(len(a1_he), -1, dtype=np.int64)
prev_a_tr = np.full(len(a1_tr), -1, dtype=np.int64)
for idx in range(len(a1_he)):
    if ti1_he[idx] > 0:
        prev_a_he[idx] = he["actions"][ai1_he[idx] - 1]
for idx in range(len(a1_tr)):
    if ti1_tr[idx] > 0:
        prev_a_tr[idx] = tr["actions"][ai1_tr[idx] - 1]

# Also check if player was sleeping (very dark terrain < 0.08 or massive brightness jump |d_terr_mean| > 0.08)
for name, a_arr, x0_arr, x1_arr, dy_arr, pa_arr in [
    ("TRAIN", a1_tr, x0_tr, x1_tr, dY_tr, prev_a_tr),
    ("DEV",   a1_he, x0_he, x1_he, dY_he, prev_a_he),
]:
    d_terr = x1_arr[:, :12].mean((1, 2, 3)) - x0_arr[:, :12].mean((1, 2, 3))
    t0_m = x0_arr[:, :12].mean((1, 2, 3))
    print(f"\n--- {name}: global brightness jumps (|d_terr_mean| > 0.05) per action ---")
    for q in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        sel = a_arr == q
        big_b = sel & (np.abs(d_terr) > 0.05)
        n_big = int(big_b.sum())
        if n_big > 0 or q in (5, 6, 8, 9):
            sse_all = float((dy_arr[sel] ** 2).sum())
            sse_big = float((dy_arr[big_b] ** 2).sum()) if n_big else 0.0
            std_all = float(dy_arr[sel].std())
            std_nobig = float(dy_arr[sel & ~big_b].std()) if (sel & ~big_b).any() else 0.0
            print(
                f"  a={q:2d} ({ACTION_NAMES[q]:<13}) n={int(sel.sum()):4d} bigBright={n_big:3d} "
                f"(SSE share={100*sse_big/max(sse_all,1e-12):5.1f}%) | std_all={std_all:.4f} -> std_noBrightJump={std_nobig:.4f}"
            )

# Check how model predicts on NON-bright-jump interaction windows vs bright-jump windows!
print("\n--- DEV: Model s42/s43 on actions 5, 8, 9 split by |d_terr_mean| > 0.05 vs <= 0.05 ---")
d_terr_he = x1_he[:, :12].mean((1, 2, 3)) - x0_he[:, :12].mean((1, 2, 3))
for q in [5, 6, 8, 9]:
    sel = a1_he == q
    for tag, m in [("brightJump(>0.05)", sel & (np.abs(d_terr_he) > 0.05)),
                   ("localOnly(<=0.05)", sel & (np.abs(d_terr_he) <= 0.05))]:
        if not m.any():
            continue
        dy = dY_he[m]
        dp42 = dP42_1[m]
        dp43 = dP43_1[m]
        sse_c = float((dy ** 2).sum())
        e42 = float(((P42_1[m] - x1_he[m]) ** 2).sum())
        e43 = float(((P43_1[m] - x1_he[m]) ** 2).sum())
        print(
            f"  a={q:2d} {tag:<18} n={int(m.sum()):3d} std_real={dy.std():.4f} "
            f"s42_std={dp42.std():.4f} (r={dp42.std()/(dy.std()+1e-12):.3f}, E/c={e42/max(sse_c,1e-12):.3f}) | "
            f"s43_std={dp43.std():.4f} (r={dp43.std()/(dy.std()+1e-12):.3f}, E/c={e43/max(sse_c,1e-12):.3f})"
        )

print("\n=== PART 1F: k=1, k=3, k=5 DRIFT DECOMPOSITION (MODEL s42 & s43 vs shift_or_stay) ===")
for k in (1, 3, 5):
    xi, ai, wi, ei, ti = scorer.windows(he, k)
    acts_k = scorer.action_values(he["actions"], ai, k)
    x0 = he["frames"][xi].astype(np.float64)
    yk = he["frames"][xi + k].astype(np.float64)
    P42 = fc42[f"pred_k{k}"].astype(np.float64)
    P43 = fc43[f"pred_k{k}"].astype(np.float64)
    Psos = scorer.rollout_shift_or_stay(sos, x0, acts_k)

    e42 = ((P42 - yk) ** 2).sum((1, 2, 3))
    e43 = ((P43 - yk) ** 2).sum((1, 2, 3))
    esos = ((Psos - yk) ** 2).sum((1, 2, 3))
    B = sc42[f"k{k}"]["B"]

    print(f"\n--- HORIZON k={k} (n={len(xi)}, B={B:.1f}) ---")
    print(f"  TOTAL SSE: s42={e42.sum():.1f} ({e42.sum()/B:.4f}) | s43={e43.sum():.1f} ({e43.sum()/B:.4f}) | sos={esos.sum():.1f} ({esos.sum()/B:.4f})")
    print(f"  GAP (model - sos): s42={e42.sum()-esos.sum():+.1f} ({(e42.sum()-esos.sum())/B:+.4f}) | s43={e43.sum()-esos.sum():+.1f} ({(e43.sum()-esos.sum())/B:+.4f})")

    # 1. Spatial decomposition of SSE and gap
    regions = {
        "outer_border_2px": np.zeros((16, 16), dtype=bool),
        "interior_terrain": np.zeros((16, 16), dtype=bool),
        "center_6x6":       np.zeros((16, 16), dtype=bool),
        "hud_rows_12_15":   np.zeros((16, 16), dtype=bool),
    }
    regions["hud_rows_12_15"][12:16, :] = True
    regions["center_6x6"][3:9, 5:11] = True
    regions["interior_terrain"][2:10, 2:14] = True
    regions["interior_terrain"][3:9, 5:11] = False
    regions["outer_border_2px"][0:12, :] = True
    regions["outer_border_2px"][2:10, 2:14] = False

    print("  [Spatial breakdown of SSE (model - sos)]")
    for rname, rmask in regions.items():
        s42_r = float(((P42[:, rmask, :] - yk[:, rmask, :]) ** 2).sum())
        s43_r = float(((P43[:, rmask, :] - yk[:, rmask, :]) ** 2).sum())
        sos_r = float(((Psos[:, rmask, :] - yk[:, rmask, :]) ** 2).sum())
        print(
            f"    {rname:<18} ({int(rmask.sum()):3d} px): s42={s42_r:7.1f} s43={s43_r:7.1f} sos={sos_r:7.1f} | "
            f"gap42={s42_r-sos_r:+7.1f} gap43={s43_r-sos_r:+7.1f} (ratio42={s42_r/max(sos_r,1e-9):.3f}, ratio43={s43_r/max(sos_r,1e-9):.3f})"
        )

    # 2. Action-sequence bucket breakdown
    has_sleep = (acts_k == 6).any(axis=1)
    has_do = (acts_k == 5).any(axis=1)
    has_place89 = ((acts_k == 8) | (acts_k == 9)).any(axis=1)
    has_other_nonmove = (~np.isin(acts_k, [1, 2, 3, 4])).any(axis=1)
    pure_moves = ~has_other_nonmove
    # Among pure moves, count unique/net shift or brightness jump
    d_terr_k = np.abs(yk[:, :12].mean((1, 2, 3)) - x0[:, :12].mean((1, 2, 3)))
    # Also check day vs night start frame
    is_dark0 = x0[:, :12].mean((1, 2, 3)) < 0.25

    buckets = [
        ("pure_moves (only 1..4)", pure_moves),
        ("has_sleep (a=6)", has_sleep),
        ("has_do (a=5, no sleep)", (~has_sleep) & has_do),
        ("has_place89 (no slp/do)", (~has_sleep) & (~has_do) & has_place89),
        ("other_nonmove (0,7,10-16)", (~has_sleep) & (~has_do) & (~has_place89) & has_other_nonmove),
    ]
    print("  [Action-sequence bucket breakdown (mutually exclusive, sums to TOTAL)]")
    for bname, bm in buckets:
        n_b = int(bm.sum())
        s42_b, s43_b, sos_b = float(e42[bm].sum()), float(e43[bm].sum()), float(esos[bm].sum())
        print(
            f"    {bname:<26} n={n_b:4d} ({100*n_b/len(xi):4.1f}%): s42={s42_b:7.1f} s43={s43_b:7.1f} sos={sos_b:7.1f} | "
            f"gap42={s42_b-sos_b:+7.1f} gap43={s43_b-sos_b:+7.1f} (r42={s42_b/max(sos_b,1e-9):.3f}, r43={s43_b/max(sos_b,1e-9):.3f})"
        )

    # Sub-split pure_moves by how many steps actually moved (net true displacement or number of open steps)
    if k == 5:
        # Count number of true open moves inside the 5-step window using step-by-step ground truth
        open_cnt = np.zeros(len(xi), dtype=np.int64)
        blk_cnt = np.zeros(len(xi), dtype=np.int64)
        for stp in range(5):
            vm, op, _ = scorer.classify_move_displacement(
                he["frames"][xi + stp], he["frames"][xi + stp + 1], acts_k[:, stp]
            )
            open_cnt += (vm & op).astype(np.int64)
            blk_cnt += (vm & (~op)).astype(np.int64)
        print("  [k=5 breakdown by # of true OPEN moves in window (all actions)]")
        for oc in range(6):
            bm = open_cnt == oc
            if not bm.any():
                continue
            print(
                f"    open_moves={oc}: n={int(bm.sum()):4d} | s42={e42[bm].sum():7.1f} s43={e43[bm].sum():7.1f} sos={esos[bm].sum():7.1f} | "
                f"gap42={e42[bm].sum()-esos[bm].sum():+7.1f} gap43={e43[bm].sum()-esos[bm].sum():+7.1f} "
                f"(r42={e42[bm].sum()/max(esos[bm].sum(),1e-9):.3f}, r43={e43[bm].sum()/max(esos[bm].sum(),1e-9):.3f})"
            )
        print("  [k=5 breakdown by # of true BLOCKED moves in window (all actions)]")
        for bc_name, bm in [("blk=0", blk_cnt == 0), ("blk=1", blk_cnt == 1), ("blk>=2", blk_cnt >= 2)]:
            print(
                f"    {bc_name:<12}: n={int(bm.sum()):4d} | s42={e42[bm].sum():7.1f} s43={e43[bm].sum():7.1f} sos={esos[bm].sum():7.1f} | "
                f"gap42={e42[bm].sum()-esos[bm].sum():+7.1f} gap43={e43[bm].sum()-esos[bm].sum():+7.1f} "
                f"(r42={e42[bm].sum()/max(esos[bm].sum(),1e-9):.3f}, r43={e43[bm].sum()/max(esos[bm].sum(),1e-9):.3f})"
            )
        print("  [k=5 breakdown by Day vs Night start frame (mean terrain < 0.25)]")
        for dn_name, bm in [("day (m>=0.25)", ~is_dark0), ("night (m<0.25)", is_dark0)]:
            print(
                f"    {dn_name:<15}: n={int(bm.sum()):4d} | s42={e42[bm].sum():7.1f} s43={e43[bm].sum():7.1f} sos={esos[bm].sum():7.1f} | "
                f"gap42={e42[bm].sum()-esos[bm].sum():+7.1f} gap43={e43[bm].sum()-esos[bm].sum():+7.1f}"
            )
        print("  [k=5 breakdown by big brightness jump |d_terr_k| > 0.08]")
        for bj_name, bm in [("brightJump(>0.08)", d_terr_k > 0.08), ("steadyBright", d_terr_k <= 0.08)]:
            print(
                f"    {bj_name:<18}: n={int(bm.sum()):4d} | s42={e42[bm].sum():7.1f} s43={e43[bm].sum():7.1f} sos={esos[bm].sum():7.1f} | "
                f"gap42={e42[bm].sum()-esos[bm].sum():+7.1f} gap43={e43[bm].sum()-esos[bm].sum():+7.1f}"
            )

    # 3. Sharpness / blur & calibration slope diagnostics at k=1,3,5
    def grad_energy(img):
        dy_p = img[:, 1:12, :, :] - img[:, 0:11, :, :]
        dx_p = img[:, 0:12, 1:, :] - img[:, 0:12, :-1, :]
        return float((dy_p ** 2).mean() + (dx_p ** 2).mean())

    def fft_hf_ratio(img):
        # 2D FFT on 12x16 terrain (averaged over channels)
        f = np.fft.rfft2(img[:, :12, :, :], axes=(1, 2))
        pwr = (np.abs(f) ** 2).mean(axis=(0, 3))
        fy = np.fft.fftfreq(12)[:, None]
        fx = np.fft.rfftfreq(16)[None, :]
        rad = np.sqrt(fy ** 2 + fx ** 2)
        hi = pwr[rad >= 0.25].sum()
        lo = pwr[(rad > 0) & (rad < 0.25)].sum()
        return float(hi), float(lo)

    ge_y = grad_energy(yk)
    ge_42 = grad_energy(P42)
    ge_43 = grad_energy(P43)
    ge_sos = grad_energy(Psos)
    hi_y, lo_y = fft_hf_ratio(yk)
    hi_42, lo_42 = fft_hf_ratio(P42)
    hi_43, lo_43 = fft_hf_ratio(P43)
    hi_sos, lo_sos = fft_hf_ratio(Psos)

    # Calibration slope & optimal shrinkage toward x0 (and toward mean_tr)
    dY_k = yk - x0
    d42_k = P42 - x0
    d43_k = P43 - x0
    dsos_k = Psos - x0
    c42 = float((d42_k * dY_k).sum() / max((d42_k ** 2).sum(), 1e-12))
    c43 = float((d43_k * dY_k).sum() / max((d43_k ** 2).sum(), 1e-12))
    csos = float((dsos_k * dY_k).sum() / max((dsos_k ** 2).sum(), 1e-12))
    # What E/B would rescaling delta by c* achieve?
    e42_cal = float((((x0 + c42 * d42_k) - yk) ** 2).sum())
    e43_cal = float((((x0 + c43 * d43_k) - yk) ** 2).sum())
    # Also optimal linear blend with train mean frame: alpha*P + (1-alpha)*mean_tr
    mean_tr = x0_tr.mean(0)
    def opt_mean_blend(P):
        a = P - mean_tr
        b = yk - mean_tr
        w = float((a * b).sum() / max((a ** 2).sum(), 1e-12))
        eb = float(((mean_tr + w * a - yk) ** 2).sum())
        return w, eb
    w42_m, e42_m = opt_mean_blend(P42)
    w43_m, e43_m = opt_mean_blend(P43)
    wsos_m, esos_m = opt_mean_blend(Psos)

    print(
        f"  [Sharpness/Blur] terrain gradE vs true: s42={ge_42/ge_y:.3f} s43={ge_43/ge_y:.3f} sos={ge_sos/ge_y:.3f} | "
        f"FFT HF vs true: s42={hi_42/hi_y:.3f} s43={hi_43/hi_y:.3f} sos={hi_sos/hi_y:.3f} | "
        f"LF vs true: s42={lo_42/lo_y:.3f} s43={lo_43/lo_y:.3f} sos={lo_sos/lo_y:.3f}"
    )
    print(
        f"  [Calibration] opt delta scale c*: s42={c42:.3f} (E/B {e42.sum()/B:.4f}->{e42_cal/B:.4f}) | "
        f"s43={c43:.3f} (E/B {e43.sum()/B:.4f}->{e43_cal/B:.4f}) | sos={csos:.3f}"
    )
    print(
        f"  [Mean-blend]  opt w*P+(1-w)*mean: s42 w={w42_m:.3f} (E/B->{e42_m/B:.4f}) | "
        f"s43 w={w43_m:.3f} (E/B->{e43_m/B:.4f}) | sos w={wsos_m:.3f} (E/B->{esos_m/B:.4f})"
    )
    # Also check variance of predictions vs true frames (on border vs interior!)
    for rname, rmask in [("border2px", regions["outer_border_2px"]), ("interior", regions["interior_terrain"])]:
        vt = float(yk[:, rmask, :].var())
        v42 = float(P42[:, rmask, :].var())
        v43 = float(P43[:, rmask, :].var())
        vsos = float(Psos[:, rmask, :].var())
        # Optimal blend with mean_tr per region
        a42 = P42[:, rmask, :] - mean_tr[rmask, :]
        ay = yk[:, rmask, :] - mean_tr[rmask, :]
        w42r = float((a42 * ay).sum() / max((a42 ** 2).sum(), 1e-12))
        asos = Psos[:, rmask, :] - mean_tr[rmask, :]
        wsosr = float((asos * ay).sum() / max((asos ** 2).sum(), 1e-12))
        print(
            f"  [Var {rname:<9}] true={vt:.5f} s42={v42:.5f} ({v42/vt:.2f}x, cal_w={w42r:.3f}) "
            f"s43={v43:.5f} ({v43/vt:.2f}x) sos={vsos:.5f} ({vsos/vt:.2f}x, cal_w={wsosr:.3f})"
        )

print("\n=== PART 1G: PER-WORLD k=5 COMPARISON (s42 & s43 vs sos) ===")
xi5, ai5, wi5, _, _ = scorer.windows(he, 5)
acts5 = scorer.action_values(he["actions"], ai5, 5)
x0_5 = he["frames"][xi5].astype(np.float64)
y5 = he["frames"][xi5 + 5].astype(np.float64)
e42_5 = ((fc42["pred_k5"].astype(np.float64) - y5) ** 2).sum((1, 2, 3))
e43_5 = ((fc43["pred_k5"].astype(np.float64) - y5) ** 2).sum((1, 2, 3))
esos_5 = ((scorer.rollout_shift_or_stay(sos, x0_5, acts5) - y5) ** 2).sum((1, 2, 3))
w_beat42 = 0
w_beat43 = 0
for w in np.unique(wi5):
    m = wi5 == w
    r42 = e42_5[m].sum() / esos_5[m].sum()
    r43 = e43_5[m].sum() / esos_5[m].sum()
    w_beat42 += int(r42 < 1.0)
    w_beat43 += int(r43 < 1.0)
    print(
        f"  world {int(w)}: n={int(m.sum()):3d} | s42/sos={r42:.3f} (gap={e42_5[m].sum()-esos_5[m].sum():+6.1f}) | "
        f"s43/sos={r43:.3f} (gap={e43_5[m].sum()-esos_5[m].sum():+6.1f})"
    )
print(f"  Worlds where model beats sos at k=5: s42={w_beat42}/16, s43={w_beat43}/16")
print("\n[PART 1 DONE]")
