"""Corrections, lessons, habits, saved notes and the tracking list (lessons.py and its use in recipe.py). Linux, fake model."""
import json
import unittest
from collections import Counter
from pathlib import Path

from sleepmlx import diary as diary_mod
from sleepmlx import lessons as L
from sleepmlx.paths import read_json

from .helpers import FACTS_DAY1, Env, write_raw

SYS = {"role": "system", "content": "You are the Desk."}


def desk_rec(user, answer, ts, history=(), tools=None, checks=None, stopped=False, extra_msgs=()):
    """A record as the Desk gateway writes it (src/gateway.js diaryRecord), with the new optional fields."""
    r = {"ts": ts, "model": "main", "messages": list(history) + [{"role": "user", "content": user}] + list(extra_msgs), "response": {"content": answer}}
    if tools:
        r["tools"] = tools
    if checks:
        r["checks"] = checks
    if stopped:
        r["stopped"] = True
    return r


def write_recs(raw: Path, date: str, recs):
    raw.mkdir(parents=True, exist_ok=True)
    with open(str(raw / (date + ".jsonl")), "a") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def chat(turns, ts0=1_700_100_000.0):
    """[(user, answer, kw)] -> Desk records carrying the history, like a real thread."""
    out, hist = [], []
    for k, (u, a, kw) in enumerate(turns):
        out.append(desk_rec(u, a, ts0 + k, history=hist, **kw))
        hist = hist + [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    return out


def step(name, args, ok=True, result="done"):
    return {"name": name, "args": json.dumps(args), "ok": ok, "result": result}


class DiaryMetaTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(days=())

    def tearDown(self):
        self.env.close()

    def test_desk_fields_reach_the_week_and_secrets_stay_out(self):
        raw = self.env.paths.diary_dir
        write_recs(raw, "2026-10-22", chat([
            ("Open my Canvas grades", "Done.", {"tools": [step("browser_go", {"url": "https://canvas.example.edu/grades"}),
                                                           step("browser_click", {"id": 4}, ok=False, result="Error: element 4 is gone"),
                                                           step("browser_type", {"id": 2, "text": "password hunter2"})],
                                                 "checks": ["Not done yet: the grades page did not load."]}),
            ("Find the bus times", "", {"stopped": True}),
        ]))
        week = diary_mod.build_week(raw, "Ben")
        users = [r for r in week["diary"] if r["role"] == "user"]
        self.assertEqual([u["text"] for u in users], ["Open my Canvas grades", "Find the bus times"])
        t = users[0]["tools"]
        self.assertEqual([x["name"] for x in t], ["browser_go", "browser_click", "browser_type"])
        self.assertEqual([x["ok"] for x in t], [True, False, True])
        self.assertNotIn("hunter2", json.dumps(week))                     # looks_secret / talks_secrets still filter
        self.assertEqual(users[0]["checks"], ["Not done yet: the grades page did not load."])
        self.assertTrue(users[1]["stopped"])
        self.assertNotIn("tools", users[1])

    def test_self_check_and_screenshot_messages_are_not_bens_turns(self):
        raw = self.env.paths.diary_dir
        hist = [{"role": "user", "content": "Book the dentist"}, {"role": "assistant", "content": "Booked."}]
        write_recs(raw, "2026-10-22", [desk_rec("[Self-check] Not done yet: no confirmation on the page.", "Now it is booked.", 1_700_100_000.0, history=hist)])
        week = diary_mod.build_week(raw, "Ben")
        users = [r for r in week["diary"] if r["role"] == "user"]
        self.assertEqual([u["text"] for u in users], ["Book the dentist"])
        self.assertEqual(users[0]["checks"], ["Not done yet: no confirmation on the page."])

    def test_mac_gateway_format_reads_tool_calls_from_the_messages(self):
        msgs = [SYS, {"role": "user", "content": "What's the weather in Dalmore?"},
                {"role": "assistant", "content": "", "tool_calls": [{"id": "a", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\": \"Dalmore weather\"}"}}]},
                {"role": "tool", "tool_call_id": "a", "content": "Error: search timed out"},
                {"role": "assistant", "content": "", "tool_calls": [{"id": "b", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\": \"Dalmore weather\"}"}}]},
                {"role": "tool", "tool_call_id": "b", "content": "Sunny, 14 C"}]
        got = diary_mod.record_turn_meta({"ts": 1, "model": "k2-main", "conv_id": "c", "messages": msgs, "response": {"content": "Sunny."}, "status": "ok"}, Path("/x"))
        self.assertEqual(got[1], "What's the weather in Dalmore?")
        self.assertEqual([(t["name"], t["ok"]) for t in got[3]["tools"]], [("web_search", False), ("web_search", True)])
        # the old 3-tuple API is unchanged
        self.assertEqual(diary_mod._record_turn({"ts": 1, "messages": msgs, "response": {"content": "Sunny."}}, Path("/x"))[1:], ("What's the weather in Dalmore?", "Sunny."))


class FailureTests(unittest.TestCase):
    def week(self, rows):
        diary = []
        for k, (u, a, extra) in enumerate(rows):
            r = {"day": 1, "session": 0, "turn": k, "role": "user", "text": u, "mentions": []}
            r.update(extra)
            diary.append(r)
            if a:
                diary.append({"day": 1, "session": 0, "turn": k, "role": "assistant", "text": a, "mentions": []})
        return {"diary": diary, "dates": {"1": "2026-10-22"}}

    def test_kinds(self):
        w = self.week([
            ("Where does Marta work?", "Marta works at Orbix.", {}),
            ("No, it's Kestrel now.", "Sorry, Kestrel.", {}),
            ("No thanks, that's all", "Okay.", {}),
            ("Open Canvas", "I couldn't open it.", {"tools": [step("open_app", {"name": "Canvas"}, ok=False, result="Error: not installed")]}),
            ("Find the bus times", "I could not find them.", {}),
            ("Check the order", "", {"stopped": True}),
            ("Book the dentist", "Booked.", {"checks": ["Not done yet: no confirmation."]}),
            ("What's wrong with my code?", "A missing bracket.", {}),
        ])
        f = L.find_failures(w, 1)
        self.assertEqual([(x["turn"], x["kind"]) for x in f], [(1, "correction"), (3, "tool_error"), (4, "gave_up"), (5, "stopped"), (6, "self_check")])
        self.assertIn("gave_up", f[1]["signals"])
        ctx = L.failure_context(f[0])
        self.assertIn("Glim: Marta works at Orbix.", ctx)
        self.assertIn("Ben then said: No, it's Kestrel now.", ctx)

    def test_correction_words(self):
        for t in ("That's wrong, it's Tuesday", "no, it is room 12", "Actually it's at 4pm", "you got it wrong", "Not quite, the Kestrel office"):
            self.assertTrue(L.is_correction(t), t)
        for t in ("No", "No thanks", "no worries", "nothing wrong here", "Remember my locker is 112"):
            self.assertFalse(L.is_correction(t), t)
        self.assertEqual(L.not_terms("Marta works at Kestrel, not Orbix. Room 12 not 9"), ["Orbix", "9"])

    def test_lesson_checks(self):
        f = {"kind": "correction", "user": "No, it's Kestrel now."}
        good = {"did": "said Orbix", "wrong": "old fact", "instead": "use the newest", "q": "Where does Marta work now?", "a": "Kestrel", "wrong_value": "Orbix"}
        self.assertIsNone(L.lesson_ok(good, f, "ctx", set()))
        self.assertEqual(L.lesson_ok(dict(good, a="Orbix"), f, "Orbix", set()), "answer_not_in_chat")   # a correction's answer must be in Ben's words
        self.assertEqual(L.lesson_ok(dict(good, a="Kestrel"), f, "", {"kestrel"}), "answer_is_the_wrong_value")
        self.assertEqual(L.lesson_ok(dict(good, q="Is Kestrel right?"), f, "", set()), "answer_in_question")
        self.assertEqual(L.lesson_ok(dict(good, instead="ask for the password"), f, "", set()), "secret")
        self.assertEqual(L.scrub("Glim said Orbix. It is Kestrel.", {"Orbix"}), "Glim said the wrong answer. It is Kestrel.")


class HabitAndFileTests(unittest.TestCase):
    def test_habits_need_three_turns(self):
        rows = []
        for k in range(4):
            tools = [step("browser_go", {"url": "https://www.canvas.example.edu/x%d" % k}), step("browser_read", {})]
            if k < 2:
                tools.append(step("run_shell", {"command": "git status"}))
            rows.append({"day": 1 + k // 2, "turn": k, "role": "user", "text": "t%d" % k, "tools": tools})
        rows.append({"day": 3, "turn": 0, "role": "user", "text": "x", "tools": [step("browser_go", {"url": "https://canvas.example.edu"}, ok=False)]})
        hs = L.habits({"diary": rows}, upto=2)
        self.assertEqual([(h["cat"], h["target"], h["n"], h["days"]) for h in hs], [("website", "canvas.example.edu", 4, 2)])
        para, qa = L.habit_cards(hs[0])
        self.assertEqual(qa, [["Which website does Ben most often have Glim open?", "canvas.example.edu"]])
        self.assertEqual(L.habits({"diary": rows}, upto=1), [])

    def test_tracking_and_notes_files(self):
        env = Env(days=())
        try:
            ud = env.paths.user_data
            ud.mkdir(parents=True)
            (ud / "tracking.md").write_text("# Keeping track of\n\n## Active\n"
                                            "- [ ] Calculator order | source: Amazon | until: 2026-11-02 | added: 2026-10-20\n"
                                            "- [ ] Old parcel | source: UPS | until: 2026-10-01 | added: 2026-09-20\n"
                                            "- [ ] Wifi password reset | source: router | until: | added: 2026-10-20\n"
                                            "- [ ] Field trip form | source:  | until:  | added: 2026-10-21\n\n"
                                            "## Done\n- [x] Library book | source: school | until: 2026-10-10 | added: 2026-10-01 | done: 2026-10-09\n")
            (ud / "memory.json").write_text(json.dumps({"facts": [{"id": "m1", "text": "Ben takes AP Chem 4th period", "topic": "school", "updated": 1761400000000},
                                                                  {"id": "m2", "text": "Locker pin is 4421", "updated": 1761400000000}]}))
            items = L.read_tracking(ud, "2026-10-28")
            self.assertEqual([i["what"] for i in items], ["Calculator order", "Field trip form"])   # expired, done and secret ones are out
            para, qa = L.track_cards(items[0])
            self.assertEqual(para, ["Ben is keeping track of Calculator order (from Amazon, until 2026-11-02)."])
            self.assertEqual([a for _, a in qa], ["Amazon", "2026-11-02"])
            self.assertEqual(L.track_cards(items[1])[1], [])
            notes = L.read_notes(ud, diary_mod.load_ignore(None))
            self.assertEqual([n["id"] for n in notes], ["m1"])
            self.assertEqual(L.read_notes(ud, [__import__("re").compile("AP Chem", 2)]), [])        # ignore.txt applies too
        finally:
            env.close()


class NightTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def cards(self):
        return [json.loads(l) for l in self.env.paths.cards.read_text().splitlines()]

    def test_correction_retires_the_old_fact_and_becomes_a_lesson(self):
        e = self.env
        res1 = e.sleeper(e.backend()).run(e.week())
        self.assertEqual(res1["status"], "done", res1)
        self.assertTrue(any("Orbix" in json.dumps(c) and "Marta" in json.dumps(c) for c in self.cards()))
        write_recs(e.paths.diary_dir, "2026-10-21", chat([
            ("Where does Marta work these days?", "Marta works at Orbix.", {}),
            ("No, it's Kestrel. Marta works at Kestrel, not Orbix.", "Got it, Kestrel.", {}),
            ("Tomas is the mentor of Pavel", "Noted.", {}),
        ], ts0=1_700_200_000.0))
        be = e.backend()
        res = e.sleeper(be).run(e.week())
        self.assertEqual(res["status"], "done", res)
        items = read_json(e.paths.items)
        self.assertTrue(items["items"]["marta|orbix"]["dead"])
        self.assertIn("marta|orbix", items["dropped"])
        self.assertIn("orbix", items["wrong"]["marta"])
        self.assertTrue(items["items"]["marta|kestrel"]["cor"])
        cards = self.cards()
        facts = [c for c in cards if c["kind"] in ("paraphrase", "qa") and "Marta" in json.dumps(c)]
        self.assertTrue(facts)
        self.assertFalse(any("Orbix" in json.dumps(c) for c in facts), facts)        # no positive card for the wrong claim
        lessons = [c for c in cards if c["kind"].startswith("lesson")]
        self.assertEqual({c["kind"] for c in lessons}, {"lesson", "lesson_qa"})
        self.assertTrue(all("2026-10-21" in c["source"] and "corrected" in c["source"] for c in lessons))
        self.assertFalse(any("Orbix" in json.dumps(c) for c in lessons))             # scrubbed: "the wrong answer"
        self.assertEqual([c["a"] for c in lessons if c["kind"] == "lesson_qa"], ["Kestrel"])
        self.assertEqual(len(res["lessons"]), 1)
        self.assertIn("Next time:", res["lessons"][0])
        self.assertTrue(any("Lesson from 2026-10-21" in p for p in be.prompts_trained))   # trained like other cards
        night = [json.loads(l) for l in e.paths.nights.read_text().splitlines()][-1]
        self.assertEqual(night["lessons"], res["lessons"])
        self.assertGreaterEqual(night["stats"]["tagging"]["superseded"], 1)

    def sleeper_on(self, users, date="2026-10-22"):
        """A sleeper with the night state set up for day 1 (to call one stage directly)."""
        e = self.env
        sl = e.sleeper(e.backend())
        week = e.week()
        sl.load_items()
        sl.N = {"date": "2026-10-20", "lessons": []}
        sl.set_scale(1.0)
        from sleepmlx.corpus import Diary
        from sleepmlx.recipe import GenCache
        sl.diary, sl.cache = Diary(week), GenCache(None)
        return sl, week

    def test_lessons_are_capped_per_night(self):
        e = Env(days=(), max_lessons=2)
        try:
            turns = [("please open %s" % n, "I couldn't open %s." % n, {"tools": [step("open_app", {"name": n}, ok=False, result="Error: not found")]})
                     for n in ("Canvas", "Spotify", "Zoom", "Teams")]
            write_recs(e.paths.diary_dir, "2026-10-20", chat(turns))
            be = e.backend()
            sl = e.sleeper(be)
            week = e.week()
            sl.load_items()
            sl.N = {"date": "2026-10-20"}
            sl.set_scale(1.0)
            from sleepmlx.corpus import Diary
            from sleepmlx.recipe import GenCache
            sl.diary, sl.cache = Diary(week), GenCache(None)
            st = Counter()
            sl.lessons_stage(week, 1, st)
            self.assertEqual(st["failures"], 4)
            self.assertEqual(st["lessons_kept"], 2)
            kept = [it for it in sl.items.values() if it.kind == "lesson"]
            self.assertEqual(sorted(it.obj for it in kept), ["Canvas", "Spotify"])
            self.assertTrue(all(it.imp and it.cor and it.qa for it in kept))
        finally:
            e.close()

    def test_habits_notes_and_tracking_become_cards_with_source_and_expiry(self):
        e = self.env
        ud = e.paths.user_data
        ud.mkdir(parents=True)
        (ud / "tracking.md").write_text("## Active\n- [ ] Calculator order | source: Amazon | until: 2026-11-02 | added: 2026-10-20\n"
                                        "- [ ] Old parcel | source: UPS | until: 2026-10-01 | added: 2026-09-20\n")
        (ud / "memory.json").write_text(json.dumps({"facts": [{"id": "m1", "text": "Ben's bus is the 41", "updated": 1761400000000}]}))
        write_recs(e.paths.diary_dir, "2026-10-19", chat([("Open grades %d" % k, "Opened.", {"tools": [step("browser_go", {"url": "https://canvas.example.edu"})]})
                                                          for k in range(3)], ts0=1_699_900_000.0))
        sl, week = self.sleeper_on(None)
        sl.today = lambda: "2026-10-28"
        st = Counter()
        sl.extras(week, 2, st)
        kinds = {k.split("|")[0] for k, it in sl.items.items() if not it.dead}
        self.assertEqual(kinds, {"habit", "note", "track"})
        tr = sl.items["track|calculator order"]
        self.assertEqual((tr.source, tr.until), ("Amazon", "2026-11-02"))
        self.assertNotIn("track|old parcel", sl.items)
        self.assertTrue(sl.elig(tr))
        sl.today = lambda: "2026-11-03"                       # a night after the until date: not trained any more
        self.assertFalse(sl.elig(tr))
        sl.today = lambda: "2026-10-28"
        sl.write_cards()
        rows = [json.loads(l) for l in e.paths.cards.read_text().splitlines()]
        tq = [r for r in rows if r["kind"] == "track_qa"]
        self.assertEqual({r["a"] for r in tq}, {"Amazon", "2026-11-02"})
        self.assertTrue(all(r["source"] == "Amazon" and r["until"] == "2026-11-02" for r in tq))
        self.assertTrue(any(r["kind"] == "habit_qa" and r["a"] == "canvas.example.edu" for r in rows))
        self.assertTrue(any(r["kind"] == "note" and "the 41" in r["text"] and r["source"].startswith("saved note") for r in rows))
        # Ben marks it done in the Desk and forgets the note: both leave the pool
        (ud / "tracking.md").write_text("## Active\n\n## Done\n- [x] Calculator order | source: Amazon | until: 2026-11-02 | added: 2026-10-20 | done: 2026-10-27\n")
        (ud / "memory.json").write_text(json.dumps({"facts": []}))
        st = Counter()
        sl.extras(week, 2, st)
        self.assertTrue(sl.items["track|calculator order"].dead and sl.items["note|m1"].dead)
        self.assertEqual((st["track_retired"], st["note_retired"]), (1, 1))

    def test_worker_reads_the_userdata_folder_from_env(self):
        from sleepmlx import worker
        e = self.env
        write_raw(e.paths.diary_dir, "2026-10-20", FACTS_DAY1)
        env = {"SLEEPMLX_HOME": str(e.paths.home), "SLEEPMLX_DIARY_DIR": str(e.paths.diary_dir), "LEARNER_OPS": str(e.paths.ops),
               "SLEEPMLX_USERDATA": str(e.paths.user_data), "SLEEPMLX_SCALE": "1", "SLEEPMODE_BUDGET_S": "100000", "SLEEPMLX_PROFILE": "k2"}
        p = worker._paths_from(env)
        self.assertEqual(p.userdata_dir, e.paths.user_data)


if __name__ == "__main__":
    unittest.main()
