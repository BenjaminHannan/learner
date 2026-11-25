"""Unit tests for PROBLEM-7 Forecast5 (Rung 1 / Rank 3) — fast CPU verification."""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for cand in (
    HERE.parent / "wm-harness",
    Path("<m3-project>/PROBLEM-7/wm-harness"),
    Path("~/learner-ops/ds-copies/problem-1/harness-sp/vendor"),
    HERE.parent / "wm",
):
    if cand.exists() and str(cand) not in sys.path:
        sys.path.append(str(cand))

import scorer
import sizes
from premonition_core_v2.board_swarm import BoardCell
from model_v5 import PINNED_BOARD_SWARM_SHA256, WorldModelV5, verify_canonical_board_swarm
from train_v5 import ARM_CONFIGS, clip_and_check_grad_norm, compute_train_step_loss, guard_sealed_path


def _tiny_cfg():
    return sizes.make_cfg("tiny")


def test_1_canonical_core_untouched_and_instance_only_patch():
    sha = verify_canonical_board_swarm()
    assert sha == PINNED_BOARD_SWARM_SHA256
    cls_enc_before = BoardCell.encode_context
    cls_tick_before = BoardCell.tick

    cfg = _tiny_cfg()
    m_on = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=42)
    m_off = WorldModelV5(cfg, use_signal_path=False, use_act_film=False, seed=42)

    assert BoardCell.encode_context is cls_enc_before
    assert BoardCell.tick is cls_tick_before
    assert "encode_context" in m_on.cell.__dict__
    assert "tick" in m_on.cell.__dict__
    assert "encode_context" not in m_off.cell.__dict__
    assert "tick" not in m_off.cell.__dict__


def test_2_signal_path_init_and_door_floor():
    cfg = _tiny_cfg()
    torch.manual_seed(42)
    m_on = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=42)
    torch.manual_seed(42)
    m_off = WorldModelV5(cfg, use_signal_path=False, use_act_film=False, seed=42)

    # Parameter init scales (Problem-1 exact recipe)
    assert float(m_on.cell.src_emb.weight.detach().std()) < 0.05
    assert float(m_on.cell.row_type_emb.weight.detach().std()) < 0.05
    assert float(m_on.cell.age_lin.bias.detach().abs().max()) == 0.0
    assert float(m_on.cell.init_rows.detach().std()) < 0.12
    assert 0.05 < float(m_on.cell.out_proj.weight.detach().std()) < 0.18
    assert float(m_on.cell.out_proj.bias.detach().abs().max()) == 0.0
    assert torch.allclose(m_on.cell.row_pos_emb, m_off.cell.row_pos_emb)
    assert float(m_on.act_film.weight.detach().abs().max()) == 0.0
    assert float(m_on.act_film.bias.detach().abs().max()) == 0.0

    # Verify door_floor >= 0.15 on non-pinned slow rows and == 0 on pinned slow rows during tick()
    x = torch.rand(4, 16, 16, 3)
    enc = m_on.encode_frame(x)
    st = m_on.cell.init_state(4, 1, dtype=torch.float32)
    pin = st.row_pin.clone()
    pin[:, :, 0] = True  # pin slow row 0
    st = dataclasses.replace(st, row_pin=pin)
    out = m_on.cell.run_tick(st, enc, noise=False)
    # Slow row 0 is pinned -> gate == 0 and row unchanged
    assert float(out.gate[:, :, 0].detach().abs().max()) == 0.0
    assert torch.allclose(out.state.rows[:, :, 0], st.rows[:, :, 0])
    # Unpinned slow rows -> gate >= 0.15
    assert float(out.gate[:, :, 1:].detach().min()) >= 0.15 - 1e-6

    # Verify pinned rows also stay unchanged during imagine_step
    act = torch.tensor([1, 2, 3, 4], dtype=torch.long)
    out_im = m_on.imagine_step(st, act, wm_grad=True)
    assert torch.allclose(out_im.next_rows[:, :, 0], st.rows[:, :, 0])


def test_3_context_blind_imagination_and_anti_wishful_thinking():
    cfg = _tiny_cfg()
    torch.manual_seed(7)
    m = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=7)
    # Give act_film non-zero weight to confirm action drives different outputs
    with torch.no_grad():
        m.act_film.weight.normal_(0.0, 0.2)

    x0 = torch.rand(4, 16, 16, 3)
    st0, _ = m.real_board(x0, x0)
    o_left = m.imagine_step(st0, torch.full((4,), 1, dtype=torch.long), wm_grad=True)
    o_right = m.imagine_step(st0, torch.full((4,), 2, dtype=torch.long), wm_grad=True)
    assert float((o_left.next_rows - o_right.next_rows).detach().abs().max()) > 1e-4

    # Anti-wishful-thinking: wm_grad=False must give ZERO grad to all model params and start rows,
    # while STILL passing gradient to a proposed action_embed!
    m.zero_grad(set_to_none=True)
    rows_leaf = st0.rows.detach().clone().requires_grad_(True)
    st_leaf = dataclasses.replace(st0, rows=rows_leaf)
    a_emb = torch.randn(4, m.D, requires_grad=True)
    o_plan = m.imagine_step(st_leaf, a_emb, wm_grad=False)
    loss_plan = o_plan.z_pred.pow(2).mean() + o_plan.next_rows.pow(2).mean()
    loss_plan.backward()

    assert a_emb.grad is not None and float(a_emb.grad.norm()) > 0.0
    assert rows_leaf.grad is None or float(rows_leaf.grad.abs().max()) == 0.0
    for name, p in m.named_parameters():
        assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"wm_grad=False leaked grad to {name}"


def test_4_start_board_detached_on_imagine_loss():
    """Imagination loss alone must NEVER backprop into reader/pos (start board is detached)."""
    cfg = _tiny_cfg()
    torch.manual_seed(9)
    m = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=9)
    x_p = torch.rand(4, 16, 16, 3)
    x_t = torch.rand(4, 16, 16, 3)
    x_n = torch.rand(4, 16, 16, 3)
    act = torch.tensor([1, 2, 3, 4], dtype=torch.long)

    st_t, _ = m.real_board(x_p, x_t)
    st_det = dataclasses.replace(st_t, rows=st_t.rows.detach())
    o = m.imagine_step(st_det, act, wm_grad=True)
    x_img_res = x_t + (m.dec(o.next_rows[:, 0]) - m.dec(st_t.rows[:, 0].detach()))
    l_img = ((x_img_res - x_n) ** 2).mean()
    m.zero_grad(set_to_none=True)
    l_img.backward()
    assert m.reader.weight.grad is None or float(m.reader.weight.grad.abs().max()) == 0.0
    assert m.pos.grad is None or float(m.pos.grad.abs().max()) == 0.0
    assert m.action_emb.weight.grad is not None and float(m.action_emb.weight.grad.norm()) > 0.0
    assert m.act_film.weight.grad is not None and float(m.act_film.weight.grad.norm()) > 0.0


def test_5_open_loop_single_init_rollout():
    cfg = _tiny_cfg()
    torch.manual_seed(11)
    m = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=11)
    m.eval()
    x0 = torch.rand(3, 16, 16, 3)
    st0, _ = m.real_board(x0, x0)
    acts5 = torch.tensor([[1, 2, 3, 4, 5], [2, 2, 1, 0, 3], [4, 3, 2, 1, 0]], dtype=torch.long)

    out = m.rollout(st0, x0, acts5)
    # Manual step-by-step verification
    with torch.no_grad():
        st = st0
        for j in range(5):
            o = m.imagine_step(st, acts5[:, j], wm_grad=True)
            st = dataclasses.replace(st, rows=o.next_rows)
        expected_abs = m.dec(st.rows[:, 0])
        expected_res = x0 + (expected_abs - m.dec(st0.rows[:, 0]))
    assert torch.allclose(out["pred_abs"], expected_abs, atol=1e-6)
    assert torch.allclose(out["pred_res"], expected_res, atol=1e-6)


def test_6_all_four_arms_train_steps_finite():
    cfg = _tiny_cfg()
    x_p = torch.rand(4, 16, 16, 3)
    x_t = torch.rand(4, 16, 16, 3)
    x_n = torch.rand(4, 16, 16, 3)
    act = torch.tensor([1, 2, 3, 4], dtype=torch.long)

    for arm_name, acfg in ARM_CONFIGS.items():
        torch.manual_seed(42)
        m = WorldModelV5(
            cfg,
            use_signal_path=acfg["use_signal_path"],
            use_act_film=acfg["use_act_film"],
            seed=42,
        )
        if arm_name == "no_act_film":
            assert m.act_film is None
        else:
            assert m.act_film is not None
        opt = torch.optim.AdamW(m.parameters(), lr=3e-4)
        for _ in range(2):
            loss, met, _ = compute_train_step_loss(
                m, x_p, x_t, act, x_n, use_res_loss=acfg["use_res_loss"]
            )
            assert torch.isfinite(loss), f"Non-finite loss in arm {arm_name}: {met}"
            opt.zero_grad(set_to_none=True)
            loss.backward()
            assert m.action_emb.weight.grad is not None and float(m.action_emb.weight.grad.norm()) > 0.0
            opt.step()


def test_7_sealed_split_guard():
    for eo, als in ((False, False), (True, False), (False, True)):
        raised = False
        try:
            guard_sealed_path("data/sealed_test.npz", eval_only=eo, allow_sealed=als)
        except RuntimeError:
            raised = True
        assert raised, f"Expected RuntimeError for eval_only={eo}, allow_sealed={als}"
    # Allowed ONLY when BOTH eval_only and allow_sealed are True
    guard_sealed_path("data/sealed_test.npz", eval_only=True, allow_sealed=True)
    # Dev split always allowed
    guard_sealed_path("../wm-harness/data/heldout.npz", eval_only=False, allow_sealed=False)


def test_8_scorer_selftest():
    rep = scorer.run_selftest()
    assert rep["selftest"] == "ALL_PASS"
    assert rep["check1_rung1_verdict"] == "PASS"
    assert rep["check2_rung1_verdict"] == "FAIL"


def test_9_batch1_and_t0_boundary():
    """Verify B=1 produces finite loss/grads/burial stats and t=0 (x_prev==x_t) is clean."""
    cfg = _tiny_cfg()
    torch.manual_seed(42)
    m = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=42)
    x_t = torch.rand(1, 16, 16, 3)
    x_n = torch.rand(1, 16, 16, 3)
    act = torch.tensor([1], dtype=torch.long)
    loss, met, rows = compute_train_step_loss(m, x_t, x_t, act, x_n, use_res_loss=True)
    assert torch.isfinite(loss), f"Non-finite B=1 loss: {met}"
    loss.backward()
    for name, p in m.named_parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all(), f"Non-finite grad in {name} at B=1"
    bs = m.board_burial_stats(rows)
    assert np.isfinite(bs["static_rms"]) and np.isfinite(bs["spread_rms"]) and np.isfinite(bs["burial_ratio"])


def test_10_wm_grad_false_all_arms_long_and_float():
    """Verify wm_grad=False leaks ZERO grad to any model param across all knob combos & Long/Float actions."""
    cfg = _tiny_cfg()
    x0 = torch.rand(3, 16, 16, 3)
    for sp in (True, False):
        for af in (True, False):
            torch.manual_seed(17)
            m = WorldModelV5(cfg, use_signal_path=sp, use_act_film=af, seed=17)
            if m.act_film is not None:
                with torch.no_grad():
                    m.act_film.weight.normal_(0.0, 0.2)
            st0, _ = m.real_board(x0, x0)

            # Long action IDs -> ZERO grad everywhere including action_emb
            m.zero_grad(set_to_none=True)
            rows_leaf = st0.rows.detach().clone().requires_grad_(True)
            st_leaf = dataclasses.replace(st0, rows=rows_leaf)
            o_int = m.imagine_step(st_leaf, torch.tensor([1, 2, 3], dtype=torch.long), wm_grad=False)
            assert not o_int.next_rows.requires_grad and not o_int.z_pred.requires_grad

            # Float action embeddings -> grad ONLY on a_emb, ZERO on every model param & start rows
            m.zero_grad(set_to_none=True)
            rows_leaf2 = st0.rows.detach().clone().requires_grad_(True)
            st_leaf2 = dataclasses.replace(st0, rows=rows_leaf2)
            a_emb = torch.randn(3, m.D, requires_grad=True)
            o_flt = m.imagine_step(st_leaf2, a_emb, wm_grad=False)
            (o_flt.next_rows.pow(2).mean() + o_flt.z_pred.pow(2).mean()).backward()
            assert a_emb.grad is not None and float(a_emb.grad.norm()) > 0.0
            assert rows_leaf2.grad is None or float(rows_leaf2.grad.abs().max()) == 0.0
            for name, p in m.named_parameters():
                assert p.grad is None or float(p.grad.abs().max()) == 0.0, f"leak ({sp},{af}) to {name}"


def test_11_arm_bit_identical_shared_init():
    """Verify all 4 arms share bit-identical reader, pos, action_emb, and dec init weights."""
    cfg = _tiny_cfg()
    models = {}
    for arm_name, acfg in ARM_CONFIGS.items():
        torch.manual_seed(42)
        models[arm_name] = WorldModelV5(
            cfg,
            use_signal_path=acfg["use_signal_path"],
            use_act_film=acfg["use_act_film"],
            seed=42,
        )
    ref = models["bundle"]
    for arm_name, m in models.items():
        assert torch.equal(m.reader.weight, ref.reader.weight), f"reader mismatch in {arm_name}"
        assert torch.equal(m.pos, ref.pos), f"pos mismatch in {arm_name}"
        assert torch.equal(m.action_emb.weight, ref.action_emb.weight), f"action_emb mismatch in {arm_name}"
        for (kn, kp), (rn, rp) in zip(m.dec.named_parameters(), ref.dec.named_parameters()):
            assert kn == rn and torch.equal(kp, rp), f"dec.{kn} mismatch in {arm_name}"
        assert torch.equal(m.cell.row_pos_emb, ref.cell.row_pos_emb), f"row_pos_emb mismatch in {arm_name}"


def test_12_sealed_symlink_guard_and_ckpt_roundtrip():
    """Verify symlink to sealed file is blocked and checkpoint save/reload is bit-identical."""
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        real_sealed = os.path.join(td, "sealed_test.npz")
        with open(real_sealed, "wb") as f:
            f.write(b"dummy")
        alias = os.path.join(td, "innocent_dev.npz")
        os.symlink(real_sealed, alias)
        raised = False
        try:
            guard_sealed_path(alias, eval_only=False, allow_sealed=False)
        except RuntimeError:
            raised = True
        assert raised, "Symlink to sealed file bypassed guard!"
        guard_sealed_path(alias, eval_only=True, allow_sealed=True)

        # Checkpoint save/reload bit-exactness
        cfg = _tiny_cfg()
        torch.manual_seed(42)
        m1 = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=42).eval()
        ck_path = os.path.join(td, "m.pt")
        torch.save({"model": m1.state_dict(), "meta": {"arm": "bundle"}}, ck_path)
        torch.manual_seed(999)
        m2 = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=999).eval()
        ck = torch.load(ck_path, map_location="cpu", weights_only=False)
        m2.load_state_dict(ck["model"], strict=True)
        x0 = torch.rand(2, 16, 16, 3)
        acts = torch.tensor([[1, 2, 3], [4, 1, 2]], dtype=torch.long)
        st1, _ = m1.real_board(x0, x0)
        st2, _ = m2.real_board(x0, x0)
        assert torch.equal(m1.rollout(st1, x0, acts)["pred_res"], m2.rollout(st2, x0, acts)["pred_res"])


def test_13_classify_move_displacement_masks_source_and_dest_sprite():
    """Requirement 1: classify_move_displacement masks BOTH destination [5:7,7:9] AND bilinear-shifted
    source footprint of the player sprite so a static centered sprite never injects phantom shift energy."""
    # Case A: Uniform grass terrain + bright contrasting player sprite at [5:7, 7:9].
    # Because only the sprite contrasts with grass, masking both dest and shifted source must yield
    # ZERO shift energy (valid=False) for all 4 move directions!
    x0 = np.full((4, 16, 16, 3), 0.30, dtype=np.float64)
    x0[:, 5:7, 7:9, :] = 0.95  # bright player sprite
    x1 = x0.copy()             # uniform grass shifted + static sprite looks identical
    acts = np.array([1, 2, 3, 4], dtype=np.int64)
    valid, is_open, _ = scorer.classify_move_displacement(x0, x1, acts)
    assert not valid.any(), f"Phantom player-sprite bleed leaked into shift energy: valid={valid}"
    assert not is_open.any()

    # Case B: Textured terrain + bright static player sprite at [5:7, 7:9].
    # Open move shifts terrain while player sprite stays fixed at [5:7, 7:9] -> alpha ~ 1.0, is_open=True.
    # Blocked move keeps frame identical -> alpha == 0.0, is_open=False.
    rng = np.random.default_rng(123)
    base = rng.uniform(0.15, 0.75, size=(4, 16, 16, 3))
    base[:, 5:7, 7:9, :] = 0.98  # contrasting player sprite
    x_open = np.empty_like(base)
    for idx_d, q in enumerate((1, 2, 3, 4)):
        dy, dx = scorer.MOVE_DIRS[q]
        sh = scorer._synthetic_shift_full(base[idx_d], dy, dx)
        sh[5:7, 7:9, :] = 0.98  # player remains centered after move!
        x_open[idx_d] = sh
    v_op, op_op, al_op = scorer.classify_move_displacement(base, x_open, acts)
    v_bl, op_bl, al_bl = scorer.classify_move_displacement(base, base, acts)
    assert v_op.all() and op_op.all(), f"Open move missed with sprite mask: v={v_op}, op={op_op}, al={al_op}"
    assert float(al_op.min()) > 0.95, f"Sprite bleed dragged open alpha below 0.95: {al_op}"
    assert v_bl.all() and not op_bl.any(), f"Blocked move misclassified: v={v_bl}, op={op_bl}, al={al_bl}"
    assert float(np.abs(al_bl).max()) < 1e-12


def test_14_shift_or_stay_centered_crop_fixed_labels_and_fairness():
    """Requirement 2: shift_or_stay uses player-centered crop [3:9, 5:11] (covering move_up rows 3:5),
    fits on fixed displacement labels (ignoring blocked HUD flicker), and scorer passes 0.7x damped
    oracle while failing obstacle-blind camera-shift-only predictors."""
    # Sub-test A: Obstacle directly ABOVE player (rows 3..4, cols 7..8) + blocked HUD flicker (MSE > 1e-4)
    # Use crisp 1-step episodes so bilinear shifting never blurs tiles across 100 steps.
    def make_up_split(n_eps, seed):
        r = np.random.default_rng(seed)
        frames, actions, eid, wid, tid = [], [], [], [], []
        for j in range(n_eps):
            f0 = r.uniform(0.15, 0.85, size=(16, 16, 3))
            blocked = bool(j % 2 == 0)
            if blocked:
                f0[3:5, 7:9, :] = np.array([0.05, 0.05, 0.92])  # blue wall directly above player
                f1 = f0.copy()
                f1[5:7, 7:9, :] = 0.95
                f0[5:7, 7:9, :] = 0.95
                f0[12:, :, :] = 0.20
                # Blocked HUD flicker (MSE > 2e-4) that tricked old MSE > 1e-4 label!
                f1[12:, :, :] = 0.20 + r.uniform(0.03, 0.05)
            else:
                f0[3:5, 7:9, :] = np.array([0.08, 0.90, 0.08])  # green grass directly above player
                f0[5:7, 7:9, :] = 0.95
                f0[12:, :, :] = 0.20
                dy, dx = scorer.MOVE_DIRS[3]
                f1 = scorer._synthetic_shift_full(f0, dy, dx)
                f1[5:7, 7:9, :] = 0.95
                f1[12:, :, :] = 0.20
            frames.append(np.stack([f0, f1], axis=0))
            actions.append(np.array([3], dtype=np.int64))
            eid.append(np.array([j, j], dtype=np.int64))
            wid.append(np.array([j % 8 + seed * 100, j % 8 + seed * 100], dtype=np.int64))
            tid.append(np.array([0, 1], dtype=np.int64))
        return {
            "frames": np.concatenate(frames).astype(np.float32),
            "actions": np.concatenate(actions).astype(np.int64),
            "episode_id": np.concatenate(eid),
            "world_id": np.concatenate(wid),
            "t_index": np.concatenate(tid),
        }

    tr_up = make_up_split(400, seed=1)
    he_up = make_up_split(200, seed=2)
    sos = scorer.fit_shift_or_stay_baseline(tr_up)
    xi1, ai1, wi1, _, _ = scorer.windows(he_up, 1)
    x0 = he_up["frames"][xi1].astype(np.float64)
    y1 = he_up["frames"][xi1 + 1].astype(np.float64)
    a0 = he_up["actions"][ai1]
    p_sos = scorer.rollout_shift_or_stay(sos, x0, a0[:, None])
    bo = scorer.score_block_open(x0, p_sos, y1, a0, wi1)
    assert bo["true_open"] == 100 and bo["true_blocked"] == 100, f"Unexpected counts: {bo}"
    assert bo["mean_err"] < 0.05 and bo["false_open_rate"] < 0.05 and bo["false_block_rate"] < 0.05, (
        f"Centered shift_or_stay failed move_up obstacle detection: {bo}"
    )

    # Sub-test B: 0.7x damped oracle PASSES rung1_verdict; camera-shift-only FAILS rung1_verdict
    tr = scorer.make_synthetic_split(list(range(8)), 100, seed=1)
    he = scorer.make_synthetic_split([1000 + i for i in range(16)], 100, seed=2)
    hfr = he["frames"].astype(np.float64)
    sh_acts = scorer.shuffle_actions_per_step(he, seed=43)
    sos_syn = scorer.fit_shift_or_stay_baseline(tr)

    p_damp, ps_damp = {}, {}
    p_cam, ps_cam = {}, {}
    for k in (1, 3, 5):
        xi, ai, _, _, _ = scorer.windows(he, k)
        x0k = hfr[xi]
        yk = hfr[xi + k]
        ak = scorer.action_values(he["actions"], ai, k)
        sak = scorer.action_values(sh_acts, ai, k)
        p_damp[k] = x0k + 0.7 * (yk - x0k)
        ps_damp[k] = scorer.rollout_shift_or_stay(sos_syn, x0k, sak)

        # Camera-shift-only: unconditionally shifts on moves (0.67 shift + 0.33 stay), Mact on non-moves
        def cam_roll(x_in, act_mat):
            x_cur = x_in.copy()
            for step in range(act_mat.shape[1]):
                xf = x_cur.reshape(len(x_cur), -1)
                nx = np.empty_like(xf)
                for q in range(17):
                    sel = act_mat[:, step] == q
                    if not sel.any():
                        continue
                    if q in (1, 2, 3, 4):
                        xsh = np.c_[xf[sel], np.ones(sel.sum())] @ sos_syn["Mshift"][q]
                        nx[sel] = 0.67 * xsh + 0.33 * xf[sel]
                    else:
                        nx[sel] = np.c_[xf[sel], np.ones(sel.sum())] @ sos_syn["Mact"][q]
                x_cur = nx.reshape(-1, 16, 16, 3)
            return x_cur

        p_cam[k] = cam_roll(x0k, ak)
        ps_cam[k] = cam_roll(x0k, sak)

    r_damp = scorer.score_predictions(tr, he, p_damp, ps_damp)
    r_cam = scorer.score_predictions(tr, he, p_cam, ps_cam)
    assert r_damp["rung1_verdict"] == "PASS", f"0.7x damped oracle must PASS: {r_damp['rung1_marks']}"
    assert r_cam["rung1_verdict"] == "FAIL", f"Camera-shift-only must FAIL: {r_cam['rung1_marks']}"
    assert r_cam["k1"]["block_open"]["cut_ge_25pct_neither_worse"] is False


def test_15_incomplete_run_fails_loudly_and_nonfinite_grad_guard():
    """Requirement 3 & 4: done < steps must fail loudly without saving; non-finite grad_norm
    must abort before opt.step(); eval-only must reject checkpoint missing meta.arm."""
    import os
    import subprocess
    import tempfile

    # Part A: non-finite grad_norm check aborts BEFORE modifying any weight
    p = torch.nn.Parameter(torch.ones(4))
    w_before = p.detach().clone()
    p.grad = torch.tensor([1.0, float("nan"), 0.0, 0.0])
    raised = False
    try:
        clip_and_check_grad_norm([p], 1.0)
    except RuntimeError:
        raised = True
    assert raised, "Non-finite NaN grad_norm failed to raise RuntimeError"
    assert torch.equal(p.detach(), w_before)

    p.grad = torch.tensor([1.0, float("inf"), 0.0, 0.0])
    raised_inf = False
    try:
        clip_and_check_grad_norm([p], 1.0)
    except RuntimeError:
        raised_inf = True
    assert raised_inf, "Non-finite Inf grad_norm failed to raise RuntimeError"

    # Part B: train_v5.py fails loudly if max-minutes stops it before args.steps (and writes no ckpt/score)
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
                sys.executable, "-B", str(HERE / "train_v5.py"),
                "--arm", "bundle", "--size", "tiny", "--device", "cpu",
                "--steps", "50", "--batch", "4", "--max-minutes", "1e-6",
                "--skip-disk-check", "--train-data", tr_p, "--eval-data", ev_p, "--out", out_d,
            ],
            capture_output=True, text=True,
        )
        assert proc.returncode != 0, f"Expected non-zero exit when done < steps! stdout={proc.stdout}"
        assert "INCOMPLETE RUN" in proc.stderr or "INCOMPLETE RUN" in proc.stdout
        assert not os.path.exists(os.path.join(out_d, "model.pt")), "Incomplete run must not save model.pt"
        assert not os.path.exists(os.path.join(out_d, "score_dev.json")), "Incomplete run must not save score"

        # Part C: --eval-only rejects checkpoint missing meta.arm
        cfg = _tiny_cfg()
        m = WorldModelV5(cfg, use_signal_path=True, use_act_film=True, seed=42)
        bad_ck = os.path.join(td, "no_arm.pt")
        torch.save({"model": m.state_dict(), "meta": {}}, bad_ck)
        proc2 = subprocess.run(
            [
                sys.executable, "-B", str(HERE / "train_v5.py"),
                "--arm", "bundle", "--size", "tiny", "--device", "cpu",
                "--eval-only", bad_ck, "--skip-disk-check",
                "--train-data", tr_p, "--eval-data", ev_p, "--out", out_d,
            ],
            capture_output=True, text=True,
        )
        assert proc2.returncode != 0, "Expected non-zero exit for checkpoint missing meta.arm"


def test_16_withlock_exit_code_warnings_and_sigterm_trap():
    """Requirement 4: withlock.sh preserves real exit code, streams warnings unbuffered,
    and releases the lock on EXIT and SIGTERM."""
    import os
    import signal
    import subprocess
    import tempfile
    import time

    wl = str(HERE / "withlock.sh")
    with tempfile.TemporaryDirectory() as td:
        lock_f = os.path.join(td, "test.lock")
        env = dict(os.environ, PREMONITION_MPS_LOCK=lock_f, PREMONITION_LOCK_POLL="1")

        # 1. Real exit code 0 + Warning preserved in log + lock released
        log1 = os.path.join(td, "ok.log")
        r1 = subprocess.run(
            ["/bin/zsh", wl, log1, sys.executable, "-u", "-c", "print('Warning: keep me'); print('done')"],
            env=env, capture_output=True, text=True,
        )
        assert r1.returncode == 0, f"Expected 0, got {r1.returncode}: {r1.stderr}"
        assert not os.path.exists(lock_f), "Lock not released on exit 0"
        log1_txt = open(log1).read()
        assert "Warning: keep me" in log1_txt and "done" in log1_txt

        # 2. Non-zero exit code 7 passed through + lock released
        log2 = os.path.join(td, "fail.log")
        r2 = subprocess.run(
            ["/bin/zsh", wl, log2, sys.executable, "-u", "-c", "import sys; print('boom'); sys.exit(7)"],
            env=env, capture_output=True, text=True,
        )
        assert r2.returncode == 7, f"Expected exit code 7, got {r2.returncode}"
        assert not os.path.exists(lock_f), "Lock not released on exit 7"
        assert "boom" in open(log2).read()

        # 3. SIGTERM releases lock and terminates child
        log3 = os.path.join(td, "term.log")
        p = subprocess.Popen(
            ["/bin/zsh", wl, log3, sys.executable, "-u", "-c", "import time; print('started', flush=True); time.sleep(30)"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for _ in range(50):
            if os.path.exists(lock_f):
                break
            time.sleep(0.05)
        assert os.path.exists(lock_f), "Lock file was never created"
        p.send_signal(signal.SIGTERM)
        rc3 = p.wait(timeout=5)
        assert rc3 != 0, f"Expected non-zero rc on SIGTERM, got {rc3}"
        assert not os.path.exists(lock_f), "Lock not released on SIGTERM trap!"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"PASS: {fn.__name__}", flush=True)
    print(f"ALL {len(tests)} UNIT TESTS PASSED", flush=True)
