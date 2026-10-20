"""R1 stage 1 runner (scripts/premonition_steals_r1_stage1.py, prerequisite P2): the evaluation-free training clock,
the interpolation, the verdict order, the seal check and the copy-off manifest. The end-to-end CPU dry run is P3
(`premonition_steals_r1_stage1.py dry`)."""
from __future__ import annotations

import copy
import importlib.util
import itertools
import json
import math
from pathlib import Path
import tempfile
import time
import unittest

import torch

from premonition import train as ptrain

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("r1s1", ROOT / "scripts" / "premonition_steals_r1_stage1.py")
r1s1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r1s1)


def make_run(arm: str, seed: int, loss: float, *, seconds: float = 100.0, acc: float = 0.5, recall=0.9) -> dict:
    """A run whose held-out loss falls linearly from loss + 1 to `loss` over `seconds` of training."""
    return {"arm": arm, "seed": seed, "settings": dict(r1s1.CARD_SETTINGS, flop_budget=1e16),
            "bound": {"code": {"x": 1}, "data": {"price": "p" * 64}},
            "status": "completed", "budget_ok": True, "finite": True, "train_seconds": seconds, "steps": 1000,
            "flops": 1e15, "provenance": {"torch": "2.11.0"},
            "s_per_step": seconds / 1000, "curve": [(0.0, 0, loss + 1.0), (seconds, 1000, loss)],
            "validation": {"accuracy": acc, "gold_recall_at_4": recall}}


def card(d=(0.5, 0.6, 0.7), **a1) -> list[dict]:
    """A0 at loss 10 in every seed; A1 lower by d_s (a positive d is a gain for Muon)."""
    return [run for seed, gain in zip(r1s1.CARD_SEEDS, d)
            for run in (make_run("A0", seed, 10.0), make_run("A1", seed, 10.0 - gain, **a1))]


class TrainClockTest(unittest.TestCase):
    def test_evaluation_time_is_off_the_clock(self) -> None:
        trainer, head, stream, held_out, _ = ptrain.toy_setup("D", steps=12, log_every=3, eval_every=3)
        pause = 0.4

        def evaluate(_model):
            time.sleep(pause)
            return {}

        started = time.perf_counter()
        trainer.train(itertools.chain(head, stream), evaluate=evaluate)
        wall = time.perf_counter() - started
        evals = sum("eval" in r for r in trainer.history)
        clock = r1s1.train_clock(trainer.history)
        self.assertGreaterEqual(evals, 3)
        self.assertEqual(sorted(clock), [r["step"] for r in trainer.history if "eval" not in r])
        self.assertLess(clock[max(clock)], wall - evals * pause + 0.05)       # no evaluation pause counted
        self.assertGreater(clock[max(clock)], 0.5 * (wall - evals * pause))   # and the training time is

    def test_eval_steps_need_a_log_window(self) -> None:
        history = [{"step": 2, "tokens": 10, "tokens_per_s": 10.0}, {"step": 3, "eval": {"held_out": {"loss": 1.0}}}]
        with self.assertRaises(RuntimeError):
            r1s1.curve_of({"history": history, "validation": {"held_out": {"loss": 1.0}}, "steps": 3})

    def test_an_aborted_report_still_gives_a_curve(self) -> None:
        history = [{"step": 2, "tokens": 10, "tokens_per_s": 10.0}, {"step": 2, "eval": {"held_out": {"loss": 3.0}}},
                   {"step": 3, "tokens": 15, "tokens_per_s": 5.0}]
        curve = r1s1.curve_of({"history": history, "validation": {"held_out": {"loss": 2.0}}})   # no "steps"
        self.assertEqual(curve, [(1.0, 2, 3.0), (2.0, 3, 2.0)])


class LossAtTest(unittest.TestCase):
    def test_interpolates_and_clamps(self) -> None:
        curve = [(10.0, 1, 4.0), (20.0, 2, 2.0), (20.0, 2, 2.0)]
        self.assertEqual(r1s1.loss_at(curve, 15.0), 3.0)
        self.assertEqual(r1s1.loss_at(curve, 5.0), 4.0)
        self.assertEqual(r1s1.loss_at(curve, 99.0), 2.0)
        self.assertEqual(r1s1.loss_at(curve, 20.0), 2.0)

    def test_t_star_is_the_shorter_arm(self) -> None:
        runs = card()
        for r in runs:
            if r["arm"] == "A1":
                r.update(train_seconds=200.0, curve=[(0.0, 0, 11.0), (200.0, 1000, r["curve"][-1][2])])
        rows = r1s1.score(runs, sealed=True)["rows"]
        self.assertEqual([row["t_star"] for row in rows], [100.0] * 3)
        self.assertAlmostEqual(rows[0]["loss_A1"], 11.0 - 0.5 * (11.0 - 9.5))      # A1 halfway down its curve


class ScoreTest(unittest.TestCase):
    def verdict(self, runs, sealed=True) -> str:
        return r1s1.score(runs, sealed=sealed)["verdict"]

    def test_pass(self) -> None:
        self.assertEqual(self.verdict(card()), "PASS")

    def test_relative_effect_floor(self) -> None:
        self.assertEqual(self.verdict(card(d=(0.25, 0.28, 0.31))), "NOT SHOWN")      # < 3% of 10

    def test_proved_wrong(self) -> None:
        self.assertEqual(self.verdict(card(d=(-0.5, -0.6, -0.7))), "PROVED WRONG")

    def test_retrieval_guard_pooled(self) -> None:
        runs = card()
        for r in runs:
            if r["arm"] == "A1":
                r["validation"]["gold_recall_at_4"] = 0.7                          # 0.7 < 0.8 x 0.9, 0.2 below
        self.assertEqual(self.verdict(runs), "NOT COUNTED (retrieval guard)")

    def test_retrieval_guard_per_seed(self) -> None:
        runs = card()
        a0 = [r for r in runs if r["arm"] == "A0"]
        a1 = [r for r in runs if r["arm"] == "A1"]
        for r, value in zip(a0, (0.5, 0.5, 1.0)):
            r["validation"]["gold_recall_at_4"] = value
        for r, value in zip(a1, (0.39, 0.39, 1.0)):                               # pooled ratio 0.89, 2 seeds -0.11
            r["validation"]["gold_recall_at_4"] = value
        out = r1s1.score(runs, sealed=True)
        self.assertGreater(out["G_RET"]["pooled_A1_A0"][0], 0.8 * out["G_RET"]["pooled_A1_A0"][1])
        self.assertEqual(out["verdict"], "NOT COUNTED (retrieval guard)")

    def test_missing_recall_trips_the_retrieval_guard(self) -> None:
        runs = card()
        runs[1]["validation"]["gold_recall_at_4"] = None
        self.assertEqual(self.verdict(runs), "NOT COUNTED (retrieval guard)")

    def test_accuracy_guard(self) -> None:
        self.assertEqual(self.verdict(card(acc=0.46)), "NOT COUNTED (accuracy guard)")   # 4 points below
        self.assertEqual(self.verdict(card(acc=0.475)), "PASS")                          # 2.5 points below

    def test_retrieval_guard_comes_before_accuracy(self) -> None:
        self.assertEqual(self.verdict(card(acc=0.4, recall=0.1)), "NOT COUNTED (retrieval guard)")

    def test_did_not_train_wins(self) -> None:
        runs = card()
        runs[3]["finite"] = False
        self.assertEqual(self.verdict(runs), "DID NOT TRAIN")
        runs[0]["status"] = "aborted"                                             # still first, and labelled
        out = self.verdict(runs, sealed=False)
        self.assertTrue(out.startswith("DID NOT TRAIN (and not the card's runs: unsealed"), out)
        partial = card()[:-1]                                                     # an arm missing
        partial[0]["finite"] = False
        self.assertTrue(self.verdict(partial).startswith("DID NOT TRAIN (and not the card's runs: arms"))

    def test_unpaired_steps_are_not_scored(self) -> None:
        runs = card()
        runs[3]["steps"] = 999
        out = r1s1.score(runs, sealed=True)
        self.assertIn("unpaired steps or FLOPs at seeds [1]", out["verdict"])
        runs = card()
        runs[5]["flops"] = 1.01e15
        self.assertIn("unpaired", self.verdict(runs))

    def test_runs_must_match_the_sealed_code_and_one_torch(self) -> None:
        out = r1s1.score(card(), sealed=True, ident={"x": 2})
        self.assertIn("other code than this sealed runner", out["verdict"])
        self.assertEqual(r1s1.score(card(), sealed=True, ident={"x": 1})["verdict"], "PASS")
        runs = card()
        runs[2]["provenance"] = {"torch": "2.8.0"}
        self.assertIn("different torch versions", self.verdict(runs))

    def test_not_scored_reasons_keep_the_numbers(self) -> None:
        cases = {"unsealed": (card(), False)}
        settings = card()
        settings[0]["settings"]["lr"] = 3e-3
        cases["settings"] = (settings, True)
        bound = card()
        bound[2]["bound"] = {"code": {"x": 2}, "data": {"price": "p" * 64}}
        cases["code or data"] = (bound, True)
        incomplete = card()
        incomplete[4]["budget_ok"] = False
        cases["incomplete"] = (incomplete, True)
        seeds = [r for r in card() if r["seed"] != 2]
        cases["seeds"] = (seeds, True)
        priced = card()
        for r in priced:
            r["bound"]["data"].pop("price")
        cases["PRICE"] = (priced, True)
        f = card()
        f[1]["settings"]["flop_budget"] = 2e16
        cases["settings differ"] = (f, True)
        for word, (runs, sealed) in cases.items():
            out = r1s1.score(runs, sealed=sealed)
            self.assertTrue(out["verdict"].startswith("NOT SCORED"), (word, out["verdict"]))
            self.assertIn(word, out["verdict"])
            self.assertIn("would_be", out)

    def test_a_missing_arm_is_not_scored(self) -> None:
        runs = card()[:-1]
        self.assertTrue(self.verdict(runs).startswith("NOT SCORED"))
        self.assertTrue(self.verdict(card() + [copy.deepcopy(card()[0])]).startswith("NOT SCORED"))

    def test_arm_order_alternates(self) -> None:
        self.assertEqual([r1s1.arm_order(s) for s in r1s1.CARD_SEEDS], [["A0", "A1"], ["A1", "A0"], ["A0", "A1"]])


def stage_1a(arm: str, s_per_step: float, startup: float = 60.0) -> dict:
    """A 1a run: 300 steps at 1e12 FLOPs each, one evaluation of 20 s at the end, `startup` s before training."""
    return {"arm": arm, "status": "completed", "finite": True, "flops": 3e14, "steps": 300, "s_per_step": s_per_step,
            "train_seconds": 300 * s_per_step, "wall_seconds": 300 * s_per_step + 20.0 + startup, "evals": [],
            "final_eval_seconds": 20.0}


class PriceTest(unittest.TestCase):
    def test_largest_f_within_the_stop(self) -> None:
        arms = [stage_1a("A0", 0.10, startup=660.0), stage_1a("A1", 0.11)]       # A0 ran first: +600 s of caches
        out = r1s1.price(arms, dph=0.45, build_seconds=1200.0)
        allowed = 0.8 * 2.50 / 0.45 * 3600
        self.assertLess(out["flop_budget"], r1s1.PRICE["f_max"])
        self.assertLessEqual(r1s1.projected_seconds(out["flop_budget"], arms, 1200.0, 500), allowed)
        self.assertGreater(r1s1.projected_seconds(out["flop_budget"] * 1.1, arms, 1200.0, 500), allowed)
        self.assertEqual(float(f"{out['flop_budget']:.2g}"), out["flop_budget"])     # two significant figures
        self.assertLessEqual(out["projected_dollars"], 2.0)
        self.assertAlmostEqual(out["muon_step_ratio"], 1.1)
        self.assertTrue(out["gate_1a"]["muon_step_ratio_ok"])
        # by hand: 3 seeds x (steps x 0.21 s + evals x 20 s + 60 s x 2) + 1200 + 900 at F / 1e12 steps
        steps = out["flop_budget"] / 1e12
        hand = 3 * (steps * 0.21 + 2 * (math.floor(steps / 500) + 1) * 20.0 + 120.0) + 2100.0 + 600.0
        self.assertAlmostEqual(r1s1.projected_seconds(out["flop_budget"], arms, 1200.0, 500), hand)

    def test_capped_at_f_max_and_gate(self) -> None:
        arms = [stage_1a("A0", 1e-6), stage_1a("A1", 2e-6)]
        out = r1s1.price(arms, dph=0.45, build_seconds=0.0)
        self.assertEqual(out["flop_budget"], r1s1.PRICE["f_max"])
        self.assertFalse(out["gate_1a"]["muon_step_ratio_ok"])

    def test_refuses_when_even_f_min_does_not_fit(self) -> None:
        arms = [stage_1a("A0", 2.0), stage_1a("A1", 2.0)]                       # 2 s/step: F_min alone is ~3.6 h
        with self.assertRaises(SystemExit):
            r1s1.price(arms, dph=0.45, build_seconds=1200.0)

    def test_check_price(self) -> None:
        good = r1s1.price([stage_1a("A0", 0.10), stage_1a("A1", 0.11)], dph=0.45, build_seconds=1200.0)
        r1s1.check_price(json.loads(json.dumps(good)))                           # survives the JSON round trip
        for change in ({"flop_budget": 5e16}, {"flop_budget": 1e14}, {"gate_1a": {"muon_step_ratio_ok": False}},
                       {"projected_dollars": 2.2}, {"rule": dict(r1s1.PRICE, safety=0.95)}):
            with self.assertRaises(SystemExit, msg=str(change)):
                r1s1.check_price({**good, **change})

    def test_refuses_an_unfinished_1a(self) -> None:
        arms = [stage_1a("A0", 0.1), dict(stage_1a("A1", 0.1), status="aborted")]
        with self.assertRaises(SystemExit):
            r1s1.price(arms, dph=0.45, build_seconds=0.0)


class SealAndManifestTest(unittest.TestCase):
    def test_seal(self) -> None:
        ident = {"card": "c" * 64, "runner": "r" * 64, "package": "p" * 64}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with self.assertRaises(SystemExit):
                r1s1.check_seal(out, ident, unsealed=False)
            self.assertFalse(r1s1.check_seal(out, ident, unsealed=True))
            (out / r1s1.SEAL).write_text(f"{'c' * 64}  design/steals-2026-10-17/R1-STAGE1-CARD.md\n"
                                         f"{'r' * 64}  scripts/premonition_steals_r1_stage1.py\n"
                                         f"{'p' * 64}  {r1s1.PACKAGE}\n")
            self.assertTrue(r1s1.check_seal(out, ident, unsealed=False))
            with self.assertRaises(SystemExit):
                r1s1.check_seal(out, {**ident, "runner": "x" * 64}, unsealed=False)
            with self.assertRaises(SystemExit):                                   # no plumbing in a sealed dir
                r1s1.check_seal(out, ident, unsealed=True)
            with self.assertRaises(SystemExit):                                   # the package is sealed too
                r1s1.check_seal(out, {**ident, "package": "q" * 64}, unsealed=False)

    def test_manifest_catches_changes_and_losses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "ckpt").mkdir()
            (out / "a.json").write_text("{}")
            (out / "ckpt" / "state.pt").write_bytes(b"\0\1")
            r1s1.write_manifest(out)
            self.assertEqual(r1s1.verify(out), [])
            (out / "a.json").write_text("{ }")
            (out / "ckpt" / "state.pt").unlink()
            self.assertEqual(sorted(r1s1.verify(out)), ["a.json", "ckpt/state.pt"])


class HeldOutLossTest(unittest.TestCase):
    def test_fixed_and_side_effect_free(self) -> None:
        trainer, _, _, held_out, _ = ptrain.toy_setup("D", steps=4)
        model = trainer.model
        rng = torch.get_rng_state()
        first = r1s1.held_out_loss(model, held_out)
        self.assertTrue(model.training)                                          # mode restored
        self.assertTrue(torch.equal(rng, torch.get_rng_state()))                 # explicit generators only
        self.assertEqual(first["held_out"], r1s1.held_out_loss(model, held_out)["held_out"])
        self.assertEqual(set(first["held_out"]), {"loss", "lm", "ask", "ans", "halt"})

    def test_weighted_by_visits(self) -> None:
        class Batch:
            def __init__(self, visits: int, loss: float) -> None:
                self.tokens, self.loss = torch.zeros(visits, 3), loss

            def to(self, _device):
                return self

        class Fake(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.w = torch.nn.Parameter(torch.zeros(1))

            def forward(self, batch, **_):
                return {k: torch.tensor(batch.loss) for k in ("loss", "lm", "ask", "ans", "halt")}

        out = r1s1.held_out_loss(Fake(), [Batch(5, 2.0), Batch(45, 1.0)])["held_out"]
        self.assertAlmostEqual(out["loss"], (5 * 2.0 + 45 * 1.0) / 50)          # not the plain mean 1.5


if __name__ == "__main__":
    unittest.main()
