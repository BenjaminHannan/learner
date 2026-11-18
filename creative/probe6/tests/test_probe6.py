import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import p6common as C
import dev_analyze as D
import test_stage as T


def mem(n, replies):
    return [dict(pool="p", task="x", try_idx=i, success=False, final_reply=r, k=f"k{i}") for i, r in enumerate(replies)]


def test_auroc_basic():
    assert C.auroc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]) == 1.0
    assert C.auroc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == 0.0
    assert C.auroc([0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0]) == 0.5
    assert C.auroc([0.9, 0.3, 0.6, 0.1], [1, 1, 0, 0]) == 0.75
    assert C.auroc([1, 2], [1, 1]) is None


def test_gate_below_threshold_is_test_t():
    m = mem(3, ["done", "Which one?", "ok"])
    tt = {"k0": 0.9, "k1": 0.5, "k2": 0.7}
    assert C.gate_pick(m, tt, {}, 0.3, 0.5)["k"] == "k0"          # P(ask) < t: plain TEST-T, no question needed


def test_gate_at_threshold_picks_asking_try():
    m = mem(3, ["done", "Which one?", "ok"])
    tt = {"k0": 0.9, "k1": 0.5, "k2": 0.7}
    assert C.gate_pick(m, tt, {}, 0.5, 0.5)["k"] == "k1"          # >= t (inclusive): restrict to tries containing '?'


def test_gate_best_among_askers_and_self_tiebreak():
    m = mem(4, ["a?", "b?", "c", "d?"])
    tt = {"k0": 0.5, "k1": 0.8, "k2": 1.0, "k3": 0.8}
    sf = {"k1": 0.2, "k3": 0.6}
    assert C.gate_pick(m, tt, sf, 0.9, 0.5)["k"] == "k3"          # tie on TEST-T between k1/k3 -> higher SELF


def test_gate_falls_back_when_no_try_asks():
    m = mem(2, ["x", "y"])
    assert C.gate_pick(m, {"k0": 0.1, "k1": 0.9}, {}, 1.0, 0.5)["k"] == "k1"


def test_gate_full_tie_lowest_try_and_none_pask():
    m = mem(3, ["a", "b?", "c?"])
    tt = {"k0": 0.5, "k1": 0.5, "k2": 0.5}
    assert C.gate_pick(m, tt, {}, 1.0, 0.5)["k"] == "k1"
    assert C.gate_pick(m, tt, {}, None, 0.5)["k"] == "k0"          # missing judge score -> TEST-T


def test_oracle_and_trap_labels():
    assert C.is_trap({"scenario": "clarify"}) and C.is_trap({"scenario": "confirm_irreversible"}) and not C.is_trap({"scenario": "multi_step"})
    assert C.oracle_p({"scenario": "clarify"}) == 1.0 and C.oracle_p({"scenario": "parallel"}) == 0.0


def test_choose_arm_and_t():
    assert D.choose({"J-LFM3": 0.7, "J-D1": 0.7, "J-HAIKU": 0.99}) == "J-LFM3"     # tie -> LFM3; Haiku never
    assert D.choose({"J-LFM3": 0.6, "J-D1": 0.7, "J-HAIKU": 0.99}) == "J-D1"
    assert D.choose({"J-LFM3": 0.6, "J-D1": None}) == "J-LFM3"
    assert D.choose_t({0.3: {"all": 50.0}, 0.5: {"all": 60.0}, 0.7: {"all": 60.0}}) == 0.7


def test_verdict():
    v = T.verdict(57.3, 62.5, 80.0)
    assert v["verdict"] == "PASS"
    assert T.verdict(57.3, 62.5, 75.0)["verdict"] == "INCONCLUSIVE"       # A2 fails
    assert T.verdict(57.3, 58.3, 90.0)["verdict"] == "PROVED WRONG"
    assert T.verdict(57.3, 60.0, 90.0)["verdict"] == "INCONCLUSIVE"


def test_judge_prompt_has_no_tries():
    tgt, non = C.dev_tasks()
    assert len(tgt) == 48 and len(non) == 200 and not {t["id"] for t in tgt} & {t["id"] for t in non}
    p = C.judge_prompt(tgt[0])
    assert tgt[0]["user"] in p and p.endswith("Answer yes or no.")
