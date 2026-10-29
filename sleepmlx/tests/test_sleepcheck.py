"""Dream check, served check, GGUF rotation (all offline)."""
import json
import tempfile
import unittest
from pathlib import Path

from sleepmlx import dreamhook, export, served
from .helpers import Env


class DreamCheckTests(unittest.TestCase):
    def test_contradicted_cards_are_dropped_and_logged(self):
        env = Env()
        try:
            seen = []

            def checker(item):
                seen.append(item)
                return "CONTRADICTED" if len(seen) == 1 else "SUPPORTED"
            sl = env.sleeper(env.backend())
            sl.dream_checker = checker
            r = sl.run(env.week())
            self.assertEqual(r["status"], "done")
            self.assertGreater(len(seen), 1)
            first = seen[0]
            cards = [json.loads(l) for l in env.paths.cards.read_text().splitlines()]
            self.assertFalse(any(c.get("q") == first["question"] and c.get("a") == first["answer"] for c in cards))
            log = [json.loads(l) for l in (env.paths.home / "dreamcheck.jsonl").read_text().splitlines()]
            self.assertEqual(log[0]["verdict"], "CONTRADICTED")
            night = [json.loads(l) for l in env.paths.nights.read_text().splitlines()][-1]
            self.assertEqual(night["stats"]["dreamcheck"]["contradicted"], 1)
            self.assertEqual(night["stats"]["dreamcheck"]["dropped"], 1)
        finally:
            env.close()

    def test_missing_checker_is_reported_not_fatal(self):
        from unittest import mock
        with mock.patch.dict("sys.modules", {"sleepmode.dreamcheck": None, "sleepmode.tools": None}):   # sleepmode is on main now: hide it
            r = dreamhook.check([{"q": "Q?", "a": "A"}], None, "/nowhere", 100, env={"SLEEPMLX_DREAMCHECK_PATH": "/nonexistent"})
        self.assertFalse(r["stats"]["available"])
        self.assertEqual(list(r["verdicts"].values()), ["UNCHECKED"])

    def test_time_cap_and_cache(self):
        t = [0.0]

        def now():
            return t[0]

        def checker(item):
            t[0] += 10
            return "SUPPORTED"
        cache = {}
        rows = [{"q": "q%d" % i, "a": "a"} for i in range(5)]
        r = dreamhook.check(rows, None, "", 25, now=now, checker=checker, cache=cache)
        self.assertEqual(r["stats"]["supported"], 3)
        self.assertEqual(r["stats"]["unchecked"], 2)
        r2 = dreamhook.check(rows, None, "", 0, now=now, checker=checker, cache=cache)
        self.assertEqual(r2["stats"]["cached"], 3)

    def test_local_chat_renders_turns_without_thinking(self):
        from sleepmlx.profile import load_profile

        class BE:
            def generate(self, prompts, n, temp, adapter=True):
                self.p, self.n, self.adapter = prompts[0], n, adapter
                return ["VERDICT: UNKNOWN"]
        prof = load_profile("lfm3_cpu")
        prof.template_mode = "manual"
        be = BE()
        out = dreamhook.LocalChat(be, None, prof).chat([{"role": "system", "content": "S"}, {"role": "user", "content": "U"},
                                                       {"role": "assistant", "content": "TOOL: diary_search {}"}, {"role": "user", "content": "RESULT"}], 1500)
        self.assertEqual(out, "VERDICT: UNKNOWN")
        self.assertEqual(be.n, dreamhook.MAX_TOKENS)
        self.assertFalse(be.adapter)
        self.assertTrue(be.p.endswith("<think></think>"))
        self.assertIn("TOOL: diary_search", be.p)


class ServedTests(unittest.TestCase):
    def test_judge(self):
        self.assertTrue(served.judge([True] * 8, [True] * 8, [True], [False])["ok"])
        self.assertTrue(served.judge([True] * 7 + [False], [True] * 8, [], [])["ok"])          # one more wrong is allowed
        self.assertFalse(served.judge([True] * 6 + [False] * 2, [True] * 8, [], [])["ok"])
        self.assertFalse(served.judge([False] * 8, [True] * 8, [], [])["ok"])                  # garbage
        self.assertTrue(served.judge([True] * 3 + [False] * 5, [True] * 3 + [False] * 5, [], [])["ok"])   # a weak base is not the adapter's fault
        self.assertFalse(served.judge([True] * 8, [True] * 8, [False], [True])["ok"])

    def test_served_check_compares_scale_on_and_off(self):
        calls = []

        def asker(url, sys, q, scale, max_tokens=24):
            calls.append(scale)
            if "Marta" in q:
                return "Orbix" if scale == 1.0 else "I don't know"
            return "garbage zzz" if scale == 1.0 else "Paris"
        r = served.served_check("http://x", [{"q": "Where does Marta work?", "a": "Orbix"}], asker=asker)
        self.assertFalse(r["ok"])
        self.assertEqual(r["held_on"], 1)
        self.assertEqual(set(calls), {0.0, 1.0})

    def test_latest_held(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cards.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in [{"status": "held_out", "q": "a?", "a": "A", "night": 1},
                                                            {"status": "held_out", "q": "b?", "a": "B", "night": 2},
                                                            {"status": "trained", "q": "c?", "a": "C", "night": 2}]))
            self.assertEqual([r["a"] for r in served.latest_held(p)], ["B"])

    def test_failed_served_check_restores_previous_gguf(self):
        env = Env(llama_cpp_dir="/l", gguf_base_dir="/hf")
        try:
            env.cfg.llama_server, env.cfg.base_gguf = "/bin/llama-server", "/m.gguf"
            gg = env.paths.home / "adapter.gguf"

            def exporter(llama, base, adapter, out):
                if Path(out).exists():
                    Path(out).replace(export.prev_path(out))
                Path(out).write_text("night%d" % (1 + export.prev_path(out).exists()))
                return True, str(out)
            sl = env.sleeper(env.backend())
            sl.exporter, sl.served_checker = exporter, (lambda *a, **k: {"ok": True, "reasons": []})
            r1 = sl.run(env.week())
            self.assertTrue(r1["served"]["pending"])
            sl.finish_served(r1)
            self.assertTrue(r1["served"]["ok"])
            side = json.loads(export.sidecar_path(gg).read_text())
            self.assertEqual(side["base_hf_id"], env.prof.hf_id)
            from .helpers import write_raw, FACTS_DAY2
            write_raw(env.paths.diary_dir, "2026-10-21", FACTS_DAY2, conv="c2")
            env.cfg.gate_min_gain = 0
            sl2 = env.sleeper(env.backend())
            sl2.exporter, sl2.served_checker = exporter, (lambda *a, **k: {"ok": False, "reasons": ["general 2/8"]})
            r2 = sl2.run(env.week())
            sl2.finish_served(r2)
            self.assertIs(r2["served"]["ok"], False)
            self.assertEqual(r2["served"]["fallback"], "previous adapter.gguf")
            self.assertEqual(gg.read_text(), "night1")
            self.assertTrue(export.sidecar_path(gg).exists())
        finally:
            env.close()

    def test_restore_prev_without_previous_removes_the_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "adapter.gguf"
            g.write_text("x")
            export.sidecar_path(g).write_text("{}")
            self.assertFalse(export.restore_prev(g))
            self.assertFalse(g.exists() or export.sidecar_path(g).exists())


if __name__ == "__main__":
    unittest.main()


class GuardTests(unittest.TestCase):
    def test_one_high_reading_is_not_a_stop(self):
        from sleepmlx.backend import Guards
        lv = [2]
        g = Guards(None, poll_s=0, pressure=lambda: lv[0])
        self.assertIsNone(g.reason())          # a model load spike
        lv[0] = 1
        self.assertIsNone(g.reason())
        lv[0] = 2
        self.assertIsNone(g.reason())
        self.assertEqual(g.reason(), "memory_pressure")   # two polls in a row


class NextDayTests(unittest.TestCase):
    def test_a_small_day_does_not_block_later_days(self):
        from sleepmlx.recipe import next_day
        week = {"dates": {"1": "2026-10-27", "2": "2026-10-28"},
                "diary": [{"role": "user", "day": 1, "text": "a"}, {"role": "user", "day": 2, "text": "b"}, {"role": "user", "day": 2, "text": "c"}]}
        self.assertEqual(next_day(week, {}), (1, "2026-10-27"))
        self.assertEqual(next_day(week, {"small": {"2026-10-27": 1}}), (2, "2026-10-28"))
        self.assertEqual(next_day(week, {"small": {"2026-10-27": 0}}), (1, "2026-10-27"))   # it grew: try again
        self.assertIsNone(next_day(week, {"small": {"2026-10-27": 1, "2026-10-28": 2}}))


class HoldoutTests(unittest.TestCase):
    def test_a_small_night_still_holds_out_cards(self):
        from collections import Counter
        from sleepmlx.recipe import Config, Item, Sleeper
        s = Sleeper.__new__(Sleeper)
        s.cfg = Config()
        items = []
        for k in range(8):
            it = Item(key="f%d" % k, subj="S%d" % k, obj="O%d" % k, rel="r", born=1)
            it.para = ["p%d" % k]
            it.qa = [("q%d" % k, "O%d" % k)]
            items.append(it)
        st = Counter()
        s.split_holdout(items, 1, st)
        self.assertGreaterEqual(st["held_out"], 1)
        self.assertTrue(all(len(it.para) + len(it.qa) >= 1 for it in items))


class GraderTests(unittest.TestCase):
    def test_fair_strict_grading(self):
        from sleepmlx.gate import correct, recall_hit
        self.assertTrue(correct("7 + 8 = 15", ["15"], "What is 7 + 8?"))
        self.assertTrue(correct("20% of 50 is 10", ["10"], "What is 20% of 50?"))
        self.assertTrue(correct("100°C (212°F)", ["100"], "At what Celsius temperature does water boil?"))
        self.assertFalse(correct("7 or 8", ["8"], "How many legs does a spider have? no"))
        self.assertTrue(correct("H₂O", ["H2O"]))
        self.assertTrue(correct("**Answer:**\nParis", ["Paris"]))
        self.assertFalse(correct("I think it might be Lyon.\nParis", ["Paris"]))
        self.assertTrue(recall_hit("Orbix", "Answer:\nOrbix"))

    def test_infra_failure_is_not_a_verdict(self):
        import sys
        r = served.check_gguf(sys.executable, "/nonexistent.gguf", "/nonexistent.lora", [], port=served.free_port(), wait_s=2)
        self.assertIsNone(r["ok"])
