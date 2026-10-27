"""toy_plumbing.py tests on a tiny random qwen3_5 (CPU, no downloads): python backbone/think/test_toy_plumbing.py   (or pytest)."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import traceback
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import toy_plumbing as Y  # noqa: E402
import board as B  # noqa: E402
import train as T  # noqa: E402
import test_think1_board as TB  # noqa: E402

CPU = torch.device("cpu")


def test_toy_data():
    train, ev = Y.make_splits(2000, 500, 0)
    assert len(train) == 2000 and len(ev) == 500
    assert not ({r["key"] for r in train} & {r["key"] for r in ev}), "eval stories also in train"
    assert len({r["key"] for r in train}) == 2000 and len({r["visit_id"] for r in train + ev}) == 2500
    assert len({r["answer"] for r in train}) == 10 and len(Y.PLACES) == 10 and len(set(Y.NAMES)) == len(Y.NAMES)
    r = train[0]
    a, b, place = r["key"]
    assert r["context"] == f"{a} is with {b}. {b} is in the {place}." and r["question"] == f"Where is {a}?" and r["answer"] == f"the {place}" and a != b
    assert Y.make_rows(50, 3) == Y.make_rows(50, 3)
    print("TOY data: 2,000 train / 500 eval distinct two-hop rows, 10 places, eval stories not in train, deterministic")


def test_toy_answer_pass_never_sees_the_story():
    """Same question, same slot K/V, different stories of equal length: the answer-side logits are identical (no leak through attention or DeltaNet state),
    while slot K/V made from the two stories differ and, with open gates, change the logits."""
    lm, tok = TB.tiny()
    runner, enc = T.Runner(lm), T.Encoder(tok, 512)
    board = TB.make_board(lm, tok, K=4, alpha=1.0)
    r1 = dict(context="Ana is with Bo. Bo is in the mill.", question="Where is Ana?", answer="the mill")
    r2 = dict(context="Ana is with Cy. Cy is in the cave.", question="Where is Ana?", answer="the cave")
    with torch.no_grad():
        (C1, m1, p1), (Q1, mq1, l1), ans = Y.toy_inputs(runner, enc, [r1], CPU)
        (C2, m2, p2), (Q2, mq2, l2), _ = Y.toy_inputs(runner, enc, [r2], CPU)
        assert torch.equal(p1, p2)
        kv1 = B.think(board, runner, C1, m1, p1, 2, keep={2}, stats=False)[0][2]
        kv2 = B.think(board, runner, C2, m2, p2, 2, keep={2}, stats=False)[0][2]
        gate = board.gate()
        a = B.answer_logits(runner, gate, Q1, mq1, p1, l1, ans, kv1)[0]
        b = B.answer_logits(runner, gate, Q2, mq2, p2, l2, ans, kv1)[0]
        c = B.answer_logits(runner, gate, Q2, mq2, p2, l2, ans, kv2)[0]
        z = B.answer_logits(runner, torch.zeros_like(gate), Q2, mq2, p2, l2, ans, kv2)[0]
        zero = B.answer_logits(runner, gate, Q1, mq1, p1, l1, ans, B.zero_notes_kv(runner, board, p1))[0]
    assert torch.equal(a, b), "answer logits depend on the story with the notes fixed: leak"
    assert float((a - c).abs().max()) > 1e-4, "different stories give the same slot K/V"
    assert float((c - z).abs().max()) > 1e-4 and float((a - zero).abs().max()) > 1e-4
    print(f"TOY no leak: logits identical for two stories with the same notes; notes change them by {float((a - c).abs().max()):.3g}")


def test_toy_question_cache_matches_a_plain_prefill():
    """With p = len(question prompt) - 1 the shifted positions start at 0, so the question-only cache equals B.prefill of the question prompt."""
    lm, tok = TB.tiny()
    runner, enc = T.Runner(lm), T.Encoder(tok, 512)
    qs = [enc.ids("Where is Ana? [answer]"), enc.ids("Where is Kim? [answer]")]
    p = torch.tensor([len(q) - 1 for q in qs])
    C, mask, last = Y.question_cache(runner, qs, p)
    C0, mask0, p0 = B.prefill(runner, qs)
    assert torch.equal(mask, mask0) and torch.equal(p, p0) and torch.equal(last, B.last_ids(qs, CPU))
    i = [j for j, t in enumerate(runner.cfg.layer_types) if t == "full_attention"][0]
    assert torch.allclose(C.layers[i].keys, C0.layers[i].keys, atol=1e-6) and torch.allclose(C.layers[i].values, C0.layers[i].values, atol=1e-6)
    C2, _, _ = Y.question_cache(runner, qs, p + 7)  # a longer story: the keys are rotated further, so they differ
    assert not torch.allclose(C2.layers[i].keys, C0.layers[i].keys, atol=1e-4)
    print("TOY question cache == plain prefill at p = len - 1; shifts with the story's p")


def test_toy_verdict_rules_and_compare():
    ev = lambda t, s, z: dict(em_true=t, em_swap=s, em_zero=z)
    assert Y.verdict(ev(0.95, 0.10, 0.10))[0] == "pass" and Y.verdict(ev(0.90, 0.20, 0.20))[0] == "pass"
    assert Y.verdict(ev(0.95, 0.25, 0.10))[0] == "not shown" and Y.verdict(ev(0.95, 0.10, 0.25))[0] == "not shown" and Y.verdict(ev(0.5, 0.1, 0.1))[0] == "not shown"
    assert Y.verdict(ev(0.20, 0.1, 0.1))[0] == "bug" and Y.verdict(ev(0.10, 0.1, 0.1))[0] == "bug"
    assert Y.verdict(ev(0.95, 0.90, 0.1))[0] == "bug" and Y.verdict(ev(0.95, 0.86, 0.1))[0] == "bug" and Y.verdict(ev(0.95, 0.80, 0.1))[0] == "not shown"
    assert Y.swap_in_batch(["a", "a", "b", "c"]) == [2, 2, 3, 0] and Y.swap_in_batch(["a", "a"]) == [0, 1]
    ev_list = [dict(step=50, em_true=0.5), dict(step=100, em_true=0.92)]
    assert Y.first_ge90(ev_list) == 100 and Y.first_ge90(ev_list[:1]) is None
    mk = lambda s: dict(alpha_init=0.0, first_ge90_step=s)
    assert Y.compare(mk(500), mk(200))["starvation_shown"] is True and Y.compare(mk(400), mk(200))["starvation_shown"] is False
    assert Y.compare(mk(None), mk(200))["starvation_shown"] is True and Y.compare(mk(100), mk(None))["starvation_shown"] is None
    print("TOY verdict: pass / bug / not shown thresholds as section 9; gate check compares first >= 90% steps")


def run_tiny(alpha, tmp, steps=4, extra=()):
    a = Y.parse(["--smoke", "--device", "cpu", "--out", tmp, "--alpha-init", str(alpha), "--steps", str(steps), "--bsz", "8", "--micro-bsz", "4", "--lmax", "2",
                 "--n-train", "32", "--n-eval", "12", "--eval-every", "2", "--k", "4", *extra])
    res = Y.run(a)
    return res, json.loads((Path(tmp) / f"result_toy_s0_a{alpha:g}.json").read_text())


def test_toy_end_to_end_tiny():
    with tempfile.TemporaryDirectory() as tmp:
        r0, j0 = run_tiny(0.0, tmp)
        r3, j3 = run_tiny(0.3, tmp)
        assert j0["alpha_init"] == 0.0 and j3["alpha_init"] == 0.3 and j0["steps"] == 4 and j0["n_train"] == 32 and j0["n_eval"] == 12 and j0["lora"] is True
        for j in (j0, j3):
            assert j["aborted"] is None and [e["step"] for e in j["train"]["evals"]] == [2, 4] and len(j["train"]["step_losses"]) == 4
            assert j["verdict"] in ("pass", "bug", "not shown") and j["verdict_reason"] and j["final"] == j["train"]["evals"][-1]
            assert len(j["train"]["grad_norm_first100"]) == 4 and set(j["train"]["grad_norm_first100"][0]) == {"step", "alpha", "e0eta", "refiner", "lora"}
            for e in j["train"]["evals"]:
                assert e["n"] == 12 and all(0 <= e[k] <= 1 for k in ("em_true", "em_swap", "em_zero", "em_gates_off")) and "refiner_grad_norm" in e
        # section 3.1 on the toy: shut gates starve the refiner (only the step penalty reaches it, ~1e-4); open gates give it a real gradient (~1e-2)
        g0, g3 = j0["train"]["grad_norm_first100"][0], j3["train"]["grad_norm_first100"][0]
        assert g0["alpha"] > 0 and 0 < g0["refiner"] < 0.1 * g3["refiner"], (g0, g3)
        assert abs(j3["train"]["evals"][0]["alpha_abs"] - 0.2913) < 0.02 and j0["train"]["evals"][0]["alpha_abs"] < 0.01
        # the verdict is the rule applied to the final eval
        assert j3["verdict"] == Y.verdict(j3["final"])[0]
        cmp = Y.compare(j0, j3)
        assert set(cmp) == {"starvation_shown", "why", "alpha0", "alpha03"}
    print(f"TOY end to end (tiny, 4 steps): verdicts {j0['verdict']} / {j3['verdict']}; refiner grad norm at step 1: {g0['refiner']:.3g} (a=0) vs {g3['refiner']:.3g} (a=0.3)")


def test_toy_no_lora_board_only():
    with tempfile.TemporaryDirectory() as tmp:
        a = Y.parse(["--smoke", "--device", "cpu", "--out", tmp, "--steps", "2", "--bsz", "4", "--micro-bsz", "4", "--lmax", "1", "--n-train", "8", "--n-eval", "6",
                     "--eval-every", "2", "--k", "4", "--no-lora", "--alpha-init", "0.3", "--seed", "1"])
        res = Y.run(a)
        assert res["lora"] is False and set(res["train"]["grad_norm_first100"][0]) == {"step", "alpha", "e0eta", "refiner"} and (Path(tmp) / "result_toy_s1_a0.3.json").exists()
    print("TOY --no-lora trains the board only")


def run_all():
    tests = [test_toy_data, test_toy_answer_pass_never_sees_the_story, test_toy_question_cache_matches_a_plain_prefill, test_toy_verdict_rules_and_compare,
             test_toy_end_to_end_tiny, test_toy_no_lora_board_only]
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
    print("toy_plumbing tests:", "ALL PASSED" if not fails else f"FAILED {fails}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
