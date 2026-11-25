"""Read-only CPU diagnostic X-ray of saved Rung-1 Arm 1 (run_r1_bundle/model.pt & forecasts_dev.npz).
Strict rules: CPU only, ZERO training, ZERO MPS, ZERO writes on M3, NEVER opens sealed_test.npz.
"""
import dataclasses
import json
import os
import sys
import numpy as np
import torch

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.abspath("../wm-harness"))

import scorer as S
import sizes
from model_v5 import WorldModelV5
from premonition_core_v2.board_swarm import ThinkMode
from train_v5 import ARM_CONFIGS

dev = torch.device("cpu")
cfg = sizes.make_cfg("P7toy")
acfg = ARM_CONFIGS["bundle"]

model = WorldModelV5(
    cfg,
    use_signal_path=acfg["use_signal_path"],
    use_act_film=acfg["use_act_film"],
    seed=42,
).to(dev)
ck = torch.load("run_r1_bundle/model.pt", map_location=dev, weights_only=False)
model.load_state_dict(ck["model"], strict=True)
model.eval()

tr = S.load_split("data/train_dn.npz")
he = S.load_split("../wm-harness/data/heldout.npz")
fc = dict(np.load("run_r1_bundle/forecasts_dev.npz"))

xi1_tr, ai1_tr, wi1_tr, _, t1_tr = S.windows(tr, 1)
xi1_he, ai1_he, wi1_he, _, t1_he = S.windows(he, 1)
tr_fr = tr["frames"].astype(np.float32)
he_fr = he["frames"].astype(np.float32)


@torch.no_grad()
def run_split_batch(split, xi, ai, ti, n_sub=None, seed=123):
    if n_sub is not None and len(xi) > n_sub:
        idx_sub = np.random.default_rng(seed).choice(len(xi), n_sub, replace=False)
        xi, ai, ti = xi[idx_sub], ai[idx_sub], ti[idx_sub]
    fr = split["frames"].astype(np.float32)
    acts = split["actions"][ai]
    n = len(xi)
    R, D = model.R, model.D
    rows0 = np.empty((n, R, D), dtype=np.float32)
    rows1_real = np.empty((n, R, D), dtype=np.float32)
    rows1_img = np.empty((n, R, D), dtype=np.float32)
    hn_img = np.empty((n, R, cfg.d_inner), dtype=np.float32)
    patch0 = np.empty((n, 16, D), dtype=np.float32)
    dec0 = np.empty((n, 16, 16, 3), dtype=np.float32)
    dec1_real = np.empty((n, 16, 16, 3), dtype=np.float32)
    dec1_img = np.empty((n, 16, 16, 3), dtype=np.float32)

    cell = model.cell
    mode = cell.mode_emb.weight[int(ThinkMode.IMAGINE_NEXT_STATE)]
    for b in range(0, n, 128):
        sl = slice(b, min(b + 128, n))
        i = xi[sl]
        tp = ti[sl]
        h = np.where(tp > 0, i - 1, i)
        xp = torch.from_numpy(fr[h])
        x0 = torch.from_numpy(fr[i])
        x1 = torch.from_numpy(fr[i + 1])
        at = torch.from_numpy(acts[sl].astype(np.int64))

        # Patch tokens before BoardCell
        centered = x0 - 0.5
        p = centered.reshape(len(i), 4, 4, 4, 4, 3).permute(0, 1, 3, 2, 4, 5).reshape(len(i), 16, 48)
        patch0[sl] = (model.reader(p) + model.pos[None]).numpy()

        st0, _ = model.real_board(xp, x0)
        st1, _ = model.real_board(x0, x1)
        o_img = model.imagine_step(st0, at, wm_grad=True)

        # Also extract hn_board from imagine trunk
        B = len(i)
        bidx = torch.arange(B)
        x0_r = st0.rows.reshape(B, R, D)
        a_u = model.action_emb(at)
        a_u = a_u / a_u.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6)
        rd = cell._reading(None, B, dev)
        cemb = cell.clock_enc(rd)[bidx]
        h_in = cell.in_proj(x0_r) + cell.row_type_emb(cell.row_type)[None] + cell.row_pos_emb[None] + mode + cemb[:, None]
        gamma, beta = model.act_film(a_u).chunk(2, dim=-1)
        h_in = h_in * (1.0 + torch.tanh(gamma)[:, None, :]) + beta[:, None, :]
        ha = cell.action_in(a_u) + cell.action_pos + mode + cemb
        h_all = torch.cat([h_in, ha[:, None]], dim=1)
        enc_a = model.encode_action_ctx(a_u)
        mem = enc_a.memory
        age_now = mem["age0"][bidx] + rd.elapsed_s.float()[bidx][:, None]
        h_out, _, _, _ = cell._trunk(h_all, mem, bidx, st0.focus.reshape(-1), age_now, None, R)
        hn_img[sl] = cell.norm_f(h_out)[:, :R].numpy()

        rows0[sl] = st0.rows[:, 0].numpy()
        rows1_real[sl] = st1.rows[:, 0].numpy()
        rows1_img[sl] = o_img.next_rows[:, 0].numpy()
        dec0[sl] = model.dec(st0.rows[:, 0]).numpy()
        dec1_real[sl] = model.dec(st1.rows[:, 0]).numpy()
        dec1_img[sl] = model.dec(o_img.next_rows[:, 0]).numpy()

    return dict(
        x0=fr[xi].astype(np.float64),
        x1=fr[xi + 1].astype(np.float64),
        acts=acts,
        patch0=patch0,
        rows0=rows0,
        rows1_real=rows1_real,
        rows1_img=rows1_img,
        hn_img=hn_img,
        dec0=dec0.astype(np.float64),
        dec1_real=dec1_real.astype(np.float64),
        dec1_img=dec1_img.astype(np.float64),
    )


print("=== 1. TRAIN (2048 wins) vs DEV (2048 wins) DIRECT METRICS ===")
d_tr = run_split_batch(tr, xi1_tr, ai1_tr, t1_tr, n_sub=2048, seed=11)
d_ev = run_split_batch(he, xi1_he, ai1_he, t1_he, n_sub=2048, seed=22)

# Verify saved forecasts_dev.npz matches recomputed dev k1
p_fc1 = fc["pred_k1"].astype(np.float64)
x0_he_all = he["frames"][xi1_he].astype(np.float64)
x1_he_all = he["frames"][xi1_he + 1].astype(np.float64)
a_he_all = he["actions"][ai1_he]
fc_copy_ratio = ((p_fc1 - x1_he_all) ** 2).sum() / ((x1_he_all - x0_he_all) ** 2).sum()
print(f"Saved forecasts_dev.npz k1: E/copy={fc_copy_ratio:.4f} (n={len(p_fc1)})")

for tag, d in [("TRAIN_2048", d_tr), ("DEV_2048", d_ev)]:
    x0, x1, acts = d["x0"], d["x1"], d["acts"]
    pred_res = x0 + (d["dec1_img"] - d["dec0"])
    pred_abs = d["dec1_img"]
    ceil_abs = d["dec1_real"]
    ceil_res = x0 + (d["dec1_real"] - d["dec0"])
    rec_mse = ((d["dec0"] - x0) ** 2).mean()
    copy_mse = ((x1 - x0) ** 2).mean()
    img_res_mse = ((pred_res - x1) ** 2).mean()
    img_abs_mse = ((pred_abs - x1) ** 2).mean()
    ceil_abs_mse = ((ceil_abs - x1) ** 2).mean()
    ceil_res_mse = ((ceil_res - x1) ** 2).mean()

    dr_true = (d["rows1_real"] - d["rows0"]).reshape(len(x0), -1).astype(np.float64)
    dr_pred = (d["rows1_img"] - d["rows0"]).reshape(len(x0), -1).astype(np.float64)
    r2_board = 1.0 - ((dr_pred - dr_true) ** 2).sum() / max(((dr_true - dr_true.mean(0)) ** 2).sum(), 1e-12)
    dr_norm_ratio = np.sqrt((dr_pred ** 2).mean()) / max(np.sqrt((dr_true ** 2).mean()), 1e-12)
    cos_board = (dr_pred * dr_true).sum(1) / (np.linalg.norm(dr_pred, axis=1) * np.linalg.norm(dr_true, axis=1) + 1e-12)

    ns = model.cell.ns
    r0 = d["rows0"].astype(np.float64)
    def bstat(arr):
        st = np.sqrt((arr.mean(0) ** 2).mean())
        sp = np.sqrt((arr.std(0) ** 2).mean())
        return st, sp, st / max(sp, 1e-12)
    st_s, sp_s, br_s = bstat(r0[:, :ns])
    st_f, sp_f, br_f = bstat(r0[:, ns:])
    st_a, sp_a, br_a = bstat(r0)

    # Also board delta R^2 on slow vs fast rows separately
    drs_t = (d["rows1_real"][:, :ns] - d["rows0"][:, :ns]).reshape(len(x0), -1).astype(np.float64)
    drs_p = (d["rows1_img"][:, :ns] - d["rows0"][:, :ns]).reshape(len(x0), -1).astype(np.float64)
    drf_t = (d["rows1_real"][:, ns:] - d["rows0"][:, ns:]).reshape(len(x0), -1).astype(np.float64)
    drf_p = (d["rows1_img"][:, ns:] - d["rows0"][:, ns:]).reshape(len(x0), -1).astype(np.float64)
    r2_s = 1.0 - ((drs_p - drs_t) ** 2).sum() / max(((drs_t - drs_t.mean(0)) ** 2).sum(), 1e-12)
    r2_f = 1.0 - ((drf_p - drf_t) ** 2).sum() / max(((drf_t - drf_t.mean(0)) ** 2).sum(), 1e-12)

    vm, to, al_true = S.classify_move_displacement(x0, x1, acts)
    _, po, al_pred = S.classify_move_displacement(x0, pred_res, acts)
    _, po_cr, al_cr = S.classify_move_displacement(x0, ceil_res, acts)
    _, po_ca, al_ca = S.classify_move_displacement(x0, ceil_abs, acts)
    op_m = vm & to
    bl_m = vm & (~to)
    print(f"\n[{tag}]")
    print(f"  rec_mse={rec_mse:.6f} (rmse={np.sqrt(rec_mse):.4f}) | copy_mse={copy_mse:.6f} (rmse={np.sqrt(copy_mse):.4f})")
    print(f"  img_res/copy={img_res_mse/copy_mse:.4f} | img_abs/copy={img_abs_mse/copy_mse:.4f} | ceil_abs/copy={ceil_abs_mse/copy_mse:.4f} | ceil_res/copy={ceil_res_mse/copy_mse:.4f}")
    print(f"  board burial: all={br_a:.2f} (st={st_a:.3f}, sp={sp_a:.3f}) | slow={br_s:.2f} (st={st_s:.3f}, sp={sp_s:.3f}) | fast={br_f:.2f} (st={st_f:.3f}, sp={sp_f:.3f})")
    print(f"  board delta: R2_all={r2_board:.4f} (slow={r2_s:.4f}, fast={r2_f:.4f}), pred_rms/true_rms={dr_norm_ratio:.4f}, mean_cos={cos_board.mean():.4f}")
    print(f"  pred_res alpha TRUE_OPEN (n={int(op_m.sum())}): mean={al_pred[op_m].mean():.4f} med={np.median(al_pred[op_m]):.4f} p90={np.percentile(al_pred[op_m], 90):.4f} max={al_pred[op_m].max():.4f}")
    print(f"  pred_res alpha TRUE_BLKD (n={int(bl_m.sum())}): mean={al_pred[bl_m].mean():.4f} med={np.median(al_pred[bl_m]):.4f} p90={np.percentile(al_pred[bl_m], 90):.4f} max={al_pred[bl_m].max():.4f}")
    print(f"  ceil_res block_open: fb={float((~po_cr[op_m]).mean()):.4f} fo={float(po_cr[bl_m].mean()):.4f} | open_al_med={np.median(al_cr[op_m]):.4f} blkd_al_med={np.median(al_cr[bl_m]):.4f}")
    print(f"  ceil_abs block_open: fb={float((~po_ca[op_m]).mean()):.4f} fo={float(po_ca[bl_m].mean()):.4f} | open_al_med={np.median(al_ca[op_m]):.4f} blkd_al_med={np.median(al_ca[bl_m]):.4f}")

    # Spatial error breakdown across moves 1..4 (open moves only vs all moves)
    mv = (acts >= 1) & (acts <= 4)
    dp_m = pred_res[mv] - x0[mv]
    dy_m = x1[mv] - x0[mv]
    err_m = pred_res[mv] - x1[mv]
    def reg_stats(sl_y, sl_x, nm):
        dy2 = (dy_m[:, sl_y, sl_x] ** 2).mean()
        dp2 = (dp_m[:, sl_y, sl_x] ** 2).mean()
        er2 = (err_m[:, sl_y, sl_x] ** 2).mean()
        print(f"    region {nm:14s}: E/copy={er2/max(dy2,1e-12):.4f}  pred_rms/true_rms={np.sqrt(dp2/max(dy2,1e-12)):.3f}  true_rms={np.sqrt(dy2):.4f}")
    print("  Spatial region breakdown on moves 1..4:")
    reg_stats(slice(2, 10), slice(2, 14), "interior_2..9")
    reg_stats(slice(0, 2), slice(0, 16), "top_border")
    reg_stats(slice(10, 12), slice(0, 16), "bot_terrain")
    reg_stats(slice(5, 7), slice(7, 9), "player_sprite")
    reg_stats(slice(12, 16), slice(0, 16), "HUD_12..15")

    print("  Per-action (0=noop, 1=L, 2=R, 3=U, 4=D, 5=do, 6=sleep):")
    for q in range(7):
        sel = acts == q
        if sel.sum() < 10:
            continue
        ec = ((pred_res[sel] - x1[sel]) ** 2).mean() / max(((x1[sel] - x0[sel]) ** 2).mean(), 1e-12)
        dp = (pred_res[sel] - x0[sel]).std()
        dy = (x1[sel] - x0[sel]).std()
        # Mean spatial change vs pixel-varying change
        dP_q = pred_res[sel] - x0[sel]
        dY_q = x1[sel] - x0[sel]
        # How much of predicted change is global mean shift (per frame) vs spatial pattern?
        glob_p = dP_q.mean((1, 2), keepdims=True)
        glob_frac_p = (glob_p ** 2).mean() / max((dP_q ** 2).mean(), 1e-12)
        glob_y = dY_q.mean((1, 2), keepdims=True)
        glob_frac_y = (glob_y ** 2).mean() / max((dY_q ** 2).mean(), 1e-12)
        # How much of predicted change is screen-blind constant image per action?
        const_p = dP_q.mean(0, keepdims=True)
        const_frac_p = (const_p ** 2).mean() / max((dP_q ** 2).mean(), 1e-12)
        print(f"    act={q} (n={int(sel.sum()):3d}): E/copy={ec:.4f} std_ratio={dp/(dy+1e-12):.3f} | global_brightness_frac(pred={glob_frac_p:.2f}, true={glob_frac_y:.2f}) | screen_blind_const_frac(pred={const_frac_p:.2f})")

print("\n=== 2. BOARD & DECODER CAPACITY PROBES (FIT ON TRAIN_2048, SCORED ON DEV_2048) ===")
Z_tr = d_tr["rows0"].reshape(len(d_tr["x0"]), -1).astype(np.float64)
Z_ev = d_ev["rows0"].reshape(len(d_ev["x0"]), -1).astype(np.float64)
Z1_tr = d_tr["rows1_real"].reshape(len(d_tr["x0"]), -1).astype(np.float64)
Z1_ev = d_ev["rows1_real"].reshape(len(d_ev["x0"]), -1).astype(np.float64)
P_tr = d_tr["patch0"].reshape(len(d_tr["x0"]), -1).astype(np.float64)
P_ev = d_ev["patch0"].reshape(len(d_ev["x0"]), -1).astype(np.float64)
H_tr = d_tr["hn_img"].reshape(len(d_tr["x0"]), -1).astype(np.float64)
H_ev = d_ev["hn_img"].reshape(len(d_ev["x0"]), -1).astype(np.float64)
X_tr = d_tr["x0"].reshape(len(d_tr["x0"]), -1)
X_ev = d_ev["x0"].reshape(len(d_ev["x0"]), -1)
Y_tr = d_tr["x1"].reshape(len(d_tr["x0"]), -1)
Y_ev = d_ev["x1"].reshape(len(d_ev["x0"]), -1)

def dual_ridge_pred(A_tr, B_tr, A_ev, lam):
    mu = A_tr.mean(0)
    sd = np.maximum(A_tr.std(0), 1e-3)
    At = (A_tr - mu) / sd
    Ae = (A_ev - mu) / sd
    ym = B_tr.mean(0)
    K = At @ At.T
    al = np.linalg.solve(K + lam * np.eye(len(At)), B_tr - ym)
    return (Ae @ At.T) @ al + ym

copy_sse_ev = ((Y_ev - X_ev) ** 2).sum()
copy_mse_ev = ((Y_ev - X_ev) ** 2).mean()

# Probe 2A: reconstruct x_t from real_board(t) vs RowLNDecoder vs patch0
for fname, F_tr, F_ev in [
    ("patch0 (16x192 before BoardCell)", P_tr, P_ev),
    ("real_board(t) (64x192)", Z_tr, Z_ev),
    ("RowLN-32 bottleneck (64x32)",
        model.dec.row_proj(model.dec.ln(torch.from_numpy(d_tr["rows0"]))).detach().flatten(1).numpy().astype(np.float64),
        model.dec.row_proj(model.dec.ln(torch.from_numpy(d_ev["rows0"]))).detach().flatten(1).numpy().astype(np.float64)),
]:
    best = (999.0, None, None)
    for lam in (0.1, 1.0, 10.0, 100.0, 500.0):
        px = dual_ridge_pred(F_tr, X_tr, F_ev, lam)
        mse = ((px - X_ev) ** 2).mean()
        if mse < best[0]:
            best = (mse, lam, px)
    print(f"Probe 2A rec x_t from {fname:36s}: MSE={best[0]:.6f} (rmse={np.sqrt(best[0]):.4f}, /copy={best[0]/copy_mse_ev:.4f}, lam={best[1]})")

dec_rec_ev = ((d_ev["dec0"].reshape(len(X_ev), -1) - X_ev) ** 2).mean()
print(f"Probe 2A rec x_t from trained RowLNDecoder                  : MSE={dec_rec_ev:.6f} (rmse={np.sqrt(dec_rec_ev):.4f}, /copy={dec_rec_ev/copy_mse_ev:.4f})")

# Fresh ridge decoder ceiling on real_board(t+1) + block_open
pred_x0_r = dual_ridge_pred(Z_tr, X_tr, Z_ev, 10.0)
pred_x1_r = dual_ridge_pred(Z_tr, X_tr, Z1_ev, 10.0)
ceil_r_abs = ((pred_x1_r - Y_ev) ** 2).sum() / copy_sse_ev
ceil_r_res = (((X_ev + pred_x1_r - pred_x0_r) - Y_ev) ** 2).sum() / copy_sse_ev
bo_rr = S.score_block_open(d_ev["x0"], (X_ev + pred_x1_r - pred_x0_r).reshape(-1, 16, 16, 3), d_ev["x1"], d_ev["acts"], np.zeros(len(X_ev), dtype=int))
print(f"Probe 2A-ceil (real_board(t+1) via fresh Ridge): abs/copy={ceil_r_abs:.4f}, res/copy={ceil_r_res:.4f}, bo_res=(fb={bo_rr['false_block_rate']:.4f}, fo={bo_rr['false_open_rate']:.4f}, me={bo_rr['mean_err']:.4f})")

# Probe 2B: Per-action linear ridge -> dx on SAME 2048 train/dev
for feat_name, F_tr, F_ev, lams in [
    ("Raw pixels x_t (768d)", X_tr, X_ev, [1.0, 10.0]),
    ("patch0 (16x192 before BoardCell)", P_tr, P_ev, [1.0, 10.0, 100.0]),
    ("real_board(t) full (64x192)", Z_tr, Z_ev, [10.0, 100.0, 500.0]),
    ("RowLN-32 bottleneck (64x32)",
        model.dec.row_proj(model.dec.ln(torch.from_numpy(d_tr["rows0"]))).detach().flatten(1).numpy().astype(np.float64),
        model.dec.row_proj(model.dec.ln(torch.from_numpy(d_ev["rows0"]))).detach().flatten(1).numpy().astype(np.float64),
        [10.0, 100.0, 500.0]),
    ("hn_img SHARED linear (single W, no act split)", H_tr, H_ev, [10.0, 100.0, 500.0]),
    ("hn_img PER-ACTION linear", H_tr, H_ev, [10.0, 100.0, 500.0]),
]:
    best = (999.0, None, None)
    shared_mode = "SHARED" in feat_name
    for lam in lams:
        if shared_mode:
            P_dx = dual_ridge_pred(F_tr, Y_tr - X_tr, F_ev, lam)
        else:
            P_dx = np.zeros_like(Y_ev)
            for q in range(17):
                s_tr = d_tr["acts"] == q
                s_ev = d_ev["acts"] == q
                if not s_ev.any() or s_tr.sum() < 5:
                    continue
                P_dx[s_ev] = dual_ridge_pred(F_tr[s_tr], (Y_tr - X_tr)[s_tr], F_ev[s_ev], lam)
        ec = (((X_ev + P_dx) - Y_ev) ** 2).sum() / copy_sse_ev
        if ec < best[0]:
            best = (ec, lam, P_dx)
    bo_p = S.score_block_open(d_ev["x0"], (X_ev + best[2]).reshape(-1, 16, 16, 3), d_ev["x1"], d_ev["acts"], np.zeros(len(X_ev), dtype=int))
    print(f"Probe 2B {feat_name:46s}: E/copy={best[0]:.4f} (lam={best[1]}) bo=(fb={bo_p['false_block_rate']:.3f}, fo={bo_p['false_open_rate']:.3f}, me={bo_p['mean_err']:.3f})")

# Probe 2C: Per-action ridge real_board(t) -> d_board -> trained model.dec
best_b2b = (999.0, None, 0.0, None)
for lam in (10.0, 100.0, 500.0):
    P_dr = np.zeros_like(Z_ev)
    for q in range(17):
        s_tr = d_tr["acts"] == q
        s_ev = d_ev["acts"] == q
        if not s_ev.any() or s_tr.sum() < 5:
            continue
        P_dr[s_ev] = dual_ridge_pred(Z_tr[s_tr], (Z1_tr - Z_tr)[s_tr], Z_ev[s_ev], lam)
    r2_lin = 1.0 - ((P_dr - (Z1_ev - Z_ev)) ** 2).sum() / max((((Z1_ev - Z_ev) - (Z1_ev - Z_ev).mean(0)) ** 2).sum(), 1e-12)
    with torch.no_grad():
        dec_p = model.dec(torch.from_numpy((Z_ev + P_dr).reshape(-1, model.R, model.D).astype(np.float32))).numpy().astype(np.float64)
    p_res = d_ev["x0"] + (dec_p - d_ev["dec0"])
    ec = ((p_res - d_ev["x1"]) ** 2).sum() / copy_sse_ev
    if ec < best_b2b[0]:
        best_b2b = (ec, lam, r2_lin, p_res)
bo_b2b = S.score_block_open(d_ev["x0"], best_b2b[3], d_ev["x1"], d_ev["acts"], np.zeros(len(X_ev), dtype=int))
print(f"Probe 2C (per-act ridge board->d_board->model.dec)      : E/copy={best_b2b[0]:.4f} (lam={best_b2b[1]}, board_dR2={best_b2b[2]:.4f}) bo=(fb={bo_b2b['false_block_rate']:.3f}, fo={bo_b2b['false_open_rate']:.3f}, me={bo_b2b['mean_err']:.3f})")

# Probe 2D: Row-independent ridge hn_img[:, r] -> d_board[:, r] (tests if trunk mixed info into each row!)
dB_tr = (d_tr["rows1_real"] - d_tr["rows0"]).astype(np.float64)
dB_ev = (d_ev["rows1_real"] - d_ev["rows0"]).astype(np.float64)
P_dr_row = np.empty_like(dB_ev)
for r_idx in range(model.R):
    ht = d_tr["hn_img"][:, r_idx, :].astype(np.float64)
    he_r = d_ev["hn_img"][:, r_idx, :].astype(np.float64)
    mu = ht.mean(0); sd = np.maximum(ht.std(0), 1e-3)
    At = np.c_[(ht - mu) / sd, np.ones(len(ht))]
    Ae = np.c_[(he_r - mu) / sd, np.ones(len(he_r))]
    W_r = np.linalg.solve(At.T @ At + 100.0 * np.eye(At.shape[1]), At.T @ dB_tr[:, r_idx, :])
    P_dr_row[:, r_idx, :] = Ae @ W_r
r2_row = 1.0 - ((P_dr_row - dB_ev) ** 2).sum() / max(((dB_ev - dB_ev.mean(0)) ** 2).sum(), 1e-12)
with torch.no_grad():
    dec_row = model.dec(torch.from_numpy((d_ev["rows0"] + P_dr_row).astype(np.float32))).numpy().astype(np.float64)
ec_row = (((d_ev["x0"] + dec_row - d_ev["dec0"]) - d_ev["x1"]) ** 2).sum() / copy_sse_ev
print(f"Probe 2D (row-indep ridge hn_img[:,r]->d_board[:,r]->dec): E/copy={ec_row:.4f}, board_dR2={r2_row:.4f}")

print("\n=== 3. ACTION x SCREEN BILINEAR ANOVA & ATTENTION MIXING (256 DEV SCREENS x ACTIONS 0..4) ===")
idx256 = np.random.default_rng(99).choice(len(xi1_he), 256, replace=False)
i256 = xi1_he[idx256]
t256 = t1_he[idx256]
h256 = np.where(t256 > 0, i256 - 1, i256)
with torch.no_grad():
    xp256 = torch.from_numpy(he_fr[h256])
    x0256 = torch.from_numpy(he_fr[i256])
    st256, _ = model.real_board(xp256, x0256)
    dec0_256 = model.dec(st256.rows[:, 0]).numpy()

    B, K, R, D = st256.rows.shape
    cell = model.cell
    ns = cell.ns
    bidx = torch.arange(B)
    x0_r = st256.rows.reshape(B, R, D)
    rd = cell._reading(None, B, dev)
    cemb = cell.clock_enc(rd)[bidx]
    mode = cell.mode_emb.weight[int(ThinkMode.IMAGINE_NEXT_STATE)]
    h_pre = cell.in_proj(x0_r) + cell.row_type_emb(cell.row_type)[None] + cell.row_pos_emb[None] + mode + cemb[:, None]

    A_list = [0, 1, 2, 3, 4]
    h_film_arr, hn_arr, delta_arr, px_delta_arr, gslow_arr = [], [], [], [], []
    exp_counts_by_a = {}
    attn_by_a = {}

    for q in A_list:
        at = torch.full((B,), q, dtype=torch.long)
        a_u = model.action_emb(at)
        a_u = a_u / a_u.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6)
        gamma, beta = model.act_film(a_u).chunk(2, dim=-1)
        hf = h_pre * (1.0 + torch.tanh(gamma)[:, None, :]) + beta[:, None, :]
        ha = cell.action_in(a_u) + cell.action_pos + mode + cemb
        h_all = torch.cat([hf, ha[:, None]], dim=1)
        enc = model.encode_action_ctx(a_u)
        mem = enc.memory
        age_now = mem["age0"][bidx] + rd.elapsed_s.float()[bidx][:, None]

        # Inspect block-0 self-attention weights manually (first 16 screens to keep super fast)
        blk0 = cell.blocks[0]
        h_sub = blk0.norm1(h_all[:16])
        nh = blk0.h
        hd = blk0.d // nh
        qa, ka, _ = blk0.qkv(h_sub).chunk(3, dim=-1)
        qa = qa.view(16, R + 1, nh, hd).transpose(1, 2)
        ka = ka.view(16, R + 1, nh, hd).transpose(1, 2)
        att_logits = (qa @ ka.transpose(-1, -2)) / np.sqrt(hd)
        att_p = torch.softmax(att_logits, dim=-1).mean((0, 1)).numpy()  # [65, 65]
        attn_by_a[q] = att_p

        h_out, _, counts, _ = cell._trunk(h_all, mem, bidx, st256.focus.reshape(-1), age_now, None, R)
        hn = cell.norm_f(h_out)[:, :R]
        raw_d = cell.out_proj(hn)
        dl = model.max_delta * torch.tanh(raw_d / model.max_delta)
        slow0, fast0 = x0_r[:, :ns], x0_r[:, ns:]
        ds, df = dl[:, :ns], dl[:, ns:]
        g_raw = torch.sigmoid(cell.gate(torch.cat([slow0, slow0 + ds], dim=-1)).squeeze(-1))
        g_slow = 0.15 + 0.85 * g_raw
        next_r = torch.cat([slow0 + g_slow[..., None] * ds, fast0 + df], dim=1)
        eff_delta = next_r - x0_r
        px_d = model.dec(next_r).numpy() - dec0_256

        h_film_arr.append(hf.numpy())
        hn_arr.append(hn.numpy())
        delta_arr.append(eff_delta.numpy())
        px_delta_arr.append(px_d)
        gslow_arr.append(g_slow.numpy())
        exp_counts_by_a[q] = counts.detach().cpu().numpy()

    def anova(T):
        T = np.asarray(T, dtype=np.float64).reshape(T.shape[0], T.shape[1], -1)
        mu = T.mean((0, 1), keepdims=True)
        u_s = T.mean(0, keepdims=True) - mu
        v_a = T.mean(1, keepdims=True) - mu
        w_sa = T - mu - u_s - v_a
        rms = lambda z: float(np.sqrt((z * z).mean()))
        st_v, sc_v, ad_v, bi_v = rms(mu), rms(u_s), rms(v_a), rms(w_sa)
        return st_v, sc_v, ad_v, bi_v, bi_v / max(ad_v, 1e-12)

    # Also compute ANOVA on shift_or_stay baseline px_delta on the SAME 256 screens x 5 actions!
    sos = S.fit_shift_or_stay_baseline(tr)
    sos_px_arr = []
    for q in A_list:
        ak_q = np.full((B, 1), q, dtype=np.int64)
        p_s = S.rollout_shift_or_stay(sos, he_fr[i256].astype(np.float64), ak_q)
        sos_px_arr.append(p_s - he_fr[i256].astype(np.float64))

    for nm, arr in [
        ("h_pre (before FiLM)", np.stack([h_pre.numpy()] * 5, 0)),
        ("h_after_film", np.stack(h_film_arr, 0)),
        ("hn_board (after trunk)", np.stack(hn_arr, 0)),
        ("eff_delta (all rows)", np.stack(delta_arr, 0)),
        ("eff_delta_SLOW", np.stack(delta_arr, 0)[:, :, :ns, :]),
        ("eff_delta_FAST", np.stack(delta_arr, 0)[:, :, ns:, :]),
        ("MODEL px_delta", np.stack(px_delta_arr, 0)),
        ("SOS_BASELINE px_delta", np.stack(sos_px_arr, 0)),
    ]:
        st_v, sc_v, ad_v, bi_v, r_v = anova(arr)
        print(f"  {nm:24s}: static={st_v:.4f} screen={sc_v:.5f} act_add={ad_v:.5f} bilinear={bi_v:.5f} (bi/add={r_v:.3f})")

    # Attention mixing diagnostics in block 0 during imagine
    a1_att = attn_by_a[1][:R, :]
    a2_att = attn_by_a[2][:R, :]
    diag_mass = float(np.mean(np.diag(a1_att[:, :R])))
    act_row_mass = float(np.mean(a1_att[:, R]))
    offdiag_row_mass = float(1.0 - diag_mass - act_row_mass)
    att_l1_lr = float(np.abs(a1_att - a2_att).sum(axis=1).mean())
    att_ent = float(-(a1_att * np.log(np.clip(a1_att, 1e-12, 1.0))).sum(axis=1).mean())
    print(f"\n  Block-0 imagine self-attn (avg over 64 board rows, 16 screens):")
    print(f"    self_diag={diag_mass:.4f}, to_action_row={act_row_mass:.4f}, cross_board_rows={offdiag_row_mass:.4f}, entropy={att_ent:.3f} (max={np.log(65):.3f})")
    print(f"    mean L1 attn shift (move_left vs move_right) = {att_l1_lr:.4f} (0=identical routing, 2=disjoint)")

    all_a = torch.arange(17, dtype=torch.long)
    ae = model.action_emb(all_a)
    ae_u = ae / ae.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6)
    g17, b17 = model.act_film(ae_u).chunk(2, dim=-1)
    tg17 = torch.tanh(g17)
    enc17 = model.encode_action_ctx(ae_u).memory["v"][0][:, 0, :]
    def mean_offdiag_cos(M):
        Mn = M / M.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        C = (Mn @ Mn.T).numpy()
        return float((C.sum() - len(C)) / (len(C) * (len(C) - 1)))
    print(f"  act_film: |W|={float(model.act_film.weight.norm()):.4f} |b|={float(model.act_film.bias.norm()):.4f} | tanh(g) rms={float(tg17.pow(2).mean().sqrt()):.4f} act_std={float(tg17.std(0).mean()):.4f} | beta rms={float(b17.pow(2).mean().sqrt()):.4f} act_std={float(b17.std(0).mean()):.4f}")
    print(f"  action_emb mean_cos={mean_offdiag_cos(ae_u):.4f} | enc_act mean_cos={mean_offdiag_cos(enc17):.4f}")
    gs_all = np.stack(gslow_arr, 0)
    print(f"  g_slow_imagine: mean={gs_all.mean():.4f} std={gs_all.std():.4f} min={gs_all.min():.4f} max={gs_all.max():.4f}")
    ec_tot = sum(exp_counts_by_a[q] for q in A_list)
    ec_frac = ec_tot / max(ec_tot.sum(), 1e-8)
    ec1n = exp_counts_by_a[1] / max(exp_counts_by_a[1].sum(), 1e-8)
    ec2n = exp_counts_by_a[2] / max(exp_counts_by_a[2].sum(), 1e-8)
    print(f"  MoE experts (imagine 0..4): active>=1%={int((ec_frac >= 0.01).sum())}/{len(ec_frac)} max={ec_frac.max():.3f} min={ec_frac.min():.3f} L1(L vs R)={float(np.abs(ec1n - ec2n).sum()):.4f}")

print("\n=== 4. GRADIENT MAGNITUDE & CONFLICT AUDIT (STEP 0 INIT vs STEP 3000 SAVED; 1 BATCH, ZERO UPDATES) ===")
j_g = np.random.default_rng(42).integers(0, len(xi1_tr), size=64)
i_g = xi1_tr[j_g]
tp_g = t1_tr[j_g]
h_g = np.where(tp_g > 0, i_g - 1, i_g)
xp_g = torch.from_numpy(tr_fr[h_g])
xt_g = torch.from_numpy(tr_fr[i_g])
xn_g = torch.from_numpy(tr_fr[i_g + 1])
act_g = torch.from_numpy(tr["actions"][ai1_tr[j_g]].astype(np.int64))

torch.manual_seed(42)
m_init = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=42).to(dev)

def grad_audit(m, label):
    m.train()
    st_t, _ = m.real_board(xp_g, xt_g)
    with torch.no_grad():
        tgt_rows = m.real_board(xt_g, xn_g)[0].rows
    x_rec_t = m.dec(st_t.rows[:, 0])
    c_w = ((xt_g - xp_g).abs().mean(-1, keepdim=True) > 0.02).float()
    l_rec = ((x_rec_t - xt_g) ** 2).mean() + 0.5 * ((((x_rec_t - xt_g) ** 2) * c_w).sum() / (c_w.sum() * 3.0 + 1e-6))
    st_det = dataclasses.replace(st_t, rows=st_t.rows.detach())
    out_img = m.imagine_step(st_det, act_g, wm_grad=True)
    x_img_abs = m.dec(out_img.next_rows[:, 0])
    x_img_res = xt_g + (x_img_abs - x_rec_t.detach())
    l_img_res = ((x_img_res - xn_g) ** 2).mean()
    l_img_abs = ((x_img_abs - xn_g) ** 2).mean()
    row_var = tgt_rows.var(dim=0, correction=0).mean().clamp_min(1e-3)
    l_row_rel = ((out_img.next_rows - tgt_rows) ** 2).mean() / row_var

    terms = {
        "1.0*l_rec": 1.0 * l_rec,
        "1.0*l_img_res": 1.0 * l_img_res,
        "0.25*l_img_abs": 0.25 * l_img_abs,
        "0.005*l_row_rel": 0.005 * l_row_rel,
    }
    trunk_p = [p for p in m.cell.parameters() if p.requires_grad]
    dec_p = [p for p in m.dec.parameters() if p.requires_grad]
    film_p = [p for p in m.act_film.parameters() if p.requires_grad]
    tg, dg = {}, {}
    print(f"\n[{label}]")
    for nm, term in terms.items():
        gt = torch.autograd.grad(term, trunk_p, retain_graph=True, allow_unused=True)
        gd = torch.autograd.grad(term, dec_p, retain_graph=True, allow_unused=True)
        gf = torch.autograd.grad(term, film_p, retain_graph=True, allow_unused=True)
        ft = torch.cat([(g.flatten() if g is not None else torch.zeros_like(p).flatten()) for g, p in zip(gt, trunk_p)])
        fd = torch.cat([(g.flatten() if g is not None else torch.zeros_like(p).flatten()) for g, p in zip(gd, dec_p)])
        ff = torch.cat([(g.flatten() if g is not None else torch.zeros_like(p).flatten()) for g, p in zip(gf, film_p)])
        tg[nm] = ft
        dg[nm] = fd
        print(f"  {nm:16s}: val={float(term):.6f} | |grad_cell|={float(ft.norm()):.5f} | |grad_dec|={float(fd.norm()):.5f} | |grad_film|={float(ff.norm()):.5f}")
    def gcos(a, b):
        return float((a @ b) / (a.norm() * b.norm() + 1e-12))
    c_ri = gcos(tg["1.0*l_rec"], tg["1.0*l_img_res"])
    c_ia = gcos(tg["1.0*l_img_res"], tg["0.25*l_img_abs"])
    c_rr = gcos(tg["1.0*l_img_res"], tg["0.005*l_row_rel"])
    cd_ri = gcos(dg["1.0*l_rec"], dg["1.0*l_img_res"])
    cd_ia = gcos(dg["1.0*l_img_res"], dg["0.25*l_img_abs"])
    print(f"  cos_cell(l_rec, l_img_res)={c_ri:.4f} | cos_cell(img_res, img_abs)={c_ia:.4f} | cos_cell(img_res, row_rel)={c_rr:.4f}")
    print(f"  cos_dec(l_rec, l_img_res)={cd_ri:.4f}  | cos_dec(img_res, img_abs)={cd_ia:.4f}")

grad_audit(m_init, "STEP_0_INIT")
grad_audit(model, "STEP_3000_SAVED")
print("\n=== DONE ===")
