"""PROBLEM-7 Rank 1 X-Ray (read-only CPU diagnostic on saved Step-2, Step-5, Step-6 weights).
Runs on M3 CPU only (nice -n 10, device=cpu, python -B). Zero training, zero MPS lock, zero M3 writes.
"""
import dataclasses
import json
import os
import sys
import time
import numpy as np
import torch

t_start = time.time()
torch.set_grad_enabled(False)
dev = "cpu"

import wm_fit as W
import sizes
from imagine_head6 import damped_imagine as damped_imagine6, add_head
from imagine_damped import damped_imagine as damped_imagine5, add_alpha
from premonition_core_v2.board_swarm import ThinkMode

SCALE = 0.20385979115962982
W.rms_level = lambda t: t / SCALE

tr = W.load_split("data/train.npz")
he = W.load_split("data/heldout.npz")

xi1_tr, ai1_tr, w1_tr, ep1_tr, t1_tr = W.windows(tr, 1)
xi1_he, ai1_he, w1_he, ep1_he, t1_he = W.windows(he, 1)
assert np.array_equal(tr["t_index"][xi1_tr], t1_tr), "train t_index mismatch"
assert np.array_equal(he["t_index"][xi1_he], t1_he), "heldout t_index mismatch"

def F(d, i):
    return torch.from_numpy(d["frames"][i].astype(np.float32)).to(dev)

def build_m6(ckpt_path):
    torch.manual_seed(42)
    m = W.WorldModel(sizes.make_cfg("P7toy")).to(dev)
    del m.head
    add_head(m.cell)
    ck = torch.load(ckpt_path, map_location=dev, weights_only=False)
    m.load_state_dict(ck["m"], strict=False)
    m.eval()
    return m

def build_m5(ckpt_path):
    torch.manual_seed(42)
    m = W.WorldModel(sizes.make_cfg("P7toy")).to(dev)
    del m.head
    add_alpha(m.cell)
    ck = torch.load(ckpt_path, map_location=dev, weights_only=False)
    m.load_state_dict(ck["m"], strict=False)
    m.eval()
    return m

m2 = build_m6("run_recon_ridge/model.pt")
m6 = build_m6("run_forecast4/model.pt")
m5r = build_m5("run_forecast3_refit/model.pt")

# Verify m2 and m6 trunk freeze identity
img_names = {
    "action_emb.weight",
    "cell.action_in.weight",
    "cell.action_in.bias",
    "cell.action_pos",
    "cell.imagine_out.0.weight",
    "cell.imagine_out.0.bias",
    "cell.imagine_out.2.weight",
    "cell.imagine_out.2.bias",
}
sd2, sd6 = m2.state_dict(), m6.state_dict()
max_trunk_diff = max(
    float((sd2[k] - sd6[k]).abs().max()) for k in sd2 if k not in img_names
)
print(f"[CHECK] m2 vs m6 shared trunk max diff = {max_trunk_diff:.3e}", flush=True)

def real_board_batch(m, d, i, tpos):
    h = np.where(tpos > 0, i - 1, i)
    st = m.read(m.cell.init_state(len(i), 1, device=dev, dtype=torch.float32), m.encode(F(d, h)))
    enc = m.encode(F(d, i))
    return m.read(st, enc)

def enc_act(m, act):
    B = act.shape[0]
    at = m.action_emb(act)
    at = (at / at.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6))[:, None]
    C = 1
    z = torch.zeros(B, C, device=dev)
    ctx = W.Context(
        tokens=at,
        mask=torch.ones(B, C, dtype=torch.bool, device=dev),
        support=torch.ones(B, C, device=dev),
        source=torch.full((B, C), int(W.Source.SIGHT), dtype=torch.long, device=dev),
        age_s=z,
        epoch=torch.zeros(B, dtype=torch.long, device=dev),
        q_hash=torch.zeros(B, dtype=torch.long, device=dev),
    )
    return m.cell.encode_context(ctx)

def trunk_hn_and_gate(m, st, act):
    """Run damped_imagine6 up through norm_f and gate, returning hn [B, R+1, d], delta [B, R, D], g_slow [B, ns], next_rows [B, 1, R, D]."""
    cell = m.cell
    enc = enc_act(m, act)
    action_embed = m.action_emb(act)
    rows = st.rows
    B, K, R, D = rows.shape
    N = B * K
    ns = cell.ns
    bidx = torch.arange(B, device=rows.device).repeat_interleave(K)
    x0 = rows.reshape(N, R, D)
    a = action_embed.reshape(B, 1, D).expand(B, K, D).reshape(N, D).to(x0.dtype)
    rd = cell._reading(None, B, rows.device)
    cemb = cell.clock_enc(rd)[bidx].to(x0.dtype)
    mode = cell.mode_emb.weight[int(ThinkMode.IMAGINE_NEXT_STATE)].to(x0.dtype)
    h = (
        cell.in_proj(x0)
        + cell.row_type_emb(cell.row_type)[None].to(x0.dtype)
        + cell.row_pos_emb[None].to(x0.dtype)
        + mode
        + cemb[:, None]
    )
    ha = cell.action_in(a) + cell.action_pos.to(x0.dtype) + mode + cemb
    h_all_in = torch.cat([h, ha[:, None]], dim=1)
    mem = enc.memory
    age_now = mem["age0"][bidx] + rd.elapsed_s.float()[bidx][:, None]
    focus = st.focus.reshape(-1).to(x0.dtype)
    h_all, aux_loss, counts, _ = cell._trunk(h_all_in, mem, bidx, focus, age_now, None, R)
    hn = cell.norm_f(h_all)
    delta = (cell.imagine_out(hn[:, :R]) * cell.imagine_scale).to(x0.dtype)
    gs = st.gate_scale.reshape(-1)
    pin = st.row_pin.reshape(N, R)
    slow0, fast0 = x0[:, :ns], x0[:, ns:]
    d_s, d_f = delta[:, :ns], delta[:, ns:]
    prop = slow0 + d_s
    g_slow = torch.sigmoid(cell.gate(torch.cat([slow0, prop], dim=-1)).squeeze(-1)) * gs[:, None].to(prop.dtype)
    g_slow = torch.where(pin[:, :ns], torch.zeros_like(g_slow), g_slow)
    slow = (slow0.float() + g_slow.float()[..., None] * d_s.float()).to(x0.dtype)
    fast = torch.where(pin[:, ns:][..., None], fast0, fast0 + d_f)
    next_rows = torch.cat([slow, fast], dim=1).view(B, K, R, D)
    return h_all_in, hn, delta, g_slow, next_rows

# Sanity-check trunk_hn_and_gate matches damped_imagine6 identically
_st_chk = m6.cell.init_state(4, 1, device=dev, dtype=torch.float32)
m6.cell.imagine_scale = torch.ones(m6.R, m6.D)
_act_chk = torch.tensor([0, 1, 2, 3], dtype=torch.long)
_o_ref = damped_imagine6(m6.cell, _st_chk, enc_act(m6, _act_chk), m6.action_emb(_act_chk))
_, _, _, _, _nr_chk = trunk_hn_and_gate(m6, _st_chk, _act_chk)
assert float((_o_ref.next_rows - _nr_chk).abs().max()) < 1e-6, "trunk_hn_and_gate mismatch vs damped_imagine6"
print("[CHECK] trunk_hn_and_gate matches damped_imagine6 (<1e-6)", flush=True)

def compute_all_boards(m, d, batch=128):
    n = len(d["frames"])
    idx = np.arange(n)
    tpos = d["t_index"]
    out = np.empty((n, m.R, m.D), dtype=np.float32)
    t0 = time.time()
    for b in range(0, n, batch):
        sl = slice(b, min(b + batch, n))
        st = real_board_batch(m, d, idx[sl], tpos[sl])
        out[sl] = st.rows[:, 0].numpy()
        if b == 0:
            # Verify state metadata is constant across samples
            f_val = st.focus
            gs_val = st.gate_scale
            pin_val = st.row_pin
            meta = (float(f_val.min()), float(f_val.max()), float(gs_val.min()), float(gs_val.max()), bool(pin_val.any()))
    dt = time.time() - t0
    print(f"[BOARDS] computed {n} frames in {dt:.1f}s ({dt/max(n/batch,1):.2f}s/batch), meta(focus_min/max, gs_min/max, any_pin)={meta}", flush=True)
    return out

def make_state(m, rows_np):
    B = len(rows_np)
    st = m.cell.init_state(B, 1, device=dev, dtype=torch.float32)
    return dataclasses.replace(st, rows=torch.from_numpy(rows_np).unsqueeze(1))

# Step 0: Compute held-out real boards (5,042 frames) first to gauge CPU speed
Z_he_all = compute_all_boards(m2, he, batch=128)
Z_he_t = Z_he_all[xi1_he]       # [5008, 64, 256]
Z_he_n = Z_he_all[xi1_he + 1]   # [5008, 64, 256]

# Step 0b: Fit exact Step-6 readout on train boards (exact forecast4.py:43-52)
NOISE = 0.2
rr = np.random.default_rng(11)
ji_ro = np.r_[rr.choice(np.flatnonzero(w1_tr < 140), 3500, replace=False),
              rr.choice(np.flatnonzero(w1_tr >= 140), 500, replace=False)]

# Compute ALL 20,175 train real boards once (used for readout + full per-action board ridge!)
Z_tr_all = compute_all_boards(m2, tr, batch=128)

def fit_exact_readout(Z_all_tr):
    Z = Z_all_tr[xi1_tr[ji_ro]].reshape(4000, -1).astype(np.float64)
    Y = tr["frames"][xi1_tr[ji_ro]].astype(np.float64).reshape(4000, -1)
    mu = Z[:3500].mean(0)
    sd = Z[:3500].std(0)
    sd = np.maximum(sd, 1e-3 + 0.1 * np.median(sd))
    A = (Z[:3500] - mu) / sd
    ym = Y[:3500].mean(0)
    n = 3500
    lam = n * NOISE ** 2
    al = np.linalg.solve(A @ A.T + lam * np.eye(n), Y[:3500] - ym)
    Wnp = (A.T @ al) / sd[:, None]
    e = float((((Z[3500:] - mu) @ Wnp + ym - Y[3500:]) ** 2).sum())
    vbase = float(((Y[3500:] - ym) ** 2).sum())
    bp_np = ym - mu @ Wnp
    return Wnp, bp_np, mu, sd, lam, e, vbase

Wnp6, bp6, mu6, sd6, lam6, val_sse6, val_base6 = fit_exact_readout(Z_tr_all)
print(f"[READOUT-6] lam={lam6} val_SSE={val_sse6:.2f} val_base={val_base6:.2f}", flush=True)
SD_t = torch.tensor(sd6, dtype=torch.float32).view(1, 1, m6.R, m6.D)
m2.cell.imagine_scale = SD_t[0, 0].clone()
m6.cell.imagine_scale = SD_t[0, 0].clone()

def RT6(rows_np):
    flat = rows_np.reshape(len(rows_np), -1).astype(np.float64)
    return (flat @ Wnp6 + bp6).reshape(-1, 16, 16, 3)

# ==============================================================================
# PART 1: BUTTON HEARING CHECK & BILINEAR ANOVA DECOMPOSITION
# ==============================================================================
print("\n=== PART 1: BUTTON HEARING CHECK ===", flush=True)
# Pick 16 windows per held-out world = 256 screens
rng_q1 = np.random.default_rng(123)
sel_q1 = np.concatenate([
    rng_q1.choice(np.flatnonzero(w1_he == w), 16, replace=False)
    for w in np.unique(w1_he)
])
Z_q1 = Z_he_t[sel_q1]  # [256, 64, 256]

# Real board burial stats (overall + slow vs fast + coordinate quantiles)
tr_flat = Z_tr_all[xi1_tr[ji_ro[:3500]]].astype(np.float64)
he_flat = Z_he_t.astype(np.float64)
tr_coord_std = tr_flat.std(0)
he_coord_std = he_flat.std(0)
board_burial = {
    "train_static_rms": float(np.sqrt(np.mean(tr_flat.mean(0) ** 2))),
    "train_spread_rms": float(np.sqrt(np.mean(tr_flat.var(0)))),
    "train_slow_spread_rms": float(np.sqrt(np.mean(tr_flat[:, :m2.cell.ns].var(0)))),
    "train_fast_spread_rms": float(np.sqrt(np.mean(tr_flat[:, m2.cell.ns:].var(0)))),
    "train_coord_std_median_p95_max": [float(np.median(tr_coord_std)), float(np.percentile(tr_coord_std, 95)), float(tr_coord_std.max())],
    "train_burial_ratio": float(np.sqrt(np.mean(tr_flat.mean(0) ** 2)) / np.sqrt(np.mean(tr_flat.var(0)))),
    "heldout_static_rms": float(np.sqrt(np.mean(he_flat.mean(0) ** 2))),
    "heldout_spread_rms": float(np.sqrt(np.mean(he_flat.var(0)))),
    "heldout_burial_ratio": float(np.sqrt(np.mean(he_flat.mean(0) ** 2)) / np.sqrt(np.mean(he_flat.var(0)))),
}
print("[BURIAL]", json.dumps(board_burial), flush=True)

from premonition_core_v2.board_swarm import age_features

def analyze_model_hearing(m, name):
    # 1. enc_act embedding e (board_swarm.py:319-321) AND block-0 cross-attn V cosine similarity across all 17 actions
    all_a = torch.arange(17, dtype=torch.long)
    at = m.action_emb(all_a)
    at = (at / at.pow(2).mean(-1, keepdim=True).sqrt().clamp_min(1e-6))[:, None]
    zoom = torch.cat([torch.tanh(s * at) for s in m.cell.cfg.zoom_scales], dim=-1)
    src = torch.full((17, 1), int(W.Source.SIGHT), dtype=torch.long)
    age_z = torch.zeros(17, 1)
    e_ctx = (m.cell.zoom(zoom) + m.cell.src_emb(src) + m.cell.age_lin(age_features(age_z, m.cell.cfg.n_age_feats).to(at.dtype)))[:, 0].numpy().astype(np.float64)
    ea_n = e_ctx / np.linalg.norm(e_ctx, axis=-1, keepdims=True)
    off = (ea_n @ ea_n.T)[~np.eye(17, dtype=bool)]
    v0 = enc_act(m, all_a).memory["v"][0].reshape(17, -1).numpy().astype(np.float64)
    v0_n = v0 / np.linalg.norm(v0, axis=-1, keepdims=True)
    v0_off = (v0_n @ v0_n.T)[~np.eye(17, dtype=bool)]
    act_emb = m.action_emb.weight.numpy().astype(np.float64)
    ae_n = act_emb / np.linalg.norm(act_emb, axis=-1, keepdims=True)
    ae_off = (ae_n @ ae_n.T)[~np.eye(17, dtype=bool)]

    # 2. Run trunk for all 256 screens x 17 actions
    N = len(Z_q1)
    hn_all = np.empty((N, 17, m.R + 1, m.cell.d), dtype=np.float32)
    hin_all = np.empty((N, 17, m.R + 1, m.cell.d), dtype=np.float32)
    del_all = np.empty((N, 17, m.R, m.D), dtype=np.float32)
    gslow_all = np.empty((N, 17, m.cell.ns), dtype=np.float32)
    st_q1 = make_state(m, Z_q1)
    for a in range(17):
        act_t = torch.full((N,), a, dtype=torch.long)
        hin, hn, delta, g_slow, _ = trunk_hn_and_gate(m, st_q1, act_t)
        hin_all[:, a] = hin.numpy()
        hn_all[:, a] = hn.numpy()
        del_all[:, a] = delta.numpy()
        gslow_all[:, a] = g_slow.numpy()

    def anova_stats(arr):
        # arr: [S, A, ...]
        arr = arr.astype(np.float64)
        mu = arr.mean(axis=(0, 1), keepdims=True)
        u_s = arr.mean(axis=1, keepdims=True) - mu
        v_a = arr.mean(axis=0, keepdims=True) - mu
        w_inter = arr - mu - u_s - v_a
        static_rms = float(np.sqrt(np.mean(mu ** 2)))
        screen_rms = float(np.sqrt(np.mean(u_s ** 2)))
        act_add_rms = float(np.sqrt(np.mean(v_a ** 2)))
        inter_rms = float(np.sqrt(np.mean(w_inter ** 2)))
        # Total cross-action std (additive + interaction) holding screen fixed
        act_total_rms = float(np.sqrt(np.mean((arr - arr.mean(axis=1, keepdims=True)) ** 2)))
        return {
            "static_rms": static_rms,
            "screen_rms": screen_rms,
            "act_total_rms": act_total_rms,
            "act_additive_rms": act_add_rms,
            "act_screen_bilinear_rms": inter_rms,
            "ratio_act_to_screen": act_total_rms / max(screen_rms, 1e-12),
            "ratio_bilinear_to_screen": inter_rms / max(screen_rms, 1e-12),
            "ratio_bilinear_to_act_total": inter_rms / max(act_total_rms, 1e-12),
        }

    out = {
        "enc_act_cos_mean": float(off.mean()),
        "enc_act_cos_min": float(off.min()),
        "enc_act_cos_max": float(off.max()),
        "enc_act_v0_cos_mean": float(v0_off.mean()),
        "action_emb_cos_mean": float(ae_off.mean()),
        "h_in_board_all17": anova_stats(hin_all[:, :, :m.R]),
        "h_in_action_all17": anova_stats(hin_all[:, :, m.R]),
        "hn_board_all17": anova_stats(hn_all[:, :, :m.R]),
        "hn_board_moves5": anova_stats(hn_all[:, :5, :m.R]),
        "hn_slow_all17": anova_stats(hn_all[:, :, :m.cell.ns]),
        "hn_fast_all17": anova_stats(hn_all[:, :, m.cell.ns:m.R]),
        "hn_action_row_all17": anova_stats(hn_all[:, :, m.R]),
        "delta_all17": anova_stats(del_all),
        "delta_moves5": anova_stats(del_all[:, :5]),
        "delta_in_SD_moves5": anova_stats(del_all[:, :5] / sd6.reshape(1, 1, m.R, m.D)),
        "g_slow_imagine": {
            "mean": float(gslow_all.mean()),
            "std": float(gslow_all.std()),
            "min": float(gslow_all.min()),
            "p10": float(np.percentile(gslow_all, 10)),
            "median": float(np.median(gslow_all)),
            "p90": float(np.percentile(gslow_all, 90)),
            "max": float(gslow_all.max()),
        },
    }
    print(f"[HEARING {name}]", json.dumps(out, indent=1), flush=True)
    return out

hear_m2 = analyze_model_hearing(m2, "step2_init")
hear_m6 = analyze_model_hearing(m6, "step6_trained")

# ==============================================================================
# PART 2: NOTEPAD CAPACITY & FROZEN-TRUNK HIDDEN-STATE RIDGE CHECKS
# ==============================================================================
print("\n=== PART 2: RIDGE PROBES ===", flush=True)

hfr = he["frames"].astype(np.float64)
x0_he = hfr[xi1_he]
y1_he = hfr[xi1_he + 1]
acts_he_1 = he["actions"][ai1_he]
mean_tr = tr["frames"][xi1_tr].astype(np.float64).mean(0)
xs_tr1 = tr["frames"][xi1_tr].astype(np.float64)
ys_tr1 = tr["frames"][xi1_tr + 1].astype(np.float64)
dd_tr1 = xs_tr1 - mean_tr
bl1 = float(((ys_tr1 - mean_tr) * dd_tr1).sum() / (dd_tr1 * dd_tr1).sum())
cp1_he = float(((x0_he - y1_he) ** 2).sum())
bs1_he = float(((mean_tr + bl1 * (x0_he - mean_tr) - y1_he) ** 2).sum())
B1_he = min(cp1_he, bs1_he)
print(f"[BASELINES] B1={B1_he:.2f} (copy={cp1_he:.2f}, blend={bs1_he:.2f}, bl1={bl1:.6f})", flush=True)

# Sanity check: exact pixel M_a [x_t, 1] linear baseline
Xa_tr = xs_tr1.reshape(len(xi1_tr), -1)
Ya_tr = ys_tr1.reshape(len(xi1_tr), -1)
aa_tr = tr["actions"][ai1_tr]
Mact = {}
for q in range(17):
    sel = aa_tr == q
    Xq = np.c_[Xa_tr[sel], np.ones(sel.sum())]
    Mact[q] = np.linalg.solve(Xq.T @ Xq + 1.0 * np.eye(769), Xq.T @ Ya_tr[sel])
P_pix_lin = np.empty((len(xi1_he), 768), dtype=np.float64)
Xhe_flat = x0_he.reshape(len(xi1_he), -1)
for q in range(17):
    sel = acts_he_1 == q
    if sel.any():
        P_pix_lin[sel] = np.c_[Xhe_flat[sel], np.ones(sel.sum())] @ Mact[q]
P_pix_lin = P_pix_lin.reshape(-1, 16, 16, 3)
E_pix_lin = float(((P_pix_lin - y1_he) ** 2).sum())
print(f"[PIXEL LINEAR BASELINE] k1 E/B = {E_pix_lin / B1_he:.6f}", flush=True)

# Helper: exact dual kernel ridge using single eigendecomposition (mathematically identical to solve)
def dual_ridge_sweep(Xf, Yf, Xv, Yv, Xh, lams=(1e-1, 1.0, 10.0, 100.0, 1000.0)):
    mu = Xf.mean(0)
    sd = Xf.std(0)
    sd = np.maximum(sd, 1e-3 + 0.1 * np.median(sd))
    Af = (Xf - mu) / sd
    Av = (Xv - mu) / sd
    Ah = (Xh - mu) / sd
    ym = Yf.mean(0)
    Kf = Af @ Af.T
    ev, Q = np.linalg.eigh(Kf)
    ev = np.maximum(ev, 0.0)
    QtY = Q.T @ (Yf - ym)
    KvQ = (Av @ Af.T) @ Q
    KhQ = (Ah @ Af.T) @ Q
    best = None
    for lam in lams:
        w = QtY / (ev[:, None] + lam)
        pv = KvQ @ w + ym
        e = float(((pv - Yv) ** 2).sum())
        if best is None or e < best[0]:
            best = (e, lam, w)
    e, lam, w = best
    ph = KhQ @ w + ym
    return ph, lam, e

# Split train windows strictly by world_id (<140 fit, >=140 val)
fit_mask = w1_tr < 140
val_mask = w1_tr >= 140
Z_tr_t_flat = Z_tr_all[xi1_tr].reshape(len(xi1_tr), -1).astype(np.float64)
Z_tr_n_flat = Z_tr_all[xi1_tr + 1].reshape(len(xi1_tr), -1).astype(np.float64)
Z_he_t_flat = Z_he_t.reshape(len(xi1_he), -1).astype(np.float64)
Z_he_n_flat = Z_he_n.reshape(len(xi1_he), -1).astype(np.float64)

# 2A: Per-action closed-form ridge on saved Step-2 real_board(t) -> x_{t+1} (all 17 actions)
# 2B: Per-action board-to-board ridge -> RT6 (exact linear projection via eigh; 20x faster, mathematically identical)
P_2a_abs = np.empty((len(xi1_he), 768), dtype=np.float64)
P_2a_del = np.empty((len(xi1_he), 768), dtype=np.float64)
P_2b_rt_del = np.empty((len(xi1_he), 768), dtype=np.float64)
lams_2a_abs, lams_2a_del, lams_2b = {}, {}, {}

mu_g = Z_tr_t_flat[fit_mask].mean(0)
sd_g = Z_tr_t_flat[fit_mask].std(0)
sd_g = np.maximum(sd_g, 1e-3 + 0.1 * np.median(sd_g))
A_tr_all = (Z_tr_t_flat - mu_g) / sd_g
A_he_all = (Z_he_t_flat - mu_g) / sd_g

t_2a = time.time()
Y_tr_del = Ya_tr - Xa_tr
# Exact RT6 pixel-space image of true board delta: (Z_{t+1} - Z_t) @ Wnp6 = RT6(Z_{t+1}) - RT6(Z_t)
RT6_tr_t_flat = RT6(Z_tr_all[xi1_tr]).reshape(len(xi1_tr), -1)
RT6_tr_n_flat = RT6(Z_tr_all[xi1_tr + 1]).reshape(len(xi1_tr), -1)
dRT6_tr = RT6_tr_n_flat - RT6_tr_t_flat
RT6_he_t = RT6(Z_he_t)
RT6_he_n = RT6(Z_he_n)
RT6_he_t_flat = RT6_he_t.reshape(len(xi1_he), -1)

# Accumulate exact board-space R^2 of 2B at winning lam per action
num_2b_board_sq = 0.0
den_2b_board_sq = 0.0

for q in range(17):
    f_idx = np.flatnonzero(fit_mask & (aa_tr == q))
    v_idx = np.flatnonzero(val_mask & (aa_tr == q))
    h_idx = np.flatnonzero(acts_he_1 == q)
    if len(h_idx) == 0:
        continue
    Af = A_tr_all[f_idx]
    Ah = A_he_all[h_idx]
    Kf = Af @ Af.T
    ev_k, Q = np.linalg.eigh(Kf)
    ev_k = np.maximum(ev_k, 0.0)
    KhQ = (Ah @ Af.T) @ Q
    has_val = len(v_idx) >= 5
    KvQ = ((A_tr_all[v_idx] @ Af.T) @ Q) if has_val else None

    # 2A-abs: Z_t -> x_{t+1}
    Yf = Ya_tr[f_idx]; ym = Yf.mean(0); QtY = Q.T @ (Yf - ym)
    best = None
    for lam in (1.0, 10.0, 100.0, 1000.0, 10000.0):
        w = QtY / (ev_k[:, None] + lam)
        e = float(((KvQ @ w + ym - Ya_tr[v_idx]) ** 2).sum()) if has_val else (0.0 if lam == 100.0 else 1e30)
        if best is None or e < best[0]:
            best = (e, lam, w)
    lams_2a_abs[q] = best[1]
    P_2a_abs[h_idx] = KhQ @ best[2] + ym

    # 2A-del: Z_t -> (x_{t+1} - x_t)
    Yf_d = Y_tr_del[f_idx]; ym_d = Yf_d.mean(0); QtY_d = Q.T @ (Yf_d - ym_d)
    best_d = None
    for lam in (1.0, 10.0, 100.0, 1000.0, 10000.0):
        w = QtY_d / (ev_k[:, None] + lam)
        e = float(((KvQ @ w + ym_d - Y_tr_del[v_idx]) ** 2).sum()) if has_val else (0.0 if lam == 100.0 else 1e30)
        if best_d is None or e < best_d[0]:
            best_d = (e, lam, w)
    lams_2a_del[q] = best_d[1]
    P_2a_del[h_idx] = Xhe_flat[h_idx] + (KhQ @ best_d[2] + ym_d)

    # 2B: Z_t -> (Z_{t+1} - Z_t) -> RT6 (commutes exactly with right-multiplication by Wnp6!)
    Yf_r = dRT6_tr[f_idx]; ym_r = Yf_r.mean(0); QtY_r = Q.T @ (Yf_r - ym_r)
    best_b = None
    for lam in (10.0, 100.0, 1000.0, 10000.0):
        w = QtY_r / (ev_k[:, None] + lam)
        if has_val:
            pred_img_v = RT6_tr_t_flat[v_idx] + (KvQ @ w + ym_r)
            e = float(((pred_img_v - Ya_tr[v_idx]) ** 2).sum())
        else:
            e = 0.0 if lam == 1000.0 else 1e30
        if best_b is None or e < best_b[0]:
            best_b = (e, lam, w)
    lam_b = best_b[1]
    lams_2b[q] = lam_b
    P_2b_rt_del[h_idx] = KhQ @ best_b[2] + ym_r

    # Board-space R^2 at winning lam_b (only 1 pass, no 4x sweep!)
    dZf_std = (Z_tr_n_flat[f_idx] - Z_tr_t_flat[f_idx]) / sd_g
    ym_bz = dZf_std.mean(0)
    w_bz = (Q.T @ (dZf_std - ym_bz)) / (ev_k[:, None] + lam_b)
    pred_dz_h = KhQ @ w_bz + ym_bz
    true_dz_h = (Z_he_n_flat[h_idx] - Z_he_t_flat[h_idx]) / sd_g
    num_2b_board_sq += float(((pred_dz_h - true_dz_h) ** 2).sum())
    den_2b_board_sq += float((true_dz_h ** 2).sum())

P_2a_abs_img = P_2a_abs.reshape(-1, 16, 16, 3)
P_2a_del_img = P_2a_del.reshape(-1, 16, 16, 3)
P_2b_abs_img = (RT6_he_t_flat + P_2b_rt_del).reshape(-1, 16, 16, 3)
P_2b_res_img = x0_he + P_2b_rt_del.reshape(-1, 16, 16, 3)

E_2a_abs = float(((P_2a_abs_img - y1_he) ** 2).sum()) / B1_he
E_2a_del = float(((P_2a_del_img - y1_he) ** 2).sum()) / B1_he
E_2b_abs = float(((P_2b_abs_img - y1_he) ** 2).sum()) / B1_he
E_2b_res = float(((P_2b_res_img - y1_he) ** 2).sum()) / B1_he
r2_2b_board = float(1.0 - num_2b_board_sq / max(den_2b_board_sq, 1e-12))
print(f"[PROBE 2A/2B] ({time.time()-t_2a:.1f}s) Step2 board per-action ridge:", flush=True)
print(f"  2A-abs (board_t -> x_{{t+1}})          E1/B1 = {E_2a_abs:.4f}", flush=True)
print(f"  2A-del (x_t + board_t -> dx)          E1/B1 = {E_2a_del:.4f}", flush=True)
print(f"  2B-abs (board_t -> board_{{t+1}} -> RT) E1/B1 = {E_2b_abs:.4f}", flush=True)
print(f"  2B-res (x_t + RT(b_hat) - RT(b_t))    E1/B1 = {E_2b_res:.4f}, board-delta R^2 = {r2_2b_board:.4f}", flush=True)

# 2C/2D/2E: Frozen-trunk hidden state hn[:, :R] probes (on BOTH Step-6 trained and Step-2 init!)
# Sample 5,000 fit (w1<140) + 1,000 val (w1>=140) from train, and ALL 5,008 held-out!
rng_hn = np.random.default_rng(77)
idx_hn_fit = rng_hn.choice(np.flatnonzero(fit_mask), 5000, replace=False)
idx_hn_val = rng_hn.choice(np.flatnonzero(val_mask), 1000, replace=False)

def compute_hn_set(m, Z_t_arr, acts_arr, batch=128):
    n = len(Z_t_arr)
    hn_out = np.empty((n, m.R + 1, m.cell.d), dtype=np.float32)
    nxt_out = np.empty((n, m.R, m.D), dtype=np.float32)
    gs_out = np.empty((n, m.cell.ns), dtype=np.float32)
    for b in range(0, n, batch):
        sl = slice(b, min(b + batch, n))
        st = make_state(m, Z_t_arr[sl])
        act_t = torch.from_numpy(acts_arr[sl].astype(np.int64))
        _, hn, _, g_slow, nxt = trunk_hn_and_gate(m, st, act_t)
        hn_out[sl] = hn.numpy()
        nxt_out[sl] = nxt[:, 0].numpy()
        gs_out[sl] = g_slow.numpy()
    return hn_out, nxt_out, gs_out

def run_hn_probes(m, tag):
    t0 = time.time()
    hn_f, _, _ = compute_hn_set(m, Z_tr_all[xi1_tr[idx_hn_fit]], aa_tr[idx_hn_fit])
    hn_v, _, _ = compute_hn_set(m, Z_tr_all[xi1_tr[idx_hn_val]], aa_tr[idx_hn_val])
    hn_h, nxt_h, gs_h = compute_hn_set(m, Z_he_t, acts_he_1)
    dt = time.time() - t0
    print(f"[HN {tag}] computed 5000+1000+5008 hn in {dt:.1f}s", flush=True)

    # Flatten hn[:, :R] -> [N, 16384] and hn[:, :R+1] -> [N, 16640]
    Xf = hn_f[:, :m.R].reshape(len(hn_f), -1).astype(np.float64)
    Xv = hn_v[:, :m.R].reshape(len(hn_v), -1).astype(np.float64)
    Xh = hn_h[:, :m.R].reshape(len(hn_h), -1).astype(np.float64)
    Yf = Ya_tr[idx_hn_fit]
    Yv = Ya_tr[idx_hn_val]
    Yf_d = Y_tr_del[idx_hn_fit]
    Yv_d = Y_tr_del[idx_hn_val]

    # (3) Shared linear ridge: hn[:, :R] -> x_{t+1} (abs) and -> dx (res)
    ph_sh_abs, lam_sh_abs, _ = dual_ridge_sweep(Xf, Yf, Xv, Yv, Xh, lams=(10.0, 100.0, 1000.0, 10000.0))
    ph_sh_del, lam_sh_del, _ = dual_ridge_sweep(Xf, Yf_d, Xv, Yv_d, Xh, lams=(10.0, 100.0, 1000.0, 10000.0))
    e_sh_abs = float(((ph_sh_abs.reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he
    e_sh_del = float((((Xhe_flat + ph_sh_del).reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he

    # Also test shared linear ridge with action row INCLUDED (hn[:, :R+1])
    Xf_a = hn_f.reshape(len(hn_f), -1).astype(np.float64)
    Xv_a = hn_v.reshape(len(hn_v), -1).astype(np.float64)
    Xh_a = hn_h.reshape(len(hn_h), -1).astype(np.float64)
    ph_sha_abs, lam_sha_abs, _ = dual_ridge_sweep(Xf_a, Yf, Xv_a, Yv, Xh_a, lams=(10.0, 100.0, 1000.0, 10000.0))
    ph_sha_del, lam_sha_del, _ = dual_ridge_sweep(Xf_a, Yf_d, Xv_a, Yv_d, Xh_a, lams=(10.0, 100.0, 1000.0, 10000.0))
    e_sha_abs = float(((ph_sha_abs.reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he
    e_sha_del = float((((Xhe_flat + ph_sha_del).reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he

    # (4) Row-independent linear ridge: hn[:, r] (256) -> delta_board[:, r] (256) per row r=0..63, then RT6!
    dB_f = (Z_tr_all[xi1_tr[idx_hn_fit] + 1] - Z_tr_all[xi1_tr[idx_hn_fit]]).astype(np.float64)
    dB_v = (Z_tr_all[xi1_tr[idx_hn_val] + 1] - Z_tr_all[xi1_tr[idx_hn_val]]).astype(np.float64)
    pred_dB_h = np.empty_like(Z_he_t, dtype=np.float64)
    pred_dB_h_with_act = np.empty_like(Z_he_t, dtype=np.float64)
    row_lams = []
    for r in range(m.R):
        # Row-only (exact linear upper bound of Step 6 imagine_out on l_row)
        Xr_f = np.c_[hn_f[:, r].astype(np.float64), np.ones(len(hn_f))]
        Xr_v = np.c_[hn_v[:, r].astype(np.float64), np.ones(len(hn_v))]
        Xr_h = np.c_[hn_h[:, r].astype(np.float64), np.ones(len(hn_h))]
        XtX = Xr_f.T @ Xr_f
        XtY = Xr_f.T @ dB_f[:, r]
        I_r = np.eye(Xr_f.shape[1]); I_r[-1, -1] = 0.0
        best_r = None
        for lam in (1.0, 10.0, 100.0, 1000.0):
            Wr = np.linalg.solve(XtX + lam * I_r, XtY)
            ev = float(((Xr_v @ Wr - dB_v[:, r]) ** 2).sum())
            if best_r is None or ev < best_r[0]:
                best_r = (ev, lam, Wr)
        row_lams.append(best_r[1])
        pred_dB_h[:, r] = Xr_h @ best_r[2]

        # Row + action row [hn[:, r], hn[:, R]]
        Xra_f = np.c_[hn_f[:, r].astype(np.float64), hn_f[:, m.R].astype(np.float64), np.ones(len(hn_f))]
        Xra_v = np.c_[hn_v[:, r].astype(np.float64), hn_v[:, m.R].astype(np.float64), np.ones(len(hn_v))]
        Xra_h = np.c_[hn_h[:, r].astype(np.float64), hn_h[:, m.R].astype(np.float64), np.ones(len(hn_h))]
        XtXa = Xra_f.T @ Xra_f
        XtYa = Xra_f.T @ dB_f[:, r]
        I_ra = np.eye(Xra_f.shape[1]); I_ra[-1, -1] = 0.0
        best_ra = None
        for lam in (1.0, 10.0, 100.0, 1000.0):
            Wra = np.linalg.solve(XtXa + lam * I_ra, XtYa)
            ev = float(((Xra_v @ Wra - dB_v[:, r]) ** 2).sum())
            if best_ra is None or ev < best_ra[0]:
                best_ra = (ev, lam, Wra)
        pred_dB_h_with_act[:, r] = Xra_h @ best_ra[2]

    P_row_abs = RT6(Z_he_t + pred_dB_h)
    P_row_res = x0_he + (P_row_abs - RT6_he_t)
    e_row_abs = float(((P_row_abs - y1_he) ** 2).sum()) / B1_he
    e_row_res = float(((P_row_res - y1_he) ** 2).sum()) / B1_he
    # Board-space R^2 of row-independent hn[:, r] -> dB[:, r] BEFORE RT6 (Astra Rung-0 check)
    dB_he_true = (Z_he_n - Z_he_t).astype(np.float64)
    sd_r = sd6.reshape(1, m.R, m.D)
    r2_row_board_std = float(1.0 - (((pred_dB_h - dB_he_true) / sd_r) ** 2).sum() / (((dB_he_true) / sd_r) ** 2).sum())
    r2_rowa_board_std = float(1.0 - (((pred_dB_h_with_act - dB_he_true) / sd_r) ** 2).sum() / (((dB_he_true) / sd_r) ** 2).sum())

    # Single-row pixel probes: best / median / worst individual row hn[:, r] -> dx
    single_row_e_del = []
    for r in range(m.R):
        Xr_f = np.c_[hn_f[:, r].astype(np.float64), np.ones(len(hn_f))]
        Xr_v = np.c_[hn_v[:, r].astype(np.float64), np.ones(len(hn_v))]
        Xr_h = np.c_[hn_h[:, r].astype(np.float64), np.ones(len(hn_h))]
        XtX = Xr_f.T @ Xr_f; XtY = Xr_f.T @ Yf_d; I_r = np.eye(Xr_f.shape[1]); I_r[-1, -1] = 0.0
        Wr = np.linalg.solve(XtX + 100.0 * I_r, XtY)
        pr = Xhe_flat + Xr_h @ Wr
        single_row_e_del.append(float(((pr.reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he)

    P_rowa_abs = RT6(Z_he_t + pred_dB_h_with_act)
    P_rowa_res = x0_he + (P_rowa_abs - RT6_he_t)
    e_rowa_abs = float(((P_rowa_abs - y1_he) ** 2).sum()) / B1_he
    e_rowa_res = float(((P_rowa_res - y1_he) ** 2).sum()) / B1_he

    # (5) Per-action linear ridge on hn[:, :R] -> x_{t+1} (on the 5000+1000 sample)
    mu_hn = Xf.mean(0)
    sd_hn = np.maximum(Xf.std(0), 1e-3 + 0.1 * np.median(Xf.std(0)))
    Af_hn = (Xf - mu_hn) / sd_hn
    Av_hn = (Xv - mu_hn) / sd_hn
    Ah_hn = (Xh - mu_hn) / sd_hn
    aa_f = aa_tr[idx_hn_fit]
    aa_v = aa_tr[idx_hn_val]
    P_hn_pa_abs = np.empty((len(xi1_he), 768), dtype=np.float64)
    P_hn_pa_del = np.empty((len(xi1_he), 768), dtype=np.float64)
    for q in range(17):
        fi = np.flatnonzero(aa_f == q)
        vi = np.flatnonzero(aa_v == q)
        hi = np.flatnonzero(acts_he_1 == q)
        if len(hi) == 0:
            continue
        if len(fi) < 3:
            P_hn_pa_abs[hi] = Xhe_flat[hi]
            P_hn_pa_del[hi] = Xhe_flat[hi]
            continue
        Kf = Af_hn[fi] @ Af_hn[fi].T
        Kh = Ah_hn[hi] @ Af_hn[fi].T
        I = np.eye(len(fi))
        has_v = len(vi) >= 3
        Kv = (Av_hn[vi] @ Af_hn[fi].T) if has_v else None
        for mode_idx, (Y_src_f, Y_src_v, out_arr, add_x0) in enumerate([
            (Yf[fi], Yv[vi] if has_v else None, P_hn_pa_abs, False),
            (Yf_d[fi], Yv_d[vi] if has_v else None, P_hn_pa_del, True),
        ]):
            ym = Y_src_f.mean(0)
            best = None
            for lam in (10.0, 100.0, 1000.0, 10000.0):
                al = np.linalg.solve(Kf + lam * I, Y_src_f - ym)
                ev = float(((Kv @ al + ym - Y_src_v) ** 2).sum()) if has_v else (0.0 if lam == 100.0 else 1e30)
                if best is None or ev < best[0]:
                    best = (ev, lam, al)
            pred = Kh @ best[2] + ym
            out_arr[hi] = (Xhe_flat[hi] + pred) if add_x0 else pred
    e_pa_abs = float(((P_hn_pa_abs.reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he
    e_pa_del = float(((P_hn_pa_del.reshape(-1, 16, 16, 3) - y1_he) ** 2).sum()) / B1_he

    res = {
        "shared_hn_board_to_xnext_abs_E1_B1": e_sh_abs,
        "shared_hn_board_to_xnext_abs_lam": lam_sh_abs,
        "shared_hn_board_to_dx_res_E1_B1": e_sh_del,
        "shared_hn_board_to_dx_res_lam": lam_sh_del,
        "shared_hn_plus_act_to_xnext_abs_E1_B1": e_sha_abs,
        "shared_hn_plus_act_to_dx_res_E1_B1": e_sha_del,
        "row_independent_hn_to_dboard_abs_E1_B1": e_row_abs,
        "row_independent_hn_to_dboard_res_E1_B1": e_row_res,
        "row_independent_hn_to_dboard_board_R2": r2_row_board_std,
        "row_plus_actrow_to_dboard_abs_E1_B1": e_rowa_abs,
        "row_plus_actrow_to_dboard_res_E1_B1": e_rowa_res,
        "row_plus_actrow_to_dboard_board_R2": r2_rowa_board_std,
        "single_row_hn_to_dx_best_E1_B1": float(min(single_row_e_del)),
        "single_row_hn_to_dx_median_E1_B1": float(np.median(single_row_e_del)),
        "per_action_hn_board_to_xnext_abs_E1_B1": e_pa_abs,
        "per_action_hn_board_to_dx_res_E1_B1": e_pa_del,
    }
    print(f"[HN PROBES {tag}]", json.dumps(res, indent=1), flush=True)
    return res, nxt_h, gs_h

hn_res_m6, nxt_he_m6, gs_he_m6 = run_hn_probes(m6, "step6_trained")
hn_res_m2, _, _ = run_hn_probes(m2, "step2_init")

# ==============================================================================
# PART 3: RULER TRAP CHECK (ORACLE, STEP 5 REFIT, STEP 6) + DAY/NIGHT SPLIT
# ==============================================================================
print("\n=== PART 3: RULER TRAP CHECK & DAY/NIGHT SPLIT ===", flush=True)

def eval_ruler_metrics(P_img, x0, y1, acts0, label):
    E = float(((P_img - y1) ** 2).sum())
    e_over_b = E / B1_he
    dP = (P_img - x0).reshape(len(P_img), -1)
    dY = (y1 - x0).reshape(len(y1), -1)
    copy_ness = float((dP ** 2).sum() / max((dY ** 2).sum(), 1e-12))
    pcs_p = int(W.pcs90(dP))
    pcs_r = int(W.pcs90(dY))
    ratios_by_a = {}
    for q in range(17):
        sel = acts0 == q
        cnt = int(sel.sum())
        if cnt >= 20:
            sp = float(dP[sel].std())
            sr = float(dY[sel].std())
            r = 1.0 if (sr < 1e-12 and sp < 1e-12) else float(sp / (sr + 1e-12))
            ratios_by_a[str(q)] = {"n": cnt, "std_pred": sp, "std_real": sr, "ratio": r}
    all_ratios = [v["ratio"] for v in ratios_by_a.values()]
    move_ratios = [ratios_by_a[str(q)]["ratio"] for q in (1, 2, 3, 4) if str(q) in ratios_by_a]
    # Frequency-weighted average std ratio & active-action (>=0.02 real std) ratios
    tot_n = sum(v["n"] for v in ratios_by_a.values())
    w_mean_ratio = float(sum(v["n"] * v["ratio"] for v in ratios_by_a.values()) / tot_n)
    active_ratios = {k: v["ratio"] for k, v in ratios_by_a.items() if v["std_real"] >= 0.02}
    okstd_old = all(0.25 <= r <= 2.0 for r in all_ratios)
    okstd_active = all(0.25 <= r <= 2.0 for r in active_ratios.values())
    okpc = pcs_p >= 0.5 * pcs_r
    out = {
        "label": label,
        "E1_over_B1": e_over_b,
        "copy_ness": copy_ness,
        "pcs90_pred": pcs_p,
        "pcs90_real": pcs_r,
        "pcs_ok": okpc,
        "okstd_old_all_n20": okstd_old,
        "okstd_active_ge002": okstd_active,
        "noop_ratio": ratios_by_a["0"]["ratio"],
        "move_ratios": move_ratios,
        "min_ratio": float(min(all_ratios)),
        "max_ratio": float(max(all_ratios)),
        "freq_weighted_ratio": w_mean_ratio,
        "ratios_by_action": {k: round(v["ratio"], 4) for k, v in ratios_by_a.items()},
    }
    print(f"[RULER {label}]", json.dumps(out), flush=True)
    return out

# 3A: Perfect-memory oracle (next_rows === real_board(t+1))
oracle_abs = RT6_he_n
oracle_res = x0_he + (RT6_he_n - RT6_he_t)
r_oracle_abs = eval_ruler_metrics(oracle_abs, x0_he, y1_he, acts_he_1, "oracle_whole_picture")
r_oracle_res = eval_ruler_metrics(oracle_res, x0_he, y1_he, acts_he_1, "oracle_residual_change")

# 3B: Exact-identity (zero delta) on Step-2 RT6
ident_abs = RT6_he_t
ident_res = x0_he + (RT6_he_t - RT6_he_t)
r_ident_abs = eval_ruler_metrics(ident_abs, x0_he, y1_he, acts_he_1, "identity_zero_delta_whole_picture")
r_ident_res = eval_ruler_metrics(ident_res, x0_he, y1_he, acts_he_1, "identity_zero_delta_residual_change")

# 3C: Actual Step-5 refit checkpoint (run_forecast3_refit/model.pt)
# Fit its own exact readout on its final weights (exact forecast3 refit procedure)
print("[STEP5] computing boards & readout for run_forecast3_refit/model.pt...", flush=True)
Z5_ro = np.concatenate([
    real_board_batch(m5r, tr, xi1_tr[ji_ro[b:b+128]], t1_tr[ji_ro[b:b+128]]).rows[:, 0].numpy()
    for b in range(0, 4000, 128)
]).reshape(4000, -1).astype(np.float64)
Y_ro = tr["frames"][xi1_tr[ji_ro]].astype(np.float64).reshape(4000, -1)
mu5 = Z5_ro[:3500].mean(0)
sd5 = np.maximum(Z5_ro[:3500].std(0), 1e-3 + 0.1 * np.median(Z5_ro[:3500].std(0)))
A5 = (Z5_ro[:3500] - mu5) / sd5
ym5 = Y_ro[:3500].mean(0)
al5 = np.linalg.solve(A5 @ A5.T + (3500 * NOISE ** 2) * np.eye(3500), Y_ro[:3500] - ym5)
Wnp5 = (A5.T @ al5) / sd5[:, None]
bp5 = ym5 - mu5 @ Wnp5
RT5 = lambda r_np: (r_np.reshape(len(r_np), -1).astype(np.float64) @ Wnp5 + bp5).reshape(-1, 16, 16, 3)

Z5_he_t = compute_all_boards(m5r, he, batch=128)
Z5_he_t_w = Z5_he_t[xi1_he]
Z5_he_n_hat = np.empty_like(Z5_he_t_w)
for b in range(0, len(xi1_he), 128):
    sl = slice(b, min(b + 128, len(xi1_he)))
    st5 = make_state(m5r, Z5_he_t_w[sl])
    act_t = torch.from_numpy(acts_he_1[sl].astype(np.int64))
    o5 = damped_imagine5(m5r.cell, st5, enc_act(m5r, act_t), m5r.action_emb(act_t))
    Z5_he_n_hat[sl] = o5.next_rows[:, 0].numpy()
step5_alpha_max = float(m5r.cell.imagine_alpha.abs().max())
step5_board_delta_max = float(np.abs(Z5_he_n_hat - Z5_he_t_w).max())
print(f"[STEP5] max|alpha|={step5_alpha_max:.3e} max|board_delta|={step5_board_delta_max:.3e}", flush=True)
P5_abs = RT5(Z5_he_n_hat)
P5_res = x0_he + (P5_abs - RT5(Z5_he_t_w))
r_s5_abs = eval_ruler_metrics(P5_abs, x0_he, y1_he, acts_he_1, "step5_refit_whole_picture")
r_s5_res = eval_ruler_metrics(P5_res, x0_he, y1_he, acts_he_1, "step5_refit_residual_change")

# 3D: Saved Step-6 (run_forecast4/model.pt) k=1 under whole-picture vs residual
P6_abs = RT6(nxt_he_m6)
P6_res = x0_he + (P6_abs - RT6_he_t)
r_s6_abs = eval_ruler_metrics(P6_abs, x0_he, y1_he, acts_he_1, "step6_whole_picture")
r_s6_res = eval_ruler_metrics(P6_res, x0_he, y1_he, acts_he_1, "step6_residual_change")

# Also check Step-6 shuffle ratio at k=1 under BOTH whole-picture and residual
sh1 = acts_he_1.copy()
g_sh = np.random.default_rng(43)
for w in np.unique(w1_he):
    idx = np.flatnonzero(w1_he == w)
    sh1[idx] = acts_he_1[idx[g_sh.permutation(len(idx))]]
_, nxt_he_m6_sh, _ = compute_hn_set(m6, Z_he_t, sh1)
P6_sh_abs = RT6(nxt_he_m6_sh)
P6_sh_res = x0_he + (P6_sh_abs - RT6_he_t)
mv1 = ((y1_he - x0_he) ** 2).mean((1, 2, 3)) > 1e-6
shuf6_abs = float(((P6_sh_abs[mv1] - y1_he[mv1]) ** 2).sum() / ((P6_abs[mv1] - y1_he[mv1]) ** 2).sum())
shuf6_res = float(((P6_sh_res[mv1] - y1_he[mv1]) ** 2).sum() / ((P6_res[mv1] - y1_he[mv1]) ** 2).sum())
print(f"[STEP6 SHUFFLE k1] whole_picture={shuf6_abs:.4f} residual={shuf6_res:.4f}", flush=True)

# 3E: Day (t < 125) vs Night (t >= 125) split
day_tr = t1_tr < 125
ngt_tr = t1_tr >= 125
day_he = t1_he < 125
ngt_he = t1_he >= 125

def subset_eb(P, mask):
    E = float(((P[mask] - y1_he[mask]) ** 2).sum())
    cp = float(((x0_he[mask] - y1_he[mask]) ** 2).sum())
    bs = float(((mean_tr + bl1 * (x0_he[mask] - mean_tr) - y1_he[mask]) ** 2).sum())
    return E / min(cp, bs)

day_night = {
    "train_day_n": int(day_tr.sum()),
    "train_night_n": int(ngt_tr.sum()),
    "train_day_brightness": float(tr["frames"][xi1_tr[day_tr]].astype(np.float64).mean()),
    "train_night_brightness": float(tr["frames"][xi1_tr[ngt_tr]].astype(np.float64).mean()) if ngt_tr.any() else None,
    "train_brightness_buckets_lt25_25to38_ge38": [
        int((xs_tr1.mean((1, 2, 3)) < 0.25).sum()),
        int(((xs_tr1.mean((1, 2, 3)) >= 0.25) & (xs_tr1.mean((1, 2, 3)) < 0.38)).sum()),
        int((xs_tr1.mean((1, 2, 3)) >= 0.38).sum()),
    ],
    "heldout_day_n": int(day_he.sum()),
    "heldout_night_n": int(ngt_he.sum()),
    "heldout_day_brightness": float(x0_he[day_he].mean()),
    "heldout_night_brightness": float(x0_he[ngt_he].mean()),
    "heldout_brightness_buckets_lt25_25to38_ge38": [
        int((x0_he.mean((1, 2, 3)) < 0.25).sum()),
        int(((x0_he.mean((1, 2, 3)) >= 0.25) & (x0_he.mean((1, 2, 3)) < 0.38)).sum()),
        int((x0_he.mean((1, 2, 3)) >= 0.38).sum()),
    ],
    "ceiling_abs_E1_B1_day": subset_eb(oracle_abs, day_he),
    "ceiling_abs_E1_B1_night": subset_eb(oracle_abs, ngt_he),
    "ceiling_res_E1_B1_day": subset_eb(oracle_res, day_he),
    "ceiling_res_E1_B1_night": subset_eb(oracle_res, ngt_he),
    "pixel_lin_E1_B1_day": subset_eb(P_pix_lin, day_he),
    "pixel_lin_E1_B1_night": subset_eb(P_pix_lin, ngt_he),
    "board_2A_abs_E1_B1_day": subset_eb(P_2a_abs_img, day_he),
    "board_2A_abs_E1_B1_night": subset_eb(P_2a_abs_img, ngt_he),
    "step6_abs_E1_B1_day": subset_eb(P6_abs, day_he),
    "step6_abs_E1_B1_night": subset_eb(P6_abs, ngt_he),
    "step6_res_E1_B1_day": subset_eb(P6_res, day_he),
    "step6_res_E1_B1_night": subset_eb(P6_res, ngt_he),
    "step6_shuf_abs_day": float(((P6_sh_abs[mv1 & day_he] - y1_he[mv1 & day_he]) ** 2).sum() / ((P6_abs[mv1 & day_he] - y1_he[mv1 & day_he]) ** 2).sum()),
    "step6_shuf_abs_night": float(((P6_sh_abs[mv1 & ngt_he] - y1_he[mv1 & ngt_he]) ** 2).sum() / ((P6_abs[mv1 & ngt_he] - y1_he[mv1 & ngt_he]) ** 2).sum()),
}
print("[DAY/NIGHT]", json.dumps(day_night, indent=1), flush=True)

# ==============================================================================
# PART 4: DOOR (g_slow READ vs IMAGINE) & NOISE VS REAL TRANSITION CHECK
# ==============================================================================
print("\n=== PART 4: DOOR & NOISE CHECK ===", flush=True)

# Measure g_slow during reading (run_tick on tick 1 & tick 2 of frame t for 256 heldout windows)
def measure_read_gslow(m, d, idx, tpos):
    # Hook/compute g_slow directly inside read of frame t (after reading frame t-1)
    h = np.where(tpos > 0, idx - 1, idx)
    st = m.read(m.cell.init_state(len(idx), 1, device=dev, dtype=torch.float32), m.encode(F(d, h)))
    enc = m.encode(F(d, idx))
    cell = m.cell
    gs_ticks = []
    for tick in range(2):
        rows = st.rows
        B, K, R, D = rows.shape
        N = B * K
        ns = cell.ns
        bidx = torch.arange(B, device=rows.device).repeat_interleave(K)
        x0 = rows.reshape(N, R, D)
        rd = cell._reading(None, B, rows.device)
        cemb = cell.clock_enc(rd)[bidx].to(x0.dtype)
        mode = cell.mode_emb.weight[int(ThinkMode.READ_INPUT)].to(x0.dtype)
        h_in = (
            cell.in_proj(x0)
            + cell.row_type_emb(cell.row_type)[None].to(x0.dtype)
            + cell.row_pos_emb[None].to(x0.dtype)
            + mode
            + cemb[:, None]
        )
        mem = enc.memory
        age_now = mem["age0"][bidx] + rd.elapsed_s.float()[bidx][:, None]
        focus = st.focus.reshape(-1).to(x0.dtype)
        h_out, _, _, _ = cell._trunk(h_in, mem, bidx, focus, age_now, None, R)
        hn = cell.norm_f(h_out)
        delta = cell.out_proj(hn).to(x0.dtype)
        gs = st.gate_scale.reshape(-1)
        pin = st.row_pin.reshape(N, R)
        slow0 = x0[:, :ns]
        prop = slow0 + delta[:, :ns]
        g_slow = torch.sigmoid(cell.gate(torch.cat([slow0, prop], dim=-1)).squeeze(-1)) * gs[:, None].to(prop.dtype)
        g_slow = torch.where(pin[:, :ns], torch.zeros_like(g_slow), g_slow)
        gs_ticks.append(g_slow.numpy())
        st = cell.run_tick(st, enc, noise=False).state
    return gs_ticks

gs_read_t1, gs_read_t2 = measure_read_gslow(m6, he, xi1_he[sel_q1], t1_he[sel_q1])
door_stats = {
    "read_tick1_g_slow": {"mean": float(gs_read_t1.mean()), "min": float(gs_read_t1.min()), "median": float(np.median(gs_read_t1)), "max": float(gs_read_t1.max())},
    "read_tick2_g_slow": {"mean": float(gs_read_t2.mean()), "min": float(gs_read_t2.min()), "median": float(np.median(gs_read_t2)), "max": float(gs_read_t2.max())},
    "imagine_step6_real_actions_g_slow": {"mean": float(gs_he_m6.mean()), "min": float(gs_he_m6.min()), "median": float(np.median(gs_he_m6)), "max": float(gs_he_m6.max())},
}

# Real 1-step transition variance in SD^2 units vs NOISE=0.2 injected variance
sd_grid = sd6.reshape(1, m6.R, m6.D)
dz_tr_sq = ((Z_tr_all[xi1_tr[fit_mask] + 1] - Z_tr_all[xi1_tr[fit_mask]]).astype(np.float64) / sd_grid) ** 2
dz_he_sq = ((Z_he_n - Z_he_t).astype(np.float64) / sd_grid) ** 2

# Simulate Step 6 exact batch-std noise (batch=64, 50 batches)
rng_n = np.random.default_rng(99)
fit_idx_all = np.flatnonzero(fit_mask)
inj_vars = []
for _ in range(50):
    b_idx = rng_n.choice(fit_idx_all, 64, replace=False)
    zb = Z_tr_all[xi1_tr[b_idx]].astype(np.float64)
    b_std = zb.std(0, keepdims=True)
    noise_term = NOISE * b_std * rng_n.standard_normal(zb.shape)
    inj_vars.append(float(np.mean((noise_term / sd_grid) ** 2)))

aa_fit = aa_tr[fit_mask]
noise_stats = {
    "noise_param": NOISE,
    "noise_theoretical_sd2": NOISE ** 2,
    "noise_measured_batch64_sd2": float(np.mean(inj_vars)),
    "real_1step_train_all_sd2": float(dz_tr_sq.mean()),
    "real_1step_train_slow_sd2": float(dz_tr_sq[:, :m6.cell.ns].mean()),
    "real_1step_train_fast_sd2": float(dz_tr_sq[:, m6.cell.ns:].mean()),
    "real_1step_train_moves1_4_sd2": float(dz_tr_sq[np.isin(aa_fit, [1, 2, 3, 4])].mean()),
    "real_1step_train_do5_sd2": float(dz_tr_sq[aa_fit == 5].mean()),
    "real_1step_train_sleep6_sd2": float(dz_tr_sq[aa_fit == 6].mean()),
    "real_1step_train_noop0_sd2": float(dz_tr_sq[aa_fit == 0].mean()),
    "real_1step_train_rare_sd2": float(dz_tr_sq[np.isin(aa_fit, [7, 10, 11, 12, 13, 14, 15, 16])].mean()),
    "real_1step_heldout_all_sd2": float(dz_he_sq.mean()),
    "noise_share_of_all_train_1step": float(np.mean(inj_vars) / dz_tr_sq.mean()),
    "noise_share_of_noop_train_1step": float(np.mean(inj_vars) / dz_tr_sq[aa_fit == 0].mean()),
    "step6_pred_delta_heldout_sd2": float(np.mean(((nxt_he_m6 - Z_he_t).astype(np.float64) / sd_grid) ** 2)),
    "step6_pred_delta_slow_sd2": float(np.mean(((nxt_he_m6[:, :m6.cell.ns] - Z_he_t[:, :m6.cell.ns]).astype(np.float64) / sd_grid[:, :m6.cell.ns]) ** 2)),
    "step6_pred_delta_fast_sd2": float(np.mean(((nxt_he_m6[:, m6.cell.ns:] - Z_he_t[:, m6.cell.ns:]).astype(np.float64) / sd_grid[:, m6.cell.ns:]) ** 2)),
}
print("[DOOR]", json.dumps(door_stats, indent=1), flush=True)
print("[NOISE]", json.dumps(noise_stats, indent=1), flush=True)

summary = {
    "elapsed_s": round(time.time() - t_start, 2),
    "trunk_freeze_max_diff": max_trunk_diff,
    "readout6": {"lam": lam6, "val_sse": val_sse6, "val_base": val_base6},
    "board_burial": board_burial,
    "hearing_step2_init": hear_m2,
    "hearing_step6_trained": hear_m6,
    "baselines": {"B1": B1_he, "copy1": cp1_he, "blend1": bs1_he, "pixel_linear_E1_B1": E_pix_lin / B1_he},
    "step2_board_per_action_ridge": {
        "2A_abs_E1_B1": E_2a_abs,
        "2A_del_E1_B1": E_2a_del,
        "2B_board_to_board_RT_abs_E1_B1": E_2b_abs,
        "2B_board_to_board_RT_res_E1_B1": E_2b_res,
        "2B_board_delta_R2": r2_2b_board,
    },
    "hn_probes_step6_trained": hn_res_m6,
    "hn_probes_step2_init": hn_res_m2,
    "ruler_checks": {
        "oracle_abs": r_oracle_abs,
        "oracle_res": r_oracle_res,
        "identity_abs": r_ident_abs,
        "identity_res": r_ident_res,
        "step5_refit_abs": r_s5_abs,
        "step5_refit_res": r_s5_res,
        "step6_abs": r_s6_abs,
        "step6_res": r_s6_res,
        "step6_k1_shuffle_abs": shuf6_abs,
        "step6_k1_shuffle_res": shuf6_res,
    },
    "day_night": day_night,
    "door_stats": door_stats,
    "noise_stats": noise_stats,
}
print("===JSON_BEGIN===")
print(json.dumps(summary, indent=1))
print("===JSON_END===")
