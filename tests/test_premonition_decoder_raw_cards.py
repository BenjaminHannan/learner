"""S2 `decoder_raw_cards` (design/info-constraints/REPORT.md, S2). DRAFT.

1. Flag off: model, store and trainer are bit-identical to commit 73b8e0224. The base `premonition/config.py`,
   `store.py`, `model.py` and `train.py` are loaded from git and compared with `torch.equal` on init (and the
   global RNG state after it), the losses, metrics and gradients of all three training modes, `answer()` with
   no wipe, a store wipe and a full wipe, `answer_with_gold`, and trainer steps in every curriculum phase.
   A 1e-7 perturbation is caught, so the comparison is not vacuous. (Harness pattern from
   `claude/steals-8:tests/test_premonition_steals_identity.py`.)
2. Flag on: same parameters and same init stream as flag off (a paired start), every mode trains with finite
   losses and gradients, the episode gains 16 rows after the think rows that hold exactly the card rows as
   inserted (same mask, same ring slot), Think never reads or changes them, and the decoder reads them.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import types
import unittest

import torch

from premonition import train as ptrain
from premonition.config import MiniConfig
from premonition.model import PremonitionMini, _Episode
from tests.test_premonition_model import VOCAB, synthetic_batch

BASE_COMMIT = "73b8e022421d9161d00703e7dc483cdb05d7374a"
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("D", "D-noask", "D-noptr")
SEEDS = (0, 1)


def _git_source(path: str) -> str:
    try:
        return subprocess.run(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:            # e.g. a shallow clone without the base
        if os.environ.get("PREMONITION_ALLOW_MISSING_BASE") == "1":         # explicit opt-in only
            raise unittest.SkipTest(f"base commit {BASE_COMMIT[:9]} not available: {error}") from None
        raise AssertionError(f"base commit {BASE_COMMIT[:9]} is needed for the identity check (a rebase re-pins it, Q41; set "
                             "PREMONITION_ALLOW_MISSING_BASE=1 to skip knowingly): {error}") from None


def _load(name: str, source: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"<{name}>"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def base_modules() -> tuple[types.ModuleType, ...]:
    """(config, store, model, train) exactly as at the base commit, wired to each other."""
    if "premonition_rawbase_train" in sys.modules:
        return tuple(sys.modules[f"premonition_rawbase_{name}"] for name in ("config", "store", "model", "train"))
    config = _load("premonition_rawbase_config", _git_source("premonition/config.py"))
    store = _load("premonition_rawbase_store", _git_source("premonition/store.py"))
    model = _load("premonition_rawbase_model", _git_source("premonition/model.py").replace(
        "from premonition.store import", "from premonition_rawbase_store import").replace(
        "from premonition.config import", "from premonition_rawbase_config import"))
    train = _load("premonition_rawbase_train", _git_source("premonition/train.py").replace(
        "from premonition.model import", "from premonition_rawbase_model import").replace(
        "from premonition.config import", "from premonition_rawbase_config import"))
    return config, store, model, train


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def base_tiny(variant: str = "D"):
    return base_modules()[0].MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6)


def build(cls, config, seed: int):
    torch.manual_seed(seed)
    model = cls(config)
    return model, torch.get_rng_state()


def run_modes(model, batch, seed: int) -> list:
    out = []
    for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
        model.zero_grad(set_to_none=True)
        result = model(batch, mode=mode, p_own=p_own, generator=torch.Generator().manual_seed(seed))
        result["loss"].backward()
        for name in ("lm", "ask", "ans", "halt", "loss"):
            out.append((f"{mode}.{name}", result[name].detach()))
        for name, value in sorted(result["metrics"].items()):
            out.append((f"{mode}.metric.{name}", value.detach()))
        for name, param in model.named_parameters():
            out.append((f"{mode}.grad.{name}", None if param.grad is None else param.grad.clone()))
    model.zero_grad(set_to_none=True)
    return out


def run_answers(model, batch, train_module) -> list:
    model.eval()
    out = []
    window = (batch.q_line - 6).clamp_min(1)
    for label, kwargs in {"none": {}, "store": dict(wipe="store", window_line=window),
                          "full": dict(wipe="full", window_line=window)}.items():
        answers = model.answer(batch, **kwargs)
        for field in ("tokens", "lengths", "loops", "first_top", "fetched", "halt_prob"):
            out.append((f"answer.{label}.{field}", getattr(answers, field)))
    gold = train_module.answer_with_gold(model, batch)
    for field in ("tokens", "lengths", "loops", "fetched", "halt_prob"):
        out.append((f"gold_answer.{field}", getattr(gold, field)))
    model.train()
    return out


def run_trainer(train_module, model, batches, seed: int) -> list:
    trainer = train_module.MiniTrainer(model, train_module.mini_train_config(lr=3e-3, warmup_steps=2, log_every=1),
                                       "cpu", flop_budget=1.0, seed=seed)
    out = []
    plans = (train_module.Plan("gold", "gold", 0.0), train_module.Plan("teacher", "teacher", 0.0),
             train_module.Plan("own", "own", 0.5))
    for step, (batch, plan) in enumerate(zip(batches, plans)):
        loops = train_module.planned_loops(batch, plan.mode, model.config)
        result = trainer._train_step(batch, plan, loops, track=True)
        for name in ("loss", "lm", "ask", "ans", "halt", "grad_norm"):
            out.append((f"step{step}.{name}", result[name]))
        out.append((f"step{step}.cards", repr(sorted(result.get("cards", {}).items()))))
    for name, param in model.named_parameters():
        out.append((f"weight.{name}", param.detach().clone()))
    for index, state in sorted(trainer.optimizer.state_dict()["state"].items()):
        for key, value in sorted(state.items()):
            out.append((f"adam.{index}.{key}", value))
    return out


def differences(left: list, right: list) -> list[str]:
    if [name for name, _ in left] != [name for name, _ in right]:
        return ["the two runs recorded different quantities"]
    bad = []
    for (name, a), (_, b) in zip(left, right):
        if isinstance(a, torch.Tensor) or isinstance(b, torch.Tensor):
            same = (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor) and a.dtype == b.dtype
                    and a.shape == b.shape and torch.equal(a, b))
        else:
            same = a == b
        if not same:
            bad.append(name)
    return bad


def everything(cls, config, train_module, seed: int) -> list:
    model, rng = build(cls, config, seed)
    batches = [synthetic_batch(seed=seed + k) for k in range(3)]
    out = [("rng_after_init", rng)] + [(f"init.{n}", p.detach().clone()) for n, p in model.named_parameters()]
    out += run_modes(model, batches[0], seed)
    out += run_answers(model, batches[0], train_module)
    out += run_trainer(train_module, model, batches, seed)
    return out


class FlagOffIsBitIdenticalTest(unittest.TestCase):
    def test_flag_off_matches_the_base_commit(self) -> None:
        base_config, _, base_model, base_train = base_modules()
        for variant in VARIANTS:
            for seed in SEEDS:
                with self.subTest(variant=variant, seed=seed):
                    mine = everything(PremonitionMini, tiny(variant), ptrain, seed)
                    theirs = everything(base_model.PremonitionMini, base_tiny(variant), base_train, seed)
                    self.assertEqual(differences(mine, theirs), [])

    def test_the_comparison_catches_a_tiny_perturbation(self) -> None:
        _, _, base_model, base_train = base_modules()
        mine = everything(PremonitionMini, tiny("D"), ptrain, 0)
        theirs = everything(base_model.PremonitionMini, base_tiny("D"), base_train, 0)
        name, value = next((n, v) for n, v in theirs if n.startswith("init."))
        nudged = [(n, v + 1e-7 if n == name else v) for n, v in theirs]
        self.assertEqual(differences(mine, theirs), [])
        self.assertIn(name, differences(mine, nudged))

    def test_full_size_init_matches(self) -> None:
        base_config, _, base_model, _ = base_modules()
        mine, rng_a = build(PremonitionMini, MiniConfig.preset("D", "full"), 0)
        theirs, rng_b = build(base_model.PremonitionMini, base_config.MiniConfig.preset("D", "full"), 0)
        self.assertTrue(torch.equal(rng_a, rng_b))
        for (n, a), (_, b) in zip(mine.named_parameters(), theirs.named_parameters()):
            self.assertTrue(torch.equal(a, b), n)


class FlagOnTest(unittest.TestCase):
    def test_paired_start_same_parameters_and_stream(self) -> None:
        for size in ("tiny", "full"):
            with self.subTest(size=size):
                plain = tiny("D") if size == "tiny" else MiniConfig.preset("D", "full")
                flagged = plain.with_(decoder_raw_cards=True)
                off, rng_off = build(PremonitionMini, plain, 0)
                on, rng_on = build(PremonitionMini, flagged, 0)
                self.assertTrue(torch.equal(rng_off, rng_on))                   # same init stream after build
                self.assertEqual(on.num_parameters(), off.num_parameters())
                self.assertEqual(flagged.num_parameters(), plain.num_parameters())
                for (n, a), (_, b) in zip(off.named_parameters(), on.named_parameters()):
                    self.assertTrue(torch.equal(a, b), n)

    def test_refused_without_a_store(self) -> None:
        with self.assertRaises(ValueError):
            tiny("D-noask", decoder_raw_cards=True)

    def test_refused_on_subclasses_that_own_the_episode_layout(self) -> None:
        from premonition.answer_path import CardBypassMini, ThinkGatedMini
        from premonition.ovn_qread import QReadMini
        for cls in (CardBypassMini, QReadMini):                      # override _start/_insert/_greedy/...
            with self.subTest(cls=cls.__name__), self.assertRaises(ValueError):
                cls(tiny("D", decoder_raw_cards=True))
        model = ThinkGatedMini(tiny("D", decoder_raw_cards=True))    # only Think changes: allowed
        out = model(synthetic_batch(seed=4), mode="gold")
        self.assertTrue(torch.isfinite(out["loss"]))

    def test_every_mode_trains_and_answers(self) -> None:
        for variant in ("D", "D-noptr"):                               # D-noask is refused (no store)
            with self.subTest(variant=variant):
                model, _ = build(PremonitionMini, tiny(variant, decoder_raw_cards=True), 0)
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
                answers = model.answer(batch)
                self.assertEqual(answers.tokens.shape[0], batch.q_visit.shape[0])
                ptrain.answer_with_gold(model, batch)

    def test_raw_rows_hold_the_cards_as_inserted_and_think_skips_them(self) -> None:
        model, _ = build(PremonitionMini, tiny("D", decoder_raw_cards=True), 0)
        model.eval()
        batch = synthetic_batch(seed=5)
        config = model.config
        with torch.no_grad():
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            episode = model._start(batch, hidden, store, model._mentions(batch))
            self.assertEqual(episode.x.shape[1], config.rows + config.cards)
            self.assertFalse(episode.valid[:, config.rows:].any())              # empty until a card arrives
            count = batch.q_visit.shape[0]
            everyone = torch.arange(count)
            gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
            preload = torch.where(gold, torch.arange(gold.shape[1]),
                                  torch.full_like(gold, -1, dtype=torch.long)).topk(1, 1).values
            model._insert(episode, store, everyone, preload)
            base, raw = model._card_base, slice(config.rows, config.rows + config.cards)
            inserted = episode.x[:, base:base + config.cards].clone()
            self.assertTrue(torch.equal(episode.x[:, raw], inserted))
            self.assertTrue(torch.equal(episode.valid[:, raw], episode.valid[:, base:base + config.cards]))
            nudged = _Episode(episode.x.clone(), episode.valid.clone(), episode.count.clone(),
                              episode.fetched.clone(), episode.q_visit, episode.q_line)
            nudged.x[:, raw] += 1.0                                            # Think must not see this
            rows, _, _, _ = model._step(episode, everyone, 0, store)
            rows_nudged, _, _, _ = model._step(nudged, everyone, 0, store)
            self.assertTrue(torch.equal(rows[:, :config.rows], rows_nudged[:, :config.rows]))
            self.assertTrue(torch.equal(episode.x[:, raw], inserted))          # untouched by the Think pass
            self.assertFalse(torch.equal(episode.x[:, base:base + config.cards], inserted))
            inputs = batch.tokens[batch.q_visit, batch.q_span[:, 1] - 1].unsqueeze(1)
            a = model._decode_logits(episode.x, episode.valid, inputs)
            b = model._decode_logits(nudged.x, nudged.valid, inputs)
            self.assertFalse(torch.equal(a, b))                                # and the decoder reads them

    def test_flop_hand_count_covers_the_raw_rows(self) -> None:
        """The hand count's S2 increment tracks the measured increment (a whole-count tolerance could not see a
        term this small)."""
        from premonition.flops import measure_mini, mini_hand_count
        plain, _ = build(PremonitionMini, tiny("D"), 0)
        model, _ = build(PremonitionMini, tiny("D", decoder_raw_cards=True), 0)
        for visits, lines, seed in ((2, 16, 1), (2, 30, 3)):
            batch = synthetic_batch(visits=visits, lines=lines, seed=seed)
            a = measure_mini(plain, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            b = measure_mini(model, batch, mode="teacher", generator=torch.Generator().manual_seed(seed))
            self.assertEqual(a.question_loops, b.question_loops)
            measured = b.flops - a.flops
            hand = (mini_hand_count(model.config, batch, b.question_loops)
                    - mini_hand_count(plain.config, batch, a.question_loops))
            self.assertGreater(measured, 0)
            self.assertLess(abs(measured - hand) / measured, 0.25, (measured, hand))

    def test_ring_overwrite_keeps_raw_rows_aligned(self) -> None:
        model, _ = build(PremonitionMini, tiny("D", decoder_raw_cards=True, card_rows=2, top_k=1), 0)
        model.eval()
        batch = synthetic_batch(seed=7)
        with torch.no_grad():
            hidden = model.read(batch)
            store = model.build_store(hidden, batch)
            episode = model._start(batch, hidden, store, model._mentions(batch))
            everyone = torch.arange(batch.q_visit.shape[0])
            base, raw = model._card_base, slice(model.config.rows, model.config.rows + 2)
            seen = []
            for line in range(3):                                      # three distinct cards into two rows
                model._insert(episode, store, everyone, torch.full((everyone.numel(), 1), line))
                self.assertTrue(torch.equal(episode.x[:, raw], episode.x[:, base:base + 2]))
                seen.append(episode.x[:, raw].clone())
            self.assertFalse(torch.equal(seen[2][:, 0], seen[0][:, 0]))  # the third card really overwrote row 0
            self.assertTrue(torch.equal(seen[2][:, 1], seen[1][:, 1]))   # and left row 1 alone


if __name__ == "__main__":
    unittest.main()
