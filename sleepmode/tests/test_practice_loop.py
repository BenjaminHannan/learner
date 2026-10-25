import json
import os
import tempfile
import time
import unittest

from sleepmode.practice import loop, research, tasks
from sleepmode.practice.model import ChatModel, FakeModel, tool_call_msg
from sleepmode.tools import ToolBox

try:
    from . import test_practice_tasks as T
except ImportError:
    import test_practice_tasks as T

GOOD = {"sum_by_group", "avg_by_group", "computed_column", "dedupe_key"}
RETRY = {"filter_rows", "join_lookup", "monthly_totals", "percent_change"}
SEED = 7


def make_fake(task_list):
    by_instr = {t.instruction: t for t in task_list}

    def fn(messages):
        user = messages[1]["content"]
        task = next(t for k, t in by_instr.items() if k in user)
        if task.family in GOOD:
            return "Here you go:\n```python\n%s\n```" % T.solution(task)
        if task.family in RETRY:
            code = T.solution(task, wrong=len(messages) == 2)
            return "```python\n%s```" % code
        return "I am not able to do this."
    return fn


def lines(path):
    with open(path) as f:
        return [json.loads(l) for l in f]


class ExtractTests(unittest.TestCase):
    def test_extract(self):
        self.assertEqual(loop.extract_code("x\n```python\nprint(1)\n```\ny"), "print(1)")
        self.assertEqual(loop.extract_code("```\nprint(2)\n```"), "print(2)")
        self.assertEqual(loop.extract_code("print(3)"), "print(3)")
        self.assertEqual(loop.extract_code("```python\ndef (:\n```\n```py\nprint(4)\n```"), "print(4)")
        self.assertIsNone(loop.extract_code("I cannot help with that"))
        self.assertIsNone(loop.extract_code(""))


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.tasks = tasks.generate("spreadsheet", 12, SEED)

    def test_round_outcomes(self):
        model = FakeModel(make_fake(self.tasks))
        cards = research.SEEDS["spreadsheet"]
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 300, out, seed=SEED, n_tasks=12, tricks=cards)
            self.assertEqual(s["n"], 12)
            self.assertAlmostEqual(s["pass1"], 4 / 12)
            self.assertAlmostEqual(s["pass_any"], 8 / 12)
            self.assertEqual((s["sft_n"], s["pairs_n"]), (7, 3))   # percent_change is held out
            self.assertGreaterEqual(s["tricks_used"], 10)
            sft = lines(s["sft_path"])
            pairs = lines(s["pairs_path"])
            rounds = lines(s["rounds_path"])
            self.assertEqual((len(sft), len(pairs), len(rounds)), (7, 3, 1))
            self.assertAlmostEqual(s["pass1_train"], 4 / 9)
            self.assertEqual((s["n_train"], s["n_heldout"], s["pass1_heldout"]), (9, 3, 0.0))
            self.assertIn("pass1_heldout", rounds[0])
            fams = {t.family for t in self.tasks if t.instruction in json.dumps(sft + pairs)}
            self.assertFalse(fams & set(loop.HELDOUT))
            for r in sft:
                self.assertEqual([m["role"] for m in r["messages"]], ["system", "user", "assistant"])
                self.assertNotIn("Hint (a trick", r["messages"][1]["content"])
                self.assertTrue(r["messages"][2]["content"].startswith("```python"))
            for p in pairs:
                self.assertNotIn("Hint (a trick", p["prompt"][1]["content"])
                self.assertNotEqual(p["chosen"], p["rejected"])
            for k in ("kind", "n", "pass1", "pass_any", "tricks_used", "elapsed_s"):
                self.assertIn(k, rounds[0])
            # the model was shown the hint on its first call
            self.assertTrue(any("Hint (a trick" in c[1]["content"] for c in model.calls))
            # retries carry feedback
            fb = [c for c in model.calls if len(c) == 4]
            self.assertTrue(any("output.csv is wrong" in c[3]["content"] for c in fb))
            self.assertTrue(any("no Python code block" in c[3]["content"] for c in fb))
            # garbage tasks used all 3 attempts, nothing recorded for them
            garbage = 4
            self.assertEqual(len(model.calls), 4 + 4 * 2 + garbage * 3)

    def test_heldout_configurable_and_never_all(self):
        model = FakeModel(make_fake(self.tasks))
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 300, out, seed=SEED, n_tasks=12, heldout_families=())
            self.assertEqual((s["sft_n"], s["pairs_n"], s["n_heldout"]), (8, 4, 0))
            self.assertIsNone(s["pass1_heldout"])
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 300, out, seed=SEED, n_tasks=12,
                               heldout_families=tasks.families("spreadsheet"))
            self.assertEqual(s["n_heldout"], 0)   # everything held out would leave nothing to train on

    def test_tools_note_says_inspect_input(self):
        self.assertIn("Inspect the input first", loop.TOOLS_NOTE)

    def test_pairs_replay_in_sandbox(self):
        model = FakeModel(make_fake(self.tasks))
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 300, out, seed=SEED, n_tasks=12)
            by_instr = {t.instruction: t for t in self.tasks}
            for p in lines(s["pairs_path"]):
                t = next(t for k, t in by_instr.items() if k in p["prompt"][1]["content"])
                ok, _ = T.run_check(t, loop.extract_code(p["chosen"]))
                bad, _ = T.run_check(t, loop.extract_code(p["rejected"]))
                self.assertTrue(ok)
                self.assertFalse(bad)

    def test_budget_stop(self):
        model = FakeModel(lambda m: "no")
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 0, out, seed=1, n_tasks=12)
            self.assertEqual(s["n"], 0)
            self.assertTrue(s["stopped_early"])
            self.assertEqual(model.calls, [])
            slow = FakeModel(lambda m: time.sleep(0.3) or "no")
            s = loop.run_round("spreadsheet", slow, 0.5, out, seed=1, n_tasks=12, retries=0)
            self.assertTrue(0 < s["n"] < 12)

    def test_model_errors_abort(self):
        def boom(m):
            raise OSError("server down")
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", FakeModel(boom), 60, out, seed=1, n_tasks=12)
            self.assertEqual(s["n"], 0)
            self.assertEqual(s["model_errors"], 3)

    def test_make_practice_fn(self):
        model = FakeModel(make_fake(tasks.generate("spreadsheet", 12, SEED)))
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as diary:
            fn = loop.make_practice_fn(home, diary, model, n_tasks=12, seed=SEED, research_web=False)
            self.assertIsNone(fn(60))  # empty diary: nothing practicable
            os.makedirs(os.path.join(diary, "raw"))
            with open(os.path.join(diary, "raw", "d.jsonl"), "w") as f:
                for q in ("sum column B in my excel spreadsheet", "pivot this csv", "write a poem"):
                    f.write(json.dumps({"messages": [{"role": "user", "content": q}]}) + "\n")
            s = fn(120)
            self.assertEqual(s["kind"], "spreadsheet")
            self.assertEqual(s["n"], 12)
            self.assertTrue(s["sft_path"].startswith(os.path.join(home, "practice")))
            self.assertTrue(os.path.exists(s["pairs_path"]) and os.path.exists(s["rounds_path"]))


class ToolRoundTests(unittest.TestCase):
    def test_tools_used_but_checker_decides(self):
        ts = tasks.generate("spreadsheet", 4, SEED)
        by_instr = {t.instruction: t for t in ts}

        def fn(messages):
            task = next(t for k, t in by_instr.items() if k in messages[1]["content"])
            if messages[-1]["role"] == "tool":
                # tool saw the task files; answer: the right script for even tasks, a wrong one for odd
                self.assertIn("exit: 0", messages[-1]["content"])
                wrong = ts.index(task) % 2 == 1
                return "```python\n%s```" % T.solution(task, wrong=wrong)
            if messages[-1]["role"] == "user" and messages[-1]["content"].startswith("RESULT"):
                return "```python\n%s```" % T.solution(task)
            first = sorted(task.files)[0]
            return tool_call_msg("python", {"code": "print(len(open(%r).read()))" % first})
        model = FakeModel(fn)
        tb = ToolBox("", web=False)
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 300, out, seed=SEED, n_tasks=4, toolbox=tb, retries=0)
            self.assertTrue(s["tools"])
            self.assertEqual(s["tool_calls"], {"python": 4})
            self.assertEqual(s["tool_calls_total"], 4)
            self.assertEqual(s["pass_any"], 0.5)  # wrong scripts fail even though tools ran
            rounds = lines(s["rounds_path"])
            self.assertEqual(rounds[0]["tool_calls"], {"python": 4})
            for r in lines(s["sft_path"]):
                self.assertEqual([m["role"] for m in r["messages"]], ["system", "user", "assistant"])
                self.assertNotIn("TOOL", json.dumps(r))
                self.assertNotIn("python to test", r["messages"][0]["content"])
        # use_tools=False ignores the toolbox
        model = FakeModel(make_fake(ts))
        with tempfile.TemporaryDirectory() as out:
            s = loop.run_round("spreadsheet", model, 300, out, seed=SEED, n_tasks=4, toolbox=tb, use_tools=False)
            self.assertEqual(s["tool_calls_total"], 0)
            self.assertFalse(s["tools"])

    def test_make_practice_fn_tools_flag(self):
        model = FakeModel(make_fake(tasks.generate("spreadsheet", 3, SEED)))
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as diary:
            os.makedirs(os.path.join(diary, "raw"))
            with open(os.path.join(diary, "raw", "d.jsonl"), "w") as f:
                f.write(json.dumps({"messages": [{"role": "user", "content": "sum column B in my excel spreadsheet csv"}]}) + "\n")
            s = loop.make_practice_fn(home, diary, model, n_tasks=3, seed=SEED, research_web=False)(60)
            self.assertTrue(s["tools"])
            s = loop.make_practice_fn(home, diary, model, n_tasks=3, seed=SEED, research_web=False, tools=False)(60)
            self.assertFalse(s["tools"])


class ChatModelTests(unittest.TestCase):
    def test_endpoint_and_retry(self):
        import http.server
        import threading
        hits = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                hits.append(self.path)
                if len(hits) == 1:
                    self.send_response(500)
                    self.end_headers()
                    return
                body = json.dumps({"choices": [{"message": {"content": "<think>x</think>hi"}}]}).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            m = ChatModel("http://127.0.0.1:%d" % srv.server_port, "m", timeout=5)
            self.assertEqual(m.chat([{"role": "user", "content": "x"}]), "hi")
            self.assertEqual(hits, ["/v1/chat/completions"] * 2)
        finally:
            srv.shutdown()

    def test_chat_tools(self):
        import http.server
        import threading
        bodies = []

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                msg = {"content": None, "tool_calls": [{"id": "x", "type": "function",
                                                        "function": {"name": "python", "arguments": "{}"}}]}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": msg}]}).encode())

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            m = ChatModel("http://127.0.0.1:%d/v1" % srv.server_port, "m", timeout=5)
            r = m.chat_tools([{"role": "user", "content": "x"}], ToolBox("").schemas())
            self.assertEqual(r["tool_calls"][0]["function"]["name"], "python")
            self.assertEqual(r["content"], "")
            self.assertIn("tools", bodies[0])
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
