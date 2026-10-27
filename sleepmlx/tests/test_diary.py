import json
import tempfile
import unittest
from pathlib import Path

from sleepmlx import diary

from .helpers import rec, write_raw


class DiaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dedupe_prefixes_keeps_newest_turn_per_call(self):
        write_raw(self.raw, "2026-10-20", ["first thing", "second thing", "third thing"])
        week = diary.build_week(self.raw)
        users = [t["text"] for t in week["diary"] if t["role"] == "user"]
        self.assertEqual(users, ["first thing", "second thing", "third thing"])
        asst = [t["text"] for t in week["diary"] if t["role"] == "assistant"]
        self.assertEqual(asst, ["Done 0.", "Done 1.", "Done 2."])

    def test_tool_loop_counts_once_and_uses_final_answer(self):
        hist = []
        calls = [
            rec("Book a table", "", conv="c", history=hist),
            rec("Book a table", "Booked for 7.", conv="c", history=[]),
        ]
        calls[0]["response"] = {"content": "", "tool_calls": [{"name": "search"}]}
        # second call: the newest message is a tool result, the user turn sits earlier
        calls[1]["messages"] = [{"role": "system", "content": "s"}, {"role": "user", "content": "Book a table"},
                                {"role": "assistant", "content": "", "tool_calls": [{}]}, {"role": "tool", "content": "RESULT"}]
        (self.raw / "2026-10-21.jsonl").write_text("\n".join(json.dumps(c) for c in calls))
        week = diary.build_week(self.raw)
        rows = week["diary"]
        self.assertEqual([r["role"] for r in rows], ["user", "assistant"])
        self.assertEqual(rows[1]["text"], "Booked for 7.")
        self.assertNotIn("RESULT", json.dumps(week))

    def test_blob_refs_and_helper_records(self):
        (self.raw / "blobs").mkdir()
        (self.raw / "blobs" / "abc123").write_text("Remember that Marta works at Orbix")
        (self.raw / "blobs" / "def456").write_text(json.dumps("It is noted."))
        r1 = rec("x")
        r1["messages"][-1]["content"] = {"$blob": "abc123"}
        r1["response"]["content"] = {"$blob": "def456"}
        r2 = rec("title this chat", model="k2-helper")
        (self.raw / "2026-10-22.jsonl").write_text(json.dumps(r1) + "\n" + json.dumps(r2) + "\n")
        week = diary.build_week(self.raw)
        self.assertEqual([t["text"] for t in week["diary"]], ["Remember that Marta works at Orbix", "It is noted."])

    def test_block_stripping(self):
        raw = ("[2026-10-27 14:03] [Background, not a request: the user is at home]\n"
               "Saved notes about Ben\n- likes tea\n- sister is Anna\n\n"
               "<memory>old stuff</memory>\nRemember that Marta works at Orbix")
        self.assertEqual(diary.strip_user(raw), "Remember that Marta works at Orbix")
        self.assertEqual(diary.strip_user("[Tue Oct 27 09:15] hello there"), "hello there")
        self.assertEqual(diary.strip_assistant("<think>hmm</think>Answer."), "Answer.")

    def test_redaction(self):
        t = diary.redact("my password is hunter22 and the code is 482913, card 4111 1111 1111 1111, ssn 123-45-6789")
        for secret in ("hunter22", "482913", "4111", "123-45-6789"):
            self.assertNotIn(secret, t)
        self.assertIn("[REDACTED]", t)
        # ordinary text and non-Luhn digit runs survive
        self.assertEqual(diary.redact("the code is clean; call me at 5551234"), "the code is clean; call me at 5551234")
        self.assertIn("1234567812345678", diary.redact("order 1234567812345678"))   # fails Luhn: not a card
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwx", diary.redact("key sk-abcdefghijklmnopqrstuvwx"))

    def test_week_json_valid_per_check_week(self):
        write_raw(self.raw, "2026-10-20", ["a b c"])
        write_raw(self.raw, "2026-10-21", ["d e f"])
        week = diary.build_week(self.raw)
        diary.check_week(week)
        self.assertEqual(week["dates"], {"1": "2026-10-20", "2": "2026-10-21"})
        self.assertEqual(week["items"], [])
        for k in diary.KINDS:
            self.assertEqual(week["tests"][k], [])
        self.assertTrue(all(t["role"] in ("user", "assistant") and "day" in t and "text" in t for t in week["diary"]))
        bad = dict(week, tests={k: [] for k in diary.KINDS[:-1]})
        with self.assertRaises(AssertionError):
            diary.check_week(bad)

    def test_ignore_list_and_test_mode_records(self):
        ign = self.raw / "ignore.txt"
        diary.ensure_ignore(ign)
        self.assertEqual([l for l in ign.read_text().splitlines() if not l.startswith("#")], diary.SEED_IGNORE)
        ign.write_text(ign.read_text() + "^zzz secret plan\\b\n")
        rows = [rec("Remember that Marta works at Orbix", "Noted."), rec("my teacher is Mr. Phipps", "ok"), rec("I like short answers", "ok"),
                rec("Please open example.com for me", "ok"), rec("Remember that I take the 7:40 bus", "ok"), rec("I'm in AP Chem 4th period today", "ok"),
                rec("zzz secret plan to start", "ok"), rec("typed by the e2e run", "ok"), rec("header test run", "ok"), rec("Tomas is the mentor of Lena", "Good.")]
        rows[7]["test"] = True
        rows[8]["request"] = {"headers": {"X-Test": "1"}}
        (self.raw / "2026-10-23.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
        week = diary.build_week(self.raw, ignore_file=ign)
        self.assertEqual([t["text"] for t in week["diary"]],
                         ["Remember that Marta works at Orbix", "Noted.", "Tomas is the mentor of Lena", "Good."])      # the ignored turns' answers are gone too
        # without an ignore file nothing but the test records is dropped
        self.assertEqual(len([t for t in diary.build_week(self.raw)["diary"] if t["role"] == "user"]), 8)

    def test_simple_app_format_splits_by_ts(self):
        # the Windows app's gateway: any file name, {ts, model, messages, response:{content}}
        rows = [{"ts": 1_700_000_000_000, "model": "lfm3", "messages": [{"role": "user", "content": "one"}], "response": {"content": "r1"}},
                {"ts": 1_700_000_000_000 + 3 * 86400 * 1000, "model": "lfm3", "messages": [{"role": "user", "content": "two"}], "response": {"content": "r2"}}]
        (self.raw / "gateway.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
        week = diary.build_week(self.raw)
        self.assertEqual(len(week["dates"]), 2)
        self.assertEqual([t["text"] for t in week["diary"] if t["role"] == "user"], ["one", "two"])


if __name__ == "__main__":
    unittest.main()


class SecretsAndStatusTest(unittest.TestCase):
    def test_gateway_status_ok_is_kept(self):
        from .helpers import rec
        r = rec("Marta works at Orbix"); r["status"] = "ok"
        self.assertIsNotNone(diary._record_turn(r, Path("/nonexistent")))
        r["status"] = 500
        self.assertIsNone(diary._record_turn(r, Path("/nonexistent")))

    def test_turns_about_credentials_are_dropped_whole(self):
        for t in ["hunter2 is my pass", "my password is x", "login with ben / secret1", "the verification code is 4411", "use this to sign in: abc"]:
            self.assertTrue(diary.talks_secrets(t), t)
        for t in ["Marta works at Orbix", "What are my upcoming assignments", "the passage was long", "a compass"]:
            self.assertFalse(diary.talks_secrets(t), t)
        with tempfile.TemporaryDirectory() as d:
            from .helpers import write_raw
            raw = Path(d) / "raw"
            write_raw(raw, "2026-10-21", ["Marta works at Orbix", "hunter2 is my pass for gmail"])
            week = diary.build_week(raw)
            text = json.dumps(week)
            self.assertIn("Orbix", text)
            self.assertNotIn("hunter2", text)
