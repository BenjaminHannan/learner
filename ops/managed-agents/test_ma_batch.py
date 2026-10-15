"""Tests for the Message Batches path in ma.py. Run from the repo root:
python3 -m unittest ops/managed-agents/test_ma_batch.py"""
import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anthropic  # noqa: E402
import ma  # noqa: E402

REAL_CLIENT = ma.client

try:  # the anthropic SDK's HTTP library is httpx2 in 1.13, httpx in older releases
    import httpx2 as httpx
except ImportError:
    import httpx

NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)  # real time: `cost --days 1` windows on the real clock


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
        self.archived, self.results_error, self.retrieve_errors = False, None, []

    def create(self, requests):
        self.created = requests
        return NS(id="msgbatch_1", created_at=NOW)

    def retrieve(self, batch_id):
        if self.retrieve_errors:
            raise self.retrieve_errors.pop(0)
        rc = NS(processing=0, succeeded=1, errored=0, canceled=0, expired=0)
        return NS(id=batch_id, processing_status=self.status, request_counts=rc, created_at=NOW, ended_at=NOW,
                  archived_at=NOW if self.archived else None)

    def results(self, batch_id):
        if self.results_error:
            raise self.results_error
        return iter(self._results)

    def list(self, limit=None):
        return iter([self.retrieve("msgbatch_1")])


class FakeClient:
    def __init__(self, tokens=1000, results=(), status="ended"):
        self.batches = FakeBatches(tokens, results, status)
        self.count_calls, self.tokens_by_text = [], {}
        self.messages = NS(batches=self.batches, count_tokens=self.count_tokens)

    def count_tokens(self, **kw):
        self.count_calls.append(kw)
        text = kw["messages"][0]["content"]
        return NS(input_tokens=self.tokens_by_text.get(text, self.batches.tokens))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = FakeClient()
        for patcher in (mock.patch.object(ma, "client", lambda: self.fake),
                        mock.patch.object(ma, "IDS_PATH", self.tmp / "no-ids.json"),
                        mock.patch.object(ma, "default_out_dir", lambda: self.tmp / "default-out"),
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


    def test_mixed_cap_names_only_the_over_cap_prompt(self):
        self.fake.tokens_by_text = {"BIG": 1_000_000}
        code, text = self.run_ma("batch", "submit", self.write("small.md", "tiny"), self.write("big.md", "BIG"),
                                 "--model", "opus", "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 1)
        self.assertIsNone(self.fake.batches.created)
        self.assertIn("REFUSED big", text)
        self.assertNotIn("REFUSED small", text)
        self.assertIn("--max-tokens", text)  # batch submit has that flag

    def test_whole_batch_ceiling(self):
        # opus, 1000 tokens, 32000 out: 0.5*(1000*5 + 32000*20)/1e6 = $0.3225 each, under the $1 request cap
        paths = [self.write(f"p{i}.md", f"t{i}") for i in range(3)]
        code, text = self.run_ma("batch", "submit", *paths, "--model", "opus", "--max-total-cents", "80",
                                 "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 1)
        self.assertIsNone(self.fake.batches.created)
        self.assertIn("--max-total-cents", text)
        self.assertFalse((self.tmp / "o").exists())
        code, _ = self.run_ma("batch", "submit", *paths, "--model", "opus", "--max-total-cents", "120",
                              "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 0)
        self.assertEqual(len(self.fake.batches.created), 3)

    def test_empty_prompt_refused_before_any_api_call(self):
        code, _ = self.run_ma("batch", "submit", self.write("p.md", "ok"), self.write("e.md", " \n"),
                              "--out-dir", str(self.tmp / "o"))
        self.assertIn("e.md is empty; nothing to send", str(code))
        self.assertEqual(self.fake.count_calls, [])
        self.assertIsNone(self.fake.batches.created)

    def test_body_size_limit(self):
        with mock.patch.object(ma, "MAX_BODY_BYTES", 100):
            code, text = self.run_ma("batch", "submit", self.write("p.md", "x" * 500),
                                     "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 1)
        self.assertIsNone(self.fake.batches.created)
        self.assertIn("split the prompts or shorten the attachments", text.lower())

    def test_unusable_out_dir_stops_before_create(self):
        blocker = self.write("file.txt")
        code, _ = self.run_ma("batch", "submit", self.write("p.md"), "--out-dir", blocker + "/sub")
        self.assertIn("Nothing submitted", str(code))
        self.assertIsNone(self.fake.batches.created)

    def test_manifest_failure_still_prints_id_and_command(self):
        out = self.tmp / "o"
        (out / "batch-msgbatch_1.json").mkdir(parents=True)  # writing the manifest will fail
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--out-dir", str(out))
        self.assertEqual(code, 0)
        self.assertIn("BATCH msgbatch_1", text)
        self.assertIn("WARNING: could not write the manifest", text)
        self.assertIn("batch collect msgbatch_1", text)

    def test_missing_api_key(self):
        with mock.patch.object(ma, "client", REAL_CLIENT), \
                mock.patch.dict(os.environ, clear=False) as env:
            env.pop("LEARNER_ANTHROPIC_API_KEY", None)
            code, _ = self.run_ma("batch", "submit", self.write("p.md"))
        self.assertIn("LEARNER_ANTHROPIC_API_KEY is not set", str(code))

    def test_poll_loop_survives_connection_error(self):
        err = anthropic.APIConnectionError(request=httpx.Request("GET", "http://x"))
        self.fake.batches.retrieve_errors = [err]
        self.fake.batches._results = [ok("p", text="hi")]
        out = self.tmp / "o"
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--wait", "--out-dir", str(out))
        self.assertEqual(code, 0)
        self.assertIn("will retry", text)
        self.assertEqual((out / "p.md").read_text(), "hi\n")

    def test_poll_loop_does_not_retry_auth_error(self):
        req = httpx.Request("GET", "http://x")
        err = anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None)
        self.fake.batches.retrieve_errors = [err]
        with self.assertRaises(anthropic.AuthenticationError):
            self.run_ma("batch", "submit", self.write("p.md"), "--wait", "--out-dir", str(self.tmp / "o"))

    def test_poll_loop_retries_server_error(self):
        req = httpx.Request("GET", "http://x")
        err = anthropic.InternalServerError("boom", response=httpx.Response(500, request=req), body=None)
        self.fake.batches.retrieve_errors = [err]
        self.fake.batches._results = [ok("p", text="hi")]
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--wait", "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 0)
        self.assertIn("will retry", text)

    def test_poll_loop_timeout_with_errors_prints_command(self):
        err = anthropic.APIConnectionError(request=httpx.Request("GET", "http://x"))
        self.fake.batches.retrieve_errors = [err] * 5
        code, text = self.run_ma("batch", "submit", self.write("p.md"), "--wait", "--minutes", "0",
                                 "--out-dir", str(self.tmp / "o"))
        self.assertEqual(code, 0)
        self.assertIn("Collect later with: python3 ops/managed-agents/ma.py batch collect msgbatch_1", text)


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

    def test_missing_manifest_warns(self):
        self.fake.batches._results = [ok("a", text="A")]
        out = self.tmp / "o"
        code, text = self.run_ma("batch", "collect", "msgbatch_1", "--out-dir", str(out))
        self.assertEqual(code, 0)
        self.assertIn(f"No manifest at {out / 'batch-msgbatch_1.json'}: writing to {out}", text)
        self.assertIn("review --out was not applied", text)
        self.assertEqual((out / "a.md").read_text(), "A\n")

    def test_unknown_model_falls_back_to_manifest_model(self):
        self.fake.batches._results = [ok("a", model="claude-mystery-9", usage=(1000, 2000, 0, 0))]
        out = self.tmp / "o"
        out.mkdir()
        (out / "batch-msgbatch_1.json").write_text(json.dumps({"id": "msgbatch_1", "model": "claude-haiku-5-5",
                                                                "requests": {}}))
        _, text = self.run_ma("batch", "collect", "msgbatch_1", "--out-dir", str(out))
        self.assertIn("($0.0006)", text)  # 0.5*(1000*0.1 + 2000*0.5)/1e6 = 0.00055
        self.assertNotIn("WARNING", text)

    def test_unknown_model_without_manifest_is_unpriced(self):
        self.fake.batches._results = [ok("a", model="claude-mystery-9")]
        _, text = self.run_ma("batch", "collect", "msgbatch_1", "--out-dir", str(self.tmp / "o"))
        self.assertIn("WARNING a: unknown model 'claude-mystery-9'", text)
        self.assertIn("total actual cost $0.0000 (batch price), 1 result(s) with an unknown model not priced", text)

    def test_cost_counts_expired_results(self):
        self.fake.batches.archived = True
        self.fake.batches.results_error = anthropic.AnthropicError("results expired")
        code, text = self.run_ma("cost", "--days", "1")
        self.assertEqual(code, 0)
        self.assertIn("batches: 1 created, $0.00 actual", text)
        self.assertIn("1 with results expired", text)

    def test_cost_results_error_without_archived_at(self):
        self.fake.batches.results_error = anthropic.AnthropicError("no results_url")
        code, text = self.run_ma("cost", "--days", "1")
        self.assertEqual(code, 0)
        self.assertIn("1 with results expired", text)

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

    def test_batch_system_text_has_no_repo_paths(self):
        self.run_ma("review", self.write("prompt.md", "Q?"), "--no-wait")
        text = self.fake.batches.created[0]["params"]["system"][0]["text"]
        self.assertNotIn("/workspace", text)
        self.assertNotIn("/mnt/session", text)
        self.assertIn("NO repository", text)
        self.assertIn("Check every factual claim", text)

    def test_out_is_stored_absolute_and_no_wait_prints_command(self):
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, os.getcwd())
        _, text = self.run_ma("review", self.write("prompt.md", "Q?"), "--no-wait", "--out", "rel/answer.md")
        manifest = json.loads((self.tmp / "default-out" / "batch-msgbatch_1.json").read_text())
        self.assertEqual(manifest["requests"]["prompt"]["out"], str((self.tmp / "rel" / "answer.md").resolve()))
        self.assertIn("batch collect msgbatch_1", text)

    def test_review_cap_hint_has_no_max_tokens_flag(self):
        self.fake.batches.tokens = 2_000_000
        code, text = self.run_ma("review", self.write("prompt.md", "Q?"), "--no-wait")
        self.assertEqual(code, 1)
        self.assertIn("REFUSED", text)
        self.assertNotIn("--max-tokens", text)

    def test_empty_prompt_refused(self):
        code, _ = self.run_ma("review", self.write("prompt.md", ""))
        self.assertIn("prompt.md is empty; nothing to send", str(code))
        self.assertIsNone(self.fake.batches.created)

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
