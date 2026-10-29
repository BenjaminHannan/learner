"""Apex's prompt/answer contract, independent of its unavailable 35B weights."""
import random
import unittest
from pathlib import Path
from unittest.mock import patch

from sleepmlx.profile import Renderer, generated_answer, load_profile
from .helpers import Env


class NativePromptTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_profile("apex35b_mlx", {})

    def test_profile_pins_exact_apex_and_quantized_mlx(self):
        self.assertEqual(self.profile.hf_id, "Apexintelligence-AI/Apex-35B-V1.0")
        self.assertEqual(self.profile.source_revision, "dde5ccd2c8da7ddbc99d804ac9dca656c6e927ef")
        self.assertEqual(self.profile.backend, "mlx")
        self.assertEqual(self.profile.training_answer_prefix, "</think>\n\n")
        self.assertNotIn("mlp.switch_mlp.gate_proj", self.profile.lora["keys"])

    def test_preserves_native_prompt_exactly_without_mode_overrides(self):
        outer = self
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                outer.assertEqual(kwargs, {"tokenize": False, "add_generation_prompt": True})
                return "<|im_start|>user\nSay hello.<|im_end|>\n<|im_start|>assistant\n<think>"
        prompt = Renderer(self.profile, Tokenizer()).render("", "Say hello.")
        self.assertEqual(prompt, "<|im_start|>user\nSay hello.<|im_end|>\n<|im_start|>assistant\n<think>")
        self.assertNotIn("</think>", prompt)

    def test_wrong_or_forced_closed_template_is_rejected(self):
        class Tokenizer:
            def apply_chat_template(self, *args, **kwargs):
                return "assistant\n<think>\n\n</think>\n\n"
        with self.assertRaisesRegex(ValueError, "native tokenizer generation prompt"):
            Renderer(self.profile, Tokenizer()).render("", "Hello")

    def test_reasoning_is_removed_and_incomplete_reasoning_has_no_answer(self):
        prompt = "assistant\n<think>"
        for text, answer in (("Paris might be wrong", ""), ("Paris\n</think>\n\nLyon", "Lyon"),
                             ("</think>\n\nParis", "Paris")):
            with self.subTest(text=text):
                self.assertEqual(generated_answer(self.profile, prompt, text), answer)

    def test_qa_supervises_close_marker_answer_and_stop(self):
        env = Env(max_seq_len=80, ob_share=0.0)
        self.addCleanup(env.close)
        env.prof.training_answer_prefix = self.profile.training_answer_prefix
        sleeper = env.sleeper(env.backend())
        sleeper.N = {"stats": {}}
        with patch("sleepmlx.recipe.P.plain_prompt", return_value="native<think>"):
            ids, start = sleeper.ex_qa("Who?", "Marta", random.Random(0), 1)
        self.assertEqual(start, len("native<think>"))
        self.assertEqual(ids[start:], sleeper.be.encode("</think>\n\nMarta") + [sleeper.be.stop_id])
        # Prefix reservation participates in the actual length check.
        sleeper.cfg.max_seq_len = len(ids) - 1
        with patch("sleepmlx.recipe.P.plain_prompt", return_value="native<think>"):
            self.assertIsNone(sleeper.ex_qa("Who?", "Marta", random.Random(0), 1))

    def test_recall_budget_and_source_revision_invalidate_cached_baselines(self):
        env = Env()
        self.addCleanup(env.close)
        sleeper = env.sleeper(env.backend())
        held = [{"q": "Who?", "a": "Marta"}]
        before = sleeper.recall_identity(held)
        sleeper.cfg.recall_max_tokens = 512
        self.assertNotEqual(before, sleeper.recall_identity(held))
        before = sleeper.recall_identity(held)
        original_general = sleeper.general_base_identity()
        sleeper.prof.source_revision = "changed-checkpoint"
        self.assertNotEqual(before, sleeper.recall_identity(held))
        self.assertNotEqual(original_general, sleeper.general_base_identity())

    def test_pinned_upstream_template_fixture_has_expected_native_tail(self):
        try:
            import jinja2
        except ImportError:
            self.skipTest("optional jinja2 dependency is not installed")
        # Exact upstream fixture, fetched from the profile's pinned revision.
        source = (Path(__file__).parent / "fixtures/apex35b_native_chat_template.jinja").read_text()
        environment = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        template = environment.from_string(source)
        def invalid(message):
            raise ValueError(message)
        rendered = template.render(messages=[{"role": "user", "content": "Say hello."}],
                                   add_generation_prompt=True, raise_exception=invalid)
        self.assertEqual(rendered, "<|im_start|>user\nSay hello.<|im_end|>\n<|im_start|>assistant\n<think>")


if __name__ == "__main__":
    unittest.main()
