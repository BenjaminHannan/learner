"""Card-pool variants prepared overnight (run ovn-20260918-235851) for the next session: the two-pool writer equals
D exactly at initialisation, construction leaves the same-seed baseline and the global random stream intact, the
pools act on keys and values separately, and the mean pool is a uniform line mean. CPU, tiny preset; no training."""
from __future__ import annotations

import random
import unittest

import torch

from premonition import card_pools, toy_ladder
from premonition.answer_path import CardBypassMini
from premonition.config import MiniConfig
from premonition.model import PremonitionMini

SPEC = toy_ladder.LadderSpec()


def config() -> MiniConfig:
    return MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size, window=64)


def build(cls, seed: int = 0):
    torch.manual_seed(seed)
    return cls(config())


def batch():
    return toy_ladder.make(SPEC, 2, random.Random(0), training=False)[0]


def store(model, data):
    with torch.no_grad():
        return model.build_store(model.read(data), data)


class CardPoolTest(unittest.TestCase):
    def test_two_pool_equals_single_pool_at_initialisation(self):
        for base_cls, cls in ((PremonitionMini, card_pools.TwoPoolMini),
                              (CardBypassMini, card_pools.TwoPoolBypassMini)):
            base, two = build(base_cls), build(cls)
            shared = base.state_dict()
            for name, tensor in two.state_dict().items():
                if name.startswith("writer.pool_value."):
                    continue
                self.assertTrue(torch.equal(tensor, shared[name]), name)
            self.assertTrue(torch.equal(two.writer.pool_value.weight, two.writer.pool.weight))
            self.assertEqual(two.num_parameters() - base.num_parameters(), base.config.d_model + 1)
            data = batch()
            a, b = store(base, data), store(two, data)
            self.assertTrue(torch.equal(a.keys, b.keys))
            self.assertTrue(torch.equal(a.values, b.values))

    def test_construction_keeps_the_global_random_stream(self):
        after = []
        for cls in (PremonitionMini, card_pools.TwoPoolMini, card_pools.MeanPoolMini):
            build(cls)
            after.append(torch.rand(4))
        self.assertTrue(torch.equal(after[0], after[1]))
        self.assertTrue(torch.equal(after[0], after[2]))

    def test_value_pool_changes_values_not_keys(self):
        two = build(card_pools.TwoPoolMini)
        data = batch()
        before = store(two, data)
        with torch.no_grad():
            two.writer.pool_value.weight.normal_(std=1.0)
        after = store(two, data)
        self.assertTrue(torch.equal(before.keys, after.keys))
        self.assertFalse(torch.allclose(before.values, after.values))

    def test_mean_pool_is_the_uniform_line_mean(self):
        model = build(card_pools.MeanPoolMini)
        data = batch()
        cards = store(model, data)
        with torch.no_grad():
            hidden = model.read(data).float()
            checked = 0
            for v in range(data.line_start.shape[0]):
                for line in range(data.line_start.shape[1]):
                    if not bool(cards.valid[v, line]):
                        continue
                    tokens = (data.line_of[v] == line).nonzero().squeeze(1)
                    expected = model.writer.value(hidden[v, tokens].mean(0))
                    self.assertTrue(torch.allclose(cards.values[v, line], expected, atol=1e-5))
                    checked += 1
        self.assertGreater(checked, 10)

    def test_full_objective_reaches_both_pools(self):
        data = batch()
        for cls, value_pool in ((card_pools.TwoPoolBypassMini, True), (card_pools.MeanPoolBypassMini, False)):
            model = build(cls)
            out = model(data, mode="own", p_own=0.5, generator=torch.Generator().manual_seed(0))
            self.assertTrue(torch.isfinite(out["loss"]))
            out["loss"].backward()
            if value_pool:
                self.assertGreater(float(model.writer.pool.weight.grad.abs().max()), 0.0)
                self.assertGreater(float(model.writer.pool_value.weight.grad.abs().max()), 0.0)
            else:
                self.assertIsNone(model.writer.pool.weight.grad)                  # the mean pool has no scores
            self.assertGreater(float(model.writer.value.weight.grad.abs().max()), 0.0)
            self.assertGreater(float(model.writer.key.weight.grad.abs().max()), 0.0)

    def test_variants_decode_and_have_distinct_identities(self):
        data, supplied, hops = toy_ladder.make(SPEC, 2, random.Random(1), training=False)
        names = set()
        for variant, cls in card_pools.CLASSES.items():
            model = build(cls)
            model.eval()
            with torch.no_grad():
                answers = model.answer(data, max_loops=2)
            self.assertEqual(answers.tokens.shape[0], len(hops))
            ident = card_pools.identity(variant, model.config)
            self.assertEqual(ident["variant"], variant)
            names.add(ident["variant"])
        self.assertEqual(len(names), len(card_pools.VARIANTS))
        with self.assertRaises(ValueError):
            card_pools.identity("D", config())


if __name__ == "__main__":
    unittest.main()
