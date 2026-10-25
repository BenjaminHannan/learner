import contextlib
import io
import json
import os
import unittest

from sleepmode import dreamcheck
from sleepmode.practice.model import FakeModel, tool_call_msg
from sleepmode.tools import ToolBox

try:
    from .helpers import TmpCase
except ImportError:
    from helpers import TmpCase


def fake(messages):
    user = messages[1]["content"]
    if messages[-1]["role"] != "tool":
        return tool_call_msg("diary_search", {"query": "dentist"})
    ev = messages[-1]["content"]
    if "Question:\nWho is my dentist?" in user:
        return 'Diary matches.\nEVIDENCE: "my dentist is  dr. OKAFOR"\nVERDICT: SUPPORTED' if "Okafor" in ev and "Okafor" in user else "VERDICT: CONTRADICTED\nFIX: Dr. Okafor"
    if "sister" in user:
        return "VERDICT: CONTRADICTED"
    return "cannot tell\nVERDICT: UNKNOWN"


class DreamTests(TmpCase):
    def setUp(self):
        super().setUp()
        d = os.path.join(self.root, "diary", "raw")
        os.makedirs(d)
        with open(os.path.join(d, "2026-10-01.jsonl"), "w") as f:
            f.write(json.dumps({"conv_id": "c1", "messages": [{"role": "user", "content": "my dentist is Dr. Okafor"}]}) + "\n")
        self.diary = os.path.join(self.root, "diary")
        self.inp = os.path.join(self.root, "dreams.jsonl")
        items = [{"id": "a", "question": "Who is my dentist?", "answer": "Dr. Okafor"},
                 {"id": "b", "question": "Who is my dentist?", "answer": "Dr. Smith"},
                 {"id": "c", "question": "What is my sister's name?", "answer": "Zed"},
                 {"id": "d", "question": "What color is my car?", "answer": "red"},
                 {"id": "e", "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "Who is my dentist?"},
                                          {"role": "assistant", "content": "Dr. Jones"}]},
                 {"id": "f", "question": "", "answer": "x"}]
        with open(self.inp, "w") as f:
            f.write("\n".join(json.dumps(i) for i in items) + "\nnot json\n")

    def lines(self, name):
        with open(os.path.join(self.out, name)) as f:
            return [json.loads(l) for l in f]

    def test_run(self):
        self.out = os.path.join(self.root, "out")
        st = dreamcheck.run(self.inp, self.out, FakeModel(fake), ToolBox(self.diary, web=False))
        kept = {r["id"]: r for r in self.lines("kept.jsonl")}
        dropped = {r["id"]: r for r in self.lines("dropped.jsonl")}
        self.assertEqual(sorted(kept), ["a", "b", "e"])
        self.assertEqual(sorted(dropped), ["c", "f"])
        quarantine = {r["id"]: r for r in self.lines("quarantine.jsonl")}
        self.assertEqual(sorted(quarantine), ["d"])
        self.assertFalse(kept["a"]["fixed"])
        self.assertTrue(kept["b"]["fixed"])
        self.assertEqual(kept["b"]["answer"], "Dr. Okafor")
        self.assertEqual(kept["e"]["messages"][-1]["content"], "Dr. Okafor")
        self.assertEqual(kept["e"]["messages"][1]["content"], "Who is my dentist?")
        self.assertEqual(kept["a"]["tool_calls"], {"diary_search": 1})
        self.assertIn("no fix", dropped["c"]["reason"])
        with open(os.path.join(self.out, "stats.json")) as f:
            self.assertEqual(json.load(f), st)
        self.assertEqual((st["n"], st["supported"], st["contradicted"], st["unknown"], st["invalid"], st["fixed"]),
                         (6, 1, 3, 1, 1, 2))
        self.assertEqual((st["kept"], st["quarantined"]), (3, 1))

    def test_keep_unknown_max_and_errors(self):
        self.out = os.path.join(self.root, "out2")
        st = dreamcheck.run(self.inp, self.out, FakeModel(fake), ToolBox(self.diary, web=False), keep_unknown=True, max_items=4)
        self.assertEqual(sorted(r["id"] for r in self.lines("kept.jsonl")), ["a", "b", "d"])
        self.assertEqual(st["n"], 4)

        def boom(m):
            raise OSError("down")
        st = dreamcheck.run(self.inp, os.path.join(self.root, "out3"), FakeModel(boom), ToolBox(self.diary, web=False))
        self.assertEqual((st["kept"], st["errors"]), (0, 5))

    def test_supported_without_valid_evidence_is_unknown(self):
        def liar(messages):
            if messages[-1]["role"] != "tool":
                return tool_call_msg("diary_search", {"query": "dentist"})
            return 'EVIDENCE: "my dentist is Dr. Smith"\nVERDICT: SUPPORTED'
        def short(messages):
            if messages[-1]["role"] != "tool":
                return tool_call_msg("diary_search", {"query": "dentist"})
            return 'EVIDENCE: "Okafor"\nVERDICT: SUPPORTED'
        for fn in (liar, short, lambda m: "VERDICT: SUPPORTED"):
            out = os.path.join(self.root, "ev")
            st = dreamcheck.run(self.inp, out, FakeModel(fn), ToolBox(self.diary, web=False), max_items=1)
            self.out = out
            self.assertEqual((st["supported"], st["unknown"], st["kept"], st["quarantined"]), (0, 1, 0, 1))
            self.assertIn("no evidence", self.lines("quarantine.jsonl")[0]["reason"])

    def test_hops_need_evidence_each(self):
        item = {"id": "h", "question": "Who is my dentist?", "answer": "Dr. Okafor", "hops": ["Ben has a dentist", "Name is Okafor"]}
        def model(reply2):
            def fn(messages):
                if messages[-1]["role"] != "tool":
                    return tool_call_msg("diary_search", {"query": "dentist"})
                return reply2
            return fn
        one = 'EVIDENCE: "my dentist is Dr. Okafor"\nVERDICT: SUPPORTED'
        two = 'EVIDENCE 1: "my dentist is Dr. Okafor"\nEVIDENCE 2: "dentist is dr. okafor"\nVERDICT: SUPPORTED'
        tb = ToolBox(self.diary, web=False)
        self.assertEqual(dreamcheck.check_item(FakeModel(model(one)), tb, item)[0], "UNKNOWN")
        m = FakeModel(model(two))
        self.assertEqual(dreamcheck.check_item(m, tb, item)[0], "SUPPORTED")
        self.assertIn("1. Ben has a dentist", m.calls[0][1]["content"])

    def test_plant(self):
        import random
        items = [{"id": "a", "question": "q", "answer": "Dr. Okafor has 12 cats"},
                 {"id": "b", "question": "q", "answer": "Dr. Smith, 3 dogs"},
                 {"id": "c", "question": "q", "answer": "yes"}]
        plants = dreamcheck.add_plants(items, 5, random.Random(1))
        self.assertEqual(len(plants), 2)   # item c has neither number nor name
        for p in plants:
            orig = next(i for i in items if i["id"] + "#planted" == p["id"])
            self.assertTrue(p["planted"])
            self.assertNotEqual(p["answer"], orig["answer"])

        def always_yes(messages):
            if messages[-1]["role"] != "tool":
                return tool_call_msg("diary_search", {"query": "dentist"})
            return 'EVIDENCE: "my dentist is Dr. Okafor"\nVERDICT: SUPPORTED'
        self.out = os.path.join(self.root, "pl")
        st = dreamcheck.run(self.inp, self.out, FakeModel(always_yes), ToolBox(self.diary, web=False), plant=2)
        self.assertEqual((st["planted"], st["planted_accepted"], st["planted_false_accept_rate"]), (2, 2, 1.0))
        self.assertEqual(st["n"], 6)
        for name in ("kept.jsonl", "quarantine.jsonl", "dropped.jsonl"):
            self.assertFalse(any(r.get("planted") for r in self.lines(name)))

    def test_parse_and_cli(self):
        self.assertEqual(dreamcheck.parse_verdict("x\nverdict: contradicted\nFIX: a\nb"), ("CONTRADICTED", "a\nb"))
        self.assertEqual(dreamcheck.parse_verdict("FIX: z\nVERDICT: CONTRADICTED"), ("CONTRADICTED", "z"))
        self.assertEqual(dreamcheck.parse_verdict("meh"), ("UNKNOWN", None))
        out = os.path.join(self.root, "cli")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = dreamcheck.main([self.inp, "--out", out, "--no-web", "--diary", self.diary, "--max", "1"],
                                 model=FakeModel(fake))
        self.assertEqual(rc, 0)
        with open(os.path.join(out, "kept.jsonl")) as f:
            self.assertEqual(len(f.readlines()), 1)
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            dreamcheck.main([self.inp, "--out", out])


if __name__ == "__main__":
    unittest.main()
