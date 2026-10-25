"""Reporting additions and the opt-in WSD schedule (all default to the v1 behaviour). Tiny CPU toy fixtures; final_eval itself (needs the
village caches, baselines and a creative checkpoint) is not run end to end here: its pieces (validate per_question, diag_fields,
make_evaluator) are tested directly."""
import random, types, unittest
import torch

from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.toy import ToySpec, make_batch
from premonition.train import label_free, mini_train_config, validate, Curriculum
from v1 import decide, dtrain
from v1 import ckpt as vckpt
from v1.run import DIAG_KEYS, diag_fields, make_evaluator

SPEC = ToySpec()


def tiny(seed=0):
    torch.manual_seed(seed)
    return PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=SPEC.vocab_size, window=64))


def batches(n=2, seed=0):
    rng = random.Random(seed)
    return [label_free(make_batch(SPEC, 3, rng)) for _ in range(n)]


class WsdSchedule(unittest.TestCase):
    def test_pure_function_shape(self):
        f = lambda s: dtrain.wsd_lr(s, 1000, 1e-3, 100)
        self.assertAlmostEqual(f(0), 1e-3 / 100)
        self.assertAlmostEqual(f(49), 1e-3 * 50 / 100)
        for s in (99, 100, 500, 800):                       # warmup done, stable until 80%
            self.assertAlmostEqual(f(s), 1e-3)
        self.assertAlmostEqual(f(900), 1e-3 * (1 - (900 - 800) / (999 - 800)))
        self.assertAlmostEqual(f(999), 0.0, places=12)       # decays to ~0 by the last step
        tail = [f(s) for s in range(800, 1000)]
        self.assertTrue(all(x >= y for x, y in zip(tail, tail[1:])))
        self.assertAlmostEqual(dtrain.wsd_lr(999, 1000, 1e-3, 100, final_frac=0.1), 1e-4)
        self.assertAlmostEqual(dtrain.wsd_lr(5, 1000, 1e-3, 0), 1e-3)     # no warmup

    def test_default_is_the_old_constant_schedule(self):
        model, cfg = tiny(), mini_train_config(lr=1e-3, warmup_steps=100)
        const = dtrain.StepTrainer(model, cfg, "cpu", total_steps=1000)
        wsd = dtrain.StepTrainer(tiny(), cfg, "cpu", total_steps=1000, lr_schedule="wsd")
        for s in (0, 10, 99, 100, 500, 999, 5000):
            self.assertEqual(const.lr_at(s), 1e-3 * min(1.0, (s + 1) / 100))       # exactly the pre-change formula
        self.assertEqual(const.lr_at(999), 1e-3)
        self.assertLess(wsd.lr_at(999), 1e-8)
        with self.assertRaises(ValueError):
            dtrain.StepTrainer(tiny(), cfg, "cpu", total_steps=10, lr_schedule="cosine")

    def test_every_param_group_gets_the_scheduled_lr(self):
        cfg = mini_train_config(lr=1e-3, warmup_steps=2)
        for opt in ("adamw", "muon"):
            tr = dtrain.StepTrainer(tiny(), cfg, "cpu", total_steps=10, optimizer=opt, lr_schedule="wsd", wsd_stable_frac=0.5)
            tr.step = 8
            batch = batches(1)[0]
            plan = tr.plan()
            from premonition.train import planned_loops
            tr._train_step(batch, plan, planned_loops(batch, plan.mode, tr.model.config), False)
            want = tr.lr_at(8)
            self.assertLess(want, 1e-3)
            self.assertTrue(all(g["lr"] == want for g in tr.optimizer.param_groups), opt)


class PerQuestion(unittest.TestCase):
    def test_rows_match_the_reported_numbers(self):
        model, bs = tiny(), batches()
        rows = []
        r = validate(model, bs, per_question=rows)
        self.assertEqual(len(rows), r["questions"])
        self.assertEqual(sum(bool(x["correct"]) for x in rows) / len(rows), r["accuracy"])
        self.assertEqual(sum(v["n"] for v in r["by_depth"].values()), r["questions"])
        self.assertEqual(sum(bool(x["correct_gold_cards"]) for x in rows) / len(rows), r["accuracy_gold_cards"])
        rows2 = []
        validate(model, bs, per_question=rows2)
        self.assertEqual(rows, rows2)                                           # deterministic
        self.assertEqual(validate(model, bs)["accuracy"], r["accuracy"])        # collecting rows changes nothing

    def test_diag_fields(self):
        r = validate(tiny(), batches())
        d = diag_fields(r)
        for k in ("by_depth", "accuracy_gold_cards", "halt_rate", "asked_rate"):
            self.assertIn(k, d)
        self.assertTrue(set(d) <= set(DIAG_KEYS))
        self.assertNotIn("cards", d)


class Evaluator(unittest.TestCase):
    def setUp(self):
        self.model = tiny()
        self.bs = batches()
        self.bridge = types.SimpleNamespace(enabled=True, frozen_ctx=False)
        self.trainer = types.SimpleNamespace(model=self.model, device=torch.device("cpu"))
        self.hook = lambda m: validate(m, self.bs)

    def test_extras_leave_rng_bridge_and_weights_alone(self):
        weights = {k: v.clone() for k, v in self.model.state_dict().items()}
        base = make_evaluator(self.trainer, self.bridge, self.hook, self.bs)
        full = make_evaluator(self.trainer, self.bridge, self.hook, self.bs, val_hook=self.hook, bridge_off=True)
        torch.manual_seed(7)
        before = vckpt.rng_state()
        a = base(self.model)
        after_base = vckpt.rng_state()
        torch.manual_seed(7)
        b = full(self.model)
        after_full = vckpt.rng_state()
        self.assertTrue(torch.equal(after_base["torch"], after_full["torch"]))      # same RNG consumption as the old eval
        self.assertTrue(self.bridge.enabled)
        self.assertFalse(self.bridge.frozen_ctx)
        self.assertTrue(all(torch.equal(weights[k], v) for k, v in self.model.state_dict().items()))
        for k in ("accuracy", "questions", "loops_mean", "gold_recall_at_4", "dev_loss"):    # the old fields are untouched
            self.assertEqual(a[k], b[k])
        for k in ("val_accuracy", "val_questions", "val_by_depth", "val_accuracy_gold_cards", "bridge_off", "by_depth"):
            self.assertIn(k, b)
        self.assertNotIn("val_accuracy", a)
        self.assertNotIn("bridge_off", a)


class Stats(unittest.TestCase):
    def test_wilson(self):
        lo, hi = decide.wilson(80, 100)
        self.assertLess(lo, 0.8)
        self.assertGreater(hi, 0.8)
        self.assertAlmostEqual(lo, 0.7112, places=3)
        self.assertAlmostEqual(hi, 0.8666, places=3)
        self.assertEqual(decide.wilson(0, 10)[0], 0.0)
        self.assertEqual(decide.wilson(10, 10)[1], 1.0)

    def test_mcnemar(self):
        r = decide.mcnemar([1] * 10 + [0] * 2, [0] * 10 + [0] * 2)
        self.assertEqual((r["only_a"], r["only_b"]), (10, 0))
        self.assertAlmostEqual(r["p_value"], 2 / 1024)
        self.assertEqual(decide.mcnemar([1, 0], [1, 0])["p_value"], 1.0)
        self.assertEqual(decide.mcnemar([1, 0], [0, 1])["p_value"], 1.0)


if __name__ == "__main__":
    unittest.main()
