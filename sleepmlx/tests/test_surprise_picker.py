"""Surprise-picked replay (picker.py) + the morning check (morning.py). Fake model only."""
import json
import unittest
from types import SimpleNamespace as NS

from sleepmlx import morning as morning_mod
from sleepmlx import picker as picker_mod

from .fakes import names
from .helpers import Env


class ScoringBackendMixin:
    """nll(): low loss when the fake already 'knows' a name in the question, high otherwise."""

    def nll(self, examples):
        self.nll_calls = getattr(self, "nll_calls", 0) + 1
        out = []
        for ids, ls in examples:
            q = self.dec(ids[:ls]).split("Question: ")[-1]
            out.append(0.05 if any(n in self.known for n in names(q)) else 3.0)
        return out


def scoring_backend(env, **kw):
    be = env.backend(**kw)
    be.__class__ = type("ScoringFake", (ScoringBackendMixin, be.__class__), {})
    return be


class PickerUnitTests(unittest.TestCase):
    def test_conflicted_questions_are_noise_and_dead_items_dont_count(self):
        a = NS(dead=False, qa=[["What is Marta's town?", "Dalmore"]], para=["Marta lives in Dalmore."])
        b = NS(dead=False, qa=[["what is marta's town", "Quillon"]], para=[])
        c = NS(dead=False, qa=[["Who mentors Lena?", "Tomas"]], para=[])
        self.assertEqual(picker_mod.conflicted_questions([a, b, c]), {"what is marta s town"})
        b.dead = True   # a correction retired the old item: the question is consistent again
        self.assertEqual(picker_mod.conflicted_questions([a, b, c]), set())
        b.dead = False
        conf = picker_mod.conflicted_questions([a, b, c])
        self.assertEqual(picker_mod.item_cards(a, conf), ["Marta lives in Dalmore."])   # text kept, conflicted Q&A dropped
        self.assertEqual(picker_mod.item_cards(b, conf), [])
        self.assertEqual(picker_mod.item_cards(c, conf), [["Who mentors Lena?", "Tomas"]])

    def test_weights_floor_and_split(self):
        w = picker_mod.surprise_weights([2.0, 0.0, None])
        self.assertEqual(w[2], 0.0)
        self.assertAlmostEqual(w[1], 0.05 * 1.0)          # floor = 5 % of the mean surprise (1.0)
        self.assertAlmostEqual(w[0], 2.05)
        self.assertEqual(picker_mod.split(16, 0.5), (8, 8))
        self.assertEqual(picker_mod.split(7, 0.0), (0, 7))
        self.assertEqual(picker_mod.split(7, 1.5), (7, 0))


class PickerNightTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def night_row(self):
        rows = [json.loads(l) for l in self.env.paths.nights.read_text().splitlines()]
        return rows[-1]

    def test_default_is_surprise_mix_and_it_splits_draws(self):
        self.assertEqual(self.env.cfg.replay_picker, "surprise_mix")
        be = scoring_backend(self.env)
        res = self.env.sleeper(be).run(self.env.week())
        self.assertEqual(res["status"], "done", res)
        self.assertGreater(getattr(be, "nll_calls", 0), 0)
        pk = self.night_row()["stats"]["picker"]
        self.assertEqual(pk["mode"], "surprise_mix")
        self.assertGreater(pk["surprise_draws"], 0)
        self.assertGreater(pk["rehearsal_draws"], 0)
        self.assertEqual(pk.get("fallback_draws", 0), 0)
        self.assertGreaterEqual(pk["rescored"], 1)
        tot = pk["surprise_draws"] + pk["rehearsal_draws"]
        self.assertLess(abs(pk["surprise_draws"] / tot - 0.5), 0.15)
        self.assertEqual(sorted(be.steps_seen), list(range(res["steps_total"])))   # same budget: every planned step ran

    def test_backend_without_nll_falls_back_to_priority(self):
        be = self.env.backend()
        res = self.env.sleeper(be).run(self.env.week())
        self.assertEqual(res["status"], "done", res)
        pk = self.night_row()["stats"]["picker"]
        self.assertGreater(pk["fallback_no_nll"], 0)
        self.assertGreater(pk["fallback_draws"], 0)
        self.assertEqual(pk.get("surprise_draws", 0), 0)

    def test_crashing_nll_falls_back_and_the_night_finishes(self):
        be = self.env.backend()
        def boom(examples):
            raise RuntimeError("metal: out of memory")
        be.nll = boom
        res = self.env.sleeper(be).run(self.env.week())
        self.assertEqual(res["status"], "done", res)
        pk = self.night_row()["stats"]["picker"]
        self.assertGreater(pk["fallback_error"], 0)
        self.assertIn("out of memory", pk["fallback_error_msg"])
        self.assertGreater(pk["fallback_draws"], 0)
        self.assertEqual(pk.get("surprise_draws", 0), 0)

    def test_switch_off_restores_the_priority_draw(self):
        self.env.cfg.replay_picker = "prio"
        be = scoring_backend(self.env)
        res = self.env.sleeper(be).run(self.env.week())
        self.assertEqual(res["status"], "done", res)
        self.assertEqual(getattr(be, "nll_calls", 0), 0)
        self.assertNotIn("picker", self.night_row()["stats"])

    def test_morning_check_reads_the_real_row(self):
        be = scoring_backend(self.env)
        self.env.sleeper(be).run(self.env.week())
        r = morning_mod.morning_check(morning_mod.last_night(self.env.paths.nights))
        self.assertTrue(r["ok"])
        self.assertTrue(r["kept"])
        self.assertIsNotNone(r["general"])
        self.assertIsNotNone(r["recall_after"])
        self.assertGreater(r["picker"]["surprise_draws"], 0)
        text = "\n".join(r["lines"])
        self.assertIn("kept", text)
        self.assertIn("General questions", text)
        self.assertIn("chosen by surprise", text)


class MorningUnitTests(unittest.TestCase):
    def test_rollback_and_empty(self):
        self.assertFalse(morning_mod.morning_check(None)["ok"])
        row = {"status": "done", "date": "2026-11-05", "reverted": True, "general": 90.0, "harm": 7.5, "quiz": 40.0, "recall_pre": 10.0,
               "held_out": 6, "stats": {"picker": {"mode": "surprise_mix", "fallback_draws": 30, "fallback_no_nll": 1}}}
        r = morning_mod.morning_check(row, harm_max=3.0)
        self.assertFalse(r["kept"])
        self.assertAlmostEqual(r["general_base"], 97.5)
        text = "\n".join(r["lines"])
        self.assertIn("ROLLED BACK", text)
        self.assertIn("lost 7.5 points; the limit is 3.0", text)
        self.assertIn("10% -> 40%", text)
        self.assertIn("backend cannot score", text)


if __name__ == "__main__":
    unittest.main()
