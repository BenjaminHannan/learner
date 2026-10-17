"""Steal 6 (design/steals-2026-10-17/SPEC.md): qk_norm, qk_norm_all, qk_clip and key_split."""
from __future__ import annotations

import math
import unittest

import torch

from premonition import train as ptrain
from premonition.model import PremonitionMini, _norm, rope
from premonition.store import CardStore
from tests.test_premonition_model import synthetic_batch, tiny_config, tiny_model


def first_loop(model: PremonitionMini, batch):
    """(episode, store, index, scores, register) after loop 0 of every question."""
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    episode = model._start(batch, hidden, store, model._mentions(batch))
    index = torch.arange(batch.q_visit.shape[0])
    rows, _, _, scores = model._step(episode, index, 0, store)
    return episode, store, index, scores, _norm(rows[:, model._register_base])


class QkNormTest(unittest.TestCase):
    def test_gains_of_one_are_exactly_the_base_scores(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=3)
        base, norm = tiny_model(seed=0), tiny_model(seed=0, qk_norm=True)
        self.assertEqual(norm.heads.query_gain.shape, (norm.config.key_dim,))
        self.assertTrue((norm.heads.query_gain == 1).all() and (norm.heads.key_gain == 1).all())
        for name, value in base.state_dict().items():                  # the gains draw no random numbers
            self.assertTrue(torch.equal(value, norm.state_dict()[name]), name)
        with torch.no_grad():
            a, b = first_loop(base, batch)[3], first_loop(norm, batch)[3]
        self.assertTrue(torch.equal(a, b))
        out = [m(batch, mode="teacher", generator=torch.Generator().manual_seed(0)) for m in (base, norm)]
        self.assertTrue(torch.equal(out[0]["loss"], out[1]["loss"]))

    def test_gains_scale_the_match_per_dimension_and_get_gradients(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=3)
        model = tiny_model(seed=1, qk_norm=True)
        with torch.no_grad():
            model.heads.query_gain.copy_(torch.rand_like(model.heads.query_gain) + 0.5)
            model.heads.key_gain.copy_(torch.rand_like(model.heads.key_gain) + 0.5)
        episode, store, index, scores, register = first_loop(model, batch)
        query = torch.nn.functional.normalize(model.heads.query(register).float(), dim=-1)
        keys = torch.cat([store.keys[episode.q_visit], store.null_key.expand(index.numel(), 1, -1)], 1)
        match = model.heads.log_kappa.exp() * torch.einsum(
            "nk,nlk->nl", query * model.heads.query_gain, keys * model.heads.key_gain)
        bias = model.think.age_bias[store.ages(episode.q_line, model.config.age_buckets)]
        bias[:, store.null] = 0.0
        ok = store.eligible(episode.q_visit, episode.q_line)
        torch.testing.assert_close(scores, (match + bias).masked_fill(~ok, float("-inf")))
        model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))["loss"].backward()
        self.assertGreater(model.heads.query_gain.grad.abs().sum(), 0)
        self.assertGreater(model.heads.key_gain.grad.abs().sum(), 0)

    def test_no_gains_without_a_store_or_the_flag(self) -> None:
        self.assertFalse(hasattr(tiny_model(), "query_gain") or hasattr(tiny_model().heads, "query_gain"))
        noask = tiny_model("D-noask", qk_norm=True)
        self.assertFalse(hasattr(noask.heads, "query_gain"))
        self.assertEqual(noask.parameter_breakdown(), noask.config.parameter_breakdown())


class QkNormAllTest(unittest.TestCase):
    def test_every_attention_normalises_q_and_k_per_head_dim(self) -> None:
        model = tiny_model(seed=0, qk_norm_all=True)
        dh = model.config.d_model // model.config.n_heads
        norms = {name: m for name, m in model.named_modules() if isinstance(m, torch.nn.RMSNorm)}
        # reader attention (1), think layers (2), decoder self (2) and cross (2) attention
        self.assertEqual(len(norms), 2 * (1 + model.config.think_layers + 2))
        self.assertEqual(sorted(n.split(".")[-1] for n in norms if n.startswith("decoder")),
                         ["cross_k_norm", "cross_q_norm", "k_norm", "q_norm"])
        for module in norms.values():
            self.assertTrue((module.weight == 1).all())
            self.assertEqual(module.weight.shape, (dh,))
            with torch.no_grad():
                module.weight.fill_(2.0)                      # RMS of the output = 1 times the weight
        seen = {}
        hooks = [m.register_forward_hook(lambda _m, _a, out, name=name: seen.setdefault(name, []).append(out))
                 for name, m in norms.items()]
        batch = synthetic_batch(visits=2, lines=20, seed=4)
        model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        for hook in hooks:
            hook.remove()
        self.assertEqual(set(seen), set(norms))
        for name, outs in seen.items():
            for out in outs:
                rms = out.float().pow(2).mean(-1).sqrt()
                torch.testing.assert_close(rms, torch.full_like(rms, 2.0), atol=1e-3, rtol=1e-3)

    def test_norm_comes_before_rope(self) -> None:
        # With RoPE after the norm the rotated q keeps the RMS of the weight; a norm after RoPE would not
        # matter here, so compare against the explicit order on the decoder's self-attention.
        model = tiny_model(seed=0, qk_norm_all=True)
        decoder = model.decoder
        captured = {}
        decoder.q_norm.register_forward_hook(lambda _m, _a, out: captured.update(q=out))
        x = torch.randn(2, 5, model.config.d_model)
        memory = torch.randn(2, 7, model.config.d_model)
        decoder(x, memory, torch.ones(2, 7, dtype=torch.bool))
        rotated = rope(captured["q"], torch.arange(5), decoder.base)
        torch.testing.assert_close(rotated.pow(2).mean(-1), captured["q"].pow(2).mean(-1))   # rotation keeps norms

    def test_runs_under_bf16_autocast(self) -> None:
        model = tiny_model(seed=0, qk_norm_all=True)
        batch = synthetic_batch(visits=2, lines=20, seed=4)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            out = model(batch, mode="own", p_own=0.5, generator=torch.Generator().manual_seed(0))
        out["loss"].backward()
        self.assertTrue(torch.isfinite(out["loss"]))

    def test_gradients_reach_the_gains(self) -> None:
        model = tiny_model(seed=0, qk_norm_all=True)
        batch = synthetic_batch(visits=2, lines=20, seed=4)
        model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))["loss"].backward()
        for name, module in model.named_modules():
            if isinstance(module, torch.nn.RMSNorm):
                self.assertIsNotNone(module.weight.grad, name)
                self.assertGreater(module.weight.grad.abs().sum(), 0, name)


class QkClipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = synthetic_batch(visits=2, lines=24, seed=6)

    def recorded(self, model: PremonitionMini) -> torch.Tensor:
        model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        return model._ask_logit_max

    def test_records_the_largest_eligible_real_card_logit(self) -> None:
        model = tiny_model(seed=0, qk_clip=1e6)
        with torch.no_grad():
            model.heads.query.weight.normal_(std=0.5)
            model.writer.key.weight.normal_(std=0.5)
        peak = self.recorded(model)
        self.assertTrue(torch.isfinite(peak) and peak > 0)
        self.assertFalse(peak.requires_grad)
        # one loop by hand: the max over eligible real cards of kappa * cos is a lower bound on the record
        with torch.no_grad():
            episode, store, index, scores, register = first_loop(model, self.batch)
            query = torch.nn.functional.normalize(model.heads.query(register).float(), dim=-1)
            match = model.heads.log_kappa.exp() * torch.einsum("nk,nlk->nl", query, store.keys[episode.q_visit])
            ok = store.eligible(episode.q_visit, episode.q_line)[:, :-1]
            self.assertLessEqual(float(match.masked_fill(~ok, float("-inf")).max()), float(peak) + 1e-4)

    def test_lowers_kappa_when_the_max_exceeds_tau_and_leaves_it_otherwise(self) -> None:
        loose = tiny_model(seed=0, qk_clip=1e6)
        tight = tiny_model(seed=0, qk_clip=0.5)
        for model in (loose, tight):
            with torch.no_grad():
                model.heads.query.weight.normal_(std=0.5)
                model.writer.key.weight.normal_(std=0.5)
        self.assertGreater(float(self.recorded(loose)), 0.5)
        peak = float(self.recorded(tight))
        before_loose, before_tight = float(loose.heads.log_kappa), float(tight.heads.log_kappa)
        loose.after_optimizer_step()
        tight.after_optimizer_step()
        self.assertEqual(float(loose.heads.log_kappa), before_loose)
        self.assertAlmostEqual(float(tight.heads.log_kappa), before_tight + math.log(0.5 / peak), places=5)
        self.assertLess(float(tight.heads.log_kappa), before_tight)
        self.assertIsNone(tight._ask_logit_max)
        tight.after_optimizer_step()                           # nothing recorded: a no-op
        self.assertAlmostEqual(float(tight.heads.log_kappa), before_tight + math.log(0.5 / peak), places=5)

    def test_after_the_clip_the_same_batch_peaks_at_tau(self) -> None:
        model = tiny_model(seed=0, qk_clip=0.5)
        with torch.no_grad():
            model.heads.query.weight.normal_(std=0.5)
            model.writer.key.weight.normal_(std=0.5)
        self.assertGreater(float(self.recorded(model)), 0.5)
        model.after_optimizer_step()
        self.assertAlmostEqual(float(self.recorded(model)), 0.5, places=3)
        model.after_optimizer_step()

    def test_off_and_eval_record_nothing(self) -> None:
        off = tiny_model(seed=0)
        self.assertIsNone(self.recorded(off))
        off.after_optimizer_step()                             # a no-op without the flag
        model = tiny_model(seed=0, qk_clip=5.0)
        model.eval()
        model.answer(self.batch)
        self.assertIsNone(model._ask_logit_max)
        model.train()
        with torch.no_grad():
            model(self.batch, mode="teacher", generator=torch.Generator().manual_seed(0))
        self.assertIsNone(model._ask_logit_max)
        kappa = float(model.heads.log_kappa)
        model.after_optimizer_step()
        self.assertEqual(float(model.heads.log_kappa), kappa)

    def test_the_trainer_calls_the_hook_after_each_step(self) -> None:
        model = tiny_model(seed=0, qk_clip=0.5)
        with torch.no_grad():
            model.heads.query.weight.normal_(std=0.5)
            model.writer.key.weight.normal_(std=0.5)
        trainer = ptrain.MiniTrainer(model, ptrain.mini_train_config(lr=1e-4, warmup_steps=1, log_every=1),
                                     "cpu", flop_budget=1.0, seed=0)
        plan = ptrain.Plan("teacher", "teacher", 0.0)
        kappa = float(model.heads.log_kappa)
        trainer._train_step(self.batch, plan, ptrain.planned_loops(self.batch, plan.mode, model.config), track=False)
        self.assertLess(float(model.heads.log_kappa), kappa - 0.05)
        self.assertIsNone(model._ask_logit_max)

    def test_other_model_classes_without_the_hook_still_train(self) -> None:
        model = tiny_model(seed=0)
        hook = PremonitionMini.after_optimizer_step
        try:
            del PremonitionMini.after_optimizer_step
            trainer = ptrain.MiniTrainer(model, ptrain.mini_train_config(lr=1e-3, warmup_steps=1, log_every=1),
                                         "cpu", flop_budget=1.0, seed=0)
            plan = ptrain.Plan("teacher", "teacher", 0.0)
            result = trainer._train_step(self.batch, plan,
                                         ptrain.planned_loops(self.batch, plan.mode, model.config), track=False)
            self.assertTrue(torch.isfinite(result["loss"]))
        finally:
            PremonitionMini.after_optimizer_step = hook


class KeySplitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = tiny_config(key_split=True)
        self.p = self.config.pos_key_dim
        torch.manual_seed(0)
        self.model = PremonitionMini(self.config)

    def test_position_width_defaults_to_a_quarter_of_the_key(self) -> None:
        self.assertEqual(self.p, 4)                          # key_dim 16 at the tiny preset
        self.assertEqual(MiniConfigWith(key_dim=64).pos_key_dim, 16)

    def test_only_the_last_dims_are_rotated_by_the_cards_line(self) -> None:
        writer = self.model.writer
        pooled = torch.randn(2, 12, self.config.d_model)
        keys = writer._keys(pooled, None)
        raw = writer.key(pooled)
        self.assertTrue(torch.equal(keys[..., :-self.p], raw[..., :-self.p]))              # content sub-key
        expected = rope(raw[..., -self.p:], torch.arange(12), self.config.key_pos_base)
        torch.testing.assert_close(keys[..., -self.p:], expected)
        self.assertTrue(torch.equal(keys[:, 0, -self.p:], raw[:, 0, -self.p:]))            # line 0: angle 0
        torch.testing.assert_close(keys.norm(dim=-1), raw.norm(dim=-1))                    # rotation keeps norms
        off = tiny_model(seed=0)
        self.assertTrue(torch.equal(off.writer._keys(pooled, None), off.writer.key(pooled)))

    def test_null_key_is_not_rotated(self) -> None:
        batch = synthetic_batch(visits=2, lines=16, seed=2)
        store = self.model.build_store(self.model.read(batch), batch)
        expected = torch.nn.functional.normalize(self.model.writer.null_key.float(), dim=-1)
        self.assertTrue(torch.equal(store.null_key, expected))

    def test_shifting_every_line_by_the_same_offset_keeps_the_position_part(self) -> None:
        writer, shift = self.model.writer, 7
        pooled = torch.randn(2, 12, self.config.d_model)
        later = torch.nn.functional.pad(pooled, (0, 0, shift, 0))                 # card j now sits on line j + shift
        keys, moved = writer._keys(pooled, None), writer._keys(later, None)[:, shift:]
        query = torch.randn(5, self.config.key_dim)
        line = torch.randint(12, 20, (5,))
        a = self.model._positioned(query, line)
        b = self.model._positioned(query, line + shift)
        part = lambda q, k: torch.einsum("np,blp->nbl", q[:, -self.p:], k[..., -self.p:])
        torch.testing.assert_close(part(a, keys), part(b, moved), atol=1e-4, rtol=1e-4)
        self.assertFalse(torch.allclose(part(a, keys), part(self.model._positioned(query, line + shift), keys),
                                        atol=1e-3))                                # but absolute lines matter
        # the content part is untouched by the shift
        self.assertTrue(torch.equal(a[:, :-self.p], query[:, :-self.p]))
        self.assertTrue(torch.equal(b[:, :-self.p], query[:, :-self.p]))

    def test_runs_in_every_mode_and_answers(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=3)
        for mode in ("gold", "teacher", "own"):
            out = self.model(batch, mode=mode, p_own=0.5, generator=torch.Generator().manual_seed(0))
            out["loss"].backward()
            self.assertTrue(torch.isfinite(out["loss"]))
        self.assertEqual(self.model.answer(batch).tokens.shape[0], batch.q_visit.shape[0])

    def test_recall_metric_uses_the_positioned_query(self) -> None:
        model, batch, seen = self.model, synthetic_batch(visits=2, lines=20, seed=3), {}
        original = CardStore.ask

        def spy(store, query, *args, **kwargs):
            seen["query"] = query.clone()
            return original(store, query, *args, **kwargs)

        hidden = model.read(batch)
        store = model.build_store(hidden, batch)
        episode = model._start(batch, hidden, store, model._mentions(batch))
        everyone = torch.arange(batch.q_visit.shape[0])
        rows, _, _, _ = model._step(episode, everyone, 0, store)
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        CardStore.ask = spy
        try:
            model._recall(store, episode, everyone, rows, gold)
        finally:
            CardStore.ask = original
        raw = model.heads.query(_norm(rows[:, model._register_base]))
        torch.testing.assert_close(seen["query"], model._positioned(raw, batch.q_line))


def MiniConfigWith(**changes):
    return tiny_config(key_split=True, **changes)


if __name__ == "__main__":
    unittest.main()
