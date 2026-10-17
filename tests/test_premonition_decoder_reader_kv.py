"""`decoder_reader_kv`: the decoder's second cross-attention, to the reader's finished states.

Flag off must be bit-identical to the model before the change (loaded from git at BASELINE);
flag on must be causal, finite and train the reader through the new path.
"""
from __future__ import annotations

import os
import subprocess
import sys
import types
import unittest
from pathlib import Path

import torch

from premonition.config import PARAM_BAND, VOCAB_V2, MiniConfig, reader_kv_parameters
from premonition.flops import measure_mini, mini_hand_count
from premonition.model import PremonitionMini
from premonition.ovn_qread import QReadMini
from tests.test_premonition_model import eager as always_ask, synthetic_batch, tiny_config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_reader_kv_guard as guard  # noqa: E402
BASELINE = os.environ.get("READER_KV_BASELINE", "73b8e022421d9161d00703e7dc483cdb05d7374a")
VARIANTS = ("D", "D-noask", "D-noptr")


def baseline_class() -> type:
    """PremonitionMini exactly as it was at BASELINE (premonition/model.py from git)."""
    try:
        source = subprocess.run(["git", "show", f"{BASELINE}:premonition/model.py"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise unittest.SkipTest(f"baseline {BASELINE[:9]} not in this checkout: {error}")
    module = types.ModuleType("premonition._model_before_reader_kv")
    module.__file__ = str(ROOT / "premonition" / "model.py")
    sys.modules[module.__name__] = module
    exec(compile(source, f"{BASELINE[:9]}:premonition/model.py", "exec"), module.__dict__)
    return module.PremonitionMini


def eager(model: PremonitionMini) -> PremonitionMini:
    return always_ask(model) if model.heads.ask is not None else model


def build(cls: type, config: MiniConfig, seed: int = 0) -> PremonitionMini:
    torch.manual_seed(seed)
    return cls(config)


def run_modes(model: PremonitionMini, batch, seed: int = 0) -> list[dict]:
    """Every training mode's losses and metrics, then the gradients of the gold-mode loss."""
    out = []
    for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
        model.zero_grad(set_to_none=True)
        result = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(seed))
        result["loss"].backward()
        grads = {name: p.grad.clone() for name, p in model.named_parameters() if p.grad is not None}
        out.append({**{k: v for k, v in result.items() if k != "metrics"}, **result["metrics"],
                    "grads": grads})
    return out


def run_answers(model: PremonitionMini, batch) -> list:
    window = torch.clamp(batch.q_line - 3, min=0)
    return [model.answer(batch), model.answer(batch, wipe="store", window_line=window),
            model.answer(batch, wipe="full", window_line=window)]


class FlagOffIsBitIdenticalTest(unittest.TestCase):
    """The swap condition: with the flag off nothing changes, on a fixed batch and seed."""

    def assert_same(self, ours, theirs, where: str) -> None:
        if isinstance(ours, dict):
            self.assertEqual(sorted(ours), sorted(theirs), where)
            for key in ours:
                self.assert_same(ours[key], theirs[key], f"{where}.{key}")
        elif isinstance(ours, (list, tuple)):
            self.assertEqual(len(ours), len(theirs), where)
            for i, (a, b) in enumerate(zip(ours, theirs)):
                self.assert_same(a, b, f"{where}[{i}]")
        elif isinstance(ours, torch.Tensor):
            self.assertTrue(torch.equal(ours, theirs), where)
        elif hasattr(ours, "__dataclass_fields__"):
            for field in ours.__dataclass_fields__:
                self.assert_same(getattr(ours, field), getattr(theirs, field), f"{where}.{field}")
        else:
            self.assertEqual(ours, theirs, where)

    def test_outputs_losses_and_gradients_match_the_baseline(self) -> None:
        before = baseline_class()
        for variant in VARIANTS:
            for seed in (0, 1):
                config = tiny_config(variant)
                self.assertFalse(config.decoder_reader_kv)
                batch = synthetic_batch(visits=3, lines=18, seed=seed)
                old, new = build(before, config, seed), build(PremonitionMini, config, seed)
                self.assert_same(new.state_dict(), old.state_dict(), f"{variant}/s{seed} init")
                torch.manual_seed(seed)
                theirs = run_modes(old, batch, seed)
                torch.manual_seed(seed)
                ours = run_modes(new, batch, seed)
                self.assert_same(ours, theirs, f"{variant}/s{seed} train")
                eager(old), eager(new)
                self.assert_same(run_answers(new, batch), run_answers(old, batch), f"{variant}/s{seed} answer")
                self.assertEqual(new.num_parameters(), old.num_parameters())

    def test_construction_leaves_the_global_stream_alone(self) -> None:
        before = baseline_class()
        for flag in (False, True):
            build(before, tiny_config())
            expected = torch.get_rng_state()
            build(PremonitionMini, tiny_config(decoder_reader_kv=flag))
            self.assertTrue(torch.equal(torch.get_rng_state(), expected), flag)


class FlagOnTest(unittest.TestCase):
    def test_shared_weights_are_the_control_and_only_new_keys_are_added(self) -> None:
        off = build(PremonitionMini, tiny_config(), 3)
        on = build(PremonitionMini, tiny_config(decoder_reader_kv=True), 3)
        state_off, state_on = off.state_dict(), on.state_dict()
        extra = sorted(set(state_on) - set(state_off))
        self.assertTrue(extra and all(k.startswith("decoder.reader_attn.") for k in extra), extra)
        self.assertFalse(set(state_off) - set(state_on))
        for key, value in state_off.items():
            self.assertTrue(torch.equal(value, state_on[key]), key)
        # Loading the control's (parent) checkpoint leaves exactly the new path to initialise.
        fresh = PremonitionMini(tiny_config(decoder_reader_kv=True))
        missing, unexpected = fresh.load_state_dict(state_off, strict=False)
        self.assertEqual(sorted(missing), extra)
        self.assertFalse(unexpected)
        # The new path's init is a function of the seed only.
        again = build(PremonitionMini, tiny_config(decoder_reader_kv=True), 3)
        other = build(PremonitionMini, tiny_config(decoder_reader_kv=True), 4)
        key = "decoder.reader_attn.kv.weight"
        self.assertTrue(torch.equal(again.state_dict()[key], state_on[key]))
        self.assertFalse(torch.equal(other.state_dict()[key], state_on[key]))

    def test_parameter_count_and_band(self) -> None:
        for vocab in (6372, VOCAB_V2):
            config = MiniConfig.preset("D", vocab_size=vocab, decoder_reader_kv=True)
            with torch.device("meta"):
                model = PremonitionMini(config)
            self.assertEqual(model.parameter_breakdown(), config.parameter_breakdown())
            self.assertEqual(model.num_parameters(), config.num_parameters())
            base = MiniConfig.preset("D", vocab_size=vocab)
            self.assertEqual(config.num_parameters() - base.num_parameters(), reader_kv_parameters(config))
            self.assertEqual(reader_kv_parameters(config), 66_304)
            self.assertTrue(PARAM_BAND[0] <= base.num_parameters() <= PARAM_BAND[1])
        self.assertEqual(reader_kv_parameters(MiniConfig.preset("D")), 0)

    def test_shapes_and_finite_losses(self) -> None:
        for variant in VARIANTS:
            config = tiny_config(variant, decoder_reader_kv=True)
            model = build(PremonitionMini, config)
            batch = synthetic_batch(visits=3, lines=18, seed=5)
            hidden = model.read(batch)
            kv, keep = model._reader_kv(batch, hidden)
            width = int(batch.q_span[:, 1].max())
            self.assertEqual(kv.shape, (3, width, 2 * config.d_model))
            self.assertEqual(keep.shape, (batch.q_visit.shape[0], width))
            for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
                out = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(0))
                for name in ("loss", "lm", "ask", "ans", "halt"):
                    self.assertTrue(torch.isfinite(out[name]).all(), (variant, mode, name))
            eager(model)
            for answers in run_answers(model, batch):
                self.assertEqual(answers.tokens.shape, (batch.q_visit.shape[0], config.max_answer))

    def test_mask_is_causal_and_real_tokens_only(self) -> None:
        model = build(PremonitionMini, tiny_config(decoder_reader_kv=True))
        batch = synthetic_batch(visits=3, lines=18, seed=6)
        _, keep = model._reader_kv(batch, model.read(batch))
        position = torch.arange(keep.shape[1])
        end = batch.q_span[:, 1].unsqueeze(1)
        real = batch.line_of[batch.q_visit, :keep.shape[1]] >= 0
        self.assertTrue(torch.equal(keep, real & (position < end)))
        low = batch.line_start[batch.q_visit, torch.clamp(batch.q_line - 3, min=0)]
        _, kept = model._reader_kv(batch, model.read(batch), low)
        self.assertTrue(torch.equal(kept, keep & (position >= low.unsqueeze(1))))

    def test_answers_ignore_everything_after_the_question(self) -> None:
        """Rewriting every token after a visit's last "[answer]" (its answers among them) changes nothing."""
        model = eager(build(PremonitionMini, tiny_config(decoder_reader_kv=True)))
        batch = synthetic_batch(visits=3, lines=18, seed=7)
        before = model.answer(batch)
        tokens = batch.tokens.clone()
        generator = torch.Generator().manual_seed(1)
        for visit in range(tokens.shape[0]):
            last = int(batch.q_span[batch.q_visit == visit, 1].max())
            tail = tokens[visit, last:batch.lengths[visit]]
            tokens[visit, last:batch.lengths[visit]] = torch.randint(10, 48, tail.shape, generator=generator)
        batch.tokens = tokens
        after = model.answer(batch)
        self.assertTrue(torch.equal(before.tokens, after.tokens))
        self.assertTrue(torch.equal(before.fetched, after.fetched))

    def test_answer_loss_reaches_the_reader_through_the_new_path(self) -> None:
        # D-noask with 4 question rows: reader states outside every question window reach L_ans
        # only through the new cross-attention (no cards, slots are embeddings).
        for flag in (False, True):
            model = build(PremonitionMini, tiny_config("D-noask", question_rows=4, decoder_reader_kv=flag))
            batch = synthetic_batch(visits=2, lines=16, seed=8)
            captured = {}
            read = model.read

            def keep_hidden(b):
                captured["hidden"] = read(b)
                return captured["hidden"]

            model.read = keep_hidden
            out = model(batch, mode="teacher", generator=torch.Generator().manual_seed(0))
            grad, = torch.autograd.grad(out["ans"], captured["hidden"], retain_graph=True)
            window = torch.zeros(batch.tokens.shape, dtype=torch.bool)
            for q, (visit, end) in enumerate(zip(batch.q_visit.tolist(), batch.q_span[:, 1].tolist())):
                window[visit, end - 4:end] = True
            outside = grad[~window].abs().sum()
            if flag:
                self.assertGreater(float(outside), 0.0)
                reader_grads = torch.autograd.grad(out["ans"], list(model.reader.parameters()))
                self.assertTrue(all(torch.isfinite(g).all() for g in reader_grads))
                self.assertGreater(sum(float(g.abs().sum()) for g in reader_grads), 0.0)
            else:
                self.assertEqual(float(outside), 0.0)
        # Full D: the answer loss reaches the states the new KV projection reads.
        model = build(PremonitionMini, tiny_config(decoder_reader_kv=True))
        seen = {}
        def capture(module, args, output) -> None:
            seen.setdefault("x", args[0])

        model.decoder.reader_attn.kv.register_forward_hook(capture)
        out = model(synthetic_batch(visits=2, lines=16, seed=9), mode="teacher",
                    generator=torch.Generator().manual_seed(0))
        grad, = torch.autograd.grad(out["ans"], seen["x"])
        self.assertGreater(float(grad.abs().sum()), 0.0)

    def test_hand_flop_count_covers_the_new_path(self) -> None:
        model = build(PremonitionMini, tiny_config(decoder_reader_kv=True))
        for visits, lines, seed in ((1, 12, 0), (2, 16, 1), (2, 30, 3)):
            batch = synthetic_batch(visits=visits, lines=lines, seed=seed)
            sample = measure_mini(model, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            hand = mini_hand_count(model.config, batch, sample.question_loops)
            self.assertLess(abs(sample.flops - hand) / hand, 0.15, (sample, hand))

    def test_unwired_subclasses_refuse_the_flag(self) -> None:
        with self.assertRaises(NotImplementedError):
            QReadMini(tiny_config(decoder_reader_kv=True))
        QReadMini(tiny_config())


class GuardMetricTest(unittest.TestCase):
    def test_counts_match_answer_and_leave_it_unchanged(self) -> None:
        for flag in (False, True):
            model = eager(build(PremonitionMini, tiny_config(decoder_reader_kv=flag)))
            batch = synthetic_batch(visits=3, lines=18, seed=11)
            plain = model.answer(batch)
            answers, asks, cards, nulls = guard.guard_counts(model, batch)
            self.assertFalse("_step" in vars(model))
            for field in ("tokens", "lengths", "loops", "fetched", "halt_prob"):
                self.assertTrue(torch.equal(getattr(plain, field), getattr(answers, field)), field)
            # Always ASK, never HALT: every loop but the last fetches.
            self.assertTrue(torch.equal(asks, answers.loops - 1))
            self.assertTrue(torch.equal(cards + nulls, answers.fetched.sum(1)))
            self.assertGreater(guard.summarize(asks, cards, nulls)["cards_per_question"], 0)
        model = build(PremonitionMini, tiny_config("D-noask"))
        _, asks, cards, _ = guard.guard_counts(model, synthetic_batch(seed=12))
        self.assertEqual(int(asks.sum() + cards.sum()), 0)

    def test_verdict_rule(self) -> None:
        def row(cards: float) -> dict:
            return {"cards_per_question": cards, "asks_per_question": cards / 4}
        held = guard.guard_verdict([row(4.0), row(2.0)], [row(3.4), row(1.6)])     # pooled drop 16.7%
        self.assertTrue(held["holds"])
        broke = guard.guard_verdict([row(4.0), row(2.0)], [row(4.0), row(0.5)])    # pooled drop 25%
        self.assertFalse(broke["holds"])
        self.assertIn("writer bypassed the thinker", broke["reading"])
        self.assertFalse(guard.guard_verdict([row(0.0)], [row(1.0)])["holds"])
        with self.assertRaises(ValueError):
            guard.guard_verdict([row(1.0)], [])


if __name__ == "__main__":
    unittest.main()
