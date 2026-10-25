"""No-network, no-model tests for Doubt Forks Step 0 (regex fake tokenizer, fake server)."""
import asyncio, importlib.util, json, math, os, re, types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("df_step0", os.path.join(os.path.dirname(HERE), "step0.py"))
s0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s0)

TASKS = s0.load_tasks()
TASK = next(t for t in TASKS if t["scenario"] == "single_tool")
PRE = "<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>"


def turn(content, calls=()):
    s = PRE + content
    if calls:
        s += "<ifm|tool_calls>"
        for n, args in calls:
            s += "\n<ifm|tool_call>" + n + "\n" + "".join(f"<ifm|arg_key>{k}</ifm|arg_key>\n<ifm|arg_value>{v}</ifm|arg_value>\n" for k, v in args)
            s += "</ifm|tool_call>"
        s += "\n</ifm|tool_calls>"
    return s + "<|ifm|im_end|>"


TEXT = ("<s><|ifm|im_start|>system\nsys<|ifm|im_end|><|ifm|im_start|>user\nhi<|ifm|im_end|>"
        + turn("", [("read_file", [("path", "/home/user/a.txt")])]) + "<|ifm|im_start|>tool\nhello<|ifm|im_end|>" + turn("Done?"))


class FakeTok:
    """Regex tokenizer: each <...> tag, word, whitespace run or punctuation char is one token. Render is a hand-rolled K2 layout."""
    RX = re.compile(r"<[^<>]*>|\w+|\s+|[^\w\s]")

    def __init__(self):
        self.vocab, self.inv = {}, {}

    def encode(self, text):
        ids, offs = [], []
        for m in self.RX.finditer(text):
            i = self.vocab.setdefault(m.group(), len(self.vocab))
            self.inv[i] = m.group()
            ids.append(i); offs.append(m.span())
        return ids, offs

    def decode(self, ids):
        return "".join(self.inv.get(i, "ZZ") for i in ids)

    def render(self, msgs, tools):
        out = "<s>"
        for m in msgs:
            if m["role"] in ("system", "user"):
                out += f"<|ifm|im_start|>{m['role']}\n{m['content']}<|ifm|im_end|>"
            elif m["role"] == "tool":
                out += f"<|ifm|im_start|>tool\n{m['content']}<|ifm|im_end|>"
            else:
                out += turn(m.get("content") or "", [(c["function"]["name"], list(c["function"]["arguments"].items())) for c in m.get("tool_calls") or []])
        return out


def test_offsets_to_spans():
    tok = FakeTok()
    ids, offs = tok.encode(TEXT)
    dec, strad = s0.type_tokens(offs, s0.spans(TEXT))
    assert strad == 0
    got = [(d["span"]["type"], TEXT[offs[d["pos"]][0]:offs[d["pos"]][1]]) for d in dec]
    assert got == [("TURN-START", "<ifm|tool_calls>"), ("TOOL-NAME", "read_file"), ("ARG-VALUE", "/"), ("TURN-START", "Done")]
    assert [d["span"]["turn"] for d in dec] == [0, 0, 0, 1]
    mask = s0.assistant_mask(TEXT, offs)
    assert not mask[offs.index((0, 3))] and mask[dec[0]["pos"]] and sum(mask) < len(mask)
    # the system/user text and tool output are not assistant tokens
    assert not any(mask[i] for i, o in enumerate(offs) if TEXT[o[0]:o[1]] in ("sys", "hi", "hello"))


def test_straddling_token_is_skipped():
    offs = [(0, 5), (5, 12)]
    dec, strad = s0.type_tokens(offs, [dict(type="TOOL-NAME", start=3, end=12, turn=0)])
    assert dec == [] and strad == 1


def test_candidate_rule():
    assert s0.is_candidate(0.9, 0.005) and s0.is_candidate(0.99, 0.01)
    assert not s0.is_candidate(0.89, 0.05) and not s0.is_candidate(0.95, 0.004)
    assert not s0.is_candidate(0.95, 0.03, actual_is_top=False)
    top, p1, p2, H = s0.lp_stats({"5": dict(logprob=math.log(0.9)), "7": dict(logprob=math.log(0.06)), "9": dict(logprob=math.log(0.04))})
    assert [t for t, _ in top] == [5, 7, 9] and abs(p1 - 0.9) < 1e-9 and abs(p2 - 0.06) < 1e-9 and 0.3 < H < 0.5


def test_alias_normaliser():
    d = s0.differs
    assert not d("ARG-VALUE", "/home/user/A.txt</ifm|arg_value>\n<ifm|arg_key>", '"/home/user/a.txt"</ifm|arg_value>')  # case + quotes
    assert not d("ARG-VALUE", "  report  q3</ifm|arg_value>", "report q3</ifm|arg_value>")  # whitespace
    assert d("ARG-VALUE", "/home/user/a.txt</ifm|arg_value>", "/home/user/b.txt</ifm|arg_value>")
    assert not d("ARG-VALUE", "/home/user/notes", "/home/user/notes.txt</ifm|arg_value>")  # cut-off prefix of the same value
    assert d("ARG-VALUE", "/home/user/notes</ifm|arg_value>", "/home/user/notes.txt</ifm|arg_value>")
    assert not d("TOOL-NAME", "Read_File\n<ifm|arg_key>", "read_file\n<ifm|arg_key>")
    assert d("TOOL-NAME", "read_file\n<ifm|arg_key>", "list_dir\n<ifm|arg_key>")
    assert not d("TURN-START", "<ifm|tool_calls>\n<ifm|tool_call>a", "Let me check.<ifm|tool_calls>\n<ifm|tool_call>b")  # still a tool turn
    assert d("TURN-START", "<ifm|tool_calls>\n<ifm|tool_call>a", "All done.<|ifm|im_end|>")
    assert d("TURN-START", "All done.<|ifm|im_end|>", "Which file do you mean?<|ifm|im_end|>")


def sim(task, calls_per_turn):
    """Run tool calls through a World the way episode.py does; returns a transcript."""
    w, tr = s0.World.from_json(task["state"]), []
    for k, calls in enumerate(calls_per_turn):
        tr.append(dict(role="assistant", content="", tool_calls=[dict(id=f"c{k}{j}", type="function", function=dict(name=n, arguments=json.dumps(a))) for j, (n, a) in enumerate(calls)]))
        for j, (n, a) in enumerate(calls):
            tr.append(dict(role="tool", tool_call_id=f"c{k}{j}", name=n, content=w.call(n, a)))
    tr.append(dict(role="assistant", content="done"))
    return tr


def test_replay_equality_sandbox():
    t = next(x for x in TASKS if x["scenario"] == "multi_step")
    tr = sim(t, [[("list_dir", dict(path="/home/user"))], [("calendar_create_event", dict(title="x", start="2026-10-27T14:00", end="2026-10-27T15:00")),
                                                       ("set_reminder", dict(text="r", when="tomorrow"))], [("calendar_list_events", dict(start_date="2026-10-27", end_date="2026-10-27"))]])
    n, bad, raw = s0.replay_prefix(t, tr, 5)
    assert n == 4 and bad == [] and raw == 4
    rep = s0.replay_report({t["id"]: t}, [dict(task_id=t["id"], transcript=tr)], 20)
    assert rep["passed"] and rep["prefixes"] == 3 and rep["outputs"] == 1 + 3 + 4
    tr[1]["content"] = "tampered"  # a changed tool output must be caught
    assert s0.replay_prefix(t, tr, 5)[1] != []
    fired = s0.Counter()
    assert s0.normalise_out("at 2026-10-24T10:11:12Z id call_0123abcd", fired) == "at <TS> id <ID>" and set(fired) == {"iso_timestamp_with_seconds", "call_id"}


def test_check_kinds_g3():
    c = s0.check_kinds(os.path.join(s0.R1, "rlaif_copy", "checks.py"), {"reply_contains": 3, "file_exists": 2})
    assert c["kinds"]["reply_contains"] == "reply" and c["kinds"]["file_exists"] == "end-state" and c["kinds"]["no_email_sent"] == "end-state"
    assert c["passed"] and not c["unclassified"] and not c["nondeterminism_imports"]


def test_verdict():
    ok2, ok3 = dict(passed=True), dict(passed=True)
    mk = lambda n: dict(survivors=n, by_type={"TURN-START": n // 2, "ARG-VALUE": n - n // 2})
    v = s0.verdict({f"t{i}": mk(8 if i < 7 else 7) for i in range(10)}, ok2, ok3, 10)
    assert v["G1"]["share"] == 0.7 and v["G1"]["passed"] and v["go"] and v["turn_start_share"] > 0.4
    v = s0.verdict({f"t{i}": mk(8 if i < 6 else 7) for i in range(10)}, ok2, ok3, 10)
    assert not v["G1"]["passed"] and not v["go"]
    assert not s0.verdict({"a": mk(20)}, dict(passed=False), ok3)["go"]
    assert not s0.verdict({"a": mk(20)}, ok2, dict(passed=False))["go"]
    assert not s0.verdict({}, ok2, ok3)["go"]


def test_pick_transcripts():
    rows = [dict(task_id="a", arm=arm, try_idx=i, success=ok) for arm, i, ok in [("plain", 0, False), ("IND", 3, False), ("IND", 1, False), ("IND", 2, True), ("IND.s2", 0, False)]]
    sel = s0.pick_transcripts(rows, {"a"})
    assert [(r["arm"], r["try_idx"]) for r in sel["a"]] == [("IND", 1), ("IND", 3)]


class FakeServer:
    """Every position: token 0 or the true token is 0.95 likely, one runner-up at 0.03. Completion: fixed text."""
    def __init__(self, tok, completion):
        self.tok, self.completion, self.calls = tok, completion, 0

    async def prompt_logprobs(self, ids):
        out = [None]
        for i, t in enumerate(ids[1:], 1):
            out.append({str(t): dict(logprob=math.log(0.95)), str(t + 1000): dict(logprob=math.log(0.03))})
        return out

    async def greedy(self, ids, n):
        self.calls += 1
        return self.completion


def test_end_to_end_fake(tmp_path):
    t = TASK
    tr = sim(t, [[("read_file", dict(path="/home/user/a.txt"))]])
    rec = dict(task_id=t["id"], arm="IND", try_idx=0, success=False, transcript=tr, extra_block=None)
    rows = [rec, dict(rec, try_idx=1)]
    res = tmp_path / "run"; res.mkdir()
    (res / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (res / "target.json").write_text(json.dumps(dict(T=[t["id"]])))
    tok = FakeTok()
    srv = FakeServer(tok, "I will just answer.<|ifm|im_end|>")
    a = types.SimpleNamespace(results=str(res / "results.jsonl"), target=None, out=str(tmp_path / "o"), per_task=2, prefixes_per_type=20, max_cand=60,
                              limit=0, tokenizer=None, template=None, base_url=None, model=None, api_key=None, concurrency=2)
    g = asyncio.run(s0.run(a, tok, srv))
    assert g["G2"]["passed"] and g["G3"]["passed"]
    # the forced completion is an answer, so TURN-START (tool -> answer) survives; tool names / values stay alias or not depending on text
    assert g["per_task"][t["id"]]["transcripts"] == 2 and g["survivors_by_type"].get("TURN-START", 0) >= 1
    for f in ("gate.json", "gate.md", "forks.jsonl", "token_stats.jsonl"):
        assert (tmp_path / "o" / f).exists()
    assert "Doubt Forks Step 0 gate" in (tmp_path / "o" / "gate.md").read_text()
