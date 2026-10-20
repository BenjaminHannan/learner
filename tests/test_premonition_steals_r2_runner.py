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
    out = {"arm": arm, "seed": seed, "finite": True, "chance": 0.0625, "identity": ident, "sealed": True,
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

    def verdict(self, runs, sealed=True) -> str:
        return self.r2.score(runs, sealed=sealed)["verdict"]

    def test_pass_and_guards(self) -> None:
        self.assertEqual(self.verdict(pairs([0.10, 0.12, 0.11])), "PASS")
        self.assertTrue(self.verdict(pairs([0.10, 0.12, 0.11], gate=0.1)).startswith("GAIN NOT COUNTED"))
        self.assertTrue(self.verdict(pairs([0.10, 0.12, 0.11], rows=9)).startswith("GAIN NOT COUNTED"))
        self.assertTrue(self.verdict(pairs([0.10, 0.12, 0.11], recall=0.1)).startswith("NOT COUNTED"))

    def test_at_chance_needs_both_arms_near_chance_not_only_a_small_gap(self) -> None:
        near = self.verdict(pairs([0.002, -0.004, 0.003], base=0.06))
        self.assertEqual(near, "PROVED WRONG (both arms at chance in every seed)")
        learned = self.verdict(pairs([0.002, -0.004, 0.003], base=0.40))
        self.assertNotIn("at chance", learned)

    def test_no_extension(self) -> None:
        """Ruling 10-20: exactly 3 seeds, verdict on 3 seeds; a near miss is just NOT SHOWN."""
        near = self.r2.score(pairs([0.040, 0.010, 0.025]), sealed=True)     # mean 2.5 pts, within 1 SE of 3
        self.assertEqual(near["verdict"], "NOT SHOWN")
        self.assertNotIn("extension_due", near)
        self.assertFalse(hasattr(self.r2, "EXTENSION_SEEDS"))
        for runs in (pairs([0.1, 0.1, 0.1, 0.1, 0.1], seeds=(0, 1, 2, 3, 4)), pairs([0.1, 0.1], seeds=(0, 1)),
                     pairs([0.1, 0.1, 0.1]) + pairs([0.1], seeds=(0,))):
            self.assertTrue(self.verdict(runs).startswith("NOT SCORED"))

    def test_mixed_code_and_smoke_settings_are_flagged(self) -> None:
        runs = pairs([0.10, 0.12, 0.11])
        runs[-1]["identity"] = "y"
        self.assertTrue(self.verdict(runs).startswith("NOT SCORED"))
        smoke = [dict(r, settings={"steps": 8, "visits": 16}) for r in pairs([0.10, 0.12, 0.11])]
        self.assertTrue(self.verdict(smoke).startswith("SMOKE"))
        one = pairs([0.10, 0.12, 0.11])                                   # every run is checked, not the first
        one[4]["settings"] = {"steps": 1500, "visits": 8}
        self.assertTrue(self.verdict(one).startswith("SMOKE"))

    def test_unsealed_is_labelled(self) -> None:
        self.assertEqual(self.verdict(pairs([0.10, 0.12, 0.11]), sealed=False), "UNSEALED: PASS")
        stray = pairs([0.10, 0.12, 0.11])
        stray[2]["sealed"] = False                                        # made outside the sealed directory
        self.assertEqual(self.verdict(stray), "UNSEALED: PASS")

    def test_did_not_train_wins(self) -> None:
        runs = [dict(r, settings={"steps": 8, "visits": 16}) for r in pairs([0.10, 0.12, 0.11])]
        runs[1]["finite"] = False
        self.assertEqual(self.verdict(runs, sealed=False), "DID NOT TRAIN")

    def test_log_line_survives_missing_values(self) -> None:
        line = self.r2.describe({"arm": "A0", "seed": 0, "steps": 3, "seconds": 1.0,
                                 "validation": {"accuracy": 0.1, "accuracy_gold_cards": None, "gold_recall_at_4": None}})
        self.assertIn("recall n/a", line)


class SealTest(unittest.TestCase):
    def test_seal_binds_runner_card_and_package(self) -> None:
        import tempfile
        r2 = runner()
        ident = {"card": "c" * 64, "runner": "r" * 64, "package": "p" * 64}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with self.assertRaises(SystemExit):
                r2.check_seal(out, ident, unsealed=False)
            self.assertFalse(r2.check_seal(out, ident, unsealed=True))
            (out / "SEAL.sha256.txt").write_text(f"{'c' * 64}  design/steals-2026-10-17/R2-STAGE0-CARD.md\n"
                                                 f"{'r' * 64}  scripts/premonition_steals_r2_stage0.py\n"
                                                 f"{'p' * 64}  {r2.PACKAGE}\n")
            self.assertTrue(r2.check_seal(out, ident, unsealed=False))
            with self.assertRaises(SystemExit):
                r2.check_seal(out, ident, unsealed=True)
            with self.assertRaises(SystemExit):
                r2.check_seal(out, {**ident, "package": "q" * 64}, unsealed=False)
        self.assertNotIn("commit", r2.identity())
        self.assertEqual(set(r2.identity()), {"runner", "card", "package"})


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
        self.assertNotIn("cross", own)
        with torch.no_grad():
            model.heads.ask.bias.fill_(20.0)
            model.heads.halt.bias.fill_(-20.0)
        asked = r2.gate_means(model, batches, model.answer)
        self.assertGreater(asked["gold"]["rows"] + asked["wrong"]["rows"], 0)

    def test_cross_gate_reads_real_answer_positions_once_per_loop(self) -> None:
        import torch
        from learnlab.core import IGNORE_INDEX
        from premonition.model import PremonitionMini
        from tests.test_premonition_model import synthetic_batch, tiny_config
        r2 = runner()
        torch.manual_seed(0)
        model = PremonitionMini(tiny_config(fetch_gate=True))
        batches = [synthetic_batch(visits=2, lines=24, seed=3), synthetic_batch(visits=2, lines=24, seed=4)]
        real = sum(int((b.answer != IGNORE_INDEX).sum()) for b in batches)
        padded = sum(b.answer.shape[0] * int((b.answer != IGNORE_INDEX).sum(1).max()) for b in batches)
        cross = r2.cross_gate_means(model, batches)
        self.assertEqual(cross["rows"], 4 * real)                          # 4 fixed loops, real positions only
        self.assertLessEqual(real, padded)
        self.assertEqual(len(cross["per_head"]), model.config.n_heads)


if __name__ == "__main__":
    unittest.main()
