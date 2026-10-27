"""CPU tests for Addendum F (arm br: the model's own middle block looped a random number of times; aplong: its compute-matched plain-LoRA control):
python -m pytest backbone/think/test_br_arm.py

Covers: the loop schedule (fixed by its seed, ramped mean, capped, ~2.8 mean at the real size), the compute ratio, the answer-stable halting readout and
Spearman helper, block_order at the loop counts br is scored at, and a short br / aplong run end to end (tags, schedule record, loops reset, aplong's steps).
"""
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import test_think1 as TK  # noqa: E402

K, T = TK.K, TK.T


def test_loop_schedule_fixed_ramped_capped():
    a, b = K.loop_schedule(1254, 5000), K.loop_schedule(1254, 5000)
    assert a == b and a != K.loop_schedule(1254, 5001) and len(a) == 1254
    assert min(a) >= 1 and max(a) <= K.BR_TRAIN_MAX
    ramp = int(K.BR_RAMP * 1254)
    assert sum(a[:50]) / 50 < 1.3  # mean starts near 1
    tail = a[ramp:]
    m = sum(tail) / len(tail)  # 1 + Poisson(3) capped at 6 has mean ~3.82
    assert 3.4 < m < 4.2, m
    assert 2.5 < sum(a) / len(a) < 3.1  # the real size's mean (2.80 for seed 5000)


def test_compute_ratio():
    assert K.compute_ratio([1, 1, 1], 24, 4) == 1.0
    assert math.isclose(K.compute_ratio([4], 24, 4), 36 / 24)
    assert math.isclose(K.compute_ratio([1, 3], 24, 4), (24 + 32) / 48)
    ls = K.loop_schedule(1254, 5000)
    assert round(1254 * K.compute_ratio(ls, 24, 4)) == 1254 + round(sum(4 * (r - 1) for r in ls) / 24)


def test_block_order_at_eval_loops():
    for r in K.BR_EVAL_LOOPS:
        o = T.block_order(24, 8, r, 4)
        assert len(o) == 24 + 4 * (r - 1) and o[:8] == list(range(8)) and o[-12:] == list(range(12, 24))
    assert T.block_order(24, 8, 1, 4) == list(range(24))


def test_spearman():
    assert math.isclose(K.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
    assert math.isclose(K.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
    assert K.spearman([1, 1, 1], [1, 2, 3]) is None and K.spearman([1], [1]) is None
    # ties get average ranks: x ranks 0, 1.5, 1.5, 3; y ranks 0, 1, 2, 3
    rx, ry = [0, 1.5, 1.5, 3], [0, 1, 2, 3]
    mx, my = sum(rx) / 4, sum(ry) / 4
    want = sum((p - mx) * (q - my) for p, q in zip(rx, ry)) / math.sqrt(sum((p - mx) ** 2 for p in rx) * sum((q - my) ** 2 for q in ry))
    assert math.isclose(K.spearman([1, 2, 2, 3], [5, 6, 7, 8]), want)
    rng = random.Random(0)
    x = [rng.random() for _ in range(50)]
    assert math.isclose(K.spearman(x, [v ** 3 for v in x]), 1.0)


def test_halting_readout():
    loops = (1, 2, 4, 8)
    rows = [dict(depth=1), dict(depth=1), dict(depth=4), dict(depth=5), dict(depth=0)]
    preds = {1: ["a", "x", "p", "u", "z"], 2: ["a", "y", "q", "v", "z"], 4: ["a", "y", "r", "w", "k"], 8: ["b", "y", "r", "t", "k"]}
    hits = {1: ["1", "0", "0", "0", "1"], 2: ["1", "1", "0", "0", "1"], 4: ["0", "1", "1", "1", "0"], 8: ["0", "1", "1", "0", "0"]}
    h = K.halting_readout(rows, preds, hits, loops=loops)
    # row 0 stops at 2 (a == a), row 1 at 4 (y == y), row 2 at 8 (r == r), row 3 never repeats: 8; row 4 at 2
    assert math.isclose(h["mean_loops"], (2 + 4 + 8 + 8 + 2) / 5)
    assert math.isclose(h["acc"], (1 + 1 + 1 + 0 + 1) / 5)
    assert h["by_depth"]["1"] == dict(n=2, mean_loops=3.0, acc=1.0) and h["by_depth"]["4"]["mean_loops"] == 8 and h["by_depth"]["0"]["n"] == 1
    assert list(h["by_depth"]) == ["0", "1", "4", "5"]
    assert math.isclose(h["spearman_depth_loops"], K.spearman([1, 1, 4, 5], [2, 4, 8, 8]))  # depth 0 left out
    assert "else 8" in h["rule"]


def test_br_and_aplong_runs():
    """br trains with the schedule, resets to BR_MAIN, scores validation at every BR_EVAL_LOOPS (with answers) and dev at main only, and writes the halting
    readout; aplong trains round(steps * ratio) plain steps from the same schedule and is scored like aplus."""
    TK.fixture()
    br = TK.arm_args("br", 0, "br", steps=6)
    assert K.run_arm(br) == 0
    r = TK.load(br)
    ls = K.loop_schedule(6, 5000)
    assert r["loop_schedule"]["seed"] == 5000 and math.isclose(r["loop_schedule"]["mean"], sum(ls) / 6)
    assert r["loop_schedule"]["eval_loops"] == list(K.BR_EVAL_LOOPS) and r["loop_schedule"]["main"] == K.BR_MAIN
    assert r["train"]["loops_hist"] == {str(k): ls.count(k) for k in sorted(set(ls))}
    assert set(r["eval"]["validation"]) == {f"r{k}" for k in K.BR_EVAL_LOOPS} | {"main"} and set(r["eval"]["dev"]) == {f"r{K.BR_MAIN}", "main"}
    v = r["eval"]["validation"]
    assert all(len(v[f"r{k}"]["preds"]) == v[f"r{k}"]["n"] for k in K.BR_EVAL_LOOPS) and "preds" not in v["main"] and "preds" not in r["eval"]["dev"][f"r{K.BR_MAIN}"]
    assert v["main"]["hits"] == v[f"r{K.BR_MAIN}"]["hits"]
    assert set(r["halting"]) == {"acc", "mean_loops", "by_depth", "spearman_depth_loops", "rule"} and 1 <= r["halting"]["mean_loops"] <= max(K.BR_EVAL_LOOPS)
    assert r["stage1_adapter"].endswith("a_s0/adapter") and r["steps_stage2"] == 6
    ap = TK.arm_args("aplong", 0, "aplong", steps=6)
    assert K.run_arm(ap) == 0
    q = TK.load(ap)
    ratio = q["loop_schedule"]["compute_ratio"]
    assert math.isclose(ratio, r["loop_schedule"]["compute_ratio"]) and q["steps_stage2"] == round(6 * ratio)
    assert len(q["train"]["step_losses"]) == q["steps_stage2"] and "loops_hist" not in q["train"]
    assert set(q["eval"]["validation"]) == {"main"} and set(q["eval"]["dev"]) == {"main"}
    print(json.dumps(dict(br_mean=r["loop_schedule"]["mean"], ratio=ratio, aplong_steps=q["steps_stage2"], halting=r["halting"]["mean_loops"])))


def test_preflight_br_worst_case(tmp_path):
    """preflight --arms br forces every step to the largest training loop count and restores loop_schedule afterwards."""
    import preflight as PF
    fx = TK.fixture()
    sched = K.loop_schedule
    argv = ["--smoke", "--arms", "br", "--a-adapter", str(Path(fx["root"]) / "base" / "a_s0" / "adapter"), "--data", str(fx["data"]), "--out", str(tmp_path / "pf"),
            "--steps", "3"]
    assert PF.main(argv) == 0 and K.loop_schedule is sched
    rep = json.loads((tmp_path / "pf" / "preflight.json").read_text())
    assert set(rep) == {"br"}
    r = json.loads((tmp_path / "pf" / "br_s0" / "result_br_s0.json").read_text())
    assert r["train"]["loops_hist"] == {str(K.BR_TRAIN_MAX): 3}
