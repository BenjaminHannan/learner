"""CPU-only regressions for truthful answer targets and promotion evidence."""
import json
import random
import unittest
from pathlib import Path
from unittest.mock import patch

from sleepmlx import gate
from .helpers import Env


class AnswerTargetTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(max_seq_len=40, ob_share=1.0)
        self.addCleanup(self.env.close)
        self.be = self.env.backend()
        self.sl = self.env.sleeper(self.be)
        self.sl.N = {"stats": {}}
        self.sl.diary = object()

    def example(self, plain, diary, answer):
        with patch("sleepmlx.recipe.P.plain_prompt", return_value=plain), patch("sleepmlx.recipe.P.diary_prompt", return_value=diary):
            return self.sl.ex_qa("question", answer, random.Random(0), 1)

    def test_open_book_reserves_actual_answer_and_stop(self):
        # The old 24-token reservation accepted this 30-token answer then cut it.
        ids, start = self.example("prompt", "context prompt", "a" * 30)
        self.assertEqual(start, len("prompt"))
        self.assertEqual(ids[start:], self.be.encode("a" * 30) + [self.be.stop_id])
        self.assertLessEqual(len(ids), 40)
        self.assertEqual(self.sl.N["stats"]["training_targets"]["qa_open_book_fallback"], 1)

    def test_exact_fit_preserves_every_answer_token_and_stop(self):
        ids, start = self.example("unused", "p" * 9, "z" * 30)
        self.assertEqual((len(ids), start), (40, 9))
        self.assertEqual(ids[start:], self.be.encode("z" * 30) + [0])

    def test_full_prompt_and_oversized_answer_are_skipped(self):
        for prompt, answer in (("p" * 40, "yes"), ("p" * 39, "yes"), ("p", "a" * 40)):
            with self.subTest(prompt=len(prompt), answer=len(answer)):
                self.assertIsNone(self.example(prompt, prompt, answer))
        self.assertEqual(self.sl.N["stats"]["training_targets"]["qa_skipped_too_long"], 3)

    def test_empty_answer_is_not_stop_only_training(self):
        self.assertIsNone(self.example("prompt", "diary", ""))

    def test_raw_lm_truncation_remains_a_separate_objective(self):
        ids, start = self.sl.ex_text("r" * 60)
        self.assertEqual((ids, start), (self.be.encode("r" * 40), 0))
        stats = self.sl.N["stats"]["training_targets"]
        self.assertEqual(stats["raw_lm_truncated"], 1)
        self.assertEqual(stats["raw_lm_target_tokens"], 39)
        self.assertNotIn("qa_examples", stats)

    def test_training_never_substitutes_a_prompt_token_for_an_answer(self):
        env = Env(max_seq_len=60, ob_share=0.0, dreamcheck=False)
        self.addCleanup(env.close)
        be = env.backend()
        original = be.train_step
        def train(batch, replay, step):
            self.assertTrue(batch)
            for ids, start in batch:
                self.assertLessEqual(len(ids), 60)
                if start:
                    self.assertEqual(ids[-1], be.stop_id)
                    self.assertGreater(len(ids) - start, 1)
            return original(batch, replay, step)
        be.train_step = train
        result = env.sleeper(be).run(env.week())
        self.assertEqual(result["status"], "done")
        stats = json.loads(env.paths.nights.read_text().splitlines()[-1])["stats"]["training_targets"]
        self.assertGreater(stats["qa_skipped_too_long"], 0)
        self.assertGreater(stats["raw_lm_target_tokens"], 0)


class ConservativeGradingTests(unittest.TestCase):
    def test_independent_answer_fixtures(self):
        rows = json.loads((Path(__file__).parent / "fixtures" / "answer_truthfulness.json").read_text())
        for row in rows:
            with self.subTest(reply=row["reply"]):
                self.assertEqual(gate.recall_hit(row["answer"], row["reply"]), row["hit"])
                self.assertEqual(gate.correct(row["reply"], [row["answer"]]), row["hit"])

    def test_baseline_must_be_a_complete_measurement(self):
        post = {"n": 4, "hits": 2}
        for pre in (None, {}, {"n": 3, "hits": 0}, {"n": 4}, {"n": 4, "hits": 99},
                    {"n": 4, "recall": float("nan")}, {"n": 4, "recall": float("inf")}):
            with self.subTest(pre=pre):
                self.assertTrue(any("inconclusive" in r for r in gate.decide({"harm_ok": True}, pre, post)))
        self.assertEqual(gate.decide({"harm_ok": True}, {"n": 4, "hits": 0}, post), [])

    def test_empty_general_measurement_cannot_pass(self):
        self.assertFalse(gate.judge([], [])["harm_ok"])
        self.assertFalse(gate.judge([True, True], [True])["harm_ok"])

    def test_short_generation_results_are_inconclusive(self):
        env = Env()
        self.addCleanup(env.close)
        be = env.backend()
        be.generate = lambda *args, **kwargs: []
        with self.assertRaisesRegex(ValueError, "incomplete general"):
            gate.score_general(be, env.R, True)
        with self.assertRaisesRegex(ValueError, "incomplete recall"):
            gate.score_recall(be, env.R, [{"q": "Who?", "a": "Cedar"}])


class IncumbentBaselineTests(unittest.TestCase):
    def test_regrading_loads_incumbent_then_restores_candidate(self):
        env = Env()
        self.addCleanup(env.close)
        env.paths.mk()
        be = env.backend()
        be.known = {"Marta": "Orbix"}
        be.save_adapter(env.paths.adapter)
        be.known = {"Marta": "Dalmore"}
        be.save_adapter(env.paths.work_adapter)
        sl = env.sleeper(be)
        held = [{"q": "Who employs Marta?", "a": "Orbix", "dir": "forward"}]
        pre = sl.measure_incumbent_recall(held)
        self.assertEqual(pre["hits"], 1)
        self.assertEqual(be.known, {"Marta": "Dalmore"})
        self.assertTrue(sl.recall_baseline_valid(pre, held))
        self.assertFalse(sl.recall_baseline_valid(dict(pre, grader="strict-2"), held))
        self.assertFalse(sl.recall_baseline_valid(pre, [{**held[0], "a": "Dalmore"}]))
        env.prof.nothink_suffix += "changed"
        self.assertFalse(sl.recall_baseline_valid(pre, held))

    def test_grader_upgrade_after_training_cannot_turn_unknown_pre_into_gain(self):
        env = Env(dreamcheck=False)
        self.addCleanup(env.close)
        be = env.backend()
        sl = env.sleeper(be)
        original_gate = sl._gate
        seen = {}
        def upgrade_then_gate(week, d, eligible, result):
            # At this point the candidate knows the held cards. Make the unchanged
            # incumbent equally competent; an old/missing baseline must not become 0.
            be.save_adapter(env.paths.adapter)
            sl.N["pre"] = {"grader": "strict-2", "n": 1, "hits": 0}
            original_gate(week, d, eligible, result)
            seen.update(sl.N["pre"])
        sl._gate = upgrade_then_gate
        result = sl.run(env.week())
        self.assertTrue(result["reverted"], result)
        self.assertIn("did not improve", result["message"])
        self.assertEqual(seen["grader"], gate.GRADER)
        self.assertGreater(seen["hits"], 0)
        self.assertEqual(result["recall_pre"], result["quiz"])

    def test_general_baseline_identity_changes_with_model_and_generation_limit(self):
        env = Env()
        self.addCleanup(env.close)
        sl = env.sleeper(env.backend())
        identity = sl.general_base_identity()
        env.prof.model_dir = "/different/model"
        self.assertNotEqual(identity, sl.general_base_identity())
        env.cfg.gate_max_tokens += 1
        self.assertNotEqual(identity["max_tokens"], sl.general_base_identity()["max_tokens"])
