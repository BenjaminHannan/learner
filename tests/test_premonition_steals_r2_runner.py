"""The R2 stage-0 runner's scoring follows its sealed card (design/steals-2026-10-17/R2-STAGE0-CARD.md)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "premonition_steals_r2_stage0.py"


def runner():
    spec = importlib.util.spec_from_file_location("premonition_steals_r2_stage0", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(arm, seed, acc, gold=None, recall=0.5, gate=0.9, rows=40, ident="x", steps=1500):
    out = {"arm": arm, "seed": seed, "finite": True, "chance": 0.0625, "identity": ident,
           "settings": {"steps": steps, "visits": 16},
           "validation": {"accuracy": acc, "accuracy_gold_cards": acc if gold is None else gold,
                          "gold_recall_at_4": recall}}
    if arm == "A1":
        out["gates_own"] = {"gold": {"rows": rows, "mean": gate}}
    return out


def pairs(d, base=0.30, seeds=(0, 1, 2), **kw):
    runs = []
    for seed, x in zip(seeds, d):
        runs += [run("A0", seed, base), run("A1", seed, base + x, **kw)]
    return runs


class ScoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.r2 = runner()

    def test_pass_and_guards(self) -> None:
        self.assertEqual(self.r2.score(pairs([0.10, 0.12, 0.11]))["verdict"], "PASS")
        self.assertTrue(self.r2.score(pairs([0.10, 0.12, 0.11], gate=0.1))["verdict"].startswith("GAIN NOT COUNTED"))
        self.assertTrue(self.r2.score(pairs([0.10, 0.12, 0.11], rows=9))["verdict"].startswith("GAIN NOT COUNTED"))
        self.assertTrue(self.r2.score(pairs([0.10, 0.12, 0.11], recall=0.1))["verdict"].startswith("NOT COUNTED"))

    def test_at_chance_needs_both_arms_near_chance_not_only_a_small_gap(self) -> None:
        near = self.r2.score(pairs([0.002, -0.004, 0.003], base=0.06))["verdict"]
        self.assertEqual(near, "PROVED WRONG (both arms at chance in every seed)")
        learned = self.r2.score(pairs([0.002, -0.004, 0.003], base=0.40))["verdict"]
        self.assertNotIn("at chance", learned)

    def test_extension_is_called_for_and_enforced(self) -> None:
        due = pairs([0.040, 0.010, 0.025])                             # mean 2.5 pts, within 1 SE of 3
        first = self.r2.score(due)
        self.assertTrue(first["extension_due"], first)
        self.assertTrue(first["verdict"].startswith("EXTENSION DUE"))
        extended = self.r2.score(due + pairs([0.03, 0.03], seeds=(3, 4)))
        self.assertEqual(extended["seeds"], [0, 1, 2, 3, 4])
        self.assertIn("three_seed", extended)
        clear = pairs([-0.05, -0.04, -0.06])                           # clearly worse: no extension
        self.assertFalse(self.r2.score(clear)["extension_due"])
        refused = self.r2.score(clear + pairs([0.2, 0.2], seeds=(3, 4)))
        self.assertTrue(refused["verdict"].startswith("NOT SCORED"))

    def test_mixed_code_and_smoke_settings_are_flagged(self) -> None:
        runs = pairs([0.10, 0.12, 0.11])
        runs[-1]["identity"] = "y"
        self.assertTrue(self.r2.score(runs)["verdict"].startswith("NOT SCORED"))
        smoke = [dict(r, settings={"steps": 8, "visits": 16}) for r in pairs([0.10, 0.12, 0.11])]
        self.assertTrue(self.r2.score(smoke)["verdict"].startswith("SMOKE"))


class GateTest(unittest.TestCase):
    def test_own_fetch_gates_count_only_the_answer_paths_inserts(self) -> None:
        """A model that never asks fetches nothing in answer(): G3 must see 0 own rows (the teacher-mode pass that
        reads the decoder gate must not leak its forced cards into the card-gate record)."""
        import torch
        from premonition.model import PremonitionMini
        from tests.test_premonition_model import synthetic_batch, tiny_config
        r2 = runner()
        torch.manual_seed(0)
        model = PremonitionMini(tiny_config(fetch_gate=True))
        with torch.no_grad():
            model.heads.ask.bias.fill_(-20.0)                           # never asks
        batches = [synthetic_batch(visits=2, lines=24, seed=3)]
        own = r2.gate_means(model, batches, model.answer)
        self.assertEqual(own["gold"]["rows"] + own["wrong"]["rows"], 0)
        self.assertGreater(own["cross"]["rows"], 0)
        with torch.no_grad():
            model.heads.ask.bias.fill_(20.0)
            model.heads.halt.bias.fill_(-20.0)
        asked = r2.gate_means(model, batches, model.answer)
        self.assertGreater(asked["gold"]["rows"] + asked["wrong"]["rows"], 0)


if __name__ == "__main__":
    unittest.main()
