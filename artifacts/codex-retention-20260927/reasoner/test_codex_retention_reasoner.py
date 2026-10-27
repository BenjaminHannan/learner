"""Tests for full-snapshot isolation and caller-identity routing."""
import random
import sys
import tempfile
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_retention_reasoner as C


class RetentionTests(unittest.TestCase):
    def test_fresh_heldout_panels_and_identity(self):
        panels = C.heldout(92029)
        self.assertEqual({name: len(items) for name, items in panels.items()},
                         {"grids5": 200, "sums4": 200})
        self.assertEqual({name: {it.env for it in items} for name, items in panels.items()},
                         {"grids5": {"grids"}, "sums4": {"sums"}})

    def test_duplicate_replacement_keeps_batch_shape_and_active_stop_rule(self):
        rng = random.Random(9)
        pool = {4: [C.E.make_latin_base(rng, 4)]}
        item = C.E.latin_item(rng, *pool[4][0])
        replacement = C.replacement_at_same_size(rng, item, pool)
        self.assertEqual(replacement.size, item.size)
        self.assertEqual(len(replacement.tokens), len(item.tokens))
        summed = C.E.make_sum(rng, 4)
        self.assertEqual(C.replacement_at_same_size(rng, summed, pool).size, 4)
        self.assertIs(C.R.evaluate, C.A2.evaluate)

    def test_complete_snapshot_stays_bit_identical_after_new_skill_step(self):
        torch.set_num_threads(2)
        torch.manual_seed(3)
        grid = C.new_net("cpu")
        items = [C.E.make_sum(random.Random(i), 3) for i in range(4)]
        before = C.prediction_signature(grid, items, "cpu")
        old_hash = C.state_hash(grid)
        with tempfile.TemporaryDirectory() as d:
            tmp_path = Path(d)
            C.save_checkpoint(tmp_path / "snapshot-grids.pt", grid, "grids", 1, 3)
            new = C.load_checkpoint(tmp_path / "snapshot-grids.pt", "cpu")
            opt = torch.optim.AdamW(new.parameters(), lr=1e-3)
            sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda _: 1.0)
            C.train_step(new, opt, sch, items, random.Random(2), "cpu")
            router = C.SnapshotRouter(tmp_path, "cpu")
            old = router.model_for("grids")
            self.assertEqual(C.state_hash(old), old_hash)
            self.assertTrue(C.equal_signature(before, C.prediction_signature(old, items, "cpu")))
            self.assertNotEqual(C.state_hash(new), old_hash)
            self.assertTrue(all(not p.requires_grad for p in old.parameters()))
            with self.assertRaises(ValueError):
                router.model_for("unknown")

    def test_restart_and_alternating_requests(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            grid = C.new_net("cpu")
            sums = C.new_net("cpu")
            C.save_checkpoint(root / "snapshot-grids.pt", grid, "grids", 1, 3)
            C.save_checkpoint(root / "snapshot-sums.pt", sums, "sums", 1, 3)
            grid_items = [C.E.latin_item(random.Random(5), *C.E.make_latin_base(random.Random(6), 4))]
            sum_items = [C.E.make_sum(random.Random(7), 4)]
            requests = (grid_items, sum_items, grid_items)
            first = C.SnapshotRouter(root, "cpu")
            outputs = [first.predict(items) for items in requests]
            scores = (first.score(grid_items), first.score(sum_items), first.score(grid_items))
            del first
            restarted = C.SnapshotRouter(root, "cpu")
            outputs_after = [restarted.predict(items) for items in requests]
            scores_after = (restarted.score(grid_items), restarted.score(sum_items), restarted.score(grid_items))
            self.assertTrue(all(C.equal_signature(a, b) for a, b in zip(outputs, outputs_after)))
            self.assertEqual(scores, scores_after)
            self.assertTrue(C.equal_signature(outputs_after[0], outputs_after[2]))
            with self.assertRaises(ValueError):
                restarted.predict(grid_items + sum_items)


if __name__ == "__main__":
    unittest.main()
