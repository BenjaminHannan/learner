"""No-network tests for Pick-1."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pools, judge_k2, judge_haiku, analyze as an  # noqa


def row(task, arm, i, ok, calls=(), reply="done"):
    tr = [dict(role="user", content="do it")]
    for n, a in calls:
        tr.append(dict(role="assistant", content="", tool_calls=[dict(id="x", type="function", function=dict(name=n, arguments=json.dumps(a)))]))
        tr.append(dict(role="tool", content="r" * 400))
    tr.append(dict(role="assistant", content=reply))
    return dict(task_id=task, arm=arm, try_idx=i, success=ok, transcript=tr, final_reply=reply)


def test_pools_ind_first_12_only():
    rows = [row("t1", "IND.s2", i, i == 3) for i in range(13)] + [row("t1", "MENU", i, False) for i in range(12)]
    rows += [row("t1", "HOT", 0, True), row("t9", "IND", 0, True), row("t1", "plain", 0, True)]
    out = pools.build(rows, ["t1"])
    assert len(out) == 24
    assert max(r["try_idx"] for r in out) == 11
    ind = [r for r in out if r["arm"] == "IND"]
    assert len(ind) == 12 and all(r["seed"] == 2 and r["pool"] == "t1|IND.s2" for r in ind)
    assert {r["seed"] for r in out if r["arm"] == "MENU"} == {1}
    assert "User request: do it" in out[0]["judge_text"]


def test_render_truncates_results():
    out = pools.build([row("t1", "MENU", 0, True, calls=[("f", {"a": 1})])], ["t1"])
    t = out[0]["judge_text"]
    assert "Tool call: f(" in t and "r" * 300 + "..." in t and "r" * 301 not in t and "Final reply: done" in t


def top(d):
    return [dict(token=k, logprob=math.log(v)) for k, v in d.items()]


def test_p_yes():
    assert abs(judge_k2.p_yes(top({" Yes": .3, "YES": .1, "yes": .1, "No": .4, " no": .1})) - 0.5) < 1e-9
    assert judge_k2.p_yes(top({"The": .5, "I": .5})) is None
    assert judge_k2.p_yes(top({"Yes": .2})) == 1.0
    assert judge_k2.p_yes(None) is None


def test_haiku_parse():
    assert judge_haiku.parse_score("8\nbecause") == 8 and judge_haiku.parse_score("10") == 10
    assert judge_haiku.parse_score("n/a") is None


def mk(pool, sigs, succ):
    return [dict(pool=pool, try_idx=i, signature=s, success=ok) for i, (s, ok) in enumerate(zip(sigs, succ))]


def test_pickers_and_ties():
    m = mk("p", ["a", "b", "b", "c"], [False, True, False, False])
    assert an.pick_vote(m)["try_idx"] == 1              # b most common, first b
    m2 = mk("q", ["a", "b", "c", "d"], [False, True, False, False])
    assert an.pick_vote(m2)["try_idx"] == 0             # all tied -> lowest try
    assert an.pick_best(m2, lambda r: 0.5)["try_idx"] == 0
    assert an.pick_best(m2, lambda r: [0.1, 0.9, 0.9, 0.2][r["try_idx"]])["try_idx"] == 1


def test_auroc():
    assert an.auroc([.9, .8, .2, .1], [1, 1, 0, 0]) == 1.0
    assert an.auroc([.1, .2, .8, .9], [1, 1, 0, 0]) == 0.0
    assert an.auroc([.5] * 4, [1, 0, 1, 0]) == 0.5
    assert abs(an.auroc([.9, .3, .5, .1], [1, 1, 0, 0]) - 0.75) < 1e-9
    assert an.auroc([1, 2], [1, 1]) is None


def test_evaluate_and_verdict():
    recs = mk("a|IND", ["x", "y", "y", "z"], [True, False, False, False]) + mk("b|IND", ["x", "y", "z", "w"], [False, False, True, False]) \
        + mk("c|IND", ["x", "y"], [False, False])
    k2 = {"a|IND|0": .9, "a|IND|1": .1, "a|IND|2": .1, "a|IND|3": .2, "b|IND|2": .8, "b|IND|0": .1, "b|IND|1": .2, "b|IND|3": .3}
    m = an.evaluate(recs, k2)       # c pool has no scores -> 0.5 each, k2_null counted
    assert m["n_pools"] == 3 and m["n_solvable"] == 2
    assert abs(m["pick_rate"]["RAND"]["all"] - 100 * (.25 + .25 + 0) / 3) < 1e-9
    assert m["pick_rate"]["SELF"]["all"] == 200 / 3 and m["pick_rate"]["SELF"]["solvable"] == 100
    assert m["pick_rate"]["VOTE"]["all"] == 0   # a: y modal (fail), b: first (fail), c: tie -> first (fail)
    assert an.verdict(m)["checks"]["P1"] and an.verdict(m)["checks"]["P2"]


def fake(R, V, S, SV, au):
    pr = {"RAND": dict(all=R), "VOTE": dict(all=V), "SELF": dict(all=S), "SELF-VOTE": dict(all=SV)}
    return dict(pick_rate=pr, auroc={"SELF": au})


def test_verdict_logic():
    assert an.verdict(fake(30, 35, 45, 40, .7))["verdict"] == "PASS"
    assert an.verdict(fake(30, 35, 44.9, 40, .7))["verdict"] == "INCONCLUSIVE"
    assert an.verdict(fake(30, 35, 45, 40, .69))["verdict"] == "INCONCLUSIVE"
    assert an.verdict(fake(30, 41, 45, 45.9, .8))["verdict"] == "INCONCLUSIVE"   # P2 fails
    assert an.verdict(fake(30, 41, 45, 46, .8))["verdict"] == "PASS"            # SELF-VOTE rescues P2
    assert an.verdict(fake(30, 20, 35, 30, .9))["verdict"] == "PROVED WRONG"
    assert an.verdict(fake(30, 20, 35.1, 30, .9))["verdict"] == "INCONCLUSIVE"
    assert an.verdict({"pick_rate": {"RAND": dict(all=1)}, "auroc": {}})["verdict"] == "NO JUDGE SCORES"


# ---- Pick-2 ----
def test_cut_option():
    rows = [row("t1", "MENU", 0, True, calls=[("f", {"a": 1})])]
    long_ = pools.build(rows, ["t1"], cut=1500)[0]["judge_text"]
    assert "r" * 400 in long_ and "r" * 300 + "..." not in long_
    assert "r" * 300 + "..." in pools.build(rows, ["t1"])[0]["judge_text"]   # default 300 unchanged
    assert "r" * 100 + "..." in pools.build(rows, ["t1"], cut=100)[0]["judge_text"]


def test_parse_think():
    p = judge_k2.parse_think
    assert p("ok.\nAnswer: yes\nConfidence: 8") == (8, True)
    assert p("Answer: No\nConfidence: 3") == (-3, True)
    assert p("Answer: **yes**\nConfidence: **10**") == (10, True)
    assert p("Answer: yes\nConfidence: 99") == (10, True)
    assert p("hmm, maybe 'Answer: yes' ... \nAnswer: no\nConfidence: 6") == (-6, True)   # last one wins
    assert p("Answer: yes") == (0, False)            # missing confidence
    assert p("Confidence: 7") == (0, False)          # missing answer
    assert p("") == (0, False) and p(None) == (0, False)
    assert judge_k2.reply_text({"message": {"reasoning_content": "think", "content": "Answer: no\nConfidence: 2"}}) == "think\nAnswer: no\nConfidence: 2"
    assert p(judge_k2.reply_text({"message": {"reasoning_content": "Answer: yes\nConfidence: 4", "content": None}})) == (4, True)
    assert p(judge_k2.reply_text({"message": {"content": "Answer: yes\nConfidence: 5"}})) == (5, True)


def test_extra_judge_and_pick2():
    recs = mk("a|IND", ["x", "y", "z", "w"], [True, False, False, False]) + mk("b|IND", ["x", "y", "z", "w"], [False, False, True, False])
    sc = {"a|IND|0": 9, "a|IND|1": -2, "a|IND|2": -3, "b|IND|2": 5, "b|IND|0": -4}   # missing -> 0
    m = an.evaluate(recs, {"a|IND|1": .9}, None, {"THINK": (sc, 0.0)})
    assert m["pick_rate"]["THINK"]["all"] == 100 and m["auroc"]["THINK"] == 1.0
    assert m["pick_rate"]["SELF"]["all"] == 0


def test_verdict_pick2():
    def f(R, S, full, think, aufull=.8, authink=.8):
        pr = {"RAND": dict(all=R), "SELF": dict(all=S), "FULL": dict(all=full), "THINK": dict(all=think)}
        return dict(pick_rate=pr, auroc={"FULL": aufull, "THINK": authink})
    v = an.verdict_pick2(f(20, 34, 37, 30))
    assert v["verdict"] == "PASS" and v["passing"] == ["FULL"] and v["best"] == "FULL"
    assert an.verdict_pick2(f(20, 34, 36.9, 30))["verdict"] == "INCONCLUSIVE"            # Q3 fails (<SELF+3), Q1 ok
    assert an.verdict_pick2(f(20, 34, 40, 30, aufull=.69))["verdict"] == "INCONCLUSIVE"   # Q2 fails
    assert an.verdict_pick2(f(30, 34, 40, 30))["verdict"] == "INCONCLUSIVE"               # Q1 fails (<RAND+15)
    v = an.verdict_pick2(f(20, 34, 35, 34.5))
    assert v["verdict"] == "PROVED WRONG" and v["best"] == "FULL"
    assert an.verdict_pick2(f(20, 34, 35.1, 30))["verdict"] == "INCONCLUSIVE"
    assert an.verdict_pick2(f(20, 34, 30, 40, authink=.7))["passing"] == ["THINK"]      # either variant can pass
    assert an.verdict_pick2({"pick_rate": {"RAND": dict(all=1)}, "auroc": {}})["verdict"] == "NO JUDGE SCORES"
    assert "Verdict: **PASS**" in an.report_pick2_md(an.verdict_pick2(f(20, 34, 37, 30)))
