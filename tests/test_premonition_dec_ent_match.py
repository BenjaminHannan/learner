"""S5 `dec_ent_match` pre-run tests (design/info-constraints/S5-STAGE0-CARD.md §2). DRAFT.

1. Flag off (only S2 on) is bit-identical to the reviewed code at 7a2f5a32a; flag-off identity to 73b8e0224 is
   `tests/test_premonition_decoder_raw_cards.py` on the same code.
2. Paired start; with kappa_d = 0 the decoder outputs, losses and gradients of shared weights are identical.
3. The bias lands on exactly the two rows (think card row, raw row) of every slot whose card names a question
   entity, and the attention logits move by kappa_d there only.
4. dL/dkappa_d != 0 on a batch with a matching card; every mode trains with finite gradients; refusals; config.
"""
from __future__ import annotations

import math
import unittest

import torch
import torch.nn.functional as F

from premonition import train as ptrain
from premonition.config import MiniConfig
from premonition.model import _norm, PremonitionMini, rope
from tests.test_premonition_decoder_raw_cards import differences, everything, modules_at
from tests.test_premonition_model import VOCAB, synthetic_batch

S4_HEAD = "7a2f5a32a"


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def toy(**flags):
    """A far-fact toy config and batch: its questions name an entity, so cards can match."""
    from premonition.toy import ToySpec, toy_set
    spec = ToySpec()
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64, **flags)
    return config, ptrain.label_free(toy_set(spec, 1, 4, 77)[0])


def build(config, seed: int, cls=PremonitionMini):
    torch.manual_seed(seed)
    model = cls(config)
    return model, torch.get_rng_state()


def gold_episode(model, batch):
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    everyone = torch.arange(batch.q_visit.shape[0])
    gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
    width = min(gold.shape[1], batch.gold_lines.shape[1] + 1, model.config.card_rows)
    cards = torch.where(gold, torch.arange(gold.shape[1]),
                        torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values
    model._insert(episode, store, everyone, cards)
    return store, episode, everyone, cards


def cross_logits(model, rows, valid, inputs, bias):
    """The decoder's cross-attention logits [n, heads, length, memory] (by hand, as Decoder.forward)."""
    dec = model.decoder
    x = model.embed(inputs)
    n, length, width = x.shape
    h = dec.heads
    q, k, v = dec.qkv(dec.norm1(x)).view(n, length, 3, h, -1).permute(2, 0, 3, 1, 4)
    pos = torch.arange(length)
    q, k = rope(q, pos, dec.base), rope(k, pos, dec.base)
    x = x + dec.proj(F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(n, length, width))
    q = dec.cross_q(dec.norm2(x)).view(n, length, h, -1).transpose(1, 2)
    kk, _ = dec.cross_kv(_norm(rows)).view(n, rows.shape[1], 2, h, -1).permute(2, 0, 3, 1, 4)
    logits = q @ kk.transpose(-1, -2) / math.sqrt(q.shape[-1])
    if bias is not None:
        logits = logits + bias[:, None, None, :]
    return logits.masked_fill(~valid[:, None, None, :], -math.inf)


class FlagOffMatchesS4HeadTest(unittest.TestCase):
    def test_only_decoder_raw_cards_on_matches_7a2f5a32a(self) -> None:
        import subprocess
        from pathlib import Path
        full = subprocess.run(["git", "rev-parse", S4_HEAD], cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True).stdout.strip() or S4_HEAD
        cfg, _, mod, trn = modules_at(full, "premonition_s4head")
        for variant in ("D", "D-noptr"):
            for seed in (0, 1):
                with self.subTest(variant=variant, seed=seed):
                    mine = everything(PremonitionMini, tiny(variant, decoder_raw_cards=True), ptrain, seed)
                    theirs = everything(mod.PremonitionMini, cfg.MiniConfig.preset(
                        variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, decoder_raw_cards=True),
                        trn, seed)
                    self.assertEqual(differences(mine, theirs), [])


class DecEntMatchTest(unittest.TestCase):
    def test_paired_start_and_identity_while_frozen_at_zero(self) -> None:
        control, rng_c = build(tiny("D", decoder_raw_cards=True), 3)
        treated, rng_t = build(tiny("D", decoder_raw_cards=True, dec_ent_match=True), 3)
        self.assertTrue(torch.equal(rng_c, rng_t))
        shared = dict(control.named_parameters())
        mine = dict(treated.named_parameters())
        self.assertEqual(sorted(set(mine) - set(shared)), ["dec_kappa"])
        for name, value in shared.items():
            self.assertTrue(torch.equal(value, mine[name]), name)
        config, batch = toy(decoder_raw_cards=True)
        control, _ = build(config, 4)
        treated, _ = build(config.with_(dec_ent_match=True), 4)
        treated.dec_kappa.requires_grad_(False)                              # stage 1: frozen at 0
        out_c = control(batch, mode="gold", weights={"ans": 1.0})
        out_t = treated(batch, mode="gold", weights={"ans": 1.0})
        self.assertTrue(torch.equal(out_c["ans"], out_t["ans"]))
        out_c["ans"].backward()
        out_t["ans"].backward()
        theirs = dict(treated.named_parameters())
        for name, value in control.named_parameters():
            a, b = value.grad, theirs[name].grad
            self.assertTrue((a is None and b is None) or torch.equal(a, b), name)   # bit-identical gradients
        treated.dec_kappa.requires_grad_(True)                               # trainable at 0: same forward values
        self.assertTrue(torch.allclose(treated(batch, mode="gold", weights={"ans": 1.0})["ans"], out_c["ans"]))

    def test_bias_lands_on_matching_card_rows_only(self) -> None:
        config, batch = toy(decoder_raw_cards=True, dec_ent_match=True)
        model, _ = build(config, 0)
        model.eval()
        with torch.no_grad():
            model.dec_kappa.fill_(1.75)
        base, think, cards = model._card_base, model.config.rows, model.config.cards
        with torch.no_grad():
            store, episode, everyone, inserted = gold_episode(model, batch)
            bias = model._match_bias(episode)
            q_ents = episode.q_ents
            for q in range(batch.q_visit.shape[0]):
                real = [int(c) for c in inserted[q] if int(c) >= 0]
                for slot, card in enumerate(real):
                    names = {int(e) for e in (store.ents[int(batch.q_visit[q]), card] if card < store.lines else [])
                             if int(e) >= 0}
                    want = 1.75 if any(bool(q_ents[q, e]) for e in names) else 0.0
                    self.assertEqual(float(bias[q, base + slot]), want)
                    self.assertEqual(float(bias[q, think + slot]), want)
                others = torch.ones(think + cards, dtype=torch.bool)
                others[base:base + cards] = False
                others[think:think + cards] = False
                self.assertTrue(bool((bias[q, others] == 0).all()))
            inputs = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
            with_bias = cross_logits(model, episode.x, episode.valid, inputs, bias)
            without = cross_logits(model, episode.x, episode.valid, inputs, None)
            finite = torch.isfinite(without)
            moved = (with_bias - without).masked_fill(~finite, 0.0)
            self.assertTrue(torch.allclose(moved, bias[:, None, None, :].expand_as(moved).masked_fill(~finite, 0.0),
                                           atol=1e-5))
            self.assertTrue(bool((bias > 0).any()))                          # the batch does have matches

    def test_kappa_d_has_gradient_at_zero_and_modes_train(self) -> None:
        config, toy_batch = toy(decoder_raw_cards=True, dec_ent_match=True)
        model, _ = build(config, 0)
        out = model(toy_batch, mode="gold", weights={"ans": 1.0})
        out["ans"].backward()
        self.assertNotEqual(float(model.dec_kappa.grad), 0.0)                # non-zero from step 1
        model, _ = build(tiny("D", decoder_raw_cards=True, dec_ent_match=True), 0)
        batch = synthetic_batch(seed=3)
        for mode in ("gold", "teacher", "own"):
            model.zero_grad(set_to_none=True)
            out = model(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            self.assertTrue(torch.isfinite(out["loss"]))
            for name, param in model.named_parameters():
                if param.grad is not None:
                    self.assertTrue(torch.isfinite(param.grad).all(), name)
        model.eval()
        window = (batch.q_line - 6).clamp_min(1)
        for kwargs in ({}, dict(wipe="store", window_line=window), dict(wipe="full", window_line=window)):
            model.answer(batch, **kwargs)
        ptrain.answer_with_gold(model, batch)

    def test_refusals_and_config(self) -> None:
        from premonition.answer_path import ThinkGatedMini
        with self.assertRaises(ValueError):
            tiny("D", dec_ent_match=True)                                    # needs S2
        with self.assertRaises(ValueError):
            tiny("D", decoder_raw_cards=True, card_address=True, dec_ent_match=True)
        with self.assertRaises(ValueError):
            ThinkGatedMini(tiny("D", decoder_raw_cards=True, dec_ent_match=True))
        flagged = tiny("D", decoder_raw_cards=True, dec_ent_match=True)
        values = ptrain.mini_config_dict(flagged)
        self.assertTrue(values["dec_ent_match"])
        self.assertEqual(ptrain.mini_config_from(values), flagged)
        self.assertNotIn("dec_ent_match", ptrain.mini_config_dict(tiny("D")))
        model, _ = build(flagged, 0)
        self.assertEqual(model.parameter_breakdown(), flagged.parameter_breakdown())
        with torch.no_grad():
            model.dec_kappa.fill_(3.0)
        model.reset_parameters()
        self.assertEqual(float(model.dec_kappa), 0.0)


if __name__ == "__main__":
    unittest.main()
