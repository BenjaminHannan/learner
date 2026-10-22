"""S3 `card_address` pre-run tests (design/info-constraints/S3-STAGE0-CARD.md §2). DRAFT.

1. Flag off is bit-identical to D + S2 as committed at 90077ef2b (coordinator-reviewed): with only
   `decoder_raw_cards` on, init, RNG, the three training modes, answers with wipes, `answer_with_gold` and trainer
   steps match the modules loaded from git at that commit. Flag-off identity to 73b8e0224 (everything off) is
   `tests/test_premonition_decoder_raw_cards.py`, which runs on the same code.
2. Paired start: D + S2 + S3 has every shared weight and the global RNG stream of D + S2 at the same seed.
3. The address block follows the ring: same slot as the card and raw rows, overwritten together, never valid.
4. The decoder takes the card rows' and raw rows' keys from the address rows and every value from the rows.
5. Every mode trains with finite losses and gradients; refusals; hand FLOPs follow the measured increment.
"""
from __future__ import annotations

import unittest

import torch

from premonition import train as ptrain
from premonition.config import MiniConfig
from premonition.model import ROW_CARD, _norm, PremonitionMini
from premonition.store import age_bucket
from tests.test_premonition_decoder_raw_cards import differences, everything, modules_at
from tests.test_premonition_model import VOCAB, synthetic_batch

S2_COMMIT = "90077ef2b09a66382c6d53fc46c8d881791a4455"


def s2_modules() -> tuple:
    """(config, store, model, train) exactly as at the reviewed S2 commit. The commit exists on this branch only:
    a rebase or squash merge re-pins it to the merged S2 head (Q41)."""
    return modules_at(S2_COMMIT, "premonition_s2")


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def build(config, seed: int, cls=PremonitionMini):
    torch.manual_seed(seed)
    model = cls(config)
    return model, torch.get_rng_state()


def preloaded(model, batch, cards=None):
    """An episode with each question's gold card inserted (or `cards` [Q, 1])."""
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    everyone = torch.arange(batch.q_visit.shape[0])
    if cards is None:
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        cards = torch.where(gold, torch.arange(gold.shape[1]),
                            torch.full_like(gold, -1, dtype=torch.long)).topk(1, 1).values
    model._insert(episode, store, everyone, cards)
    return store, episode, everyone


class FlagOffMatchesReviewedS2Test(unittest.TestCase):
    def test_only_decoder_raw_cards_on_matches_90077ef2b(self) -> None:
        s2_config, _, s2_model, s2_train = s2_modules()
        for variant in ("D", "D-noptr"):
            for seed in (0, 1):
                with self.subTest(variant=variant, seed=seed):
                    mine = everything(PremonitionMini, tiny(variant, decoder_raw_cards=True), ptrain, seed)
                    theirs = everything(s2_model.PremonitionMini, s2_config.MiniConfig.preset(
                        variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, decoder_raw_cards=True),
                        s2_train, seed)
                    self.assertEqual(differences(mine, theirs), [])


class CardAddressTest(unittest.TestCase):
    def test_paired_start(self) -> None:
        for size in ("tiny", "full"):
            with self.subTest(size=size):
                plain = (tiny("D", decoder_raw_cards=True) if size == "tiny"
                         else MiniConfig.preset("D", "full", decoder_raw_cards=True))
                control, rng_c = build(plain, 3)
                treated, rng_t = build(plain.with_(card_address=True), 3)
                self.assertTrue(torch.equal(rng_c, rng_t))
                shared = dict(control.named_parameters())
                mine = dict(treated.named_parameters())
                self.assertEqual(sorted(set(mine) - set(shared)), ["address.pool.bias", "address.pool.weight",
                                                                   "address.proj.bias", "address.proj.weight"])
                for name, value in shared.items():
                    self.assertTrue(torch.equal(value, mine[name]), name)
                self.assertTrue(torch.equal(treated.address.pool.weight, treated.writer.pool.weight))
                self.assertEqual(treated.config.parameter_breakdown(), treated.parameter_breakdown())
        other, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 4)
        self.assertFalse(torch.equal(other.address.proj.weight,
                                     build(tiny("D", decoder_raw_cards=True, card_address=True), 3)[0]
                                     .address.proj.weight))                         # seed-dependent init

    def test_refusals(self) -> None:
        from premonition.answer_path import CardBypassMini
        with self.assertRaises(ValueError):
            tiny("D", card_address=True)                                   # needs S2
        with self.assertRaises(ValueError):
            tiny("D-noask", decoder_raw_cards=True, card_address=True)
        with self.assertRaises(ValueError):
            CardBypassMini(tiny("D", decoder_raw_cards=True, card_address=True))

    def test_every_mode_trains_and_answers(self) -> None:
        for variant in ("D", "D-noptr"):
            with self.subTest(variant=variant):
                model, _ = build(tiny(variant, decoder_raw_cards=True, card_address=True), 0)
                batch = synthetic_batch(seed=3)
                for mode in ("gold", "teacher", "own"):
                    model.zero_grad(set_to_none=True)
                    out = model(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
                    out["loss"].backward()
                    self.assertTrue(torch.isfinite(out["loss"]))
                    for name, param in model.named_parameters():
                        if param.grad is not None:
                            self.assertTrue(torch.isfinite(param.grad).all(), name)
                    self.assertIsNotNone(model.address.proj.weight.grad)          # the address is trained
                model.eval()
                model.answer(batch)
                ptrain.answer_with_gold(model, batch)
                window = (batch.q_line - 6).clamp_min(1)
                model.answer(batch, wipe="store", window_line=window)
                model.answer(batch, wipe="full", window_line=window)

    def test_address_rows_follow_the_ring_and_think_skips_them(self) -> None:
        model, _ = build(tiny("D", decoder_raw_cards=True, card_address=True, card_rows=2, top_k=1), 0)
        model.eval()
        config = model.config
        batch = synthetic_batch(seed=7)
        think, cards = config.rows, config.cards
        address = slice(think + cards, think + 2 * cards)
        with torch.no_grad():
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            episode = model._start(batch, hidden, store, model._mentions(batch))
            self.assertEqual(episode.x.shape[1], think + 2 * cards)
            everyone = torch.arange(batch.q_visit.shape[0])
            seen = []
            for line in range(3):                                     # three distinct cards into two slots
                model._insert(episode, store, everyone, torch.full((everyone.numel(), 1), line))
                slot = line % 2
                visit = batch.q_visit
                want = (store.addresses[visit, line].float()
                        + model.think.age(age_bucket(batch.q_line - line, config.age_buckets)).float()
                        + model.think.row_type.weight[ROW_CARD].float())
                self.assertTrue(torch.allclose(episode.x[:, think + cards + slot], want))
                seen.append(episode.x[:, address].clone())
            self.assertFalse(episode.valid[:, address].any())               # never memory itself
            self.assertFalse(torch.equal(seen[2][:, 0], seen[0][:, 0]))     # third card overwrote slot 0
            self.assertTrue(torch.equal(seen[2][:, 1], seen[1][:, 1]))      # and kept slot 1
            before = episode.x[:, think:].clone()
            model._step(episode, everyone, 0, store)
            self.assertTrue(torch.equal(episode.x[:, think:], before))      # Think skips raw + address rows

    def test_keys_from_address_values_from_rows(self) -> None:
        """`_decode_logits` equals an independent reference: cross-attention K from `_norm(address)` at the card and
        raw slots and from `_norm(row)` elsewhere, V from `_norm(row)` everywhere; and the splice matters."""
        import torch.nn.functional as F
        from premonition.model import rope
        model, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 0)
        model.eval()
        config, dec = model.config, model.decoder
        think, cards, base = config.rows, config.cards, model._card_base
        batch = synthetic_batch(seed=5)
        with torch.no_grad():
            store, episode, everyone = preloaded(model, batch)
            model._step(episode, everyone, 0, store)
            x_rows, valid = episode.x, episode.valid
            inputs = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
            got = model._decode_logits(x_rows, valid, inputs)

            memory, address = x_rows[:, :think + cards], x_rows[:, think + cards:]
            key_rows = torch.cat([memory[:, :base], address, memory[:, base + cards:think], address], dim=1)
            mask = valid[:, :think + cards]
            x = model.embed(inputs)
            n, length, width = x.shape
            h = dec.heads
            q, k, v = dec.qkv(dec.norm1(x)).view(n, length, 3, h, -1).permute(2, 0, 3, 1, 4)
            pos = torch.arange(length)
            q, k = rope(q, pos, dec.base), rope(k, pos, dec.base)
            x = x + dec.proj(F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2)
                             .reshape(n, length, width))
            q = dec.cross_q(dec.norm2(x)).view(n, length, h, -1).transpose(1, 2)
            kk, _ = dec.cross_kv(_norm(key_rows)).view(n, key_rows.shape[1], 2, h, -1).permute(2, 0, 3, 1, 4)
            _, vv = dec.cross_kv(_norm(memory)).view(n, memory.shape[1], 2, h, -1).permute(2, 0, 3, 1, 4)
            att = F.scaled_dot_product_attention(q, kk, vv, attn_mask=mask[:, None, None, :])
            x = x + dec.cross_proj(att.transpose(1, 2).reshape(n, length, width))
            want = dec.norm(x + dec.mlp(dec.norm3(x)))
            plain = dec(model.embed(inputs), memory, mask)                       # keys from the rows themselves
        self.assertTrue(torch.allclose(got, want, atol=1e-6), (got - want).abs().max())
        self.assertFalse(torch.allclose(got, plain, atol=1e-6))                 # the address keys are used

    def test_building_s3_does_not_reseed_anything(self) -> None:
        build(tiny("D", decoder_raw_cards=True, card_address=True), 11)
        self.assertEqual(torch.initial_seed(), 11)                              # no manual_seed inside

    def test_reset_parameters_keeps_the_s3_init_rules_and_the_paired_stream(self) -> None:
        control, _ = build(tiny("D", decoder_raw_cards=True), 2)
        model, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 2)
        before = model.address.proj.weight.clone()
        torch.manual_seed(9)
        control.reset_parameters()
        rng_c = torch.get_rng_state()
        torch.manual_seed(9)
        model.reset_parameters()
        self.assertTrue(torch.equal(torch.get_rng_state(), rng_c))            # same global stream after a re-init
        shared = dict(control.named_parameters())
        for name, value in model.named_parameters():
            if name in shared:
                self.assertTrue(torch.equal(value, shared[name]), name)        # same shared weights
        self.assertTrue(torch.equal(model.address.pool.weight, model.writer.pool.weight))
        self.assertTrue(torch.equal(model.address.proj.weight, before))       # its own generator, same seed

    def test_refused_on_any_subclass(self) -> None:
        from premonition.answer_path import ThinkGatedMini
        from premonition.card_pools import MeanPoolMini
        for cls in (ThinkGatedMini, MeanPoolMini):
            with self.subTest(cls=cls.__name__), self.assertRaises(ValueError):
                cls(tiny("D", decoder_raw_cards=True, card_address=True))

    def test_plain_config_dict_and_digest_match_the_base_commit(self) -> None:
        from premonition.identity import config_digest
        from tests.test_premonition_decoder_raw_cards import base_modules
        base_config, _, _, base_train = base_modules()
        for variant in ("D", "D-noask", "D-noptr"):
            mine = ptrain.mini_config_dict(MiniConfig.preset(variant, "full"))
            theirs = base_train.mini_config_dict(base_config.MiniConfig.preset(variant, "full"))
            self.assertEqual(mine, theirs)
            self.assertEqual(config_digest(mine), config_digest(theirs))
        flagged = MiniConfig.preset("D", "tiny", decoder_raw_cards=True, card_address=True)
        values = ptrain.mini_config_dict(flagged)
        self.assertTrue(values["decoder_raw_cards"] and values["card_address"])
        self.assertEqual(ptrain.mini_config_from(values), flagged)             # round trip keeps the flags
        self.assertEqual(ptrain.mini_config_from(theirs), MiniConfig.preset("D-noptr", "full"))   # old dicts load

    def test_band_excludes_s3(self) -> None:
        plain = MiniConfig.preset("D", "full", decoder_raw_cards=True)
        flagged = plain.with_(card_address=True)
        self.assertEqual(flagged.num_parameters() - plain.num_parameters(),
                         flagged.parameter_breakdown()["card_address"])

    def test_flop_hand_count_follows_the_measured_increment(self) -> None:
        from premonition.flops import measure_mini, mini_hand_count
        s2, _ = build(tiny("D", decoder_raw_cards=True), 0)
        s3, _ = build(tiny("D", decoder_raw_cards=True, card_address=True), 0)
        for visits, lines, seed in ((2, 16, 1), (2, 30, 3)):
            batch = synthetic_batch(visits=visits, lines=lines, seed=seed)
            a = measure_mini(s2, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            b = measure_mini(s3, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            self.assertEqual(a.question_loops, b.question_loops)
            measured = b.flops - a.flops
            hand = mini_hand_count(s3.config, batch, b.question_loops) - mini_hand_count(s2.config, batch,
                                                                                        a.question_loops)
            self.assertGreater(measured, 0)
            self.assertLess(abs(measured - hand) / measured, 0.25, (measured, hand))


if __name__ == "__main__":
    unittest.main()
