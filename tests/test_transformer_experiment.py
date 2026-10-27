"""End-to-end run_experiment coverage for the selected transformer backbone."""
import math
import tempfile
import unittest

import torch

from memorylab.checkpoint import load_checkpoint
from memorylab.experiment import (
    _ThetaState,
    _checkpoint_limit,
    _training_checkpoint_reserve,
    run_experiment,
)
from memorylab.model import MainNetwork
from memorylab.positive_controls import _ControlTheta
from memorylab.storage import Budget
from memorylab.transformer_model import RecurrentTransformerLearner


def make_tiny_transformer(seed=123):
    # Reader width is shrunk for speed; the persistent memory keeps the
    # selected four 128x128 heads because checkpoints only accept that shape.
    torch.manual_seed(seed)
    return RecurrentTransformerLearner(
        model_width=64,
        memory_width=128,
        memory_heads=4,
        attention_heads=4,
        ffn_width=128,
        reasoning_steps=2,
        max_reasoning_steps=2,
        max_decode_len=16,
    )


def make_budget(root):
    return Budget(root, hard=500_000_000, steady=400_000_000, free_floor=0)


class ThetaViewTests(unittest.TestCase):
    def test_theta_and_writer_views_cover_every_parameter(self):
        for model in (make_tiny_transformer(), MainNetwork()):
            everything = {name for name, _ in model.named_parameters()}
            writer = {f"writer.{name}" for name, _ in model.writer.named_parameters()}
            for view in (_ThetaState, _ControlTheta):
                theta = {name for name, _ in view(model).named_parameters()}
                self.assertFalse(theta & writer, view.__name__)
                self.assertEqual(theta | writer, everything, view.__name__)
        transformer_theta = {
            name for name, _ in _ThetaState(make_tiny_transformer()).named_parameters()
        }
        self.assertIn("positions", transformer_theta)
        self.assertIn("memory_head_embedding", transformer_theta)

    def test_full_transformer_pilot_reserves_measured_checkpoint_time(self):
        full = RecurrentTransformerLearner()
        self.assertEqual(_training_checkpoint_reserve("pilot", full), 120.0)
        self.assertEqual(_training_checkpoint_reserve("evaluate", full), 0.0)
        self.assertEqual(_training_checkpoint_reserve("pilot", make_tiny_transformer()), 0.0)


class TransformerRunExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def test_smoke_trains_writes_intervenes_and_restarts_exactly(self):
        model = make_tiny_transformer()
        with tempfile.TemporaryDirectory() as root:
            result = run_experiment(
                "smoke",
                make_budget(root),
                seed=5,
                device="cpu",
                tiers=(1,),
                steps=1,
                seconds=60,
                eval_worlds=1,
                model=model,
                backbone="transformer",
            )

        self.assertEqual(result["backbone"], "transformer")
        self.assertEqual(
            result["model"]["config"]["architecture"], "RecurrentTransformerLearner"
        )
        self.assertEqual(result["model"]["config"]["memory_heads"], 4)
        self.assertEqual(result["status"], "completed")

        # Backward pass ran and reached writer, encoder, and memory reader.
        self.assertEqual(result["training"]["steps_completed"], 1)
        attempt = result["training"]["attempts"][0]
        self.assertTrue(math.isfinite(attempt["loss"]))
        self.assertGreater(attempt["writer_grad_norm"], 0.0)
        self.assertGreater(attempt["encoder_grad_norm"], 0.0)
        self.assertGreater(attempt["memory_query_grad_norm"], 0.0)

        # Accepted teachings changed W from zero in training and evaluation.
        self.assertGreater(attempt["w_change_norm"], 0.0)
        self.assertGreater(result["evaluation"]["w_change_norm"]["min"], 0.0)

        # Zeroing W changes the answer logits for every evaluated query.
        overall = result["evaluation"]["overall"]
        self.assertGreater(overall["queries"], 0)
        self.assertEqual(overall["positive_logit_causal_deltas"], overall["queries"])

        # Serialized theta/phi/W restore bit-exact outputs without workspace.
        restart = result["restart_identity"]
        self.assertTrue(restart["workspace_is_none"])
        self.assertTrue(restart["identical_tokens"])
        self.assertTrue(restart["identical_logits"])
        self.assertEqual(restart["logits_max_abs_diff"], 0.0)
        self.assertTrue(all(value is True for key, value in result["controls"].items()
                            if key != "tier3_positive_control_reader"))

    def test_training_checkpoint_resume_and_evaluate_restore_exact_state(self):
        with tempfile.TemporaryDirectory() as root:
            budget = make_budget(root)
            trained = make_tiny_transformer()
            first = run_experiment(
                "smoke",
                budget,
                seed=19,
                device="cpu",
                tiers=(1,),
                steps=1,
                seconds=60,
                eval_worlds=1,
                model=trained,
                backbone="transformer",
            )
            first_path = budget.root / first["artifacts"]["training_checkpoint"]

            # Every theta and phi tensor, including root-level parameters,
            # comes back exactly; the saved persistent W is the zero state.
            fresh = make_tiny_transformer(seed=999)
            loaded = load_checkpoint(
                first_path,
                _ThetaState(fresh),
                fresh.writer,
                restore_rng=False,
                max_bytes=_checkpoint_limit(fresh),
            )
            self.assertIsNone(loaded.workspace)
            self.assertEqual(tuple(loaded.W.shape), (4, 128, 128))
            self.assertEqual(loaded.W.dtype, torch.float32)
            trained_state = trained.state_dict()
            for name, tensor in fresh.state_dict().items():
                self.assertTrue(torch.equal(tensor, trained_state[name]), name)

            resumed = run_experiment(
                "pilot",
                budget,
                seed=19,
                device="cpu",
                tiers=(1,),
                steps=1,
                seconds=60,
                eval_worlds=1,
                model=make_tiny_transformer(),
                backbone="transformer",
                resume_checkpoint=first_path,
            )
            self.assertEqual(resumed["training"]["global_step_start"], 1)
            self.assertEqual(resumed["training"]["global_step_end"], 2)
            self.assertEqual(resumed["loaded_checkpoint"]["global_step"], 1)
            self.assertTrue(resumed["restart_identity"]["identical_logits"])

            resumed_path = budget.root / resumed["artifacts"]["training_checkpoint"]
            evaluated = run_experiment(
                "evaluate",
                budget,
                seed=23,
                device="cpu",
                tiers=(1,),
                seconds=60,
                eval_worlds=1,
                model=make_tiny_transformer(),
                backbone="transformer",
                checkpoint=resumed_path,
            )
            self.assertEqual(evaluated["backbone"], "transformer")
            self.assertEqual(evaluated["loaded_checkpoint"]["global_step"], 2)
            self.assertTrue(evaluated["loaded_checkpoint"]["workspace_is_none"])
            self.assertTrue(evaluated["restart_identity"]["identical_logits"])
            self.assertEqual(evaluated["status"], "completed")


if __name__ == "__main__":
    unittest.main()
