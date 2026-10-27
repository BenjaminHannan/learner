import json
import unittest
from pathlib import Path

from sleepmlx import gate as gate_mod
from sleepmlx import prompts as P
from sleepmlx.backend import Guards
from sleepmlx.paths import read_json
from sleepmlx.profile import Renderer, load_profile
from sleepmlx.recipe import clip_scale, rem_plan, ref_gen_batches, cosine_lr, Config
from sleepmlx.shy import shy_core

from .helpers import Env, FACTS_DAY1, FACTS_DAY2


class PlanTests(unittest.TestCase):
    def test_scale_clip_and_plan(self):
        self.assertEqual(clip_scale(1, 33, 4, 150, ref_gen_batches(8)), 0.25)
        self.assertEqual(clip_scale(1e9, 33, 4, 150, ref_gen_batches(8)), 4.0)
        s = clip_scale(3600, 33, 4, 150, ref_gen_batches(8))
        self.assertTrue(0.25 < s < 1.0, s)
        for n in (1, 10, 57, 150):
            self.assertEqual(sum(a + b for a, b in rem_plan(n)), n)
        self.assertAlmostEqual(cosine_lr(1.0, 0, 10), 1.0)
        self.assertAlmostEqual(cosine_lr(1.0, 10, 10), 0.0)

    def test_shy_keeps_direction_and_shrinks(self):
        import numpy as np
        rng = np.random.default_rng(0)
        a, b = rng.normal(size=(32, 6)).astype("f"), rng.normal(size=(6, 20)).astype("f")
        a2, b2, z, m, e0, e1 = shy_core(a, b, 2.0, 0.85, 0.0, rng)
        self.assertLess(float(np.abs(2 * a2 @ b2 - 0.85 * 2 * a @ b).max()), 1e-3)
        self.assertEqual(z, 0)

    def test_profiles(self):
        k2, lfm, cpu = load_profile("k2"), load_profile("lfm3"), load_profile("lfm3_cpu")
        self.assertEqual(k2.stop_token, "<|ifm|im_end|>")
        self.assertEqual(lfm.stop_token, "<|im_end|>")
        self.assertEqual(cpu.lora["rank"], 8)
        for p in (k2, lfm, cpu):
            p.template_mode = "manual"
        r = Renderer(k2, None).render("sys", "hi")
        self.assertTrue(r.endswith("<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>"), r)
        r = Renderer(lfm, None).render("sys", "hi")
        self.assertTrue(r.endswith("<|im_start|>assistant\n<think></think>"), r)
        self.assertTrue(Renderer(k2, None).render_think("s", "u").endswith("<ifm|think>\n"))
        import os
        p = load_profile("k2", {"SLEEPMLX_MODEL_DIR": "/x/y", "SLEEPMLX_LOADER": "m:f"})
        self.assertEqual((p.model_dir, p.loader), ("/x/y", "m:f"))

    def test_prompts_use_the_name_parameter(self):
        R = Renderer(load_profile("k2"), None)
        R.p.template_mode = "manual"
        for pr in (P.tag_prompt(R, "hi", "Ben"), P.names_prompt(R, "hi", "A", "B", "Ben"), P.nrem_prompt(R, "ctx", "A", "B", 4, "Ben"),
                   P.gist_prompt(R, "A is B.", 3, "Ben"), P.ctx_prompt(R, "ctx", "q", "Ben")):
            self.assertNotIn("Sam", pr)
            self.assertIn("Ben", pr)

    def test_parsers(self):
        self.assertEqual(P.parse_q1("Question: Who is X?\nAnswer: Y"), "Who is X?")
        self.assertIsNone(P.parse_q1("Answer: Y"))
        self.assertEqual(P.parse_qa1("Question: Q?\nAnswer: Z."), ("Q?", "Z"))
        self.assertIsNone(P.parse_rel_neg("Not related"))
        self.assertIsNotNone(P.parse_rel_neg("works at"))
        self.assertEqual(P.strip_think("thinking </ifm|think>", "</ifm|think>"), ("thinking", True))


class NightTests(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def full_night(self, **be_kw):
        be = self.env.backend(**be_kw)
        res = self.env.sleeper(be).run(self.env.week())
        return be, res

    def test_full_night_outputs(self):
        be, res = self.full_night()
        e = self.env.paths
        self.assertEqual(res["status"], "done", res)
        self.assertFalse(res["reverted"])
        self.assertIsNotNone(res["quiz"])
        self.assertGreater(res["steps_total"], 0)
        self.assertEqual(sorted(be.steps_seen), list(range(res["steps_total"])))
        self.assertTrue((e.adapter / "adapters.safetensors").exists() and (e.adapter / "adapter_config.json").exists())
        self.assertEqual(be.downscaled, 1)
        cards = [json.loads(l) for l in e.cards.read_text().splitlines()]
        self.assertTrue(any(c["status"] == "held_out" for c in cards))
        self.assertTrue(any(c["status"] == "trained" for c in cards))
        nights = [json.loads(l) for l in e.nights.read_text().splitlines()]
        self.assertEqual(len(nights), 1)
        self.assertEqual(nights[0]["status"], "done")
        st = read_json(e.state)
        self.assertEqual(st["slept_days"], ["2026-10-20"])
        self.assertFalse(e.work.exists())
        # nothing new to sleep on
        again = self.env.sleeper(self.env.backend()).run(self.env.week())
        self.assertEqual(again["status"], "no_new_day")

    def test_held_out_cards_never_trained_and_recall_measured(self):
        be, res = self.full_night()
        held = [c for c in map(json.loads, self.env.paths.cards.read_text().splitlines()) if c["status"] == "held_out"]
        self.assertGreaterEqual(len(held), 1)
        self.assertEqual(res["held_out"], len(held))
        trained_blob = "\n".join(be.prompts_trained)
        for h in held:
            self.assertNotIn("Question: " + h["q"], trained_blob)
            self.assertNotIn("user\n" + h["q"] + "<", trained_blob)
        self.assertIn(res["recall_pre"], (0.0, None))
        self.assertGreater(res["quiz"], 0.0)       # the fake learns pairs from the other cards
        self.assertTrue(set(res["recall_by_dir"]) <= {"forward", "reverse"})

    def test_second_night_keeps_previous_adapter_and_replays_cards(self):
        self.full_night()
        e = self.env
        # day 2 arrives
        from .helpers import write_raw
        write_raw(e.paths.diary_dir, "2026-10-21", FACTS_DAY2, conv="c2")
        be2 = e.backend()
        res = e.sleeper(be2).run(e.week())
        self.assertEqual(res["status"], "done", res)
        self.assertTrue((e.paths.adapter_prev / "adapters.safetensors").exists())
        self.assertEqual(read_json(e.paths.state)["slept_days"], ["2026-10-20", "2026-10-21"])
        # the night started from last night's adapter and trained on earlier nights' cards too
        self.assertTrue(be2.loaded and be2.loaded[0] == str(e.paths.adapter))
        self.assertTrue(any("Marta" in p or "Orbix" in p for p in be2.prompts_trained))
        self.assertTrue(any("Pavel" in p or "Quillon" in p for p in be2.prompts_trained))

    def test_dry_run_writes_cards_only(self):
        be = self.env.backend()
        res = self.env.sleeper(be).run(self.env.week(), dry_run=True)
        e = self.env.paths
        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(be.steps_seen, [])
        self.assertFalse(e.adapter.exists())
        self.assertTrue(e.cards.exists() and e.cards.read_text().strip())
        self.assertEqual(read_json(e.state, {}).get("slept_days", []), [])

    def test_too_little_data_is_a_dry_run_with_a_message_not_an_error(self):
        env = Env(days=(("2026-10-20", ["Remember that Marta works at Orbix"]),))
        try:
            be = env.backend()
            res = env.sleeper(be).run(env.week())
            self.assertEqual(res["status"], "dry_run")
            self.assertIn("trainable cards", res["message"])
            self.assertEqual(be.steps_seen, [])
            self.assertEqual(read_json(env.paths.state)["slept_days"] if env.paths.state.exists() else [], [])
            # same data again: answered at once, no new generation
            be2 = env.backend()
            res2 = env.sleeper(be2).run(env.week())
            self.assertEqual(res2["status"], "dry_run")
            self.assertEqual(be2.calls["generate"], 0)
        finally:
            env.close()

    def test_thinking_path_is_used_for_k2_and_not_for_lfm3(self):
        be, _ = self.full_night()
        self.assertTrue(any(m == 512 for m in be.max_tokens_seen))      # K2: the 512-token thinking stage
        env = Env(profile="lfm3")
        try:
            be3 = env.backend()
            r = env.sleeper(be3).run(env.week(), dry_run=True)
            self.assertEqual(r["status"], "dry_run")
            self.assertFalse(any(m == 512 for m in be3.max_tokens_seen))
        finally:
            env.close()


class BudgetTests(unittest.TestCase):
    def test_budget_stop_and_resume(self):
        env = Env()
        try:
            be1 = env.backend()
            r1 = env.sleeper(be1, budget=330).run(env.week())
            self.assertEqual(r1["status"], "stopped", r1)
            self.assertEqual(r1["stop_reason"], "budget")
            self.assertFalse(r1["interrupted"])          # a budget end is normal, not a wake
            self.assertEqual(r1["phase"], "train")
            night = read_json(env.paths.night_json)
            self.assertGreater(night["done_steps"], 0)
            self.assertLess(night["done_steps"], night["total_steps"])
            self.assertEqual(be1.steps_seen, list(range(night["done_steps"])))
            self.assertTrue(env.paths.work_adapter.exists())          # checkpointed
            self.assertFalse(env.paths.adapter.exists())              # not committed yet
            self.assertIsNone(r1.get("quiz"))
            # next chunk resumes at the saved step
            be2 = env.backend()
            r2 = env.sleeper(be2, budget=100000).run(env.week())
            self.assertEqual(r2["status"], "done", r2)
            self.assertTrue(r2["resumed"])
            self.assertEqual(be1.steps_seen + be2.steps_seen, list(range(night["total_steps"])))
            self.assertEqual(be2.loaded[0], str(env.paths.work_adapter))
            self.assertTrue(env.paths.adapter.exists())
            self.assertIsNotNone(r2["quiz"])
        finally:
            env.close()

    def test_tiny_budget_stops_before_any_work_and_resumes_cleanly(self):
        env = Env()
        try:
            r = env.sleeper(env.backend(), budget=10).run(env.week())
            self.assertEqual(r["status"], "stopped")
            r2 = env.sleeper(env.backend(), budget=100000).run(env.week())
            self.assertEqual(r2["status"], "done")
        finally:
            env.close()

    def test_stop_in_generation_reuses_cache(self):
        ref = Env()
        try:
            full = ref.backend(gen_s=30)
            ref.sleeper(full).run(ref.week())
            total_calls = full.calls["generate"]
        finally:
            ref.close()
        env = Env()
        try:
            be1 = env.backend(gen_s=30)
            r1 = env.sleeper(be1, budget=200).run(env.week())
            self.assertEqual(r1["status"], "stopped")
            self.assertIn(r1["phase"], ("tag", "dream"))
            self.assertGreater(be1.calls["generate"], 0)
            self.assertTrue(env.paths.gen_cache.exists())
            done = 0
            for _ in range(20):                                   # chunks of 300 s until the night is done
                be = env.backend(gen_s=30)
                r = env.sleeper(be, budget=200).run(env.week())
                done += be.calls["generate"]
                if r["status"] == "done":
                    break
            self.assertEqual(r["status"], "done")
            self.assertLessEqual(be1.calls["generate"] + done, total_calls + 1)   # no finished batch was generated twice
        finally:
            env.close()

    def test_external_stops(self):
        for name, setup in (("assistant_running", lambda p: p.assistant_running.write_text("1")),
                            ("pause_others", lambda p: p.pause_file.write_text("1"))):
            env = Env()
            try:
                g = Guards(env.paths, poll_s=0, pressure=lambda: 1, now=env.time.now)
                setup(env.paths)
                r = env.sleeper(env.backend(), guards=g).run(env.week())
                self.assertEqual(r["status"], "stopped")
                self.assertEqual(r["stop_reason"], name)
                self.assertTrue(r["interrupted"])
            finally:
                env.close()
        env = Env()
        try:
            g = Guards(env.paths, poll_s=0, pressure=lambda: 2, now=env.time.now)
            r = env.sleeper(env.backend(), guards=g).run(env.week())
            self.assertEqual(r["stop_reason"], "memory_pressure")
            g2 = Guards(env.paths, poll_s=0, pressure=lambda: 1, now=env.time.now)
            g2.signal("sigterm")
            r = env.sleeper(env.backend(), guards=g2).run(env.week())
            self.assertEqual(r["stop_reason"], "sigterm")
        finally:
            env.close()

    def test_wake_mid_training_checkpoints_the_steps_done(self):
        env = Env()
        try:
            be = env.backend()
            flag = {"n": 0}
            orig = be.train_step

            def step(batch, replay, i):
                flag["n"] += 1
                if flag["n"] == 7:
                    env.paths.assistant_running.write_text("1")
                return orig(batch, replay, i)
            be.train_step = step
            g = Guards(env.paths, poll_s=0, pressure=lambda: 1, now=env.time.now)
            r = env.sleeper(be, guards=g).run(env.week())
            self.assertEqual(r["stop_reason"], "assistant_running")
            night = read_json(env.paths.night_json)
            self.assertEqual(night["done_steps"], 7)
            saved = json.loads((env.paths.work_adapter / "adapters.safetensors").read_text())
            self.assertEqual(saved["steps"], list(range(7)))
        finally:
            env.close()


class GateTests(unittest.TestCase):
    def test_judge(self):
        base = [True] * 38 + [False] * 2
        self.assertTrue(gate_mod.judge(base, [True] * 37 + [False] * 3)["harm_ok"])      # -2.5 points
        j = gate_mod.judge(base, [True] * 36 + [False] * 4)                              # -5 points
        self.assertFalse(j["harm_ok"])
        self.assertAlmostEqual(j["harm"], 5.0)
        self.assertEqual(len(gate_mod.GENERAL_QA), 40)
        self.assertEqual(len(gate_mod.gate_questions(20)), 20)
        self.assertTrue(gate_mod.correct("It is 42.", ["42"]) and not gate_mod.correct("142", ["42"]))

    def test_harm_undoes_the_night(self):
        env = Env()
        try:
            # night 1 is fine
            r1 = env.sleeper(env.backend()).run(env.week())
            self.assertFalse(r1["reverted"])
            before = (env.paths.adapter / "adapters.safetensors").read_text()
            from .helpers import write_raw
            write_raw(env.paths.diary_dir, "2026-10-21", FACTS_DAY2, conv="c2")
            be = env.backend(damage=True)
            r2 = env.sleeper(be).run(env.week())
            self.assertEqual(r2["status"], "done")
            self.assertTrue(r2["reverted"])
            self.assertGreater(r2["harm"], 3.0)
            self.assertIn("general questions dropped", r2["message"])
            # the previous adapter is what stays committed, and the model in memory is back on it
            self.assertEqual((env.paths.adapter / "adapters.safetensors").read_text(), before)
            self.assertFalse(env.paths.adapter_prev.exists())
            self.assertEqual(be.loaded[-1], str(env.paths.adapter))
            nights = [json.loads(l) for l in env.paths.nights.read_text().splitlines()]
            self.assertTrue(nights[-1]["reverted"])
            self.assertFalse(env.paths.work.exists())
        finally:
            env.close()

    def test_first_night_harm_leaves_no_adapter(self):
        env = Env()
        try:
            be = env.backend(damage=True)
            r = env.sleeper(be).run(env.week())
            self.assertTrue(r["reverted"])
            self.assertFalse(env.paths.adapter.exists())
            self.assertEqual(be.loaded[-1], "None")
            self.assertEqual(be.known, {})
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
