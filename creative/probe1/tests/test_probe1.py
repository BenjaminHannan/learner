"""No-network, no-GPU tests for Probe-1."""
import json, os, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import probe_common as pc, replay, write_probes as wp, analyze as an  # noqa

TASKS = pc.load_tasks()
BY = {t["id"]: t for t in TASKS}


def call(n, a):
    return dict(role="assistant", content="", tool_calls=[dict(id="x", type="function", function=dict(name=n, arguments=a if isinstance(a, str) else json.dumps(a)))])


def rec(calls, reply="done"):
    return dict(transcript=[dict(role="user", content="hi")] + [call(n, a) for n, a in calls] + [dict(role="assistant", content=reply)], final_reply=reply)


# ---- replay
def test_reference_replay_satisfies_real_checks():
    t = BY["t004"]
    w, reply = replay.replay_reference(t)
    assert len(w.sent) == 1 and replay.success_of(t, w, reply)
    r = rec([(c["name"], c["arguments"]) for c in t["reference"]], t["reference_reply"])
    w2, reply2 = replay.replay_try(t, r)
    assert w2.sent == w.sent and replay.success_of(t, w2, reply2)
    w3, reply3 = replay.replay_try(t, rec([]))          # did nothing -> the email check fails
    assert not replay.success_of(t, w3, reply3)


def test_replay_bad_args_and_string_args():
    t = BY["t004"]
    w, _ = replay.replay_try(t, rec([("send_email", "{not json"), ("nope", {})]))
    assert w.sent == []                                   # unparsable arguments -> sandbox error, nothing sent
    assert replay.calls_of(rec([("read_file", '{"path": "/a"}')])["transcript"]) == [("read_file", {"path": "/a"})]
    assert replay.calls_of(rec([("list_dir", "")])["transcript"]) == [("list_dir", {})]


def test_all_reference_plans_pass_most_real_checks():
    ok = [replay.success_of(t, *replay.replay_reference(t)) for t in TASKS]
    assert sum(ok) / len(ok) > 0.9


@pytest.mark.skipif(not os.path.exists(pc.DEFAULT_RESULTS + "/results.jsonl"), reason="Guess-1 results not mounted")
def test_gate_on_real_tries():
    rows = replay.load_rows(pc.DEFAULT_RESULTS)
    some = dict(list(rows.items())[:40:3] + [kv for kv in rows.items() if kv[1]["success"]][:10])
    rate, bad, _ = replay.gate(some, TASKS)
    assert len(some) >= 10 and rate >= 0.99 and not bad
    k, r = next((k, r) for k, r in rows.items() if r["success"])
    flipped = {k: dict(r, transcript=[r["transcript"][0]], final_reply="")}   # drop the work: recorded success no longer reproduced
    rate2, bad2, _ = replay.gate(flipped, TASKS)
    assert rate2 == 0 and len(bad2) == 1


# ---- probe extraction and validation
def test_extract_checks_variants():
    c = {"type": "file_exists", "path": "/a"}
    d = {"type": "reply_contains", "any_of": ["x", "y"]}
    j = json.dumps({"checks": [c, d]})
    for txt in (j, f"```json\n{j}\n```", f"Sure! Here:\n{j}\nHope that helps", f"<think>{{\"a\":1}}</think>{j}", json.dumps([c, d]),
                j.replace("]}", ",]}")):
        assert wp.extract_checks(txt) == [c, d], txt
    assert wp.extract_checks(j[:-12]) == [c]              # truncated: the complete inner object is kept
    assert wp.extract_checks(json.dumps(c) + "\n" + json.dumps(d)) == [c, d]
    assert wp.extract_checks("no json here") is None and wp.extract_checks("") is None and wp.extract_checks(None) is None
    assert wp.extract_checks('{"checks": []}') == []


def test_validator_filtering():
    good = {"type": "email_sent", "to": "a@b.com"}
    bad = [{"type": "email_sent"}, {"type": "nope"}, {"type": "file_exists"}, {"type": "file_exists", "path": 3}, {"type": ["x"]}, "str", None,
           {"type": "reply_contains", "any_of": []}, {"type": "no_email_sent", "to": "x"}]
    assert an.valid(good) and not any(an.valid(b) for b in bad)
    assert an.task_valid([[good] + bad, None, []]) == [[good], [], []]


# ---- scoring
def world_after(task_id, calls):
    return replay.replay_try(BY[task_id], rec(calls))


def test_probe_score_and_skipped_samples():
    t = BY["t004"]
    sent = [("send_email", dict(to=["x@y.org"], subject="s", body="Nov 14"))]
    states = {"p|0": world_after("t004", sent), "p|1": world_after("t004", [])}
    recs = [dict(pool="p", task="t004", try_idx=i) for i in (0, 1)]
    a, b = {"type": "email_sent", "to": "x@y.org"}, {"type": "no_email_sent"}
    probes = {"t004": [[a, b], [a], [{"type": "bogus"}], None]}        # samples 3 and 4 have no valid probe: skipped
    sc = an.probe_scores(recs, states, probes)
    assert sc["p|0"] == pytest.approx((1 / 2 + 1) / 2) and sc["p|1"] == pytest.approx((1 / 2 + 0) / 2)
    assert an.probe_scores(recs, states, {}) == {"p|0": 0.5, "p|1": 0.5}                # no probes at all -> 0.5
    assert an.probe_scores(recs, states, {"t004": [[{"type": "bogus"}]]}) == {"p|0": 0.5, "p|1": 0.5}


def test_check_that_raises_counts_as_failed():
    w, reply = world_after("t004", [])
    assert an.passes({"type": "file_contains", "path": ["a"], "text": ["b"]}, w, reply) is False
    assert an.passes({"type": "weird"}, w, reply) is False


# ---- pickers
def mkrecs(pool, succ, task="t"):
    return [dict(pool=pool, task=task, try_idx=i, signature=str(i), success=s) for i, s in enumerate(succ)]


def test_picker_tie_breaks():
    recs = mkrecs("a|IND", [False, False, True, False]) + mkrecs("b|IND", [False, True, False, False]) + mkrecs("c|IND", [False, False, False, True])
    k = lambda p, i: f"{p}|{i}"   # noqa
    # pool a: all probe scores tie -> SELF decides (try 2); pool b: probe says try 1 beats a SELF favourite; pool c: full tie incl. SELF -> lowest try
    probe = {k("a|IND", i): .5 for i in range(4)} | {k("b|IND", 0): .2, k("b|IND", 1): .9, k("b|IND", 2): .2, k("b|IND", 3): .2} | {k("c|IND", i): .7 for i in range(4)}
    self_ = {k("a|IND", 2): .8, k("a|IND", 0): .1, k("b|IND", 0): .99, k("b|IND", 1): .1, k("c|IND", 3): .5}
    m = an.evaluate(recs, probe, None, self_)
    assert m["pick_rate"]["PROBE-S"]["all"] == pytest.approx(100 * 2 / 3)      # a ok (SELF), b ok (probe), c lowest try -> fail
    assert m["pick_rate"]["SELF"]["all"] == pytest.approx(100 / 3)             # a ok; b picks try 0; c: all SELF = 0.5 -> try 0
    assert m["pick_rate"]["PROBE-R"]["all"] in (100 * 2 / 3, 100 / 3, 100.0, 0.0, 100 * 1 / 3)
    exp = m["pick_rate"]["PROBE-R (expected over ties)"]["all"]
    assert exp == pytest.approx(100 * (1 / 4 + 1 + 1 / 4) / 3)
    assert m["pick_rate"]["PROBE-R"]["all"] == an.evaluate(recs, probe, None, self_)["pick_rate"]["PROBE-R"]["all"]   # seed 0 is reproducible
    assert 0 < m["auroc"]["PROBE-S"] < 1


def test_verdict_marks():
    base = lambda p, au, s=34.375: dict(pick_rate={"SELF": {"all": s}, "PROBE-S": {"all": p}}, auroc={"PROBE-S": au})   # noqa
    assert an.verdict(base(39.6, .76))["verdict"] == "PASS"
    assert an.verdict(base(39.6, .70))["verdict"] == "INCONCLUSIVE"
    assert an.verdict(base(37.0, .90))["verdict"] == "INCONCLUSIVE"
    assert an.verdict(base(35.3, .90))["verdict"] == "PROVED WRONG"
    assert an.verdict(base(30.0, .50))["verdict"] == "PROVED WRONG"
    assert an.verdict(base(34.375 + 5, .75))["verdict"] == "PASS"                 # marks are inclusive
    assert an.verdict(dict(pick_rate={}, auroc={}))["verdict"] == "NO PROBES"


# ---- prompt: no leakage, language in step with the sandbox
SENT = "SENTINEL-9f3a"


def test_prompt_depends_only_on_date_and_request():
    for t in TASKS:
        leaky = dict(t, reference=[dict(name="send_email", arguments=dict(body=SENT))], reference_reply=SENT, rubric=SENT,
                     checks=[dict(type="reply_contains", any_of=[SENT])], state=dict(t["state"], files={"/x": SENT}, emails=[dict(body=SENT)], notes={SENT: SENT}))
        p = wp.task_prompt(leaky, with_state=False)
        assert SENT not in p and p == wp.task_prompt(t, with_state=False)
        assert t["user"] in p and t["state"].get("today", "2026-10-24") in p
        assert t["rubric"] not in p and t["reference_reply"] not in p
        for r in t["reference"]:
            assert json.dumps(r["arguments"]) not in p


def test_prompt_has_every_tool_and_check_type():
    p = wp.build_prompt("2026-10-24", "do x")
    assert all(n in p for n in [t["function"]["name"] for t in pc.TOOLS])
    assert set(wp.LANG) == set(pc.CHECK_KEYS)
    for t, (_, ex) in wp.LANG.items():
        assert set(ex) <= pc.CHECK_KEYS[t] and pc.validate_check(dict(type=t, **ex)), t
    assert {k for _, ex in wp.LANG.values() for k in ex} == {k for ks in pc.CHECK_KEYS.values() for k in ks}


def test_auroc_and_seed_helpers():
    assert an.auroc([.9, .1], [True, False]) == 1.0
    assert wp.job_seed("t1", 0) == wp.job_seed("t1", 0) != wp.job_seed("t1", 1)


def test_probe2_prompt_has_state_but_no_answer_key():
    t = TASKS[0]
    leaky = dict(t, reference=[dict(name="send_email", arguments=dict(body=SENT))], reference_reply=SENT, rubric=SENT,
                 checks=[dict(type="reply_contains", any_of=[SENT])])
    p = wp.task_prompt(leaky, with_state=True)
    assert SENT not in p and p == wp.task_prompt(t, with_state=True) and p != wp.task_prompt(t, with_state=False)
    planted = dict(t, state=dict(t["state"], files={"/home/user/x.txt": "PLANTED-STATE"}))
    assert "PLANTED-STATE" in wp.task_prompt(planted, with_state=True) and "PLANTED-STATE" not in wp.task_prompt(planted, with_state=False)
