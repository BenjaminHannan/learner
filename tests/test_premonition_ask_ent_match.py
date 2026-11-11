"""S6 `ask_ent_match` pre-run tests (design/info-constraints/S6-STAGE0-CARD.md §2). DRAFT.

1. Flag off (S2 + S5 on) is bit-identical to the reviewed S5 code at 7c0456589.
2. Paired start; with kappa_a frozen at 0 the losses and gradients of every shared weight are identical.
3. The ASK term is kappa_a * m_l, m_l = 1 where card l names a question-span entity, NULL 0 (by hand).
4. dL_ask/dkappa_a != 0 at kappa_a = 0 on a teacher batch; every mode trains with finite gradients; refusals; config.
"""
from __future__ import annotations

import unittest

import torch

from premonition import train as ptrain
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from tests.test_premonition_decoder_raw_cards import differences, everything, modules_at
from tests.test_premonition_model import VOCAB, synthetic_batch

S5_HEAD = "7c0456589"
BASE = dict(decoder_raw_cards=True, dec_ent_match=True)


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def toy(**flags):
    """A far-fact toy config and batch: its questions name an entity, so cards can match."""
    from premonition.toy import ToySpec, toy_set
    spec = ToySpec()
    config = MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64, **flags)
    return config, ptrain.label_free(toy_set(spec, 1, 4, 77)[0])


def build(config, seed: int):
    torch.manual_seed(seed)
    model = PremonitionMini(config)
    return model, torch.get_rng_state()


class FlagOffMatchesS5HeadTest(unittest.TestCase):
    def test_s2_s5_on_matches_7c0456589(self) -> None:
        import subprocess
        from pathlib import Path
        full = subprocess.run(["git", "rev-parse", S5_HEAD], cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True).stdout.strip() or S5_HEAD
        cfg, _, mod, trn = modules_at(full, "premonition_s5head")
        for seed in (0, 1):
            with self.subTest(seed=seed):
                mine = everything(PremonitionMini, tiny("D", **BASE), ptrain, seed)
                theirs = everything(mod.PremonitionMini, cfg.MiniConfig.preset(
                    "D", "tiny", vocab_size=VOCAB, window=16, max_loops=6, **BASE), trn, seed)
                self.assertEqual(differences(mine, theirs), [])


class AskEntMatchTest(unittest.TestCase):
    def test_paired_start_and_identity_while_frozen_at_zero(self) -> None:
        control, rng_c = build(tiny("D", **BASE), 3)
        treated, rng_t = build(tiny("D", ask_ent_match=True, **BASE), 3)
        self.assertTrue(torch.equal(rng_c, rng_t))
        shared = dict(control.named_parameters())
        mine = dict(treated.named_parameters())
        self.assertEqual(sorted(set(mine) - set(shared)), ["ask_kappa"])
        for name, value in shared.items():
            self.assertTrue(torch.equal(value, mine[name]), name)
        config, batch = toy(**BASE)
        control, _ = build(config, 4)
        treated, _ = build(config.with_(ask_ent_match=True), 4)
        treated.ask_kappa.requires_grad_(False)                              # stage 1: frozen at 0
        for mode in ("gold", "teacher"):
            outs = []
            for model in (control, treated):
                model.zero_grad(set_to_none=True)
                out = model(batch, mode=mode, generator=torch.Generator().manual_seed(5))
                out["loss"].backward()
                outs.append(out)
            for name in ("lm", "ask", "ans", "halt", "loss"):
                self.assertTrue(torch.equal(outs[0][name], outs[1][name]), f"{mode}.{name}")
            theirs = dict(treated.named_parameters())
            for name, value in control.named_parameters():
                a, b = value.grad, theirs[name].grad
                self.assertTrue((a is None and b is None) or torch.equal(a, b), f"{mode}.{name}")

    def test_term_is_kappa_a_times_match(self) -> None:
        config, batch = toy(ask_ent_match=True, **BASE)
        model, _ = build(config, 0)
        model.eval()
        with torch.no_grad():
            model.ask_kappa.fill_(1.5)
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            episode = model._start(batch, hidden, store, model._mentions(batch))
            everyone = torch.arange(batch.q_visit.shape[0])
            term = model._entity_scores(None, store, episode, everyone)
            vocab = config.vocab_size
            for q in range(batch.q_visit.shape[0]):
                v = int(batch.q_visit[q])
                start, end = (int(x) for x in batch.q_span[q])
                names = {int(t) - vocab for t in batch.tokens[v, start:end] if int(t) >= vocab}
                for line in range(store.lines):
                    ents = {int(e) for e in store.ents[v, line] if int(e) >= 0}
                    self.assertEqual(float(term[q, line]), 1.5 if ents & names else 0.0)
                self.assertEqual(float(term[q, store.null]), 0.0)                    # NULL
                self.assertEqual(float(term[q, int(batch.gold_lines[q, 0])]), 1.5)   # the gold card matches
            register = torch.zeros(everyone.numel(), config.d_model)
            query = model.heads.query(register)
            args = (query, episode.q_visit, episode.q_line, model.heads.log_kappa.exp(), model.think.age_bias)
            plain = store.ask(*args, questions=everyone)
            moved = store.ask(*args, questions=everyone, extra=term)
            live = plain > -1e8
            self.assertTrue(torch.allclose((moved - plain)[live], term[live]))
            self.assertTrue(bool((term > 0).any()) and bool((term == 0).any()))

    def test_kappa_a_has_gradient_at_zero_and_modes_train(self) -> None:
        config, toy_batch = toy(ask_ent_match=True, **BASE)
        model, _ = build(config, 0)
        out = model(toy_batch, mode="teacher", generator=torch.Generator().manual_seed(0),
                    weights={"ask": 1.0})
        out["loss"].backward()
        self.assertNotEqual(float(model.ask_kappa.grad), 0.0)                # live from the first ASK-loss step
        model, _ = build(tiny("D", ask_ent_match=True, **BASE), 0)
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
            tiny("D", decoder_raw_cards=True, ask_ent_match=True)                 # needs S5
        with self.assertRaises(ValueError):
            tiny("D", ask_ent_match=True, ent_key=True, **BASE)                   # one ASK extra at a time
        with self.assertRaises(ValueError):
            ThinkGatedMini(tiny("D", ask_ent_match=True, **BASE))
        flagged = tiny("D", ask_ent_match=True, **BASE)
        values = ptrain.mini_config_dict(flagged)
        self.assertTrue(values["ask_ent_match"])
        self.assertEqual(ptrain.mini_config_from(values), flagged)
        self.assertNotIn("ask_ent_match", ptrain.mini_config_dict(tiny("D", **BASE)))
        self.assertNotIn("ask_ent_match", ptrain.mini_config_dict(tiny("D")))
        model, _ = build(flagged, 0)
        self.assertEqual(model.parameter_breakdown(), flagged.parameter_breakdown())
        with torch.no_grad():
            model.ask_kappa.fill_(3.0)
        model.reset_parameters()
        self.assertEqual(float(model.ask_kappa.detach()), 0.0)


if __name__ == "__main__":
    unittest.main()
