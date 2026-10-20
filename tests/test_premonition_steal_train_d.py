"""R1 stage 1, prerequisite P1: `train.train_d(optimizer=...)` (design/steals-2026-10-17/R1-STAGE1-BID.md).

On a tiny generated village, `train_d` with the default optimizer gives the same report (timing fields aside) and
the same checkpoint weights as the base commit's own `train_d`. With `optimizer="muon"` it trains with MuonAdamW,
says so in the report and the checkpoint, and resumes as Muon.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import torch

from premonition import train as ptrain
from premonition.muon import MuonAdamW
from tests.test_premonition_steals_identity import base_modules

TIMING = ("seconds", "per_s", "started")


def strip(value):
    """The report without wall-clock fields (and without the checkpoint's absolute path)."""
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if not any(t in k for t in TIMING) and k != "checkpoint"}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


class TrainDOptimizerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from learnlab.tokenizer import Tokenizer
        from learnlab import step1
        from learnlab.village.names import SYLLABLES
        from learnlab.village.shards import write_shards
        from memorylab.storage import Budget
        cls.holder = tempfile.TemporaryDirectory(prefix="steal-train-d-")
        cls.root = Path(cls.holder.name)
        for split, count in (("train", 24), ("validation", 8)):
            write_shards(split, count, cls.root / "data" / "v", 1, seed=0, visits_per_shard=8, verbose=False)
        texts = [text.read_text(encoding="utf-8") for text, _ in step1.shard_files(cls.root / "data" / "v" / "train")]
        Tokenizer.train(texts, vocab_size=1200, syllables=SYLLABLES).save(cls.root / "tok.json")
        cls.budget = Budget(cls.root, hard=10_000_000_000, steady=8_000_000_000)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.holder.cleanup()

    def train(self, module, name: str, **kwargs) -> dict:
        return module.train_d(self.budget, data_rel="data/v", tokenizer_path="tok.json", flop_budget=6e10,
                              size="tiny", device="cpu", seed=0, max_tokens=4000, max_visits=8, warmup_steps=2,
                              log_every=2, eval_every=1000, eval_visits=8, calibration_batches=2,
                              checkpoint=f"ckpt/{name}", log=lambda _line: None, **kwargs)

    def test_the_default_matches_the_base_commit(self) -> None:
        base_train = base_modules()[3]
        new, old = self.train(ptrain, "new"), self.train(base_train, "old")
        self.assertGreater(new["steps"], 2)
        self.assertNotIn("optimizer", new)
        self.assertEqual(strip(new), strip(old))
        a = torch.load(self.root / "ckpt" / "new" / "state.pt", map_location="cpu", weights_only=False)
        b = torch.load(self.root / "ckpt" / "old" / "state.pt", map_location="cpu", weights_only=False)
        for name, tensor in a["model"].items():
            self.assertTrue(torch.equal(tensor, b["model"][name]), name)

    def test_muon_trains_reports_and_resumes(self) -> None:
        report = self.train(ptrain, "muon", optimizer="muon")
        self.assertEqual(report["optimizer"], "muon")
        self.assertEqual(report["status"], "completed")
        again = ptrain.resume_trainer(self.root / "ckpt" / "muon")
        self.assertIsInstance(again.optimizer, MuonAdamW)
        with self.assertRaises(ValueError):
            self.train(ptrain, "bad", optimizer="sgd")


if __name__ == "__main__":
    unittest.main()
