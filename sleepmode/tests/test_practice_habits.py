import json
import os
import tempfile
import unittest

from sleepmode.practice import habits


def write_diary(d, lines):
    os.makedirs(os.path.join(d, "raw"))
    with open(os.path.join(d, "raw", "2026-10-25.jsonl"), "w") as f:
        for ln in lines:
            f.write((ln if isinstance(ln, str) else json.dumps(ln)) + "\n")


def rec(user, system=None):
    msgs = [{"role": "system", "content": system if system is not None else {"$blob": "abc"}}]
    msgs += [{"role": "user", "content": user}]
    return {"ts": "2026-10-25T10:00:00Z", "conv_id": "c", "messages": msgs, "response": {"content": "ok"}}


class HabitTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(habits.classify("sum this column in my Excel spreadsheet with SUMIFS"), "spreadsheet")
        self.assertEqual(habits.classify("fix this python bug, traceback below"), "code")
        self.assertEqual(habits.classify("hello there"), "other")
        self.assertEqual(habits.classify("move my meeting on the calendar"), "scheduling")

    def test_analyze_formats(self):
        with tempfile.TemporaryDirectory() as d:
            write_diary(d, [
                rec("make a pivot table from this csv"),
                rec([{"type": "text", "text": "vlookup these two spreadsheet tabs"}, {"type": "image_url", "image_url": {}}]),
                rec("make a pivot table from this csv"),  # duplicate text, counted once
                "not json",
                rec("draft an email reply to my inbox"),
                rec({"$blob": "x"}),  # no text
                rec("how are you"),
                {"messages": "weird"},
            ])
            s = habits.analyze(d)
            self.assertEqual(s["counts"], {"spreadsheet": 2, "email": 1, "other": 1})
            self.assertEqual(s["total"], 4)
            self.assertAlmostEqual(s["share"]["spreadsheet"], 0.5)

    def test_uses_last_user_turn_and_flat_dir(self):
        with tempfile.TemporaryDirectory() as d:
            r = rec("old csv question")
            r["messages"] += [{"role": "assistant", "content": "a"}, {"role": "user", "content": "now fix my python code bug"}]
            with open(os.path.join(d, "x.jsonl"), "w") as f:  # no raw/ subdir
                f.write(json.dumps(r) + "\n")
            self.assertEqual(habits.analyze(d)["counts"], {"code": 1})

    def test_pick_kind(self):
        self.assertEqual(habits.practicable_kinds(), ["spreadsheet"])
        stats = {"total": 10, "counts": {"spreadsheet": 2, "email": 8}, "share": {"spreadsheet": .2, "email": .8}}
        self.assertEqual(habits.pick_kind(stats), "spreadsheet")
        stats = {"total": 100, "counts": {"spreadsheet": 2, "email": 98}, "share": {"spreadsheet": .02, "email": .98}}
        self.assertIsNone(habits.pick_kind(stats))
        self.assertIsNone(habits.pick_kind(stats, min_share=0.01) and None)
        self.assertEqual(habits.pick_kind(stats, min_share=0.01), "spreadsheet")
        self.assertIsNone(habits.pick_kind(habits.analyze("/nonexistent/dir")))


if __name__ == "__main__":
    unittest.main()
