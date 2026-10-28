"""Probe-5 tests. No model and no real server: a stub HTTP server plays llama-server (request bodies are recorded, replies are scripted).
Pure-python parts always run; the torch / peft parts skip without torch; the tokenizer parts skip unless LFM3_TOKENIZER_DIR points at a dir with the LFM3 tokenizer files (tokenizer.json, tokenizer_config.json, chat_template.jinja)."""
import json, math, os, re, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
P5 = os.path.dirname(HERE)
sys.path.insert(0, P5)
import p5common as C  # noqa: E402
import llm_server as LS  # noqa: E402
import agent_lfm3 as AG  # noqa: E402
import self_lfm3 as SF  # noqa: E402
import gen_tests_lfm3 as GT  # noqa: E402
import check_gates as CG  # noqa: E402
import lfm3_load as L  # noqa: E402
import agent_mlx as A4  # noqa: E402
import replay  # noqa: E402

P = C.P
TASKS = P.load_tasks()
BYID = {t["id"]: t for t in TASKS}
OLD = {t["id"]: t for t in P.load_old_tasks()}      # Guess-1 tasks (t001 ...): scripted references for the episode-loop tests
TOKDIR = os.environ.get("LFM3_TOKENIZER_DIR")


# ---------- LFM3 tool-call text exactly as the chat template renders it ----------
def lfm3_text(calls, content=""):
    """What the model writes after the (empty) think block: content, then one <tool_call> block per call, blocks separated by a blank line (checked against the real template below)."""
    blocks = []
    for c in calls:
        s = "<tool_call>\n<function=" + c["name"] + ">\n"
        for k, v in c["arguments"].items():
            s += f"<parameter={k}>\n{v if isinstance(v, str) else json.dumps(v)}\n</parameter>\n"
        blocks.append(s + "</function>\n</tool_call>")
    return content + "\n\n".join(blocks)


def schema_valid(call):
    sch = {t["function"]["name"]: t["function"]["parameters"]["properties"] for t in P.TOOLS}[call["name"]]
    ty = {"string": str, "integer": int, "boolean": bool, "array": list, "object": dict}
    return all(k in sch and isinstance(v, ty[sch[k]["type"]]) and not (sch[k]["type"] == "integer" and isinstance(v, bool)) for k, v in call["arguments"].items())


# ---------- stub llama-server ----------
class Stub:
    def __init__(self, handler):
        self.requests, self.handler = [], handler
        stub = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                self._send(200, {"status": "ok"})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                stub.requests.append((self.path, body))
                out = stub.handler(body, self.path)
                if isinstance(out, tuple):
                    self._send(*out)
                else:
                    self._send(200, out)

            def _send(self, code, obj):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


def chat_resp(content="", tool_calls=None, finish=None, usage=(11, 7), top=None):
    msg = dict(role="assistant", content=content)
    if tool_calls:
        msg["tool_calls"] = [dict(id=f"c{i}", type="function", function=dict(name=c["name"], arguments=json.dumps(c["arguments"]))) for i, c in enumerate(tool_calls)]
    ch = dict(index=0, finish_reason=finish or ("tool_calls" if tool_calls else "stop"), message=msg)
    if top:   # llama.cpp's chat shape: choices[0].logprobs.content[0].{token, logprob, top_logprobs[{token, logprob}]}
        ch["logprobs"] = dict(content=[dict(id=1, token=top[0][0], logprob=top[0][1], bytes=[], top_logprobs=[dict(id=i, token=t, logprob=lp, bytes=[]) for i, (t, lp) in enumerate(top)])])
    return dict(choices=[ch], usage=dict(prompt_tokens=usage[0], completion_tokens=usage[1], total_tokens=sum(usage)))


@pytest.fixture()
def stub():
    made = []

    def make(handler):
        s = Stub(handler)
        made.append(s)
        return s
    yield make
    for s in made:
        s.close()


# ---------- raw text tool calls ----------
def test_text_parser_reads_template_format_and_coerces_types():
    calls = [dict(name="read_file", arguments=dict(path="~/a.txt", max_lines=3)), dict(name="send_email", arguments=dict(to=["a@b.c"], subject="s", body="x\ny", cc=[]))]
    r = LS.parse_tool_text(lfm3_text(calls, "Let me check."))
    assert r["calls"] == calls and r["content"] == "Let me check."
    r = LS.parse_tool_text(lfm3_text(calls[:1]) + " and then some text")
    assert r["calls"] == calls[:1] and r["content"] == "and then some text"
    # the literal one-line form of the task statement
    one = "<tool_call><function=list_dir><parameter=path>/home/user</parameter><parameter=recursive>true</parameter></function></tool_call>"
    assert LS.parse_tool_text(one)["calls"] == [dict(name="list_dir", arguments=dict(path="/home/user", recursive=True))]
    assert LS.parse_tool_text("<tool_call><function=list_dir></function></tool_call>")["calls"] == [dict(name="list_dir", arguments={})]
    assert LS.parse_tool_text("Just text.") == dict(content="Just text.", calls=[])


def test_text_parser_is_strict_like_probe4():
    ok = lfm3_text([dict(name="read_file", arguments=dict(path="~/a.txt", max_lines=3))], "hi ")
    for broken in (lfm3_text([dict(name="no_such_tool", arguments={})]),                                         # unknown tool: whole group dropped
                   ok.replace("<parameter=max_lines>", "<parameter=path>"),                                         # duplicate argument
                   ok.replace("</function>", "junk</function>"),                                                    # stray text inside the function
                   "<tool_call>stuff <function=list_dir></function></tool_call>",                                   # stray text in the group
                   "<tool_call><function=list_dir>",                                                                # never closed
                   "<function=list_dir></function> middle <function=list_dir></function>"):                       # text between two functions
        r = LS.parse_tool_text(broken)
        assert r["calls"] == [] and r["content"] == broken.strip(), broken


def g1_calls(limit=600):
    out = []
    for ln in open(os.path.join(C.CREATIVE, "probe3", "inputs", "guess1_run", "results.jsonl")):
        r = json.loads(ln)
        for m in r["transcript"]:
            if m.get("tool_calls"):
                out.append([dict(name=c["function"]["name"], arguments=json.loads(c["function"]["arguments"])) for c in m["tool_calls"]])
        if len(out) >= limit:
            break
    return out


def test_text_parser_round_trips_real_tool_calls():
    rows = g1_calls()
    assert len(rows) >= 300
    bad = 0
    for i, calls in enumerate(rows):
        content = ["", "Let me check. ", "I'll look that up. "][i % 3]
        got = LS.parse_tool_text(lfm3_text(calls, content))
        ok = len(got["calls"]) == len(calls) and all(g["name"] == c["name"] and g["arguments"] == c["arguments"] for g, c in zip(got["calls"], calls)) and got["content"] == content.strip()
        if not ok:
            assert not all(schema_valid(c) for c in calls), (calls, got)       # only a value of the wrong type may be coerced differently
            bad += 1
    assert bad <= len(rows) * 0.02


@pytest.mark.skipif(not TOKDIR, reason="LFM3_TOKENIZER_DIR not set")
def test_helper_text_equals_the_real_chat_template_rendering():
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(TOKDIR)
    for calls in g1_calls(60):
        msgs = [dict(role="system", content="s"), dict(role="user", content="u"), dict(role="assistant", content="Let me check.", tool_calls=[dict(id="x", type="function", function=c) for c in calls])]
        pre = tok.apply_chat_template(msgs[:2], tools=P.TOOLS, add_generation_prompt=True, tokenize=False, enable_thinking=False)
        full = tok.apply_chat_template(msgs, tools=P.TOOLS, tokenize=False, enable_thinking=False)
        assert pre.endswith("<|im_start|>assistant\n<think></think>") and full.startswith(pre) and full.endswith("<|im_end|>\n")
        assert full[len(pre):-len("<|im_end|>\n")] == lfm3_text(calls, "Let me check.")


def test_cut_think():
    assert LS.cut_think("Paris</think>Paris") == "Paris"
    assert LS.cut_think("<think>hmm</think>\n\nanswer") == "\n\nanswer"
    assert LS.cut_think("a</think>b</think>c") == "c"
    assert LS.cut_think("plain") == "plain" and LS.cut_think(None) == ""


# ---------- client against the stub ----------
def test_chat_request_fields_and_lora_scale(stub):
    s = stub(lambda body, path: chat_resp("ok"))
    cl = LS.LlamaServer(s.url, retries=1)
    msgs = [dict(role="system", content="s"), dict(role="user", content="hello")]
    cl.chat(msgs, P.TOOLS, temperature=0.7, top_p=0.95, max_tokens=512, seed=5, lora_scale=0.0)
    cl.chat(msgs, P.TOOLS, lora_scale=1.0)
    cl.chat(msgs, None)
    (p0, b0), (p1, b1), (_, b2) = s.requests
    assert p0 == "/v1/chat/completions"
    assert b0["lora"] == [dict(id=0, scale=0.0)] and b1["lora"] == [dict(id=0, scale=1.0)] and "lora" not in b2     # explicit per request; absent = server default
    assert b0["chat_template_kwargs"] == dict(enable_thinking=False) and b0["tools"] == P.TOOLS and b0["messages"] == msgs
    assert (b0["temperature"], b0["top_p"], b0["max_tokens"], b0["seed"], b0["stream"]) == (0.7, 0.95, 512, 5, False)
    assert "tools" not in b2 and "logprobs" not in b0
    cl.chat(msgs, None, top_logprobs=20)
    assert s.requests[-1][1]["logprobs"] is True and s.requests[-1][1]["top_logprobs"] == 20


def test_native_tool_calls_text_fallback_and_think_cut(stub):
    calls = [dict(name="read_file", arguments=dict(path="~/a.txt", max_lines=3))]
    script = iter([chat_resp("Checking.", tool_calls=calls),                                # server parsed the call
                   chat_resp("</think>" + lfm3_text(calls, "Checking. ")),                  # server returned the raw text as content
                   chat_resp("Paris</think>Paris"),
                   chat_resp("", tool_calls=[dict(name="bogus", arguments={})]),            # unknown tool: no calls
                   chat_resp("x", finish="length", usage=(100, 512))])
    cl = LS.LlamaServer(stub(lambda b, p: next(script)).url, retries=1)
    r = cl.chat([dict(role="user", content="u")], P.TOOLS)
    assert r.calls == calls and r.source == "native" and r.content == "Checking." and (r.prompt_tokens, r.completion_tokens) == (11, 7)
    r = cl.chat([dict(role="user", content="u")], P.TOOLS)
    assert r.calls == calls and r.source == "text" and r.content == "Checking."
    r = cl.chat([dict(role="user", content="u")], P.TOOLS)
    assert r.calls == [] and r.content == "Paris" and r.source == "none"
    r = cl.chat([dict(role="user", content="u")], P.TOOLS)
    assert r.calls == [] and r.source == "none"
    r = cl.chat([dict(role="user", content="u")], P.TOOLS)
    assert r.hit_max and r.completion_tokens == 512


def test_native_arguments_are_coerced_to_the_schema():
    nat = [dict(id="a", type="function", function=dict(name="read_file", arguments=json.dumps({"path": "~/a", "max_lines": "5"})))]
    assert LS.parse_native_calls(nat) == [dict(name="read_file", arguments=dict(path="~/a", max_lines=5))]
    bad = [dict(id="a", type="function", function=dict(name="read_file", arguments="{not json"))]
    assert LS.parse_native_calls(bad) is None


def test_http_errors(stub, monkeypatch):
    monkeypatch.setattr(LS.time, "sleep", lambda s: None)            # no waiting in tests
    n = [0]

    def h(body, path):
        n[0] += 1
        return (500, {"error": "busy"}) if n[0] < 3 else chat_resp("ok")
    cl = LS.LlamaServer(stub(h).url, retries=5)
    assert cl.chat([dict(role="user", content="u")]).content == "ok" and n[0] == 3          # 5xx is retried
    m = [0]

    def h400(body, path):
        m[0] += 1
        return 400, {"error": {"message": "prompt exceeds context"}}
    cl = LS.LlamaServer(stub(h400).url, retries=5)
    with pytest.raises(LS.ServerError) as e:
        cl.chat([dict(role="user", content="u")])
    assert e.value.status == 400 and m[0] == 1                                              # 4xx is not


# ---------- SELF logprobs ----------
def test_p_yes_from_top_follows_pick1_rule():
    top = [("Yes", math.log(0.5)), (" no", math.log(0.2)), ("yes", math.log(0.1)), ("\tNO", math.log(0.05)), ("The", math.log(0.1)), ("maybe", math.log(0.05))]
    assert LS.p_yes_from_top(top) == pytest.approx(0.6 / 0.85)
    assert LS.p_yes_from_top([("The", -0.1)]) is None and LS.p_yes_from_top(None) is None
    # only the top 20 by logprob count: a 'yes' ranked 21st is ignored
    filler = [(f"t{i}", -1.0 - i * 0.01) for i in range(20)]
    assert LS.p_yes_from_top(filler + [("yes", -5.0)]) is None
    assert LS.p_yes_from_top(filler + [("yes", -5.0)], topk=21) == 1.0


def test_logprob_extraction_shapes():
    top = [("Yes", -0.2), ("No", -1.7)]
    assert LS.top_from_response(chat_resp("Yes", top=top)["choices"][0]) == top
    comp = dict(completion_probabilities=[dict(token="Yes", logprob=-0.2, top_logprobs=[dict(token="Yes", logprob=-0.2), dict(token="No", logprob=-1.7)])])      # /completion
    assert LS.top_from_response(comp) == top
    old = dict(completion_probabilities=[dict(content="Yes", probs=[dict(tok_str="Yes", prob=math.exp(-0.2)), dict(tok_str="No", prob=math.exp(-1.7))])])
    got = LS.top_from_response(old)
    assert [t for t, _ in got] == ["Yes", "No"] and got[1][1] == pytest.approx(-1.7)
    assert LS.top_from_response(chat_resp("Yes")["choices"][0]) is None


def test_client_p_yes_asks_for_one_token_no_tools_base_adapter(stub):
    s = stub(lambda b, p: chat_resp("Yes", top=[("Yes", math.log(0.75)), ("No", math.log(0.25))], usage=(321, 1)))
    cl = LS.LlamaServer(s.url, retries=1)
    p, n, top = cl.p_yes("Did it work? Answer yes or no.")
    body = s.requests[0][1]
    assert p == pytest.approx(0.75) and n == 321
    assert body["max_tokens"] == 1 and body["temperature"] == 0.0 and body["logprobs"] is True and body["top_logprobs"] == 20 and "tools" not in body
    assert body["messages"] == [dict(role="user", content="Did it work? Answer yes or no.")] and body["lora"] == [dict(id=0, scale=0.0)]
    assert body["chat_template_kwargs"] == dict(enable_thinking=False)


def test_check_lora_detects_an_ignored_lora_field(stub):
    def honoured(body, path):
        sc = body["lora"][0]["scale"]
        return chat_resp("a", top=[("a", -0.5 - 0.1 * sc), ("b", -1.5 + 0.1 * sc)])
    diff, noise, _, _ = LS.check_lora(LS.LlamaServer(stub(honoured).url, retries=1))
    assert diff == pytest.approx(0.1) and noise == 0
    diff, noise, _, _ = LS.check_lora(LS.LlamaServer(stub(lambda b, p: chat_resp("a", top=[("a", -0.5), ("b", -1.5)])).url, retries=1))
    assert diff == 0


# ---------- the whole pipeline against a scripted server, ending in analyze_e2e ----------
def scripted_server(tasks):
    """Stands in for llama-server: agent turns follow each task's reference plan (a coin flip per turn from the request seed decides whether the 'model' goes on or bails out; native tool_calls for even seeds, raw text for
    odd ones), SELF requests get a fixed yes/no, the test writer returns the reference checks at adapter scale 1.0 and a useless check at 0.0."""
    byuser = {t["user"]: t for t in tasks}
    byprompt = {}
    import write_probes as wp
    for t in tasks:
        byprompt[wp.task_prompt(t, with_state=True)] = t

    def h(body, path):
        msgs, scale = body["messages"], (body.get("lora") or [dict(scale=1.0)])[0]["scale"]
        if body.get("max_tokens") == 1:
            return chat_resp("Yes", top=[("Yes", math.log(0.6)), ("No", math.log(0.4))], usage=(50, 1))
        if msgs[0]["content"] in byprompt:
            t = byprompt[msgs[0]["content"]]
            checks = t["checks"] if scale >= 1.0 else [dict(type="no_email_sent")]
            return chat_resp("<think></think>" + json.dumps(dict(checks=checks)), usage=(400, 60))
        t = byuser[msgs[1]["content"]]
        k = sum(m["role"] == "assistant" for m in msgs)
        assert msgs[0]["role"] == "system" and body["tools"] == P.TOOLS and body["lora"] == [dict(id=0, scale=0.0)] and body["chat_template_kwargs"] == dict(enable_thinking=False)
        if body["seed"] % 3 == 0:
            return chat_resp("Done.", usage=(100 + k, 5))
        if k < len(t["reference"]):
            call = t["reference"][k]
            if body["seed"] % 2 == 0:
                return chat_resp("", tool_calls=[call], usage=(100 + k, 20))
            return chat_resp(lfm3_text([call], "Working. "), usage=(100 + k, 20))
        return chat_resp(t["reference_reply"], usage=(100 + k, 12))
    return h


def run_main(mod, argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x"] + argv)
    return mod.main()


def test_pipeline_outputs_feed_analyze_e2e(stub, tmp_path, monkeypatch):
    tasks = TASKS[:4]
    tf = tmp_path / "tasks.jsonl"
    tf.write_text("".join(json.dumps(t) + "\n" for t in tasks))
    s = stub(scripted_server(tasks))
    out = str(tmp_path)
    common = ["--url", s.url, "--no-pause-flag", "--parallel", "3"]
    assert run_main(AG, ["--tasks", str(tf), "--out", out + "/tries", "--tries", "12"] + common, monkeypatch) == 0
    assert run_main(SF, ["--tries", out + "/tries/results.jsonl", "--tasks", str(tf), "--pools", out + "/pools.jsonl", "--out", out + "/self_scores.jsonl"] + common, monkeypatch) == 0
    assert run_main(GT, ["--arm", "base", "--tasks-file", str(tf), "--out-dir", out + "/tests_b"] + common, monkeypatch) == 0
    assert run_main(GT, ["--arm", "tuned", "--tasks-file", str(tf), "--out-dir", out + "/tests_t"] + common, monkeypatch) == 0
    rows = [json.loads(l) for l in open(out + "/tries/results.jsonl")]
    assert len(rows) == 48 and {(r["task_id"], r["try_idx"]) for r in rows} == {(t["id"], i) for t in tasks for i in range(12)}
    need = {"task_id", "scenario", "arm", "try_idx", "success", "checks", "transcript", "n_turns", "tokens", "final_reply", "reply_log", "extra_block", "trap", "turns_hit_max"}
    assert all(set(r) >= need and r["arm"] == "IND" and r["transcript"][0]["role"] == "user" for r in rows)
    assert any(r["success"] for r in rows) and not all(r["success"] for r in rows)
    srcs = {x for r in rows for x in r["tool_call_sources"]}
    assert {"native", "text"} <= srcs                                  # both parsing paths were exercised
    for r in rows:
        t = BYID[r["task_id"]]
        assert replay.success_of(t, *replay.replay_try(t, r)) == r["success"]
    sc = [json.loads(l) for l in open(out + "/self_scores.jsonl")]
    assert len(sc) == 48 and all(set(x) == {"key", "p_yes", "n_prompt"} and x["p_yes"] == pytest.approx(0.6) and x["n_prompt"] == 50 for x in sc)
    pb = [json.loads(l) for l in open(out + "/tests_b/probes_lfm3base.jsonl")]
    pt = [json.loads(l) for l in open(out + "/tests_t/probes_lfm3.jsonl")]
    assert len(pb) == len(pt) == 16 and all(set(r) >= {"key", "task", "sample", "parse_ok", "checks", "raw"} and r["parse_ok"] for r in pt)
    gl = [json.loads(l) for l in open(out + "/tests_t/probes_lfm3.genlog.jsonl")]
    assert len(gl) == 16 and gl[0]["prompt_tokens"] == 400 and gl[0]["new_tokens"] == 60
    lora_by_stage = {(b["max_tokens"] == 1, b.get("lora", [{}])[0].get("scale")) for _, b in s.requests}
    assert (False, 0.0) in lora_by_stage and (False, 1.0) in lora_by_stage and (True, 0.0) in lora_by_stage      # tries/TEST-B/SELF at 0.0, TEST-T at 1.0
    # resumable: a second run adds nothing
    n = len(s.requests)
    assert run_main(AG, ["--tasks", str(tf), "--out", out + "/tries", "--tries", "12"] + common, monkeypatch) == 0 and len(s.requests) == n
    # analysis (probe4/analyze_e2e unchanged)
    r = subprocess.run([sys.executable, os.path.join(P5, "analyze_p5.py"), "--tasks", str(tf), "--tries", out + "/tries/results.jsonl", "--self", out + "/self_scores.jsonl",
                        "--test-b", out + "/tests_b/probes_lfm3base.jsonl", "--test-t", out + "/tests_t/probes_lfm3.jsonl", "--out", out + "/report"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    rep = json.load(open(out + "/report/report.json"))
    assert set(rep["rates"]) == {"FIRST", "RAND", "VOTE", "SELF", "TEST-B", "TEST-T", "ORACLE"} and rep["verdict"] in ("PASS", "PROVED WRONG", "INCONCLUSIVE")
    assert rep["info"]["n_tasks"] == 4 and rep["info"]["gate"] == 1.0
    assert rep["rates"]["TEST-T"]["all"] >= rep["rates"]["TEST-B"]["all"] and rep["rates"]["TEST-T"]["all"] == pytest.approx(rep["rates"]["ORACLE"]["all"])   # reference tests pick a passing try when one exists
    assert "Probe-5 report" in open(out + "/report/report.md").read()
    assert rep["tokens"]["TEST-T"]["generated"] > rep["tokens"]["ORACLE"]["generated"]                    # genlog side file was read
    # gates
    os.makedirs(out + "/train")
    json.dump(dict(val_loss_before=1.2, val_loss_after=0.9), open(out + "/train/train_summary.json", "w"))
    res, missing = CG.evaluate(out, str(tf))
    assert not missing and all(v["ok"] for k, v in res.items() if "ok" in v), res
    assert res["parse"]["tool_call_sources"]["native"] > 0 and res["parse"]["tool_call_sources"]["text"] > 0
    json.dump(dict(val_loss_before=0.9, val_loss_after=1.2), open(out + "/train/train_summary.json", "w"))
    res, _ = CG.evaluate(out, str(tf))
    assert not res["val"]["ok"]


def test_episode_record_equals_probe4_episode_for_the_same_turns():
    """LfmEpisode must write the same record as Probe-4's Episode fed the equivalent K2 text (ids, messages, turn cap, tokens)."""
    t = OLD["t001"]
    def k2_text(calls, content=""):
        s = content + "<ifm|tool_calls>" if calls else content
        for c in calls:
            s += "\n<ifm|tool_call>" + c["name"] + "\n" + "".join(f"<ifm|arg_key>{k}</ifm|arg_key>\n<ifm|arg_value>{v if isinstance(v, str) else json.dumps(v)}</ifm|arg_value>\n" for k, v in c["arguments"].items()) + "</ifm|tool_call>"
        return s + ("\n</ifm|tool_calls>" if calls else "")
    steps = [(t["reference"][:2], "Looking. "), (t["reference"][2:], ""), ([], t["reference_reply"])]
    a, b = A4.Episode(t, 0), AG.LfmEpisode(t, 0)
    for calls, content in steps:
        if a.done:
            break
        a.step(k2_text(calls, content), 100, 20)
        b.step_reply(LS.Reply(content=content.strip(), calls=calls, prompt_tokens=100, completion_tokens=20, source="native"))
    ra, rb = a.record(), b.record()
    assert rb.pop("tool_call_sources") == ["native"] * 3 and rb.pop("server_errors") == 0
    assert ra == rb and ra["success"]
    # 6-turn cap: still calling tools -> no final reply
    loop = [dict(name="notes_search", arguments=dict(query="x"))]
    b = AG.LfmEpisode(t, 1)
    for _ in range(10):
        if b.done:
            break
        b.step_reply(LS.Reply(content="", calls=loop))
    assert b.n == 6 and b.done and b.reply == "" and not b.record()["success"]


def test_server_refusal_ends_the_try_instead_of_crashing(stub):
    cl = LS.LlamaServer(stub(lambda b, p: (400, {"error": "too long"})).url, retries=1)
    rec = AG.run_episode(cl, TASKS[0], 0)
    assert rec["final_reply"] == "" and rec["success"] is False and rec["server_errors"] == 1


def test_pause_flag_stops_before_any_request(stub, tmp_path, monkeypatch):
    s = stub(lambda b, p: chat_resp("x"))
    flag = tmp_path / "ASSISTANT_RUNNING"
    flag.write_text("1")
    monkeypatch.setenv("ASSISTANT_FLAG", str(flag))
    tf = tmp_path / "t.jsonl"
    tf.write_text(json.dumps(TASKS[0]) + "\n")
    rc = run_main(AG, ["--tasks", str(tf), "--out", str(tmp_path / "o"), "--tries", "2", "--url", s.url], monkeypatch)
    assert rc == C.EXIT_PAUSED == 75 and not [r for r in s.requests if r[0].startswith("/v1")]
    flag.unlink()
    assert run_main(AG, ["--tasks", str(tf), "--out", str(tmp_path / "o"), "--tries", "2", "--url", s.url], monkeypatch) == 0


# ---------- gates ----------
def test_gate_helpers():
    ok = dict(transcript=[dict(role="user", content="u"), dict(role="assistant", content="", tool_calls=[1])], final_reply="")
    reply = dict(transcript=[dict(role="user", content="u"), dict(role="assistant", content="hi")], final_reply="hi")
    nothing = dict(transcript=[dict(role="user", content="u"), dict(role="assistant", content="")], final_reply="")
    assert CG.parse_rate([ok, reply, nothing, ok]) == 0.75


def test_empty_share(tmp_path):
    rows = [dict(key="a|0", task="a", sample=0, checks=[dict(type="no_email_sent")], raw="x"), dict(key="a|1", task="a", sample=1, checks=None, raw=""),
            dict(key="a|2", task="a", sample=2, checks=[dict(type="bogus")], raw="y"), dict(key="a|3", task="a", sample=3, checks=[], raw="z")]
    p = tmp_path / "p.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    e = CG.empty_share(str(p), 4)
    assert e["empty"] == 3 and e["raw_empty"] == 1 and e["share"] == 0.75
    assert CG.empty_share(str(p), 8)["share"] == 3 / 8      # missing samples count as not-yet-done, never as valid


# ---------- run_m3.sh ----------
def test_run_m3_script_shape():
    sh = open(os.path.join(P5, "run_m3.sh")).read()
    assert subprocess.run(["bash", "-n", os.path.join(P5, "run_m3.sh")]).returncode == 0
    for needle in ("--smoke", "LLAMA_CPP_DIR", "ASSISTANT_RUNNING", "convert_lora_to_gguf.py", "--lora", "-np", "--jinja", "check_gates.py", "stop_server", "trap 'stop_server' EXIT", "analyze_p5.py",
                   "train_lora_lfm3.py", "HF_REV=40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd", "exit 75", "gguf/LFM3-1.7B-BF16.gguf"):
        assert needle in sh, needle
    assert "trust_remote_code" not in sh.replace("no trust_remote_code", "")


# ---------- vendored model code, LoRA targets, training (torch) ----------
def test_vendored_files_match_pinned_hashes_and_readme():
    assert L.check_hashes() == []
    readme = open(os.path.join(P5, "vendor", "README.md")).read()
    assert L.PINNED_REVISION in readme and all(h in readme for h in L.HASHES.values())


def test_target_regex_picks_exactly_the_nine_module_kinds():
    rx = re.compile(L.TARGET_REGEX)
    yes = ["model.layers.0.self_attn.q_proj", "model.layers.5.self_attn.k_proj", "model.layers.5.self_attn.v_proj", "model.layers.23.self_attn.o_proj", "model.layers.1.conv.in_proj",
           "model.layers.1.conv.out_proj", "model.layers.7.feed_forward.w1", "model.layers.7.feed_forward.w2", "model.layers.7.feed_forward.w3"]
    no = ["model.layers.2.self_attn.gate_proj", "model.layers.1.conv.conv", "model.layers.1.operator_norm", "model.layers.2.self_attn.q_norm", "model.embed_tokens", "lm_head",
          "model.layers.0.feed_forward", "model.layers.0.conv"]
    assert all(rx.fullmatch(n) for n in yes) and not any(rx.fullmatch(n) for n in no)


try:
    import torch
    import peft  # noqa: F401
    import transformers  # noqa: F401
    HAVE_TORCH = True
except Exception:  # noqa
    HAVE_TORCH = False
needs_torch = pytest.mark.skipif(not HAVE_TORCH, reason="torch / transformers / peft not installed")


@pytest.fixture(scope="module")
def tiny_dir(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("tiny"))
    modeling, _ = L.vendored()
    torch.manual_seed(0)
    modeling.Lfm3ForCausalLM(L.tiny_config(2000)).save_pretrained(d)
    return d


@needs_torch
def test_vendored_loader_round_trips_a_saved_model_without_remote_code(tiny_dir):
    modeling, _ = L.vendored()
    net = L.load_model(tiny_dir, dtype=torch.float32)
    assert type(net) is modeling.Lfm3ForCausalLM and type(net).__module__ == "lfm3_vendor.modeling_lfm3"
    x = torch.randint(0, 2000, (1, 12))
    again = modeling.Lfm3ForCausalLM(L.tiny_config(2000))
    again.load_state_dict(net.state_dict())
    assert torch.allclose(net(x).logits, again(x).logits)
    with pytest.raises(FileNotFoundError):
        L.load_model(tiny_dir + "_missing")


@needs_torch
def test_peft_hooks_all_nine_kinds_and_only_lora_trains(tiny_dir):
    from peft import LoraConfig, get_peft_model
    net = L.load_model(tiny_dir, dtype=torch.float32)
    lm = get_peft_model(net, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=L.TARGET_REGEX, task_type="CAUSAL_LM"))
    names = [n for n, p in lm.named_parameters() if p.requires_grad]
    assert names and all("lora_" in n for n in names)
    assert {k for k in L.MODULE_KINDS if any(f".{k}.lora_A" in n for n in names)} == set(L.MODULE_KINDS)
    assert not any("gate_proj" in n or "conv.conv" in n for n in names)


@needs_torch
def test_keyed_dropout_gives_the_same_gradients_with_and_without_checkpointing(tiny_dir):
    import train_lora_lfm3 as T
    from peft import LoraConfig, get_peft_model
    grads = []
    for ckpt in (False, True):
        net = L.load_model(tiny_dir, dtype=torch.float32)
        if ckpt:
            net.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            net.enable_input_require_grads()
        torch.manual_seed(1)
        lm = get_peft_model(net, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.3, target_modules=L.TARGET_REGEX, task_type="CAUSAL_LM", init_lora_weights=False))
        T.use_keyed_dropout(lm)
        lm.train()
        ids = torch.randint(0, 2000, (1, 30))
        lab = ids.clone()
        lab[:, :10] = -100
        T.KeyedDropout.SEED_BOX[0] = 7
        loss, k = T.answer_loss(lm, ids, torch.ones_like(ids), lab)
        loss.backward()
        grads.append((float(loss.detach()), {n: p.grad.clone() for n, p in lm.named_parameters() if p.requires_grad}))
        torch.manual_seed(1234)      # a different global RNG state must not matter
    assert grads[0][0] == pytest.approx(grads[1][0])
    for n, g in grads[0][1].items():
        assert torch.allclose(g, grads[1][1][n], atol=1e-5), n
    # and the mask really is dropping things and depends on the seed
    T.KeyedDropout.SEED_BOX[0] = 8
    lm.zero_grad()
    loss2, _ = T.answer_loss(lm, ids, torch.ones_like(ids), lab)
    assert float(loss2) != pytest.approx(grads[0][0])


@pytest.mark.skipif(not TOKDIR, reason="LFM3_TOKENIZER_DIR not set")
def test_encode_masks_the_prompt_and_ends_with_im_end():
    import train_lora_lfm3 as T
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(TOKDIR)
    ids, lab = T.encode(tok, "What is 2+2?", '{"checks":[]}')
    p = tok.apply_chat_template([dict(role="user", content="What is 2+2?")], add_generation_prompt=True, tokenize=False, enable_thinking=False)
    assert p.endswith("<|im_start|>assistant\n<think></think>")
    n = len(tok(p, add_special_tokens=False)["input_ids"])
    assert all(x == -100 for x in lab[:n]) and lab[n:] == ids[n:] and ids[-1] == tok.convert_tokens_to_ids("<|im_end|>")
    assert tok.decode(ids[n:-1]) == '{"checks":[]}' and T.encode(tok, "x", "y", max_len=3) is None


@needs_torch
@pytest.mark.skipif(not TOKDIR, reason="LFM3_TOKENIZER_DIR not set")
def test_training_smoke_pause_resume_and_adapter(tiny_dir, tmp_path, monkeypatch):
    import train_lora_lfm3 as T
    data = tmp_path / "data"
    data.mkdir()
    for nm, n in (("train", 8), ("val", 3)):
        (data / f"{nm}.jsonl").write_text("".join(json.dumps(dict(prompt=f"Write the checks for job {i}.", target=json.dumps(dict(checks=[dict(type="no_email_sent")])), task=f"t{i}")) + "\n" for i in range(n)))
    out = tmp_path / "train"
    base = ["--tiny", "--tokenizer", TOKDIR, "--data", str(data), "--out", str(out), "--batch", "2", "--max-steps", "6", "--save-every", "2"]
    flag = tmp_path / "ASSISTANT_RUNNING"
    flag.write_text("1")
    monkeypatch.setenv("ASSISTANT_FLAG", str(flag))
    monkeypatch.setattr(sys, "argv", ["x"] + base)
    assert T.main() == 75 and (out / "ckpt.pt").exists() and not (out / "adapter").exists()      # paused at step 0 with a checkpoint
    flag.unlink()
    assert T.main() == 0
    assert (out / "adapter" / "adapter_model.safetensors").exists() and (out / "adapter" / "adapter_config.json").exists() and not (out / "ckpt.pt").exists()
    cfg = json.load(open(out / "adapter" / "adapter_config.json"))
    assert (cfg["r"], cfg["lora_alpha"], cfg["lora_dropout"], cfg["target_modules"]) == (16, 32, 0.05, L.TARGET_REGEX)
    summ = json.load(open(out / "train_summary.json"))
    assert summ["val_loss_after"] < summ["val_loss_before"] and summ["steps"] == 6
    log = [json.loads(l) for l in open(out / "train_log.jsonl")]
    assert [r["epoch"] for r in log if r["event"] == "val"][0] == 0 and [r["step"] for r in log if r["event"] == "step"] == [1, 2, 3, 4, 5, 6]
    assert max(r["lr"] for r in log if r["event"] == "step") <= 1e-4
    from safetensors import safe_open
    keys = list(safe_open(str(out / "adapter" / "adapter_model.safetensors"), "pt").keys())
    assert keys and all(k.startswith("base_model.model.model.layers.") and ".lora_" in k for k in keys)
    monkeypatch.setattr(sys, "argv", ["x"] + base)
    assert T.main() == 0       # a finished run is not redone
