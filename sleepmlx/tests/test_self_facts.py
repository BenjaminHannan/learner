"""Facts Ben states about himself, quizzable saved notes, the holdout guarantee, card notes (recipe.py). Fake model."""
import json
import unittest
from collections import Counter

from sleepmlx import gate as gate_mod
from sleepmlx import prompts as P
from sleepmlx.corpus import Diary
from sleepmlx.recipe import GenCache, Item, selfify, triple_status

from .fakes import FakeBackend
from .helpers import Env

TURN = "I'm applying to Duke and my essay is about robotics"


class TagBackend(FakeBackend):
    """A tagger that answers with a fixed reply."""
    reply = "[]"

    def one(self, p, max_tokens, adapter):
        if "List the facts this message states" in p:
            return self.reply
        return super().one(p, max_tokens, adapter)


def stage_sleeper(env, be=None):
    sl = env.sleeper(be or env.backend())
    week = env.week()
    sl.load_items()
    sl.N = {"date": "2026-10-20", "lessons": []}
    sl.set_scale(1.0)
    sl.diary, sl.cache = Diary(week, "Ben"), GenCache(None)
    sl.today = lambda: "2026-10-28"
    return sl, week, int(min(week["dates"], key=int))


def write_memory(env, facts):
    ud = env.paths.userdata_dir
    ud.mkdir(parents=True, exist_ok=True)
    (ud / "memory.json").write_text(json.dumps({"facts": facts}))


def held_n(sl, d):
    return sum(1 for it in sl.items.values() for h in it.held if h["night"] == d)


class SelfFactTests(unittest.TestCase):
    def test_i_applying_to_duke_is_a_ben_fact(self):
        env = Env(days=(("2026-10-20", [TURN]),))
        try:
            be = TagBackend(env.time)
            be.reply = json.dumps([{"subject": "I", "relation": "is applying to", "object": "Duke"}])
            sl, week, d = stage_sleeper(env, be)
            st = Counter()
            sl.tag(d, st)
            self.assertEqual(list(sl.items), ["ben|duke"])
            it = sl.items["ben|duke"]
            self.assertEqual((it.subj, it.obj, it.rel), ("Ben", "Duke", "is applying to"))
            self.assertEqual(st["dropped_invalid"], 0)
            self.assertIn("Ben himself", P.tag_prompt(sl.R, "hi", "Ben"))
        finally:
            env.close()

    def test_ben_with_a_generic_word_stays_invalid(self):
        env = Env(days=(("2026-10-20", [TURN]),))
        try:
            sl, week, d = stage_sleeper(env)
            ts = lambda a, b: triple_status(sl.diary, set(), 0, a, b, "Ben")   # noqa: E731
            self.assertEqual(ts("Ben", "my"), "invalid")
            self.assertEqual(ts("Ben", "Ben"), "invalid")
            self.assertEqual(ts("Ben", "he"), "invalid")
            self.assertEqual(ts("Ben", "Duke"), "ok")
            self.assertEqual(triple_status(sl.diary, set(), 0, "Ben", "Duke"), "invalid")   # without `who`, Ben is generic as before
            self.assertEqual((selfify("my", "Ben"), selfify("Duke", "Ben"), selfify("ben", "Ben")), ("Ben", "Duke", "Ben"))
        finally:
            env.close()

    def test_small_day_still_holds_out_a_card(self):
        env = Env(days=(("2026-10-20", ["Remember that Marta works at Orbix"]),))
        try:
            sl = env.sleeper(env.backend())
            res = sl.run(env.week(), dry_run=True)     # one fact: under min_cards, no training
            held = [h for it in sl.items.values() for h in it.held]
            self.assertGreaterEqual(len(held), 1)
        finally:
            env.close()


class NoteQuizTests(unittest.TestCase):
    NOTES = [{"id": "m1", "text": "My sister is Emma", "topic": "family"}, {"id": "m2", "text": "Ben's mentor is Tomas", "topic": ""}]

    def test_notes_and_a_lesson_get_a_held_out_card(self):
        env = Env(days=(("2026-10-20", ["ok thanks"]),))
        try:
            write_memory(env, self.NOTES)
            sl, week, d = stage_sleeper(env)
            sl.items["lesson|x"] = Item("lesson|x", "Glim", "Emma", "lesson", d, first=d, para=["Glim forgot."], qa=[["Who is right?", "Emma"]], kind="lesson")
            st = Counter()
            sl.extras(week, d, st)
            self.assertEqual(st["note_qa_kept"], 2)
            sl.hold_lessons(d, st)
            self.assertEqual(held_n(sl, d), 0)          # one lesson: the old rule holds none
            sl.top_up_holdout(d, st)
            self.assertEqual(held_n(sl, d), 2)
            self.assertTrue(sl.items["lesson|x"].held and sl.items["lesson|x"].para)    # the lesson keeps its paraphrase
            self.assertEqual(gate_mod.decide({"harm_ok": True}, {"n": held_n(sl, d), "hits": 0}, {"n": held_n(sl, d), "hits": 1}), [])
            self.assertEqual(sl.items["note|m1"].qa + sl.items["note|m2"].qa, [x for x in sl.items["note|m1"].qa + sl.items["note|m2"].qa if x[1] in ("Emma", "Tomas")])
        finally:
            env.close()

    def test_note_card_is_stable_across_nights(self):
        env = Env(days=(("2026-10-20", ["ok thanks"]),))
        try:
            write_memory(env, self.NOTES[:1])
            sl, week, d = stage_sleeper(env)
            sl.extras(week, d, Counter())
            sl.top_up_holdout(d, Counter())
            it = sl.items["note|m1"]
            held = list(it.held)
            self.assertEqual(len(held), 1)
            sl.save_items()
            calls = []
            sl2, _, _ = stage_sleeper(env)
            sl2.gen = lambda *a, **k: calls.append(a) or []        # a regenerated card would call the model
            st = Counter()
            sl2.extras(week, d + 1, st)
            self.assertEqual(calls, [])
            self.assertEqual(sl2.items["note|m1"].held, held)
            self.assertEqual((st["note_new"], st["note_changed"], st["note_qa_kept"]), (0, 0, 0))
            write_memory(env, [dict(self.NOTES[0], text="My sister is Anna")])      # the note changes: a new card
            sl2.gen = sl.gen
            st = Counter()
            sl2.extras(week, d + 1, st)
            self.assertEqual((st["note_changed"], st["note_qa_kept"]), (1, 1))
            self.assertEqual(sl2.items["note|m1"].qa[0][1], "Anna")
        finally:
            env.close()


class CardNoteTests(unittest.TestCase):
    CARD = {"id": "c1", "text": "I => is applying to => Duke", "topic": "Card"}

    def test_card_lines_skip_note_cards(self):
        env = Env(days=(("2026-10-20", ["ok thanks"]),))
        try:
            write_memory(env, [{"id": "m3", "text": "Marta => works at => Orbix; Lena => owns => Sunbird", "topic": "stuff"}])
            sl, week, d = stage_sleeper(env)
            st = Counter()
            sl.extras(week, d, st)
            self.assertEqual((st["note_qa_skipped_card_lines"], st["note_qa_kept"]), (1, 0))
            self.assertEqual(sl.items["note|m3"].qa, [])
        finally:
            env.close()

    def test_card_note_becomes_a_fact_and_retires_with_the_note(self):
        env = Env(days=(("2026-10-20", ["ok thanks"]),))
        try:
            write_memory(env, [self.CARD])
            sl, week, d = stage_sleeper(env)
            st = Counter()
            sl.card_notes(d, st)
            sl.refresh(d)
            it = next(it for it in sl.items.values() if it.card_note_id == self.CARD["id"])
            self.assertEqual((it.kind, it.subj, it.obj, it.rel, it.source), ("fact", "Ben", "Duke", "is applying to", "saved card note"))
            sl.extras(week, d, st)
            self.assertFalse([k for k in sl.items if k.startswith("note|")])         # no note paraphrase or quiz for it
            E = [x for x in sl.items.values() if sl.elig(x)]
            st2 = Counter()
            fresh = sl.dream(d, E, st2)
            self.assertIn(it, fresh)
            self.assertGreaterEqual(len(it.para) + len(it.qa), 2)
            sl.split_holdout(fresh, d, st2)
            self.assertGreaterEqual(held_n(sl, d), 1)
            sl.save_items()
            sl2, _, _ = stage_sleeper(env)
            sl2.card_notes(d + 1, Counter())                                         # next night: still there, not re-made
            self.assertEqual((sl2.items[it.key].born, sl2.items[it.key].dead), (d, False))
            write_memory(env, [])
            st3 = Counter()
            sl2.card_notes(d + 1, st3)
            self.assertTrue(sl2.items[it.key].dead)
            self.assertEqual(st3["card_retired"], 1)
        finally:
            env.close()


class LogTests(unittest.TestCase):
    def test_last_step_and_quiz_are_logged(self):
        env = Env()
        try:
            res = env.sleeper(env.backend()).run(env.week())
            n = res["steps_total"]
            self.assertTrue(any(l.startswith("[night] step %d/%d " % (n, n)) for l in env.logs), env.logs[-8:])
            self.assertIn("[night] quiz", env.logs)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
