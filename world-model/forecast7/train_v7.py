"""PROBLEM-7 Forecast7 (Rank 7) Trainer & Evaluator.

Trains a dedicated 100%-learned 2-frame 2D Spatial Conv World Model strictly on k=1 real
transitions from train_dn.npz.
Evaluates open-loop k=1, 3, 5 rollouts via the pinned forecast7/scorer.py
(forecast7-v2, adopted n200_or_neff10 std gate, sha 720adce8a1881c2...) under two pinned rollout modes (`--rollout {plain,reencode}`):
  - `reencode` (`reencode_res`): verdict of record (projects intermediate open-loop latents
    onto the encoder manifold via `encode(clamp(x0 + decode(z) - dec0, 0, 1))`).
  - `plain`: raw latent rollout reported as the one-knob isolation.
Supports `--n-history {1,2}` so the exact same pinned evaluation path also re-scores saved
Rank 6 (`n_history=1`) models under both `plain` and `reencode` for a full 2x2 comparison.

Hard safety & anti-leakage guards:
  - Verifies forecast7/scorer.py exact SHA-256 at runtime before scoring.
  - REFUSES any path resolving to sealed_test.npz (via path, symlink, OR SHA-256)
    unless BOTH --eval-only AND --allow-sealed are passed.
  - When --allow-sealed is passed, verifies eval_data matches pinned sealed SHA-256.
  - In --eval-only mode, validates checkpoint BEFORE loading eval_data and restores
    checkpoint hyperparams into logged metadata.
  - Enforces >= 12.0 GiB free disk before training and before saving checkpoints.
  - Enforces M3 power rule before MPS use (`torch.device(args.device).type == "mps"`):
    AC Power OR battery >= 35% (via pmset).
  - Fails loudly (non-zero exit, no save/score) if done < args.steps, loss is
    non-finite, or grad_norm is non-finite before opt.step().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

MIN_FREE_GIB = 12.0
MIN_MPS_BATTERY_PCT = 35
PINNED_SEALED_TEST_SHA256 = "74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f"
PINNED_CANONICAL_BOARD_SWARM_SHA256 = "8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d"
ARCH_TAG_BY_HIST = {
    1: "R6_spatial_conv_unet",
    2: "R7_spatial_conv_unet_2f",
}
ARCH_TAG = ARCH_TAG_BY_HIST[2]
CEILING_DEFINITION = (
    "abs: decode(encode(x_{t+1})) [real next frame reconstructed through same encoder+decoder, "
    "zero actions/dynamics]; res: x_t + (decode(encode(x_{t+1})) - decode(encode(x_t)))"
)
AE_CEILING_DIAG_TRIGGER = 0.20


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_disk(path: str) -> float:
    target = path if os.path.exists(path) else os.path.dirname(os.path.abspath(path))
    while not os.path.exists(target):
        target = os.path.dirname(target)
    free_gib = shutil.disk_usage(target).free / (1024 ** 3)
    print(f"[DISK] {target}: {free_gib:.2f} GiB free (floor {MIN_FREE_GIB:.1f} GiB)", flush=True)
    if free_gib < MIN_FREE_GIB:
        sys.exit(f"ABORT: free disk {free_gib:.2f} GiB < {MIN_FREE_GIB:.1f} GiB floor")
    return free_gib


def parse_pmset_batt(output: str) -> tuple[bool, int | None]:
    """Parse `pmset -g batt` stdout -> (on_ac_power, battery_pct_or_None)."""
    on_ac = "AC Power" in output
    m = re.search(r"(\d+)%", output)
    pct = int(m.group(1)) if m else None
    return on_ac, pct


def check_mps_power(pmset_output: str | None = None) -> tuple[bool, int | None]:
    """Enforce AC Power OR battery >= 35% before any MPS execution."""
    if pmset_output is None:
        proc = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ABORT: pmset -g batt failed (rc={proc.returncode}): {proc.stderr.strip()}")
        pmset_output = proc.stdout
    on_ac, pct = parse_pmset_batt(pmset_output)
    if on_ac:
        print(f"[POWER] AC Power (battery={pct}%) -> OK for MPS", flush=True)
        return on_ac, pct
    if pct is not None and pct >= MIN_MPS_BATTERY_PCT:
        print(f"[POWER] Battery {pct}% >= {MIN_MPS_BATTERY_PCT}% -> OK for MPS", flush=True)
        return on_ac, pct
    raise RuntimeError(
        f"ABORT: MPS power guard tripped (on_ac={on_ac}, battery={pct}% < {MIN_MPS_BATTERY_PCT}%). "
        f"Connect AC power or charge to >= {MIN_MPS_BATTERY_PCT}% before running MPS."
    )


def is_sealed_path(path: str) -> bool:
    """Detect sealed test split by resolved realpath (following symlinks) OR pinned SHA-256."""
    real = os.path.realpath(path)
    if "sealed" in os.path.basename(real).lower() or "sealed" in real.lower():
        return True
    if "sealed" in os.path.basename(path).lower() or "sealed" in os.path.abspath(path).lower():
        return True
    if os.path.isfile(real) and sha256_file(real) == PINNED_SEALED_TEST_SHA256:
        return True
    return False


def guard_sealed_path(path: str, eval_only: bool, allow_sealed: bool) -> None:
    sealed = is_sealed_path(path)
    if sealed:
        if not (eval_only and allow_sealed):
            raise RuntimeError(
                f"REFUSED: {path} (resolved: {os.path.realpath(path)}) is a sealed test split! "
                f"Sealed test may ONLY be read with BOTH --eval-only AND --allow-sealed."
            )
        if os.path.isfile(os.path.realpath(path)):
            have = sha256_file(os.path.realpath(path))
            if have != PINNED_SEALED_TEST_SHA256:
                raise RuntimeError(
                    f"REFUSED: sealed eval file SHA {have} != pinned {PINNED_SEALED_TEST_SHA256}"
                )
    elif allow_sealed:
        raise RuntimeError(
            f"REFUSED: --allow-sealed was passed, but {path} is NOT the pinned sealed_test.npz!"
        )


def prev_frame_indices(split: dict, xi: np.ndarray, ti: np.ndarray) -> np.ndarray:
    """Compute strictly in-episode, in-world previous-frame index (x_{-1} = x_0 at episode start).

    Hard invariants enforced at runtime:
      - At episode start (ti == 0): h_idx == xi (x_{-1} = x_0).
      - For ti > 0: h_idx == xi - 1.
      - Never crosses an episode boundary OR world boundary.
    """
    xi = np.asarray(xi, dtype=np.int64)
    ti = np.asarray(ti, dtype=np.int64)
    if xi.shape != ti.shape:
        raise ValueError(f"xi shape {xi.shape} != ti shape {ti.shape}")
    h_idx = np.where(ti > 0, xi - 1, xi)
    if len(xi) > 0:
        if np.any(h_idx < 0):
            raise RuntimeError("History index went negative (< 0)!")
        if not np.array_equal(split["episode_id"][h_idx], split["episode_id"][xi]):
            raise RuntimeError("History index crossed an episode boundary!")
        if not np.array_equal(split["world_id"][h_idx], split["world_id"][xi]):
            raise RuntimeError("History index crossed a world boundary!")
        if not np.all((h_idx == xi) | (h_idx == xi - 1)):
            raise RuntimeError("Invalid history offset (must be 0 or -1)!")
        if not np.all(h_idx[ti == 0] == xi[ti == 0]):
            raise RuntimeError("Episode start (ti == 0) did not clamp x_{-1} = x_0!")
    return h_idx


def clip_and_check_grad_norm(parameters, max_norm: float = 1.0) -> torch.Tensor:
    """Clip global grad norm and abort loudly before opt.step() if any gradient is non-finite."""
    grad_norm = torch.nn.utils.clip_grad_norm_(parameters, max_norm)
    if not torch.isfinite(grad_norm):
        raise RuntimeError(f"Non-finite grad_norm={float(grad_norm)} before opt.step()")
    return grad_norm


def compute_train_step_loss(
    model,
    x_prev: torch.Tensor,
    x_t: torch.Tensor,
    act: torch.Tensor,
    x_next: torch.Tensor,
    *,
    w_lat: float = 0.05,
):
    """Strictly k=1 real-transition joint loss (start latents detached on dynamics branch).

    Encoder receives ONLY `l_rec` on `x_t` (imagination never corrupts encoding).
    Dynamics receives ONLY `l_img_res + 0.25 * l_img_abs + w_lat * l_lat` (exact Rank 6 loss).
    """
    z_t = model.encode(x_t)
    with torch.no_grad():
        z_next_tgt = model.encode(x_next)
        z_prev_det = model.encode(x_prev) if model.n_history == 2 else None

    x_rec_t = model.decode(z_t)
    l_rec = ((x_rec_t - x_t) ** 2).mean()

    z_next_pred = model.imagine_step(z_t.detach(), act, z_prev=z_prev_det, wm_grad=True)
    x_img_abs = model.decode(z_next_pred)
    x_img_res = x_t + (x_img_abs - x_rec_t.detach())

    l_img_res = ((x_img_res - x_next) ** 2).mean()
    l_img_abs = ((x_img_abs - x_next) ** 2).mean()
    l_lat = ((z_next_pred - z_next_tgt) ** 2).mean()
    copy_mse = ((x_t - x_next) ** 2).mean().clamp_min(1e-8)

    loss = 1.0 * l_rec + 1.0 * l_img_res + 0.25 * l_img_abs + float(w_lat) * l_lat
    metrics = {
        "loss": float(loss.detach()),
        "l_rec": float(l_rec.detach()),
        "l_img_res": float(l_img_res.detach()),
        "l_img_abs": float(l_img_abs.detach()),
        "l_lat": float(l_lat.detach()),
        "img_over_copy": float(l_img_res.detach() / copy_mse),
    }
    return loss, metrics, z_t.detach()


def compute_interaction_diagnostics(eval_split: dict, pred_k1: np.ndarray) -> dict:
    """Non-gating honesty diagnostic: asleep wake-up R2 + non-wake do/place_table/place_furnace R2.

    100% purely visual (zero game-memory cheats): separates sleep wake-ups by visual terrain std
    jump (`s0 < 0.08` -> `s1 > 0.10` and `rms > 0.08`) so wake-up prediction is reported separately
    from awake local chopping/placing (`Ctr6x6 [3:9, 5:11]` and `HUD [12:, :]`).
    """
    import scorer

    xi1, ai1, _, _, _ = scorer.windows(eval_split, 1)
    hfr = eval_split["frames"].astype(np.float64)
    x0 = hfr[xi1]
    x1 = hfr[xi1 + 1]
    a0 = eval_split["actions"][ai1]
    P1 = np.asarray(pred_k1, dtype=np.float64)
    dY = x1 - x0
    dP = P1 - x0

    s0 = x0[:, :12].std((1, 2, 3))
    s1 = x1[:, :12].std((1, 2, 3))
    rms = np.sqrt((dY ** 2).mean((1, 2, 3)))
    asleep = s0 < 0.08
    is_wake = asleep & (s1 > 0.10) & (rms > 0.08)

    def _r2_std(dp_sub, dy_sub):
        if len(dy_sub) == 0:
            return {"n": 0, "R2": None, "std_ratio": None}
        sse_p = float(((dp_sub - dy_sub) ** 2).sum())
        sse_0 = float((dy_sub ** 2).sum())
        r2 = float(1.0 - sse_p / sse_0) if sse_0 > 1e-12 else 0.0
        sp = float(dp_sub.std())
        sr = float(dy_sub.std())
        rat = 1.0 if (sr < 1e-12 and sp < 1e-12) else float(sp / (sr + 1e-12))
        return {"n": int(len(dy_sub)), "R2": r2, "std_ratio": rat}

    # Asleep overall + brightness-jump AUROC on wake vs stay-asleep
    asl_stat = _r2_std(dP[asleep], dY[asleep])
    asl_stat["n_wake"] = int(is_wake.sum())
    stay_asl = asleep & (~is_wake)
    if is_wake.any() and stay_asl.any():
        db_wk = dP[is_wake, :12].mean((1, 2, 3))
        db_st = dP[stay_asl, :12].mean((1, 2, 3))
        asl_stat["wake_dBright_auroc"] = float(
            (db_wk[:, None] > db_st[None, :]).mean() + 0.5 * (db_wk[:, None] == db_st[None, :]).mean()
        )
    else:
        asl_stat["wake_dBright_auroc"] = None

    m_ctr_hud = np.zeros((16, 16), dtype=bool)
    m_ctr_hud[3:9, 5:11] = True
    m_ctr_hud[12:, :] = True

    non_wake_actions = {}
    for q, name in ((5, "do"), (8, "place_table"), (9, "place_furnace")):
        sel = (a0 == q) & (~is_wake)
        full = _r2_std(dP[sel], dY[sel])
        ctr = _r2_std(dP[sel][:, 3:9, 5:11, :], dY[sel][:, 3:9, 5:11, :])
        hud = _r2_std(dP[sel][:, 12:, :, :], dY[sel][:, 12:, :, :])
        ch = _r2_std(dP[sel][:, m_ctr_hud, :], dY[sel][:, m_ctr_hud, :])
        non_wake_actions[f"{q}_{name}"] = {
            "n": full["n"],
            "n_wake_excluded": int(((a0 == q) & is_wake).sum()),
            "full_R2": full["R2"],
            "full_std_ratio": full["std_ratio"],
            "ctr6x6_R2": ctr["R2"],
            "ctr6x6_std_ratio": ctr["std_ratio"],
            "hud_R2": hud["R2"],
            "hud_std_ratio": hud["std_ratio"],
            "ctr_hud_R2": ch["R2"],
            "ctr_hud_std_ratio": ch["std_ratio"],
        }

    return {
        "asleep_all": asl_stat,
        "non_wake_actions": non_wake_actions,
    }


def _fit_linear_action_baseline_2f(train_split: dict, ridge: float = 1.0) -> dict[int, np.ndarray]:
    import scorer

    xi1, ai1, _, _, ti1 = scorer.windows(train_split, 1)
    h1 = prev_frame_indices(train_split, xi1, ti1)
    fr = train_split["frames"].astype(np.float64)
    Xt = fr[xi1].reshape(len(xi1), -1)
    Xp = fr[h1].reshape(len(xi1), -1)
    Xd = Xt - Xp
    Ya = fr[xi1 + 1].reshape(len(xi1), -1)
    aa = train_split["actions"][ai1]
    eye = float(ridge) * np.eye(1537)
    Mact = {}
    for q in range(17):
        sel = aa == q
        if sel.sum() == 0:
            Mact[q] = np.vstack([np.eye(768), np.zeros((769, 768))])
        else:
            Xq = np.c_[Xt[sel], Xd[sel], np.ones(sel.sum())]
            Mact[q] = np.linalg.solve(Xq.T @ Xq + eye, Xq.T @ Ya[sel])
    return Mact


def _rollout_linear_action_baseline_2f(Mact: dict, x_prev: np.ndarray, x0: np.ndarray, acts_k: np.ndarray) -> np.ndarray:
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


def _fit_shift_or_stay_baseline_2f(train_split: dict, ridge: float = 1.0, gate_ridge: float = 10.0) -> dict:
    import scorer

    xi1, ai1, _, _, ti1 = scorer.windows(train_split, 1)
    h1 = prev_frame_indices(train_split, xi1, ti1)
    fr = train_split["frames"].astype(np.float64)
    Xp_img = fr[h1]
    X_img = fr[xi1]
    Y_img = fr[xi1 + 1]
    Xp = Xp_img.reshape(len(xi1), -1)
    Xt = X_img.reshape(len(xi1), -1)
    Xd = Xt - Xp
    Ya = Y_img.reshape(len(xi1), -1)
    aa = train_split["actions"][ai1]
    valid_mv, is_open_mv, _ = scorer.classify_move_displacement(X_img, Y_img, aa)
    Mact = _fit_linear_action_baseline_2f(train_split, ridge=ridge)
    Mshift = {}
    Wgate = {}
    eye = float(ridge) * np.eye(1537)
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
            Wgate[q] = np.linalg.solve(Xc.T @ Xc + float(gate_ridge) * np.eye(Xc.shape[1]), Xc.T @ yc)
    return {"Mact": Mact, "Mshift": Mshift, "Wgate": Wgate}


def _rollout_shift_or_stay_2f(sos: dict, x_prev: np.ndarray, x0: np.ndarray, acts_k: np.ndarray) -> np.ndarray:
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


def compute_2f_baselines_context(train_split: dict, eval_split: dict, B_by_k: dict[int, float]) -> dict:
    """Non-gating context: 2-frame versions of linear_Mact and shift_or_stay (pinned bars remain 1-frame)."""
    import scorer

    Mact2 = _fit_linear_action_baseline_2f(train_split, ridge=1.0)
    sos2 = _fit_shift_or_stay_baseline_2f(train_split, ridge=1.0, gate_ridge=10.0)
    hfr = eval_split["frames"].astype(np.float64)

    out = {
        "note": "Non-gating 2-frame baseline context (exact analog of scorer.py ridge=1.0, gate_ridge=10.0). Pinned pass bars stay 1-frame.",
        "linear_Mact_2f": {"E_over_B": {}},
        "shift_or_stay_2f": {"E_over_B": {}},
    }
    for k in (1, 3, 5):
        xi, ai, wi, _, ti = scorer.windows(eval_split, k)
        h = prev_frame_indices(eval_split, xi, ti)
        ak = scorer.action_values(eval_split["actions"], ai, k)
        xp, x0, yk = hfr[h], hfr[xi], hfr[xi + k]
        p_act = _rollout_linear_action_baseline_2f(Mact2, xp, x0, ak)
        p_sos = _rollout_shift_or_stay_2f(sos2, xp, x0, ak)
        Bk = max(float(B_by_k[k]), 1e-12)
        out["linear_Mact_2f"]["E_over_B"][f"k{k}"] = float(((p_act - yk) ** 2).sum()) / Bk
        out["shift_or_stay_2f"]["E_over_B"][f"k{k}"] = float(((p_sos - yk) ** 2).sum()) / Bk
        if k == 1:
            out["linear_Mact_2f"]["block_open"] = scorer.score_block_open(x0, p_act, yk, ak[:, 0], wi)
            out["shift_or_stay_2f"]["block_open"] = scorer.score_block_open(x0, p_sos, yk, ak[:, 0], wi)
    return out


@torch.no_grad()
def rollout_eval_predictions(
    model,
    eval_split: dict,
    device: torch.device,
    *,
    rollout: str = "reencode",
    batch_size: int = 128,
    horizons: tuple[int, ...] = (1, 3, 5),
    compute_ceiling: bool = True,
):
    """Generate open-loop predictions (real + per-step shuffled) for requested horizons.

    Strictly enforces all history rules:
      - Only `x_{t-1}` (`prev_frame_indices`) and `x_t` (`xi`) are read from `eval_split["frames"]`.
      - Never touches `eval_split["frames"][xi + 1 .. xi + k - 1]`.
      - Episode starts clamp `x_{-1} = x_0` and never cross episode or world boundaries.
    """
    import scorer
    from model_v7 import ROLLOUT_MODES

    if rollout not in ROLLOUT_MODES:
        raise ValueError(f"Unknown rollout={rollout!r}; expected one of {ROLLOUT_MODES}")

    model.eval()
    hfr = eval_split["frames"]
    sh_acts = scorer.shuffle_actions_per_step(eval_split, seed=43)

    def _f(idx):
        return torch.from_numpy(hfr[idx].astype(np.float32)).to(device)

    preds_by_k = {}
    preds_abs_by_k = {}
    shuf_preds_by_k = {}
    ceil_abs_k1 = None
    ceil_res_k1 = None

    for k in horizons:
        xi, ai, _, _, ti = scorer.windows(eval_split, k)
        h_idx = prev_frame_indices(eval_split, xi, ti)
        acts_k = scorer.action_values(eval_split["actions"], ai, k)
        s_acts_k = scorer.action_values(sh_acts, ai, k)

        P_list, Pabs_list, Ps_list = [], [], []
        c_abs_list, c_res_list = [], []

        for b in range(0, len(xi), batch_size):
            sl = slice(b, min(b + batch_size, len(xi)))
            i = xi[sl]
            x0 = _f(i)
            x_prev = _f(h_idx[sl]) if model.n_history == 2 else None
            ak_t = torch.from_numpy(acts_k[sl].astype(np.int64)).to(device)
            sak_t = torch.from_numpy(s_acts_k[sl].astype(np.int64)).to(device)

            out_r = model.rollout(x0, ak_t, x_prev=x_prev, rollout_mode=rollout, wm_grad=False)
            out_s = model.rollout(x0, sak_t, x_prev=x_prev, rollout_mode=rollout, wm_grad=False)
            P_list.append(out_r["pred_res"].cpu().double().numpy())
            Pabs_list.append(out_r["pred_abs"].cpu().double().numpy())
            Ps_list.append(out_s["pred_res"].cpu().double().numpy())

            if k == 1 and compute_ceiling:
                x1 = _f(i + 1)
                dec0 = model.decode(out_r["z0"])
                dec1 = model.decode(model.encode(x1))
                c_abs_list.append(dec1.cpu().double().numpy())
                c_res_list.append((x0 + (dec1 - dec0)).cpu().double().numpy())

        preds_by_k[k] = np.concatenate(P_list, axis=0)
        preds_abs_by_k[k] = np.concatenate(Pabs_list, axis=0)
        shuf_preds_by_k[k] = np.concatenate(Ps_list, axis=0)
        if k == 1 and compute_ceiling:
            ceil_abs_k1 = np.concatenate(c_abs_list, axis=0)
            ceil_res_k1 = np.concatenate(c_res_list, axis=0)

    return preds_by_k, preds_abs_by_k, shuf_preds_by_k, ceil_abs_k1, ceil_res_k1


@torch.no_grad()
def evaluate_model(
    model,
    train_split: dict,
    eval_split: dict,
    device: torch.device,
    batch_size: int = 128,
    extra_meta: dict | None = None,
    rollout: str = "reencode",
    include_2f_baselines: bool = True,
):
    """Run strictly open-loop k=1,3,5 evaluation (real + per-step shuffled actions).

    `rollout` selects `plain` (raw latent rollout) or `reencode` (`reencode_res`, verdict of record).
    """
    import scorer

    preds_by_k, preds_abs_by_k, shuf_preds_by_k, ceil_abs_k1, ceil_res_k1 = rollout_eval_predictions(
        model,
        eval_split,
        device,
        rollout=rollout,
        batch_size=batch_size,
        horizons=(1, 3, 5),
        compute_ceiling=True,
    )

    meta = dict(extra_meta or {})
    meta["rollout_mode"] = rollout
    meta["n_history"] = int(model.n_history)

    res = scorer.score_predictions(
        train_split,
        eval_split,
        preds_by_k,
        shuf_preds_by_k,
        ceiling_abs_pred_k1=ceil_abs_k1,
        ceiling_res_pred_k1=ceil_res_k1,
        extra_meta=meta,
    )
    hfr = eval_split["frames"]
    diag_abs = {}
    B_by_k = {}
    for k in (1, 3, 5):
        xi = scorer.windows(eval_split, k)[0]
        yk = hfr[xi + k].astype(np.float64)
        e_abs = float(((preds_abs_by_k[k] - yk) ** 2).sum())
        B_by_k[k] = res[f"k{k}"]["B"]
        diag_abs[f"k{k}"] = e_abs / max(B_by_k[k], 1e-12)

    res["diag_pred_abs_E_over_B"] = diag_abs
    res["diag_ae_ceiling_le_0.20"] = bool(res["k1"]["ceiling_abs_E_over_B"] <= AE_CEILING_DIAG_TRIGGER)
    res["diag_non_wake_interactions"] = compute_interaction_diagnostics(eval_split, preds_by_k[1])
    if include_2f_baselines:
        res["diag_baselines_2f"] = compute_2f_baselines_context(train_split, eval_split, B_by_k)
    res["rank7_verdict"] = res["rung1_verdict"]
    return res, preds_by_k


def lr_factor(step: int, total_steps: int, warmup: int = 100, min_ratio: float = 0.1) -> float:
    w = min(warmup, max(total_steps // 10, 1)) if total_steps < warmup else warmup
    if step < w:
        return float(step + 1) / float(max(w, 1))
    prog = float(step - w) / float(max(total_steps - w, 1))
    prog = min(max(prog, 0.0), 1.0)
    return min_ratio + (1.0 - min_ratio) * 0.5 * (1.0 + math.cos(math.pi * prog))


def main():
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    from model_v7 import MODEL_SIZES, ROLLOUT_MODES, SpatialWorldModelV7, verify_pinned_scorer

    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=sorted(MODEL_SIZES.keys()), default="R7conv")
    ap.add_argument("--n-history", type=int, choices=(1, 2), default=2)
    ap.add_argument("--rollout", choices=ROLLOUT_MODES, default="reencode")
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--train-data", default="../wm5/data/train_dn.npz")
    ap.add_argument("--eval-data", default="../wm-harness/data/heldout.npz")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=5000)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--wd", type=float, default=1e-4)
    ap.add_argument("--w-lat", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-minutes", type=float, default=14.0)
    ap.add_argument("--eval-only", default=None, help="Path to saved model.pt to evaluate without training")
    ap.add_argument("--allow-sealed", action="store_true", help="Explicit opt-in required with --eval-only to touch sealed_test.npz")
    ap.add_argument("--save-forecasts", action="store_true")
    ap.add_argument("--skip-disk-check", action="store_true")
    ap.add_argument("--skip-power-check", action="store_true", help="Test-only override; never pass on M3 MPS runs")
    ap.add_argument("--timing-only", action="store_true", help="Run exact training loop for --steps without saving or scoring")
    args = ap.parse_args()

    scorer_sha = verify_pinned_scorer(here / "scorer.py")
    guard_sealed_path(args.train_data, eval_only=False, allow_sealed=False)

    dev = torch.device(args.device)
    if dev.type == "mps" and not args.skip_power_check:
        check_mps_power()

    os.makedirs(args.out, exist_ok=True)
    if not args.skip_disk_check:
        check_disk(args.out)

    expected_arch = ARCH_TAG_BY_HIST[args.n_history]
    torch.manual_seed(args.seed)
    model = SpatialWorldModelV7(size=args.size, n_history=args.n_history).to(dev)
    pcounts = model.param_counts()

    # Validate --eval-only checkpoint BEFORE reading eval_data (never open sealed_test.npz on bad ckpt!)
    ck = None
    ck_meta = {}
    if args.eval_only:
        ck = torch.load(args.eval_only, map_location=dev, weights_only=False)
        ck_meta = ck.get("meta", {})
        if ck_meta.get("arch") != expected_arch:
            raise ValueError(f"Checkpoint arch {ck_meta.get('arch')!r} != expected {expected_arch!r} (n_history={args.n_history})")
        if ck_meta.get("size") != args.size:
            raise ValueError(f"Checkpoint size {ck_meta.get('size')!r} != CLI --size {args.size!r}")
        model.load_state_dict(ck["model"], strict=True)
        print(
            f"[EVAL-ONLY] validated & loaded {args.eval_only} "
            f"(arch={ck_meta.get('arch')}, size={ck_meta.get('size')}, seed={ck_meta.get('seed')}, rollout={args.rollout})",
            flush=True,
        )

    guard_sealed_path(args.eval_data, eval_only=bool(args.eval_only), allow_sealed=bool(args.allow_sealed))

    print(
        f"[INIT] arch={expected_arch} size={args.size} n_history={args.n_history} rollout={args.rollout} "
        f"dev={args.device} seed={args.seed} enc={pcounts['encoder']:,} dec={pcounts['decoder']:,} "
        f"act={pcounts['action_emb']:,} dyn={pcounts['dynamics']:,} total={pcounts['model_total']:,} "
        f"scorer_sha={scorer_sha[:12]}",
        flush=True,
    )

    import scorer

    tr = scorer.load_split(args.train_data)
    ev = scorer.load_split(args.eval_data)
    xi1, ai1, _, _, ti1 = scorer.windows(tr, 1)
    h1 = prev_frame_indices(tr, xi1, ti1)
    print(
        f"[DATA] train={args.train_data} ({len(xi1)} k1 wins) eval={args.eval_data} "
        f"({len(scorer.windows(ev, 1)[0])} k1 wins)",
        flush=True,
    )

    train_meta = {
        "arch": expected_arch,
        "size": args.size,
        "n_history": int(args.n_history),
        "rollout_mode": args.rollout,
        "model_cfg": model.cfg,
        "seed": args.seed,
        "device": args.device,
        "w_lat": float(args.w_lat),
        "lr": float(args.lr),
        "wd": float(args.wd),
        "batch": int(args.batch),
        "ceiling_definition": CEILING_DEFINITION,
        "scorer_sha256": scorer_sha,
        "train_data": os.path.abspath(args.train_data),
        "train_data_sha256": sha256_file(args.train_data),
        "eval_data": os.path.abspath(args.eval_data),
        "eval_data_sha256": sha256_file(args.eval_data),
        "params": pcounts,
    }

    if args.eval_only:
        train_meta["eval_only_ckpt"] = os.path.abspath(args.eval_only)
        train_meta["eval_only_ckpt_sha256"] = sha256_file(args.eval_only)
        train_meta["trained_steps"] = ck.get("steps", None)
        train_meta["ckpt_seed"] = ck_meta.get("seed", None)
        # Restore trained hyperparams from checkpoint metadata when present
        for k_hp in ("seed", "w_lat", "lr", "wd", "batch"):
            if ck_meta.get(k_hp) is not None:
                train_meta[k_hp] = ck_meta[k_hp]
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd)
        sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: lr_factor(s, args.steps))
        rng = np.random.default_rng(args.seed)
        t0 = time.time()
        t_steady = None
        warmup_timing = min(10, max(args.steps // 5, 1))
        done = 0
        grad_step0 = {}
        lat_step0 = None
        lat_final = None
        model.train()

        for s in range(args.steps):
            if s == warmup_timing:
                if dev.type == "mps":
                    torch.mps.synchronize()
                t_steady = time.time()

            j = rng.integers(0, len(xi1), size=args.batch)
            i = xi1[j]
            h = h1[j]
            x_prev = torch.from_numpy(tr["frames"][h].astype(np.float32)).to(dev)
            x_t = torch.from_numpy(tr["frames"][i].astype(np.float32)).to(dev)
            x_next = torch.from_numpy(tr["frames"][i + 1].astype(np.float32)).to(dev)
            act = torch.from_numpy(tr["actions"][ai1[j]].astype(np.int64)).to(dev)

            loss, m, z_t = compute_train_step_loss(model, x_prev, x_t, act, x_next, w_lat=args.w_lat)
            if not torch.isfinite(loss):
                raise RuntimeError(f"Non-finite loss at step {s}: {m}")

            opt.zero_grad(set_to_none=True)
            loss.backward()
            if s == 0:
                grad_step0["action_emb"] = float(model.action_emb.weight.grad.norm())
                grad_step0["encoder"] = float(
                    math.sqrt(sum(float(p.grad.pow(2).sum()) for p in model.encoder.parameters() if p.grad is not None))
                )
                grad_step0["dynamics"] = float(
                    math.sqrt(sum(float(p.grad.pow(2).sum()) for p in model.dynamics.parameters() if p.grad is not None))
                )
                grad_step0["decoder"] = float(
                    math.sqrt(sum(float(p.grad.pow(2).sum()) for p in model.decoder.parameters() if p.grad is not None))
                )
                lat_step0 = model.latent_stats(z_t)
                print(
                    f"[STEP0] grad={ {k: round(v, 5) for k, v in grad_step0.items()} } "
                    f"lat_burial={lat_step0['burial_ratio']:.2f} "
                    f"(static={lat_step0['static_rms']:.4f}, spread={lat_step0['spread_rms']:.4f})",
                    flush=True,
                )

            grad_norm = clip_and_check_grad_norm(model.parameters(), 1.0)
            opt.step()
            sch.step()
            done = s + 1

            if s < 3 or (s + 1) % 250 == 0 or (s + 1) == args.steps:
                el = time.time() - t0
                print(
                    f"step {s:4d} loss {m['loss']:.5f} rec {m['l_rec']:.5f} "
                    f"img_res {m['l_img_res']:.5f} img_abs {m['l_img_abs']:.5f} "
                    f"img/copy {m['img_over_copy']:.3f} lat {m['l_lat']:.5f} "
                    f"gnorm {float(grad_norm):.3f} t {el:.1f}s",
                    flush=True,
                )

            if args.max_minutes > 0.0 and (time.time() - t0) >= args.max_minutes * 60.0 and done < args.steps:
                print(f"[CAP] max-minutes {args.max_minutes} reached at step {done}/{args.steps}", flush=True)
                break

        if dev.type == "mps":
            torch.mps.synchronize()
        train_sec = time.time() - t0

        if done < args.steps:
            raise RuntimeError(
                f"INCOMPLETE RUN: completed {done}/{args.steps} steps before hitting "
                f"max-minutes={args.max_minutes} cap ({train_sec:.1f}s). "
                f"Refusing to save/score an under-stepped run."
            )

        if args.timing_only:
            steady_steps = done - warmup_timing
            steady_sec = (time.time() - t_steady) if (t_steady is not None and steady_steps > 0) else train_sec
            ms_per_step = (steady_sec / max(steady_steps, 1)) * 1000.0
            print(
                f"[TIMING] size={args.size} n_history={args.n_history} steps={done} total={train_sec:.2f}s "
                f"steady({steady_steps}st)={steady_sec:.2f}s ms/step={ms_per_step:.1f} "
                f"proj_3000={ms_per_step*3000/60000:.2f}m proj_4000={ms_per_step*4000/60000:.2f}m "
                f"proj_5000={ms_per_step*5000/60000:.2f}m proj_6000={ms_per_step*6000/60000:.2f}m",
                flush=True,
            )
            return

        model.eval()
        with torch.no_grad():
            j_b = np.random.default_rng(7).choice(len(xi1), min(128, len(xi1)), replace=False)
            z_b = model.encode(torch.from_numpy(tr["frames"][xi1[j_b]].astype(np.float32)).to(dev))
            lat_final = model.latent_stats(z_b)

        train_meta.update({
            "requested_steps": int(args.steps),
            "trained_steps": done,
            "train_wall_seconds": round(train_sec, 2),
            "grad_step0": grad_step0,
            "lat_step0": lat_step0,
            "lat_final": lat_final,
        })
        if not args.skip_disk_check:
            check_disk(args.out)
        ckpt_path = os.path.join(args.out, "model.pt")
        torch.save({"model": model.state_dict(), "steps": done, "meta": train_meta}, ckpt_path)
        print(
            f"[SAVED] {ckpt_path} ({done} steps, {train_sec:.1f}s, lat_burial={lat_final['burial_ratio']:.2f})",
            flush=True,
        )

    t_eval = time.time()
    res, preds_by_k = evaluate_model(model, tr, ev, dev, extra_meta=train_meta, rollout=args.rollout)
    eval_sec = time.time() - t_eval
    res["eval_wall_seconds"] = round(eval_sec, 2)

    split_tag = "sealed" if is_sealed_path(args.eval_data) else "dev"
    score_mode_path = os.path.join(args.out, f"score_{split_tag}_{args.rollout}.json")
    with open(score_mode_path, "w") as f:
        json.dump(res, f, indent=2)
    # Verdict of record (`reencode`) also populates canonical score_{split_tag}.json
    if args.rollout == "reencode":
        score_canon_path = os.path.join(args.out, f"score_{split_tag}.json")
        with open(score_canon_path, "w") as f:
            json.dump(res, f, indent=2)

    if args.save_forecasts:
        fc_path = os.path.join(args.out, f"forecasts_{split_tag}_{args.rollout}.npz")
        np.savez(
            fc_path,
            pred_k1=preds_by_k[1].astype(np.float16),
            pred_k3=preds_by_k[3].astype(np.float16),
            pred_k5=preds_by_k[5].astype(np.float16),
        )

    k1, k3, k5 = res["k1"], res["k3"], res["k5"]
    bo = k1["block_open"]
    nw = res["diag_non_wake_interactions"]
    asl_r2 = nw["asleep_all"]["R2"]
    do_nw = nw["non_wake_actions"]["5_do"]
    pt_nw = nw["non_wake_actions"]["8_place_table"]
    print(
        f"[SCORE {split_tag} {args.rollout}] E/B={k1['E_over_B']:.4f}/{k3['E_over_B']:.4f}/{k5['E_over_B']:.4f} "
        f"(base1f={k1['strongest_baseline_E_over_B']:.4f}/{k3['strongest_baseline_E_over_B']:.4f}/{k5['strongest_baseline_E_over_B']:.4f}) "
        f"ceil_abs={k1['ceiling_abs_E_over_B']:.4f} ceil_res={k1['ceiling_res_E_over_B']:.4f} "
        f"shuf={k1['shuffle_pooled']:.3f}/{k5['shuffle_pooled']:.3f} "
        f"worlds={res['worlds_k1_shuffle']}/{res['worlds_k5_shuffle']}/{res['worlds_both']} "
        f"pcs={k1['pcs90_pred']}/{k1['pcs90_real']} std_ok={res['std_ok']} "
        f"bo_err={bo['model']['mean_err']:.4f} (fb={bo['model']['false_block_rate']:.4f}, fo={bo['model']['false_open_rate']:.4f}, "
        f"base={bo['strongest_baseline_mean_err']:.4f}, cut={bo['mean_err_reduction_frac']*100:.1f}%) "
        f"diag_aslR2={asl_r2 if asl_r2 is not None else float('nan'):+.3f} "
        f"diag_nw_do_chR2={do_nw['ctr_hud_R2'] if do_nw['ctr_hud_R2'] is not None else float('nan'):+.3f} "
        f"diag_nw_pt_chR2={pt_nw['ctr_hud_R2'] if pt_nw['ctr_hud_R2'] is not None else float('nan'):+.3f} "
        f"strike={res['strike_class']} reasons={res['strike_reasons']} "
        f"legacy={res['verdict']} rung1={res['rung1_verdict']} rank7={res['rank7_verdict']} eval_t={eval_sec:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
