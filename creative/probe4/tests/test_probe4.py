"""Probe-4 tests. Pure-python parts always run; tests that need the HF tokenizer (hub) or mlx skip without them. The tiny-model smoke needs `pip install mlx[cpu] mlx-lm transformers` and the hub."""
import importlib.util, json, os, subprocess, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
P4 = os.path.dirname(HERE)
CREATIVE = os.path.dirname(P4)
sys.path.insert(0, P4)
import p4common as P  # noqa
import agent_mlx as A  # noqa
import gen_tasks as G  # noqa
import validate_tasks as V  # noqa
import analyze_e2e as E  # noqa
import self_mlx as S  # noqa
import write_probes as wp  # noqa
import replay  # noqa

OLD = P.load_old_tasks()
BYID = {t["id"]: t for t in OLD}
G1_RESULTS = os.path.join(CREATIVE, "probe3", "inputs", "guess1_run", "results.jsonl")
try:
    import mlx.core as mx  # noqa
    import mlx_lm  # noqa
    HAVE_MLX = True
except Exception:  # noqa
    HAVE_MLX = False
needs_mlx = pytest.mark.skipif(not HAVE_MLX, reason="mlx / mlx-lm not installed")


def k2_text(calls, content=""):
    """What the model writes for tool calls in the template's xml format (cross-checked against the real template below)."""
    if not calls:
        return content
    s = content + "<ifm|tool_calls>"
    for c in calls:
        s += "\n<ifm|tool_call>" + c["name"] + "\n"
        for k, v in c["arguments"].items():
            s += f"<ifm|arg_key>{k}</ifm|arg_key>\n<ifm|arg_value>{v if isinstance(v, str) else json.dumps(v)}</ifm|arg_value>\n"
        s += "</ifm|tool_call>"
    return s + "\n</ifm|tool_calls>"


@pytest.fixture(scope="module")
def tok():
    try:
        import mlx_common as C
        return C.hf_tokenizer(), open(C.TEMPLATE).read()
    except BaseException as e:  # noqa
        pytest.skip(f"HF tokenizer unavailable: {e}")


# ---------- K2 tool-call format ----------
def g1_calls(limit=600):
    out = []
    for ln in open(G1_RESULTS):
        r = json.loads(ln)
        for m in r["transcript"]:
            if m.get("tool_calls"):
                out.append([dict(name=c["function"]["name"], arguments=json.loads(c["function"]["arguments"])) for c in m["tool_calls"]])
        if len(out) >= limit:
            break
    return out


def schema_valid(call):
    sch = {t["function"]["name"]: t["function"]["parameters"]["properties"] for t in P.TOOLS}[call["name"]]
    ty = {"string": str, "integer": int, "boolean": bool, "array": list, "object": dict}
    return all(k in sch and isinstance(v, ty[sch[k]["type"]]) and not (sch[k]["type"] == "integer" and isinstance(v, bool)) for k, v in call["arguments"].items())


def test_parser_round_trips_template_rendering_of_real_guess1_tool_calls(tok):
    t, tpl = tok
    rows = g1_calls()
    assert len(rows) >= 300
    bad = n = 0
    for i, calls in enumerate(rows):
        content = ["", "Let me check.", "I'll look that up. "][i % 3]
        msgs = [dict(role="system", content="s"), dict(role="user", content="u"), dict(role="assistant", content=content, tool_calls=[dict(id="x", type="function", function=c) for c in calls])]
        pre = t.apply_chat_template(msgs[:2], tools=P.TOOLS, chat_template=tpl, add_generation_prompt=True, tokenize=False)
        full = t.apply_chat_template(msgs, tools=P.TOOLS, chat_template=tpl, tokenize=False)
        assert full.startswith(pre) and full.endswith("<|ifm|im_end|>")
        gen = full[len(pre):-len("<|ifm|im_end|>")]          # exactly what the model would have generated after the (empty) think block in the prompt
        assert gen == k2_text(calls, content), (gen, k2_text(calls, content))
        got = A.parse_k2(gen)
        ok = all(g["name"] == c["name"] and g["arguments"] == c["arguments"] for g, c in zip(got["calls"], calls)) and len(got["calls"]) == len(calls) and got["content"] == content.strip()
        if not ok:
            assert not all(schema_valid(c) for c in calls), (calls, got)    # only a value of the wrong type (e.g. "5" for an integer) may be coerced differently
            bad += 1
        n += 1
    assert bad <= n * 0.02


def test_generation_prompt_ends_with_empty_think_block(tok):
    t, tpl = tok
    p = t.apply_chat_template([dict(role="system", content="s"), dict(role="user", content="u")], tools=P.TOOLS, chat_template=tpl, add_generation_prompt=True, tokenize=False)
    assert p.endswith("<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>") and "<ifm|arg_key>$PARAMETER_NAME</ifm|arg_key>" in p


def test_render_function_gives_history_with_tool_results(tok):
    t, tpl = tok
    ep = A.Episode(BYID["t001"], 0)
    ep.step(k2_text([dict(name="email_search", arguments=dict(query="Brightwave", limit=5))], "Checking. "), 10, 5)
    ids = A.make_render(t, tpl)(ep.msgs)
    text = t.decode(ids)
    assert "<|ifm|im_start|>tool\n" in text and "Overdue: INV-5530" in text and '<ifm|arg_value>5</ifm|arg_value>' in text and text.endswith("<ifm|think>\n</ifm|think>")


def test_parser_server_semantics():
    ok = k2_text([dict(name="read_file", arguments=dict(path="~/a.txt", max_lines=3)), dict(name="list_dir", arguments=dict(path="/", recursive=True))], "hi ")
    r = A.parse_k2(ok + " bye")
    assert r["calls"] == [dict(name="read_file", arguments=dict(path="~/a.txt", max_lines=3)), dict(name="list_dir", arguments=dict(path="/", recursive=True))] and r["content"] == "hi  bye"
    assert A.parse_k2("Just text.") == dict(content="Just text.", calls=[])
    assert A.parse_k2("<ifm|tool_calls>\n<ifm|tool_call>list_dir\n</ifm|tool_call>\n</ifm|tool_calls>")["calls"] == [dict(name="list_dir", arguments={})]
    for broken in (ok.replace("</ifm|tool_calls>", ""),                                                   # no closing group tag
                   k2_text([dict(name="no_such_tool", arguments={})]),                                    # unknown tool: whole group dropped
                   ok.replace("<ifm|arg_value>3", "<ifm|arg_value>3</ifm|arg_value><ifm|arg_value>3"),    # stray tags
                   k2_text([dict(name="read_file", arguments={"path": "a"})]).replace("</ifm|tool_call>", "<ifm|arg_key>path</ifm|arg_key>\n<ifm|arg_value>b</ifm|arg_value>\n</ifm|tool_call>"),   # duplicate arg
                   "<ifm|tool_calls> junk <ifm|tool_call>list_dir\n</ifm|tool_call></ifm|tool_calls>"):
        r = A.parse_k2(broken)
        assert r["calls"] == [] and r["content"] == broken.strip()
    assert A.parse_k2(k2_text([dict(name="send_email", arguments=dict(to=["a@b.c"], subject="s", body="x\ny", cc=[]))]))["calls"][0]["arguments"] == dict(to=["a@b.c"], subject="s", body="x\ny", cc=[])
    assert A.coerce("5", ["integer"]) == 5 and A.coerce("true", ["boolean"]) is True and A.coerce("[1, 2]", ["array"]) == [1, 2] and A.coerce("x", ["integer"]) == "x"


# ---------- episode loop ----------
def run_scripted(task, turns, **kw):
    ep = A.Episode(task, 0)
    for t in turns:
        ep.step(t, 100, 20)
        if ep.done:
            break
    return ep


def ref_turns(task):
    return [k2_text([c]) for c in task["reference"]] + [task["reference_reply"]]


def test_episode_follows_guess1_loop_and_record_format():
    t = BYID["t001"]
    ep = run_scripted(t, [k2_text(t["reference"][:2], "Looking. ")] + [k2_text(t["reference"][2:])] + [t["reference_reply"]])
    rec = ep.record()
    assert rec["success"] and rec["arm"] == "IND" and rec["n_turns"] == 3 and rec["task_id"] == "t001" and rec["tokens"] == dict(prompt=300, completion=60)
    assert set(rec) >= {"task_id", "scenario", "arm", "try_idx", "success", "checks", "transcript", "n_turns", "tokens", "final_reply", "reply_log", "extra_block"}
    tr = rec["transcript"]
    assert [m["role"] for m in tr] == ["user", "assistant", "tool", "tool", "assistant", "tool", "assistant"]
    a = tr[1]
    assert a["content"] == "Looking." and a["tool_calls"][0]["type"] == "function" and a["tool_calls"][0]["id"].startswith("chatcmpl-tool-") and isinstance(a["tool_calls"][0]["function"]["arguments"], str)
    assert tr[2]["tool_call_id"] == a["tool_calls"][0]["id"] and tr[2]["name"] == "email_search" and tr[-1]["content"] == t["reference_reply"]
    assert json.loads(P.signature(rec))[-1] == "reply" and replay.success_of(t, *replay.replay_try(t, rec)) is True


def test_episode_turn_cap_and_unparsable_calls():
    t = BYID["t001"]
    loop = k2_text([dict(name="notes_search", arguments=dict(query="x"))])
    ep = run_scripted(t, [loop] * 10)
    assert ep.n == 6 and ep.done and ep.reply == "" and ep.record()["final_reply"] == "" and not ep.record()["success"]      # Guess-1: out of turns -> no final reply
    ep = run_scripted(t, [k2_text([dict(name="bogus", arguments={})], "Doing it")])
    assert ep.n == 1 and ep.reply.startswith("Doing it") and "<ifm|tool_calls>" in ep.reply and ep.msgs[-1].get("tool_calls") is None
    ep = run_scripted(t, [k2_text([dict(name="read_file", arguments={})]), "done"])        # sandbox error goes back as the tool result
    assert ep.msgs[3]["content"].startswith("error: missing required argument")


def test_drive_batches_resumes_and_pauses():
    tasks = [BYID["t001"], BYID["t002"]]
    scripts = {t["id"]: ref_turns(t) for t in tasks}
    def render2(msgs):
        return (msgs[1]["content"], sum(m["role"] == "assistant" for m in msgs))
    def generate2(prompts):
        return [[(next(t["id"] for t in tasks if t["user"] == u), k)] for u, k in prompts]
    def decode(o):
        tid, k = o[0]
        return scripts[tid][k]
    done = []
    r = A.drive([(t, i) for t in tasks for i in range(3)], render2, generate2, decode, 4, done.append)
    assert r == 6 and len(done) == 6 and all(d["success"] for d in done) and sorted((d["task_id"], d["try_idx"]) for d in done) == sorted((t["id"], i) for t in tasks for i in range(3))
    done2, calls = [], [0]
    def pause():
        calls[0] += 1
        return "memory pressure" if calls[0] == 3 else None
    assert A.drive([(t, i) for t in tasks for i in range(3)], render2, generate2, decode, 2, done2.append, pause=pause, log=lambda s: None) is None
    assert len(done2) < 6


# ---------- copies of Guess-1 / Pick-1 helpers ----------
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def g1_records(n=80):
    rows = [json.loads(l) for l in open(G1_RESULTS)]
    pools = json.load(open(os.path.join(CREATIVE, "probe3", "inputs", "guess1_run", "target.json")))["T"]
    out = []
    for r in rows:
        if r["arm"] == "IND" and r["try_idx"] < 12:
            out.append(dict(r, transcript=[dict(role="user", content=BYID[r["task_id"]]["user"])] + r["transcript"]))
        if len(out) >= n:
            break
    return out


def test_copies_match_guess1_and_pick1():
    try:
        g1 = load(os.path.join(CREATIVE, "guess1", "run.py"), "guess1_run_t")
        sys.path.insert(0, os.path.join(CREATIVE, "reach1"))
        import episode
    except ImportError as e:
        pytest.skip(str(e))
    assert P.SYSTEM == episode.SYSTEM and P.MAX_TURNS == episode.MAX_TURNS and P.SAMPLING["max_tokens"] == 512
    import client
    assert P.SAMPLING == client.SAMPLING and P.MARKUP_RE.pattern == client.MARKUP_RE.pattern
    recs = g1_records()
    assert recs
    for r in recs:
        assert P.signature(r) == g1.signature(r)
    ours = P.build_pools(recs)
    assert [x["judge_text"] for x in ours] == [g1.r1.render(r["transcript"][0]["content"], r["transcript"], 300) for r in sorted(recs, key=lambda r: (r["task_id"], r["try_idx"]))]
    assert all(x["pool"] == f"{x['task']}|IND" and set(x) == {"pool", "task", "arm", "seed", "try_idx", "success", "signature", "judge_text"} for x in ours)


def test_self_prompt_is_pick1s_and_p_yes_rule():
    c = P.load_pick1("common")
    assert S.judge_prompt("TEXT") == f"TEXT\n\n{c.QUESTION}" and c.QUESTION.endswith("Answer yes or no.")
    import numpy as np
    vocab = {0: "Yes", 1: " yes", 2: "No", 3: "maybe", 4: "no", 5: "x"}
    lg = np.log(np.array([0.3, 0.1, 0.2, 0.2, 0.1, 0.1]))
    assert S.p_yes_from_logits(lg, vocab.get) == pytest.approx(0.4 / 0.7)
    assert S.p_yes_from_logits(np.array([0.0, 0.0, 9.0, 0.0, 0.0, 0.0]) * 0 + np.log([0.1, 0.1, 0.1, 0.1, 0.1, 0.5]), {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f"}.get) is None
    top = [dict(token="Yes", logprob=float(np.log(0.3))), dict(token=" yes", logprob=float(np.log(0.1))), dict(token="No", logprob=float(np.log(0.2))), dict(token="no", logprob=float(np.log(0.1)))]
    sys.path.insert(0, os.path.join(CREATIVE, "pick1"))
    try:
        j = load(os.path.join(CREATIVE, "pick1", "judge_k2.py"), "pick1_judge_k2_t2")
    finally:
        sys.path.pop(0)
        sys.modules.pop("common", None)
    assert j.p_yes(top) == pytest.approx(S.p_yes_from_logits(np.log([0.3, 0.1, 0.2, 0.1, 1e-9]), {0: "Yes", 1: " yes", 2: "No", 3: "no", 4: "z"}.get), rel=1e-6)


# ---------- gen_tasks ----------
def test_gen_prompt_and_plumbing():
    p = G.build_prompt(1, 0)
    assert p == G.build_prompt(1, 0) and p != G.build_prompt(1, 1) and p != G.build_prompt(2, 0)
    for name in ("multi_step", "confirm_irreversible", "direct_answer", "error_recovery", "clarify", "parallel", "single_tool", "summarize_long"):
        assert name in p
    assert p.count('"scenario":') >= 3 and BYID["t001"]["user"] in p and BYID["t015"]["user"] in p and "literal_plan" in p
    assert sum(G.TRAPS_PATTERN[i % 5] for i in range(30)) / (6 * 30) == 0.4
    reqs = G.requests_for(1, G.N_REQ)
    assert len(reqs) == 36 and len({c for c, _ in reqs}) == 36 and all(len(c) < 64 for c, _ in reqs)
    tin, tout, cost = G.estimate(reqs)
    assert 0.3 < cost < 5 and G.MODEL == "claude-sonnet-5-5"
    assert G.parse_tasks('Here:\n```json\n[{"a": 1}, {"b": 2}]\n```') == [{"a": 1}, {"b": 2}] and G.parse_tasks("nothing") == []
    r = subprocess.run([sys.executable, os.path.join(P4, "gen_tasks.py"), "--dry-run", "--state", "/nonexistent/state.json"], capture_output=True, text=True, env=dict(os.environ, LEARNER_ANTHROPIC_API_KEY=""))
    assert r.returncode == 0 and "est. cost" in r.stdout and "216 tasks" in r.stdout


def with_flags(t, trap=None):
    t = dict(t)
    t["trap"] = bool(trap)
    t.setdefault("literal_plan", None)
    t.setdefault("literal_reply", None)
    return t


def trap_example():
    return dict(with_flags(BYID["t015"], True), literal_plan=G.TRAP_EXAMPLE_PLAN["plan"], literal_reply=G.TRAP_EXAMPLE_PLAN["reply"])


def test_validate_existing_tasks_pass():
    plain = [with_flags(t) for t in OLD if t["scenario"] not in ("clarify", "confirm_irreversible") and t["reference"]]
    ok = [t for t in plain if not V.check_task(t)[0]]
    assert len(ok) >= 0.9 * len(plain) and all(not V.check_task(with_flags(BYID[i]))[0] for i in ("t001", "t002"))
    assert V.check_task(trap_example()) == ([], [])


def test_validate_broken_tasks_fail():
    t = with_flags(BYID["t001"])
    def bad(**kw):
        return V.check_task(dict(t, **kw))[0]
    assert bad(checks=[{"type": "no_such_check"}]) == ["invalid_check"]
    assert bad(checks=[{"type": "email_sent"}]) == ["invalid_check"]                       # needs at least one key
    assert bad(checks=[]) == ["invalid_check"]
    assert bad(checks=[{"type": "draft_exists", "to": "nobody@example.com"}]) == ["reference_fails_checks"]
    assert bad(reference=[]) == ["bad_reference"] and bad(reference=[{"name": "nope", "arguments": {}}]) == ["bad_reference"]
    assert bad(trap="yes") == ["bad_trap_flag"]
    assert V.check_task({k: v for k, v in t.items() if k != "user"})[0] == ["missing_fields"]
    assert bad(state={"files": ["not a dict"]}) == ["bad_state"]
    assert bad(trap=True) == ["trap_without_literal_plan"]                                   # a trap needs its literal plan
    assert bad(trap=True, literal_plan=t["reference"], literal_reply=t["reference_reply"]) == ["literal_plan_passes"]   # the "just do it" plan solves it: not a trap
    te = trap_example()
    assert V.check_task(dict(te, literal_plan=[]))[0] == ["trap_without_literal_plan"]
    assert V.check_task(dict(te, literal_plan=BYID["t015"]["reference"], literal_reply=BYID["t015"]["reference_reply"]))[0] == ["literal_plan_passes"]
    assert V.check_task(t, others=[t["user"].upper() + " "])[0] == ["duplicate"]
    assert V.check_task(t, others=[t["user"] + " please"])[0] == ["duplicate"]
    assert V.check_task(t, others=["something completely different about taxes"])[0] == []


def test_validate_cli_end_to_end_and_selection(tmp_path):
    raw = [dict(with_flags(BYID[i]), _src=f"x#{k}") for k, i in enumerate(("t001", "t002"))] + [dict(trap_example(), _src="x#9"), dict(with_flags(BYID["t001"]), checks=[{"type": "zz"}], _src="x#10"), dict(with_flags(BYID["t002"]), _src="dup")]
    rp, out = tmp_path / "raw.jsonl", tmp_path / "new.jsonl"
    rp.write_text("".join(json.dumps(r) + "\n" for r in raw))
    r = subprocess.run([sys.executable, os.path.join(P4, "validate_tasks.py"), "--raw", str(rp), "--out", str(out), "--report", str(tmp_path / "rep.json"), "--min", "2"], capture_output=True, text=True)
    # t001 / t002 / t015 are among the 420 existing tasks, so the dedup rule drops all of them
    assert r.returncode == 3 and json.loads((tmp_path / "rep.json").read_text())["drops"] == {"duplicate": 4, "invalid_check": 1}
    many = [dict(with_flags(BYID["t001"]), trap=False, user=f"u{i}") for i in range(30)] + [dict(trap_example(), user=f"v{i}") for i in range(30)]
    sel = V.select(many, 10, 20)
    assert len(sel) == 20 and sum(t["trap"] for t in sel) == 8 and V.select(many[:5], 1, 20) == many[:5]


# ---------- analysis on fake data ----------
def fake_run(tmp_path, win_try=5):
    """8 real tasks (3 flagged as traps); 12 tries each from scripted episodes: only try `win_try` succeeds. TEST-T writes the true checks, TEST-B writes a useless always-true check, SELF is flat."""
    ids = [t["id"] for t in OLD if t["reference"] and not V.check_task(with_flags(t))[0]][:8]
    tasks = [dict(with_flags(BYID[i], trap=k < 3), id=i) for k, i in enumerate(ids)]
    assert len(tasks) == 8
    rows = []
    for t in tasks:
        for i in range(12):
            ep = A.Episode(t, i)
            for turn in (ref_turns(t) if i == win_try else ["I could not do it."]):
                ep.step(turn, 50, 10)
                if ep.done:
                    break
            rows.append(ep.record())
    tp, selfp, tt, tb = tmp_path / "tasks.jsonl", tmp_path / "self.jsonl", tmp_path / "tt.jsonl", tmp_path / "tb.jsonl"
    tp.write_text("".join(json.dumps(t) + "\n" for t in tasks))
    (tmp_path / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    selfp.write_text("".join(json.dumps(dict(key=f"{t['id']}|IND|{i}", p_yes=0.5, n_prompt=40)) + "\n" for t in tasks for i in range(12)))
    for p, mk in ((tt, lambda t: t["checks"]), (tb, lambda t: [{"type": "reply_contains", "any_of": [""]}])):
        p.write_text("".join(json.dumps(wp.record("k2", t["id"], s, json.dumps({"checks": mk(t)}))) + "\n" for t in tasks for s in range(4)))
        (p.parent / (p.stem + ".genlog.jsonl")).write_text("".join(json.dumps(dict(key=f"{t['id']}|{s}", prompt_tokens=100, new_tokens=30, hit_max=False)) + "\n" for t in tasks for s in range(4)))
    return tasks, tp, tmp_path / "results.jsonl", selfp, tb, tt


def run_analysis(tmp_path, **kw):
    tasks, tp, res, selfp, tb, tt = fake_run(tmp_path, **kw)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, os.path.join(P4, "analyze_e2e.py"), "--tasks", str(tp), "--tries", str(res), "--self", str(selfp), "--test-b", str(tb), "--test-t", str(tt), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.load(open(out / "report.json")), (out / "report.md").read_text()


def test_analyze_e2e_fake_data_pass(tmp_path):
    rep, md = run_analysis(tmp_path, win_try=5)
    tasks = P.load_tasks(str(tmp_path / "tasks.jsonl"))
    rt = {p: r["all"] for p, r in rep["rates"].items()}
    assert rt["FIRST"] == 0 and rt["ORACLE"] == 100 and rt["TEST-T"] == 100 and rt["SELF"] == 0 and rt["TEST-B"] == 0 and rt["VOTE"] == 0
    assert rt["RAND"] == pytest.approx(100 / 12) and rep["verdict"] == "PASS" and rep["checks"] == dict(E1=True, E2=True, E3=True)
    assert rep["rates"]["TEST-T"]["traps"] == 100 and rep["info"]["n_traps"] == 3 and rep["info"]["n_plain"] == 5 and rep["info"]["gate"] == 1
    tk = rep["tokens"]
    assert tk["TEST-T"]["generated"] > tk["SELF"]["generated"] > tk["RAND"]["generated"] > tk["FIRST"]["generated"] and tk["TEST-B"]["generated"] == tk["TEST-T"]["generated"]
    assert "Verdict: **PASS**" in md and "| TEST-T |" in md and rep["picks"][tasks[0]["id"]]["TEST-T"] == 5 and rep["picks"][tasks[0]["id"]]["SELF"] == 0


def test_analyze_e2e_fake_data_first_wins(tmp_path):
    rep, _ = run_analysis(tmp_path, win_try=0)      # the first try already succeeds: nothing to gain
    rt = {p: r["all"] for p, r in rep["rates"].items()}
    assert rt["FIRST"] == 100 and rt["TEST-T"] == 100
    assert rep["verdict"] == "PROVED WRONG" and rep["checks"]["E1"] is False


def test_verdict_pass_marks():
    base = {"FIRST": 30.0, "SELF": 35.0, "TEST-B": 36.0, "TEST-T": 41.0}
    assert E.verdict(base)["checks"] == dict(E1=True, E2=True, E3=True)
    assert E.verdict(dict(base, **{"TEST-T": 40.0}))["verdict"] == "INCONCLUSIVE"
    assert E.verdict(dict(base, **{"TEST-T": 40.0}))["checks"]["E1"] is True and E.verdict(dict(base, **{"TEST-T": 40.0}))["checks"]["E3"] is False
    assert E.verdict(dict(base, **{"TEST-T": 41.0}))["verdict"] == "PASS"
    assert E.verdict(dict(base, **{"TEST-T": 33.0}))["verdict"] == "PROVED WRONG" and E.verdict(dict(base, **{"TEST-T": 33.1}))["verdict"] == "INCONCLUSIVE"
    assert E.verdict({"FIRST": 1})["verdict"] == "INCOMPLETE"


# ---------- plumbing ----------
def test_write_probes_tasks_file_option_keeps_defaults(tmp_path):
    f = tmp_path / "t.jsonl"
    f.write_text("".join(json.dumps(BYID[i]) + "\n" for i in ("t001", "t002")))
    assert [t["id"] for t in wp.select_tasks(None, tasks_file=str(f))] == ["t001", "t002"] and [t["id"] for t in wp.select_tasks(None, ["t002"], tasks_file=str(f))] == ["t002"]
    res = os.path.join(CREATIVE, "probe3", "inputs", "guess1_run")
    assert [t["id"] for t in wp.select_tasks(res)] == json.load(open(os.path.join(res, "target.json")))["T"] and [t["id"] for t in wp.select_tasks(res, ["t001"])] == ["t001"]


def test_run_m3_script_is_valid_bash_and_names_the_adapter():
    s = open(os.path.join(P4, "run_m3.sh")).read()
    assert subprocess.run(["bash", "-n", os.path.join(P4, "run_m3.sh")]).returncode == 0
    assert "probe3-out/train/adapter" in s and "--tasks-file" in s and "agent_mlx.py" in s and "self_mlx.py" in s and "analyze_e2e.py" in s and s.index("agent_mlx.py") < s.index("self_mlx.py") < s.index("--arm base") < s.index("--arm tuned") < s.index("analyze_e2e.py")
    t3 = open(os.path.join(CREATIVE, "probe3", "mlx", "run_m3.sh")).read()
    assert '"$OUT/train/adapter"' in t3                      # the layout run_m3.sh of Probe-3 leaves behind


# ---------- tiny-model smoke (random-init K2 on mlx CPU/GPU) ----------
def py(script, *args, d=P4):
    return subprocess.run([sys.executable, os.path.join(d, script), *args], capture_output=True, text=True, timeout=1500, env=dict(os.environ, TOKENIZERS_PARALLELISM="false"))


@pytest.fixture(scope="module")
def hub(tok):
    return tok


@needs_mlx
def test_tiny_smoke_agent_self_and_tests(hub, tmp_path):
    tf = tmp_path / "t.jsonl"
    tf.write_text("".join(json.dumps(with_flags(BYID[i])) + "\n" for i in ("t001", "t002")))
    out = tmp_path / "tries"
    r = py("agent_mlx.py", "--tasks", str(tf), "--out", str(out), "--tiny", "--limit-tasks", "1", "--tries", "2", "--max-tokens", "16", "--batch", "2")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rows = P.read_jsonl(str(out / "results.jsonl"))
    assert sorted(x["try_idx"] for x in rows) == [0, 1] and all(x["task_id"] == "t001" and x["arm"] == "IND" and x["n_turns"] >= 1 and x["tokens"]["prompt"] > 500 and x["transcript"][0]["role"] == "user" for x in rows)
    r = py("agent_mlx.py", "--tasks", str(tf), "--out", str(out), "--tiny", "--limit-tasks", "1", "--tries", "2", "--max-tokens", "16")
    assert r.returncode == 0 and "0 to run" in r.stdout and len(P.read_jsonl(str(out / "results.jsonl"))) == 2
    r = py("agent_mlx.py", "--tasks", str(tf), "--out", str(out), "--tiny", "--limit-tasks", "1", "--tries", "3", "--max-tokens", "8", "--sequential")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert sorted(x["try_idx"] for x in P.read_jsonl(str(out / "results.jsonl"))) == [0, 1, 2]
    r = py("self_mlx.py", "--tries", str(out / "results.jsonl"), "--tasks", str(tf), "--pools", str(tmp_path / "pools.jsonl"), "--out", str(tmp_path / "self.jsonl"), "--tiny", "--limit", "3")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    sc = P.read_jsonl(str(tmp_path / "self.jsonl"))
    assert len(sc) == 3 and sc[0]["key"] == "t001|IND|0" and all(x["n_prompt"] > 50 and (x["p_yes"] is None or 0 <= x["p_yes"] <= 1) for x in sc)
    r = py("gen_mlx.py", "--arm", "base", "--tasks-file", str(tf), "--tiny", "--limit-tasks", "1", "--samples", "1", "--max-tokens", "8", "--out-dir", str(tmp_path / "tb"), d=os.path.join(CREATIVE, "probe3", "mlx"))
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rows = P.read_jsonl(str(tmp_path / "tb" / "probes_k2base_mlx.jsonl"))
    assert len(rows) == 1 and rows[0]["task"] == "t001"
