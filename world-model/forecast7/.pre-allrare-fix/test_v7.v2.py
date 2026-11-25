"""Unit tests for PROBLEM-7 Forecast7 (Rank 7: 2-Frame 2D Conv World Model) — fast CPU verification."""
from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
FORECAST5_SCORER_SHA256 = "6ff1c135c0eeb2085aa4d49479b915cc5630f355b6d4ad3d5fa18ad81a98b83c"
sys.path.insert(0, str(HERE))

import scorer
import train_v7
from model_v7 import PINNED_SCORER_SHA256, SpatialWorldModelV7, verify_pinned_scorer
from train_v7 import (
    ARCH_TAG,
    ARCH_TAG_BY_HIST,
    PINNED_CANONICAL_BOARD_SWARM_SHA256,
    check_mps_power,
    clip_and_check_grad_norm,
    compute_train_step_loss,
    evaluate_model,
    guard_sealed_path,
    prev_frame_indices,
    rollout_eval_predictions,
    sha256_file,
)


def test_1_pinned_scorer_and_canonical_core_untouched():
    """Verify the adopted forecast7 scorer pin, untouched forecast5 scorer, and canonical core."""
    sha = verify_pinned_scorer(HERE / "scorer.py")
    assert sha == PINNED_SCORER_SHA256
    for old_scorer in (
        HERE.parent / "forecast5" / "scorer.py",
        HERE.parent / "forecast6" / "scorer.py",
        Path.home() / "learner-ops" / "seven-problems-m3" / "PROBLEM-7" / "wm5" / "scorer.py",
        Path.home() / "learner-ops" / "seven-problems-m3" / "PROBLEM-7" / "wm6" / "scorer.py",
    ):
        if old_scorer.exists():
            assert sha256_file(str(old_scorer)) == FORECAST5_SCORER_SHA256
    for cand in (
        HERE.parent / "wm-harness" / "premonition_core_v2" / "board_swarm.py",
        Path("<m3-project>/PROBLEM-7/wm-harness/premonition_core_v2/board_swarm.py"),
    ):
        if cand.exists():
            assert sha256_file(str(cand)) == PINNED_CANONICAL_BOARD_SWARM_SHA256


def test_2_param_counts_shapes_and_2f_sensitivity():
    """Verify R7conv (n_history=2, +4,096 params vs R6conv), R6conv (n_history=1), and x_prev sensitivity."""
    m6 = SpatialWorldModelV7(size="R6conv", n_history=1)
    m7 = SpatialWorldModelV7(size="R7conv", n_history=2)
    p6 = m6.param_counts()
    p7 = m7.param_counts()
    assert p6["model_total"] == 2_688_963, f"Unexpected R6conv param count: {p6}"
    assert p7["model_total"] == p6["model_total"] + 4_096, f"Expected exactly +4,096 params, got {p7['model_total'] - p6['model_total']}"
    assert p7["encoder"] == p6["encoder"] and p7["decoder"] == p6["decoder"] and p7["action_emb"] == p6["action_emb"]

    torch.manual_seed(7)
    m = SpatialWorldModelV7(size="tiny", n_history=2).eval()
    x_prev_a = torch.rand(3, 16, 16, 3)
    x_prev_b = torch.rand(3, 16, 16, 3)
    x0 = torch.rand(3, 16, 16, 3)
    act = torch.tensor([1, 2, 3], dtype=torch.long)

    z_pa = m.encode(x_prev_a)
    z_pb = m.encode(x_prev_b)
    z0 = m.encode(x0)
    assert z0.shape == (3, m.latent_ch, 16, 16)
    assert m.decode(z0).shape == (3, 16, 16, 3)

    # Distinct x_prev MUST change imagine_step output (2-frame history is genuinely wired!)
    zn_a = m.imagine_step(z0, act, z_prev=z_pa, wm_grad=True)
    zn_b = m.imagine_step(z0, act, z_prev=z_pb, wm_grad=True)
    assert float((zn_a - zn_b).detach().abs().max()) > 1e-4, "n_history=2 ignored z_prev!"

    # Distinct actions MUST change output
    zn_l = m.imagine_step(z0, torch.full((3,), 1, dtype=torch.long), z_prev=z_pa, wm_grad=True)
    zn_r = m.imagine_step(z0, torch.full((3,), 2, dtype=torch.long), z_prev=z_pa, wm_grad=True)
    assert float((zn_l - zn_r).detach().abs().max()) > 1e-4

    # Missing z_prev / x_prev on n_history=2 MUST raise ValueError
    for fn in (
        lambda: m.imagine_step(z0, act, z_prev=None),
        lambda: m.rollout(x0, act[:, None], x_prev=None),
    ):
        raised = False
        try:
            fn()
        except ValueError:
            raised = True
        assert raised, "n_history=2 failed to reject missing previous frame/latent"


def test_3_strictly_k1_train_loss_and_encoder_protected():
    """Training loss uses strictly k=1 real transitions; dynamics never leaks grad to encoder (incl. via x_prev)."""
    sig = inspect.signature(compute_train_step_loss)
    assert list(sig.parameters.keys())[:5] == ["model", "x_prev", "x_t", "act", "x_next"]

    torch.manual_seed(42)
    m = SpatialWorldModelV7(size="tiny", n_history=2)
    x_prev = torch.rand(4, 16, 16, 3)
    x_t = torch.rand(4, 16, 16, 3)
    x_n = torch.rand(4, 16, 16, 3)
    act = torch.tensor([1, 2, 3, 4], dtype=torch.long)

    # Pure imagination loss (l_rec omitted) MUST put ZERO grad on encoder
    z_t = m.encode(x_t)
    with torch.no_grad():
        z_prev_det = m.encode(x_prev)
    x_rec_t = m.decode(z_t)
    z_n = m.imagine_step(z_t.detach(), act, z_prev=z_prev_det, wm_grad=True)
    x_img_res = x_t + (m.decode(z_n) - x_rec_t.detach())
    l_img = ((x_img_res - x_n) ** 2).mean()
    m.zero_grad(set_to_none=True)
    l_img.backward()
    for name, p in m.encoder.named_parameters():
        assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"Imagination leaked grad to encoder.{name}"
    assert m.action_emb.weight.grad is not None and float(m.action_emb.weight.grad.norm()) > 0.0

    # Joint step-0 loss puts finite, non-zero grads on encoder, decoder, action_emb, and dynamics
    m.zero_grad(set_to_none=True)
    loss, met, z_det = compute_train_step_loss(m, x_prev, x_t, act, x_n)
    assert torch.isfinite(loss), f"Non-finite loss: {met}"
    loss.backward()
    assert float(m.action_emb.weight.grad.norm()) > 0.0
    assert float(m.encoder.conv1.weight.grad.norm()) > 0.0
    assert float(m.decoder.conv2.weight.grad.norm()) > 0.0
    assert float(m.dynamics.in_proj.weight.grad.norm()) > 0.0
    assert float(m.dynamics.out_conv.weight.grad.norm()) > 0.0
    assert not z_det.requires_grad


def test_4a_history_rule_only_xtm1_and_xt_real_nan_poison_plain_and_reencode():
    """History rule 1: ONLY x_{t-1} and x_t may be real. NaN-poison x_{t-2} and x_{t+1..t+k-1}
    in BOTH `plain` AND `reencode` rollout modes and verify bit-identical finite predictions."""
    torch.manual_seed(11)
    m = SpatialWorldModelV7(size="tiny", n_history=2).eval()
    rng = np.random.default_rng(77)

    # 8-frame episodes (t = 0..7):
    # - Window at t=2 with k=5 predicts t=7 from real (t=1, t=2).
    #   Poison BOTH earlier frame t=0 (x_{t-2}) AND all intermediate future frames t=3,4,5,6 with NaN!
    n_eps = 16
    frames_clean, actions, eid, wid, tid = [], [], [], [], []
    for e in range(n_eps):
        frames_clean.append(rng.uniform(0.1, 0.9, size=(8, 16, 16, 3)).astype(np.float32))
        actions.append(rng.integers(0, 7, size=(7,), dtype=np.int64))
        eid.append(np.full(8, e, dtype=np.int64))
        wid.append(np.full(8, 1000 + e, dtype=np.int64))
        tid.append(np.arange(8, dtype=np.int64))

    ev_clean = {
        "frames": np.concatenate(frames_clean, axis=0),
        "actions": np.concatenate(actions, axis=0),
        "episode_id": np.concatenate(eid),
        "world_id": np.concatenate(wid),
        "t_index": np.concatenate(tid),
    }

    # Build poisoned copy targeting the t=2 -> t=7 window (only frames t=1 and t=2 are allowed real!)
    fr_poison = ev_clean["frames"].copy()
    for e in range(n_eps):
        fr_poison[e * 8 + 0] = np.nan        # t-2 MUST NOT be read
        fr_poison[e * 8 + 3 : e * 8 + 7] = np.nan  # t+1..t+4 MUST NOT be read
    ev_poison = dict(ev_clean, frames=fr_poison)

    xi5, _, _, _, ti5 = scorer.windows(ev_clean, 5)
    sel_t2 = ti5 == 2
    assert int(sel_t2.sum()) == n_eps

    for mode in ("plain", "reencode"):
        p_clean, _, ps_clean, _, _ = rollout_eval_predictions(
            m, ev_clean, torch.device("cpu"), rollout=mode, batch_size=8, horizons=(5,), compute_ceiling=False
        )
        # Note: windows at t=0 and t=1 touch t=0 (NaN) or t=1 (clean)/t=2 (clean),
        # so restrict comparison to t=2 windows (which are independent per sample in the batch!)
        # Even stronger: run rollout_eval_predictions on an episode slice where ONLY t=2 window exists,
        # OR verify every t=2 output row is finite and bit-identical!
        # Since no BatchNorm exists, batch rows are 100% independent — still verify exact slice!
        p_poison, _, ps_poison, _, _ = rollout_eval_predictions(
            m, ev_poison, torch.device("cpu"), rollout=mode, batch_size=8, horizons=(5,), compute_ceiling=False
        )
        assert np.isfinite(p_poison[5][sel_t2]).all(), f"[{mode}] Poisoned t-2 or t+1..t+4 leaked NaN into k=5 real rollout!"
        assert np.isfinite(ps_poison[5][sel_t2]).all(), f"[{mode}] Poisoned t-2 or t+1..t+4 leaked NaN into k=5 shuf rollout!"
        assert np.array_equal(p_clean[5][sel_t2], p_poison[5][sel_t2]), f"[{mode}] k=5 real rollout differed under NaN poison!"
        assert np.array_equal(ps_clean[5][sel_t2], ps_poison[5][sel_t2]), f"[{mode}] k=5 shuf rollout differed under NaN poison!"

    # Also test 6-frame episodes (k=5 has ONLY t=0 -> t=5 windows) where ALL intermediate frames t=1,2,3,4 are NaN
    ev6_clean = {
        "frames": np.concatenate([f[:6] for f in frames_clean], axis=0),
        "actions": np.concatenate([a[:5] for a in actions], axis=0),
        "episode_id": np.concatenate([np.full(6, e, dtype=np.int64) for e in range(n_eps)]),
        "world_id": np.concatenate([np.full(6, 1000 + e, dtype=np.int64) for e in range(n_eps)]),
        "t_index": np.concatenate([np.arange(6, dtype=np.int64) for _ in range(n_eps)]),
    }
    fr6_p = ev6_clean["frames"].copy()
    for e in range(n_eps):
        fr6_p[e * 6 + 1 : e * 6 + 5] = np.nan
    ev6_poison = dict(ev6_clean, frames=fr6_p)

    for mode in ("plain", "reencode"):
        pc, _, psc, _, _ = rollout_eval_predictions(
            m, ev6_clean, torch.device("cpu"), rollout=mode, batch_size=8, horizons=(5,), compute_ceiling=False
        )
        pp, _, psp, _, _ = rollout_eval_predictions(
            m, ev6_poison, torch.device("cpu"), rollout=mode, batch_size=8, horizons=(5,), compute_ceiling=False
        )
        assert np.isfinite(pp[5]).all() and np.isfinite(psp[5]).all(), f"[{mode}] NaN leaked into t=0 k=5 rollout!"
        assert np.array_equal(pc[5], pp[5]) and np.array_equal(psc[5], psp[5])

    # Verify k=1 plain and reencode are BIT-IDENTICAL, while k=5 differs (snap active)
    tr_syn = scorer.make_synthetic_split([0, 1, 2, 3], 40, seed=1)
    ev_syn = scorer.make_synthetic_split([1000 + i for i in range(4)], 40, seed=2)
    res_p, preds_p = evaluate_model(m, tr_syn, ev_syn, torch.device("cpu"), batch_size=32, rollout="plain", include_2f_baselines=False)
    res_r, preds_r = evaluate_model(m, tr_syn, ev_syn, torch.device("cpu"), batch_size=32, rollout="reencode", include_2f_baselines=True)
    assert np.array_equal(preds_p[1], preds_r[1]), "k=1 must be bit-identical between plain and reencode!"
    assert float(np.abs(preds_p[5] - preds_r[5]).max()) > 1e-4, "k=5 reencode unexpectedly matched plain!"
    assert res_r["rollout_mode"] == "reencode" and res_p["rollout_mode"] == "plain"
    assert "diag_non_wake_interactions" in res_r and "diag_baselines_2f" in res_r

    # Verify ceiling_abs_E_over_B equals exact decode(encode(x_{t+1})) error / B
    xi1 = scorer.windows(ev_syn, 1)[0]
    x1_t = torch.from_numpy(ev_syn["frames"][xi1 + 1].astype(np.float32))
    with torch.no_grad():
        c_abs_direct = m.decode(m.encode(x1_t)).double().numpy()
    y1 = ev_syn["frames"][xi1 + 1].astype(np.float64)
    exp_ceil_abs = float(((c_abs_direct - y1) ** 2).sum() / res_r["k1"]["B"])
    assert abs(res_r["k1"]["ceiling_abs_E_over_B"] - exp_ceil_abs) < 1e-6


def test_4b_history_rule_step2_onward_uses_own_outputs_plain_and_reencode():
    """History rule 2: from rollout step 2 onward (0-indexed step >= 2, i.e., t+2->t+3...),
    BOTH history entries (z_prev, z) passed into dynamics are strictly the model's own outputs,
    and step 1 already uses model output z_hat_1 with real z_0."""
    torch.manual_seed(19)
    m = SpatialWorldModelV7(size="tiny", n_history=2).eval()
    x_prev = torch.rand(3, 16, 16, 3)
    x0 = torch.rand(3, 16, 16, 3)
    acts5 = torch.tensor([[1, 2, 3, 4, 5], [2, 2, 1, 0, 3], [4, 3, 2, 1, 6]], dtype=torch.long)

    for mode in ("plain", "reencode"):
        recorded_inputs = []
        orig_fwd = m.dynamics.forward

        def _spy_forward(z_in, act_emb, z_prev_in=None, _orig=orig_fwd, _rec=recorded_inputs):
            _rec.append((z_prev_in.detach().clone(), z_in.detach().clone()))
            return _orig(z_in, act_emb, z_prev_in)

        m.dynamics.forward = _spy_forward
        try:
            with torch.no_grad():
                out = m.rollout(x0, acts5, x_prev=x_prev, rollout_mode=mode, wm_grad=False)
        finally:
            m.dynamics.forward = orig_fwd

        assert len(recorded_inputs) == 5
        # Independently step by hand and check EVERY step's (z_prev, z) matches bit-for-bit!
        with torch.no_grad():
            z_m1 = m.encode(x_prev)
            z0 = m.encode(x0)
            dec0 = m.decode(z0)
            hist_chain = [z_m1, z0]
            for stp in range(5):
                exp_zp, exp_z = hist_chain[-2], hist_chain[-1]
                got_zp, got_z = recorded_inputs[stp]
                assert torch.equal(got_zp, exp_zp), f"[{mode}] step {stp} z_prev mismatch"
                assert torch.equal(got_z, exp_z), f"[{mode}] step {stp} z mismatch"
                z_next = m.imagine_step(exp_z, acts5[:, stp], z_prev=exp_zp, wm_grad=False)
                if mode == "reencode" and stp < 4:
                    pred_s = x0 + (m.decode(z_next) - dec0)
                    z_feed = m.encode(pred_s.clamp(0.0, 1.0))
                else:
                    z_feed = z_next
                hist_chain.append(z_feed)
            assert torch.equal(out["pred_abs"], m.decode(hist_chain[-1]))
            assert torch.equal(out["pred_res"], x0 + (m.decode(hist_chain[-1]) - dec0))

        # Perturb ONLY a_0 (step 0 action) -> MUST change BOTH z_prev and z at step 2 (proving step 2's
        # history comes strictly from the model's own step-0/step-1 outputs!)
        acts5_alt = acts5.clone()
        acts5_alt[:, 0] = (acts5_alt[:, 0] + 1) % 7
        rec_alt = []
        m.dynamics.forward = lambda z_in, ae, zp=None, _orig=orig_fwd, _r=rec_alt: (
            _r.append((zp.detach().clone(), z_in.detach().clone())),
            _orig(z_in, ae, zp),
        )[1]
        try:
            with torch.no_grad():
                m.rollout(x0, acts5_alt, x_prev=x_prev, rollout_mode=mode, wm_grad=False)
        finally:
            m.dynamics.forward = orig_fwd

        # Step 0 inputs unchanged; Step 1 z_prev (z0) unchanged, z_1 changed; Step 2 BOTH z_prev & z changed!
        assert torch.equal(recorded_inputs[0][0], rec_alt[0][0]) and torch.equal(recorded_inputs[0][1], rec_alt[0][1])
        assert torch.equal(recorded_inputs[1][0], rec_alt[1][0])
        assert float((recorded_inputs[1][1] - rec_alt[1][1]).abs().max()) > 1e-4
        assert float((recorded_inputs[2][0] - rec_alt[2][0]).abs().max()) > 1e-4, f"[{mode}] step 2 z_prev did not depend on model step-0 output!"
        assert float((recorded_inputs[2][1] - rec_alt[2][1]).abs().max()) > 1e-4, f"[{mode}] step 2 z did not depend on model outputs!"


def test_4c_history_rule_never_crosses_episode_or_world_boundary():
    """History rule 3: x_{t-1} NEVER crosses an episode boundary (same world) OR world boundary;
    at episode start (t=0), x_{-1} = x_0."""
    torch.manual_seed(23)
    m = SpatialWorldModelV7(size="tiny", n_history=2).eval()
    rng = np.random.default_rng(101)

    # 3 consecutive episodes:
    #   ep 0 (world 1000, len 7) -> ends with frame index 6
    #   ep 1 (world 1000, same world new episode, len 7) -> starts at index 7 (t=0)
    #   ep 2 (world 1001, new world new episode, len 7) -> starts at index 14 (t=0)
    ep_specs = [(0, 1000, 7), (1, 1000, 7), (2, 1001, 7)]
    frames_clean, actions, eid, wid, tid = [], [], [], [], []
    for e_id, w_id, L in ep_specs:
        frames_clean.append(rng.uniform(0.1, 0.9, size=(L, 16, 16, 3)).astype(np.float32))
        actions.append(rng.integers(0, 7, size=(L - 1,), dtype=np.int64))
        eid.append(np.full(L, e_id, dtype=np.int64))
        wid.append(np.full(L, w_id, dtype=np.int64))
        tid.append(np.arange(L, dtype=np.int64))

    split_clean = {
        "frames": np.concatenate(frames_clean, axis=0),
        "actions": np.concatenate(actions, axis=0),
        "episode_id": np.concatenate(eid),
        "world_id": np.concatenate(wid),
        "t_index": np.concatenate(tid),
    }
    # Poison the LAST frame of ep 0 (idx 6) and ep 1 (idx 13) with NaN!
    fr_edge_nan = split_clean["frames"].copy()
    fr_edge_nan[6] = np.nan   # immediately precedes ep 1 t=0 (same world)
    fr_edge_nan[13] = np.nan  # immediately precedes ep 2 t=0 (different world)
    split_edge_nan = dict(split_clean, frames=fr_edge_nan)

    for k in (1, 3, 5):
        xi, ai, wi, ei, ti = scorer.windows(split_clean, k)
        h_idx = prev_frame_indices(split_clean, xi, ti)
        assert np.array_equal(split_clean["episode_id"][h_idx], split_clean["episode_id"][xi])
        assert np.array_equal(split_clean["world_id"][h_idx], split_clean["world_id"][xi])
        starts_mask = ti == 0
        assert int(starts_mask.sum()) == 3
        assert np.array_equal(h_idx[starts_mask], xi[starts_mask])

        # Verify actual predictions at t=0 of ep 1 and ep 2 are finite, bit-identical despite NaN prior
        # episode end, AND bit-identical to explicit rollout(x0, acts_k, x_prev=x0) in BOTH modes!
        for mode in ("plain", "reencode"):
            p_c, _, _, _, _ = rollout_eval_predictions(
                m, split_clean, torch.device("cpu"), rollout=mode, batch_size=16, horizons=(k,), compute_ceiling=False
            )
            p_n, _, _, _, _ = rollout_eval_predictions(
                m, split_edge_nan, torch.device("cpu"), rollout=mode, batch_size=16, horizons=(k,), compute_ceiling=False
            )
            assert np.isfinite(p_n[k][starts_mask]).all(), f"[{mode}] k={k} boundary NaN leaked across episode/world!"
            assert np.array_equal(p_c[k][starts_mask], p_n[k][starts_mask])

            # Direct check against explicit x_prev = x0 (atol=1e-5 across differing batch sizes, bit-equal at B=1)
            ak = torch.from_numpy(scorer.action_values(split_clean["actions"], ai[starts_mask], k).astype(np.int64))
            x0_s = torch.from_numpy(split_clean["frames"][xi[starts_mask]].astype(np.float32))
            direct = m.rollout(x0_s, ak, x_prev=x0_s, rollout_mode=mode, wm_grad=False)["pred_res"].double().numpy()
            assert np.allclose(p_n[k][starts_mask], direct, atol=1e-5), f"[{mode}] k={k} mismatch vs explicit x_prev=x0"
            p_b1, _, _, _, _ = rollout_eval_predictions(
                m, split_edge_nan, torch.device("cpu"), rollout=mode, batch_size=1, horizons=(k,), compute_ceiling=False
            )
            for row_j in range(len(x0_s)):
                d1 = m.rollout(x0_s[row_j : row_j + 1], ak[row_j : row_j + 1], x_prev=x0_s[row_j : row_j + 1], rollout_mode=mode, wm_grad=False)["pred_res"].double().numpy()
                assert np.array_equal(p_b1[k][starts_mask][row_j : row_j + 1], d1)

    # Also verify prev_frame_indices raises loudly if given a corrupted ti that would cross a boundary!
    xi1, _, _, _, ti1 = scorer.windows(split_clean, 1)
    bad_ti = ti1.copy()
    bad_ti[ti1 == 0] = 1  # forces idx=7 (ep 1 start) to look back to idx=6 (ep 0 end)
    raised = False
    try:
        prev_frame_indices(split_clean, xi1, bad_ti)
    except RuntimeError:
        raised = True
    assert raised, "prev_frame_indices failed to reject episode/world boundary crossing!"


def test_5_wm_grad_false_anti_wishful_thinking_plain_and_reencode():
    """Verify wm_grad=False leaks ZERO grad to every model param & real frames for both plain & reencode."""
    torch.manual_seed(17)
    m = SpatialWorldModelV7(size="tiny", n_history=2)
    x_prev = torch.rand(3, 16, 16, 3)
    x0 = torch.rand(3, 16, 16, 3)
    z_prev = m.encode(x_prev)
    z0 = m.encode(x0)

    # Integer action IDs -> detached output
    m.zero_grad(set_to_none=True)
    z_int = m.imagine_step(
        z0.detach().clone().requires_grad_(True),
        torch.tensor([1, 2, 3], dtype=torch.long),
        z_prev=z_prev.detach().clone().requires_grad_(True),
        wm_grad=False,
    )
    assert not z_int.requires_grad

    # Continuous float action emb -> grad ONLY on a_emb, ZERO on every model param, z0, and z_prev
    m.zero_grad(set_to_none=True)
    z_leaf = z0.detach().clone().requires_grad_(True)
    zp_leaf = z_prev.detach().clone().requires_grad_(True)
    a_emb = torch.randn(3, m.cond_dim, requires_grad=True)
    z_flt = m.imagine_step(z_leaf, a_emb, z_prev=zp_leaf, wm_grad=False)
    z_flt.pow(2).mean().backward()
    assert a_emb.grad is not None and float(a_emb.grad.norm()) > 0.0
    assert z_leaf.grad is None or float(z_leaf.grad.abs().max()) == 0.0
    assert zp_leaf.grad is None or float(zp_leaf.grad.abs().max()) == 0.0
    for name, p in m.named_parameters():
        assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"imagine_step wm_grad=False leaked to {name}"

    # Multi-step rollout(wm_grad=False) in BOTH plain and reencode modes
    for mode in ("plain", "reencode"):
        m.zero_grad(set_to_none=True)
        x0_leaf = x0.detach().clone().requires_grad_(True)
        xp_leaf = x_prev.detach().clone().requires_grad_(True)
        a_seq = torch.randn(3, 3, m.cond_dim, requires_grad=True)
        ro = m.rollout(x0_leaf, a_seq, x_prev=xp_leaf, rollout_mode=mode, wm_grad=False)
        ro["pred_res"].pow(2).mean().backward()
        assert a_seq.grad is not None and float(a_seq.grad[:, 0].norm()) > 0.0 and float(a_seq.grad[:, 2].norm()) > 0.0
        assert x0_leaf.grad is None or float(x0_leaf.grad.abs().max()) == 0.0
        assert xp_leaf.grad is None or float(xp_leaf.grad.abs().max()) == 0.0
        for name, p in m.named_parameters():
            assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"[{mode}] rollout wm_grad=False leaked to {name}"


def test_6_batch1_finite_and_ckpt_roundtrip_v6_and_v7():
    """Verify B=1 finite loss/grads/latent_stats, V7 round-trip, and V6 (n_history=1) compat."""
    torch.manual_seed(42)
    m = SpatialWorldModelV7(size="tiny", n_history=2)
    x_p = torch.rand(1, 16, 16, 3)
    x_t = torch.rand(1, 16, 16, 3)
    x_n = torch.rand(1, 16, 16, 3)
    act = torch.tensor([2], dtype=torch.long)
    loss, met, z_det = compute_train_step_loss(m, x_p, x_t, act, x_n)
    assert torch.isfinite(loss), f"Non-finite B=1 loss: {met}"
    loss.backward()
    for name, p in m.named_parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all(), f"Non-finite grad in {name} at B=1"
    ls = m.latent_stats(z_det)
    assert np.isfinite(ls["static_rms"]) and np.isfinite(ls["spread_rms"]) and np.isfinite(ls["burial_ratio"])

    with tempfile.TemporaryDirectory() as td:
        ck_path = os.path.join(td, "m7.pt")
        m.eval()
        torch.save({"model": m.state_dict(), "meta": {"arch": ARCH_TAG, "size": "tiny", "n_history": 2}}, ck_path)
        torch.manual_seed(999)
        m2 = SpatialWorldModelV7(size="tiny", n_history=2).eval()
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        m2.load_state_dict(ck["model"], strict=True)
        xp = torch.rand(2, 16, 16, 3)
        x0 = torch.rand(2, 16, 16, 3)
        acts = torch.tensor([[1, 2, 3], [4, 1, 2]], dtype=torch.long)
        for mode in ("plain", "reencode"):
            assert torch.equal(
                m.rollout(x0, acts, x_prev=xp, rollout_mode=mode)["pred_res"],
                m2.rollout(x0, acts, x_prev=xp, rollout_mode=mode)["pred_res"],
            )


def test_7_sealed_split_guard_and_symlink():
    """Verify sealed_test.npz and symlinks to it are blocked unless BOTH --eval-only AND --allow-sealed."""
    for eo, als in ((False, False), (True, False), (False, True)):
        raised = False
        try:
            guard_sealed_path("data/sealed_test.npz", eval_only=eo, allow_sealed=als)
        except RuntimeError:
            raised = True
        assert raised, f"Expected RuntimeError for eval_only={eo}, allow_sealed={als}"

    raised_wrong = False
    try:
        guard_sealed_path("../wm-harness/data/heldout.npz", eval_only=True, allow_sealed=True)
    except RuntimeError:
        raised_wrong = True
    assert raised_wrong

    with tempfile.TemporaryDirectory() as td:
        real_sealed = os.path.join(td, "sealed_test.npz")
        with open(real_sealed, "wb") as f:
            f.write(b"dummy")
        alias = os.path.join(td, "innocent_dev.npz")
        os.symlink(real_sealed, alias)
        for eo, als in ((False, False), (True, True)):
            raised = False
            try:
                guard_sealed_path(alias, eval_only=eo, allow_sealed=als)
            except RuntimeError:
                raised = True
            assert raised


def test_8_mps_power_guard_and_indexed_mps():
    """Verify MPS power guard (AC or >=35% battery) AND that torch.device('mps:0').type == 'mps'."""
    assert torch.device("mps:0").type == "mps"
    on_ac, pct = check_mps_power("Now drawing from 'AC Power'\n -InternalBattery-0\t24%; charging;\n")
    assert on_ac is True and pct == 24
    on_ac2, pct2 = check_mps_power("Now drawing from 'Battery Power'\n -InternalBattery-0\t35%; discharging;\n")
    assert on_ac2 is False and pct2 == 35
    for low_txt in (
        "Now drawing from 'Battery Power'\n -InternalBattery-0\t34%; discharging;\n",
        "Now drawing from 'Battery Power'\n -InternalBattery-0\t24%; discharging;\n",
        "Now drawing from 'Battery Power'\n",
    ):
        raised = False
        try:
            check_mps_power(low_txt)
        except RuntimeError:
            raised = True
        assert raised


def test_9_incomplete_run_nonfinite_grad_and_ckpt_validation():
    """Verify done < steps fails loudly, non-finite grad aborts before opt.step(), and --eval-only rejects mismatched arch/size."""
    p = torch.nn.Parameter(torch.ones(4))
    w_before = p.detach().clone()
    for bad_val in (float("nan"), float("inf")):
        p.grad = torch.tensor([1.0, bad_val, 0.0, 0.0])
        raised = False
        try:
            clip_and_check_grad_norm([p], 1.0)
        except RuntimeError:
            raised = True
        assert raised and torch.equal(p.detach(), w_before)

    with tempfile.TemporaryDirectory() as td:
        tr = scorer.make_synthetic_split([0, 1], 30, seed=5)
        ev = scorer.make_synthetic_split([1000, 1001], 30, seed=6)
        tr_p = os.path.join(td, "tr.npz")
        ev_p = os.path.join(td, "ev.npz")
        out_d = os.path.join(td, "out")
        np.savez(tr_p, **tr)
        np.savez(ev_p, **ev)
        proc = subprocess.run(
            [
                sys.executable, "-B", str(HERE / "train_v7.py"),
                "--size", "tiny", "--device", "cpu",
                "--steps", "50", "--batch", "4", "--max-minutes", "1e-6",
                "--skip-disk-check", "--train-data", tr_p, "--eval-data", ev_p, "--out", out_d,
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode != 0
        assert "INCOMPLETE RUN" in proc.stderr or "INCOMPLETE RUN" in proc.stdout
        assert not os.path.exists(os.path.join(out_d, "model.pt"))

        # --eval-only rejects mismatched n_history (R6 arch loaded as n_history=2) BEFORE loading eval_data!
        m6 = SpatialWorldModelV7(size="tiny", n_history=1)
        r6_ck = os.path.join(td, "r6_tiny.pt")
        torch.save({"model": m6.state_dict(), "meta": {"arch": ARCH_TAG_BY_HIST[1], "size": "tiny"}}, r6_ck)
        proc2 = subprocess.run(
            [
                sys.executable, "-B", str(HERE / "train_v7.py"),
                "--size", "tiny", "--n-history", "2", "--device", "cpu", "--eval-only", r6_ck,
                "--skip-disk-check", "--train-data", tr_p, "--eval-data", os.path.join(td, "nonexistent.npz"), "--out", out_d,
            ],
            capture_output=True, text=True,
        )
        assert proc2.returncode != 0
        assert "Checkpoint arch" in proc2.stderr, f"Expected arch mismatch before eval_data load! stderr={proc2.stderr}"

        guard_calls = []

        def _record_guard(path, eval_only, allow_sealed):
            guard_calls.append((path, eval_only, allow_sealed))

        eval_sentinel = os.path.join(td, "must_not_be_opened.npz")
        old_argv = sys.argv
        sys.argv = [
            "train_v7.py", "--size", "tiny", "--n-history", "2", "--device", "cpu",
            "--eval-only", os.path.join(td, "missing.pt"), "--skip-disk-check",
            "--train-data", tr_p, "--eval-data", eval_sentinel, "--out", out_d,
        ]
        try:
            with patch.object(train_v7, "guard_sealed_path", side_effect=_record_guard), patch.object(
                train_v7.torch, "load", side_effect=RuntimeError("checkpoint-first sentinel")
            ):
                try:
                    train_v7.main()
                except RuntimeError as exc:
                    assert str(exc) == "checkpoint-first sentinel"
                else:
                    raise AssertionError("Expected patched checkpoint load to fail")
        finally:
            sys.argv = old_argv
        assert guard_calls == [(tr_p, False, False)], f"Eval data guard ran before checkpoint validation: {guard_calls}"


def test_10_scorer_selftest_and_withlock_sha():
    """Verify scorer selftest and lock-safe withlock.sh (sha 77e3ac48...)."""
    rep = scorer.run_selftest()
    assert rep["selftest"] == "ALL_PASS"
    assert rep["check1_rung1_verdict"] == "PASS"
    assert rep["check2_rung1_verdict"] == "FAIL"

    wl = HERE / "withlock.sh"
    assert sha256_file(str(wl)) == "77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa"
    with tempfile.TemporaryDirectory() as td:
        lock_f = os.path.join(td, "test.lock")
        env = dict(os.environ, PREMONITION_MPS_LOCK=lock_f, PREMONITION_LOCK_POLL="1")
        log1 = os.path.join(td, "fail.log")
        r1 = subprocess.run(
            ["/bin/zsh", str(wl), log1, sys.executable, "-u", "-c", "import sys; print('err'); sys.exit(7)"],
            env=env, capture_output=True, text=True,
        )
        assert r1.returncode == 7 and not os.path.exists(lock_f)

        log2 = os.path.join(td, "term.log")
        p = subprocess.Popen(
            ["/bin/zsh", str(wl), log2, sys.executable, "-u", "-c", "import time; print('go', flush=True); time.sleep(30)"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for _ in range(50):
            if os.path.exists(lock_f):
                break
            time.sleep(0.05)
        assert os.path.exists(lock_f)
        p.send_signal(signal.SIGTERM)
        assert p.wait(timeout=5) != 0 and not os.path.exists(lock_f)


def test_11_std_gate_saved_rank6_real_rescore_fail():
    """Stored end-to-end Rank 6 re-scores remain FAIL with explicit strike classification."""
    for seed in (42, 43):
        new_score = json.loads((HERE / f"rank6_rescore_s{seed}.json").read_text())
        assert new_score["scorer_version"] == "forecast7-v2-rung1-n200_or_neff10"
        assert new_score["rung1_verdict"] == "FAIL"
        assert new_score["rank7_verdict"] == "FAIL"
        assert new_score["strike_class"] == "LINE"
        assert "std_high_count_or_concentrated" in new_score["strike_reasons"]
        assert new_score["k1"]["std_gate"]["individual_fail_actions"] == [5]
        assert new_score["k1"]["std_gate"]["pool"]["actions"] == [8, 9]

        candidates = (
            HERE.parent / "forecast6" / f"run_r6_s{seed}" / "score_dev.json",
            Path.home() / "learner-ops" / "seven-problems-m3" / "PROBLEM-7" / "wm6" / f"run_r6_s{seed}" / "score_dev.json",
        )
        old_score = json.loads(next(p for p in candidates if p.exists()).read_text())
        assert old_score["scorer_version"] == "forecast5-v3-rung1"
        assert old_score["std_ok"] is False
        assert old_score["rung1_verdict"] == "FAIL"
        assert abs(old_score["k5"]["E_over_B"] - new_score["k5"]["E_over_B"]) < 1e-12


def test_12_std_gate_oracle_passes_collapsed_fails():
    """The adopted gate pools one-event rare actions but still rejects collapsed high-count actions."""
    rng = np.random.default_rng(20261125)
    changes, actions = [], []
    for q in (1, 2, 3, 4):
        changes.append(rng.normal(0.0, 0.06, (250, 768)))
        actions.append(np.full(250, q, dtype=np.int64))
    changes.append(rng.normal(0.0, 0.025, (250, 768)))
    actions.append(np.full(250, 5, dtype=np.int64))
    changes.append(rng.normal(0.0, 0.15, (64, 768)))
    actions.append(np.full(64, 6, dtype=np.int64))
    for q, amp in ((8, 0.40), (13, 0.16)):
        y = rng.normal(0.0, 0.004, (60, 768))
        y[0] = rng.normal(0.0, amp, 768)
        changes.append(y)
        actions.append(np.full(60, q, dtype=np.int64))
    dY = np.concatenate(changes)
    a0 = np.concatenate(actions)

    oracle = rng.normal(0.0, 0.003, dY.shape)
    for q in (1, 2, 3, 4, 5, 6):
        oracle[a0 == q] = 0.90 * dY[a0 == q]
    table_event = np.flatnonzero(a0 == 8)[0]
    oracle[table_event] = 0.70 * dY[table_event]
    oracle_gate = scorer.decide_std_gate(scorer.summarize_std_by_action(oracle, dY, a0))
    assert oracle_gate["old_ok"] is False
    assert oracle_gate["old_fail_actions"] == [13]
    assert oracle_gate["amended_ok"] is True
    assert oracle_gate["individual_fail_actions"] == []
    assert oracle_gate["pool"]["actions"] == [8, 13]
    assert 0.25 <= oracle_gate["pool"]["ratio"] <= 2.0

    collapsed = rng.normal(0.0, 0.003, dY.shape)
    for q in (1, 2, 3, 4, 6):
        collapsed[a0 == q] = 0.90 * dY[a0 == q]
    collapsed_gate = scorer.decide_std_gate(scorer.summarize_std_by_action(collapsed, dY, a0))
    assert collapsed_gate["old_ok"] is False
    assert collapsed_gate["amended_ok"] is False
    assert collapsed_gate["individual_fail_actions"] == [5]


def test_12b_std_gate_all_rare_oracle_passes():
    """All-rare data (no individually gated action): pool alone decides; oracle PASS, collapse FAIL."""
    rng = np.random.default_rng(20261126)
    changes, actions = [], []
    for q, amp in ((8, 0.40), (13, 0.16)):
        y = rng.normal(0.0, 0.004, (60, 768))
        y[0] = rng.normal(0.0, amp, 768)
        changes.append(y)
        actions.append(np.full(60, q, dtype=np.int64))
    dY = np.concatenate(changes)
    a0 = np.concatenate(actions)
    gate = scorer.decide_std_gate(scorer.summarize_std_by_action(dY.copy(), dY, a0))
    assert gate["individual_ratios"] == {}
    assert gate["pool"] is not None and gate["pool"]["active"]
    assert gate["amended_ok"] is True
    collapsed = rng.normal(0.0, 0.003, dY.shape)
    cgate = scorer.decide_std_gate(scorer.summarize_std_by_action(collapsed, dY, a0))
    assert cgate["amended_ok"] is False
    quiet = rng.normal(0.0, 0.001, dY.shape)
    qgate = scorer.decide_std_gate(scorer.summarize_std_by_action(quiet * 0.5, quiet, a0))
    assert qgate["amended_ok"] is False  # nothing active anywhere: never a vacuous pass

def test_13_scorer_diff_only_amended_logic():
    """Only version, std gate, PARTIAL exclusivity, and strike fields differ from forecast5."""
    old_path = next(
        p for p in (
            HERE.parent / "forecast5" / "scorer.py",
            Path.home() / "learner-ops" / "seven-problems-m3" / "PROBLEM-7" / "wm5" / "scorer.py",
            Path.home() / "learner-ops" / "seven-problems-m3" / "PROBLEM-7" / "wm6" / "scorer.py",
        ) if p.exists()
    )
    new_path = HERE / "scorer.py"
    old_src = old_path.read_text()
    new_src = new_path.read_text()
    assert sha256_file(str(old_path)) == FORECAST5_SCORER_SHA256
    assert sha256_file(str(new_path)) == PINNED_SCORER_SHA256

    normalized = new_src
    for name in ("summarize_std_by_action", "decide_std_gate", "classify_strike"):
        tree = ast.parse(normalized)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        lines = normalized.splitlines(keepends=True)
        start = node.lineno - 1
        while start > 0 and lines[start - 1].strip() == "":
            start -= 1
        del lines[start:node.end_lineno]
        normalized = "".join(lines)
    normalized = normalized.replace('"forecast7-v2-rung1-n200_or_neff10"', '"forecast5-v3-rung1"', 1)
    marker = "            # Rung-1 blocked-vs-open visual terrain-displacement readout (blind to predictors)"
    old_start = old_src.index("            std_by_action = {}\n")
    old_end = old_src.index(marker, old_start)
    new_start = normalized.index("            std_by_action = summarize_std_by_action")
    new_end = normalized.index(marker, new_start)
    normalized = normalized[:new_start] + old_src[old_start:old_end] + normalized[new_end:]

    new_legacy_partial = """    partial = (
        (not full) and ok1 and ok3 and okS1 and okSb and okstd and okpc and okceil
        and (not proves_wrong) and (not ok5)
    )
"""
    old_legacy_partial = "    partial = (not full) and ok1 and okS1 and okstd and okpc and okceil and (not proves_wrong) and ((not ok3) or (not ok5))\n"
    normalized = normalized.replace(new_legacy_partial, old_legacy_partial, 1)

    new_r1_partial = """    r1_partial = (
        (not r1_full) and ok1 and ok3 and r1_b1 and r1_b3 and r1_bo
        and okS1 and okSb and r1_shuf_pool1 and okstd and okpc and okceil
        and (not proves_wrong) and ((not ok5) or (not r1_b5))
    )
"""
    old_r1_partial = """    r1_partial = (
        (not r1_full) and ok1 and r1_b1 and r1_bo and okS1 and r1_shuf_pool1
        and okstd and okpc and okceil and (not proves_wrong)
        and ((not ok3) or (not ok5) or (not r1_b3) or (not r1_b5))
    )
"""
    normalized = normalized.replace(new_r1_partial, old_r1_partial, 1)

    strike_start = normalized.index("    strike_class, strike_reasons = classify_strike(\n")
    strike_end = normalized.index("\n    res.update({\n", strike_start)
    normalized = normalized[:strike_start] + "\n" + normalized[strike_end + 1:]
    normalized = normalized.replace('        "strike_class": strike_class,\n        "strike_reasons": strike_reasons,\n', "", 1)
    assert normalized == old_src

    spec = importlib.util.spec_from_file_location("forecast5_scorer_for_diff_test", old_path)
    old_scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_scorer)
    tr = scorer.make_synthetic_split(list(range(8)), 40, seed=31)
    he = scorer.make_synthetic_split([1000 + i for i in range(16)], 40, seed=32)
    hfr = he["frames"].astype(np.float64)
    preds, shuf = {}, {}
    for k in (1, 3, 5):
        xi = scorer.windows(he, k)[0]
        preds[k] = hfr[xi + k]
        shuf[k] = hfr[xi]
    old_res = old_scorer.score_predictions(tr, he, preds, shuf)
    new_res = scorer.score_predictions(tr, he, preds, shuf)
    allowed = {
        ("scorer_version",),
        ("k1", "std_ratio_by_action"),
        ("k1", "std_ratio_old_active_and_fw_ok"),
        ("k1", "std_ratio_active_and_fw_ok"),
        ("k1", "std_gate"),
        ("std_ok",),
        ("strike_class",),
        ("strike_reasons",),
        ("verdict",),
        ("rung1_verdict",),
        ("marks", "std_ok"),
        ("rung1_marks", "std_ok"),
    }

    def _compare(a, b, path=()):
        if path in allowed:
            return
        if isinstance(a, dict):
            for key, value in a.items():
                assert key in b, f"Missing key {path + (key,)}"
                _compare(value, b[key], path + (key,))
            for key in b:
                if key not in a:
                    assert path + (key,) in allowed, f"Unexpected new key {path + (key,)}"
        else:
            assert a == b, f"Non-std mark changed at {path}: {a!r} != {b!r}"

    _compare(old_res, new_res)


def test_14_partial_exclusivity_selective_collapse_and_strikes():
    """Only a k5-only miss is PARTIAL; selective rare collapse fails; strike classes are explicit."""
    tr = scorer.make_synthetic_split(list(range(8)), 100, seed=41)
    he = scorer.make_synthetic_split([1000 + i for i in range(16)], 100, seed=42)
    hfr = he["frames"].astype(np.float64)
    preds, shuf = {}, {}
    for k in (1, 3, 5):
        xi = scorer.windows(he, k)[0]
        preds[k] = hfr[xi + k]
        shuf[k] = np.zeros_like(hfr[xi])

    base = scorer.score_predictions(tr, he, preds, shuf)
    assert base["rung1_verdict"] == "PASS" and base["strike_class"] == "NONE"

    p3 = dict(preds)
    p3[3] = np.zeros_like(preds[3])
    r3 = scorer.score_predictions(tr, he, p3, shuf)
    assert r3["verdict"] == "FAIL" and r3["rung1_verdict"] == "FAIL"
    assert r3["strike_class"] == "LINE" and "k3_accuracy_or_baseline" in r3["strike_reasons"]

    p5 = dict(preds)
    s5 = dict(shuf)
    p5[5] = np.zeros_like(preds[5])
    s5[5] = np.zeros_like(shuf[5])
    r5 = scorer.score_predictions(tr, he, p5, s5)
    assert r5["worlds_both"] == 0
    assert r5["verdict"] == "FAIL" and r5["rung1_verdict"] == "FAIL"
    assert r5["strike_class"] == "LINE" and "shuffle_or_worlds" in r5["strike_reasons"]

    p5_only = dict(preds)
    noise = np.random.default_rng(99).normal(0.0, np.sqrt(base["k5"]["B"] / preds[5].size), preds[5].shape)
    p5_only[5] = preds[5] + noise
    r5_only = scorer.score_predictions(tr, he, p5_only, shuf)
    assert r5_only["verdict"] == "PARTIAL" and r5_only["rung1_verdict"] == "PARTIAL"
    assert r5_only["strike_class"] == "NONE"

    rng = np.random.default_rng(20261126)
    changes, actions = [], []
    changes.append(rng.normal(0.0, 0.06, (250, 768)))
    actions.append(np.full(250, 1, dtype=np.int64))
    for q in (8, 13):
        y = rng.normal(0.0, 0.004, (60, 768))
        y[0] = rng.normal(0.0, 0.25, 768)
        changes.append(y)
        actions.append(np.full(60, q, dtype=np.int64))
    dY = np.concatenate(changes)
    a0 = np.concatenate(actions)
    dP = rng.normal(0.0, 0.003, dY.shape)
    dP[a0 == 1] = 0.90 * dY[a0 == 1]
    dP[a0 == 8] = 0.0
    dP[a0 == 13] = np.sqrt(2.0) * dY[a0 == 13]
    gate = scorer.decide_std_gate(scorer.summarize_std_by_action(dP, dY, a0))
    assert gate["pool"]["actions"] == [8, 13]
    assert 0.25 <= gate["pool"]["ratio"] <= 2.0
    assert gate["pool"]["dominant_collapse_actions"] == [8]
    assert gate["amended_ok"] is False

    zero = np.zeros((20, 768))
    zero_stats = scorer.summarize_std_by_action(zero, zero, np.zeros(20, dtype=np.int64))
    assert zero_stats["0"]["kish_neff"] == 0.0

    variant_gate = {
        "individual_fail_actions": [],
        "individual_ratios": {"1": 0.9},
        "freq_weighted_ok": True,
        "pool": {
            "active": True,
            "ratio": 0.1,
            "dominant_collapse_actions": [],
        },
    }
    strike, reasons = scorer.classify_strike(
        "FAIL", ok1=True, r1_b1=True, ok3=True, r1_b3=True, r1_bo=True,
        okS1=True, okSb=True, r1_shuf_pool1=True, okstd=False, okpc=True,
        okceil=True, proves_wrong=False, std_gate=variant_gate,
    )
    assert strike == "VARIANT" and reasons == ["std_rare_pool_ratio"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"PASS: {fn.__name__}", flush=True)
    print(f"ALL {len(tests)} UNIT TESTS PASSED", flush=True)
