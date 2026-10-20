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

    def test_did_not_train_wins_and_keeps_its_labels(self) -> None:
        runs = pairs([0.10, 0.12, 0.11])
        runs[1]["finite"] = False
        self.assertEqual(self.verdict(runs), "DID NOT TRAIN")
        smoke = [dict(r, settings={"steps": 8, "visits": 16}) for r in runs]
        self.assertEqual(self.verdict(smoke, sealed=False), "UNSEALED: SMOKE, not the card's settings: DID NOT TRAIN")
        partial = runs[:-1]                                                # and an arm missing
        out = self.verdict(partial)
        self.assertTrue(out.startswith("DID NOT TRAIN (and NOT SCORED: the card needs"), out)

    def test_runs_must_be_this_seals_runs(self) -> None:
        ident = {"runner": "r", "card": "c", "package": "p"}
        runs = [dict(r, identity=ident, seal="s1") for r in pairs([0.10, 0.12, 0.11])]
        self.assertEqual(self.r2.score(runs, sealed=True, ident=ident, seal="s1")["verdict"], "PASS")
        other = self.r2.score(runs, sealed=True, ident={**ident, "card": "c2"}, seal="s1")["verdict"]
        self.assertIn("other code than the current runner", other)
        moved = self.r2.score(runs, sealed=True, ident=ident, seal="s2")["verdict"]   # an older seal, or copied in
        self.assertIn("another seal", moved)

    def test_one_torch_and_gates_present(self) -> None:
        runs = [dict(r, settings={"steps": 1500, "visits": 16, "torch": "2.11"}) for r in pairs([0.10, 0.12, 0.11])]
        self.assertEqual(self.verdict(runs), "PASS")
        runs[0] = dict(runs[0], settings={"steps": 1500, "visits": 16, "torch": "2.8"})
        self.assertIn("different torch versions", self.verdict(runs))
        gapped = pairs([0.10, 0.12, 0.11])
        del gapped[1]["gates_own"]
        self.assertIn("gate readouts missing for ['A1-s0']", self.verdict(gapped))

    def test_unreadable_recall_trips_g2(self) -> None:
        runs = pairs([0.10, 0.12, 0.11])
        for r in runs:
            if r["arm"] == "A1":
                r["validation"]["gold_recall_at_4"] = None
        out = self.r2.score(runs, sealed=True)
        self.assertFalse(out["G2"]["ok"])
        self.assertEqual(out["verdict"], "NOT COUNTED (retrieval guard G2)")

    def test_proved_wrong_by_the_band(self) -> None:
        out = self.r2.score(pairs([-0.10, -0.12, -0.11], base=0.40), sealed=True)
        self.assertLess(out["upper"], 0)
        self.assertEqual(out["verdict"], "PROVED WRONG")

    def test_log_line_survives_missing_values(self) -> None:
        line = self.r2.describe({"arm": "A0", "seed": 0, "steps": 3, "seconds": 1.0,
                                 "validation": {"accuracy": 0.1, "accuracy_gold_cards": None, "gold_recall_at_4": None}})
        self.assertIn("recall n/a", line)


class SealTest(unittest.TestCase):
    def test_seal_binds_runner_card_and_package_listing(self) -> None:
        import hashlib
        import subprocess
        import tempfile
        r2 = runner()
        listing = r2.package_listing()
        ident = {"card": "c" * 64, "runner": "r" * 64, "package": hashlib.sha256(listing.encode()).hexdigest()}
        self.assertEqual(r2.identity()["package"], ident["package"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with self.assertRaises(SystemExit):
                r2.check_seal(out, ident, unsealed=False)
            self.assertFalse(r2.check_seal(out, ident, unsealed=True))
            (out / r2.PACKAGE).write_text(listing)
            (out / r2.SEAL).write_text(f"{'c' * 64}  design/steals-2026-10-17/R2-STAGE0-CARD.md\n"
                                       f"{'r' * 64}  scripts/premonition_steals_r2_stage0.py\n"
                                       f"{ident['package']}  artifacts/x/r2-stage0/{r2.PACKAGE}\n")
            self.assertTrue(r2.check_seal(out, ident, unsealed=False))
            with self.assertRaises(SystemExit):
                r2.check_seal(out, ident, unsealed=True)
            with self.assertRaises(SystemExit):
                r2.check_seal(out, {**ident, "package": "q" * 64}, unsealed=False)
            (out / r2.PACKAGE).write_text(listing + "0" * 64 + "  premonition/extra.py\n")   # listing edited
            with self.assertRaises(SystemExit):
                r2.check_seal(out, ident, unsealed=False)
            (out / r2.PACKAGE).write_text(listing)
            checked = subprocess.run(["sha256sum", "--quiet", "-c", str(out / r2.PACKAGE)], cwd=r2.ROOT,
                                     capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)   # independently checkable
        self.assertNotIn("commit", r2.identity())
        self.assertEqual(set(r2.identity()), {"runner", "card", "package"})


class MainTest(unittest.TestCase):
    """main() with training replaced by a stub: the save-then-gates order, reuse, the sealed-settings rule and the
    single writer of result.json."""

    def setUp(self) -> None:
        import tempfile
        from unittest import mock
        self.mock = mock
        self.r2 = runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.trained = []

    def stub_run(self, arm, seed, settings, ident, sealed, seal):
        self.trained.append((arm, seed))
        result = {"arm": arm, "seed": seed, "settings": settings, "identity": ident, "sealed": sealed, "seal": seal,
                  "steps": 3, "seconds": 0.0, "chance": 0.0625, "finite": True,
                  "validation": {"accuracy": 0.3, "accuracy_gold_cards": 0.3, "gold_recall_at_4": 0.5}}
        return result, None

    def main(self, *argv, gates=None):
        gates = gates or (lambda result, model: {"gates_own": {"gold": {"rows": 40, "mean": 0.9}}})
        with self.mock.patch.object(self.r2, "run", self.stub_run), self.mock.patch.object(self.r2, "gates", gates), \
                self.mock.patch("sys.argv", ["r2", "--out", str(self.out), *argv]), \
                self.mock.patch("builtins.print"):
            self.r2.main()

    def test_training_never_writes_result_and_score_does(self) -> None:
        self.main("--unsealed", "--steps", "8")
        self.assertEqual(len(self.trained), 6)
        self.assertFalse((self.out / "result.json").exists())
        self.main("--unsealed", "--steps", "8")                           # reuse: nothing trains again
        self.assertEqual(len(self.trained), 6)
        self.main("--unsealed", "--score")
        import json
        verdict = json.loads((self.out / "result.json").read_text())["score"]["verdict"]
        self.assertTrue(verdict.startswith("UNSEALED: SMOKE"), verdict)

    def test_a_gate_failure_keeps_the_saved_run(self) -> None:
        def broken(result, model):
            raise RuntimeError("boom")
        self.main("--unsealed", "--steps", "8", "--seeds", "0", gates=broken)
        import json
        saved = json.loads((self.out / "A1-s0.json").read_text())
        self.assertEqual(saved["gates_error"], "RuntimeError: boom")
        self.assertEqual(saved["steps"], 3)

    def test_a_sealed_directory_takes_only_the_card_settings(self) -> None:
        listing = self.r2.package_listing()
        ident = self.r2.identity()
        (self.out / self.r2.PACKAGE).write_text(listing)
        (self.out / self.r2.SEAL).write_text(f"{ident['card']}  design/steals-2026-10-17/R2-STAGE0-CARD.md\n"
                                             f"{ident['runner']}  scripts/premonition_steals_r2_stage0.py\n"
                                             f"{ident['package']}  {self.r2.PACKAGE}\n")
        with self.assertRaises(SystemExit) as cm:
            self.main("--steps", "8")
        self.assertIn("takes only the card's settings", str(cm.exception))
        self.assertEqual(self.trained, [])


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
