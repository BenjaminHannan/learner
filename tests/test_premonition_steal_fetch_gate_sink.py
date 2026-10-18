"""Steal 2, `fetch_gate` and `fetch_sink`: gated fetched values, headwise gated cross-attention and
per-head sinks (design/steals-2026-10-17/SPEC.md section 2)."""
from __future__ import annotations

import math
import unittest

import torch

from premonition.config import MiniConfig
from premonition.model import Decoder
from premonition.store import set_cross_entropy, set_cross_entropy_with_sink
from tests.test_premonition_model import synthetic_batch, tiny_config, tiny_model

SIGMOID3 = 1 / (1 + math.exp(-3.0))


def decoder_pair(**overrides) -> tuple[Decoder, Decoder]:
    """(flagged decoder, plain decoder) of two models, with identical shared weights and the model's inits."""
    flagged, plain = tiny_model(**overrides).decoder, tiny_model().decoder
    plain.load_state_dict({k: v for k, v in flagged.state_dict().items() if k in plain.state_dict()})
    return flagged.eval(), plain.eval()


def decode_inputs(config: MiniConfig, rows: int = 12) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    gen = torch.Generator().manual_seed(1)
    x = torch.randn(3, 5, config.d_model, generator=gen)
    memory = torch.randn(3, rows, config.d_model, generator=gen)
    valid = torch.rand(3, rows, generator=gen) > 0.3
    valid[:, 0] = True
    return x, memory, valid


class BuildTest(unittest.TestCase):
    def test_flags_off_build_nothing(self) -> None:
        model = tiny_model()
        self.assertFalse(hasattr(model.think, "fetch_gate"))
        self.assertFalse(hasattr(model.decoder, "cross_gate"))
        self.assertFalse(hasattr(model.decoder, "cross_sink"))
        self.assertFalse(hasattr(model.heads, "ask_sink"))

    def test_counts_match_the_config_in_every_variant(self) -> None:
        for variant in ("D", "D-noask", "D-noptr"):
            for flags in ({"fetch_gate": True}, {"fetch_sink": True}, {"fetch_gate": True, "fetch_sink": True}):
                model = tiny_model(variant, **flags)
                self.assertEqual(model.parameter_breakdown(), model.config.parameter_breakdown(), (variant, flags))

    def test_controls_without_a_store_have_only_the_decoder_parts(self) -> None:
        model = tiny_model("D-noask", fetch_gate=True, fetch_sink=True)
        self.assertFalse(hasattr(model.think, "fetch_gate"))
        self.assertFalse(hasattr(model.heads, "ask_sink"))
        self.assertTrue(hasattr(model.decoder, "cross_gate") and hasattr(model.decoder, "cross_sink"))

    def test_parameter_deltas_at_full_size(self) -> None:
        base = MiniConfig.preset("D").num_parameters()
        self.assertEqual(base, 2_013_140)
        gate = MiniConfig.preset("D", fetch_gate=True).num_parameters() - base
        sink = MiniConfig.preset("D", fetch_sink=True).num_parameters() - base
        self.assertEqual(gate, (256 * 4 + 4) + (128 * 4 + 4))
        self.assertEqual(sink, 4 + 1)

    def test_inits(self) -> None:
        model = tiny_model(fetch_gate=True, fetch_sink=True, fetch_gate_bias=2.5, sink_init=-1.5)
        self.assertTrue(torch.all(model.think.fetch_gate.bias == 2.5))
        self.assertTrue(torch.all(model.decoder.cross_gate.bias == 2.5))
        self.assertTrue(torch.all(model.decoder.cross_sink == -1.5))
        self.assertEqual(model.heads.ask_sink.item(), -2 * model.config.kappa_init)
        self.assertEqual(model.heads.ask_sink.dim(), 0)


class FetchGateTest(unittest.TestCase):
    def test_gate_is_open_at_init(self) -> None:
        model = tiny_model(fetch_gate=True)
        register, value = torch.randn(4, model.config.d_model), torch.randn(4, 3, model.config.d_model)
        gated = model.think.gate_values(register, value)
        ratio = gated / value
        self.assertTrue(torch.allclose(ratio, torch.full_like(ratio, SIGMOID3), atol=0.03), ratio.mean().item())
        self.assertEqual(gated.dtype, torch.float32)

    def test_decoder_gate_is_open_at_init(self) -> None:
        decoder, _ = decoder_pair(fetch_gate=True)
        normed = decoder.norm2(torch.randn(3, 5, decoder.cross_gate.in_features))
        gate = torch.sigmoid(decoder.cross_gate(normed))
        self.assertEqual(tuple(gate.shape), (3, 5, decoder.heads))
        self.assertTrue(torch.allclose(gate, torch.full_like(gate, SIGMOID3), atol=0.03))

    def test_gate_is_per_head_and_broadcasts_over_head_channels(self) -> None:
        model = tiny_model(fetch_gate=True)
        d, heads = model.config.d_model, model.config.n_heads
        with torch.no_grad():
            model.think.fetch_gate.weight.zero_()
            model.think.fetch_gate.bias.copy_(torch.tensor([-50.0, 0.0, 50.0, 0.0]))
        value = torch.ones(2, 3, d)
        gated = model.think.gate_values(torch.randn(2, d), value).view(2, 3, heads, d // heads)
        self.assertTrue(torch.allclose(gated[..., 0, :], torch.zeros(1), atol=1e-6))
        self.assertTrue(torch.allclose(gated[..., 1, :], torch.full((1,), 0.5)))
        self.assertTrue(torch.allclose(gated[..., 2, :], torch.ones(1)))

    def test_decoder_gate_scales_each_head_of_the_cross_attention_output(self) -> None:
        decoder, plain = decoder_pair(fetch_gate=True)
        x, memory, valid = decode_inputs(decoder_config := tiny_config(fetch_gate=True))
        with torch.no_grad():
            decoder.cross_gate.weight.zero_()
            decoder.cross_gate.bias.fill_(60.0)               # gate = 1: identical to the plain decoder
            self.assertTrue(torch.allclose(decoder(x, memory, valid), plain(x, memory, valid), atol=1e-5))
            decoder.cross_gate.bias.fill_(-60.0)              # gate = 0: cross-attention contributes nothing
            plain.cross_proj.weight.zero_()
            plain.cross_proj.bias.zero_()
            self.assertTrue(torch.allclose(decoder(x, memory, valid), plain(x, memory, valid), atol=1e-5))
        self.assertEqual(decoder_config.n_heads, decoder.heads)

    def test_insert_rows_and_binds_use_the_gated_value(self) -> None:
        batch = synthetic_batch(seed=4)
        gated = tiny_model(fetch_gate=True)
        plain = tiny_model()
        plain.load_state_dict({k: v for k, v in gated.state_dict().items() if k in plain.state_dict()})
        with torch.no_grad():
            gated.think.fetch_gate.weight.zero_()
            gated.think.fetch_gate.bias.fill_(0.0)            # every gate is exactly 1/2
        out = []
        for model in (gated, plain):
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            episode = model._start(batch, hidden, store, model._mentions(batch))
            line = (store.ents[batch.q_visit] >= 0).any(2).float().argmax(1)
            cards = torch.stack([line, torch.full_like(line, store.null)], dim=1)   # a real card and NULL
            model._insert(episode, store, torch.arange(batch.q_visit.shape[0]), cards)
            out.append((store, episode, cards))
        (store, g_ep, cards), (_, p_ep, _) = out
        base = gated._card_base
        # Row = gated value + age + type: the difference to the plain row is half the value.
        for slot, line in ((0, cards[:, 0]), (1, torch.full_like(cards[:, 0], store.null))):
            values, _, _ = store.gather(line.unsqueeze(1), batch.q_visit)
            diff = p_ep.x[:, base + slot] - g_ep.x[:, base + slot]
            self.assertTrue(torch.allclose(diff, 0.5 * values[:, 0].float(), atol=1e-5), slot)
        slots = slice(gated.config.question_rows, gated.config.question_rows + gated.config.n_ent)
        self.assertFalse(torch.equal(g_ep.x[:, slots], p_ep.x[:, slots]))     # the binds saw gated values too

    def test_gradients_reach_both_gates(self) -> None:
        model = tiny_model(fetch_gate=True)
        batch = synthetic_batch(seed=2)
        for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
            model.zero_grad(set_to_none=True)
            out = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            for module in (model.think.fetch_gate, model.decoder.cross_gate):
                self.assertGreater(module.weight.grad.abs().sum().item(), 0.0, mode)
                self.assertTrue(torch.isfinite(module.weight.grad).all(), mode)


class DecoderSinkTest(unittest.TestCase):
    def test_a_minus_inf_sink_equals_no_sink(self) -> None:
        sunk, plain = decoder_pair(fetch_sink=True)
        x, memory, valid = decode_inputs(tiny_config())
        with torch.no_grad():
            sunk.cross_sink.fill_(-math.inf)
            self.assertTrue(torch.allclose(sunk(x, memory, valid), plain(x, memory, valid), atol=1e-5))
            sunk.cross_sink.fill_(0.0)                         # a live sink changes the answer
            self.assertFalse(torch.allclose(sunk(x, memory, valid), plain(x, memory, valid), atol=1e-5))

    def test_a_large_sink_sends_the_cross_attention_to_zero(self) -> None:
        sunk, plain = decoder_pair(fetch_sink=True)
        x, memory, valid = decode_inputs(tiny_config())
        with torch.no_grad():
            sunk.cross_sink.fill_(1e4)
            plain.cross_proj.weight.zero_()
            plain.cross_proj.bias.zero_()
            self.assertTrue(torch.allclose(sunk(x, memory, valid), plain(x, memory, valid), atol=1e-5))
            q = torch.randn(3, 4, 5, 8)
            k, v = torch.randn(3, 4, 12, 8), torch.randn(3, 4, 12, 8)
            self.assertEqual(sunk._sink_attention(q, k, v, valid).abs().max().item(), 0.0)

    def test_the_sink_is_per_head_and_matches_the_softmax_formula(self) -> None:
        sunk, _ = decoder_pair(fetch_sink=True)
        gen = torch.Generator().manual_seed(3)
        q, k, v = (torch.randn(2, 4, 3, 8, generator=gen), torch.randn(2, 4, 7, 8, generator=gen),
                   torch.randn(2, 4, 7, 8, generator=gen))
        valid = torch.rand(2, 7, generator=gen) > 0.3
        valid[:, 0] = True
        bias = torch.tensor([-2.0, 0.0, 1.5, 4.0])
        with torch.no_grad():
            sunk.cross_sink.copy_(bias)
        logits = q @ k.transpose(-1, -2) / math.sqrt(8)                       # [2, 4, 3, 7]
        logits = logits.masked_fill(~valid[:, None, None, :], -math.inf)
        logits = torch.cat([logits, bias.view(1, 4, 1, 1).expand(2, 4, 3, 1)], dim=-1)
        weight = logits.softmax(-1)
        expected = weight[..., :-1] @ v                                       # the sink's value is 0
        self.assertTrue(torch.allclose(sunk._sink_attention(q, k, v, valid), expected, atol=1e-5))

    def test_sink_gets_gradient_and_invalid_rows_stay_masked(self) -> None:
        sunk, _ = decoder_pair(fetch_sink=True)
        x, memory, valid = decode_inputs(tiny_config())
        base = sunk(x, memory, valid)
        base.sum().backward()
        self.assertGreater(sunk.cross_sink.grad.abs().sum().item(), 0.0)
        shifted = memory.clone()
        shifted[~valid] += 100.0
        self.assertTrue(torch.allclose(sunk(x, shifted, valid), base, atol=1e-5))


class AskSinkTest(unittest.TestCase):
    def fixture(self, sink: float):
        model = tiny_model(fetch_sink=True)
        batch = synthetic_batch(seed=1)
        store = model.build_store(model.read(batch), batch)
        with torch.no_grad():
            model.heads.ask_sink.fill_(sink)
        return model, store

    def test_the_sink_blocks_low_scoring_cards(self) -> None:
        model, store = self.fixture(0.0)
        scores = torch.full((3, store.lines + 1), -5.0)
        scores[0, 2], scores[0, 4], scores[0, 6] = 7.0, 3.0, 0.5     # above the sink
        scores[1, 1] = 0.0                                           # exactly at the sink: blocked
        scores[1, 3] = 2.0
        scores[2, 5] = 1.0
        ask, stop = torch.ones(3), torch.zeros(3, dtype=torch.bool)
        top = model._choose(None, torch.arange(3), store, scores, ask, stop)
        self.assertEqual(top[0].tolist(), [2, 4, 6, -1])
        self.assertEqual(top[1].tolist(), [3, -1, -1, -1])
        self.assertEqual(top[2].tolist(), [5, -1, -1, -1])

    def test_the_old_masks_still_apply_and_a_low_sink_blocks_nothing(self) -> None:
        model, store = self.fixture(0.0)
        scores = torch.full((2, store.lines + 1), 4.0)
        top = model._choose(None, torch.arange(2), store, scores, torch.tensor([1.0, -1.0]),
                            torch.zeros(2, dtype=torch.bool))
        self.assertTrue((top[0] >= 0).all())
        self.assertTrue((top[1] == -1).all())                        # ASK <= 0
        top = model._choose(None, torch.arange(2), store, scores, torch.ones(2), torch.tensor([False, True]))
        self.assertTrue((top[0] >= 0).all() and (top[1] == -1).all())   # stop
        model, store = self.fixture(-100.0)
        top = model._choose(None, torch.arange(2), store, scores, torch.ones(2), torch.zeros(2, dtype=torch.bool))
        self.assertTrue((top >= 0).all())

    def test_ineligible_cards_stay_minus_one(self) -> None:
        model, store = self.fixture(-100.0)
        scores = torch.full((1, store.lines + 1), -math.inf)
        scores[0, 3] = 1.0
        top = model._choose(None, torch.arange(1), store, scores, torch.ones(1), torch.zeros(1, dtype=torch.bool))
        self.assertEqual(top[0].tolist(), [3, -1, -1, -1])

    def test_set_cross_entropy_with_the_sink_matches_a_hand_computation(self) -> None:
        scores = torch.tensor([[1.0, 2.0, -1.0, 0.5], [0.3, -0.7, 2.2, 1.1], [1.0, -math.inf, 0.0, 2.0]])
        target = torch.tensor([[True, False, True, False], [False] * 4, [False, False, False, True]])
        sink = torch.tensor(0.4)
        got = set_cross_entropy_with_sink(scores, target, sink)
        denominators = [sum(math.exp(s) for s in row if s != -math.inf) + math.exp(0.4) for row in scores.tolist()]
        want = [-math.log((math.exp(1.0) + math.exp(-1.0)) / denominators[0]),     # a set target
                -math.log(math.exp(0.4) / denominators[1]),                         # nothing to fetch: the sink
                -math.log(math.exp(2.0) / denominators[2])]
        self.assertTrue(torch.allclose(got, torch.tensor(want), atol=1e-5), (got, want))
        # With a sink of -inf, rows that have a target equal the plain set cross-entropy.
        plain = set_cross_entropy(scores[[0, 2]], target[[0, 2]])
        none = set_cross_entropy_with_sink(scores[[0, 2]], target[[0, 2]], torch.tensor(-math.inf))
        self.assertTrue(torch.allclose(none, plain, atol=1e-6))

    def test_the_sink_cross_entropy_has_gradient_for_the_sink_on_both_kinds_of_row(self) -> None:
        scores = torch.randn(2, 5)
        target = torch.tensor([[True, False, False, False, True], [False] * 5])
        for rows in ([0], [1]):
            sink = torch.tensor(0.0, requires_grad=True)
            set_cross_entropy_with_sink(scores[rows], target[rows], sink).sum().backward()
            self.assertNotEqual(sink.grad.item(), 0.0)
            # A set row pushes the sink down; a nothing-to-fetch row pulls it up.
            self.assertEqual(sink.grad.item() > 0, rows == [0])

    def test_forward_ask_loss_includes_the_sink_and_trains_it(self) -> None:
        batch = synthetic_batch(seed=2)
        model = tiny_model(fetch_sink=True)
        plain = tiny_model()
        plain.load_state_dict({k: v for k, v in model.state_dict().items() if k in plain.state_dict()})
        for mode, p_own in (("teacher", 0.0), ("own", 0.5)):
            model.zero_grad(set_to_none=True)
            out = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
            ref = plain(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
            self.assertTrue(torch.isfinite(out["ask"]), mode)
            self.assertNotEqual(out["ask"].item(), ref["ask"].item())    # extra denominator term and rows
            out["loss"].backward()
            self.assertIsNotNone(model.heads.ask_sink.grad, mode)
            self.assertNotEqual(model.heads.ask_sink.grad.item(), 0.0, mode)
            self.assertGreater(model.decoder.cross_sink.grad.abs().sum().item(), 0.0, mode)

    def test_only_the_ask_terms_and_the_decoder_attention_change(self) -> None:
        """With the sink effects neutralised (ASK sink -inf, decoder sink -inf), forward matches the plain model
        on lm, ans and halt; the ASK loss differs only through the extra rows (nothing-to-fetch rows)."""
        batch = synthetic_batch(seed=2)
        model = tiny_model(fetch_sink=True)
        plain = tiny_model()
        plain.load_state_dict({k: v for k, v in model.state_dict().items() if k in plain.state_dict()})
        with torch.no_grad():
            model.heads.ask_sink.fill_(-math.inf)
            model.decoder.cross_sink.fill_(-math.inf)
        out = model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        ref = plain(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        for name in ("lm", "ans", "halt"):
            self.assertTrue(torch.allclose(out[name], ref[name], atol=1e-5), name)


if __name__ == "__main__":
    unittest.main()
