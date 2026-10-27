"""Milestone-3 harness (scripts/premonition_pool_controls.py): matched writer arms, gradient separation, checkpoint
identity, schedule identity, CE parity for the H1 forward, and the cluster bootstrap. CPU; no training."""
from __future__ import annotations

from pathlib import Path
import random
import sys
import tempfile
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_ovn_ladder as L  # noqa: E402
import premonition_ovn_retrieval as R  # noqa: E402
import premonition_pool_controls as H  # noqa: E402

from premonition import toy_ladder  # noqa: E402

H.L, H.R = L, R
SPEC = toy_ladder.LadderSpec()


def item(seed=3, training=True):
    return L.label_free_item(toy_ladder.make(SPEC, 4, random.Random(seed), training=training))


def same_state(a, b, skip=()):
    sa, sb = a.state_dict(), b.state_dict()
    return all(torch.equal(sa[k], sb[k]) for k in sb if k in sa and not k.startswith(skip))


class BuildTest(unittest.TestCase):
    def test_original_arms_are_the_overnight_builds(self):
        self.assertTrue(same_state(H.build("answer", "original", 0), L.build("nothink+qread", 0)))
        self.assertTrue(same_state(H.build("retrieval", "original", 0), R.build("bypass-k1", 0)))

    def test_writers_share_initial_weights_and_the_random_stream(self):
        for kind, writers in (("answer", ("original", "mean")), ("retrieval", ("original", "mean", "two"))):
            after, models = [], []
            for writer in writers:
                models.append(H.build(kind, writer, 1))
                after.append(torch.rand(3))
            for model in models[1:]:
                self.assertTrue(same_state(model, models[0], skip=("writer.pool_value",)))
                self.assertEqual(set(model.state_dict()) - set(models[0].state_dict()),
                                 {"writer.pool_value.weight", "writer.pool_value.bias"} if type(
                                     model.writer).__name__ == "TwoPoolCardWriter" else set())
            self.assertTrue(all(torch.equal(a, after[0]) for a in after))
        two = H.build("retrieval", "two", 1)
        self.assertTrue(torch.equal(two.writer.pool_value.weight, two.writer.pool.weight))
        with self.assertRaises(SystemExit):
            H.build("answer", "two", 0)

    def test_mean_pool_uses_only_the_line_positions(self):
        model = H.build("answer", "mean", 0)
        batch = item()[0]
        self.assertTrue(bool((batch.line_of < 0).any()))                      # padding present
        torch.manual_seed(0)
        hidden = torch.randn(*batch.tokens.shape, model.config.d_model)
        base = model.writer(hidden, batch).values
        moved = hidden.clone()
        moved[batch.line_of < 0] += 100.0                                      # padding / non-line tokens
        self.assertTrue(torch.equal(model.writer(moved, batch).values, base))
        v, line = 0, int(batch.line_of[0, 5])
        moved = hidden.clone()
        moved[v, int((batch.line_of[v] == line).nonzero()[0])] += 1.0
        changed = (model.writer(moved, batch).values != base).any(-1)
        self.assertEqual(changed.nonzero().tolist(), [[v, line]])


class GradientTest(unittest.TestCase):
    def test_separate_pools_split_key_and_value_gradients(self):
        batch = item()[0]
        for writer, split in (("original", False), ("two", True)):
            model = H.build("retrieval", writer, 0)
            hidden = model.read(batch)
            store = model.writer(hidden, batch)
            value_pool = model.writer.pool_value if split else model.writer.pool
            gk = torch.autograd.grad(store.keys.sum(), [model.writer.pool.weight, value_pool.weight],
                                     retain_graph=True, allow_unused=True)
            gv = torch.autograd.grad(store.values.sum(), [model.writer.pool.weight, value_pool.weight],
                                     allow_unused=True)
            nz = lambda g: g is not None and float(g.abs().max()) > 0
            self.assertTrue(nz(gk[0]) and nz(gv[1]))
            self.assertEqual(nz(gk[1]), not split)           # keys reach the value pool only when shared
            self.assertEqual(nz(gv[0]), not split)           # values reach the key pool only when shared

    def test_answer_loss_leaves_the_separate_key_pool_untouched(self):
        batch = item()[0]
        for writer, touched in (("original", True), ("two", False)):
            model = H.build("retrieval", writer, 0)
            model(batch, mode="gold", loops=2, weights={"ans": 1.0})["loss"].backward()
            g = model.writer.pool.weight.grad
            self.assertEqual(g is not None and float(g.abs().max()) > 0, touched)


class HarnessTest(unittest.TestCase):
    def test_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = H.OUT
            H.OUT = Path(tmp)
            try:
                for kind, writer in (("answer", "mean"), ("retrieval", "two")):
                    model = H.build(kind, writer, 2)
                    name = f"{kind}-{writer}-s2"
                    H.save(name, model, kind, writer, 2)
                    loaded, info = H.load(name)
                    self.assertEqual(type(loaded).__name__, type(model).__name__)
                    self.assertTrue(same_state(loaded, model) and same_state(model, loaded))
                    self.assertEqual((info["kind"], info["writer"], info["seed"]), (kind, writer, 2))
                    blob = torch.load(H.OUT / "ckpt" / f"{name}.pt", weights_only=False)
                    self.assertIn("writer_identity", blob["identity"])
            finally:
                H.OUT = old

    def test_reference_schedule_matches_curricula_and_generators(self):
        from premonition.train import Curriculum, MiniTrainer, mini_train_config
        head = [item(seed=9)[0]]
        states, fits = [], []
        for writer in ("original", "mean", "two"):
            model = H.build("retrieval", writer, 0)
            trainer = MiniTrainer(model, mini_train_config(log_every=50, eval_every=0), "cpu", flop_budget=1.0,
                                  seed=0, curriculum=Curriculum())
            fits.append(trainer.calibrate(head))
            states.append(trainer.generator.get_state())
        self.assertTrue(all(torch.equal(s, states[0]) for s in states))
        from premonition.train import planned_loops
        plan = Curriculum().plan(0.5)
        costs = [fits[0](head[0].tokens.numel(), int(planned_loops(head[0], plan.mode, H.R.config_for("bypass-k1")).sum()))]
        self.assertGreater(costs[0], 0)

    def test_answer_forward_matches_the_overnight_loss(self):
        model = H.build("answer", "mean", 0)
        it = item(seed=4)
        want = L.loss_of(model, it, "nothink+qread+meanpool", torch.Generator().manual_seed(7), cards="all")
        order = torch.rand(it[1].shape, generator=torch.Generator().manual_seed(7)).argsort(1)
        got, logits = H.answer_forward(model, it, order)
        self.assertTrue(torch.allclose(got, want, atol=1e-6))
        self.assertEqual(tuple(logits.shape), (len(it[2]), model.config.total_vocab))

    def test_cluster_bootstrap(self):
        ones = H.cluster_bootstrap(torch.ones(40), torch.arange(40) // 4, resamples=500)
        self.assertEqual((ones["point"], ones["lower"], ones["upper"], ones["clusters"]), (1.0, 1.0, 1.0, 10))
        torch.manual_seed(0)
        x = (torch.rand(400) < 0.6).float()
        boot = H.cluster_bootstrap(x, torch.arange(400) // 2, resamples=2000)
        self.assertLessEqual(boot["lower"], boot["point"])
        self.assertLessEqual(boot["point"], boot["upper"])
        same = H.paired_bootstrap(x, x, torch.arange(400) // 2, resamples=500)
        self.assertEqual((same["lower"], same["upper"]), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
