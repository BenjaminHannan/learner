"""S4 `ent_key` pre-run tests (design/info-constraints/S4-STAGE0-CARD.md §2). DRAFT.

1. Flag off (only S2 on) is bit-identical to D + S2 as committed at e548d89d2 (the S3 head of review round 12);
   flag-off identity to 73b8e0224 is `tests/test_premonition_decoder_raw_cards.py` on the same code.
2. Paired start: shared weights and the global stream equal D + S2's; with kappa_e = 0 the ASK scores are identical.
3. The entity term equals kappa_e * (pi . e_l) by hand; NULL and entity-free cards get 0.
4. Every mode trains with finite losses and gradients, kappa_e is trained by L_ask; refusals; config round trip.
"""
from __future__ import annotations

import math
import unittest

import torch

from premonition import train as ptrain
from premonition.config import MiniConfig
from premonition.model import _norm, PremonitionMini
from tests.test_premonition_decoder_raw_cards import differences, everything, modules_at
from tests.test_premonition_model import VOCAB, synthetic_batch

S3_HEAD = "e548d89d207fb73245b28588811e8acc7e441598"   # the S3 head of review round 12


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def build(config, seed: int, cls=PremonitionMini):
    torch.manual_seed(seed)
    model = cls(config)
    return model, torch.get_rng_state()


def first_ask(model, batch):
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    everyone = torch.arange(batch.q_visit.shape[0])
    rows, _, _, scores = model._step(episode, everyone, 0, store)
    return store, episode, everyone, rows, scores


class FlagOffMatchesS3HeadTest(unittest.TestCase):
    def test_only_decoder_raw_cards_on_matches_e548d89d2(self) -> None:
        cfg, _, mod, trn = modules_at(S3_HEAD, "premonition_s3head")
        for variant in ("D", "D-noptr"):
            for seed in (0, 1):
                with self.subTest(variant=variant, seed=seed):
                    mine = everything(PremonitionMini, tiny(variant, decoder_raw_cards=True), ptrain, seed)
                    theirs = everything(mod.PremonitionMini, cfg.MiniConfig.preset(
                        variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, decoder_raw_cards=True),
                        trn, seed)
                    self.assertEqual(differences(mine, theirs), [])


class EntKeyTest(unittest.TestCase):
    def test_paired_start_and_identical_scores_at_init(self) -> None:
        for size in ("tiny", "full"):
            with self.subTest(size=size):
                plain = (tiny("D", decoder_raw_cards=True) if size == "tiny"
                         else MiniConfig.preset("D", "full", decoder_raw_cards=True))
                control, rng_c = build(plain, 3)
                treated, rng_t = build(plain.with_(ent_key=True), 3)
                self.assertTrue(torch.equal(rng_c, rng_t))
                shared = dict(control.named_parameters())
                mine = dict(treated.named_parameters())
                self.assertEqual(sorted(set(mine) - set(shared)), ["ent_query.bias", "ent_query.weight", "kappa_e"])
                for name, value in shared.items():
                    self.assertTrue(torch.equal(value, mine[name]), name)
                self.assertEqual(float(treated.kappa_e), 0.0)
        control, _ = build(tiny("D", decoder_raw_cards=True), 1)
        treated, _ = build(tiny("D", decoder_raw_cards=True, ent_key=True), 1)
        batch = synthetic_batch(seed=2)
        with torch.no_grad():
            a = first_ask(control.eval(), batch)[4]
            b = first_ask(treated.eval(), batch)[4]
        self.assertTrue(torch.equal(a, b))                                   # kappa_e = 0: same ASK scores

    def test_entity_term_by_hand(self) -> None:
        model, _ = build(tiny("D", decoder_raw_cards=True, ent_key=True), 0)
        model.eval()
        with torch.no_grad():
            model.kappa_e.fill_(2.5)
        batch = synthetic_batch(seed=4)
        n_ent = model.config.n_ent
        with torch.no_grad():
            store, episode, everyone, rows, _ = first_ask(model, batch)
            register = _norm(rows[:, model._register_base])
            got = model._entity_scores(register, store, episode, everyone)
            mentions = model._mentions(batch)
            logits = model.ent_query(register).float()
            for q in range(batch.q_visit.shape[0]):
                allowed = mentions[q]
                pi = torch.zeros(n_ent)
                if allowed.any():
                    pi[allowed] = torch.softmax(logits[q][allowed], 0)
                v = int(batch.q_visit[q])
                for line in range(store.lines):
                    ents = [int(e) for e in store.ents[v, line] if int(e) >= 0]
                    want = 2.5 * (sum(float(pi[e]) for e in ents) / len(ents)) if ents else 0.0
                    self.assertTrue(math.isclose(float(got[q, line]), want, rel_tol=1e-5, abs_tol=1e-6))
                self.assertEqual(float(got[q, store.null]), 0.0)                 # NULL gets 0

    def test_every_mode_trains_and_kappa_e_learns_from_l_ask(self) -> None:
        for variant in ("D", "D-noptr"):
            with self.subTest(variant=variant):
                model, _ = build(tiny(variant, decoder_raw_cards=True, ent_key=True), 0)
                batch = synthetic_batch(seed=3)
                for mode in ("gold", "teacher", "own"):
                    model.zero_grad(set_to_none=True)
                    out = model(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
                    out["loss"].backward()
                    self.assertTrue(torch.isfinite(out["loss"]))
                    for name, param in model.named_parameters():
                        if param.grad is not None:
                            self.assertTrue(torch.isfinite(param.grad).all(), name)
                    if mode == "teacher":
                        self.assertNotEqual(float(model.kappa_e.grad), 0.0)      # L_ask reaches kappa_e
                    if mode == "gold":                                         # stage 1: no ASK set loss
                        self.assertTrue(model.kappa_e.grad is None or float(model.kappa_e.grad) == 0.0)
                model.eval()
                model.answer(batch)
                ptrain.answer_with_gold(model, batch)
                window = (batch.q_line - 6).clamp_min(1)
                model.answer(batch, wipe="store", window_line=window)
                model.answer(batch, wipe="full", window_line=window)

    def test_reset_parameters_keeps_the_pairing(self) -> None:
        control, _ = build(tiny("D", decoder_raw_cards=True), 2)
        model, _ = build(tiny("D", decoder_raw_cards=True, ent_key=True), 2)
        before = model.ent_query.weight.clone()
        torch.manual_seed(9)
        control.reset_parameters()
        rng_c = torch.get_rng_state()
        torch.manual_seed(9)
        model.reset_parameters()
        self.assertTrue(torch.equal(torch.get_rng_state(), rng_c))
        shared = dict(control.named_parameters())
        for name, value in model.named_parameters():
            if name in shared:
                self.assertTrue(torch.equal(value, shared[name]), name)
        self.assertTrue(torch.equal(model.ent_query.weight, before))
        self.assertEqual(float(model.kappa_e), 0.0)

    def test_refusals_and_config_round_trip(self) -> None:
        from premonition.answer_path import ThinkGatedMini
        with self.assertRaises(ValueError):
            tiny("D-noask", ent_key=True)
        with self.assertRaises(ValueError):
            ThinkGatedMini(tiny("D", ent_key=True))
        flagged = tiny("D", decoder_raw_cards=True, ent_key=True)
        values = ptrain.mini_config_dict(flagged)
        self.assertTrue(values["ent_key"])
        self.assertEqual(ptrain.mini_config_from(values), flagged)
        self.assertNotIn("ent_key", ptrain.mini_config_dict(tiny("D")))
        plain = MiniConfig.preset("D", "full", decoder_raw_cards=True)
        self.assertEqual(plain.with_(ent_key=True).num_parameters() - plain.num_parameters(),
                         plain.with_(ent_key=True).parameter_breakdown()["ent_key"])

    def test_flop_hand_count_follows_the_measured_increment(self) -> None:
        from premonition.flops import measure_mini, mini_hand_count
        s2, _ = build(tiny("D", decoder_raw_cards=True), 0)
        s4, _ = build(tiny("D", decoder_raw_cards=True, ent_key=True), 0)
        batch = synthetic_batch(visits=2, lines=30, seed=3)
        a = measure_mini(s2, batch, mode="teacher", generator=torch.Generator().manual_seed(3))
        b = measure_mini(s4, batch, mode="teacher", generator=torch.Generator().manual_seed(3))
        measured = b.flops - a.flops
        hand = mini_hand_count(s4.config, batch, b.question_loops) - mini_hand_count(s2.config, batch, a.question_loops)
        self.assertGreater(measured, 0)
        self.assertLess(abs(measured - hand) / measured, 0.25, (measured, hand))


if __name__ == "__main__":
    unittest.main()
