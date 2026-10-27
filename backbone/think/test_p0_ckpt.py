"""p0_ckpt.py tests on a tiny random qwen3_5 (CPU, no downloads): python backbone/think/test_p0_ckpt.py   (or pytest). Uses test_think1's smoke fixture for the stage-1 adapter."""
from __future__ import annotations

import contextlib
import json
import sys
import time
import traceback
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import p0_ckpt as P  # noqa: E402
import board as B  # noqa: E402
import think1 as K  # noqa: E402
import test_think1 as TT  # noqa: E402

_CK = {}


def ckpt(arm, extra=()):
    """A finished smoke run of `arm` (6 joint steps from the shared stage-1 adapter); cached."""
    key = (arm, tuple(extra))
    if key not in _CK:
        fx = TT.fixture()
        a = TT.arm_args(arm, 0, "p0_" + arm + "_".join(extra).replace("-", ""), steps=6, extra=extra)
        assert K.run_arm(a) == 0
        _CK[key] = (a.out, fx["data"])
    return _CK[key]


def p0(arm, extra=(), more=()):
    out, data = ckpt(arm, extra)
    a = P.parse(["--ckpt", out, "--data", str(data), "--smoke", "--device", "cpu", "--limit", "10", "--eval-bsz", "4", "--out", str(Path(out) / "p0.json"), *more])
    return P.run(a), a


def test_p0_tj_readings():
    res, a = p0("tj")
    on_disk = json.loads(Path(a.out).read_text())
    assert on_disk["arm"] == "tj" and on_disk["rows"] == 10 and on_disk["lmax"] == 4 and on_disk["alpha_init"] == 0.0 and on_disk["smoke"]
    w = res["wiring"]
    assert w["gate"] == 0.5 and w["rows"] == 10 and w["max_abs_dlogit"] > 1e-3 and w["bug"] is False and res["rules"]["row1_wiring_bug"] is False, w
    g = res["gates"]
    assert 0 < g["mean_abs_tanh"] < 0.1 and len(g["per_layer"]) == 2 and res["rules"]["row2_gate_closed"] is True, g
    d = res["drift"]
    assert "skipped" not in d and set(d["parts"]) == set(P.BOARD_PARTS) and set(d["groups"]) == {"alpha", "e0eta", "refiner"}, d
    assert d["groups"]["refiner"]["delta_norm"] > 0 and d["refiner_rel"] > 0 and d["parts"]["alpha"]["rel"] is None and d["parts"]["alpha"]["delta_norm"] > 0  # alpha started at 0: no relative drift
    n = res["notes"]
    assert n["rows"] == 10 and n["stories"] >= 2 and n["mean_sq_note"] > 0 and n["ratio_across_rows"] >= 0 and n["ratio_across_stories"] is not None
    assert n["lap_change"]["first_lap"] == 1 and len(n["lap_change"]["values"]) == 4 and all(v >= 0 for v in n["lap_change"]["values"])
    assert "skipped" in res["blind"] and "skipped" in res["bridge"] and res["env"]["gpu"] == "cpu"
    print(f"P0 tj: wiring max|dlogit| {w['max_abs_dlogit']:.3g}, mean|tanh a| {g['mean_abs_tanh']:.4f}, refiner drift {d['refiner_rel']:.3g}, story ratio {n['ratio_across_stories']:.3g}")


def test_p0_wiring_rule_fires_when_the_read_is_cut():
    """Negative control: with the board read disabled (what a wiring bug would do) the forced-gate reading is exactly 0 and the rule fires."""
    @contextlib.contextmanager
    def dead(runner, gate, slot_kv, read_from=None):
        yield
    real = B.reading
    B.reading = dead
    try:
        res, _ = p0("tj")
    finally:
        B.reading = real
    assert res["wiring"]["max_abs_dlogit"] == 0.0 and res["wiring"]["bug"] is True and res["rules"]["row1_wiring_bug"] is True
    print("P0 wiring rule: a cut read gives max|dlogit| 0 and bug = True")


def test_p0_drift_start_is_the_run_start_and_skips_when_not_deterministic():
    out, data = ckpt("tj")
    a = P.parse(["--ckpt", out, "--data", str(data), "--smoke", "--device", "cpu"])
    runner, board, tok, meta, start = P.load_ckpt(a, torch.device("cpu"), torch.float32)
    again = P.fresh_start(a, runner, tok, meta, torch.device("cpu"))
    assert all(torch.equal(start[k], again.state_dict()[k]) for k in start), "init is not deterministic given the seed"
    d = P.drift_reading(board, start, again)
    assert d["refiner_rel"] > 0
    # the saved e0_hat / eta moved from exactly that start, and a block built at the saved seed IS the one training began from
    with torch.no_grad():
        again.w_in.weight.add_(1.0)
    assert "not deterministic" in P.drift_reading(board, start, again)["skipped"]
    # alpha_init is read from the checkpoint: a run started at 0.3 has a non-zero start norm and a relative alpha drift
    out3, _ = ckpt("tj", ("--alpha-init", "0.3"))
    a3 = P.parse(["--ckpt", out3, "--data", str(data), "--smoke", "--device", "cpu"])
    runner3, board3, tok3, meta3, start3 = P.load_ckpt(a3, torch.device("cpu"), torch.float32)
    assert meta3["alpha_init"] == 0.3 and torch.allclose(start3["alpha"], torch.full_like(start3["alpha"], 0.3))
    d3 = P.drift_reading(board3, start3, P.fresh_start(a3, runner3, tok3, meta3, torch.device("cpu")))
    assert d3["parts"]["alpha"]["rel"] is not None and d3["parts"]["alpha"]["start_norm"] > 0
    print("P0 drift: start re-created bitwise from the seed, nondeterminism detected, alpha_init picked up from the checkpoint")


def test_p0_tf_blind_baselines():
    res, a = p0("tf", more=("--limit", "12"))
    b = res["blind"]
    assert "skipped" not in b and b["rows"] == 12 and b["swapped_n"] > 0, b
    for k in ("true", "zeroed", "gates_off", "swapped", "true_on_swapped_rows", "swap_cost", "zero_cost"):
        assert isinstance(b[k], float), (k, b)
    assert all(0 <= b[k] <= 1 for k in ("true", "zeroed", "gates_off", "swapped")), b
    # zero_notes_kv is exactly zero (nothing to attend to), so the zeroed and gates-off blind readings agree
    out, data = ckpt("tf")
    runner, board, tok, meta, _ = P.load_ckpt(P.parse(["--ckpt", out, "--data", str(data), "--smoke", "--device", "cpu"]), torch.device("cpu"), torch.float32)
    prompts = [[5, 6, 7, 8, 9], [5, 6, 7, 8, 9, 10, 11]]
    p = torch.tensor([len(x) - 1 for x in prompts])
    kv = B.zero_notes_kv(runner, board, p)
    assert len(kv) == 2 and kv[0][0].shape[0] == 2 and all(float(x.abs().max()) == 0.0 for k, v in kv for x in (k, v))  # zero in, zero out: the gates-off read
    assert b['zeroed'] == b['gates_off']
    rows = [dict(depth=2, visit_id="a"), dict(depth=2, visit_id="a"), dict(depth=2, visit_id="b"), dict(depth=3, visit_id="c")]
    part, same = P.swap_partners(rows)
    assert part == [2, 2, 0, None] and same == 0
    print(f"P0 tf blind: true {b['true']:.2f} zeroed {b['zeroed']:.2f} swapped {b['swapped']:.2f} (n={b['swapped_n']}); partners: same depth, other story first")
    res2, _ = p0("tj", more=("--blind", "on"))
    assert "skipped" not in res2["blind"]


def test_p0_main_writes_json():
    out, data = ckpt("tj")
    f = Path(out) / "main.json"
    assert P.main(["--ckpt", out, "--data", str(data), "--smoke", "--device", "cpu", "--limit", "6", "--eval-bsz", "3", "--out", str(f)]) == 0
    assert json.loads(f.read_text())["rows"] == 6


def run_all():
    tests = [test_p0_tj_readings, test_p0_wiring_rule_fires_when_the_read_is_cut, test_p0_drift_start_is_the_run_start_and_skips_when_not_deterministic,
             test_p0_tf_blind_baselines, test_p0_main_writes_json]
    fails = []
    for fn in tests:
        t0 = time.time()
        try:
            fn()
            print(f"PASS {fn.__name__} ({time.time() - t0:.0f}s)", flush=True)
        except Exception:
            traceback.print_exc()
            print(f"FAIL {fn.__name__}", flush=True)
            fails.append(fn.__name__)
    print("p0_ckpt tests:", "ALL PASSED" if not fails else f"FAILED {fails}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
