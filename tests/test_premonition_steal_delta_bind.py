"""Steal 1, `delta_bind`: key-addressed delta-rule slot binds (design/steals-2026-10-17/SPEC.md section 1)."""
from __future__ import annotations

import unittest

import torch
import torch.nn.functional as F

from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from tests.test_premonition_model import synthetic_batch, tiny_model


def delta_model(variant: str = "D", **overrides) -> PremonitionMini:
    return tiny_model(variant, delta_bind=True, **overrides)


def addressed(model: PremonitionMini, rows: int) -> None:
    """kappa = normalize(key[:rows]): keys e_i address row i. Beta saturates at 1; w ignores the slot."""
    d = model.config.d_model
    with torch.no_grad():
        model.think.delta_address.weight.zero_()
        model.think.delta_address.weight[:, :rows] = torch.eye(rows)
        model.think.delta_write.weight[:, :d].zero_()
        model.think.delta_write.bias[0] = 30.0


def target(model: PremonitionMini, value: torch.Tensor) -> torch.Tensor:
    """The write vector w = tanh(W_w v + b) when the slot part of the write weights is zero."""
    d = model.config.d_model
    write = F.linear(value, model.think.delta_write.weight[1:, d:], model.think.delta_write.bias[1:])
    return torch.tanh(write)


class BuildTest(unittest.TestCase):
    def test_modules_replace_the_binder(self) -> None:
        model = delta_model()
        config = model.config
        self.assertIsNone(model.think.binder)
        self.assertEqual(model.think.delta_address.weight.shape, (config.delta_bind_rows, config.key_dim))
        self.assertEqual(model.think.delta_write.weight.shape,
                         (config.d_model // config.delta_bind_rows + 1, 2 * config.d_model))
        self.assertEqual(model.parameter_breakdown(), config.parameter_breakdown())
        plain = tiny_model()
        self.assertIsNotNone(plain.think.binder)
        self.assertFalse(hasattr(plain.think, "delta_address"))

    def test_no_pointers_builds_neither(self) -> None:
        for variant in ("D-noask", "D-noptr"):
            model = delta_model(variant)
            self.assertIsNone(model.think.binder)
            self.assertIsNone(model.think.delta_address)
            self.assertIsNone(model.think.delta_write)
            self.assertEqual(model.parameter_breakdown(), model.config.parameter_breakdown())

    def test_parameter_delta_at_full_size(self) -> None:
        base = MiniConfig.preset("D").num_parameters()
        on = MiniConfig.preset("D", delta_bind=True).num_parameters()
        self.assertEqual(base, 2_013_140)
        self.assertEqual(on - base, (64 * 8 + 8) + (256 * 17 + 17) - (256 * 256 + 256))


class GatherKeysTest(unittest.TestCase):
    def test_unit_keys_and_the_null_key(self) -> None:
        model, batch = delta_model(), synthetic_batch(seed=4)
        store = model.build_store(model.read(batch), batch)
        visit = torch.zeros(2, dtype=torch.long)
        valid = int(store.valid[0].nonzero()[0])
        keys = store.gather_keys(torch.tensor([[valid, store.null, -1], [store.null, valid, -1]]), visit)
        self.assertEqual(tuple(keys.shape), (2, 3, model.config.key_dim))
        self.assertTrue(torch.equal(keys[0, 0], store.keys[0, valid]))
        self.assertTrue(torch.equal(keys[1, 1], store.keys[0, valid]))
        for row, col in ((0, 1), (0, 2), (1, 0), (1, 2)):
            self.assertTrue(torch.equal(keys[row, col], store.null_key))
        self.assertTrue(torch.allclose(keys.norm(dim=-1), torch.ones(2, 3), atol=1e-5))


class DeltaRuleTest(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(0)
        self.model = delta_model()
        self.d = self.model.config.d_model
        self.rows = self.model.config.delta_bind_rows
        self.key_dim = self.model.config.key_dim

    def key(self, index: int, count: int = 1) -> torch.Tensor:
        return torch.eye(self.key_dim)[index].expand(count, -1)

    def test_a_slot_that_already_reads_back_w_is_unchanged(self) -> None:
        addressed(self.model, self.rows)
        with torch.no_grad():                              # beta = 1/2, so "unchanged" does not rest on beta = 1
            self.model.think.delta_write.bias[0] = 0.0
        value, key = torch.randn(5, self.d), F.normalize(torch.randn(5, self.key_dim), dim=-1)
        w = target(self.model, value)
        kappa = F.normalize(self.model.think.delta_address(key), dim=-1)
        matrix = torch.randn(5, self.rows, self.d // self.rows)
        matrix = matrix + kappa.unsqueeze(-1) * (w - torch.einsum("ma,mab->mb", kappa, matrix)).unsqueeze(1)
        slot = matrix.reshape(5, -1)                      # reads back w along kappa
        again = self.model.think.delta_bind(slot, value, key)
        self.assertTrue(torch.allclose(again, slot, atol=1e-6))

    def test_a_write_with_beta_one_reads_back_and_repeats_to_a_fixed_point(self) -> None:
        addressed(self.model, self.rows)
        value, key, slot = torch.randn(4, self.d), self.key(2, 4), torch.randn(4, self.d)
        w = target(self.model, value)
        once = self.model.think.delta_bind(slot, value, key)
        self.assertTrue(torch.allclose(once.view(4, self.rows, -1)[:, 2], w, atol=1e-5))
        twice = self.model.think.delta_bind(once, value, key)
        self.assertTrue(torch.allclose(twice, once, atol=1e-5))

    def test_directions_orthogonal_to_the_address_are_untouched(self) -> None:
        addressed(self.model, self.rows)
        value, slot = torch.randn(3, self.d), torch.randn(3, self.d)
        out = self.model.think.delta_bind(slot, value, self.key(5, 3))
        before, after = slot.view(3, self.rows, -1), out.view(3, self.rows, -1)
        others = [r for r in range(self.rows) if r != 5]
        self.assertTrue(torch.equal(before[:, others], after[:, others]))
        self.assertFalse(torch.allclose(before[:, 5], after[:, 5]))

    def test_two_writes_with_orthogonal_addresses_both_read_back(self) -> None:
        addressed(self.model, self.rows)
        v1, v2, slot = torch.randn(1, self.d), torch.randn(1, self.d), torch.zeros(1, self.d)
        slot = self.model.think.delta_bind(slot, v1, self.key(0))
        slot = self.model.think.delta_bind(slot, v2, self.key(1))
        matrix = slot.view(1, self.rows, -1)
        self.assertTrue(torch.allclose(matrix[:, 0], target(self.model, v1), atol=1e-5))
        self.assertTrue(torch.allclose(matrix[:, 1], target(self.model, v2), atol=1e-5))

    def test_the_same_address_replaces_its_row(self) -> None:
        addressed(self.model, self.rows)
        v1, v2, slot = torch.randn(1, self.d), torch.randn(1, self.d), torch.zeros(1, self.d)
        slot = self.model.think.delta_bind(slot, v1, self.key(0))
        slot = self.model.think.delta_bind(slot, v2, self.key(0))
        self.assertTrue(torch.allclose(slot.view(1, self.rows, -1)[:, 0], target(self.model, v2), atol=1e-5))

    def test_output_is_fp32_under_autocast(self) -> None:
        slot, value = torch.randn(6, self.d), torch.randn(6, self.d)
        key = F.normalize(torch.randn(6, self.key_dim), dim=-1)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            out = self.model.think.delta_bind(slot, value, key)
        self.assertEqual(out.dtype, torch.float32)
        self.assertTrue(torch.isfinite(out).all())


class InsertTest(unittest.TestCase):
    def test_insert_binds_only_the_cards_entities_with_the_cards_key(self) -> None:
        model, batch = delta_model(), synthetic_batch(seed=4)
        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        episode = model._start(batch, hidden, store, model._mentions(batch))
        count = batch.q_visit.shape[0]
        line = (store.ents[batch.q_visit] >= 0).any(2).float().argmax(1)         # first line with an entity
        base = model.config.question_rows
        slots = slice(base, base + model.config.n_ent)
        before = episode.x[:, slots].clone()
        model._insert(episode, store, torch.arange(count), line.unsqueeze(1))
        after = episode.x[:, slots]
        ents = store.ents[batch.q_visit, line]
        for q in range(count):
            named = {int(e) for e in ents[q] if e >= 0}
            for e in range(model.config.n_ent):
                self.assertEqual(not torch.equal(before[q, e], after[q, e]), e in named, (q, e))
        # Reproduce one bind by hand from the card's own value and key.
        q = int((ents >= 0).any(1).nonzero()[0])
        e = int(ents[q][ents[q] >= 0][0])
        value = store.values[batch.q_visit[q], line[q]].unsqueeze(0)
        key = store.keys[batch.q_visit[q], line[q]].unsqueeze(0)
        expected = model.think.delta_bind(before[q, e].unsqueeze(0), value, key)
        self.assertTrue(torch.allclose(after[q, e], expected[0], atol=1e-6))

    def test_gradients_reach_the_delta_modules(self) -> None:
        model = delta_model()
        batch = synthetic_batch(seed=2)
        for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
            model.zero_grad(set_to_none=True)
            out = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            for name in ("delta_address", "delta_write"):
                module = getattr(model.think, name)
                for param in module.parameters():
                    self.assertIsNotNone(param.grad, (mode, name))
                    self.assertTrue(torch.isfinite(param.grad).all(), (mode, name))
                self.assertGreater(module.weight.grad.abs().sum().item(), 0.0, (mode, name))

    def test_answer_fetches_and_binds(self) -> None:
        model = delta_model()
        with torch.no_grad():
            model.heads.ask.bias.fill_(20.0)
            model.heads.halt.bias.fill_(-20.0)
        batch = synthetic_batch(seed=3)
        answers = model.answer(batch)
        self.assertTrue(answers.fetched.any())
        self.assertEqual(answers.tokens.shape[0], batch.q_visit.shape[0])


if __name__ == "__main__":
    unittest.main()
