"""State-lab flags (think_inject, registers=16, multi_query, answer(min_loops)). CPU, tiny d = 32, toy batches."""
from __future__ import annotations

import random
import unittest

import torch

from premonition import toy
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.train import mini_config_dict

SPEC = toy.ToySpec()


def build(seed: int = 0, **flags) -> PremonitionMini:
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size, decoder_raw_cards=True, **flags))


def batch(seed: int = 1):
    return toy.make_batch(SPEC, 2, random.Random(seed))


def losses(model, b, mode="teacher"):
    model.eval()
    gen = torch.Generator().manual_seed(5)
    return model(b, mode=mode, generator=gen)


class FlagsOffTest(unittest.TestCase):
    def test_off_flags_leave_config_dict_unchanged(self):
        values = mini_config_dict(MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size))
        self.assertNotIn("think_inject", values)
        self.assertNotIn("multi_query", values)

    def test_band_ignores_new_params_and_checks_bounds(self):
        full = MiniConfig.preset("D", "full", vocab_size=7068, decoder_raw_cards=True, think_inject=True)
        self.assertEqual(full.parameter_breakdown()["think_inject"], 128 * 128 + 128)
        MiniConfig.preset("D", "full", vocab_size=7068, decoder_raw_cards=True, registers=16, multi_query=4)
        with self.assertRaises(ValueError):
            MiniConfig.preset("D", "tiny", vocab_size=50, multi_query=5)        # > registers (4)


class ThinkInjectTest(unittest.TestCase):
    def test_zero_init_equals_baseline(self):
        b = batch()
        base, inj = build(), build(think_inject=True)
        shared = {k: v for k, v in inj.state_dict().items() if not k.startswith("inject.")}
        self.assertEqual(set(shared), set(base.state_dict()))
        self.assertTrue(all(torch.equal(shared[k], v) for k, v in base.state_dict().items()))
        self.assertTrue(torch.count_nonzero(inj.inject.weight) == 0 and torch.count_nonzero(inj.inject.bias) == 0)
        self.assertEqual(inj.parameter_breakdown()["think_inject"], 32 * 32 + 32)
        for mode in ("gold", "teacher", "own"):
            a, c = losses(base, b, mode), losses(inj, b, mode)
            for name in ("lm", "ask", "ans", "halt", "loss"):
                self.assertTrue(torch.equal(a[name], c[name]), (mode, name))
        x, y = base.answer(b), inj.answer(b)
        self.assertTrue(torch.equal(x.tokens, y.tokens) and torch.equal(x.loops, y.loops))
        self.assertTrue(torch.equal(x.halt_prob, y.halt_prob))

    def test_inject_trains_and_changes_output(self):
        b = batch()
        model = build(think_inject=True)
        model.train()
        out = model(b, mode="teacher", generator=torch.Generator().manual_seed(5))
        out["loss"].backward()
        self.assertGreater(float(model.inject.weight.grad.abs().sum()), 0.0)   # the zero weight still gets a gradient
        base_loss = float(losses(model, b)["loss"].detach())
        with torch.no_grad():
            model.inject.weight.normal_(std=0.5)
        self.assertNotEqual(base_loss, float(losses(model, b)["loss"]))

    def test_reset_parameters_keeps_inject_zero(self):
        model = build(think_inject=True)
        model.reset_parameters()
        self.assertTrue(torch.count_nonzero(model.inject.weight) == 0)

    def test_without_raw_cards(self):
        torch.manual_seed(0)
        cfg = dict(vocab_size=SPEC.vocab_size)
        base = PremonitionMini(MiniConfig.preset("D", "tiny", **cfg))
        torch.manual_seed(0)
        inj = PremonitionMini(MiniConfig.preset("D", "tiny", think_inject=True, **cfg))
        b = batch()
        self.assertTrue(torch.equal(losses(base, b)["loss"], losses(inj, b)["loss"]))


class RegistersAndMultiQueryTest(unittest.TestCase):
    def run_all(self, **flags):
        b = batch()
        model = build(**flags)
        model.train()
        out = model(b, mode="own", p_own=0.5, generator=torch.Generator().manual_seed(2))
        out["loss"].backward()
        self.assertTrue(torch.isfinite(out["loss"]))
        self.assertTrue(all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters()))
        model.eval()
        answers = model.answer(b)
        self.assertEqual(answers.tokens.shape[0], b.q_visit.shape[0])
        return model, out

    def test_registers_16(self):
        model, _ = self.run_all(registers=16)
        self.assertEqual(model.config.rows, 40 + 16 + 16 + 16)
        self.assertEqual(model.think.register.num_embeddings, 16)

    def test_multi_query_4(self):
        self.run_all(registers=16, multi_query=4)
        self.run_all(multi_query=4)

    def test_multi_query_scores_are_elementwise_max(self):
        model = build(multi_query=3)
        b = batch()
        hidden = model.read(b)
        store = model.build_store(hidden, b)
        episode = model._start(b, hidden, store, model._mentions(b))
        index = torch.arange(b.q_visit.shape[0])
        rows = torch.randn_like(episode.x[:, :model.config.rows])
        got = model._ask_scores(rows, episode, index, store, episode.fetched[index])
        singles = []
        for j in range(3):
            one = build(multi_query=0)
            one.load_state_dict({k: v for k, v in model.state_dict().items()})
            rolled = rows.clone()
            rolled[:, one._register_base] = rows[:, one._register_base + j]
            singles.append(one._ask_scores(rolled, episode, index, store, episode.fetched[index]))
        self.assertTrue(torch.equal(got, torch.stack(singles).max(0).values))

    def test_multi_query_one_equals_baseline(self):
        b = batch()
        a, c = losses(build(), b), losses(build(multi_query=1), b)
        self.assertTrue(torch.equal(a["loss"], c["loss"]))


class AnsLastOnlyTest(unittest.TestCase):
    def test_changes_ans_only_in_own_mode(self):
        b = batch()
        base, last = build(), build(ans_last_only=True)
        for mode in ("gold", "teacher"):
            a, c = losses(base, b, mode), losses(last, b, mode)
            self.assertTrue(all(torch.equal(a[k], c[k]) for k in ("lm", "ask", "ans", "halt", "loss")), mode)
        a, c = losses(base, b, "own"), losses(last, b, "own")
        self.assertFalse(torch.equal(a["ans"], c["ans"]))
        for k in ("lm", "ask", "halt"):
            self.assertTrue(torch.equal(a[k], c[k]), k)


class MinLoopsTest(unittest.TestCase):
    def test_min_loops_forces_loops(self):
        b = batch()
        model = build()
        model.eval()
        with torch.no_grad():
            model.heads.halt.bias.fill_(20.0)                  # HALT everywhere: one loop by default
        self.assertTrue((model.answer(b).loops == 1).all())
        self.assertTrue(torch.equal(model.answer(b).loops, model.answer(b, min_loops=None).loops))
        for k in (1, 3, 5, 8):
            self.assertTrue((model.answer(b, min_loops=k).loops == k).all())
        self.assertTrue((model.answer(b, min_loops=8, max_loops=4).loops == 4).all())     # capped by max
        self.assertTrue((model.answer(b, min_loops=20).loops == model.config.max_loops).all())

    def test_default_loops_unchanged_when_never_halting(self):
        b = batch()
        model = build()
        with torch.no_grad():
            model.heads.halt.bias.fill_(-20.0)
        self.assertTrue((model.answer(b, min_loops=3).loops == model.config.max_loops).all())


if __name__ == "__main__":
    unittest.main()
