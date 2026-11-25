from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

import pilot_driver
import scorer
import train_v7 as pilot
from model_v7 import SpatialWorldModelV7, verify_pinned_scorer

HERE = Path(__file__).resolve().parent
def load_v7():
    candidates = (
        HERE.parent / "forecast7" / "train_v7.py",
        HERE.parent / "wm7" / "train_v7.py",
    )
    source = next(path for path in candidates if path.exists())
    spec = importlib.util.spec_from_file_location("forecast7_train_for_equivalence", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_1_pins_and_default_sampler():
    assert verify_pinned_scorer(HERE / "scorer.py") == "ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912"
    assert pilot.sha256_file(str(HERE / "model_v7.py")) == "c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006"
    assert pilot.sha256_file(str(HERE / "withlock.sh")) == "77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa"
    tree = ast.parse((HERE / "train_v7.py").read_text())
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "--sampler":
                defaults = {kw.arg: kw.value for kw in node.keywords}
                assert isinstance(defaults["default"], ast.Constant) and defaults["default"].value == "uniform"
                found = True
    assert found


def test_2_uniform_byte_identical_20_steps():
    original = load_v7()
    split = scorer.make_synthetic_split(list(range(6)), 30, seed=71)
    xi1, ai1, _, _, ti1 = scorer.windows(split, 1)
    h1 = pilot.prev_frame_indices(split, xi1, ti1)
    torch.manual_seed(7)
    model_old = SpatialWorldModelV7(size="tiny", n_history=2)
    torch.manual_seed(7)
    model_new = SpatialWorldModelV7(size="tiny", n_history=2)
    opt_old = torch.optim.AdamW(model_old.parameters(), lr=3e-4, weight_decay=1e-4)
    opt_new = torch.optim.AdamW(model_new.parameters(), lr=3e-4, weight_decay=1e-4)
    rng_old = np.random.default_rng(7)
    rng_new = np.random.default_rng(7)
    for step in range(20):
        j_old = rng_old.integers(0, len(xi1), size=4)
        j_new = pilot.draw_minibatch_indices(rng_new, len(xi1), 4, None)
        assert np.array_equal(j_old, j_new), f"batch indices differ at step {step}"
        i, h = xi1[j_old], h1[j_old]
        x_prev = torch.from_numpy(split["frames"][h].astype(np.float32))
        x_t = torch.from_numpy(split["frames"][i].astype(np.float32))
        x_next = torch.from_numpy(split["frames"][i + 1].astype(np.float32))
        act = torch.from_numpy(split["actions"][ai1[j_old]].astype(np.int64))
        loss_old, metrics_old, _ = original.compute_train_step_loss(model_old, x_prev, x_t, act, x_next)
        loss_new, metrics_new, _ = pilot.compute_train_step_loss(model_new, x_prev, x_t, act, x_next)
        assert torch.equal(loss_old, loss_new), f"loss differs at step {step}"
        assert metrics_old == metrics_new, f"metrics differ at step {step}"
        opt_old.zero_grad(set_to_none=True)
        opt_new.zero_grad(set_to_none=True)
        loss_old.backward()
        loss_new.backward()
        torch.nn.utils.clip_grad_norm_(model_old.parameters(), 1.0)
        torch.nn.utils.clip_grad_norm_(model_new.parameters(), 1.0)
        opt_old.step()
        opt_new.step()
    for name, value in model_old.state_dict().items():
        assert torch.equal(value, model_new.state_dict()[name]), f"parameter {name} differs after 20 steps"


def test_3_relper_formula_distribution_and_determinism():
    copy_mse = np.array([0.0, 0.001, 0.01, 0.1, 0.002, 0.02], dtype=np.float64)
    actions = np.array([0, 0, 0, 1, 1, 1], dtype=np.int64)
    sampler = pilot.RelPERSampler(copy_mse, actions, seed=7)
    means = np.array([copy_mse[actions == a].mean() for a in actions])
    expected_r = np.minimum(copy_mse / (means + 1e-4), 20.0)
    weights = (expected_r + 1e-6) ** 0.7
    expected_p = 0.5 * (1.0 / len(copy_mse)) + 0.5 * weights / weights.sum()
    np.testing.assert_allclose(sampler.relative_priority(), expected_r, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(sampler.probabilities, expected_p, rtol=0.0, atol=1e-15)
    assert np.isfinite(sampler.probabilities).all() and (sampler.probabilities >= 0.0).all()
    assert abs(float(sampler.probabilities.sum()) - 1.0) < 1e-12
    same = pilot.RelPERSampler(copy_mse, actions, seed=7)
    for _ in range(10):
        assert np.array_equal(sampler.sample(32), same.sample(32))
    draws = sampler.sample(128)
    assert len(np.unique(draws)) < len(draws)
    old_error = sampler.ema_error.copy()
    indices = np.array([1, 1, 3], dtype=np.int64)
    residual = np.array([0.5, 0.25, 0.125], dtype=np.float64)
    sampler.update(indices, residual)
    expected_error = old_error.copy()
    for idx, value in zip(indices, residual):
        expected_error[idx] = 0.8 * expected_error[idx] + 0.2 * value
    assert np.array_equal(sampler.ema_error, expected_error)
    sampler.refresh()
    assert sampler.refresh_count == 2
    assert pilot.RELPER_REFRESH_STEPS == 25


def test_4_relper_has_no_extra_forward_passes():
    torch.manual_seed(7)
    model = SpatialWorldModelV7(size="tiny", n_history=2)
    x_prev = torch.rand(3, 16, 16, 3)
    x_t = torch.rand(3, 16, 16, 3)
    x_next = torch.rand(3, 16, 16, 3)
    act = torch.tensor([1, 2, 5], dtype=torch.long)
    counts = {"encode": 0, "decode": 0, "imagine_step": 0}
    originals = {name: getattr(model, name) for name in counts}

    def wrap(name):
        def call(*args, **kwargs):
            counts[name] += 1
            return originals[name](*args, **kwargs)
        return call

    for name in counts:
        setattr(model, name, wrap(name))
    pilot.compute_train_step_loss(model, x_prev, x_t, act, x_next)
    baseline = dict(counts)
    for name in counts:
        counts[name] = 0
    _, _, _, residual = pilot.compute_train_step_loss(
        model, x_prev, x_t, act, x_next, return_per_sample_residual=True
    )
    assert counts == baseline
    assert residual.shape == (3,) and torch.isfinite(residual).all()


def test_5_heldout_worlds_never_enter_training():
    full = scorer.make_synthetic_split(list(range(3000, 3080)), 8, seed=7)
    train = pilot_driver.subset_by_worlds(full, pilot_driver.TRAIN_WORLDS)
    evaluation = pilot_driver.subset_by_worlds(full, pilot_driver.EVAL_WORLDS)
    assert np.unique(train["world_id"]).astype(int).tolist() == list(pilot_driver.TRAIN_WORLDS)
    assert np.unique(evaluation["world_id"]).astype(int).tolist() == list(pilot_driver.EVAL_WORLDS)
    assert not set(np.unique(train["world_id"])) & set(np.unique(evaluation["world_id"]))
    xi1, ai1, worlds, _, _ = scorer.windows(train, 1)
    assert not np.isin(worlds, pilot_driver.EVAL_WORLDS).any()
    copy_mse, actions = pilot.transition_copy_mse(train, xi1, ai1)
    sampler = pilot.RelPERSampler(copy_mse, actions, seed=7)
    sampled_worlds = train["world_id"][xi1[sampler.sample(4096)]]
    assert not np.isin(sampled_worlds, pilot_driver.EVAL_WORLDS).any()
    pilot_driver.validate_split(train, pilot_driver.TRAIN_WORLDS)
    pilot_driver.validate_split(evaluation, pilot_driver.EVAL_WORLDS)


def test_6_driver_cannot_reach_other_eval_paths():
    source = (HERE / "pilot_driver.py").read_text()
    assert "heldout.npz" not in source
    assert "sealed_test.npz" not in source
    assert "../wm-harness" not in source
    command = pilot_driver.build_run_command(
        7, "relper", Path("/tmp/pilot_train.npz"), Path("/tmp/pilot_eval.npz"),
        Path("/tmp/pilot_out"), Path("/tmp/pilot.log"),
    )
    train_value = command[command.index("--train-data") + 1]
    eval_value = command[command.index("--eval-data") + 1]
    assert train_value == "/tmp/pilot_train.npz"
    assert eval_value == "/tmp/pilot_eval.npz"
    assert "--allow-sealed" not in command
    assert "--eval-only" not in command


def make_event_split():
    frames, actions, episode_ids, world_ids, t_indices = [], [], [], [], []
    specs = (
        (0.02, 0.20, 5),
        (0.02, 0.20, 5),
        (0.2, 0.20, 5),
        (0.2, 0.20, 5),
        (0.05, 0.05, 6),
        (0.05, 0.05, 6),
    )
    for episode, (hud_delta, next_std, action) in enumerate(specs):
        x0 = np.full((16, 16, 3), 0.2, dtype=np.float32)
        x0[:12] = np.linspace(0.15, 0.25, 12, dtype=np.float32)[:, None, None]
        x0[12:] = 0.0
        x1 = x0.copy()
        x1[12:] = hud_delta
        if next_std > 0.1:
            x1[:12] = np.linspace(0.0, 0.40, 12, dtype=np.float32)[:, None, None]
        frames.append(np.stack([x0, x1]))
        actions.append(np.array([action], dtype=np.int64))
        episode_ids.append(np.array([episode, episode], dtype=np.int64))
        world_ids.append(np.array([4000 + episode, 4000 + episode], dtype=np.int64))
        t_indices.append(np.array([0, 1], dtype=np.int64))
    return {
        "frames": np.concatenate(frames),
        "actions": np.concatenate(actions),
        "episode_id": np.concatenate(episode_ids),
        "world_id": np.concatenate(world_ids),
        "t_index": np.concatenate(t_indices),
    }


def test_7_event_labeller_and_exact_p2_metric():
    split = make_event_split()
    labeller = pilot.fit_event_labeller(split)
    threshold = labeller["post_wake_hud_distance_threshold"]
    assert 0.02 ** 2 * 192 < threshold < 0.20 ** 2 * 192
    events = pilot.label_transition_events(split, labeller)
    assert int(events["wake_e89"].sum()) == 2
    assert int(events["wake_hurt"].sum()) == 2
    assert int(events["sleep_stay"].sum()) == 2
    xi1, x0, _, _ = pilot._k1_transition_arrays(split)
    pred = x0.copy()
    pred[events["wake_e89"]] += 0.10
    pred[events["sleep_stay"]] += 0.01
    metrics = pilot.compute_pilot_event_metrics(split, pred, labeller)
    assert abs(metrics["wake_e89_mean_pred_dBright"] - 0.10) < 1e-6
    assert abs(metrics["stay_asleep_mean_pred_dBright"] - 0.01) < 1e-6
    assert abs(metrics["wake_e89_minus_stay_asleep_dBright"] - 0.09) < 1e-6


def test_8_paired_gate_boundaries():
    base = {
        "k1": {
            "std_ratio_by_action": {"5": {"ratio": 0.30}},
            "E_over_B": 0.25,
            "block_open": {"model": {"mean_err": 0.04}},
        },
        "k3": {"E_over_B": 0.38},
        "pilot_event_diagnostics": {"wake_e89_minus_stay_asleep_dBright": 0.03},
        "diag_non_wake_interactions": {"asleep_all": {"R2": 0.1}},
    }
    uniform = json.loads(json.dumps(base))
    uniform["pilot_event_diagnostics"]["wake_e89_minus_stay_asleep_dBright"] = 0.01
    relper = json.loads(json.dumps(base))
    relper["k1"]["E_over_B"] = 0.255
    relper["k3"]["E_over_B"] = 0.388
    relper["k1"]["block_open"]["model"]["mean_err"] = 0.045
    relper["pilot_event_diagnostics"]["wake_e89_minus_stay_asleep_dBright"] = 0.03
    result = pilot_driver.paired_metrics(uniform, relper)
    assert result["P1"] and result["P2"] and result["P3_k1"] and result["P3_k3"] and result["P3_wall"]
    relper["k1"]["std_ratio_by_action"]["5"]["ratio"] = 0.299999
    relper["pilot_event_diagnostics"]["wake_e89_minus_stay_asleep_dBright"] = 0.029999
    relper["k1"]["E_over_B"] = 0.255001
    result = pilot_driver.paired_metrics(uniform, relper)
    assert not result["P1"] and not result["P2"] and not result["P3_k1"]


def test_9_distribution_refreshes_every_25_steps_in_real_loop():
    train = scorer.make_synthetic_split([0, 1, 2], 20, seed=7)
    evaluation = scorer.make_synthetic_split([4000, 4001], 20, seed=8)
    old_argv = sys.argv
    old_log_steps = pilot.RELPER_LOG_STEPS
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            train_path = root / "train.npz"
            eval_path = root / "eval.npz"
            out_dir = root / "out"
            np.savez(train_path, **train)
            np.savez(eval_path, **evaluation)
            sys.argv = [
                "train_v7.py", "--size", "tiny", "--n-history", "2", "--device", "cpu",
                "--steps", "26", "--batch", "4", "--max-minutes", "0", "--skip-disk-check",
                "--timing-only", "--sampler", "relper", "--train-data", str(train_path),
                "--eval-data", str(eval_path), "--out", str(out_dir),
            ]
            pilot.RELPER_LOG_STEPS = 1
            with contextlib.redirect_stdout(io.StringIO()):
                pilot.main()
            records = [json.loads(line) for line in (out_dir / "sampler_log.jsonl").read_text().splitlines()]
            by_step = {record["step"]: record for record in records}
            assert by_step[24]["distribution_refreshes"] == 1
            assert by_step[25]["distribution_refreshes"] == 2
            assert by_step[26]["distribution_refreshes"] == 2
            assert set(by_step[25]["event_share"]) == set(pilot.EVENT_TYPES)
            assert set(by_step[25]["mean_priority"]) == set(pilot.EVENT_TYPES)
            assert abs(sum(by_step[25]["event_share"].values()) - 1.0) < 1e-12
    finally:
        sys.argv = old_argv
        pilot.RELPER_LOG_STEPS = old_log_steps


def test_10_scorer_and_architecture_unchanged():
    report = scorer.run_selftest()
    assert report["selftest"] == "ALL_PASS"
    model = SpatialWorldModelV7(size="R7conv", n_history=2)
    assert model.param_counts()["model_total"] == 2_693_059


if __name__ == "__main__":
    torch.set_num_threads(1)
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}", flush=True)
    print(f"ALL {len(tests)} PILOT TESTS PASSED", flush=True)
