"""Tests for Recall-then-read stage 1: RRF + trimming, condition-W deletion, R/D3 ledger equality (plus key parsing and the exact test). CPU only, no model."""
import json
from pathlib import Path

import pytest

from sleep2.recallread import arms as A
from sleep2.recallread import keypass, retrieve, stats
from sleep2.recallread.alias_table import AliasTable
from sleep2.recallread.index import Index
from sleep2.recallread.make_condition_w import build_w_index, check_deletion, deleted_turns
from sleep2.recallread.run_eval import FakeRunner
from sleep2.recallread.world import FROZEN


def mk_turns():
    T = [
        (0, 1, "Kizibra has Kreilozho as a mentor and says card games are best"),     # hop 1
        (1, 2, "Kreilozho is based out in Foperukin which is where i am heading"),    # hop 2
        (2, 2, "what are good campfire games for the weekend"),
        (3, 3, "Kizibra lent me a tent for the weekend trip"),
        (4, 3, "Zorvan owns a boat called Tradepil"),
        (5, 4, "Zorvan was born in Quenbra last spring"),
        (6, 5, "totally unrelated note about dinner and chicken rice"),
    ]
    return [dict(turn_id=i, day=d, text=t, mentions=[]) for i, d, t in T]


CHAIN = dict(id="th000", start="Kizibra", bridge="Kreilozho", answer="Foperukin", hop1_turns=[0], hop2_turns=[1])


# ---------------------------------------------------------------- RRF + trimming
def test_rrf_scores_and_order():
    fused = retrieve.rrf([[10, 11, 12], [12, 10], [13]], k=60)
    sc = dict(fused)
    assert sc[10] == pytest.approx(1 / 61 + 1 / 62)
    assert sc[12] == pytest.approx(1 / 63 + 1 / 61)
    assert sc[11] == pytest.approx(1 / 62)
    assert sc[13] == pytest.approx(1 / 61)
    # 10 (1/61+1/62) > 12 (1/63+1/61) > 11 (1/62) vs 13 (1/61): 13 is above 11
    assert [d for d, _ in fused] == [10, 12, 13, 11]


def test_rrf_tie_break_is_turn_id():
    assert [d for d, _ in retrieve.rrf([[5], [3]])] == [3, 5]


def test_trim_respects_budget_and_stops_at_first_overflow():
    idx = Index(mk_turns())
    cost = lambda s: len(s.split())  # noqa: E731
    line = lambda d: cost(retrieve.render_turn(idx.get(d)) + "\n")  # noqa: E731
    order = [0, 1, 2, 3]
    kept, used = retrieve.trim(order, idx, cost, budget=line(0) + line(1))
    assert kept == [0, 1] and used == line(0) + line(1)
    kept, used = retrieve.trim(order, idx, cost, budget=line(0) + line(1) - 1)
    assert kept == [0]           # stops at the first turn that does not fit, even if a later short one would
    kept, used = retrieve.trim(order, idx, cost, budget=10_000)
    assert kept == order and used <= 10_000


def test_retrieve_fuses_key_hits_and_trims_to_k_tokens():
    idx = Index(mk_turns())
    cost = lambda s: len(s.split())  # noqa: E731
    r = retrieve.retrieve(idx, ["where does the mentor of Kizibra live", "Kreilozho"], cost, budget=40)
    assert r.k_tokens <= 40 and r.kept == r.fused[:len(r.kept)]
    assert 1 in r.fused                      # hop 2 is only reachable through the key 'Kreilozho'
    assert 1 not in retrieve.retrieve(idx, ["where does the mentor of Kizibra live"], cost, budget=40).fused


# ---------------------------------------------------------------- condition W
def test_condition_w_deletes_hop1_and_keeps_hop2():
    turns = mk_turns()
    dele = deleted_turns(turns, [CHAIN])
    assert dele == {0}
    assert check_deletion(turns, [CHAIN], dele) == []
    widx, d2 = build_w_index(turns, [CHAIN])
    assert d2 == dele and len(widx) == len(turns) - 1
    assert not widx.contains(0) and widx.contains(1)
    assert 0 not in widx.search("Kizibra mentor Kreilozho")           # the deleted turn can no longer be found
    assert 1 in widx.search("Kreilozho Foperukin")                    # hop 2 still can, by the bridge name


def test_condition_w_also_deletes_untagged_start_bridge_paraphrase():
    turns = mk_turns() + [dict(turn_id=7, day=5, text="kizibra said Kreilozho taught them everything", mentions=[])]
    assert deleted_turns(turns, [CHAIN]) == {0, 7}


def test_condition_w_checker_flags_a_deleted_hop2_turn_and_a_surviving_link():
    turns = mk_turns()
    assert any("hop-2 turn was deleted" in p for p in check_deletion(turns, [CHAIN], {0, 1}))
    assert any("still links" in p for p in check_deletion(turns, [CHAIN], set()))


@pytest.mark.skipif(not (FROZEN / "items.json").exists() or not (FROZEN / "week2.json").exists(), reason="frozen items not built")
def test_condition_w_on_the_real_world():
    from sleep2.recallread.world import load_world, user_turns
    P = json.loads((FROZEN / "items.json").read_text())
    turns = user_turns(load_world(FROZEN / "week2.json"))
    w = [c for c in P["chains"] if c["W"]]
    widx, dele = build_w_index(turns, w)
    assert sorted(dele) == P["w_deleted_turns"] and check_deletion(turns, w, dele) == []
    for c in w:
        assert not any(widx.contains(t) for t in c["hop1_turns"]) and all(widx.contains(t) for t in c["hop2_turns"])
    full = Index(turns)
    assert len(widx) == len(full) - len(dele)


# ---------------------------------------------------------------- ledger equality
def rows_for():
    base = dict(item="th000", gold="Foperukin", start="Kizibra", bridge="Kreilozho", hop1_turns=[0], hop2_turns=[1], dev=False, index="full")
    return [dict(base, row_id="th000:nat", split="twohop_nat", q="Where does the mentor of Kizibra live?"),
            dict(base, row_id="th000:W", split="W_nat", q="Where does the mentor of Kizibra live?", index="W")]


def make_env():
    fr = FakeRunner()
    turns = mk_turns()
    wi, _ = build_w_index(turns, [CHAIN])
    al = AliasTable([dict(alias="Kizibra's mentor", entity="Kreilozho", relation="mentor")])
    return A.Env(fr.render, fr.gen, fr.count_tokens, Index(turns), wi, al, AliasTable([]))


def test_ledger_R_and_D3_have_equal_budgets():
    env, rows = make_env(), rows_for()
    r = A.run_arm("R", rows, env, "s1")
    d3 = A.run_arm("D3", rows, env)
    summ = A.assert_equal_budget(r, d3)
    assert summ["rounds_a"] == 1 and summ["rounds_b"] == 2        # D3 gets the extra retrieval round by design
    assert all(x["ledger"]["key_calls"] == 1 and x["ledger"]["key_max_new"] == keypass.KEY_MAX_NEW == 40 for x in r + d3)
    assert all(x["ledger"]["k_tokens_used"] <= retrieve.K_TOKENS for x in r + d3)


def test_ledger_rejects_unequal_budgets():
    env, rows = make_env(), rows_for()
    r = A.run_arm("R", rows, env, "s1")
    d3 = A.run_arm("D3", rows, env)
    bad = json.loads(json.dumps(d3))
    bad[0]["ledger"]["key_max_new"] = 60
    with pytest.raises(AssertionError):
        A.assert_equal_budget(r, bad)
    bad = json.loads(json.dumps(d3))
    bad[1]["ledger"]["k_tokens_budget"] = 3000
    with pytest.raises(AssertionError):
        A.assert_equal_budget(r, bad)
    over = json.loads(json.dumps(r))
    over[0]["ledger"]["key_new_tokens"] = [41]                      # decoded more than the budget
    with pytest.raises(AssertionError):
        A.assert_equal_budget(over, d3)
    with pytest.raises(AssertionError):
        A.assert_equal_budget(r[:1], d3)


def test_w_rows_use_the_post_deletion_index():
    env, rows = make_env(), rows_for()
    res = {x["row_id"]: x for x in A.run_arm("D0", rows, env)}
    assert res["th000:nat"]["hop1_in_ctx"] is True and res["th000:W"]["hop1_in_ctx"] is False


def test_all_arms_run_and_lora_arms_need_an_adapter():
    env, rows = make_env(), rows_for()
    for arm in A.ALL_ARMS:
        if arm == "R_tau":
            continue
        out = A.run_arm(arm, rows, env, "s1" if arm in A.LORA_ARMS else None)
        assert len(out) == 2 and all(o["ledger"]["k_tokens_used"] <= retrieve.K_TOKENS for o in out)
    with pytest.raises(ValueError):
        A.run_arm("R", rows, env, None)
    r = A.run_arm("R", rows, env, "s1")
    tune = A.tune_tau(rows, env, "s1", r)
    assert "tau" in tune and tune["dev_table"]
    rt = A.run_arm("R_tau", rows, env, "s1", {"tau": tune["tau"], "replay": {x["row_id"]: x for x in r}})
    assert [x["row_id"] for x in rt] == [x["row_id"] for x in r]


# ---------------------------------------------------------------- key pass and stats
def test_parse_keys():
    assert keypass.parse_keys("Keys: my sister -> Maya; Maya -> dentist Dr. Lee\nextra") == ["my sister -> Maya", "Maya -> dentist Dr. Lee"]
    assert keypass.parse_keys("a; b; c; d; e; f") == ["a", "b", "c", "d"]
    assert keypass.parse_keys("none") == [] and keypass.parse_keys("") == []
    assert keypass.parse_keys("x; x; y") == ["x", "y"]


def test_key_logprobs_and_gate():
    pieces = ["my", " sister", " ->", " Maya", ";", " Maya", " ->", " dentist"]
    lps = [-1.0, -1.0, -1.0, -1.0, -0.0, -3.0, -3.0, -3.0]
    keys = keypass.parse_keys("".join(pieces))
    ml = keypass.key_logprobs(pieces, lps, keys)
    assert ml[0] == pytest.approx(-1.0)
    assert ml[1] == pytest.approx(-3.0)
    assert keypass.gate(keys, ml, -2.0) == [keys[0]] and keypass.gate(keys, ml, None) == keys


def test_mcnemar_exact():
    assert stats.mcnemar_exact(0, 0) == 1.0
    assert stats.mcnemar_exact(1, 7) == pytest.approx(2 * (1 + 8) / 256)
    assert stats.mcnemar_exact(10, 10) == 1.0


def test_alias_table_expansion_and_w_blindness():
    t = AliasTable([dict(alias="Kizibra's mentor", entity="Kreilozho", relation="mentor"), dict(alias="owner of Tradepil", entity="Zorvan", relation="owner")])
    assert t.expand("Where does the mentor of Kizibra live?") == ["Kreilozho"]
    assert t.expand("Who is Zorvan's favourite cousin?") == []
    env, rows = make_env(), rows_for()
    res = {x["row_id"]: x for x in A.run_arm("D4", rows, env)}
    assert res["th000:nat"]["keys"] == ["Kreilozho"] and res["th000:W"]["keys"] == []   # the W table was built without the hop-1 turn
