"""Flashcards from the turns Ben rated with a thumbs up or down (lessons.rated, recipe.rated_stage). Linux, fake model."""
import json
import unittest
from collections import Counter

from sleepmlx import diary as diary_mod
from sleepmlx import lessons as L
from sleepmlx.paths import read_json

from .helpers import Env
from .test_lessons import chat, write_recs

UP_ASK, UP_ANS = "Who should I thank for the Orbix tour?", "Thank Marta and Tomas, they ran the Orbix tour."
DOWN_ASK, DOWN_ANS = "Where does Pavel live?", "Pavel lives in Dalmore."
FIX = "No, it's Quillon. Pavel lives in Quillon, not Dalmore."


def feedback(env, rows, ts="2026-10-22T10:00:00Z"):
    ud = env.paths.userdata_dir
    ud.mkdir(parents=True, exist_ok=True)
    with open(str(ud / "feedback.jsonl"), "w") as f:
        for fb, u, a in rows:
            f.write(json.dumps({"ts": ts, "fb": fb, "user": u, "answer": a}) + "\n")


def week_of(env):
    return diary_mod.build_week(env.paths.diary_dir, "Ben", feedback=L.read_feedback(env.paths.userdata_dir))


class RatedTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(days=(), min_cards=2)

    def tearDown(self):
        self.env.close()

    def cards(self):
        return [json.loads(l) for l in self.env.paths.cards.read_text().splitlines()]

    def only_rated_day(self, date="2026-10-21", ts0=1_700_200_000.0):
        write_recs(self.env.paths.diary_dir, date, chat([(UP_ASK, UP_ANS, {}), ("thanks", "Anytime.", {})], ts0=ts0))

    def sleep(self, be=None):
        e = self.env
        be = be or e.backend()
        return be, e.sleeper(be).run(week_of(e))

    def test_rated_lists_context_and_skips_unanswered_and_secrets(self):
        e = self.env
        write_recs(e.paths.diary_dir, "2026-10-21", chat([("hello there", "Hi.", {}), (DOWN_ASK, DOWN_ANS, {}), (FIX, "Got it, Quillon.", {}), ("my password is hunter2", "ok", {})]))
        feedback(e, [(-1, DOWN_ASK, DOWN_ANS), (1, "my password is hunter2", "ok")])
        r = L.rated(week_of(e))
        self.assertEqual(len(r), 1)
        self.assertTrue(r[0]["key"].startswith("rated|") and len(r[0]["key"]) == 18)
        self.assertEqual(r[0]["fb"], -1)
        for part in ("Ben: hello there", "(Ben gave this answer a thumbs down)", "Ben then said: " + FIX, "Glim: Got it, Quillon."):
            self.assertIn(part, r[0]["ctx"])

    def test_thumbs_up_turn_yields_verified_cards_with_one_held_out(self):
        e = self.env
        self.only_rated_day()
        feedback(e, [(1, UP_ASK, UP_ANS)])
        _, res = self.sleep()
        self.assertEqual(res["status"], "done", res)
        it = [x for x in read_json(e.paths.items)["items"].values() if x["kind"] == "rated"]
        self.assertEqual(len(it), 1)
        self.assertEqual(len(it[0]["qa"]) + len(it[0]["held"]), 3)   # Marta, Tomas, Orbix, all verified
        self.assertGreaterEqual(len(it[0]["held"]), 1)   # 1 from the rated rule (+1 if the night's top-up needed a second)
        self.assertIn("thumbs up", it[0]["source"])
        self.assertFalse(any(k.startswith("liked|") for k in read_json(e.paths.items)["items"]))   # no duplicate liked card
        self.assertTrue(any(c["kind"] == "rated_qa" for c in self.cards()))
        self.assertFalse(any(h["q"] in json.dumps(c) for h in it[0]["held"] for c in self.cards()))   # held card is never written for training

    def test_thumbs_down_with_correction_uses_bens_words(self):
        e = self.env
        write_recs(e.paths.diary_dir, "2026-10-21", chat([(DOWN_ASK, DOWN_ANS, {}), (FIX, "Got it.", {})]))
        feedback(e, [(-1, DOWN_ASK, DOWN_ANS)])
        be, res = self.sleep()
        it = [x for x in read_json(e.paths.items)["items"].values() if x["kind"] == "rated"][0]
        self.assertTrue(it["cor"])
        answers = [a for _, a in it["qa"]] + [h["a"] for h in it["held"]]
        self.assertIn("Quillon", answers)
        self.assertNotIn("Dalmore", answers)
        self.assertNotIn("Dalmore", json.dumps(it["para"]))

    def test_older_day_is_carded_once_and_not_regenerated(self):
        e = self.env
        self.only_rated_day("2026-10-19", 1_699_900_000.0)
        feedback(e, [(1, UP_ASK, UP_ANS)], "2026-10-19T10:00:00Z")
        be1, res1 = self.sleep()
        self.assertEqual(res1["status"], "done", res1)
        before = {k: json.dumps({a: b for a, b in v.items() if a != "trained"}, sort_keys=True) for k, v in read_json(e.paths.items)["items"].items() if v["kind"] == "rated"}
        self.assertEqual(len(before), 1)
        held = [v["held"] for v in read_json(e.paths.items)["items"].values() if v["kind"] == "rated"][0]
        # a second night on a later day: the rated turn is already carded
        write_recs(e.paths.diary_dir, "2026-10-22", chat([("Lena owns Sunbird", "Noted.", {}), ("Tomas is the mentor of Lena", "Noted.", {}),
                                                          ("Marta works at Orbix", "Noted.", {}), ("Pavel lives in Quillon", "Noted.", {})], ts0=1_700_300_000.0))
        be2 = e.backend()
        sl = e.sleeper(be2)
        calls = []
        orig = sl.gen
        sl.gen = lambda prompts, *a, **kw: (calls.extend(p for p in prompts if "Write flashcards from this chat" in p), orig(prompts, *a, **kw))[1]
        res2 = sl.run(week_of(e))
        self.assertEqual(res2["status"], "done", res2)
        self.assertEqual(calls, [])
        after = {k: json.dumps({a: b for a, b in v.items() if a != "trained"}, sort_keys=True) for k, v in read_json(e.paths.items)["items"].items() if v["kind"] == "rated"}
        self.assertEqual(after, before)
        self.assertEqual([v["held"] for v in read_json(e.paths.items)["items"].values() if v["kind"] == "rated"][0], held)

    def test_unrated_turn_retires_its_item(self):
        e = self.env
        self.only_rated_day()
        feedback(e, [(1, UP_ASK, UP_ANS)])
        self.sleep()
        feedback(e, [(0, UP_ASK, UP_ANS)])
        write_recs(e.paths.diary_dir, "2026-10-22", chat([("Lena owns Sunbird", "Noted.", {})], ts0=1_700_300_000.0))
        self.sleep()
        self.assertTrue(all(v["dead"] for v in read_json(e.paths.items)["items"].values() if v["kind"] == "rated"))

    def test_turn_with_no_verified_card_is_remembered_and_up_keeps_liked_card(self):
        e = self.env
        write_recs(e.paths.diary_dir, "2026-10-21", chat([("plan my week", "do the reading first, then rest", {}), ("ok", "Fine.", {})]))
        feedback(e, [(1, "plan my week", "do the reading first, then rest")])
        week = week_of(e)
        from .test_lessons import NightTests
        sl, _ = NightTests.sleeper_on(self, None)
        sl.cfg.use_lessons = True
        st = Counter()
        sl.rated_stage(week, 1, st)
        sl.today = lambda: "2026-10-28"
        sl.extras(week, 1, st)
        self.assertEqual(st["rated_none"], 1)
        self.assertEqual(st["liked"], 1)                        # the word-for-word liked card is the fallback
        marker = sl.items[L.rated(week)[0]["key"]]
        self.assertFalse(marker.qa or marker.para)
        st2 = Counter()
        n = []
        sl.gen = lambda *a, **k: n.append(1) or []
        sl.rated_stage(week, 2, st2)
        self.assertEqual(n, [])                                  # not retried

    def test_night_of_only_rated_turns_has_held_cards_and_passes_the_gate_check(self):
        e = self.env
        self.only_rated_day()
        feedback(e, [(1, UP_ASK, UP_ANS)])
        _, res = self.sleep()
        self.assertEqual(res["status"], "done", res)
        night = [json.loads(l) for l in e.paths.nights.read_text().splitlines()][-1]
        self.assertEqual(night["stats"]["lessons"]["rated_held_out"], 1)
        self.assertTrue(any(h["night"] == 1 for v in read_json(e.paths.items)["items"].values() for h in v["held"]))
        self.assertNotIn("no held-out cards", json.dumps(res.get("gate") or res.get("reasons") or ""))


if __name__ == "__main__":
    unittest.main()
