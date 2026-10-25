"""No-network tests: fake client replays scripted responses."""
import asyncio, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import client as C  # noqa: E402
import episode as E  # noqa: E402
import run as R  # noqa: E402

TASKS = R.load_tasks()
BYID = {t["id"]: t for t in TASKS}


def call(name, **kw):
    return dict(id="", name=name, arguments=kw)


class Fake:
    """Replays a list of responses (dicts content/tool_calls); a callable is called with the messages instead."""
    def __init__(self, script):
        self.script, self.i, self.seen = script, 0, []

    async def chat(self, messages, tools=None):
        self.seen.append(messages)
        r = self.script(messages) if callable(self.script) else self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        return dict(usage={}, content=r.get("content", ""), tool_calls=[dict(c, id=c["id"] or f"c{self.i}") for c in r.get("tool_calls", [])])


def reference_script(task):
    return [dict(tool_calls=[call(c["name"], **c["arguments"]) for c in task["reference"]]) if task["reference"] else {},
            dict(content=task["reference_reply"])] if task["reference"] else [dict(content=task["reference_reply"])]


def run(coro):
    return asyncio.run(coro)


# ---- parsing ----
def test_parse_openai_tool_calls():
    m = C.parse_message(dict(content=None, tool_calls=[dict(id="x1", function=dict(name="read_file", arguments='{"path": "/a"}'))]))
    assert m["tool_calls"] == [dict(id="x1", name="read_file", arguments={"path": "/a"})]
    bad = C.parse_message(dict(content="", tool_calls=[dict(function=dict(name="f", arguments="{oops"))]))
    assert bad["tool_calls"][0]["arguments"] == "{oops" and bad["tool_calls"][0]["id"]


def test_parse_lfm_pythonic():
    t = 'Sure.<|tool_call_start|>[read_file(path="/a/b", max_lines=5), email_search(query="x y", limit=2)]<|tool_call_end|>'
    m = C.parse_message(dict(content=t))
    assert [(c["name"], c["arguments"]) for c in m["tool_calls"]] == [("read_file", dict(path="/a/b", max_lines=5)),
                                                                     ("email_search", dict(query="x y", limit=2))]
    assert m["content"] == "Sure." and all(c["id"] for c in m["tool_calls"])


def test_parse_json_tool_call_and_plain_text():
    m = C.parse_message(dict(content='<tool_call>{"name": "list_dir", "arguments": {"path": "~"}}</tool_call>'))
    assert m["tool_calls"][0]["name"] == "list_dir" and m["tool_calls"][0]["arguments"] == {"path": "~"} and m["content"] == ""
    p = C.parse_message(dict(content="Done."))
    assert p["tool_calls"] == [] and p["content"] == "Done."
    assert C.strip_planning("<think>hmm</think>Hi") == "Hi"


# ---- episodes ----
def test_episode_reference_succeeds_on_real_tasks():
    tasks = [t for t in TASKS if t["reference"]][:25] + [t for t in TASKS if not t["reference"]][:5]
    for t in tasks:
        r = run(E.run_episode(Fake(reference_script(t)), t))
        assert r["success"], (t["id"], r["checks"])
        assert r["n_turns"] == (2 if t["reference"] else 1)


def test_episode_empty_reply_fails():
    t = next(t for t in TASKS if t["reference"])
    r = run(E.run_episode(Fake([dict(content="")]), t, arm="plain", try_idx=3))
    assert not r["success"] and r["try_idx"] == 3 and r["arm"] == "plain" and r["n_turns"] == 1


def test_episode_turn_cap_extra_block_and_tool_ids():
    t = next(t for t in TASKS if t["reference"])
    f = Fake([dict(tool_calls=[call("list_dir", path="/")])])
    r = run(E.run_episode(f, t, extra_block="EXTRA-BLOCK"))
    assert r["n_turns"] == 6 and not r["success"] and r["final_reply"] == ""
    assert "EXTRA-BLOCK" in f.seen[0][0]["content"] and r["extra_block"] == "EXTRA-BLOCK"
    tool_msgs = [m for m in r["transcript"] if m["role"] == "tool"]
    assert len(tool_msgs) == 6 and all(m["tool_call_id"] for m in tool_msgs)
    assert not any(k in json.dumps(f.seen) for k in ("rubric", "reference_reply"))


# ---- resume ----
def test_resume_skips_done(tmp_path):
    store = R.Store(str(tmp_path))
    jobs = [dict(task=TASKS[0], arm="plain", try_idx=i) for i in range(3)]
    f = Fake([dict(content="ok")])
    run(R.run_jobs(f, store, jobs, 2))
    assert f.i == 3
    store2 = R.Store(str(tmp_path))  # fresh load from disk
    run(R.run_jobs(f, store2, jobs + [dict(task=TASKS[0], arm="plain", try_idx=3)], 2))
    assert f.i == 4 and len(R.Store(str(tmp_path)).rows) == 4


# ---- BORROW ----
def rec(tid, success, arm="plain", i=0, extra=None):
    return dict(task_id=tid, scenario=BYID[tid]["scenario"], arm=arm, try_idx=i, success=success, checks=[success], final_reply="",
                transcript=[dict(role="assistant", content="reply " + tid)], extra_block=extra)


def mkstore(tmp_path, rows):
    s = R.Store(str(tmp_path))
    s.rows = rows
    s.done = {(r["task_id"], r["arm"], r["try_idx"]) for r in rows}
    return s


def test_borrow_excludes_same_scenario_and_unsolved(tmp_path):
    hard = TASKS[0]
    same = [t for t in TASKS if t["scenario"] == hard["scenario"] and t is not hard][:3]
    other = [t for t in TASKS if t["scenario"] != hard["scenario"]][:12]
    rows = [rec(t["id"], True) for t in same] + [rec(t["id"], True, i=2) for t in other[:6]] + [rec(t["id"], False) for t in other[6:]]
    rows += [rec(other[0]["id"], True, i=5), rec(other[0]["id"], False, i=0)]
    s = mkstore(tmp_path, rows)
    cands = R.borrow_candidates(s, TASKS, hard)
    ids = [c.get("id") for c, _ in cands]
    assert set(ids) == {t["id"] for t in other[:6]}
    assert all(BYID[i]["scenario"] != hard["scenario"] for i in ids)
    w = dict(cands)[other[0]] if False else [w for c, w in cands if c["id"] == other[0]["id"]][0]
    assert w["try_idx"] == 2 and w["success"]
    # closeness ordering: Jaccard of request words
    jac = [len(R.words(hard["user"]) & R.words(c["user"])) / len(R.words(hard["user"]) | R.words(c["user"])) for c, _ in cands]
    assert jac == sorted(jac, reverse=True)


def test_parse_numbered_and_render():
    items = R.parse_numbered("Intro\n1. Assumed A\n   more -> New approach: do B\n2) Assumed C -> New approach: D\n")
    assert items == ["Assumed A more -> New approach: do B", "Assumed C -> New approach: D"]
    tr = [dict(role="assistant", content="", tool_calls=[dict(id="1", function=dict(name="read_file", arguments='{"path":"/x"}'))]),
          dict(role="tool", tool_call_id="1", content="y" * 500), dict(role="assistant", content="done")]
    txt = R.render("do it", tr)
    assert "User request: do it" in txt and "read_file" in txt and "Final reply: done" in txt and "y" * 301 not in txt


# ---- report ----
HARD = [t["id"] for t in TASKS[:20]]


def synth(tmp_path, r_win, x_win, replay_ok=3, n_hard=20, flip_only=()):
    """r_win / x_win: sets of hard task ids cracked by R+ / X."""
    rows = []
    for tid in HARD[:n_hard]:
        rows += [rec(tid, False, i=i) for i in range(64)]
        rows += [rec(tid, tid in r_win and i == 0, "R+", i) for i in range(16)]
        rows += [rec(tid, tid in x_win and i == 0, "FLIP" if tid in flip_only or i % 2 == 0 else "BORROW", i % 8) for i in range(2)]
        if tid in x_win:
            rows += [rec(tid, k < replay_ok, "replay", k, extra="x") for k in range(3)]
    s = mkstore(tmp_path, rows)
    s.jsave("hard.json", dict(hard=HARD[:n_hard], n_hard=n_hard, stopped=n_hard < 15))
    return R.report(s, TASKS)


def test_report_pass(tmp_path):
    assert synth(tmp_path, set(HARD[:1]), set(HARD[:7]))["verdict"] == "PASS"


def test_report_wrong(tmp_path):
    assert synth(tmp_path, set(HARD[:4]), set(HARD[:1]))["verdict"] == "PROVED WRONG"
    assert synth(tmp_path, set(HARD[:6]), set(HARD[2:8]))["verdict"] == "PROVED WRONG"  # X == R+


def test_report_inconclusive_and_p3(tmp_path):
    assert synth(tmp_path, set(HARD[:1]), set(HARD[:4]))["verdict"].startswith("INCONCLUSIVE")  # 4 cracked, gap 3 but P1 fails
    assert synth(tmp_path, set(), set(HARD[:7]), replay_ok=1)["verdict"].startswith("P1+P2 met but P3 FAILED")
    # gap 3 but only-R+ outnumbers: R+={0,1,2,3}, X={0..9} -> only_X 6, only_R 0 ok; make ratio fail
    res = synth(tmp_path, set(HARD[:6]) | {HARD[10]}, set(HARD[:5]) | set(HARD[11:15]))
    assert res["gap"] >= 1 and not res["P2"]


def test_report_stop_when_few_hard(tmp_path):
    res = synth(tmp_path, set(), set(), n_hard=10)
    assert res["verdict"].startswith("STOPPED") and "almost everything" in res["note"]
