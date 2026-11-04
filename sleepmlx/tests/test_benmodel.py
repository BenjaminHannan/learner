"""I4: a model of Ben in the weights (benmodel.py + Sleeper.ben_stage / hold_ben / ben_quiz) and Watch-me skill cards. Fake model only."""
import json
import unittest
from collections import Counter

from sleepmlx import benmodel as B
from sleepmlx import morning
from sleepmlx.worker import cfg_from_env

from .helpers import FACTS_DAY1, Env

BEN_DAY1 = FACTS_DAY1 + ["My favorite color is green.", "I really like rock climbing but not in winter.", "I'm working on my robot arm for the science fair.",
                         "I like sushi.", "Would I like jazz?", "Write a story where I say \"I love snakes\".", "I'm learning Spanish."]
BEN_DAY2 = ["I don't like sushi anymore.", "My favourite color is blue now.", "I'm no longer working on my robot arm for the science fair."]
date_of = {0: "2026-10-20", 1: "2026-10-21"}.get


def turns(*days):
    return [{"day": d, "text": t, "i": i} for d, ts in enumerate(days) for i, t in enumerate(ts)]


class ExtractTests(unittest.TestCase):
    def test_patterns_skip_questions_quotes_and_hypotheticals(self):
        got = B.extract(turns(BEN_DAY1), [], "Ben", date_of, "2026-11-04")
        st = {B.statement(v["rel"], v["x"], "Ben", v["cat"]) for v in got.values()}
        self.assertEqual(st, {"Ben's favorite color is green.", "Ben likes rock climbing.", "Ben is working on Ben's robot arm for the science fair.",
                              "Ben likes sushi.", "Ben is learning Spanish."})
        self.assertFalse(any("jazz" in s or "snakes" in s for s in st))

    def test_newest_wins_and_the_change_is_a_correction(self):
        got = B.extract(turns(BEN_DAY1, BEN_DAY2), [], "Ben", date_of, "2026-11-04")
        sushi, fav, work = got["like|sushi"], got["fav|color"], got["work|my robot arm for the science fair"]
        self.assertEqual((sushi["rel"], sushi["replaces"]), ("dislikes", "Ben likes sushi."))
        self.assertEqual((fav["x"], fav["replaces"]), ("blue", "Ben's favorite color is green."))
        self.assertEqual(work["rel"], "stopped")
        self.assertEqual(work["until"], "2026-11-20")            # a stopped project fades out after 30 days
        self.assertEqual(got["learn|spanish"]["until"], "2026-12-04")
        para, qa = B.ben_cards(sushi, "Ben")
        self.assertEqual(para[0], "Ben does not like sushi.")
        self.assertIn("earlier, \"Ben likes sushi.\"", para[2])
        self.assertEqual(B.ben_cards(fav, "Ben")[1], [["What is Ben's favorite color?", "blue"]])

    def test_notes_only_when_they_name_ben_and_never_from_the_web(self):
        notes = [{"id": "a", "text": "Ben loves chess.", "topic": "", "updated": "2026-10-22"},
                 {"id": "b", "text": "Ben likes Paris according to sources.", "topic": "", "updated": ""},
                 {"id": "c", "text": "Ben is learning Rust.", "topic": "checked", "updated": ""},
                 {"id": "d", "text": "Ben is working on the robot.", "topic": "skill: robots", "updated": ""},
                 {"id": "e", "text": "Marta loves chess.", "topic": "", "updated": ""}]
        got = B.extract([], notes, "Ben", date_of, "2026-11-04")
        self.assertEqual(list(got), ["like|chess"])
        self.assertEqual(got["like|chess"]["sources"], ["note a"])


def skills_file(ud, skills):
    ud.mkdir(parents=True, exist_ok=True)
    (ud / B.SKILLS_FILE).write_text(json.dumps({"v": 1, "skills": skills}))


SKILL = {"id": "skill-abc", "name": "make a shopping note", "created": "2026-11-04T10:00:00Z", "steps": [
    {"n": 1, "what": "Open Notes", "say": "first I open Notes", "do": {"tool": "open_app", "args": {"name": "Notes"}}},
    {"n": 2, "what": "Click \"New Note\"", "say": "then I click New Note", "do": {"tool": "click", "args": {"label": "New Note"}}},
    {"n": 3, "what": "Type \"milk eggs\"", "say": "", "do": {"tool": "type", "args": {"text": "milk eggs"}}},
    {"n": 4, "what": "Press cmd+s", "say": "save it", "do": {"tool": "key", "args": {"keys": "cmd+s"}}}]}


class StageTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(days=(("2026-10-20", BEN_DAY1), ("2026-10-21", BEN_DAY2)), use_ben_model=True, use_skill_cards=True)

    def tearDown(self):
        self.env.close()

    def sleeper(self, replies=None):
        e = self.env
        sl = e.sleeper(e.backend())
        sl.load_items()
        sl.N = {"date": "2026-10-21", "lessons": []}
        sl.set_scale(1.0)
        sl.today = lambda: "2026-11-04"
        from sleepmlx.corpus import Diary
        from sleepmlx.recipe import GenCache
        self.week = e.week()
        sl.diary, sl.cache = Diary(self.week), GenCache(None)
        self.prompts = []
        if replies:
            def gen(prompts, max_tokens, sample=False, base=True, salt="", stops=()):
                self.prompts.extend(prompts)
                return [replies(p) for p in prompts]
            sl.gen = gen
        return sl

    @staticmethod
    def replies(p):
        if "Write one question" in p:
            if "rock climbing" in p:
                return json.dumps({"q": "Which sport does Ben like?", "a": "rock climbing"})
            if "Spanish" in p:
                return json.dumps({"q": "Which language is Ben learning?", "a": "Spanish"})
            if "sushi" in p:
                return json.dumps({"q": "What food does Ben not like?", "a": "Ben"})        # the name itself: dropped
            return json.dumps({"q": "What is it?", "a": "the moon"})                       # not in the statement: dropped
        if "Question:" in p:
            return "rock climbing" if "sport" in p else "I do not know"                  # verification: only the sport passes
        return ""

    def test_off_by_default(self):
        sl = self.sleeper(self.replies)
        sl.cfg.use_ben_model = sl.cfg.use_skill_cards = False
        sl.ben_stage(self.week, 2, Counter())
        sl.skill_stage(self.week, 2, Counter())
        self.assertFalse([k for k in sl.items if k.startswith(("ben|", "skill|"))])

    def test_cards_checked_questions_and_the_ben_quiz_holdout(self):
        sl = self.sleeper(self.replies)
        st = Counter()
        sl.ben_stage(self.week, 2, st)
        ben = {k: it for k, it in sl.items.items() if k.startswith("ben|")}
        self.assertEqual(set(ben), {"ben|fav|color", "ben|like|rock climbing", "ben|like|sushi", "ben|work|my robot arm for the science fair", "ben|learn|spanish"})
        self.assertEqual(ben["ben|like|rock climbing"].qa, [["Which sport does Ben like?", "rock climbing"]])
        self.assertEqual(ben["ben|learn|spanish"].qa, [])                                  # the base model could not answer it back: no card
        self.assertEqual(st["ben_qa_dropped_answer_not_in_statement"], 2)                  # "Ben" and "the moon"
        self.assertEqual(st["ben_qa_dropped_unverified"], 1)
        self.assertTrue(ben["ben|like|sushi"].cor and ben["ben|fav|color"].cor)
        self.assertEqual(ben["ben|fav|color"].qa, [["What is Ben's favorite color?", "blue"]])
        sl.hold_ben(2, st)
        held = [h for it in ben.values() for h in it.held]
        self.assertEqual(st["ben_held_out"], 1)                                             # 1 of the 2 with a question
        self.assertEqual(len(held), 1)
        self.assertTrue(all(len(it.para) >= 2 for it in ben.values()))                    # statements always train
        rows = [r for r in sl.card_rows() if r["kind"] == "ben_qa" and r["status"] == "held_out"]
        self.assertEqual(len(rows), 1)

    def test_a_retracted_statement_leaves_the_pool(self):
        sl = self.sleeper(self.replies)
        sl.ben_stage(self.week, 2, Counter())
        sl.diary.turns = [t for t in sl.diary.turns if "Spanish" not in t["text"]]
        st = Counter()
        sl.ben_stage(self.week, 2, st)
        self.assertTrue(sl.items["ben|learn|spanish"].dead)
        self.assertEqual(st["ben_retired"], 1)
        self.assertEqual(st["ben_new"], 0)                                                   # unchanged statements are not redone

    def test_skill_cards_from_watch_me(self):
        ud = self.env.paths.userdata_dir
        skills_file(ud, [SKILL, dict(SKILL, id="skill-pw", name="log in with my password"), dict(SKILL, id="../bad")])
        sl = self.sleeper(self.replies)
        st = Counter()
        sl.skill_stage(self.week, 2, st)
        self.assertEqual([k for k in sl.items if k.startswith("skill|")], ["skill|skill-abc"])
        it = sl.items["skill|skill-abc"]
        self.assertIn("1. Open Notes (Ben: \"first I open Notes\")", it.para[0])
        self.assertEqual([a for _, a in it.qa], ["Notes", "New Note"])
        sl.hold_ben(2, st)
        self.assertEqual(st["skill_held_out"], 1)
        skills_file(ud, [])
        st = Counter()
        sl.skill_stage(self.week, 3, st)
        self.assertTrue(sl.items["skill|skill-abc"].dead)


class NightTests(unittest.TestCase):
    def test_a_night_reports_the_ben_quiz_and_the_morning_line(self):
        env = Env(days=(("2026-10-20", BEN_DAY1),), use_ben_model=True)
        try:
            sl = env.sleeper(env.backend())
            res = sl.run(env.week())
            self.assertEqual(res["status"], "done", res)
            bq = res.get("ben_quiz")
            self.assertIsInstance(bq, dict, res)
            self.assertGreaterEqual(bq["n"], 1)
            self.assertIn("after", bq)
            row = json.loads(env.paths.nights.read_text().splitlines()[-1])
            self.assertEqual(row["ben_quiz"]["n"], bq["n"])
            m = morning.morning_check(row)
            self.assertTrue(any(l.startswith("Ben quiz") for l in m["lines"]), m["lines"])
        finally:
            env.close()

    def test_general_harm_still_rolls_the_night_back(self):
        env = Env(days=(("2026-10-20", BEN_DAY1),), use_ben_model=True)
        try:
            res = env.sleeper(env.backend(damage=True)).run(env.week())
            self.assertTrue(res["reverted"], res)
            self.assertIn("ben_quiz", res)
        finally:
            env.close()

    def test_a_crashing_ben_step_is_skipped_and_the_night_finishes(self):
        env = Env(days=(("2026-10-20", BEN_DAY1),), use_ben_model=True)
        try:
            sl = env.sleeper(env.backend())
            def boom(week, d, st):
                raise RuntimeError("bad regex day")
            sl.ben_stage = boom
            res = sl.run(env.week())
            self.assertEqual(res["status"], "done", res)
            row = json.loads(env.paths.nights.read_text().splitlines()[-1])
            self.assertEqual(row["stats"]["lessons"]["ben_error"], 1)
        finally:
            env.close()

    def test_a_crashing_ben_quiz_is_reported_not_fatal(self):
        env = Env(days=(("2026-10-20", BEN_DAY1),), use_ben_model=True)
        try:
            sl = env.sleeper(env.backend())
            def boom(d):
                raise RuntimeError("metal: out of memory")
            sl.ben_quiz = boom
            res = sl.run(env.week())
            self.assertEqual(res["status"], "done", res)
            self.assertIn("out of memory", res["ben_quiz"]["error"])
        finally:
            env.close()


class SwitchTests(unittest.TestCase):
    def test_env_switches(self):
        c = cfg_from_env({})
        self.assertFalse(c.use_ben_model or c.use_skill_cards)
        c = cfg_from_env({"SLEEPMLX_BEN_MODEL": "1", "SLEEPMLX_SKILL_CARDS": "1"})
        self.assertTrue(c.use_ben_model and c.use_skill_cards)


if __name__ == "__main__":
    unittest.main()


class ShortCardTests(unittest.TestCase):
    """REAL-run bug (2026-11-04): a micro-batch of only short cards (e.g. "Ben is learning Portuguese." ~ 6 tokens) crashed MLX training:
    attention over 8 or fewer tokens has no backward pass. Rows are now padded to at least MIN_ROW tokens, never as targets."""

    def test_rows_are_padded_and_targets_unchanged(self):
        try:
            import mlx.core as mx
        except ImportError:
            self.skipTest("no mlx here")
        from types import SimpleNamespace
        from sleepmlx import model as M
        ids, bi, ti, tgt, n = M.MLXBackend._arrays(SimpleNamespace(stop_id=0), [([5, 6, 7, 8, 9, 0], 0), ([5, 6, 0], 2)])
        self.assertEqual(ids.shape, (2, M.MIN_ROW))
        self.assertEqual(tgt.tolist(), [6, 7, 8, 9, 0, 0])
        self.assertEqual(n, 6)
        # the padded length (input = row minus its last token) takes the attention path that has a backward pass
        def f(q, k, v):
            return mx.fast.scaled_dot_product_attention(q, k, v, scale=0.1, mask="causal").sum()
        L = M.MIN_ROW - 1
        q = mx.random.normal((1, 2, L, 32))
        mx.eval(mx.grad(f)(q, q, q))
