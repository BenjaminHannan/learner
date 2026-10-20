"""R1 stage 1, prerequisite P1: `train.train_d(optimizer=...)` (design/steals-2026-10-17/R1-STAGE1-BID.md).

On a tiny generated village, `train_d` with the default optimizer gives the same report (timing fields aside) and
the same checkpoint weights as the base commit's own `train_d`. With `optimizer="muon"` it trains with MuonAdamW,
says so in the report and the checkpoint, and resumes as Muon.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import torch

from premonition import train as ptrain
from premonition.muon import MuonAdamW
from tests.test_premonition_steals_identity import base_modules

TIMING = {"seconds", "tokens_per_s", "padded_tokens_per_s", "build_seconds"}     # wall-clock keys, by exact name


def strip(value):
    """The report without wall-clock fields (and without the checkpoint's absolute path)."""
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if k not in TIMING and k != "checkpoint"}
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
        self.assertEqual(sorted(a), sorted(b))
        self.assertEqual(list(a["model"]), list(b["model"]))
        for name, tensor in a["model"].items():
            self.assertTrue(torch.equal(tensor, b["model"][name]), name)
        self.assertEqual(repr(a["optimizer"]), repr(b["optimizer"]))                    # AdamW moments, steps
        self.assertEqual(repr(a.get("trainer")), repr(b.get("trainer")))                # step, flops, generator
        self.assertEqual(json.loads((self.root / "ckpt" / "new" / "config.json").read_text()),
                         json.loads((self.root / "ckpt" / "old" / "config.json").read_text()))

    def test_muon_trains_reports_and_resumes(self) -> None:
        built = []
        original = ptrain.MiniTrainer.__init__

        def spy(trainer, *args, **kwargs):
            original(trainer, *args, **kwargs)
            built.append(trainer)

        ptrain.MiniTrainer.__init__ = spy
        try:
            report = self.train(ptrain, "muon", optimizer="muon")
            default = self.train(ptrain, "adamw-again")
        finally:
            ptrain.MiniTrainer.__init__ = original
        self.assertIsInstance(built[0].optimizer, MuonAdamW)                     # the live run used Muon
        self.assertTrue(any(g["muon"] for g in built[0].optimizer.param_groups))
        self.assertEqual(report["optimizer"], "muon")
        self.assertEqual(report["status"], "completed")
        self.assertNotEqual(strip(report)["history"], strip(default)["history"])    # and trained differently
        again = ptrain.resume_trainer(self.root / "ckpt" / "muon")
        self.assertIsInstance(again.optimizer, MuonAdamW)
        state = again.optimizer.state_dict()
        self.assertTrue(any(s for part in state["parts"] for s in part["state"].values()))   # momentum restored
        weights = [p for p in again.model.parameters() if p.requires_grad]
        before = [p.detach().clone() for p in weights]
        for p in weights:
            p.grad = torch.ones_like(p)
        again.optimizer.step()                                                   # the restored state takes a step
        self.assertTrue(all(torch.isfinite(p).all() for p in weights))
        self.assertTrue(any(not torch.equal(p, b) for p, b in zip(weights, before)))
        with self.assertRaises(ValueError):
            self.train(ptrain, "bad", optimizer="Muon")


if __name__ == "__main__":
    unittest.main()
