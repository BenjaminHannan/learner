"""Read-only CPU diagnostic Part 3:
  3A. Saved s42 & s43 on TRAIN asleep/wake frames + AE fidelity on HUD energy pixels.
  3B. Exact train loss-share simulation for candidate single-knob loss weightings.
  3C. Full scorer.py evaluation of zero-training `reencode_res` on s42 & s43 (real + shuffled k=1,3,5)
      plus step-by-step block_open / alpha / sharpness under `reencode_res`.
"""
import os
import sys
import time
import numpy as np
import torch

torch.set_grad_enabled(False)
t0 = time.time()

BASE = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7")
sys.path.insert(0, os.path.join(BASE, "wm6"))
import scorer
from model_v6 import SpatialWorldModelV6

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

def get_sleep_masks(x0, x1):
    s0 = x0[:, :12].std((1, 2, 3))
    s1 = x1[:, :12].std((1, 2, 3))
    rms = np.sqrt(((x1 - x0) ** 2).mean((1, 2, 3)))
    is_asleep = s0 < 0.08
    is_wake = is_asleep & (s1 > 0.10) & (rms > 0.08)
    return is_asleep, is_wake

asl_tr, wk_tr = get_sleep_masks(x0_tr, x1_tr)
asl_he, wk_he = get_sleep_masks(x0_he, x1_he)

models = {}
for seed in (42, 43):
    m = SpatialWorldModelV6(size="R6conv")
    ck = torch.load(os.path.join(BASE, f"wm6/run_r6_s{seed}/model.pt"), map_location="cpu", weights_only=False)
    m.load_state_dict(ck["model"], strict=True)
    m.eval()
    models[seed] = m

# ============================================================================
# 3A. SAVED MODELS ON TRAIN ASLEEP/WAKE FRAMES & HUD AE FIDELITY
# ============================================================================
print("=== PART 3A: SAVED s42 & s43 ON TRAIN ASLEEP/WAKE FRAMES & HUD AE FIDELITY ===")
asl_tr_idx = np.flatnonzero(asl_tr)
# Evaluate all 138 train wake frames + 600 random train stay-asleep frames
rng = np.random.default_rng(77)
wk_tr_idx = np.flatnonzero(wk_tr)
sta_tr_idx = rng.choice(np.flatnonzero(asl_tr & (~wk_tr)), size=600, replace=False)

def eval_k1_and_ae(model, x0_np, a_np, batch=256):
    dp_l, ae_l = [], []
    for b in range(0, len(a_np), batch):
        sl = slice(b, min(b + batch, len(a_np)))
        x = torch.from_numpy(x0_np[sl].astype(np.float32))
        a = torch.from_numpy(a_np[sl, None].astype(np.int64))
        z0 = model.encode(x)
        dec0 = model.decode(z0)
        z1 = model.imagine_step(z0, a[:, 0], wm_grad=False)
        dec1 = model.decode(z1)
        dp_l.append((dec1 - dec0).double().numpy())
        ae_l.append((dec0 - x).double().numpy())
    return np.concatenate(dp_l, 0), np.concatenate(ae_l, 0)

for seed in (42, 43):
    m = models[seed]
    dp_wk, ae_wk = eval_k1_and_ae(m, x0_tr[wk_tr_idx], a1_tr[wk_tr_idx])
    dp_st, ae_st = eval_k1_and_ae(m, x0_tr[sta_tr_idx], a1_tr[sta_tr_idx])
    rms_wk = np.sqrt((dp_wk ** 2).mean((1, 2, 3)))
    rms_st = np.sqrt((dp_st ** 2).mean((1, 2, 3)))
    r2_wk = 1.0 - float(((dp_wk - dY_tr[wk_tr_idx]) ** 2).sum()) / float((dY_tr[wk_tr_idx] ** 2).sum())
    # AE fidelity on HUD energy pixels (12,6), (13,8), (13,9) vs signal difference (0.029)
    ae_hud_rms = float(np.sqrt((ae_wk[:, 12:, :, :] ** 2).mean()))
    ae_en_rms = float(np.sqrt((ae_wk[:, [12, 13, 13], [6, 8, 9], :] ** 2).mean()))
    # Check AUROC of model's predicted brightness jump dBright on TRAIN wake vs stay!
    db_wk = dp_wk[:, :12].mean((1, 2, 3))
    db_st = dp_st[:, :12].mean((1, 2, 3))
    au = float((db_wk[:, None] > db_st[None, :]).mean() + 0.5 * (db_wk[:, None] == db_st[None, :]).mean())
    print(
        f"  s{seed} TRAIN asleep: wake(n={len(wk_tr_idx)}) pred_rms={rms_wk.mean():.4f} (true={np.sqrt((dY_tr[wk_tr_idx]**2).mean((1,2,3))).mean():.4f}, R2={r2_wk:+.3f}, dBright={db_wk.mean():+.4f}) | "
        f"stay(n={len(sta_tr_idx)}) pred_rms={rms_st.mean():.4f} (dBright={db_st.mean():+.4f}) | AUROC(dBright)={au:.3f}"
    )
    print(f"       AE recon error on wake frames: HUD_rms={ae_hud_rms:.5f}, top3_energy_px_rms={ae_en_rms:.5f} (signal diff ~0.029)")
    # Also check: does AE reconstruction of HUD preserve linear wake-AUROC?
    x_tr_ae_wk = x0_tr[wk_tr_idx] + ae_wk
    x_tr_ae_st = x0_tr[sta_tr_idx] + ae_st
    # Check per-action on train wakes (moves vs non-moves)
    mv_w = np.isin(a1_tr[wk_tr_idx], [1, 2, 3, 4])
    print(
        f"       TRAIN wake split: moves(n={int(mv_w.sum())}) pred_rms={rms_wk[mv_w].mean():.4f} dB={db_wk[mv_w].mean():+.4f} | "
        f"nonmove(n={int((~mv_w).sum())}) pred_rms={rms_wk[~mv_w].mean():.4f} dB={db_wk[~mv_w].mean():+.4f}"
    )

# Also check WHY train wake AUROC is what it is: what fraction of train wakes had energy==9 vs hurt?
# Check using energy pixel (12, 6) and (13, 8) distributions on wake vs stay!
print("\n  [Inspect exact (12,6) and (13,8) HUD energy pixels on TRAIN wake vs stay]")
e12_6_wk = x0_tr[wk_tr_idx, 12, 6, :].mean(axis=1)
e12_6_st = x0_tr[sta_tr_idx, 12, 6, :].mean(axis=1)
print(f"    pixel (12,6) mean RGB pcts: wake={[round(float(v),3) for v in np.percentile(e12_6_wk, [10,25,50,75,90])]} | stay={[round(float(v),3) for v in np.percentile(e12_6_st, [10,25,50,75,90])]}")

# Check exact Crafter sleep wake-up reason by checking health pixel or exact HUD diff at t-1 -> t!
# Wait: also check how many steps after a=6 each train wake occurs!
starts_tr, ends_tr, aoffs_tr = scorer.episode_index(tr)
# Map each window to steps_since_sleep
ep_s_tr = {int(tr["episode_id"][s]): (int(s), int(ao)) for s, e, ao in zip(starts_tr, ends_tr, aoffs_tr)}
durs_tr = []
for idx in wk_tr_idx:
    ep = int(tr["episode_id"][xi1_tr[idx]])
    t = int(tr["t_index"][xi1_tr[idx]])
    s, ao = ep_s_tr[ep]
    pa = tr["actions"][ao : ao + t]
    sp = np.flatnonzero(pa == 6)
    durs_tr.append(int(t - sp[-1]) if len(sp) else -1)
vals, cnts = np.unique(durs_tr, return_counts=True)
top_durs = sorted(zip(cnts.tolist(), vals.tolist()), reverse=True)[:10]
print(f"    Top-10 sleep durations before TRAIN wake (count, steps): {top_durs}")

# ============================================================================
# 3B. LOSS-SHARE SIMULATION FOR CANDIDATE SINGLE-KNOB LOSS WEIGHTINGS
# ============================================================================
print("\n=== PART 3B: TRAIN LOSS-SHARE SIMULATION FOR CANDIDATE WEIGHTINGS (AT COPY/STEP-0 ERROR) ===")
# Compare how different 100% domain-general loss weightings rebalance gradient share across event types!
err_px = (dY_tr ** 2).mean(axis=3)  # [28000, 16, 16] per-pixel squared change
chg_mask = np.abs(dY_tr).mean(axis=3) > 0.02  # [28000, 16, 16] (exact Step-2 definition!)
ex_mse = err_px.mean(axis=(1, 2))  # [28000]
# Per-example changed-pixel MSE (Step-2 style: mean over changed pixels of that example, 0 if none)
chg_cnt = chg_mask.sum(axis=(1, 2))
ex_chg_mse = np.where(chg_cnt > 0, (err_px * chg_mask).sum(axis=(1, 2)) / np.maximum(chg_cnt, 1), 0.0)
# Per-pixel weighted MSE: (1 + 10 * chg_mask)
ex_pxw10 = (err_px * (1.0 + 10.0 * chg_mask)).mean(axis=(1, 2))
# Inverse action-frequency weight (1 / p(a), capped or uncapped)
a_cnts = np.bincount(a1_tr, minlength=17).astype(np.float64)
inv_a_w = (len(a1_tr) / 17.0) / np.maximum(a_cnts[a1_tr], 1.0)
# Inverse action-RMS weight (1 / max(std_a, 0.01)) -> equalizes per-action SSE contribution!
a_sse = np.array([float(ex_mse[a1_tr == q].sum()) for q in range(17)])
inv_asse_w = (ex_mse.sum() / 17.0) / np.maximum(a_sse[a1_tr], 1e-8)

is_sleep_enter = (a1_tr == 6) & (~asl_tr) & (np.sqrt(ex_mse) > 0.08)
buckets = [
    ("moves_awake (1..4)",   np.isin(a1_tr, [1, 2, 3, 4]) & (~asl_tr)),
    ("sleep_enter (a=6)",    is_sleep_enter),
    ("sleep_wake (ANY a)",   wk_tr),
    ("do_awake (a=5)",       (a1_tr == 5) & (~asl_tr)),
    ("place_table (a=8)",    (a1_tr == 8) & (~asl_tr)),
    ("place_furnace (a=9)",  (a1_tr == 9) & (~asl_tr)),
    ("other_awake",          (~np.isin(a1_tr, [1, 2, 3, 4, 5, 8, 9])) & (~is_sleep_enter) & (~asl_tr)),
]

schemes = [
    ("uniform_MSE", ex_mse),
    ("MSE + 1*chg_ex", ex_mse + ex_chg_mse),
    ("MSE + 2*chg_ex", ex_mse + 2.0 * ex_chg_mse),
    ("px_w(1+10*chg)", ex_pxw10),
    ("inv_act_freq", ex_mse * inv_a_w),
    ("inv_act_freq + chg_ex", (ex_mse + ex_chg_mse) * inv_a_w),
    ("inv_act_SSE", ex_mse * inv_asse_w),
]
hdr = f"{'bucket':<22} | " + " | ".join(f"{name:>13}" for name, _ in schemes)
print(hdr)
print("-" * len(hdr))
for bname, bm in buckets:
    row = f"{bname:<22} | " + " | ".join(f"{100*float(sc[bm].sum())/float(sc.sum()):12.2f}%" for _, sc in schemes)
    print(row)

# Also check within do_awake & place_table_awake: share of loss on Ctr6x6+HUD vs OuterTerr under uniform vs chg_ex!
for q, qname in [(5, "do_awake"), (8, "place_table_awake")]:
    bm = (a1_tr == q) & (~asl_tr)
    ep_u = err_px[bm]
    cm = chg_mask[bm]
    # Under per-example chg_mse, each pixel (i,y,x) has effective weight 1/cnt_i if chg else 0
    w_ce = np.where(cm, 1.0 / np.maximum(cm.sum(axis=(1, 2), keepdims=True), 1), 0.0)
    m_ch = np.zeros((16, 16), dtype=bool)
    m_ch[3:9, 5:11] = True
    m_ch[12:, :] = True
    share_u = float(ep_u[:, m_ch].sum() / ep_u.sum())
    share_c = float((ep_u * w_ce)[:, m_ch].sum() / (ep_u * w_ce).sum())
    print(f"  [{qname}] Ctr6x6+HUD share of SSE: uniform={share_u*100:.1f}% | chg_ex={share_c*100:.1f}%")

# ============================================================================
# 3C. FULL SCORER.PY CHECK OF ZERO-TRAINING `reencode_res` ON s42 & s43!
# ============================================================================
print(f"\n=== PART 3C: FULL SCORER.PY CHECK OF ZERO-TRAINING `reencode_res` ON s42 & s43 (t={time.time()-t0:.1f}s) ===")
sh_acts = scorer.shuffle_actions_per_step(he, seed=43)
hfr = he["frames"]

def eval_reencode_res_full(model, batch_size=256):
    preds_by_k = {}
    shuf_preds_by_k = {}
    ceil_abs_k1, ceil_res_k1 = None, None
    for k in (1, 3, 5):
        xi, ai, _, _, _ = scorer.windows(he, k)
        acts_k = scorer.action_values(he["actions"], ai, k)
        s_acts_k = scorer.action_values(sh_acts, ai, k)
        P_list, Ps_list, ca_list, cr_list = [], [], [], []
        for b in range(0, len(xi), batch_size):
            sl = slice(b, min(b + batch_size, len(xi)))
            i = xi[sl]
            x0 = torch.from_numpy(hfr[i].astype(np.float32))
            for ak_np, out_list in [(acts_k[sl], P_list), (s_acts_k[sl], Ps_list)]:
                ak = torch.from_numpy(ak_np.astype(np.int64))
                z0 = model.encode(x0)
                dec0 = model.decode(z0)
                z = z0
                for stp in range(k):
                    z = model.imagine_step(z, ak[:, stp], wm_grad=False)
                    dec_s = model.decode(z)
                    pred_s = x0 + (dec_s - dec0)
                    if stp < k - 1:
                        # Zero-training pixel-manifold snap (pure open-loop, zero intermediate true frames!)
                        z = model.encode(pred_s.clamp(0.0, 1.0))
                out_list.append(pred_s.double().numpy())
            if k == 1:
                x1 = torch.from_numpy(hfr[i + 1].astype(np.float32))
                z0 = model.encode(x0)
                d0 = model.decode(z0)
                d1 = model.decode(model.encode(x1))
                ca_list.append(d1.double().numpy())
                cr_list.append((x0 + (d1 - d0)).double().numpy())
        preds_by_k[k] = np.concatenate(P_list, 0)
        shuf_preds_by_k[k] = np.concatenate(Ps_list, 0)
        if k == 1:
            ceil_abs_k1 = np.concatenate(ca_list, 0)
            ceil_res_k1 = np.concatenate(cr_list, 0)
    return scorer.score_predictions(tr, he, preds_by_k, shuf_preds_by_k,
                                    ceiling_abs_pred_k1=ceil_abs_k1,
                                    ceiling_res_pred_k1=ceil_res_k1), preds_by_k

for seed in (42, 43):
    t1 = time.time()
    res, pbk = eval_reencode_res_full(models[seed])
    k1, k3, k5 = res["k1"], res["k3"], res["k5"]
    bo = k1["block_open"]["model"]
    # Also compute k=5 sharpness under reencode_res
    P5 = pbk[5]
    xi5 = scorer.windows(he, 5)[0]
    Y5 = he["frames"][xi5 + 5].astype(np.float64)
    ge_y = float(((Y5[:, 1:12] - Y5[:, 0:11])**2).mean() + ((Y5[:, :12, 1:] - Y5[:, :12, :-1])**2).mean())
    ge_p = float(((P5[:, 1:12] - P5[:, 0:11])**2).mean() + ((P5[:, :12, 1:] - P5[:, :12, :-1])**2).mean())
    print(
        f"  s{seed} reencode_res ({time.time()-t1:.1f}s): "
        f"E/B={k1['E_over_B']:.4f}/{k3['E_over_B']:.4f}/{k5['E_over_B']:.4f} "
        f"(CI95 k5={[round(v,4) for v in k5['E_over_B_ci95_worlds']]}, E/sos k5={k5['E_over_strongest_baseline']:.4f} "
        f"CI95={[round(v,4) for v in k5['E_over_strongest_baseline_ci95_worlds']]}) | "
        f"shuf={k1['shuffle_pooled']:.2f}/{k5['shuffle_pooled']:.2f} worlds={res['worlds_k1_shuffle']}/{res['worlds_k5_shuffle']}/{res['worlds_both']} | "
        f"bo={bo['mean_err']:.4f} pcs={k1['pcs90_pred']}/{k1['pcs90_real']} std_ok={res['std_ok']} | "
        f"k5 gradE={ge_p/ge_y:.3f} | rung1_marks={res['rung1_marks']}"
    )

print(f"\n[PART 3 DONE in {time.time()-t0:.1f}s]")
