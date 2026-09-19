"""Milestone-2 diagnostic variants (premonition/answer_path.py): identities, shared weights, and that baseline D
is unchanged. CPU, tiny preset, toy batches; no training."""
from __future__ import annotations

import random
import unittest

import torch

from premonition import answer_path
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.toy import ToySpec, make_batch

SPEC = ToySpec()


def tiny(seed: int = 0) -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size, window=64))


def batch():
    return make_batch(SPEC, 3, random.Random(5))


class AnswerPathVariantTest(unittest.TestCase):
    def test_from_base_copies_every_shared_weight(self):
        base = tiny()
        for name in answer_path.ADJUSTMENTS:
            model = answer_path.from_base(name, base)
            shared = base.state_dict()
            for key, value in model.state_dict().items():
                if key in shared:
                    self.assertTrue(torch.equal(value, shared[key]), (name, key))
            self.assertEqual(set(model.state_dict()) - set(shared), {"think.alpha"} if name ==
                             answer_path.THINK_GATED else set())

    def test_gate_at_zero_is_the_identity_and_alpha_gets_a_gradient(self):
        model = answer_path.from_base(answer_path.THINK_GATED, tiny())
        x = torch.randn(2, model.config.rows, model.config.d_model)
        valid = torch.ones(2, model.config.rows, dtype=torch.bool)
        valid[:, 3] = False
        self.assertTrue(torch.equal(model.think(x, valid, 0), x))
        out = model.forward(batch(), mode="gold", loops=2, weights={"ans": 1.0})
        out["loss"].backward()
        self.assertNotEqual(float(model.think.alpha.grad), 0.0)
        self.assertEqual(float(model.think.layers[0].qkv.weight.grad.abs().max()), 0.0)
        self.assertEqual(float(model.think.step.weight.grad.abs().max()), 0.0)   # the step embedding is gated too

    def test_bypass_decoder_reads_the_inserted_card_rows(self):
        base = tiny()
        model = answer_path.from_base(answer_path.CARD_BYPASS, base)
        seen = []
        original = PremonitionMini._decode_logits

        def spy(self, rows, valid, inputs):
            seen.append((rows.detach().clone(), valid.clone()))
            return original(self, rows, valid, inputs)
        b = batch()
        with torch.no_grad():
            PremonitionMini._decode_logits = spy
            try:
                model.forward(b, mode="gold", loops=2, weights={"ans": 1.0})
            finally:
                PremonitionMini._decode_logits = original
        c = model.config
        cards = slice(c.question_rows + c.slots, c.question_rows + c.slots + c.cards)
        first, second = seen[0][0][:, cards], seen[1][0][:, cards]
        self.assertTrue(torch.equal(first, second))                       # card rows frozen across loops
        self.assertEqual(seen[0][0].shape[1], c.rows)                     # same memory size
        self.assertTrue(torch.equal(seen[0][1], seen[1][1]))              # same mask
        self.assertGreater(float(first.abs().sum()), 0.0)
        self.assertIsNone(model._reading)                                 # no graph kept after forward

    def test_answer_works_for_both_variants(self):
        base = tiny()
        b = batch()
        for name in answer_path.ADJUSTMENTS:
            model = answer_path.from_base(name, base).eval()
            answers = model.answer(b, max_loops=3)
            self.assertEqual(answers.tokens.shape[0], b.q_visit.shape[0])

    def test_identity_names_the_variant_and_is_diagnostic(self):
        config = tiny().config
        for name in answer_path.ADJUSTMENTS:
            ident = answer_path.identity(name, config)
            self.assertEqual((ident["variant"], ident["base_variant"], ident["purpose"]), (name, "D", "diagnostic"))
            self.assertEqual(len(ident["source_sha256"]), 64)
        with self.assertRaises(ValueError):
            answer_path.identity("D", config)

    def test_baseline_d_is_unchanged(self):
        model = tiny()
        self.assertIs(type(model.think).forward, answer_path.Think.forward)
        self.assertFalse(hasattr(model.think, "alpha"))


if __name__ == "__main__":
    unittest.main()
