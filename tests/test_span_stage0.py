"""The Stage 0 branch-point check (scripts/span_stage0.py, `branch_check`): it passes on a true branch and fails on
each way the built-in review (2026-10-18) showed the earlier check could pass with a broken pairing. CPU, tiny."""
from __future__ import annotations

import unittest

import torch
import torch.nn as nn

from scripts import span_stage0
from tests.test_premonition_model import synthetic_batch
from tests.test_premonition_span_cards import plain_model, span_model

DEVICE = torch.device("cpu")


def batches() -> list:
    return [synthetic_batch(visits=2, lines=16, seed=s) for s in (3, 4)]


def pair(**overrides):
    return plain_model(3), span_model(7, **overrides)


class BranchCheckTest(unittest.TestCase):
    def test_a_true_branch_passes_and_the_eager_pass_uses_the_cards(self) -> None:
        line, span = pair()
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertTrue(check["passed"], check["reasons"])
        self.assertEqual(check["economy"]["line_aligned"], 1.0)
        self.assertGreater(check["eager"]["cards_fetched"], 0)
        self.assertEqual(check["missing"], sorted(span_stage0.GATE_KEYS))
        self.assertFalse(line.training or span.training)

    def test_an_unloaded_weight_fails(self) -> None:
        """Review finding 1: strict=False dropped every key mismatch."""
        line, span = pair()
        line.extra = nn.Parameter(torch.zeros(1))                   # a LINE weight SPAN has no slot for
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertFalse(check["passed"])
        self.assertIn("weights", check["reasons"])

    def test_wrong_card_keys_fail(self) -> None:
        """Review finding 3: the key difference was only logged, not part of `passed`."""
        line, span = pair()
        span.writer.key.register_forward_hook(lambda _m, _a, out: out + 0.5)
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertGreater(check["max_key_diff"], 0.1)
        self.assertFalse(check["passed"])
        self.assertIn("card keys or values", check["reasons"])

    def test_wrong_card_values_fail_when_the_natural_pass_never_fetches(self) -> None:
        """Review finding 2: with weights that never ASK, identical answers did not exercise the cards. Here the
        natural pass fetches nothing and matches exactly (the old check passed this pair); the value check and the
        eager pass (which fetches, and whose halt probabilities read the card values) both fail it."""
        line, span = pair()
        with torch.no_grad():
            line.heads.ask.bias.fill_(-20.0)                        # the natural pass never fetches a card
        span.writer.value.register_forward_hook(lambda _m, _a, out: out * 3.0 + 1.0)
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertEqual(check["natural"]["cards_fetched"], 0)
        self.assertEqual(check["natural"]["differing"], 0)
        self.assertFalse(check["passed"])
        self.assertIn("card keys or values", check["reasons"])
        self.assertIn("answers (eager)", check["reasons"])
        self.assertGreater(check["eager"]["cards_fetched"], 0)
        self.assertGreater(check["eager"]["max_halt_diff"], span_stage0.TOLERANCE)

    def test_a_wrong_layout_fails_on_line_alignment(self) -> None:
        line, span = pair(max_span=3)                               # the cap splits every line
        check = span_stage0.branch_check(line, span, batches(), DEVICE)
        self.assertFalse(check["passed"])
        self.assertIn("line_aligned != 1", check["reasons"])

    def test_no_cards_is_reported_not_a_crash(self) -> None:
        """Review finding 6: an empty card set raised inside the check."""
        cut = []
        for batch in batches():
            fields = dict(batch.__dict__)
            fields["card_end"] = torch.zeros_like(batch.card_end)
            cut.append(type(batch)(**fields))
        line, span = pair()
        check = span_stage0.branch_check(line, span, cut, DEVICE)
        self.assertFalse(check["passed"])
        self.assertIn("no cards", check["reasons"])


if __name__ == "__main__":
    unittest.main()
