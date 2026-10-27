import tempfile
import unittest
from unittest import mock

import torch

from memorylab.experiment import (
    _symmetric_contrastive_alignment,
    causal_generate,
    evaluate_model,
    meta_train_episode,
    run_experiment,
)
from memorylab.model import MainNetwork
from memorylab.storage import Budget
from memorylab.tasks import generate_episode


def make_fast_model():
    torch.manual_seed(123)
    return MainNetwork(
        embed_width=8,
        hidden_width=128,
        reasoning_steps=1,
        max_reasoning_steps=1,
        max_decode_len=2,
    )


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_meta_training_has_writer_and_encoder_gradients(self):
        model = make_fast_model()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        episode = generate_episode("train", 7, tier=1)
        result = meta_train_episode(
            model,
            episode,
            optimizer,
            device="cpu",
            grad_clip=1.0,
        )
        self.assertGreater(result["writer_grad_norm"], 0.0)
        self.assertGreater(result["encoder_grad_norm"], 0.0)
        self.assertGreater(result["w_change_norm"], 0.0)
        self.assertGreater(result["support_queries"], 0)
        self.assertGreater(result["support_loss"], 0.0)
        self.assertGreater(result["loss"], result["query_loss"])
        self.assertGreaterEqual(result["memory_margin_loss"], 0.0)
        self.assertGreater(result["no_w_query_loss"], 0.0)
        self.assertGreater(result["key_alignment_loss"], 0.0)
        self.assertGreaterEqual(result["key_alignment_pairs"], 2)
        self.assertIn("key_alignment_max_off_diagonal", result)

    def test_contrastive_alignment_rejects_all_key_collapse(self):
        collapsed = torch.tensor([[1.0, 0.0]]).expand(3, -1)
        separated = torch.eye(3)
        collapsed_loss, _, collapsed_offdiag = _symmetric_contrastive_alignment(
            collapsed,
            collapsed,
        )
        separated_loss, matched, separated_offdiag = _symmetric_contrastive_alignment(
            separated,
            separated,
        )
        self.assertGreater(float(collapsed_loss), 1.0)
        self.assertLess(float(separated_loss), 1e-4)
        self.assertEqual(float(matched), 1.0)
        self.assertEqual(float(collapsed_offdiag), 1.0)
        self.assertEqual(float(separated_offdiag), 0.0)

    def test_no_w_control_changes_only_memory_argument(self):
        model = make_fast_model().eval()
        query = generate_episode("validation", 3, tier=1).queries[0]
        weights = model.new_memory(batch=1)
        weights[0, 0, 0] = 1.0
        with mock.patch.object(model, "generate", wraps=model.generate) as spy:
            causal_generate(model, query, weights, device="cpu")
        self.assertEqual(spy.call_count, 2)
        first_weights = spy.call_args_list[0].args[1]
        second_weights = spy.call_args_list[1].args[1]
        torch.testing.assert_close(first_weights, weights, rtol=0, atol=0)
        torch.testing.assert_close(second_weights, torch.zeros_like(weights), rtol=0, atol=0)
        torch.testing.assert_close(
            spy.call_args_list[0].args[0],
            spy.call_args_list[1].args[0],
            rtol=0,
            atol=0,
        )

    def test_evaluation_rejects_train_split(self):
        model = make_fast_model()
        with self.assertRaises(ValueError):
            evaluate_model(
                model,
                split="train",
                tiers=(1,),
                worlds_per_tier=1,
                seed=0,
                device="cpu",
            )

    def test_smoke_result_schema_and_restart_identity(self):
        model = make_fast_model()
        with tempfile.TemporaryDirectory() as root:
            budget = Budget(
                root,
                hard=100_000_000,
                steady=80_000_000,
                free_floor=0,
            )
            result = run_experiment(
                "smoke",
                budget,
                seed=5,
                device="cpu",
                tiers=(1,),
                steps=1,
                seconds=20,
                eval_split="validation",
                eval_worlds=1,
                learning_rate=1e-3,
                model=model,
            )

            self.assertIn(result["status"], {"completed", "time_limit", "failed_controls"})
            self.assertEqual(result["device"], "cpu")
            self.assertIsNone(result["peak_cuda_memory_bytes"])
            self.assertGreater(result["elapsed_seconds"], 0.0)
            self.assertEqual(result["training"]["steps_completed"], 1)
            self.assertEqual(result["training"]["stop_reason"], "max_steps")
            self.assertGreater(result["limits"]["evaluation_reserve_seconds"], 0.0)
            self.assertEqual(result["training"]["attempts"][0]["tier"], 1)
            self.assertEqual(result["evaluation"]["split"], "validation")
            self.assertTrue(result["evaluation"]["worlds"])
            self.assertTrue(result["restart_identity"]["workspace_is_none"])
            self.assertTrue(result["restart_identity"]["identical_tokens"])
            self.assertEqual(
                result["restart_identity"]["tokens_before"],
                result["restart_identity"]["tokens_after"],
            )
            self.assertIn("exact_match_rate", result["quality"])
            self.assertIsInstance(result["quality"]["all_exact"], bool)
            result_path = budget.root / result["artifacts"]["result_json"]
            checkpoint_path = budget.root / result["artifacts"]["restart_checkpoint"]
            training_checkpoint_path = (
                budget.root / result["artifacts"]["training_checkpoint"]
            )
            self.assertTrue(result_path.is_file())
            self.assertTrue(checkpoint_path.is_file())
            self.assertTrue(training_checkpoint_path.is_file())
            self.assertTrue(result["training_checkpoint"]["persistent_w_is_zero"])

    def test_training_checkpoint_resumes_cursor_and_can_be_evaluated(self):
        with tempfile.TemporaryDirectory() as root:
            budget = Budget(
                root,
                hard=100_000_000,
                steady=80_000_000,
                free_floor=0,
            )
            first = run_experiment(
                "smoke",
                budget,
                seed=19,
                device="cpu",
                tiers=(1,),
                steps=1,
                seconds=20,
                eval_worlds=1,
                learning_rate=1e-3,
                model=make_fast_model(),
            )
            first_path = budget.root / first["artifacts"]["training_checkpoint"]
            resumed = run_experiment(
                "pilot",
                budget,
                seed=19,
                device="cpu",
                tiers=(1,),
                steps=1,
                seconds=20,
                eval_worlds=1,
                learning_rate=1e-3,
                model=make_fast_model(),
                resume_checkpoint=first_path,
            )
            self.assertEqual(resumed["training"]["global_step_start"], 1)
            self.assertEqual(resumed["training"]["global_step_end"], 2)
            self.assertEqual(resumed["loaded_checkpoint"]["global_step"], 1)

            resumed_path = budget.root / resumed["artifacts"]["training_checkpoint"]
            evaluated = run_experiment(
                "evaluate",
                budget,
                seed=23,
                device="cpu",
                tiers=(1,),
                seconds=20,
                eval_worlds=1,
                model=make_fast_model(),
                checkpoint=resumed_path,
            )
            self.assertEqual(evaluated["loaded_checkpoint"]["global_step"], 2)
            self.assertTrue(evaluated["loaded_checkpoint"]["workspace_is_none"])

if __name__ == "__main__":
    unittest.main()
