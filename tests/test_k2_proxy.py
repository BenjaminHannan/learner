import json
import shutil
import urllib.request
from pathlib import Path

import pytest

from practice import k2_proxy as K
from tests import k2_fake_upstream as F

TOOLS = [{"type": "function", "function": {"name": "bash", "description": "run", "parameters": {"type": "object", "properties": {
    "command": {"type": "string"}, "timeout": {"type": "integer"}, "flag": {"type": "boolean"}, "xs": {"type": "array"}, "ratio": {"type": "number"}}, "required": ["command"]}}}]
TPL = Path(__file__).parent / "k2_nothink.jinja"


def call(name, **kw):
    inner = "".join(f"<ifm|arg_key>{k}</ifm|arg_key>\n<ifm|arg_value>{v}</ifm|arg_value>\n" for k, v in kw.items())
    return f"<ifm|tool_call>{name}\n{inner}</ifm|tool_call>"


# ------------------------------------------------------------------ parsing
def test_single_call():
    t = "Let me run it.\n<ifm|tool_calls>\n" + call("bash", command="print(1)") + "\n</ifm|tool_calls>"
    content, calls = K.parse_native(t, TOOLS)
    assert content == "Let me run it.\n"
    assert calls == [{"name": "bash", "arguments": {"command": "print(1)"}}]


def test_multi_arg_coercion():
    t = "<ifm|tool_calls>\n" + call("bash", command="ls\n-l", timeout="5000", flag="true", xs="[1, 2]", ratio="2.5") + "\n</ifm|tool_calls>"
    content, calls = K.parse_native(t, TOOLS)
    assert content is None
    assert calls[0]["arguments"] == {"command": "ls\n-l", "timeout": 5000, "flag": True, "xs": [1, 2], "ratio": 2.5}


def test_coercion_falls_back_to_string():
    t = "<ifm|tool_calls>\n" + call("bash", command="x", timeout="soon", flag="maybe") + "\n</ifm|tool_calls>"
    assert K.parse_native(t, TOOLS)[1][0]["arguments"] == {"command": "x", "timeout": "soon", "flag": "maybe"}


def test_two_calls():
    t = "<ifm|tool_calls>\n" + call("bash", command="a") + "\n" + call("read", path="/x") + "\n</ifm|tool_calls>"
    _, calls = K.parse_native(t, TOOLS)
    assert [(c["name"], c["arguments"]) for c in calls] == [("bash", {"command": "a"}), ("read", {"path": "/x"})]


def test_no_call():
    assert K.parse_native("Just text <answer>4</answer>", TOOLS) == ("Just text <answer>4</answer>", [])


def test_unclosed_call():
    t = "ok\n<ifm|tool_calls>\n<ifm|tool_call>bash\n<ifm|arg_key>command</ifm|arg_key>\n<ifm|arg_value>python3 -c 'print(2)'"  # cut off mid-value
    content, calls = K.parse_native(t, TOOLS)
    assert content == "ok\n" and calls == [{"name": "bash", "arguments": {"command": "python3 -c 'print(2)'"}}]
    # closed call but the stop string was dropped by the server
    t2 = "<ifm|tool_calls>\n" + call("bash", command="x") + "\n"
    assert K.parse_native(t2, TOOLS)[1] == [{"name": "bash", "arguments": {"command": "x"}}]


def test_typed_and_json_forms():
    typed = "<ifm|tool_calls>\n<ifm|tool_call>bash\n<ifm|arg_key>timeout</ifm|arg_key>\n<ifm|arg_type>integer</ifm|arg_type>\n<ifm|arg_value>7</ifm|arg_value>\n</ifm|tool_call>\n</ifm|tool_calls>"
    assert K.parse_native(typed, TOOLS)[1][0]["arguments"] == {"timeout": 7}
    js = '<ifm|tool_calls>\n<ifm|tool_call>{"name": "bash", "arguments": {"command": "ls"}}</ifm|tool_call>\n</ifm|tool_calls>'
    assert K.parse_native(js, TOOLS)[1] == [{"name": "bash", "arguments": {"command": "ls"}}]


def test_openai_calls_shape():
    oc = K.to_openai_calls([{"name": "bash", "arguments": {"command": "a"}}])[0]
    assert oc["type"] == "function" and oc["id"].startswith("call_") and oc["function"]["name"] == "bash"
    assert json.loads(oc["function"]["arguments"]) == {"command": "a"}


def test_map_messages():
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": None, "reasoning_content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "{\"command\": \"ls\"}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "out"}]
    m = K.map_messages(msgs)
    assert m[2]["content"] == "" and "reasoning_content" not in m[2]
    assert m[2]["tool_calls"][0]["function"]["arguments"] == {"command": "ls"}
    assert m[3]["content"] == "out"


def test_render_matches_native_form():
    """The template renders a mapped assistant tool_call history exactly in the form the parser reads back."""
    from practice import oc_lessons as L
    call_text = "I will check.\n<ifm|tool_calls>\n" + call("bash", command="print(6)", timeout=1000).replace("1000", "1000") + "\n</ifm|tool_calls>"
    content, calls = K.parse_native(call_text, TOOLS)
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "Q"},
            {"role": "assistant", "content": content, "tool_calls": K.to_openai_calls(calls)}, {"role": "tool", "tool_call_id": "x", "content": "6"}]
    p = L.render_prompt(msgs, TOOLS, template_path=TPL)
    assert p.endswith("<|ifm|im_start|>tool\n6<|ifm|im_end|><|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>")
    assert "<ifm|tool_call>bash\n<ifm|arg_key>command</ifm|arg_key>\n<ifm|arg_value>print(6)</ifm|arg_value>\n" in p
    assert K.parse_native(p[p.index("I will check"):p.index("<|ifm|im_end|>", p.index("I will check"))], TOOLS)[1][0]["arguments"]["command"] == "print(6)"
    assert "<ifm|tools>" in p or "bash" in p


# ------------------------------------------------------------------ SSE
def test_sse_shape():
    resp, _ = K.build_response("hi\n<ifm|tool_calls>\n" + call("bash", command="a") + "\n" + call("bash", command="b") + "\n</ifm|tool_calls>", TOOLS,
                               {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}, "m")
    ch = K.sse_chunks(resp, include_usage=True)
    assert ch[-1] == "[DONE]"
    objs = [json.loads(c) for c in ch[:-1]]
    assert objs[0]["choices"][0]["delta"] == {"role": "assistant", "content": ""}
    assert objs[1]["choices"][0]["delta"] == {"content": "hi\n"}
    tcs = [o["choices"][0]["delta"]["tool_calls"][0] for o in objs[2:4]]
    assert [t["index"] for t in tcs] == [0, 1] and all(t["type"] == "function" and t["id"] for t in tcs)
    assert json.loads(tcs[1]["function"]["arguments"]) == {"command": "b"}
    assert objs[4]["choices"][0]["finish_reason"] == "tool_calls"
    assert objs[5]["choices"] == [] and objs[5]["usage"]["total_tokens"] == 3


# ------------------------------------------------------------------ end to end with a fake upstream
def post(port, body, headers=None, path="/v1/chat/completions"):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", json.dumps(body).encode(), {"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(), r.headers


@pytest.fixture
def stack(tmp_path):
    up = F.start()
    px = K.Proxy(f"http://127.0.0.1:{up.server_address[1]}", tmp_path / "log")
    port = px.start_thread(0)
    yield up, px, port
    px.stop()
    up.shutdown()


def test_proxy_end_to_end(stack, tmp_path):
    up, px, port = stack
    body = {"model": "k2", "messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "What is 1+5?"}], "tools": TOOLS, "max_tokens": 99, "temperature": 0.3}
    raw, _ = post(port, body, {"X-Practice-Try": "tryA"})
    r = json.loads(raw)
    ch = r["choices"][0]
    assert ch["finish_reason"] == "tool_calls" and ch["message"]["content"] == "I will check it.\n"
    tc = ch["message"]["tool_calls"][0]
    assert tc["function"]["name"] == "bash" and json.loads(tc["function"]["arguments"])["command"] == "python3 -c 'print(6)'"
    # upstream saw: forced model, stop string, tools, mapped params, no stream
    q = up.requests[0]
    assert q["model"] == "default_model" and q["stop"] == [K.STOP] and q["stream"] is False and q["max_tokens"] == 99 and q["temperature"] == 0.3 and q["tools"]
    # the stop string was dropped by the fake; the proxy re-appended it in the logged raw text
    log = K.read_try_log(tmp_path / "log", "tryA")
    assert len(log) == 1 and log[0]["completion_text"].endswith(K.STOP) and log[0]["tools"] == TOOLS and log[0]["usage"]["completion_tokens"] == 7
    # second turn: history with the tool call and result -> final answer, no tool_calls
    msgs = body["messages"] + [{"role": "assistant", "content": ch["message"]["content"], "tool_calls": ch["message"]["tool_calls"]}, {"role": "tool", "tool_call_id": tc["id"], "content": "6\n"}]
    r2 = json.loads(post(port, {**body, "messages": msgs}, {"X-Practice-Try": "tryA"})[0])
    assert r2["choices"][0]["finish_reason"] == "stop" and "tool_calls" not in r2["choices"][0]["message"] and "<answer>6</answer>" in r2["choices"][0]["message"]["content"]
    assert isinstance(up.requests[1]["messages"][2]["tool_calls"][0]["function"]["arguments"], dict)  # mapped for the template
    log = K.read_try_log(tmp_path / "log", "tryA")
    assert [c["seq"] for c in log] == [0, 1] and len({c["tools_hash"] for c in log}) == 1 and len(list((tmp_path / "log" / "tools").iterdir())) == 1


def test_proxy_stream_and_models_and_keys(stack, tmp_path):
    up, px, port = stack
    body = {"messages": [{"role": "user", "content": "hello there"}], "tools": TOOLS, "stream": True, "stream_options": {"include_usage": True}}
    raw, hdr = post(port, body)
    assert hdr["Content-Type"].startswith("text/event-stream")
    lines = [l[6:] for l in raw.decode().split("\n\n") if l.startswith("data: ")]
    assert lines[-1] == "[DONE]" and json.loads(lines[-3])["choices"][0]["finish_reason"] == "tool_calls"
    assert up.requests[0]["stream"] is False  # upstream is never streamed
    assert list((tmp_path / "log").glob("try_msg*.jsonl"))  # keyed by the first user message when no header
    post(port, body, path="/t/pathkey/v1/chat/completions")
    assert (tmp_path / "log" / "try_pathkey.jsonl").exists()
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models") as r:
        assert json.load(r)["data"][0]["id"] == "k2"


def test_upstream_error_is_reported(tmp_path):
    px = K.Proxy("http://127.0.0.1:9", tmp_path)  # nothing listens there
    port = px.start_thread(0)
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            post(port, {"messages": [{"role": "user", "content": "x"}]})
        assert e.value.code == 502
    finally:
        px.stop()


# ------------------------------------------------------------------ lessons
def test_render_try_matches_served_prompt(stack, tmp_path):
    from practice import oc_lessons as L
    up, px, port = stack
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "Q"}]
    post(port, {"messages": msgs, "tools": TOOLS}, {"X-Practice-Try": "r1"})
    log = K.read_try_log(tmp_path / "log", "r1")
    rec = {"proxy_calls": [{"request_messages": c["request_messages"], "tools_hash": c["tools_hash"], "completion_text": c["completion_text"]} for c in log],
           "proxy_tools": {c["tools_hash"]: c["tools"] for c in log}}
    (p, c), = L.render_try(rec, None, TPL)
    assert p.startswith("<|ifm|im_start|>system\n# Tools") and p.endswith("<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>") and "Q<|ifm|im_end|>" in p
    assert c.endswith("</ifm|tool_calls><|ifm|im_end|>")

    class Tok:  # char-level stand-in for a tokenizer
        def __call__(self, t, add_special_tokens=False):
            return type("R", (), {"input_ids": list(t)})
    rows = L.lengths(rec, Tok(), TPL)
    assert rows[0]["prompt_tokens"] == len(p) and rows[0]["total"] == len(p) + len(c) and rows[0]["over_cap"] == (len(p) + len(c) > 2048)


# ------------------------------------------------------------------ real opencode through the proxy
@pytest.mark.skipif(shutil.which("opencode") is None, reason="opencode is not installed")
def test_opencode_end_to_end(stack, tmp_path):
    from practice.oc_harness import OpenCodeHarness
    up, px, port = stack
    h = OpenCodeHarness(f"http://127.0.0.1:{port}", tmp_path / "log", concurrency=2, timeout=150, log=lambda *a: None)
    puzzles = [{"id": "p1", "prompt": "What is 1+5?", "answer": "6", "answer_type": "int", "kind": "arith", "source": "test"}]
    done = []
    recs = h.run(puzzles, 1, seed=0, on_done=done.append, label="t")
    assert len(recs) == 1 and done == recs
    r = recs[0]
    assert r["correct"] and r["answered"] and r["answer"] == "6" and r["end"] == "answer", r.get("error")
    assert r["harness"] == "opencode" and r["tools"] == ["bash"] and r["tool_calls"] == 1 and r["turns"] == 2
    assert [m["role"] for m in r["messages"]] == ["system", "user", "assistant", "tool", "assistant"]
    assert r["messages"][1]["content"].startswith("What is 1+5?")  # not wrapped in quotes
    assert len(r["proxy_calls"]) == 2 and r["gen_tokens"] == 14 and h.stats["rollouts"] == 1
    for k in ("id", "try", "kind", "source", "messages", "tool_calls", "tools", "turns", "answer", "answered", "correct", "gen_tokens", "web", "end", "seconds"):
        assert k in r
    # only the allowed tools reach K2; no title/summary side calls
    names = sorted(t["function"]["name"] for t in up.requests[0]["tools"])
    assert names == ["bash", "edit", "read", "webfetch", "websearch", "write"]  # edit comes with write in opencode
    assert len(up.requests) == 2
    from practice import oc_lessons as L
    pairs = L.render_try(r, None, TPL)
    assert len(pairs) == 2 and pairs[1][0].endswith("<ifm|think>\n</ifm|think>")


def test_proxy_refuses_long_prompt():
    from practice.k2_proxy import CONTEXT_ERR, ContextTooLong, Proxy
    import tempfile
    px = Proxy("http://127.0.0.1:9", tempfile.mkdtemp(), max_prompt_chars=100)
    try:
        px.complete({"messages": [{"role": "user", "content": "x" * 200}]}, "k")
        assert False
    except ContextTooLong as e:
        assert CONTEXT_ERR in str(e)
