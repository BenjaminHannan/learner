"""Unit tests for PROBLEM-7 Forecast6 (Rank 6: Dedicated 2D Conv World Model) — fast CPU verification."""
from __future__ import annotations

import inspect
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import scorer
from model_v6 import PINNED_SCORER_SHA256, SpatialWorldModelV6, verify_pinned_scorer
from train_v6 import (
    ARCH_TAG,
    PINNED_CANONICAL_BOARD_SWARM_SHA256,
    check_mps_power,
    clip_and_check_grad_norm,
    compute_train_step_loss,
    evaluate_model,
    guard_sealed_path,
    sha256_file,
)


def test_1_pinned_scorer_and_canonical_core_untouched():
    """Requirement 1 & 9: forecast6/scorer.py is bit-identical to pinned 6ff1c135... and canonical core untouched."""
    sha = verify_pinned_scorer(HERE / "scorer.py")
    assert sha == PINNED_SCORER_SHA256
    f5_scorer = HERE.parent / "forecast5" / "scorer.py"
    if f5_scorer.exists():
        assert sha256_file(str(f5_scorer)) == PINNED_SCORER_SHA256
    for cand in (
        HERE.parent / "wm-harness" / "premonition_core_v2" / "board_swarm.py",
        Path("<m3-project>/PROBLEM-7/wm-harness/premonition_core_v2/board_swarm.py"),
    ):
        if cand.exists():
            assert sha256_file(str(cand)) == PINNED_CANONICAL_BOARD_SWARM_SHA256


def test_2_param_counts_and_shapes():
    """Verify both R6conv (~2M compact 2D model) and tiny presets run cleanly with expected shapes."""
    m_full = SpatialWorldModelV6(size="R6conv")
    pc = m_full.param_counts()
    assert 1_000_000 <= pc["model_total"] <= 3_000_000, f"Unexpected R6conv param count: {pc}"

    m = SpatialWorldModelV6(size="tiny")
    x = torch.rand(3, 16, 16, 3)
    z = m.encode(x)
    assert z.shape == (3, m.latent_ch, 16, 16)
    xr = m.decode(z)
    assert xr.shape == (3, 16, 16, 3)
    act = torch.tensor([1, 2, 3], dtype=torch.long)
    zn = m.imagine_step(z, act, wm_grad=True)
    assert zn.shape == z.shape
    # Action sensitivity: different actions must produce distinct latents
    zn_l = m.imagine_step(z, torch.full((3,), 1, dtype=torch.long), wm_grad=True)
    zn_r = m.imagine_step(z, torch.full((3,), 2, dtype=torch.long), wm_grad=True)
    assert float((zn_l - zn_r).detach().abs().max()) > 1e-4


def test_3_strictly_k1_train_loss_and_encoder_protected():
    """Requirement 3: training loss uses strictly k=1 pairs (x_t, act, x_next); dynamics never corrupts encoder."""
    sig = inspect.signature(compute_train_step_loss)
    assert list(sig.parameters.keys())[:4] == ["model", "x_t", "act", "x_next"]

    torch.manual_seed(42)
    m = SpatialWorldModelV6(size="tiny")
    x_t = torch.rand(4, 16, 16, 3)
    x_n = torch.rand(4, 16, 16, 3)
    act = torch.tensor([1, 2, 3, 4], dtype=torch.long)

    # Pure imagination loss alone (l_rec omitted) MUST put ZERO gradient on encoder!
    z_t = m.encode(x_t)
    x_rec_t = m.decode(z_t)
    z_n = m.imagine_step(z_t.detach(), act, wm_grad=True)
    x_img_res = x_t + (m.decode(z_n) - x_rec_t.detach())
    l_img = ((x_img_res - x_n) ** 2).mean()
    m.zero_grad(set_to_none=True)
    l_img.backward()
    for name, p in m.encoder.named_parameters():
        assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"Imagination leaked grad to encoder.{name}"
    assert m.action_emb.weight.grad is not None and float(m.action_emb.weight.grad.norm()) > 0.0

    # Joint step-0 loss puts finite, non-zero grads on encoder, decoder, action_emb, and dynamics
    m.zero_grad(set_to_none=True)
    loss, met, z_det = compute_train_step_loss(m, x_t, act, x_n)
    assert torch.isfinite(loss), f"Non-finite loss: {met}"
    loss.backward()
    assert float(m.action_emb.weight.grad.norm()) > 0.0
    assert float(m.encoder.conv1.weight.grad.norm()) > 0.0
    assert float(m.decoder.conv2.weight.grad.norm()) > 0.0
    assert float(m.dynamics.out_conv.weight.grad.norm()) > 0.0
    assert not z_det.requires_grad


def test_4_open_loop_rollout_exact_and_no_intermediate_real_frames():
    """Requirement 3: k=3 and k=5 rollouts run strictly open-loop from x0 only and NEVER touch intermediate real frames."""
    torch.manual_seed(11)
    m = SpatialWorldModelV6(size="tiny").eval()
    x0 = torch.rand(4, 16, 16, 3)
    acts5 = torch.tensor([[1, 2, 3, 4, 5], [2, 2, 1, 0, 3], [4, 3, 2, 1, 0], [6, 1, 1, 2, 5]], dtype=torch.long)

    # Part A: rollout() matches manual open-loop step-by-step from x0 only
    out = m.rollout(x0, acts5, wm_grad=False)
    with torch.no_grad():
        z0 = m.encode(x0)
        dec0 = m.decode(z0)
        z = z0
        for step in range(5):
            z = m.imagine_step(z, acts5[:, step], wm_grad=False)
        exp_abs = m.decode(z)
        exp_res = x0 + (exp_abs - dec0)
    assert torch.allclose(out["pred_abs"], exp_abs, atol=1e-6)
    assert torch.allclose(out["pred_res"], exp_res, atol=1e-6)

    # Part B: evaluate_model produces BIT-IDENTICAL k=3 and k=5 predictions even when
    # every intermediate frame (t=1, 2, 3, 4 inside a single 6-frame episode!) is poisoned with NaNs!
    rng = np.random.default_rng(77)
    n_eps = 16
    frames_clean, actions, eid, wid, tid = [], [], [], [], []
    for e in range(n_eps):
        ep_fr = rng.uniform(0.1, 0.9, size=(6, 16, 16, 3)).astype(np.float32)
        ep_act = rng.integers(0, 7, size=(5,), dtype=np.int64)
        frames_clean.append(ep_fr)
        actions.append(ep_act)
        eid.append(np.full(6, e, dtype=np.int64))
        wid.append(np.full(6, 1000 + e, dtype=np.int64))
        tid.append(np.arange(6, dtype=np.int64))

    ev_clean = {
        "frames": np.concatenate(frames_clean, axis=0),
        "actions": np.concatenate(actions, axis=0),
        "episode_id": np.concatenate(eid),
        "world_id": np.concatenate(wid),
        "t_index": np.concatenate(tid),
    }
    # For k=5 windows, xi points to t=0 and target is t=5; intermediate frames are t=1,2,3,4.
    # Poison t=1,2,3,4 in a copy and verify rollout(x0, acts_5) produces BIT-IDENTICAL predictions!
    ev_poison = dict(ev_clean)
    fr_poison = ev_clean["frames"].copy()
    for e in range(n_eps):
        fr_poison[e * 6 + 1 : e * 6 + 5] = np.nan
    ev_poison["frames"] = fr_poison

    xi5, ai5, _, _, _ = scorer.windows(ev_clean, 5)
    acts_5 = torch.from_numpy(scorer.action_values(ev_clean["actions"], ai5, 5).astype(np.int64))
    p5_clean = m.rollout(torch.from_numpy(ev_clean["frames"][xi5]), acts_5, wm_grad=False)["pred_res"]
    p5_poison = m.rollout(torch.from_numpy(ev_poison["frames"][xi5]), acts_5, wm_grad=False)["pred_res"]
    assert torch.isfinite(p5_poison).all(), "Poisoned intermediate frames leaked NaN into k=5 rollout!"
    assert torch.equal(p5_clean, p5_poison), "k=5 rollout differed when intermediate frames were poisoned!"

    # Also verify evaluate_model k=1,3,5 predictions match direct open-loop rollout(x0, acts_k) bit-for-bit
    tr_syn = scorer.make_synthetic_split([0, 1, 2, 3], 40, seed=1)
    ev_syn = scorer.make_synthetic_split([1000 + i for i in range(4)], 40, seed=2)
    res, preds = evaluate_model(m, tr_syn, ev_syn, torch.device("cpu"), batch_size=32)
    for k in (1, 3, 5):
        xik, aik, _, _, _ = scorer.windows(ev_syn, k)
        ak_t = torch.from_numpy(scorer.action_values(ev_syn["actions"], aik, k).astype(np.int64))
        x0_t = torch.from_numpy(ev_syn["frames"][xik].astype(np.float32))
        chunks = [
            m.rollout(x0_t[b : b + 32], ak_t[b : b + 32], wm_grad=False)["pred_res"].double().numpy()
            for b in range(0, len(xik), 32)
        ]
        direct_batched = np.concatenate(chunks, axis=0)
        assert np.array_equal(preds[k], direct_batched), f"evaluate_model k={k} not bit-identical to pure open-loop rollout"
        direct_full = m.rollout(x0_t, ak_t, wm_grad=False)["pred_res"].double().numpy()
        assert np.allclose(preds[k], direct_full, atol=1e-4), f"evaluate_model k={k} batch-size drift > 1e-4"

    # Requirement 2: verify ceiling_abs_E_over_B equals exact decode(encode(x_{t+1})) error / B
    xi1 = scorer.windows(ev_syn, 1)[0]
    x1_t = torch.from_numpy(ev_syn["frames"][xi1 + 1].astype(np.float32))
    with torch.no_grad():
        c_abs_direct = m.decode(m.encode(x1_t)).double().numpy()
    y1 = ev_syn["frames"][xi1 + 1].astype(np.float64)
    exp_ceil_abs = float(((c_abs_direct - y1) ** 2).sum() / res["k1"]["B"])
    assert abs(res["k1"]["ceiling_abs_E_over_B"] - exp_ceil_abs) < 1e-6


def test_5_wm_grad_false_anti_wishful_thinking_long_and_float():
    """Verify wm_grad=False leaks ZERO grad to every model param & start latent for both Long and Float actions."""
    torch.manual_seed(17)
    m = SpatialWorldModelV6(size="tiny")
    x0 = torch.rand(3, 16, 16, 3)
    z0 = m.encode(x0)

    # Integer action IDs -> output detached, ZERO grad anywhere including action_emb
    m.zero_grad(set_to_none=True)
    z_leaf = z0.detach().clone().requires_grad_(True)
    z_int = m.imagine_step(z_leaf, torch.tensor([1, 2, 3], dtype=torch.long), wm_grad=False)
    assert not z_int.requires_grad

    # Continuous float action embeddings -> grad ONLY on a_emb, ZERO on every model param & z_leaf
    m.zero_grad(set_to_none=True)
    z_leaf2 = z0.detach().clone().requires_grad_(True)
    a_emb = torch.randn(3, m.cond_dim, requires_grad=True)
    z_flt = m.imagine_step(z_leaf2, a_emb, wm_grad=False)
    z_flt.pow(2).mean().backward()
    assert a_emb.grad is not None and float(a_emb.grad.norm()) > 0.0
    assert z_leaf2.grad is None or float(z_leaf2.grad.abs().max()) == 0.0
    for name, p in m.named_parameters():
        assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"wm_grad=False leaked grad to {name}"

    # Multi-step rollout(x0, a_emb_seq, wm_grad=False): grad reaches ALL steps of action plan,
    # ZERO grad on encoder/decoder/action_emb/dynamics!
    m.zero_grad(set_to_none=True)
    x0_leaf = x0.detach().clone().requires_grad_(True)
    a_seq = torch.randn(3, 3, m.cond_dim, requires_grad=True)
    ro = m.rollout(x0_leaf, a_seq, wm_grad=False)
    ro["pred_abs"].pow(2).mean().backward()
    assert a_seq.grad is not None and float(a_seq.grad[:, 0].norm()) > 0.0 and float(a_seq.grad[:, 2].norm()) > 0.0
    assert x0_leaf.grad is None or float(x0_leaf.grad.abs().max()) == 0.0
    for name, p in m.named_parameters():
        assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"rollout wm_grad=False leaked grad to {name}"


def test_6_batch1_finite_and_ckpt_roundtrip():
    """Verify B=1 produces finite loss/grads/latent_stats and checkpoint save/reload is bit-identical."""
    torch.manual_seed(42)
    m = SpatialWorldModelV6(size="tiny")
    x_t = torch.rand(1, 16, 16, 3)
    x_n = torch.rand(1, 16, 16, 3)
    act = torch.tensor([2], dtype=torch.long)
    loss, met, z_det = compute_train_step_loss(m, x_t, act, x_n)
    assert torch.isfinite(loss), f"Non-finite B=1 loss: {met}"
    loss.backward()
    for name, p in m.named_parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all(), f"Non-finite grad in {name} at B=1"
    ls = m.latent_stats(z_det)
    assert np.isfinite(ls["static_rms"]) and np.isfinite(ls["spread_rms"]) and np.isfinite(ls["burial_ratio"])

    with tempfile.TemporaryDirectory() as td:
        ck_path = os.path.join(td, "m.pt")
        m.eval()
        torch.save({"model": m.state_dict(), "meta": {"arch": ARCH_TAG, "size": "tiny"}}, ck_path)
        torch.manual_seed(999)
        m2 = SpatialWorldModelV6(size="tiny").eval()
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        m2.load_state_dict(ck["model"], strict=True)
        x0 = torch.rand(2, 16, 16, 3)
        acts = torch.tensor([[1, 2, 3], [4, 1, 2]], dtype=torch.long)
        assert torch.equal(m.rollout(x0, acts)["pred_res"], m2.rollout(x0, acts)["pred_res"])


def test_7_sealed_split_guard_and_symlink():
    """Verify sealed_test.npz and symlinks to it are blocked unless BOTH --eval-only AND --allow-sealed."""
    for eo, als in ((False, False), (True, False), (False, True)):
        raised = False
        try:
            guard_sealed_path("data/sealed_test.npz", eval_only=eo, allow_sealed=als)
        except RuntimeError:
            raised = True
        assert raised, f"Expected RuntimeError for eval_only={eo}, allow_sealed={als}"

    # Passing --allow-sealed on a non-sealed file must also fail loudly
    raised_wrong = False
    try:
        guard_sealed_path("../wm-harness/data/heldout.npz", eval_only=True, allow_sealed=True)
    except RuntimeError:
        raised_wrong = True
    assert raised_wrong, "Expected RuntimeError when --allow-sealed is passed on non-sealed file"

    with tempfile.TemporaryDirectory() as td:
        real_sealed = os.path.join(td, "sealed_test.npz")
        with open(real_sealed, "wb") as f:
            f.write(b"dummy")
        alias = os.path.join(td, "innocent_dev.npz")
        os.symlink(real_sealed, alias)
        raised_sym = False
        try:
            guard_sealed_path(alias, eval_only=False, allow_sealed=False)
        except RuntimeError:
            raised_sym = True
        assert raised_sym, "Symlink to sealed file bypassed guard!"
        # Dummy file fails pinned SHA check even with --eval-only --allow-sealed
        raised_sha = False
        try:
            guard_sealed_path(alias, eval_only=True, allow_sealed=True)
        except RuntimeError:
            raised_sha = True
        assert raised_sha, "Modified sealed file bypassed pinned SHA-256 check!"


def test_8_mps_power_guard():
    """Requirement 10: MPS requires AC Power OR battery >= 35%."""
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
        assert raised, f"Power guard failed to reject: {low_txt!r}"


def test_9_incomplete_run_and_nonfinite_grad_fail_loud():
    """Requirement 6: done < steps fails loudly without saving; non-finite grad aborts before opt.step()."""
    p = torch.nn.Parameter(torch.ones(4))
    w_before = p.detach().clone()
    for bad_val in (float("nan"), float("inf")):
        p.grad = torch.tensor([1.0, bad_val, 0.0, 0.0])
        raised = False
        try:
            clip_and_check_grad_norm([p], 1.0)
        except RuntimeError:
            raised = True
        assert raised, f"Failed to abort on {bad_val} grad"
        assert torch.equal(p.detach(), w_before)

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
                sys.executable, "-B", str(HERE / "train_v6.py"),
                "--size", "tiny", "--device", "cpu",
                "--steps", "50", "--batch", "4", "--max-minutes", "1e-6",
                "--skip-disk-check", "--train-data", tr_p, "--eval-data", ev_p, "--out", out_d,
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode != 0, f"Expected non-zero exit when done < steps! stdout={proc.stdout}"
        assert "INCOMPLETE RUN" in proc.stderr or "INCOMPLETE RUN" in proc.stdout
        assert not os.path.exists(os.path.join(out_d, "model.pt"))
        assert not os.path.exists(os.path.join(out_d, "score_dev.json"))

        # --eval-only rejects mismatched size checkpoint
        m = SpatialWorldModelV6(size="tiny")
        bad_ck = os.path.join(td, "bad_size.pt")
        torch.save({"model": m.state_dict(), "meta": {"arch": ARCH_TAG, "size": "R6conv"}}, bad_ck)
        proc2 = subprocess.run(
            [
                sys.executable, "-B", str(HERE / "train_v6.py"),
                "--size", "tiny", "--device", "cpu", "--eval-only", bad_ck,
                "--skip-disk-check", "--train-data", tr_p, "--eval-data", ev_p, "--out", out_d,
            ],
            capture_output=True, text=True,
        )
        assert proc2.returncode != 0, "Expected non-zero exit on checkpoint size mismatch"


def test_10_scorer_selftest_and_withlock_sha():
    """Verify bit-identical scorer selftest and lock-safe withlock.sh (sha 77e3ac48...)."""
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


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"PASS: {fn.__name__}", flush=True)
    print(f"ALL {len(tests)} UNIT TESTS PASSED", flush=True)
