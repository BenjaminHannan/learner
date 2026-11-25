"""Verify forecast5/scorer.py on saved M3 checkpoints (CPU-only, nice -n 10, zero training, zero MPS).
Proves on legacy dev held-out (1000..1015, NEVER touching sealed_test.npz):
  1. Synthetic drift & verdict checks (--selftest) ALL PASS.
  2. Dead Step-5 refit (run_forecast3_refit/model.pt, alpha=0):
     - Under old absolute-frame decoding: fake pcs90_pred ~107 (PASS) and copy_ness ~0.605.
     - Under fixed forecast5 residual decoding: pcs90_pred drops to 1 (FAIL), copy_ness -> 0.000, std_ok=False, FAIL.
  3. Perfect-Memory Real-Board Oracle (real_board(t+k) through Step-6 frozen RT):
     - Under old absolute-frame decoding: FAILS std_ratio <= 2.0 on noop (~5.0!).
     - Under fixed forecast5 residual decoding: PASSES all marks (E/B <= 0.80/0.90/0.95, std_ok=True, pcs_ok=True, ceiling <= 0.70, PASS).
  4. 1-Line Linear Per-Action Baseline (M_a [x_t, 1]): PASSES all marks under forecast5.
  5. Saved Step-6 (run_forecast4/model.pt): STILL FAILS cleanly under forecast5 (no false pass).
"""
import dataclasses
import json
import os
import sys
import time
import numpy as np
import torch

torch.set_grad_enabled(False)
dev = "cpu"

HARNESS = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7/wm-harness")
WM5 = os.path.expanduser("~/learner-ops/seven-problems-m3/PROBLEM-7/wm5")
sys.path.insert(0, HARNESS)
sys.path.insert(0, WM5)

import wm_fit as W
import sizes
from imagine_head6 import damped_imagine as damped_imagine6, add_head
from imagine_damped import damped_imagine as damped_imagine5, add_alpha
import scorer as S

SCALE = 0.20385979115962982
W.rms_level = lambda t: t / SCALE
NOISE = 0.2

t0 = time.time()
print("=== 1. SYNTHETIC DRIFT & VERDICT SELFTEST ===", flush=True)
st_rep = S.run_selftest()

tr = S.load_split(f"{HARNESS}/data/train.npz")
he = S.load_split(f"{HARNESS}/data/heldout.npz")
xi1_tr, ai1_tr, w1_tr, _, t1_tr = S.windows(tr, 1)
hfr = he["frames"].astype(np.float64)
sh_he_acts = S.shuffle_actions_per_step(he, seed=43)

def F(d, i):
    return torch.from_numpy(d["frames"][i].astype(np.float32)).to(dev)

def real_board_batch(m, d, i, tpos):
    h = np.where(tpos > 0, i - 1, i)
    st = m.read(m.cell.init_state(len(i), 1, device=dev, dtype=torch.float32), m.encode(F(d, h)))
    return m.read(st, m.encode(F(d, i)))

def compute_all_boards(m, d, batch=128):
    n = len(d["frames"])
    idx = np.arange(n)
    tpos = d["t_index"]
    out = np.empty((n, m.R, m.D), dtype=np.float32)
    for b in range(0, n, batch):
        sl = slice(b, min(b + batch, n))
        out[sl] = real_board_batch(m, d, idx[sl], tpos[sl]).rows[:, 0].numpy()
    return out

def enc_act(m, act):
    B = act.shape[0]
    at = m.action_emb(act)
    at = (at / at.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6))[:, None]
    z = torch.zeros(B, 1, device=dev)
    ctx = W.Context(
        tokens=at,
        mask=torch.ones(B, 1, dtype=torch.bool, device=dev),
        support=torch.ones(B, 1, device=dev),
        source=torch.full((B, 1), int(W.Source.SIGHT), dtype=torch.long, device=dev),
        age_s=z,
        epoch=torch.zeros(B, dtype=torch.long, device=dev),
        q_hash=torch.zeros(B, dtype=torch.long, device=dev),
    )
    return m.cell.encode_context(ctx)

def fit_rt(m):
    rr = np.random.default_rng(11)
    ji = np.r_[rr.choice(np.flatnonzero(w1_tr < 140), 3500, replace=False),
               rr.choice(np.flatnonzero(w1_tr >= 140), 500, replace=False)]
    Z = np.concatenate([
        real_board_batch(m, tr, xi1_tr[ji[b:b+128]], t1_tr[ji[b:b+128]]).rows[:, 0].numpy()
        for b in range(0, 4000, 128)
    ]).reshape(4000, -1).astype(np.float64)
    Y = tr["frames"][xi1_tr[ji]].astype(np.float64).reshape(4000, -1)
    mu = Z[:3500].mean(0)
    sd = np.maximum(Z[:3500].std(0), 1e-3 + 0.1 * np.median(Z[:3500].std(0)))
    A = (Z[:3500] - mu) / sd
    ym = Y[:3500].mean(0)
    lam = 3500 * NOISE ** 2
    al = np.linalg.solve(A @ A.T + lam * np.eye(3500), Y[:3500] - ym)
    Wnp = (A.T @ al) / sd[:, None]
    bp = ym - mu @ Wnp
    RT = lambda r_np: (r_np.reshape(len(r_np), -1).astype(np.float64) @ Wnp + bp).reshape(-1, 16, 16, 3)
    return RT, sd

def make_state(m, rows_np):
    st = m.cell.init_state(len(rows_np), 1, device=dev, dtype=torch.float32)
    return dataclasses.replace(st, rows=torch.from_numpy(rows_np).unsqueeze(1))

def rollout_model(m, imagine_step, Z_all, RT):
    preds_abs, shuf_abs, preds_res, shuf_res = {}, {}, {}, {}
    for k in (1, 3, 5):
        xi, ai, _, _, _ = S.windows(he, k)
        x0 = hfr[xi]
        acts = S.action_values(he["actions"], ai, k)
        sh = S.action_values(sh_he_acts, ai, k)
        Z0 = Z_all[xi]
        rt0 = RT(Z0)
        for tag, act_mat, d_abs, d_res in [
            ("true", acts, preds_abs, preds_res),
            ("shuf", sh, shuf_abs, shuf_res),
        ]:
            out = np.empty_like(Z0)
            for b in range(0, len(xi), 128):
                sl = slice(b, min(b + 128, len(xi)))
                st = make_state(m, Z0[sl])
                for j in range(k):
                    a_t = torch.from_numpy(act_mat[sl, j].astype(np.int64))
                    o = imagine_step(m.cell, st, enc_act(m, a_t), m.action_emb(a_t))
                    st = dataclasses.replace(st, rows=o.next_rows)
                out[sl] = st.rows[:, 0].numpy()
            rt_k = RT(out)
            d_abs[k] = rt_k
            d_res[k] = S.residual_decode(x0, rt_k, rt0)
    xi1 = S.windows(he, 1)[0]
    ceil_abs = RT(Z_all[xi1 + 1])
    ceil_res = S.residual_decode(hfr[xi1], ceil_abs, RT(Z_all[xi1]))
    return preds_abs, shuf_abs, preds_res, shuf_res, ceil_abs, ceil_res

# --- 2. Dead Step-5 Refit ---
print("\n=== 2. DEAD STEP-5 REFIT (run_forecast3_refit/model.pt) ===", flush=True)
torch.manual_seed(42)
m5 = W.WorldModel(sizes.make_cfg("P7toy")).to(dev); del m5.head; add_alpha(m5.cell)
m5.load_state_dict(torch.load(f"{HARNESS}/run_forecast3_refit/model.pt", map_location=dev, weights_only=False)["m"], strict=False)
m5.eval()
RT5, _ = fit_rt(m5)
Z5_he = compute_all_boards(m5, he)
p5_abs, ps5_abs, p5_res, ps5_res, c5_abs, c5_res = rollout_model(m5, damped_imagine5, Z5_he, RT5)
s5_old = S.score_predictions(tr, he, p5_abs, ps5_abs, c5_abs, c5_res, extra_meta={"model": "step5_refit_old_abs"})
s5_new = S.score_predictions(tr, he, p5_res, ps5_res, c5_abs, c5_res, extra_meta={"model": "step5_refit_forecast5_res"})
print(f"Step-5 OLD abs: pcs={s5_old['k1']['pcs90_pred']}/{s5_old['k1']['pcs90_real']} (ok={s5_old['pcs_ok']}), copy_ness={s5_old['k1']['copy_ness']:.4f}, std_ok={s5_old['std_ok']}, verdict={s5_old['verdict']}", flush=True)
print(f"Step-5 NEW res: pcs={s5_new['k1']['pcs90_pred']}/{s5_new['k1']['pcs90_real']} (ok={s5_new['pcs_ok']}), copy_ness={s5_new['k1']['copy_ness']:.6f}, std_ok={s5_new['std_ok']}, verdict={s5_new['verdict']}", flush=True)

# --- 3. Step-6 & Perfect-Memory Real-Board Oracle ---
print("\n=== 3. PERFECT-MEMORY ORACLE & STEP-6 (run_forecast4/model.pt) ===", flush=True)
torch.manual_seed(42)
m6 = W.WorldModel(sizes.make_cfg("P7toy")).to(dev); del m6.head; add_head(m6.cell)
m6.load_state_dict(torch.load(f"{HARNESS}/run_forecast4/model.pt", map_location=dev, weights_only=False)["m"], strict=False)
m6.eval()
RT6, sd6 = fit_rt(m6)
m6.cell.imagine_scale = torch.tensor(sd6, dtype=torch.float32).view(m6.R, m6.D)
Z6_he = compute_all_boards(m6, he)

# Perfect-memory oracle: true next board decoded via RT6; shuffled-action counterfactual via M_a [x_t, 1] on sh_he_acts
Mact = S.fit_linear_action_baseline(tr)
po_abs, po_res, pso_shuf = {}, {}, {}
for k in (1, 3, 5):
    xi, ai, _, _, _ = S.windows(he, k)
    x0 = hfr[xi]
    rt_k = RT6(Z6_he[xi + k])
    rt_0 = RT6(Z6_he[xi])
    po_abs[k] = rt_k
    po_res[k] = S.residual_decode(x0, rt_k, rt_0)
    pso_shuf[k] = S.rollout_linear_action_baseline(Mact, x0, S.action_values(sh_he_acts, ai, k))

xi1_h = S.windows(he, 1)[0]
c6_abs = RT6(Z6_he[xi1_h + 1])
c6_res = S.residual_decode(hfr[xi1_h], c6_abs, RT6(Z6_he[xi1_h]))

so_old = S.score_predictions(tr, he, po_abs, pso_shuf, c6_abs, c6_res, extra_meta={"model": "oracle_old_abs"})
so_new = S.score_predictions(tr, he, po_res, pso_shuf, c6_abs, c6_res, extra_meta={"model": "oracle_forecast5_res"})
print(f"Oracle OLD abs: E/B={so_old['k1']['E_over_B']:.4f}/{so_old['k3']['E_over_B']:.4f}/{so_old['k5']['E_over_B']:.4f}, noop_std={so_old['k1']['std_ratio_by_action']['0']['ratio']:.3f}, all_n20_ok={so_old['k1']['std_ratio_all_n20_ok']}, active_ok={so_old['std_ok']}", flush=True)
print(f"Oracle NEW res: E/B={so_new['k1']['E_over_B']:.4f}/{so_new['k3']['E_over_B']:.4f}/{so_new['k5']['E_over_B']:.4f}, noop_std={so_new['k1']['std_ratio_by_action']['0']['ratio']:.3f}, fw_std={so_new['k1']['freq_weighted_std_ratio']:.3f}, active_ok={so_new['std_ok']}, pcs={so_new['k1']['pcs90_pred']}/{so_new['k1']['pcs90_real']}, worlds={so_new['worlds_k1_shuffle']}/{so_new['worlds_k5_shuffle']}/{so_new['worlds_both']}, verdict={so_new['verdict']}", flush=True)

# 1-Line Linear Per-Action Baseline end-to-end
pl_t, pl_s = {}, {}
for k in (1, 3, 5):
    xi, ai, _, _, _ = S.windows(he, k)
    pl_t[k] = S.rollout_linear_action_baseline(Mact, hfr[xi], S.action_values(he["actions"], ai, k))
    pl_s[k] = S.rollout_linear_action_baseline(Mact, hfr[xi], S.action_values(sh_he_acts, ai, k))
sl_new = S.score_predictions(tr, he, pl_t, pl_s, extra_meta={"model": "linear_per_action_forecast5"})
print(f"Linear M_a NEW: E/B={sl_new['k1']['E_over_B']:.4f}/{sl_new['k3']['E_over_B']:.4f}/{sl_new['k5']['E_over_B']:.4f}, shuf={sl_new['k1']['shuffle_pooled']:.3f}/{sl_new['k5']['shuffle_pooled']:.3f}, worlds={sl_new['worlds_k1_shuffle']}/{sl_new['worlds_k5_shuffle']}/{sl_new['worlds_both']}, std_ok={sl_new['std_ok']}, pcs={sl_new['k1']['pcs90_pred']}/{sl_new['k1']['pcs90_real']}, verdict={sl_new['verdict']}", flush=True)

# Saved Step-6 end-to-end
p6_abs, ps6_abs, p6_res, ps6_res, _, _ = rollout_model(m6, damped_imagine6, Z6_he, RT6)
s6_old = S.score_predictions(tr, he, p6_abs, ps6_abs, c6_abs, c6_res, extra_meta={"model": "step6_old_abs"})
s6_new = S.score_predictions(tr, he, p6_res, ps6_res, c6_abs, c6_res, extra_meta={"model": "step6_forecast5_res"})
print(f"Step-6 OLD abs: E/B={s6_old['k1']['E_over_B']:.4f}/{s6_old['k3']['E_over_B']:.4f}/{s6_old['k5']['E_over_B']:.4f}, shuf={s6_old['k1']['shuffle_pooled']:.3f}/{s6_old['k5']['shuffle_pooled']:.3f}, worlds={s6_old['worlds_both']}, verdict={s6_old['verdict']}", flush=True)
print(f"Step-6 NEW res: E/B={s6_new['k1']['E_over_B']:.4f}/{s6_new['k3']['E_over_B']:.4f}/{s6_new['k5']['E_over_B']:.4f}, shuf={s6_new['k1']['shuffle_pooled']:.3f}/{s6_new['k5']['shuffle_pooled']:.3f}, worlds={s6_new['worlds_both']}, pcs={s6_new['k1']['pcs90_pred']}/{s6_new['k1']['pcs90_real']}, std_ok={s6_new['std_ok']}, verdict={s6_new['verdict']}", flush=True)

# Hard proof assertions (Step-5 refit has tiny residual |alpha| ~4e-5; verify fake pcs=107 & copy_ness=0.605 collapse!)
assert s5_old["pcs_ok"] is True and s5_old["k1"]["pcs90_pred"] >= 100 and s5_old["k1"]["copy_ness"] > 0.5
assert s5_new["pcs_ok"] is False and s5_new["k1"]["pcs90_pred"] <= 10, f"Step-5 refit failed to drop fake pcs90: {s5_new['k1']['pcs90_pred']}"
assert s5_new["k1"]["copy_ness"] < 0.01 and s5_new["std_ok"] is False and s5_new["verdict"] == "FAIL"
assert so_old["k1"]["std_ratio_all_n20_ok"] is False, "Expected old abs oracle to fail noop std_ratio"
assert so_new["verdict"] == "PASS", f"Expected residual oracle PASS, got {so_new['verdict']} {so_new['marks']}"
assert sl_new["verdict"] == "PASS", f"Expected linear M_a PASS, got {sl_new['verdict']} {sl_new['marks']}"
assert s6_new["verdict"] == "FAIL", f"Expected Step-6 FAIL under new ruler, got {s6_new['verdict']}"

out = {
    "elapsed_s": round(time.time() - t0, 2),
    "selftest": st_rep,
    "step5_old_abs": s5_old,
    "step5_new_res": s5_new,
    "oracle_old_abs": so_old,
    "oracle_new_res": so_new,
    "linear_M_a_new": sl_new,
    "step6_old_abs": s6_old,
    "step6_new_res": s6_new,
}
print("===VERIFY_JSON_BEGIN===")
print(json.dumps(out, indent=1))
print("===VERIFY_JSON_END===")
