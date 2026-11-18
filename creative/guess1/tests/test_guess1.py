"""No-network tests for the Guess-1 harness (fake client)."""
import asyncio, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("guess1_run", os.path.join(G, "run.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

TASKS = g.subset(g.load_tasks())
WITH_REF = [t for t in TASKS if t["reference"]]


def tc(name, args):
    return dict(role="assistant", content="", tool_calls=[dict(id="x", type="function", function=dict(name=name, arguments=args if isinstance(args, str) else json.dumps(args)))])


def rec(calls, reply, success=False, tokens=(10, 5), **kw):
    tr = [tc(n, a) for n, a in calls] + [dict(role="assistant", content=reply)]
    return dict(transcript=tr, final_reply=reply, success=success, tokens=dict(prompt=tokens[0], completion=tokens[1]), **kw)


class Fake:
    """Answers with tool calls from the reference, then the reference reply; records system prompts and sampling."""
    def __init__(self, task_by_user, fail=False):
        self.by, self.sys, self.samp, self.fail = task_by_user, [], [], fail

    async def chat(self, messages, tools=None, **sampling):
        self.sys.append(messages[0]["content"])
        self.samp.append(sampling)
        if tools is None:
            return dict(content="1. read first\n2. search email\n3. ask the user", tool_calls=[], usage=dict(prompt_tokens=7, completion_tokens=9))
        t = self.by[messages[1]["content"]]
        done = any(m["role"] == "tool" for m in messages)
        if done or not t["reference"] or self.fail:
            return dict(content=t["reference_reply"] if not self.fail else "no", tool_calls=[], usage=dict(prompt_tokens=3, completion_tokens=2))
        calls = [dict(id=f"c{i}", name=c["name"], arguments=c["arguments"]) for i, c in enumerate(t["reference"])]
        return dict(content="", tool_calls=calls, usage=dict(prompt_tokens=3, completion_tokens=2))


def run(c):
    return asyncio.run(c)


# ---- signature ----
def test_signature_normalises_whitespace_and_case_and_key_order():
    a = rec([("search", {"q": "Hello  World", "n": 2})], "Done.")
    b = rec([("search", '{"n": 2, "q": " hello world "}')], "All good")
    assert g.signature(a) == g.signature(b)
    assert g.signature(a) != g.signature(rec([("search", {"q": "other", "n": 2})], "Done."))


def test_signature_order_and_ending():
    x, y = ("a", {"p": 1}), ("b", {"p": 1})
    assert g.signature(rec([x, y], "ok")) != g.signature(rec([y, x], "ok"))
    s_reply, s_q, s_none = g.signature(rec([x], "Done.")), g.signature(rec([x], "Which one?")), g.signature(rec([x], ""))
    assert len({s_reply, s_q, s_none}) == 3
    assert g.signature(rec([], "Hi.")) != g.signature(rec([x], "Hi."))


# ---- LIST prompt ----
def test_list_block_content():
    assert g.list_block([]) is None
    e = [rec([("read_file", {"path": "/" + "x" * 200})], "I read it. " * 30, success=True), rec([], "Which file?")]
    b = g.list_block(e)
    assert b.startswith(g.LIST_HEAD) and b.rstrip().endswith(g.LIST_TAIL)
    assert "1. " in b and "2. " in b and "3. " not in b
    assert "x" * 81 not in b and ("I read it. " * 30)[:121] not in b
    assert "success" not in b.lower() and "check" not in b.lower() and "fail" not in b.lower()


def test_arms_list_sees_only_own_earlier_tries_and_no_checks(tmp_path):
    ts = WITH_REF[:2]
    fake = Fake({t["user"]: t for t in TASKS})
    store = g.Store(str(tmp_path))
    caps = dict(min_p=True, seed=True)
    run(g.arms(fake, store, ts, 1, 4, caps))
    for t in ts:
        for a in g.ARMS:
            assert sorted(r["try_idx"] for r in store.arm(a) if r["task_id"] == t["id"]) == list(range(12))
    lst = {(r["task_id"], r["try_idx"]): r for r in store.arm("LIST")}
    for t in ts:
        assert lst[(t["id"], 0)]["extra_block"] is None
        for k in (1, 5, 11):
            blk = lst[(t["id"], k)]["extra_block"]
            assert blk.count("\n") == k + 2 and f"{k}. " in blk and f"{k + 1}. " not in blk
            assert "Approach to use" not in blk
    ind = [r for r in store.arm("IND")]
    assert all(r["extra_block"] is None for r in ind)
    men = [r for r in store.arm("MENU") if r["task_id"] == ts[0]["id"]]
    assert men[0]["extra_block"] == "Approach to use: read first" == men[1]["extra_block"] and men[2]["extra_block"] == "Approach to use: search email"
    assert men[11]["extra_block"] == "Approach to use: ask the user"  # 3 parsed lines cycle
    hot = store.arm("HOT")[0]["sampling"]
    assert hot["temperature"] == 1.0 and hot["top_p"] == 1.0 and hot["min_p"] == 0.1 and "seed" in hot
    assert store.arm("IND")[0]["sampling"]["temperature"] == 0.7
    assert g.gen_tokens(store, "MENU", 1) == sum(r["tokens"]["completion"] for r in store.arm("MENU")) + 9 * len(ts)
    n = len(store.rows)
    run(g.arms(fake, store, ts, 1, 4, caps))  # resumable: nothing re-run
    assert len(store.rows) == n


def test_min_p_dropped_when_unsupported_and_seed_deterministic():
    assert "min_p" not in g.sampling_for("HOT", 1, "t1", 0, dict(min_p=False, seed=True))
    assert "seed" not in g.sampling_for("IND", 1, "t1", 0, dict(min_p=True, seed=False))
    a, b = g.sampling_for("IND", 1, "t1", 3, {}), g.sampling_for("IND", 1, "t1", 3, {})
    assert a["seed"] == b["seed"] and 100000 <= a["seed"] < 200000
    assert g.sampling_for("IND", 2, "t1", 3, {})["seed"] >= 200000 and a["seed"] != g.sampling_for("IND", 1, "t1", 4, {})["seed"]


# ---- MENU parsing ----
def test_parse_menu_clean_and_messy():
    assert g.parse_menu("1. a\n2. b\n3. c") == ["a", "b", "c"]
    messy = ("Sure! Here are some ways:\n\n**1.** Search the mail first\n   then read the top hit\n2) List the folder\n- 3: Ask the user\n"
             "4. **Approach**: do it in reverse\n  5.  Check the calendar\n6. Draft a note\n7. extra seventh\nHope this helps!")
    m = g.parse_menu(messy)
    assert len(m) == 6 and m[0] == "Search the mail first then read the top hit" and m[1] == "List the folder" and m[2] == "Ask the user"
    assert m[4] == "Check the calendar" and "extra seventh" not in " ".join(m)
    assert g.parse_menu("no list here") == [] and g.parse_menu("") == []


# ---- target selection ----
def _screen_store(tmp_path, succ):
    st = g.Store(str(tmp_path))
    for t, k in zip(TASKS, succ):
        for i in range(8):
            st.rows.append(dict(task_id=t["id"], arm="plain", try_idx=i, success=i < k))
    return st


def test_pick_rules(tmp_path):
    n = len(TASKS)
    st = _screen_store(tmp_path / "a", [0, 1, 2, 3, 4, 8] * (n // 6 + 1))
    info = g.pick(st, TASKS)
    low = [t["id"] for t, k in zip(TASKS, ([0, 1, 2, 3, 4, 8] * (n // 6 + 1))) if k <= 3]
    assert not info["stopped"] and info["T"] == low[:48] and len(info["T"]) == 48 and info["n_low"] == len(low)
    assert json.load(open(tmp_path / "a" / "target.json"))["T"] == info["T"]
    few = _screen_store(tmp_path / "b", [8] * 10 + [0] * 19 + [4] * (n - 29))
    r = g.pick(few, TASKS)
    assert r["stopped"] and r["n_low"] == 19 and "already solves" in r["note"]
    ok = g.pick(_screen_store(tmp_path / "c", [8] * 10 + [0] * 20 + [4] * (n - 30)), TASKS)
    assert not ok["stopped"] and len(ok["T"]) == 20
    st = g.Store(str(tmp_path / "d"))
    try:
        g.pick(st, TASKS)
        assert False
    except SystemExit:
        pass


def test_subset_is_every_second_task():
    allt = g.load_tasks()
    assert len(TASKS) == len(allt[::2]) == 210 and TASKS[1]["id"] == allt[2]["id"]


# ---- top-up ----
def test_topup_rule():
    assert not g.topup_needed(1000, [1100, 1150], 12)
    assert g.topup_needed(1000, [1100, 1151], 12)
    assert g.topup_needed(1000, [900, 2000], 15)
    assert not g.topup_needed(1000, [2000, 3000], 16)


def test_topup_runs_until_within_15_percent(tmp_path):
    ts = WITH_REF[:2]
    st = g.Store(str(tmp_path))
    for t in ts:
        for i in range(12):
            for a, c in (("IND", 100), ("LIST", 150), ("MENU", 100)):
                st.rows.append(dict(task_id=t["id"], arm=a, try_idx=i, tokens=dict(prompt=1, completion=c), success=False))
        st.done |= {(t["id"], "IND", i) for i in range(12)}
    fake = Fake({t["user"]: t for t in TASKS})
    run(g.topup(fake, st, ts, 1, 2, dict(min_p=True, seed=True)))
    n = sorted({r["try_idx"] for r in st.arm("IND")})
    assert n[-1] >= 12 and n[-1] <= 15
    assert not g.topup_needed(g.gen_tokens(st, "IND", 1), [g.gen_tokens(st, "LIST", 1)], n[-1] + 1) or n[-1] == 15


# ---- metrics and verdict ----
def test_arm_metrics():
    a, b = ("a", {"p": 1}), ("b", {"p": 1})
    rows = [dict(rec([a], "ok", True), task_id="t1", try_idx=0), dict(rec([a], "ok", True), task_id="t1", try_idx=1),
            dict(rec([b], "ok", False), task_id="t1", try_idx=2), dict(rec([b], "?", False), task_id="t2", try_idx=0),
            dict(rec([a], "ok", True), task_id="t9", try_idx=0)]
    m = g.arm_metrics(rows, {"t1", "t2"})
    assert m["cracked"] == ["t1"] and m["distinct_plans"] == 3 and m["distinct_correct_plans"] == 1
    assert abs(m["top_share"] - (2 / 3 + 1) / 2) < 1e-9 and m["gen_tokens"] == 20 and m["prompt_tokens"] == 40 and m["tries"] == 4


def C(ind, hot, lst, men, dc=(10, 10, 10), dp=(20, 20, 20), only=((0, 0), (0, 0))):
    d = lambda n, c, p, o=None: dict(n_cracked=n, distinct_correct_plans=c, distinct_plans=p, only_vs_IND=o)
    return dict(IND=d(ind, dc[0], dp[0]), HOT=d(hot, 0, 0), LIST=d(lst, dc[1], dp[1], only[0]), MENU=d(men, dc[2], dp[2], only[1]))


def test_verdict_pass_and_each_mark_failing():
    base = dict(ind=10, hot=11, lst=14, men=12, dc=(10, 15, 9), only=((6, 2), (3, 1)))
    assert g.verdict(C(**base))["verdict"] == "PASS"
    assert g.verdict(C(**base))["best"] == "LIST"
    v = g.verdict(C(**base | dict(lst=13, men=11)))
    assert not v["P1"] and v["verdict"] == "INCONCLUSIVE"
    v = g.verdict(C(**base | dict(hot=12)))
    assert not v["P2"] and v["verdict"] == "INCONCLUSIVE"
    v = g.verdict(C(**base | dict(dc=(10, 14, 9))))
    assert not v["P3"] and v["verdict"] == "INCONCLUSIVE"
    v = g.verdict(C(**base | dict(only=((5, 3), (0, 0)))))
    assert not v["P4"] and v["verdict"] == "INCONCLUSIVE"
    assert g.verdict(C(**base | dict(only=((4, 2), (0, 0)))))["P4"]


def test_verdict_best_tiebreak_and_menu_best():
    assert g.verdict(C(10, 10, 15, 15, only=((5, 0), (1, 0))))["best"] == "LIST"
    v = g.verdict(C(10, 10, 12, 15, only=((5, 0), (6, 0)), dc=(10, 1, 20)))
    assert v["best"] == "MENU" and v["verdict"] == "PASS"


def test_verdict_proved_wrong_and_diagnostic():
    v = g.verdict(C(10, 12, 11, 11))
    assert v["verdict"] == "PROVED WRONG"
    v = g.verdict(C(10, 12, 9, 11, dp=(20, 10, 45)))
    assert v["verdict"] == "PROVED WRONG" and v["diagnostic_diversity_without_quality"]
    v = g.verdict(C(10, 10, 12, 11))
    assert v["verdict"] == "INCONCLUSIVE"
    assert g.verdict(C(10, 10, 12, 11), mult=2)["verdict"] == "PROVED WRONG"  # <= IND + 2
    v = g.verdict(C(10, 10, 14, 11, only=((6, 2), (0, 0)), dc=(10, 15, 9)), mult=2)
    assert not v["P1"]  # needs +8 with two seeds
