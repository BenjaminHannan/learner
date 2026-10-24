"""Breakdown evaluator on a tiny CPU data root and a toy D."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import torch

from generalize import evaluate, probes
from generalize.tests import toy

TOK = evaluate.DEFAULT_TOKENIZER


class Evaluator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.root, cls.probes = toy.build_root(base, train_shards=3, dev_shards=1, probe_visits=25, val_visits=25)
        cls.ckpt = toy.train_toy_d(cls.root, TOK, base / "D-only.pt", steps=4)
        cls.bridge_ckpt = toy.train_toy_d(cls.root, TOK, base / "D-bridge.pt", steps=1, bridge=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_eval(self, **kw):
        return evaluate.evaluate(self.ckpt, self.root, probes_root=self.probes, log=lambda s: None, **kw)

    def test_end_to_end_report(self):
        rep = self.run_eval(max_visits=10)
        self.assertEqual(list(rep["sets"]), ["dev", "validation", "P0", "Pname", "Pword", "Pstyle", "Pdepth", "Prule", "Pall"])
        for name, s in rep["sets"].items():
            self.assertGreater(s["questions"], 0)
            for dim in evaluate.DIMENSIONS:
                self.assertEqual(sum(c["n"] for c in s["breakdown"][dim].values()), s["questions"], (name, dim))
        self.assertTrue(set(rep["sets"]["Pdepth"]["breakdown"]["depth"]) - {"0", "1", "2", "3"})
        self.assertIn("True", rep["sets"]["Prule"]["breakdown"]["r8"])
        self.assertNotIn("True", rep["sets"]["P0"]["breakdown"]["r8"])
        self.assertEqual(set(rep["sets"]["Pstyle"]["breakdown"]["style_status"]), {"validation"})
        self.assertEqual(set(rep["sets"]["P0"]["breakdown"]["style_status"]), {"train"})
        self.assertNotIn("test", " ".join(rep["sets"]))
        md = evaluate.to_markdown(rep)
        self.assertIn("## By depth", md)
        json.dumps(rep, default=float)

    def test_accuracy_matches_validate(self):
        """Same batching and judge as premonition.train.validate (judge patched so accuracy is not a flat 0)."""
        from premonition import preprocess
        from premonition import data as pdata
        from learnlab.tokenizer import Tokenizer
        from premonition.train import validate
        tok, caches = toy.make_caches(self.root, TOK)
        model, _ = evaluate.load_d(self.ckpt)

        def fake_judge(answers, batch, **kw):
            ok = [sum(map(ord, qid)) % 3 == 0 for qid in batch.question_ids]
            return ok, ["x"] * len(ok)

        with mock.patch("premonition.train.judge", fake_judge):
            batches = [pdata.collate(caches["validation"], g) for g in
                       pdata.length_batches(caches["validation"].lengths.tolist(), 55_000, max_visits=48)]
            from learnlab import step1
            stops = sorted(step1.stop_ids(tok)[0])
            ref = validate(model, batches, tokenizer=tok, stop=stops)
            scores = evaluate.score_cache(model, caches["validation"], tok)
        acc = sum(s["correct"] for s in scores.values()) / len(scores)
        self.assertEqual(len(scores), ref["questions"])
        self.assertGreater(acc, 0)
        self.assertAlmostEqual(acc, ref["accuracy"])

    def test_extra_loops(self):
        tok, caches = toy.make_caches(self.root, TOK)
        model, _ = evaluate.load_d(self.ckpt)
        cache = caches["validation"]
        base = evaluate.score_cache(model, cache, tok, max_visits=5)
        zero = evaluate.score_cache(model, cache, tok, max_visits=5, extra_loops=0)
        self.assertEqual(base, zero)
        # a model that halts at once: HALT logit forced high
        with torch.no_grad():
            model.heads.halt.bias.fill_(50.0)
        quick = evaluate.score_cache(model, cache, tok, max_visits=5)
        slow = evaluate.score_cache(model, cache, tok, max_visits=5, extra_loops=3)
        self.assertTrue(all(v["loops"] == 1 for v in quick.values()))
        self.assertTrue(all(v["loops"] == 4 for v in slow.values()))
        capped = evaluate.score_cache(model, cache, tok, max_visits=5, extra_loops=50)
        self.assertTrue(all(v["loops"] == model.config.max_loops for v in capped.values()))

    def test_bridge_checkpoint_needs_b2(self):
        with self.assertRaises(SystemExit) as cm:
            evaluate.load_d(self.bridge_ckpt)
        self.assertIn("--b2", str(cm.exception))
        stub = types.SimpleNamespace(d=48)
        model, info = evaluate.load_d(self.bridge_ckpt, b2="fake-b2.pt", creative_loader=lambda p, dev: stub)
        self.assertEqual(info["kind"], "bridge")
        self.assertTrue(model.bridge_in is not None)
        self.assertEqual(evaluate.load_d(self.ckpt)[1]["kind"], "d-only")

    def test_not_a_d_checkpoint(self):
        bad = Path(self.tmp.name) / "bad.pt"
        torch.save({"weights": 1}, bad)
        with self.assertRaises(ValueError):
            evaluate.load_d(bad)

    def test_sealed_split_never_found(self):
        (self.root / "test").mkdir(exist_ok=True)
        (self.root / "test" / "shard-00000.txt").write_text("x\n")
        (self.root / "test" / "manifest.json").write_text('{"split": "test"}')
        try:
            self.assertNotIn("test", evaluate.discover(self.root, self.probes))
            with self.assertRaises(SystemExit):
                self.run_eval(sets=["test"])
        finally:
            for p in (self.root / "test").iterdir():
                p.unlink()
            (self.root / "test").rmdir()

    def test_attribution(self):
        mk = lambda a: {"accuracy": a}
        sets = {"P0": mk(0.8), "validation": mk(0.4), "Pname": mk(0.78), "Pword": mk(0.75), "Pstyle": mk(0.79),
                "Pdepth": mk(0.55), "Prule": mk(0.7), "Pall": mk(0.41)}
        att = evaluate.attribution(sets)
        self.assertAlmostEqual(att["G"], 0.4)
        self.assertEqual(att["bottlenecks"], ["Pdepth"])           # drop 0.25 >= G/2 = 0.2
        self.assertTrue(att["drops"]["Prule"]["reaches_quarter"] is True)
        flat = dict(sets, Pdepth=mk(0.75), Prule=mk(0.75), Pword=mk(0.75))
        self.assertIn("WRONG-IF", evaluate.attribution(flat)["verdict"])


if __name__ == "__main__":
    unittest.main()
