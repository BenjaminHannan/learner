"""Steal 8, the Muon option (design/steals-2026-10-17/SPEC.md section 8)."""
from __future__ import annotations

import inspect
import io
import math
import unittest

import torch
from torch import nn

from premonition import train as ptrain
from premonition.muon import MuonAdamW, muon_param_groups, newton_schulz
from premonition.model import PremonitionMini
from tests.test_premonition_model import synthetic_batch, tiny_config, tiny_model


def trainer(model: PremonitionMini, optimizer: str, lr: float = 3e-3, **config) -> ptrain.MiniTrainer:
    settings = dict(lr=lr, warmup_steps=3, log_every=1, weight_decay=0.1)
    settings.update(config)
    return ptrain.MiniTrainer(model, ptrain.mini_train_config(**settings), "cpu", flop_budget=1.0, seed=0,
                              optimizer=optimizer)


def step(t: ptrain.MiniTrainer, batch, mode: str = "teacher") -> float:
    plan = ptrain.Plan(mode, mode, 0.0)
    return float(t._train_step(batch, plan, ptrain.planned_loops(batch, mode, t.model.config), track=False)["loss"])


def muon_names(model: nn.Module) -> set[str]:
    groups = muon_param_groups(model, 0.1)
    ids = {id(p) for g in groups if g["muon"] for p in g["params"]}
    return {name for name, p in model.named_parameters() if id(p) in ids}


class NewtonSchulzTest(unittest.TestCase):
    def test_output_is_near_orthogonal(self) -> None:
        generator = torch.Generator().manual_seed(0)
        for shape in ((32, 64), (64, 32), (48, 48), (128, 384)):
            with self.subTest(shape=shape):
                out = newton_schulz(torch.randn(shape, generator=generator))
                svals = torch.linalg.svdvals(out)
                self.assertEqual(out.shape, shape)
                self.assertGreater(svals.min().item(), 0.5)          # the quintic leaves values in ~[0.7, 1.2]
                self.assertLess(svals.max().item(), 1.3)
                gram = out @ out.T if shape[0] <= shape[1] else out.T @ out
                self.assertLess((gram - torch.eye(gram.shape[0])).abs().max().item(), 0.5)

    def test_keeps_the_singular_vectors(self) -> None:
        g = torch.randn(24, 40, generator=torch.Generator().manual_seed(1))
        u, _, vh = torch.linalg.svd(g, full_matrices=False)
        out = newton_schulz(g)
        self.assertGreater(torch.nn.functional.cosine_similarity(out.flatten(), (u @ vh).flatten(), dim=0).item(), 0.95)

    def test_scale_free_and_rejects_non_matrices(self) -> None:
        g = torch.randn(16, 16, generator=torch.Generator().manual_seed(2))
        torch.testing.assert_close(newton_schulz(g), newton_schulz(1000 * g), rtol=1e-4, atol=1e-4)
        with self.assertRaises(ValueError):
            newton_schulz(torch.randn(4))


class StepRuleTest(unittest.TestCase):
    def test_muon_step_follows_the_recipe(self) -> None:
        w = nn.Parameter(torch.randn(8, 24, generator=torch.Generator().manual_seed(0)))
        start = w.detach().clone()
        grad = torch.randn(8, 24, generator=torch.Generator().manual_seed(1))
        opt = MuonAdamW([dict(params=[w], muon=True, weight_decay=0.1)], lr=0.01)
        w.grad = grad.clone()
        opt.step()
        want = start * (1 - 0.01 * 0.1) - 0.01 * 0.2 * math.sqrt(24) * newton_schulz(grad * (1 + 0.95))
        torch.testing.assert_close(w.detach(), want, rtol=1e-5, atol=1e-6)
        buffer = opt.state[w]["momentum_buffer"]
        torch.testing.assert_close(buffer, grad)
        w.grad = grad.clone()
        before = w.detach().clone()
        opt.step()                                            # second step: buf = 0.95 g + g, input = g + 0.95 buf
        torch.testing.assert_close(opt.state[w]["momentum_buffer"], 1.95 * grad)
        want = before * (1 - 0.01 * 0.1) - 0.01 * 0.2 * math.sqrt(24) * newton_schulz(grad + 0.95 * 1.95 * grad)
        torch.testing.assert_close(w.detach(), want, rtol=1e-5, atol=1e-6)

    def test_adamw_groups_match_torch_adamw(self) -> None:
        make = lambda: nn.Parameter(torch.randn(5, 7, generator=torch.Generator().manual_seed(3)))
        a, b = make(), make()
        mine = MuonAdamW([dict(params=[a], muon=False, weight_decay=0.1)], lr=0.02, betas=(0.9, 0.99), eps=1e-8)
        ref = torch.optim.AdamW([b], lr=0.02, betas=(0.9, 0.99), eps=1e-8, weight_decay=0.1)
        for i in range(5):
            grad = torch.randn(5, 7, generator=torch.Generator().manual_seed(10 + i))
            a.grad, b.grad = grad.clone(), grad.clone()
            mine.step()
            ref.step()
        torch.testing.assert_close(a.detach(), b.detach(), rtol=1e-5, atol=1e-6)

    def test_params_without_gradients_are_skipped(self) -> None:
        w = nn.Parameter(torch.ones(4, 4))
        MuonAdamW([dict(params=[w], muon=True)], lr=0.1).step()
        self.assertTrue(torch.equal(w.detach(), torch.ones(4, 4)))

    def test_muon_groups_reject_vectors(self) -> None:
        with self.assertRaises(ValueError):
            MuonAdamW([dict(params=[nn.Parameter(torch.ones(4))], muon=True)])


class GroupingTest(unittest.TestCase):
    def expected(self, model: PremonitionMini) -> set[str]:
        names = set()
        for name, p in model.named_parameters():
            if not name.endswith(".weight") or p.dim() != 2:
                continue
            owner = name[:-len(".weight")]
            if owner.startswith(("reader.", "think.layers.", "decoder.")) and owner != "decoder.cross_gate":
                names.add(name)
            if owner in ("writer.key", "writer.value"):
                names.add(name)
        return names

    def test_muon_takes_exactly_the_listed_linears(self) -> None:
        model = tiny_model()
        names = muon_names(model)
        self.assertEqual(names, self.expected(model))
        for wanted in ("reader.layers.0.mixer.inp.weight", "reader.layers.1.mixer.qkv.weight",
                       "reader.layers.2.mlp.fc.weight", "writer.key.weight", "writer.value.weight",
                       "think.layers.0.qkv.weight", "think.layers.1.mlp.out.weight", "decoder.qkv.weight",
                       "decoder.cross_kv.weight", "decoder.mlp.fc.weight"):
            self.assertIn(wanted, names)
        for kept in ("embed.weight", "writer.pool.weight", "writer.null_key", "think.binder.weight",
                     "think.row_type.weight", "think.register.weight", "think.step.weight", "think.age.weight",
                     "think.age_bias", "heads.query.weight", "heads.ask.weight", "heads.halt.weight",
                     "heads.log_kappa", "reader.norm.weight", "decoder.norm.weight"):
            self.assertNotIn(kept, names)

    def test_every_parameter_lands_in_exactly_one_group(self) -> None:
        for variant in ("D", "D-noask", "D-noptr"):
            for flags in ({}, {"engram": True}):
                with self.subTest(variant=variant, **flags):
                    model = tiny_model(variant, **flags)
                    groups = muon_param_groups(model, 0.1)
                    seen = [id(p) for g in groups for p in g["params"]]
                    self.assertEqual(len(seen), len(set(seen)))
                    self.assertEqual(set(seen), {id(p) for p in model.parameters()})
                    muon = [g for g in groups if g["muon"]]
                    self.assertEqual(len(muon), 1)
                    self.assertTrue(all(p.dim() == 2 and min(p.shape) > 1 for p in muon[0]["params"]))
                    if flags:
                        self.assertFalse(any("engram" in n for n in muon_names(model)))
                    if variant == "D-noask":
                        self.assertNotIn("writer.key.weight", muon_names(model))

    def test_weight_decay_goes_to_matrices_only(self) -> None:
        groups = muon_param_groups(tiny_model(), 0.1)
        decay = {g["weight_decay"] for g in groups if all(p.dim() >= 2 for p in g["params"])}
        self.assertEqual(decay, {0.1})
        for g in groups:
            if any(p.dim() < 2 for p in g["params"]):
                self.assertEqual(g["weight_decay"], 0.0)
                self.assertTrue(all(p.dim() < 2 for p in g["params"]))

    def test_works_for_a_model_without_the_premonition_modules(self) -> None:
        class Plain(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.reader = nn.Sequential(nn.Linear(8, 8), nn.LayerNorm(8))
                self.head = nn.Linear(8, 1)

        groups = muon_param_groups(Plain(), 0.1)
        self.assertEqual([g["muon"] for g in groups], [True, False, False])
        self.assertEqual(len(groups[0]["params"]), 1)

    def test_a_bare_linear_model_has_no_muon_group(self) -> None:
        groups = muon_param_groups(nn.Linear(4, 4), 0.1)
        self.assertFalse(any(g["muon"] for g in groups))


class TrainerTest(unittest.TestCase):
    def test_default_is_torch_adamw_and_names_are_validated(self) -> None:
        t = trainer(tiny_model(), "adamw")
        self.assertIsInstance(t.optimizer, torch.optim.AdamW)
        self.assertEqual(inspect.signature(ptrain.MiniTrainer).parameters["optimizer"].default, "adamw")
        self.assertEqual(inspect.signature(ptrain.train_toy).parameters["optimizer"].default, "adamw")
        with self.assertRaises(ValueError):
            trainer(tiny_model(), "sgd")

    def test_muon_trainer_optimizer(self) -> None:
        t = trainer(tiny_model(), "muon", lr=3e-3)
        self.assertIsInstance(t.optimizer, MuonAdamW)
        adamw = [g for g in t.optimizer.param_groups if not g["muon"]]
        self.assertTrue(adamw and all(g["betas"] == (0.9, 0.99) and g["eps"] == 1e-8 for g in adamw))
        self.assertIsInstance(t.optimizer.parts[-1], torch.optim.AdamW)       # the AdamW half is torch's own
        self.assertEqual({g["lr"] for g in t.optimizer.param_groups}, {3e-3})

    def test_the_lr_schedule_drives_every_group(self) -> None:
        t = trainer(tiny_model(), "muon", lr=3e-3, warmup_steps=4)
        batch = synthetic_batch(visits=2, lines=20, seed=11)
        for i in range(3):
            step(t, batch)
            self.assertEqual({g["lr"] for g in t.optimizer.param_groups}, {t.lr_at(i)})
        self.assertAlmostEqual(t.optimizer.param_groups[0]["lr"], 3e-3 * 3 / 4)

    def test_steps_run_and_lower_the_loss(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=11)
        for kind in ("adamw", "muon"):
            with self.subTest(optimizer=kind):
                t = trainer(tiny_model(), kind, lr=3e-3)
                losses = [step(t, batch) for _ in range(25)]
                self.assertTrue(all(math.isfinite(x) for x in losses))
                self.assertLess(losses[-1], 0.8 * losses[0])

    def test_muon_moves_muon_and_adamw_params(self) -> None:
        model = tiny_model()
        before = {n: p.detach().clone() for n, p in model.named_parameters()}
        t = trainer(model, "muon", lr=3e-3)
        step(t, synthetic_batch(visits=2, lines=20, seed=11))
        moved = {n for n, p in model.named_parameters() if not torch.equal(p, before[n])}
        self.assertIn("reader.layers.0.mixer.inp.weight", moved)
        self.assertIn("embed.weight", moved)
        self.assertIn("heads.halt.weight", moved)

    def test_engram_model_trains_under_muon(self) -> None:
        model = tiny_model(engram=True)
        t = trainer(model, "muon")
        batch = synthetic_batch(visits=2, lines=20, seed=11)
        losses = [step(t, batch) for _ in range(3)]
        self.assertTrue(all(math.isfinite(x) for x in losses))
        self.assertGreater(model.writer.engram_tables[0].weight.grad.abs().sum().item(), 0)

    def test_optimizer_state_round_trips(self) -> None:
        batch = synthetic_batch(visits=2, lines=20, seed=11)
        first = trainer(tiny_model(seed=0), "muon")
        for _ in range(3):
            step(first, batch)
        buffer = io.BytesIO()
        torch.save({"model": first.model.state_dict(), "optimizer": first.optimizer.state_dict(),
                    "trainer": first.state_dict()}, buffer)
        buffer.seek(0)
        saved = torch.load(buffer, weights_only=False)
        second = trainer(tiny_model(seed=1), "muon")
        second.model.load_state_dict(saved["model"])
        second.optimizer.load_state_dict(saved["optimizer"])
        second.load_state_dict(saved["trainer"])
        self.assertEqual([g["muon"] for g in second.optimizer.param_groups],
                         [g["muon"] for g in first.optimizer.param_groups])
        for a, b in zip(first.model.parameters(), second.model.parameters()):
            state_a, state_b = first.optimizer.state[a], second.optimizer.state[b]
            self.assertEqual(set(state_a), set(state_b))
            for key in state_a:
                self.assertTrue(torch.equal(torch.as_tensor(state_a[key]), torch.as_tensor(state_b[key])))
        # Continuing from the restored state gives the same next step (both trainers share a fresh generator).
        first.generator.set_state(second.generator.get_state())
        self.assertEqual(step(first, batch), step(second, batch))
        for a, b in zip(first.model.parameters(), second.model.parameters()):
            self.assertTrue(torch.equal(a, b))

    def test_train_toy_passes_the_optimizer_through(self) -> None:
        out = ptrain.train_toy(steps=4, log_every=2, warmup_steps=2, optimizer="muon")
        self.assertIsInstance(out["trainer"].optimizer, MuonAdamW)
        self.assertTrue(math.isfinite(out["history"][-1]["loss"]))

    def test_a_muon_checkpoint_resumes_with_muon(self) -> None:
        import tempfile
        from pathlib import Path
        from memorylab.storage import Budget
        t = trainer(tiny_model(), "muon")
        batches = [synthetic_batch(seed=s) for s in (1, 2)]
        t.calibrate(batches, modes=("teacher",))
        step(t, batches[0])
        with tempfile.TemporaryDirectory() as folder:
            budget = Budget(Path(folder), hard=10_000_000_000, steady=8_000_000_000)
            config = ptrain.checkpoint_config(t, contender="D")
            self.assertEqual(config["optimizer"], "muon")
            ptrain.save_mini_checkpoint(budget, "ck/D", t, config)
            again = ptrain.resume_trainer(Path(folder) / "ck" / "D")
        self.assertIsInstance(again.optimizer, MuonAdamW)
        self.assertEqual(step(again, batches[1]), step(t, batches[1]))
        self.assertNotIn("optimizer", ptrain.checkpoint_config(trainer(tiny_model(), "adamw"), contender="D"))


if __name__ == "__main__":
    unittest.main()
