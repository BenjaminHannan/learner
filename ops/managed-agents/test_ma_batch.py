"""Tests for the Message Batches path in ma.py. Run from the repo root:
python3 -m unittest ops/managed-agents/test_ma_batch.py"""
import contextlib
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ma  # noqa: E402

NOW = dt.datetime(2026, 10, 11, 12, 0, tzinfo=dt.timezone.utc)


def msg(text="answer", stop="end_turn", model="claude-haiku-5-5", usage=(1000, 2000, 0, 0), blocks=None):
    inp, out, cw, cr = usage
    content = blocks or [NS(type="text", text=text)]
    u = NS(input_tokens=inp, output_tokens=out, cache_creation_input_tokens=cw, cache_read_input_tokens=cr)
    return NS(content=content, stop_reason=stop, usage=u, model=model)


def ok(cid, **kw):
    return NS(custom_id=cid, result=NS(type="succeeded", message=msg(**kw)))


class FakeBatches:
    def __init__(self, tokens, results=(), status="ended"):
        self.created, self.tokens, self._results, self.status = None, tokens, list(results), status

    def create(self, requests):
        self.created = requests
        return NS(id="msgbatch_1", created_at=NOW)

    def retrieve(self, batch_id):
        rc = NS(processing=0, succeeded=1, errored=0, canceled=0, expired=0)
        return NS(id=batch_id, processing_status=self.status, request_counts=rc, created_at=NOW, ended_at=NOW)

    def results(self, batch_id):
        return iter(self._results)

    def list(self, limit=None):
        return iter([self.retrieve("msgbatch_1")])


class FakeClient:
    def __init__(self, tokens=1000, results=(), status="ended"):
        self.batches = FakeBatches(tokens, results, status)
        self.count_calls = []
        self.messages = NS(batches=self.batches, count_tokens=self.count_tokens)

    def count_tokens(self, **kw):
        self.count_calls.append(kw)
        return NS(input_tokens=self.batches.tokens)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = FakeClient()
        for patcher in (mock.patch.object(ma, "client", lambda: self.fake),
                        mock.patch.object(ma, "IDS_PATH", self.tmp / "no-ids.json"),
                        mock.patch.object(ma.time, "sleep", lambda s: None)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def write(self, name, text="hello"):
        path = self.tmp / name
        path.write_text(text)
        return str(path)

    def run_ma(self, *argv):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["ma.py", *argv]), contextlib.redirect_stdout(out):
            try:
                ma.main()
                code = 0
            except SystemExit as e:
                code = e.code
        return code, out.getvalue()


class TestHelpers(unittest.TestCase):
    def test_custom_ids_sanitise_and_dedupe(self):
        ids = ma.make_custom_ids(["my file.v2", "a", "a", "a"])
        self.assertEqual(ids, ["my-file-v2", "a", "a-2", "a-3"])

    def test_custom_ids_long(self):
        ids = ma.make_custom_ids(["x" * 100, "x" * 100])
        self.assertEqual(ids[0], "x" * 64)
        self.assertEqual(ids[1], "x" * 62 + "-2")
        self.assertTrue(all(len(i) <= 64 for i in ids))

    def test_cost_by_hand(self):
        # sonnet: 0.5*(1000*2 + 100*2*1.25 + 500*0.2 + 2000*10)/1e6 = 0.5*22350/1e6
        got = ma.batch_cost("claude-sonnet-5-5", 1000, 100, 500, 2000)
        self.assertAlmostEqual(got, 0.011175, places=9)

    def test_haiku_long_prompt_pricing(self):
        short = ma.batch_cost("claude-haiku-5-5", 100_000, 0, 0, 1000)  # not over 100K
        self.assertAlmostEqual(short, 0.5 * (100_000 * 0.10 + 1000 * 0.50) / 1e6)
        long_ = ma.batch_cost("claude-haiku-5-5", 60_000, 30_000, 20_000, 1000)  # total 110K
        self.assertAlmostEqual(long_, 0.5 * (60_000 * 0.5 + 30_000 * 0.5 * 1.25 + 20_000 * 0.05 + 1000 * 2.5) / 1e6)

    def test_unknown_model_rejected(self):
        with self.assertRaises(SystemExit):
            ma.model_id("gpt-9")
        self.assertEqual(ma.model_id("opus"), "claude-opus-5-5")
        self.assertEqual(ma.model_id("claude-fable-5-1"), "claude-fable-5-1")


class TestSubmit(Base):
    def test_params_attachments_manifest(self):
        p1, p2 = self.write("q one.md", "Q1"), self.write("q one.txt", "Q2")
        data = self.write("data.txt", "x" * 50000 + "END")
        out = self.tmp / "out"
        code, text = self.run_ma("batch", "submit", p1, p2, "--model", "sonnet", "--effort", "high",
                                 "--attach", data, "--out-dir", str(out))
        self.assertEqual(code, 0)
        reqs = self.fake.batches.created
        self.assertEqual([r["custom_id"] for r in reqs], ["q-one", "q-one-2"])
        params = reqs[0]["params"]
        self.assertEqual(params["model"], "claude-sonnet-5-5")
        self.assertEqual(params["output_config"], {"effort": "high"})
        self.assertEqual(params["max_tokens"], 32000)
        self.assertNotIn("thinking", params)
        block = params["system"][0]
        self.assertEqual(block["cache_control"], {"type": "ephemeral"})
        self.assertTrue(block["text"].startswith(f'<file path="{data}">'))
        self.assertIn("x" * 50000 + "END", block["text"])
        manifest = json.loads((out / "batch-msgbatch_1.json").read_text())
        self.assertEqual(manifest["model"], "claude-sonnet-5-5")
        self.assertEqual(manifest["requests"]["q-one-2"]["prompt"], p2)
        self.assertEqual(manifest["requests"]["q-one"]["out"], str(out / "q-one.md"))
        self.assertIn("batch collect msgbatch_1", text)
        self.assertEqual(len(self.fake.count_calls), 2)

    def test_system_file_before_attachments_and_none(self):
        sysf, data = self.write("s.md", "be brief"), self.write("d.txt", "D")
        self.run_ma("batch", "submit", self.write("p.md"), "--system", sysf, "--attach", data,
                    "--out-dir", str(self.tmp / "o"))
        system = self.fake.batches.created[0]["params"]["system"]
        self.assertEqual(system[0], {"type": "text", "text": "be brief"})
        self.assertIn("cache_control", system[1])
        self.fake.batches.created = None
        self.run_ma("batch", "submit", self.write("p2.md"), "--out-dir", str(self.tmp / "o"))
        self.assertNotIn("system", self.fake.batches.created[0]["params"])

    def test_bad_utf8_attachment(self):
        bad = self.tmp / "bad.bin"
        bad.write_bytes(b"\xff\xfe\x00")
        code, _ = self.run_ma("batch", "submit", self.write("p.md"), "--attach", str(bad),
                              "--out-dir", str(self.tmp / "o"))
        self.assertIn("bad.bin", str(code))
        self.assertIsNone(self.fake.batches.created)

    def test_cap_refusal_submits_nothing(self):
        self.fake.batches.tokens = 1_000_000
        # opus: 0.5*(1e6*4*1.25 + 32000*20)/1e6 = $2.82 > $1
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--model", "opus",
                                 "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 1)
        self.assertIsNone(self.fake.batches.created)
        self.assertIn("REFUSED p", text)
        self.assertFalse((self.tmp / "o").exists())

    def test_wait_collects(self):
        self.fake.batches._results = [ok("p", text="hi")]
        out = self.tmp / "o"
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--wait", "--out-dir", str(out))
        self.assertEqual(code, 0)
        self.assertEqual((out / "p.md").read_text(), "hi\n")

    def test_wait_timeout_exits_zero(self):
        self.fake.batches.status = "in_progress"
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--wait", "--minutes", "0",
                                 "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 0)
        self.assertIn("batch collect msgbatch_1", text)


class TestCollect(Base):
    def test_collect(self):
        think = NS(type="thinking", thinking="secret")
        self.fake.batches._results = [
            ok("b", text="B", stop="refusal"),
            NS(custom_id="c", result=NS(type="errored", error=NS(type="error", error=NS(type="overloaded_error")))),
            ok("a", blocks=[think, NS(type="text", text="A1"), NS(type="text", text="A2")],
               stop="max_tokens", usage=(1_000_000, 100_000, 0, 0)),
            NS(custom_id="d", result=NS(type="expired")),
        ]
        out = self.tmp / "o"
        out.mkdir()
        manifest = {"id": "msgbatch_1", "requests": {"a": {"prompt": "x", "out": str(self.tmp / "custom.md")}}}
        (out / "batch-msgbatch_1.json").write_text(json.dumps(manifest))
        code, text = self.run_ma("batch", "collect", "msgbatch_1", "--out-dir", str(out))
        self.assertEqual(code, 0)
        self.assertEqual((self.tmp / "custom.md").read_text(), "A1A2\n")  # no thinking, manifest path
        self.assertEqual((out / "b.md").read_text(), "B\n")
        self.assertIn("WARNING a: stopped with max_tokens", text)
        self.assertIn("WARNING b: stopped with refusal", text)
        self.assertIn("c: errored (overloaded_error)", text)
        self.assertIn("d: expired", text)
        # a: haiku, 1.1M input -> long prices: 0.5*(1e6*0.5 + 1e5*2.5)/1e6 = 0.375; b: 0.5*(1000*0.1+2000*0.5)/1e6
        self.assertIn("a: " + str(self.tmp / "custom.md") + "  ($0.3750)", text)
        updated = json.loads((out / "batch-msgbatch_1.json").read_text())
        self.assertAlmostEqual(updated["cost_cents"], (0.375 + 0.00055) * 100, places=3)
        self.assertIn("collected", updated)
        code, _ = self.run_ma("batch", "collect", "msgbatch_1", "--out-dir", str(out))  # rerun is safe
        self.assertEqual(code, 0)

    def test_not_ended_writes_nothing(self):
        self.fake.batches._results = [ok("a")]
        self.fake.batches.status = "in_progress"
        out = self.tmp / "o"
        code, text = self.run_ma("batch", "collect", "msgbatch_1", "--out-dir", str(out))
        self.assertEqual(code, 0)
        self.assertIn("in_progress", text)
        self.assertFalse(out.exists())

    def test_status_and_cost(self):
        self.fake.batches._results = [ok("a")]
        code, text = self.run_ma("batch", "status", "msgbatch_1")
        self.assertIn("ended", text)
        code, text = self.run_ma("batch", "status")
        self.assertIn("msgbatch_1", text)
        code, text = self.run_ma("cost", "--days", "1")
        self.assertIn("batches: 1 created", text)


class TestReview(Base):
    def test_default_uses_batches(self):
        att = self.write("r.json", '{"a": 1}')
        out = self.tmp / "answer.md"
        self.fake.batches._results = [ok("prompt", text="review!")]
        code, text = self.run_ma("review", self.write("prompt.md", "Q?"), "--attach", att, "--out", str(out),
                                 "--wait-min", "1")
        self.assertEqual(code, 0)
        params = self.fake.batches.created[0]["params"]
        self.assertEqual((params["model"], params["max_tokens"]), ("claude-opus-5-5", 64000))
        self.assertEqual(params["output_config"], {"effort": "xhigh"})
        self.assertEqual(params["messages"][0]["content"], "Q?")
        self.assertIn("NO repository", params["system"][0]["text"])
        self.assertIn("outside reviewer", params["system"][0]["text"])
        self.assertIn("cache_control", params["system"][1])
        self.assertEqual(out.read_text(), "review!\n")

    def test_repo_flag_uses_session_path(self):
        with mock.patch.object(ma, "cmd_review_repo", return_value=0) as old:
            code, _ = self.run_ma("review", self.write("prompt.md"), "--repo")
        self.assertEqual(code, 0)
        old.assert_called_once()
        self.assertIsNone(self.fake.batches.created)

    def test_repo_path_needs_ids(self):
        code, _ = self.run_ma("review", self.write("prompt.md"), "--repo")
        self.assertIn("ids.json", str(code))


if __name__ == "__main__":
    unittest.main()
