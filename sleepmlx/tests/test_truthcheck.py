"""I2 truth check before sleep (truthcheck.py + the recipe hook). Linux, fake model; truths = Ben's corrections, his card notes, hashes."""
import json
import unittest

from sleepmlx import insight as I
from sleepmlx import truthcheck as TC
from sleepmlx.recipe import Item

from .helpers import Env


def rows(n, src, bad, none):
    return [{"src": src, "v": "bad" if i < bad else "none" if i < bad + none else "ok"} for i in range(n)]


V, S = (lambda r: r["v"]), (lambda r: r["src"])


class RuleTests(unittest.TestCase):
    def test_trusted_failed_and_unchecked_sources(self):
        r = TC.check(rows(40, "a", 2, 5) + rows(40, "b", 12, 8) + rows(30, "c", 0, 25) + rows(30, "d", 1, 25), V, S)
        self.assertEqual({k: v["mode"] for k, v in r["sources"].items()}, {"a": "trusted", "b": "failed", "c": "unchecked", "d": "failed"})
        self.assertEqual([r["sources"][k]["kept"] for k in "abcd"], [38, 20, 30, 4])
        self.assertTrue(all(x["v"] != "bad" for x in r["kept"]))

    def test_a_raising_verifier_is_no_truth(self):
        def boom(_):
            raise RuntimeError("x")
        r = TC.check(rows(12, "a", 0, 0), boom, S)
        self.assertEqual(r["stats"]["none"], 12)
        self.assertEqual(len(r["kept"]), 12)

    def test_qa_against_bens_facts(self):
        wrong, facts = {"ben": {"chicago"}}, {"ben": {"dresden"}}
        self.assertEqual(TC.qa_verdict("Where does Ben live?", "Chicago", wrong, facts), "bad")
        self.assertEqual(TC.qa_verdict("Where does Ben live?", "Dresden", wrong, facts), "ok")
        self.assertEqual(TC.qa_verdict("Where does Ana live?", "Chicago", wrong, facts), "none")


def item(key, kind, qa, first=1, subj="Ben", obj="x", source=""):
    return Item(key, subj, obj, kind, first, first=first, qa=[list(p) for p in qa], para=["text"], kind=kind, source=source)


class NightStepTests(unittest.TestCase):
    def test_wrong_answers_are_removed_and_logged_per_kind(self):
        items = {"card|1": Item("card|1", "Ben", "Dresden", "lives in", 1, kind="fact", source="saved card note")}
        for i in range(12):
            items["rated|%d" % i] = item("rated|%d" % i, "rated", [["Where does Ben live?", "Dresden"], ["What did Ben ask about %d?" % i, "maths"]])
        items["rated|bad"] = item("rated|bad", "rated", [["Where does Ben live?", "Chicago"], ["What is Ben's dog?", "Rex"]])
        logs = []
        res = TC.night_step(items, {"ben": {"chicago"}}, [], None, log=logs.append)
        self.assertEqual(items["rated|bad"].qa, [["What is Ben's dog?", "Rex"]])   # trusted source: only the wrong Q&A goes
        self.assertFalse(items["rated|bad"].dead)
        self.assertEqual(res["stats"]["bad"], 1)
        self.assertTrue(any(l.startswith("[night] rated cards: truth check 12 right, 1 wrong") for l in logs), logs)
        self.assertEqual(len([l for l in logs if "cards: truth check" in l]), 3)   # one line per kind, every night

    def test_a_poisoned_source_keeps_only_verified_cards(self):
        items = {"card|1": Item("card|1", "Ben", "Dresden", "lives in", 1, kind="fact", source="saved card note")}
        for i in range(10):
            items["lesson|ok%d" % i] = item("lesson|ok%d" % i, "lesson", [["Where does Ben live?", "Dresden"]])
        for i in range(6):
            items["lesson|bad%d" % i] = item("lesson|bad%d" % i, "lesson", [["Where does Ben live?", "Chicago"]])
        items["lesson|unk"] = item("lesson|unk", "lesson", [["What colour is the sky?", "blue"]])
        items["lesson|other_night"] = item("lesson|other_night", "lesson", [["What colour is grass?", "green"]], first=2)
        TC.night_step(items, {"ben": {"chicago"}}, [], None, log=lambda s: None)
        self.assertTrue(all(items["lesson|bad%d" % i].dead for i in range(6)))
        self.assertTrue(items["lesson|unk"].dead)                  # unverifiable card of a failed source
        self.assertFalse(any(items["lesson|ok%d" % i].dead for i in range(10)))
        self.assertFalse(items["lesson|other_night"].dead)         # another night's source is not touched

    def test_insight_cards_are_rechecked_against_the_hash(self):
        e = {"id": "scientist:001", "truth": {"type": "sha256", "norm": "out", "value": I.truth_hash("4", "out")}}
        items = {"insight|scientist:001": item("insight|scientist:001", "insight", [["print(2+2)", "4"]]),
                 "insight|scientist:002": item("insight|scientist:002", "insight", [["p", "5"]])}
        e2 = {"id": "scientist:002", "truth": {"type": "sha256", "norm": "out", "value": I.truth_hash("6", "out")}}
        TC.night_step(items, {}, [e, e2], None, log=lambda s: None)
        self.assertFalse(items["insight|scientist:001"].dead)
        self.assertTrue(items["insight|scientist:002"].dead)


class RecipeHookTests(unittest.TestCase):
    def test_night_runs_with_the_hook_and_survives_a_crash(self):
        env = Env()
        try:
            sl = env.sleeper(env.backend())
            res = sl.run(env.week())
            self.assertEqual(res["status"], "done", res)
            ud = env.paths.userdata_dir
            if sl.cfg.use_userdata and (ud / TC.LOG).exists():
                parts = [json.loads(l)["part"] for l in (ud / TC.LOG).read_text().splitlines()]
                self.assertIn("sleep-rated", parts)
        finally:
            env.close()
        env = Env()
        try:
            sl = env.sleeper(env.backend())
            orig = TC.night_step
            TC.night_step = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
            try:
                res = sl.run(env.week())
            finally:
                TC.night_step = orig
            self.assertEqual(res["status"], "done", res)
            row = json.loads(env.paths.nights.read_text().splitlines()[-1])
            self.assertEqual(row["stats"]["lessons"]["truthcheck_error"], 1)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
