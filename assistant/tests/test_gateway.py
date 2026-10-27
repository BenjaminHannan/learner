import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fake_upstream  # noqa: E402
import gateway  # noqa: E402


def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Base(unittest.TestCase):
    small_up = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.big = fake_upstream.start()
        self.small = fake_upstream.start() if self.small_up else None
        small_url = ("http://127.0.0.1:%d" % self.small.server_port if self.small
                     else "http://127.0.0.1:%d" % free_port())
        self.srv = gateway.make_server("http://127.0.0.1:%d" % self.big.server_port, small_url,
                                       0, self.tmp.name)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_port
        self.diary = Path(self.tmp.name)
        self.big.gate.set()

    def tearDown(self):
        for s in (self.srv, self.big, self.small):
            if s:
                s.shutdown()
                s.server_close()
        self.tmp.cleanup()

    def post(self, body):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("POST", "/v1/chat/completions", json.dumps(body), {"Content-Type": "application/json"})
        return c, c.getresponse()

    def lines(self):
        self.srv.gw.diary.flush()
        out = []
        for f in (self.diary / "raw").glob("*.jsonl"):
            out += [json.loads(x) for x in f.read_text().splitlines()]
        return out


MSGS = [{"role": "system", "content": "You are helpful."},
        {"role": "user", "content": [{"type": "text", "text": "Where is the pineapple?"}]}]


class TestGateway(Base):
    def test_models_lists_four(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/v1/models")
        ids = [m["id"] for m in json.loads(c.getresponse().read())["data"]]
        self.assertEqual(ids, ["qwen36-auto", "qwen36", "qwen36-fast", "k2-helper"])

    def test_health_passthrough(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/health")
        self.assertEqual(json.loads(c.getresponse().read()), {"status": "ok"})

    def test_plain_request_rewrites(self):
        body = {"model": "qwen36-fast", "messages": MSGS, "reasoning_effort": "high",
                "chat_template_kwargs": {"foo": 1}, "tools": [{"type": "function", "function": {"name": "bash"}}]}
        _, r = self.post(body)
        out = json.loads(r.read())
        up = self.big.requests[-1]
        self.assertEqual(up["model"], "default_model")
        self.assertEqual(up["chat_template_kwargs"], {"foo": 1, "enable_thinking": False})
        self.assertNotIn("reasoning_effort", up)
        self.assertEqual(up["max_tokens"], 8192)
        self.assertEqual(up["messages"], MSGS)
        self.assertEqual(up["tools"], body["tools"])
        m = out["choices"][0]["message"]
        self.assertEqual(m["reasoning_content"], "hmm")
        self.assertNotIn("reasoning", m)
        self.assertEqual(out["model"], "qwen36-fast")
        self.assertEqual(out["usage"]["prompt_tokens_details"]["cached_tokens"], 64)

    def test_thinking_on_and_unknown_model(self):
        self.post({"model": "gpt-4o", "messages": MSGS, "max_tokens": 50})[1].read()
        up = self.big.requests[-1]
        self.assertTrue(up["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(up["max_tokens"], 50)

    def test_small_routing(self):
        self.post({"model": "k2-helper", "messages": MSGS})[1].read()
        self.assertEqual(len(self.small.requests), 1)
        self.assertEqual(self.small.requests[0]["max_tokens"], 2048)
        self.assertNotIn("chat_template_kwargs", self.small.requests[0])

    def test_stream_incremental_and_diary(self):
        self.big.gate.clear()
        c, r = self.post({"model": "qwen36", "messages": MSGS, "stream": True,
                          "stream_options": {"include_usage": True}})
        first = r.readline()  # arrives while upstream is still blocked on the gate
        self.assertTrue(first.startswith(b"data: "))
        self.assertFalse(self.big.gate.is_set())
        self.big.gate.set()
        rest = r.read().decode()
        raw = first.decode() + rest
        self.assertIn("data: [DONE]", raw)
        self.assertNotIn('"reasoning":', raw)
        chunks = [json.loads(l[6:]) for l in raw.splitlines() if l.startswith("data: {")]
        self.assertTrue(all(ch["model"] == "qwen36" for ch in chunks))
        self.assertEqual(chunks[0]["choices"][0]["delta"]["reasoning_content"], "think ")
        self.assertEqual(self.big.requests[-1]["stream_options"], {"include_usage": True})
        rec = self.lines()[-1]
        self.assertEqual(rec["response"]["content"], "Hello")
        self.assertEqual(rec["response"]["reasoning"], "think more")
        tc = rec["response"]["tool_calls"][0]
        self.assertEqual((tc["id"], tc["function"]["name"], tc["function"]["arguments"]),
                         ("c1", "bash", '{"cmd": "ls"}'))
        self.assertEqual(rec["finish_reason"], "tool_calls")
        self.assertEqual(rec["usage"]["prompt_tokens_details"]["cached_tokens"], 64)
        self.assertIsNotNone(rec["ttft_s"])

    def test_diary_blobs_and_sqlite(self):
        tools = [{"type": "function", "function": {"name": "bash"}}]
        self.post({"model": "qwen36", "messages": MSGS, "tools": tools})[1].read()
        self.post({"model": "qwen36", "messages": MSGS, "tools": tools})[1].read()
        recs = self.lines()
        self.assertEqual(len(recs), 2)
        self.assertEqual(len(recs[0]["conv_id"]), 16)
        blob = self.diary / "raw" / "blobs" / (recs[0]["tools_hash"] + ".json")
        self.assertEqual(json.loads(blob.read_text()), tools)
        sysblob = recs[0]["messages"][0]["content"]["$blob"]
        self.assertEqual(json.loads((self.diary / "raw/blobs" / (sysblob + ".json")).read_text()),
                         "You are helpful.")
        self.assertEqual(len(list((self.diary / "raw/blobs").glob("*.json"))), 2)  # deduplicated
        import sqlite3
        db = sqlite3.connect(self.diary / "diary.sqlite")
        rows = db.execute("SELECT title, text FROM turns WHERE turns MATCH 'pineapple'").fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "Where is the pineapple?")
        self.assertNotIn("hmm", rows[0][1])  # reasoning not indexed

    def test_mcp_tools(self):
        self.post({"model": "qwen36", "messages": MSGS})[1].read()
        self.srv.gw.diary.flush()
        env = dict(os.environ, DIARY_DIR=self.tmp.name)
        reqs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "diary_search", "arguments": {"query": 'pineapple?! "x'}}},
            {"jsonrpc": "2.0", "id": 4, "method": "foo/bar"},
            {"jsonrpc": "2.0", "id": 5, "method": "ping"},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
             "params": {"name": "diary_days", "arguments": {}}},
        ]
        p = subprocess.run([sys.executable, str(HERE.parent / "diary_mcp.py")], env=env, text=True,
                           input="\n".join(json.dumps(r) for r in reqs) + "\nnot json\n",
                           capture_output=True, timeout=20)
        out = [json.loads(l) for l in p.stdout.splitlines()]
        by = {o["id"]: o for o in out}
        self.assertEqual(len(out), 7)  # no reply to the notification, one parse error
        self.assertEqual(by[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual([t["name"] for t in by[2]["result"]["tools"]],
                         ["diary_search", "diary_read", "diary_days"])
        hit = by[3]["result"]["content"][0]["text"]
        self.assertIn("pineapple", hit)
        self.assertEqual(by[4]["error"]["code"], -32601)
        self.assertIn("1 conversation", by[6]["result"]["content"][0]["text"])
        cid = hit.split("conv_id=")[1].split()[0]
        sys.path.insert(0, str(HERE.parent))
        import diary_mcp
        diary_mcp.DIARY_DIR = Path(self.tmp.name)
        txt = diary_mcp.call_tool("diary_read", {"conv_id": cid})
        self.assertIn("Ben: Where is the pineapple?", txt)

    def test_mcp_empty_diary(self):
        import diary_mcp
        old = diary_mcp.DIARY_DIR
        diary_mcp.DIARY_DIR = Path(self.tmp.name) / "nope"
        try:
            self.assertIn("empty", diary_mcp.call_tool("diary_search", {"query": "x"}))
        finally:
            diary_mcp.DIARY_DIR = old


class TestAuto(Base):
    TOOLS = [{"type": "function", "function": {"name": "bash"}}]

    def auto(self, msgs, **kw):
        body = {"model": "qwen36-auto", "messages": msgs, "tools": self.TOOLS}
        body.update(kw)
        out = json.loads(self.post(body)[1].read())
        self.assertEqual(out["model"], "qwen36-auto")
        return self.big.requests[-1]

    def test_judge_zero_is_fast(self):
        self.big.judge_digit = 0
        up = self.auto(MSGS)
        self.assertIs(up["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual(up["model"], "default_model")
        self.assertEqual(len(self.big.judge_calls), 1)

    def test_judge_two_thinks(self):
        self.big.judge_digit = 2
        up = self.auto(MSGS)
        self.assertIs(up["chat_template_kwargs"]["enable_thinking"], True)

    def test_decision_reused_in_tool_loop(self):
        self.big.judge_digit = 0
        self.auto(MSGS)
        loop = MSGS + [{"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "done"}]
        self.big.judge_digit = 2  # would flip the answer if asked again
        up = self.auto(loop)
        self.assertIs(up["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual(len(self.big.judge_calls), 1)

    def test_judge_failure_thinks(self):
        self.big.judge_digit = None
        up = self.auto(MSGS)
        self.assertIs(up["chat_template_kwargs"]["enable_thinking"], True)

    def test_judge_request_shape(self):
        self.auto(MSGS)
        j = self.big.judge_calls[0]
        self.assertEqual(j["messages"][:-1], MSGS)
        self.assertTrue(j["messages"][-1]["content"].startswith("(Internal check, not from Ben.)"))
        self.assertEqual(j["messages"][-1]["role"], "user")
        self.assertEqual(j["tools"], self.TOOLS)
        self.assertEqual(j["tool_choice"], "none")
        self.assertIs(j["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual((j["temperature"], j["max_tokens"], j["stream"]), (0, 2, False))

    def test_no_user_message_is_fast(self):
        up = self.auto([{"role": "system", "content": "x"}])
        self.assertIs(up["chat_template_kwargs"]["enable_thinking"], False)
        self.assertEqual(self.big.judge_calls, [])

    def test_diary_has_level_and_no_judge_turn(self):
        self.big.judge_digit = 2
        self.auto(MSGS)
        for _ in range(50):  # the diary entry is queued just after the reply is sent
            recs = self.lines()
            if recs:
                break
            time.sleep(0.1)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["auto_level"], 2)
        self.assertIsNotNone(recs[0]["judge_s"])
        self.assertEqual(recs[0]["model"], "qwen36-auto")

    def test_lru_bounded(self):
        gw = self.srv.gw
        for i in range(gateway.AUTO_CACHE_MAX + 5):
            gw.auto_put(str(i), 1)
        self.assertEqual(len(gw._auto), gateway.AUTO_CACHE_MAX)
        self.assertIsNone(gw.auto_get("0"))


class TestSmallDown(Base):
    small_up = False

    def test_hidden_and_fallback(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/v1/models")
        ids = [m["id"] for m in json.loads(c.getresponse().read())["data"]]
        self.assertEqual(ids, ["qwen36-auto", "qwen36", "qwen36-fast"])
        self.post({"model": "k2-helper", "messages": MSGS})[1].read()
        up = self.big.requests[-1]
        self.assertFalse(up["chat_template_kwargs"]["enable_thinking"])


class TestBigDown(Base):
    def test_503(self):
        self.big.shutdown()
        self.big.server_close()
        _, r = self.post({"model": "qwen36", "messages": MSGS})
        self.assertEqual(r.status, 503)
        self.assertIn("Start Assistant", json.loads(r.read())["error"]["message"])
        self.big = None


class PrepareTest(unittest.TestCase):
    def test_fast_and_thinking_share_system_prompt(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import gateway
        a = gateway.prepare({"messages": [{"role": "system", "content": "I am qwen36-auto."}]}, True, 1)
        self.assertEqual(a["messages"][0]["content"], "I am qwen36.")
        msgs = [{"role": "system", "content": "You are model premonition/qwen36-fast."},
                {"role": "user", "content": "hi qwen36-fast"}]
        fast = gateway.prepare({"messages": msgs}, False, 100)
        think = gateway.prepare({"messages": [dict(m) for m in msgs]}, True, 100)
        self.assertEqual(fast["messages"][0]["content"], "You are model premonition/qwen36.")
        self.assertEqual(fast["messages"], think["messages"][:1] + fast["messages"][1:])
        self.assertEqual(fast["messages"][1]["content"], "hi qwen36-fast")  # user text untouched
        self.assertEqual(msgs[0]["content"], "You are model premonition/qwen36-fast.")  # input not mutated

    def test_skills_listing_stripped(self):
        import gateway
        sysmsg = ("Intro.\nSkills provide specialized instructions and workflows for specific tasks.\n"
                  "Use the skill tool to load a skill when a task matches its description.\n"
                  "<available_skills>\n  <skill>\n    <name>x</name>\n  </skill>\n</available_skills>\nOutro.")
        msgs = [{"role": "system", "content": sysmsg},
                {"role": "user", "content": "<available_skills>keep</available_skills>"}]
        out = gateway.prepare({"messages": msgs}, None, 1)["messages"]
        self.assertEqual(out[0]["content"], "Intro.\nOutro.")
        self.assertEqual(out[1], msgs[1])  # user text untouched
        self.assertIn("<available_skills>", msgs[0]["content"])  # input not mutated

    def test_request_sizes(self):
        import gateway
        b = {"messages": [{"role": "system", "content": "abcd"}, {"role": "user", "content": "xy"},
                          {"role": "user", "content": [{"type": "text", "text": "z"}]}], "tools": []}
        self.assertTrue(gateway.request_sizes(b).startswith("system=4 user=%d tools=2" % (2 + len(json.dumps(b["messages"][2]["content"])))))


if __name__ == "__main__":
    unittest.main()
