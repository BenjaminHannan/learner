"""CPU-only regressions: real answer contexts, teacher identity, and no gate leakage."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sleepmlx import gate, replay
from sleepmlx.backend import Stop
from sleepmlx.paths import read_json, write_json
from sleepmlx.recipe import Config, GENERIC_PROMPTS
from sleepmlx.replay_monitor import LEARNING, MONITOR_QA, measure, paired_experiment
from sleepmlx.worker import cfg_from_env
from .helpers import Env


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.env = Env(replay_mode="continuation", max_seq_len=640)
        self.addCleanup(self.env.close)
        self.be = self.env.backend()
        self.path = self.env.paths.home / "replay_cache.json"
        self.calls = []

        def generate(prompts, max_tokens, temp=0.0, adapter=True):
            self.calls.append({"prompts": list(prompts), "limit": max_tokens, "temp": temp, "adapter": adapter})
            return ["trusted answer" for _ in prompts]
        self.be.generate = generate

    def build(self, questions=("Explain a bicycle bell.",), **kwargs):
        return replay.continuation_examples(self.be, self.env.R, questions, self.path, **kwargs)

    def test_answer_continuation_and_prompt_mask_are_present(self):
        self.env.prof.training_answer_prefix = "</think>"
        rows, stats = self.build()
        self.assertEqual(len(rows), 1)
        ids, start = rows[0]
        prompt = self.env.R.render(replay.TEACHER_SYSTEM, "Explain a bicycle bell.")
        self.assertEqual(ids[:start], self.be.encode(prompt))
        self.assertEqual(ids[start:], self.be.encode("</think>trusted answer") + [self.be.stop_id])
        self.assertGreater(len(ids) - start, 1)
        self.assertEqual(start, len(self.be.encode(prompt)))
        self.assertEqual(stats["continuation_examples"], 1)
        self.assertEqual(stats["continuation_target_tokens"], len(ids) - start)
        self.assertEqual((self.calls[0]["adapter"], self.calls[0]["temp"]), (False, 0.0))
        cache = read_json(self.path)
        row = next(iter(cache["records"].values()))
        self.assertIn("not factual verification", row["provenance"]["verified"])
        self.assertIn("unknown", row["provenance"]["completion"])

    def test_cache_reuses_reference_but_not_incumbent_adapter_identity(self):
        rows, _ = self.build()
        self.be.known = {"private": "new value"}
        again, stats = self.build()
        self.assertEqual(again, rows)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(stats["cache_hits"], 1)

    def test_cache_invalidation_for_model_template_tokenizer_version_and_limits(self):
        original = copy.deepcopy(self.env.prof)
        self.build()
        for field, value in (("hf_id", "different/model"), ("source_revision", "new-revision"),
                             ("nothink_suffix", "new-template-tail"), ("training_answer_prefix", "new-prefix")):
            with self.subTest(field=field):
                self.env.prof.__dict__.update(copy.deepcopy(original.__dict__))
                self.build()
                before = len(self.calls)
                setattr(self.env.prof, field, value)
                self.build()
                self.assertEqual(len(self.calls), before + 1)
        before = len(self.calls)
        with patch("sleepmlx.replay.VERSION", "base-continuation-next"):
            self.build()
        self.assertEqual(len(self.calls), before + 1)
        before = len(self.calls)
        self.build(max_tokens=96)
        self.assertEqual(len(self.calls), before + 1)
        before = len(self.calls)
        self.be.tok = type("Tokenizer", (), {"get_vocab": lambda _: {"new-token": 9}})()
        self.build(max_tokens=96)
        self.assertEqual(len(self.calls), before + 1)

    def test_local_config_and_weight_replacement_invalidate_cache(self):
        with tempfile.TemporaryDirectory() as root:
            self.env.prof.model_dir = root
            config = Path(root) / "config.json"
            weight = Path(root) / "model.safetensors"
            config.write_text('{"quantization": 4}')
            weight.write_bytes(b"weights-one")
            self.build()
            config.write_text('{"quantization": 8}')
            self.build()
            weight.write_bytes(b"weights-two-different-size")
            self.build()
            self.assertEqual(len(self.calls), 3)
            identity = read_json(self.path)["identity"]
            self.assertEqual(identity["local_weight_identity"], "path-size-mtime_ns")
            self.assertIn("config.json", identity["assets"])

    def test_corrupt_reference_integrity_is_regenerated(self):
        self.build()
        cache = read_json(self.path)
        next(iter(cache["records"].values()))["answer"] = "edited cache answer"
        write_json(self.path, cache)
        rows, stats = self.build()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.be.dec(rows[0][0][rows[0][1]:-1]), "trusted answer")
        self.assertEqual(stats["generated_answers"], 1)

    def test_generation_limit_reserves_context_and_answer_transition(self):
        q = "Explain a bicycle bell."
        self.env.prof.training_answer_prefix = "prefix"
        n = len(self.be.encode(self.env.R.render(replay.TEACHER_SYSTEM, q)))
        self.be.generate = lambda prompts, max_tokens, **kw: self.calls.append(max_tokens) or ["x" * max_tokens]
        rows, stats = self.build(max_tokens=128, max_seq_len=n + len("prefix") + 7 + 1)
        self.assertEqual(self.calls, [7])
        self.assertEqual(len(rows[0][0]), n + len("prefix") + 8)
        self.assertEqual(stats["continuation_examples"], 1)

    def test_timeout_falls_back_and_is_not_cached(self):
        self.be.generate = lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("teacher timed out"))
        rows, stats = self.build()
        self.assertEqual(stats["generation_timeouts"], 1)
        self.assertEqual(stats["fallback_prompt_examples"], 1)
        self.assertEqual(rows[0][1], 0)
        self.assertFalse(self.path.exists())

    def test_external_stop_propagates_instead_of_fallback_training(self):
        for reason in ("budget", "assistant_running"):
            with self.subTest(reason=reason), self.assertRaises(Stop):
                self.build(before_generate=lambda _: (_ for _ in ()).throw(Stop(reason)))
        self.assertEqual(self.calls, [])

    def test_partial_generation_empty_answer_and_oversized_answer_fall_back(self):
        for value, stat in (([], "incomplete_batches"), ([""], "empty_answers"), (["x" * 129], "oversized_answers")):
            with self.subTest(value=str(value)[:30]):
                self.be.generate = lambda *args, **kwargs: value
                rows, stats = self.build(max_tokens=128)
                self.assertEqual(stats[stat], 1)
                self.assertEqual(rows[0][1], 0)
                self.assertFalse(self.path.exists())

    def test_overlong_prompt_is_skipped_without_generation_or_truncation(self):
        rows, stats = self.build(max_seq_len=10)
        self.assertEqual(rows, [])
        self.assertEqual(self.calls, [])
        self.assertEqual(stats["skipped_contexts"], 1)


class IsolationAndMonitorTests(unittest.TestCase):
    def test_public_replay_and_monitors_are_disjoint_from_promotion_gate(self):
        keys = lambda qs: {replay.question_key(q) for q in qs}
        gate_keys = keys(q for q, _ in gate.GENERAL_QA)
        monitors = keys(q for q, _ in MONITOR_QA)
        blocked = [q for q, _ in gate.GENERAL_QA + MONITOR_QA]
        questions = replay.public_questions(GENERIC_PROMPTS, blocked)
        self.assertTrue(questions)
        self.assertFalse(keys(questions) & gate_keys)
        self.assertFalse(keys(questions) & monitors)
        self.assertFalse(monitors & gate_keys)
        self.assertFalse(monitors & keys(GENERIC_PROMPTS))
        self.assertFalse(monitors & keys(q for row in LEARNING for q in (row[0], row[2])))
        self.assertNotIn("What is the capital of France?", questions)
        self.assertEqual(replay.public_questions([" WHAT is the capital of France!!! "], blocked), [])

    def test_recipe_default_feature_gate_and_environment_overrides(self):
        self.assertEqual(Config().replay_mode, "prompt")
        cfg = cfg_from_env({"SLEEPMLX_REPLAY_MODE": "continuation", "SLEEPMLX_REPLAY_MAX_TOKENS": "64"})
        self.assertEqual((cfg.replay_mode, cfg.replay_max_tokens), ("continuation", 64))
        env = Env()
        self.addCleanup(env.close)
        be = env.backend()
        sl = env.sleeper(be)
        rows = sl.replay_set()
        self.assertTrue(rows)
        self.assertEqual(be.calls["generate"], 0)
        self.assertTrue(all(start == 0 for _, start in rows))
        self.assertFalse(any("capital of France" in be.dec(ids) for ids, _ in rows))
        self.assertTrue(all(len(ids) <= env.cfg.max_seq_len for ids, _ in rows))

    def test_opt_in_recipe_uses_only_public_base_teacher_prompts(self):
        env = Env(replay_mode="continuation")
        self.addCleanup(env.close)
        be = env.backend()
        prompts = []
        def generate(ps, *args, **kwargs):
            self.assertFalse(kwargs["adapter"])
            prompts.extend(ps)
            return ["a public reference answer" for _ in ps]
        be.generate = generate
        sl = env.sleeper(be)
        sl.N = {"stats": {}}
        rows = sl.replay_set()
        self.assertTrue(all(start > 0 for _, start in rows))
        self.assertFalse(any(name in p for p in prompts for name in ("Marta", "Orbix", "Dalmore", "Tomas", "Lena")))
        self.assertEqual(sl.N["stats"]["replay"]["continuation_examples"], len(rows))

    def test_monitor_rejects_incomplete_generation(self):
        env = Env()
        self.addCleanup(env.close)
        be = env.backend()
        be.generate = lambda *args, **kw: []
        with self.assertRaisesRegex(ValueError, "incomplete independent"):
            measure(be, env.R)

    def test_paired_harness_restores_same_initial_adapter_and_never_promotes(self):
        env = Env()
        self.addCleanup(env.close)
        be = env.backend()
        initial = dict(be.known)
        report = paired_experiment(be, env.R, env.paths.home / "experiment", steps=2, max_seq_len=640)
        self.assertFalse(report["quality_claim"])
        self.assertEqual(set(report["arms"]), {"prompt", "continuation"})
        self.assertEqual(report["pass_marks"]["previously_correct_monitor_losses_max"], 0)
        self.assertEqual(be.known, initial)
        self.assertFalse(env.paths.adapter.exists())
        self.assertEqual(len(be.loaded), 3)
        self.assertEqual(len(set(be.loaded)), 1)


if __name__ == "__main__":
    unittest.main()
