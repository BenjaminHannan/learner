"""The swap condition for every frontier steal (design/steals-2026-10-17/SPEC.md).

1. With every steal flag off, the model, card store and trainer are bit-identical to commit 73b8e0224:
   the base `premonition/model.py`, `store.py` and `train.py` are loaded from git and compared with
   `torch.equal` on init (and the global RNG state after it), the losses, metrics and gradients of all
   three training modes, `answer()` with no wipe, a store wipe and a full wipe, `answer_with_gold`, and
   trainer steps in every curriculum phase (losses, final weights, optimizer state). The comparison is
   shown to catch a 1e-7 perturbation, so it is not vacuous.
2. Any single flag on (and all of them on together) builds, trains every mode with finite losses and
   gradients, answers, takes trainer steps, and the hand parameter count matches the modules.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import types
import unittest

import torch

from premonition import train as ptrain
from premonition.config import STEAL_FLAGS, MiniConfig
from premonition.model import PremonitionMini
from tests.test_premonition_model import VOCAB, synthetic_batch

BASE_COMMIT = "73b8e022421d9161d00703e7dc483cdb05d7374a"
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("D", "D-noask", "D-noptr")
SEEDS = (0, 1)
# One setting per steal that turns it on (qk_clip is a float threshold).
SINGLE = {name: {name: True} for name in STEAL_FLAGS}
SINGLE["qk_clip"] = {"qk_clip": 5.0}


def _git_source(path: str) -> str:
    return subprocess.run(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def _load(name: str, source: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"<{name}>"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def base_modules() -> tuple[types.ModuleType, types.ModuleType, types.ModuleType, types.ModuleType]:
    """(config, store, model, train) exactly as at the base commit, wired to each other."""
    if "premonition_base_train" in sys.modules:
        return tuple(sys.modules[f"premonition_base_{name}"] for name in ("config", "store", "model", "train"))
    config = _load("premonition_base_config", _git_source("premonition/config.py"))
    store = _load("premonition_base_store", _git_source("premonition/store.py"))
    model = _load("premonition_base_model", _git_source("premonition/model.py").replace(
        "from premonition.store import", "from premonition_base_store import").replace(
        "from premonition.config import", "from premonition_base_config import"))
    train = _load("premonition_base_train", _git_source("premonition/train.py").replace(
        "from premonition.model import", "from premonition_base_model import").replace(
        "from premonition.config import", "from premonition_base_config import"))
    return config, store, model, train


def tiny(variant: str = "D", **flags) -> MiniConfig:
    return MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6, **flags)


def base_tiny(variant: str = "D"):
    """The same config built by the base commit's own config.py."""
    return base_modules()[0].MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, window=16, max_loops=6)


def build(cls, config: MiniConfig, seed: int) -> tuple[torch.nn.Module, torch.Tensor]:
    torch.manual_seed(seed)
    model = cls(config)
    return model, torch.get_rng_state()


def run_modes(model: torch.nn.Module, batch, seed: int) -> list[tuple[str, object]]:
    """Every loss, metric and gradient of the three training modes, in a fixed order."""
    out = []
    for mode, p_own in (("gold", 0.0), ("teacher", 0.0), ("own", 0.5)):
        model.zero_grad(set_to_none=True)
        generator = torch.Generator().manual_seed(seed)
        result = model(batch, mode=mode, p_own=p_own, generator=generator)
        result["loss"].backward()
        for name in ("lm", "ask", "ans", "halt", "loss"):
            out.append((f"{mode}.{name}", result[name].detach()))
        for name, value in sorted(result["metrics"].items()):
            out.append((f"{mode}.metric.{name}", value.detach()))
        for name, param in model.named_parameters():
            out.append((f"{mode}.grad.{name}", None if param.grad is None else param.grad.clone()))
    model.zero_grad(set_to_none=True)
    return out


def run_answers(model: torch.nn.Module, batch, train_module) -> list[tuple[str, object]]:
    model.eval()
    out = []
    window = (batch.q_line - 6).clamp_min(1)
    runs = {"none": dict(), "store": dict(wipe="store", window_line=window),
            "full": dict(wipe="full", window_line=window)}
    for label, kwargs in runs.items():
        answers = model.answer(batch, **kwargs)
        for field in ("tokens", "lengths", "loops", "first_top", "fetched", "halt_prob"):
            out.append((f"answer.{label}.{field}", getattr(answers, field)))
    gold = train_module.answer_with_gold(model, batch)
    for field in ("tokens", "lengths", "loops", "fetched", "halt_prob"):
        out.append((f"gold_answer.{field}", getattr(gold, field)))
    model.train()
    return out


def run_trainer(train_module, model: torch.nn.Module, batches, seed: int) -> list[tuple[str, object]]:
    """Trainer steps in each curriculum phase through `MiniTrainer._train_step`."""
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


class AllOffIsBitIdenticalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_config, cls.base_store, cls.base_model, cls.base_train = base_modules()

    def test_config_defaults_are_off(self) -> None:
        config = MiniConfig.preset("D")
        self.assertEqual(config.steals, ())
        self.assertEqual(config.base(), config.with_(check_band=False))
        self.assertEqual(config.num_parameters(), 2_013_140)

    def test_init_training_and_answers_match_the_base_commit(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=3)
        for variant in VARIANTS:
            for seed in SEEDS:
                with self.subTest(variant=variant, seed=seed):
                    new, new_rng = build(PremonitionMini, tiny(variant), seed)
                    old, old_rng = build(self.base_model.PremonitionMini, base_tiny(variant), seed)
                    self.assertTrue(torch.equal(new_rng, old_rng), "construction drew a different RNG stream")
                    new_state, old_state = new.state_dict(), old.state_dict()
                    self.assertEqual(list(new_state), list(old_state))
                    for name in new_state:
                        self.assertTrue(torch.equal(new_state[name], old_state[name]), name)
                    self.assertEqual(differences(run_modes(new, batch, seed), run_modes(old, batch, seed)), [])
                    self.assertEqual(differences(run_answers(new, batch, ptrain),
                                                 run_answers(old, batch, self.base_train)), [])

    def test_full_size_init_matches(self) -> None:
        new, new_rng = build(PremonitionMini, MiniConfig.preset("D"), 0)
        old, old_rng = build(self.base_model.PremonitionMini, self.base_config.MiniConfig.preset("D"), 0)
        self.assertTrue(torch.equal(new_rng, old_rng))
        self.assertEqual(list(new.state_dict()), list(old.state_dict()))
        for (name, a), (_, b) in zip(new.state_dict().items(), old.state_dict().items()):
            self.assertTrue(torch.equal(a, b), name)

    def test_configs_and_checkpoint_configs_match(self) -> None:
        """Every config the base accepts is accepted, counts the same parameters, and serialises to the same
        checkpoint config (so older code still reads a flags-off checkpoint)."""
        settings = [dict(), dict(d_model=36, n_heads=2), dict(d_model=20, n_heads=2), dict(max_loops=1)]
        for variant in VARIANTS:
            for extra in settings:
                with self.subTest(variant=variant, extra=extra):
                    new = MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, **extra)
                    old = self.base_config.MiniConfig.preset(variant, "tiny", vocab_size=VOCAB, **extra)
                    self.assertEqual(new.parameter_breakdown(), old.parameter_breakdown())
                    self.assertEqual(ptrain.mini_config_dict(new), self.base_train.mini_config_dict(old))
        for variant in VARIANTS:
            self.assertEqual(MiniConfig.preset(variant).num_parameters(),
                             self.base_config.MiniConfig.preset(variant).num_parameters())

    def test_trainer_steps_match_the_base_commit(self) -> None:
        batches = [synthetic_batch(visits=2, lines=20, seed=s) for s in (11, 12, 13)]
        for variant in VARIANTS:
            with self.subTest(variant=variant):
                new, _ = build(PremonitionMini, tiny(variant), 0)
                old, _ = build(self.base_model.PremonitionMini, base_tiny(variant), 0)
                self.assertEqual(differences(run_trainer(ptrain, new, batches, 0),
                                             run_trainer(self.base_train, old, batches, 0)), [])

    def test_the_comparison_catches_a_tiny_perturbation(self) -> None:
        batch = synthetic_batch(visits=2, lines=24, seed=3)
        new, _ = build(PremonitionMini, tiny(), 0)
        old, _ = build(self.base_model.PremonitionMini, base_tiny(), 0)
        with torch.no_grad():
            next(new.think.parameters()).view(-1)[0] += 1e-7
        self.assertNotEqual(differences(run_modes(new, batch, 0), run_modes(old, batch, 0)), [])


class PairedInitTest(unittest.TestCase):
    """At a given seed a steal leaves every shared weight and the RNG stream as the flag-off model has them, so a
    paired A/B differs only in the steal (delta_bind too: the binder it removes still has its draws taken)."""

    def test_shared_weights_match_the_flag_off_model(self) -> None:
        for variant in VARIANTS:
            for seed in SEEDS:
                off, off_rng = build(PremonitionMini, tiny(variant), seed)
                reference = off.state_dict()
                for label, flags in SINGLE.items():
                    with self.subTest(variant=variant, seed=seed, flag=label):
                        on, on_rng = build(PremonitionMini, tiny(variant, **flags), seed)
                        self.assertTrue(torch.equal(on_rng, off_rng))
                        for name, value in on.state_dict().items():
                            if name in reference:
                                self.assertTrue(torch.equal(value, reference[name]), name)

    def test_steal_weights_depend_on_the_seed(self) -> None:
        a, _ = build(PremonitionMini, tiny(fetch_gate=True), 0)
        b, _ = build(PremonitionMini, tiny(fetch_gate=True), 1)
        c, _ = build(PremonitionMini, tiny(fetch_gate=True), 0)
        self.assertFalse(torch.equal(a.decoder.cross_gate.weight, b.decoder.cross_gate.weight))
        self.assertTrue(torch.equal(a.decoder.cross_gate.weight, c.decoder.cross_gate.weight))


class EachFlagRunsTest(unittest.TestCase):
    """Any single steal on, and all of them together: builds, trains, answers, steps; counts match."""

    def check(self, flags: dict) -> None:
        config = tiny(**flags)
        self.assertNotEqual(config.steals, ())
        model, _ = build(PremonitionMini, config, 0)
        self.assertEqual(model.parameter_breakdown(), config.parameter_breakdown())
        batch = synthetic_batch(visits=2, lines=24, seed=5)
        for name, value in run_modes(model, batch, 0):
            if isinstance(value, torch.Tensor) and value.is_floating_point():
                self.assertTrue(torch.isfinite(value).all(), name)
        answers = model.answer(batch)
        self.assertEqual(answers.tokens.shape[0], batch.q_visit.shape[0])
        model.answer(batch, wipe="store", window_line=(batch.q_line - 6).clamp_min(1))
        ptrain.answer_with_gold(model, batch)
        model.train()
        batches = [synthetic_batch(visits=2, lines=20, seed=s) for s in (11, 12, 13)]
        for name, value in run_trainer(ptrain, model, batches, 0):
            if isinstance(value, torch.Tensor) and value.is_floating_point():
                self.assertTrue(torch.isfinite(value).all(), name)
        full = MiniConfig.preset("D", **flags)            # the d = 128 band still holds D itself
        self.assertGreater(full.num_parameters(), 0)

    def test_each_single_flag(self) -> None:
        for label, flags in SINGLE.items():
            with self.subTest(flag=label):
                self.check(flags)

    def test_all_flags_together(self) -> None:
        flags = {name: True for name in STEAL_FLAGS}
        flags["qk_clip"] = 5.0
        self.check(flags)

    def test_controls_take_every_flag(self) -> None:
        for variant in ("D-noask", "D-noptr"):
            for label, flags in SINGLE.items():
                with self.subTest(variant=variant, flag=label):
                    config = tiny(variant, **flags)
                    model, _ = build(PremonitionMini, config, 0)
                    self.assertEqual(model.parameter_breakdown(), config.parameter_breakdown())
                    out = model(synthetic_batch(seed=1), mode="own", p_own=0.5,
                                generator=torch.Generator().manual_seed(0))
                    out["loss"].backward()
                    self.assertTrue(torch.isfinite(out["loss"]))


if __name__ == "__main__":
    unittest.main()
