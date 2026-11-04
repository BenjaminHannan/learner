"""T5 sleep insight (insight.py + recipe.Sleeper.insight_stage). Linux, fake model: the candidates are canned, the truth is a hash."""
import hashlib
import json
import unittest
from collections import Counter

from sleepmlx import insight as I
from sleepmlx.paths import read_json

from .helpers import Env

ANSWER = "zebra-quartz-17"


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def stuck_file(ud, items):
    ud.mkdir(parents=True, exist_ok=True)
    (ud / I.STUCK_FILE).write_text(json.dumps({"v": 1, "items": items}))


def entry(i, problem, truth=None, norm="out", source="scientist", weight=1.0):
    return {"id": "scientist:%03d" % i, "source": source, "kind": "python", "problem": problem, "context": "All 4 of my tries were wrong.",
            "truth": {"type": "sha256", "norm": norm, "value": I.truth_hash(truth, norm)} if truth is not None else {"type": "none"}, "weight": weight}


class NormAndTruthTests(unittest.TestCase):
    def test_hashes_match_the_desk(self):
        # values from desk/src/stuck.js truthHash (node), so JS and Python agree on what "the same answer" is
        self.assertEqual(I.truth_hash(ANSWER + "\r\n  \n", "out"), "f63334c41ac8a1b855b28829a83ccfde85070251cde9e8af2c850dee3bfbea93")
        self.assertEqual(I.truth_hash("Answer: 1, 2 3.", "puzzle"), "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3")
        self.assertEqual(I.truth_hash("  [3, 4]\n\n", "out"), "beeb756daf8284d15b71625981db2f335c1bf299ee918a8f0929f934e9ded2fa")

    def test_only_a_matching_hash_verifies(self):
        e = entry(1, "p", ANSWER)
        self.assertTrue(I.verified(e, ANSWER + "  \n"))
        self.assertFalse(I.verified(e, "zebra-quartz-18"))
        self.assertFalse(I.verified(e, ""))
        self.assertFalse(I.verified(entry(2, "p"), ANSWER))                                    # no truth: never verified
        self.assertFalse(I.verified({"truth": {"type": "sha256", "norm": "out", "value": "x"}}, ANSWER))   # malformed hash
        self.assertFalse(I.verified({"truth": {"type": "sha256", "norm": "llm", "value": h(ANSWER)}}, ANSWER))   # unknown checker
        self.assertTrue(I.verified(entry(3, "p", "1 2 3", norm="puzzle"), "answer: 1,2,3"))

    def test_read_stuck_refuses_plain_answers_and_sorts_by_weight(self):
        env = Env()
        try:
            ud = env.paths.userdata_dir
            bad = dict(entry(9, "leaky", ANSWER), answer=ANSWER)
            stuck_file(ud, [entry(1, "low", ANSWER, weight=0.3), bad, entry(2, "high", ANSWER, weight=1.0), {"id": "", "problem": "x"}])
            got = I.read_stuck(ud)
            self.assertEqual([e["problem"] for e in got], ["high", "low"])
            self.assertEqual(I.read_stuck(None), [])
        finally:
            env.close()


class RecallTests(unittest.TestCase):
    def test_related_memories_rank_first_and_pairs_mix_them(self):
        mems = ["Paris is the capital of France.", "To reverse the letters of a word, read it from the end.", "upper() makes every letter upper case.",
                "Marta works at Kestrel."]
        rec = [t for _, t in I.recall("Puzzle: reverse the letters of 'kayak', then make every letter upper case.", mems, 3)]
        self.assertEqual(set(rec[:2]), {mems[1], mems[2]})
        self.assertNotIn(mems[3], rec)
        ps = I.pairs(rec, 4)
        self.assertEqual(len(ps), 4)
        self.assertEqual(set(ps[0]), set(rec[:2]))
        self.assertEqual(I.pairs([], 2), [(), ()])


class StageTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def sleeper(self, replies):
        e = self.env
        sl = e.sleeper(e.backend())
        sl.load_items()
        sl.N = {"date": "2026-11-04", "lessons": []}
        sl.set_scale(1.0)
        from sleepmlx.corpus import Diary
        from sleepmlx.recipe import GenCache
        sl.diary, sl.cache = Diary(e.week()), GenCache(None)
        self.prompts = []

        def gen(prompts, max_tokens, sample=False, base=True, salt="", stops=()):
            self.prompts.extend(prompts)
            return [replies(p, i) for i, p in enumerate(prompts)]
        sl.gen = gen
        return sl

    def test_only_verified_candidates_become_cards(self):
        ud = self.env.paths.userdata_dir
        stuck_file(ud, [entry(1, "What does this print?\nprint('zebra' + '-quartz-' + str(17))", ANSWER),
                        entry(2, "What does this print?\nprint(2 + 2)", "4"),
                        entry(3, "Ben keeps seeing ModuleNotFoundError: numpy", source="ben-error")])
        # problem 1: first mix wrong, second right; problem 2: every mix wrong (stays stuck)
        def replies(p, i):
            if "zebra" in p:
                return json.dumps({"working": "join the parts", "answer": ANSWER if i % 4 == 1 else "zebra quartz 17"})
            return json.dumps({"working": "add", "answer": "5"})
        sl = self.sleeper(replies)
        st = Counter()
        sl.insight_stage(1, st)
        it = sl.items.get("insight|scientist:001")
        self.assertIsNotNone(it)
        self.assertEqual(it.kind, "insight")
        self.assertEqual(it.qa[0][1], ANSWER)
        self.assertIn("checked by the executor", it.para[0])
        self.assertNotIn("insight|scientist:002", sl.items)
        self.assertNotIn("insight|scientist:003", sl.items)
        self.assertEqual(st["insight_clicked"], 1)
        self.assertEqual(st["insight_no_truth"], 1)
        self.assertEqual(st["insight_tried"], 2)
        self.assertEqual(st["insight_unverified_dropped"], 1 + 4)
        self.assertFalse(any(ANSWER in p for p in self.prompts))                         # the answer itself is never in a prompt
        self.assertFalse(any(I.truth_hash(ANSWER) in p for p in self.prompts))        # the truth never reaches a prompt
        res = read_json(ud / I.RESULTS_FILE)
        self.assertEqual([c["id"] for c in res["clicked"]], ["scientist:001"])
        self.assertEqual(res["no_truth"], 1)
        self.assertEqual(len(self.prompts), 2 * sl.cfg.insight_k)                         # same K per problem

    def test_nothing_is_stored_when_no_candidate_checks_out(self):
        ud = self.env.paths.userdata_dir
        stuck_file(ud, [entry(1, "What does this print?\nprint(2 + 2)", "4")])
        sl = self.sleeper(lambda p, i: "not json" if i == 0 else json.dumps({"answer": "four"}))
        st = Counter()
        sl.insight_stage(1, st)
        self.assertFalse([k for k in sl.items if k.startswith("insight|")])
        self.assertEqual(st["insight_parse_fail"], 1)
        self.assertEqual(read_json(ud / I.RESULTS_FILE)["clicked"], [])

    def test_a_solved_problem_is_not_redone_and_the_switch_turns_it_off(self):
        ud = self.env.paths.userdata_dir
        stuck_file(ud, [entry(1, "What does this print?\nprint(2 + 2)", "4")])
        sl = self.sleeper(lambda p, i: json.dumps({"working": "2 and 2", "answer": "4"}))
        sl.insight_stage(1, Counter())
        n = len(self.prompts)
        st = Counter()
        sl.insight_stage(2, st)
        self.assertEqual(len(self.prompts), n)
        self.assertEqual(read_json(ud / I.RESULTS_FILE)["clicked"][0].get("earlier"), True)
        sl.cfg.use_insight = False
        (ud / I.RESULTS_FILE).unlink()
        sl.insight_stage(3, Counter())
        self.assertFalse((ud / I.RESULTS_FILE).exists())


class NightSafetyTests(unittest.TestCase):
    def test_a_crashing_insight_step_is_skipped_and_the_night_finishes(self):
        env = Env()
        try:
            sl = env.sleeper(env.backend())
            def boom(d, st):
                raise RuntimeError("metal: out of memory")
            sl.insight_stage = boom
            res = sl.run(env.week())
            self.assertEqual(res["status"], "done", res)
            row = json.loads(env.paths.nights.read_text().splitlines()[-1])
            self.assertEqual(row["stats"]["lessons"]["insight_error"], 1)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
