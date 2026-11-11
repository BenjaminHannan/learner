"""Stage 0 runner of the decoder_reader_kv A/B: the paired arms train identical steps (RUN-CARD Addendum A)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_reader_kv_stage0 as stage0  # noqa: E402
from premonition.train import train_toy  # noqa: E402


class Stage0StepMatchingTest(unittest.TestCase):
    STEPS = 30          # enough for the gold, teacher and own phases (0-5%, 5-30%, 30-100% of the budget)

    def test_control_arm_is_train_toy(self) -> None:
        ours = stage0.train_arm(0, False, self.STEPS)
        theirs = train_toy("D", steps=self.STEPS, lr=stage0.LR, warmup_steps=stage0.WARMUP, seed=0,
                           config_overrides={"decoder_reader_kv": False})
        for key in ("steps", "flops", "flop_budget", "stop", "tokens"):
            self.assertEqual(ours["train"][key], theirs["train"][key], key)
        self.assertEqual(ours["train"]["final"], theirs["train"]["final"])
        self.assertEqual(ours["validation"]["accuracy"], theirs["validation"]["accuracy"])
        for (name, a), (_, b) in zip(ours["trainer"].model.state_dict().items(),
                                     theirs["trainer"].model.state_dict().items()):
            self.assertTrue(torch.equal(a, b), name)

    def test_matched_treated_arm_takes_the_control_steps_and_phases(self) -> None:
        for seed in (0, 1):
            control = stage0.train_arm(seed, False, self.STEPS)
            matched = (control["trainer"].fit, control["trainer"].flop_budget)
            treated = stage0.train_arm(seed, True, self.STEPS, matched)
            self.assertEqual(treated["train"]["steps"], control["train"]["steps"], seed)
            self.assertEqual(treated["train"]["flops"], control["train"]["flops"], seed)
            self.assertEqual(treated["phases"], control["phases"], seed)
            self.assertEqual({p for _, p in control["phases"]}, {"gold", "teacher", "own"})
            # Same teacher-distractor / own-pick stream: the trainers' generators end in the same state.
            self.assertTrue(torch.equal(treated["trainer"].generator.get_state(),
                                        control["trainer"].generator.get_state()), seed)
            # Treated's own fit says it really costs more per step; that is reported, not matched.
            self.assertGreater(treated["own_budget"], control["trainer"].flop_budget)


if __name__ == "__main__":
    unittest.main()
