"""H1 (milestone 3): verified ladder triplets and the paired JS / changed-margin objective. CPU; no training."""
from __future__ import annotations

from collections import Counter
from dataclasses import fields
import math
import random
import unittest

import torch
import torch.nn.functional as F

from premonition import ladder_triplets, toy_ladder
from premonition.batch import VisitBatch
from premonition.paired_objectives import H1Config, h1_terms, js_divergence, log_odds_change, triplet_metrics
from premonition.train import label_free

SPEC = toy_ladder.LadderSpec()
ON = H1Config(enabled=True, js_weight=1.0, margin_weight=1.0, margin=1.0)


def reference_js(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    p, q = p.double(), q.double()
    m = (p + q) / 2
    kl = lambda a, b: torch.where(a > 0, a * (a.log() - b.log()), torch.zeros_like(a)).sum(-1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


class LossTest(unittest.TestCase):
    def test_js_matches_float64_reference_and_is_bounded(self):
        torch.manual_seed(0)
        x, y = torch.randn(64, 20) * 3, torch.randn(64, 20) * 3
        got = js_divergence(F.log_softmax(x, -1), F.log_softmax(y, -1))
        want = reference_js(F.softmax(x, -1), F.softmax(y, -1))
        self.assertTrue(torch.allclose(got.double(), want, atol=1e-6))
        self.assertTrue(bool((got >= 0).all()) and bool((got <= math.log(2) + 1e-6).all()))
        self.assertTrue(torch.allclose(got, js_divergence(F.log_softmax(y, -1), F.log_softmax(x, -1))))

    def test_js_zero_with_zero_gradient_at_agreement(self):
        logits = torch.randn(3, 10, requires_grad=True)
        other = logits.detach().clone().requires_grad_(True)
        js = js_divergence(F.log_softmax(logits, -1), F.log_softmax(other, -1)).sum()
        js.backward()
        self.assertLess(float(js.detach()), 1e-7)
        self.assertLess(float(logits.grad.abs().max()), 1e-6)

    def test_extreme_logits_stay_finite(self):
        for scale in (1e4, 1e30):
            x = torch.tensor([[scale, -scale, 0.0, 1.0], [-scale, scale, 2.0, 0.0]], requires_grad=True)
            u = torch.tensor([[-scale, scale, 0.0, 1.0], [scale, -scale, 0.0, 0.0]], requires_grad=True)
            v = torch.tensor([[scale, scale, 0.0, -scale], [0.0, 0.0, scale, -scale]], requires_grad=True)
            out = h1_terms(x, u, v, torch.tensor([0, 1]), torch.tensor([1, 2]), ON)
            out["loss"].backward()
            self.assertTrue(bool(torch.isfinite(out["loss"])))
            for t in (x, u, v):
                self.assertTrue(bool(torch.isfinite(t.grad).all()), scale)
        with self.assertRaises(ValueError):
            h1_terms(torch.tensor([[float("inf"), 0.0]]), torch.zeros(1, 2), torch.zeros(1, 2), torch.tensor([0]),
                     torch.tensor([1]), ON)

    def test_log_odds_change_value(self):
        lx = F.log_softmax(torch.tensor([[2.0, 0.5, -1.0]]), -1)
        lv = F.log_softmax(torch.tensor([[0.0, 1.5, 0.0]]), -1)
        delta = log_odds_change(lx, lv, torch.tensor([0]), torch.tensor([1]))
        self.assertAlmostEqual(float(delta), (2.0 - 0.5) - (0.0 - 1.5), places=5)

    def test_margin_gradient_direction_and_satisfied_margin(self):
        a, b = torch.tensor([0]), torch.tensor([1])
        x = torch.zeros(1, 4, requires_grad=True)
        u = torch.zeros(1, 4, requires_grad=True)
        v = torch.zeros(1, 4, requires_grad=True)
        only_margin = H1Config(enabled=True, js_weight=0.0, margin_weight=1.0, margin=1.0)
        h1_terms(x, u, v, a, b, only_margin)["loss"].backward()
        # descending the loss raises log-odds(a:b) on x and lowers it on v
        self.assertLess(float(x.grad[0, 0]), 0.0)
        self.assertGreater(float(x.grad[0, 1]), 0.0)
        self.assertGreater(float(v.grad[0, 0]), 0.0)
        self.assertLess(float(v.grad[0, 1]), 0.0)
        self.assertEqual(float(u.grad.abs().max()), 0.0)
        x2 = torch.tensor([[5.0, 0.0, 0.0, 0.0]], requires_grad=True)
        v2 = torch.tensor([[0.0, 5.0, 0.0, 0.0]], requires_grad=True)
        out = h1_terms(x2, torch.zeros(1, 4), v2, a, b, only_margin)
        out["loss"].backward()
        self.assertEqual(float(out["loss"]), 0.0)
        self.assertEqual(float(x2.grad.abs().max()) + float(v2.grad.abs().max()), 0.0)

    def test_mask_removes_triplets_and_disabled_adds_nothing(self):
        torch.manual_seed(1)
        x, u, v = (torch.randn(3, 6, requires_grad=True) for _ in range(3))
        a, b = torch.tensor([0, 1, 2]), torch.tensor([3, 4, 5])
        h1_terms(x, u, v, a, b, ON, mask=torch.tensor([True, False, True]))["loss"].backward()
        for t in (x, u, v):
            self.assertEqual(float(t.grad[1].abs().max()), 0.0)
            self.assertGreater(float(t.grad[[0, 2]].abs().max()), 0.0)
        for t in (x, u, v):
            t.grad = None
        out = h1_terms(x, u, v, a, b, H1Config())
        self.assertEqual(float(out["loss"]), 0.0)
        out["loss"].backward()
        self.assertEqual(max(0.0 if t.grad is None else float(t.grad.abs().max()) for t in (x, u, v)), 0.0)
        with self.assertRaises(ValueError):
            h1_terms(x, u, v, a, a, ON)

    def test_grouped_ce_parity_when_h1_is_off(self):
        torch.manual_seed(2)
        logits = torch.randn(9, 7, requires_grad=True)
        targets = torch.randint(7, (9,))
        ce = F.cross_entropy(logits, targets)
        ce.backward()
        plain = logits.grad.clone()
        logits.grad = None
        idx = torch.tensor([0, 1, 2])
        total = F.cross_entropy(logits, targets) + h1_terms(logits[idx], logits[idx + 3], logits[idx + 6],
                                                            targets[idx], (targets[idx] + 1) % 7, H1Config())["loss"]
        total.backward()
        self.assertTrue(torch.equal(plain, logits.grad))

    def test_constant_answers_fail_changed_pair_metrics(self):
        a, b = torch.tensor([10, 11, 12]), torch.tensor([13, 14, 15])
        constant = triplet_metrics(a, a, a, a, b)
        self.assertEqual(int(constant["relevant_both_correct"].sum()), 0)
        self.assertEqual(int(constant["invariant_both_correct"].sum()), 3)
        perfect = triplet_metrics(a, a, b, a, b)
        self.assertEqual(int(perfect["all_three_correct"].sum()), 3)


class TripletTest(unittest.TestCase):
    def triplets(self, n=60, seed=5, training=True):
        rng, edit = random.Random(seed), random.Random(seed + 1)
        return [ladder_triplets.make_triplet(SPEC, rng, edit, training=training) for _ in range(n)]

    def test_roles_follow_an_independent_oracle(self):
        for t in self.triplets(training=False):
            q = t.x[t.q_line]
            for lines, world in zip((t.x, t.u, t.v), t.worlds):
                self.assertEqual(ladder_triplets.oracle_answer(world, lines[t.q_line]),
                                 t.answer_a if lines is not t.v else t.answer_b)
            self.assertNotEqual(t.answer_a, t.answer_b)
            self.assertEqual(q.hops, 1)

    def test_swaps_keep_the_word_inventory_and_edits_are_minimal(self):
        inventory = lambda lines: Counter(tok for line in lines if not line.question for tok in line.tokens)
        for t in self.triplets():
            self.assertEqual(inventory(t.x), inventory(t.v))
            if t.kind_u == "decoy_swap":
                self.assertEqual(inventory(t.x), inventory(t.u))
            changed = sum(p.tokens != q.tokens for p, q in zip(t.x, t.u) if not p.question)
            self.assertEqual(changed, 2 if t.kind_u == "decoy_swap" else 1)
            self.assertEqual(sum(p.tokens != q.tokens for p, q in zip(t.x, t.v) if not p.question), 2)

    def test_kinds_are_mixed_and_training_triplets_hold_out_the_composition(self):
        ts = self.triplets(n=80)
        self.assertEqual(set(t.kind_u for t in ts), set(ladder_triplets.IRRELEVANT_KINDS))
        self.assertEqual(set(t.kind_v for t in ts), set(ladder_triplets.RELEVANT_KINDS))
        for t in ts:
            for lines in (t.x, t.u, t.v):
                self.assertFalse(any(l.question and l.hops == 2 and l.relation == SPEC.heldout_relation
                                     for l in lines))

    def test_verify_rejects_a_corrupted_triplet(self):
        t = self.triplets(n=1)[0]
        t.answer_b = t.answer_a
        with self.assertRaises(AssertionError):
            ladder_triplets.verify(SPEC, t)

    def test_batch_carries_no_role_metadata_and_indices_survive_label_free(self):
        stream = ladder_triplets.triplet_batches(SPEC, 11, per_batch=6, training=True)
        (batch, supplied, hops), meta = next(stream)
        self.assertEqual({f.name for f in fields(VisitBatch)}, {f.name for f in fields(batch)})
        self.assertFalse(any(word in qid for qid in batch.question_ids for word in ("x", "u", "v", "role")))
        self.assertNotEqual(meta.rows[:, 0].tolist(), list(range(6)))          # x visits are not simply first
        clean = label_free(batch)
        self.assertTrue(torch.equal(clean.answer[meta.x_q, 0], meta.a))
        self.assertTrue(torch.equal(clean.answer[meta.u_q, 0], meta.a))
        self.assertTrue(torch.equal(clean.answer[meta.v_q, 0], meta.b))
        for q in torch.cat([meta.x_q, meta.u_q, meta.v_q]).tolist():
            v, start, end = int(clean.q_visit[q]), int(clean.q_span[q, 0]), int(clean.q_span[q, 1])
            self.assertEqual(int(clean.tokens[v, end - 1]), toy_ladder.ANSWER)  # the answer is not in the input
            self.assertNotIn(int(clean.answer[q, 0]), clean.tokens[v, start:end].tolist())
        order = ladder_triplets.shared_order(meta, len(hops), torch.Generator().manual_seed(0))
        for t in range(6):
            rx, ru, rv = meta.rows[t].tolist()
            self.assertTrue(torch.equal(order[rx * 4:rx * 4 + 4], order[ru * 4:ru * 4 + 4]))
            self.assertTrue(torch.equal(order[rx * 4:rx * 4 + 4], order[rv * 4:rv * 4 + 4]))


if __name__ == "__main__":
    unittest.main()
