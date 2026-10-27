"""CPU integrity checks for the additive memory-network baseline; no saved models."""
from dataclasses import replace
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_memnn as M
M.bootstrap()
import torch
import torch.nn.functional as F
from premonition import toy_ladder
from premonition.train import label_free
from premonition.flops import count_flops


class MemoryNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.inputs, cls.target = M.training_batch(random.Random(982431), visits=2)

    def model(self):
        torch.manual_seed(981111)
        return M.MemoryNetwork()

    def test_parameter_budget(self):
        self.assertEqual(self.model().parameters_count(), 79473)
        self.assertLess(abs(79473 / 79748 - 1), .005)

    def test_adapter_matches_frozen_training_stream(self):
        batch, _, _ = toy_ladder.make(toy_ladder.LadderSpec(), 2, random.Random(982431), training=True)
        batch = label_free(batch)
        encoded = M.from_batch(batch)
        for name in ("memory", "questions", "owner", "eligible"):
            self.assertTrue(torch.equal(getattr(encoded, name), getattr(self.inputs, name)), name)
        self.assertTrue(torch.equal(batch.answer[:, 0], self.target))
        self.assertFalse(batch.slices["heldout"].any())
        # Labels, oracle entity mentions, question IDs, names and depth are unused.
        poison = replace(batch, answer=torch.zeros_like(batch.answer),
                         gold_lines=torch.zeros_like(batch.gold_lines),
                         depth=torch.full_like(batch.depth, 99), slices=None,
                         line_ents=torch.full_like(batch.line_ents, 999), names=[], question_ids=[])
        other = M.from_batch(poison)
        for name in ("memory", "questions", "owner", "eligible"):
            self.assertTrue(torch.equal(getattr(encoded, name), getattr(other, name)))

    def test_accounting_matches_registered_counter(self):
        model = self.model()
        counted = count_flops(lambda: F.cross_entropy(model(self.inputs), self.target))
        self.assertEqual(counted, M.training_flops(self.inputs))

    def test_answer_gradient_reaches_memory_addressing(self):
        model = self.model()
        F.cross_entropy(model(self.inputs), self.target).backward()
        for module in (model.key, model.value, model.question, model.transition):
            self.assertGreater(float(module.weight.grad.abs().sum()), 0.)
        for table in (model.key, model.value, model.question):
            self.assertEqual(float(table.weight.grad[0].abs().sum()), 0.)

    def test_causal_mask_and_null(self):
        inputs = M.pack([[[3, 52, 8, 12, 7], [], [3, 53, 9, 13, 7]]],
                        [[4, 52, 8, 5]], [0], [1])
        model = self.model()
        logits, attention = model(inputs, trace=True)
        changed = replace(inputs, memory=inputs.memory.clone())
        changed.memory[0, 2] = torch.tensor([3, 59, 10, 24, 7])
        self.assertTrue(torch.equal(logits, model(changed)))
        self.assertEqual(float(attention[:, :, 1:3].detach().abs().sum()), 0.)
        empty = replace(inputs, eligible=torch.zeros_like(inputs.eligible))
        result, weights = model(empty, trace=True)
        self.assertTrue(torch.isfinite(result).all())
        self.assertTrue(torch.equal(weights[:, :, -1], torch.ones(1, 3)))

    def test_word_order_and_padding(self):
        model = self.model()
        x = torch.tensor([[3, 52, 11, 53, 7]])
        y = torch.tensor([[3, 53, 11, 52, 7]])
        self.assertFalse(torch.equal(model.encode(x, model.key), model.encode(y, model.key)))
        self.assertTrue(torch.equal(model.encode(x, model.key),
                                    model.encode(F.pad(x, (0, 4)), model.key)))

    def test_state_isolation(self):
        model = self.model().eval()
        full = model(self.inputs)
        for q, owner in enumerate(self.inputs.owner):
            one = M.Inputs(self.inputs.memory[owner:owner+1], self.inputs.questions[q:q+1],
                           torch.zeros(1, dtype=torch.long), self.inputs.eligible[q:q+1])
            self.assertTrue(torch.allclose(full[q:q+1], model(one), atol=1e-6, rtol=1e-5))
            self.assertEqual(int(full[q].argmax()), int(model(one).argmax()))

    def test_counterfactual_pairs_count_jointly(self):
        from premonition_memnn_compare import score_predictions
        a, gold_a = [[12,2], [13,2]], [[12,2], [13,2]]
        b, gold_b = [[14,2], [13,2]], [[14,2], [15,2]]
        self.assertEqual(score_predictions(a,gold_a,b,gold_b), [1,0])
        self.assertEqual(score_predictions(a,gold_a,b,gold_b,True), [0,0])
        self.assertEqual(score_predictions(a,gold_a,a,gold_a,True), [1,1])

    def test_seed_1101_two_successive_batches_match(self):
        direct_rng, frozen_rng = random.Random(1101), random.Random(1101)
        for _ in range(2):
            direct, target = M.training_batch(direct_rng, visits=16)
            batch, _, _ = toy_ladder.make(toy_ladder.LadderSpec(), 16, frozen_rng, training=True)
            batch = label_free(batch)
            frozen = M.from_batch(batch)
            for name in ("memory", "questions", "owner", "eligible"):
                self.assertTrue(torch.equal(getattr(direct,name), getattr(frozen,name)))
            self.assertTrue(torch.equal(target, batch.answer[:,0]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
