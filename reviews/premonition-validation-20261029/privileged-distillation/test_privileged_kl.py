import unittest

import torch

from privileged_kl import Limits, answer_kl


class AnswerKLTests(unittest.TestCase):
    def fixture(self):
        # Different prefix lengths, identical answer [2, 3].
        return dict(
            teacher_logits=torch.zeros(1, 5, 4, dtype=torch.float64, requires_grad=True),
            student_logits=torch.zeros(1, 4, 4, dtype=torch.float64, requires_grad=True),
            teacher_ids=torch.tensor([[0, 1, 0, 2, 3]]),
            student_ids=torch.tensor([[1, 0, 2, 3]]),
            teacher_mask=torch.ones(1, 5, dtype=torch.bool),
            student_mask=torch.ones(1, 4, dtype=torch.bool),
            teacher_prefix_lengths=torch.tensor([3]),
            student_prefix_lengths=torch.tensor([2]),
            answer_lengths=torch.tensor([2]),
            teacher_vocab_id="toy-vocabulary-pinned-sha",
            student_vocab_id="toy-vocabulary-pinned-sha",
        )

    def test_equality_is_zero_and_teacher_has_no_grad(self):
        kw = self.fixture()
        loss = answer_kl(**kw)
        self.assertEqual(float(loss.detach()), 0.0)
        loss.backward()
        self.assertIsNone(kw["teacher_logits"].grad)
        self.assertTrue(torch.equal(kw["student_logits"].grad,
                                    torch.zeros_like(kw["student_logits"])))

    def test_gradient_moves_student_toward_teacher_distribution(self):
        kw = self.fixture()
        with torch.no_grad():
            kw["teacher_logits"][0, 2:4, 2] = 3.0
        loss = answer_kl(**kw)
        loss.backward()
        expected = (torch.full((4,), .25, dtype=torch.float64) -
                    torch.softmax(torch.tensor([0., 0., 3., 0.], dtype=torch.float64), -1)) / 2
        torch.testing.assert_close(kw["student_logits"].grad[0, 1], expected)
        self.assertLess(float(kw["student_logits"].grad[0, 1, 2]), 0)
        self.assertIsNone(kw["teacher_logits"].grad)
        # A tiny gradient step lowers the same objective.
        before = float(loss.detach())
        with torch.no_grad():
            kw["student_logits"].sub_(.1 * kw["student_logits"].grad)
        self.assertLess(float(answer_kl(**kw).detach()), before)

    def test_first_answer_uses_last_prefix_logit(self):
        kw = self.fixture()
        kw["answer_lengths"] = torch.tensor([1])
        with torch.no_grad():
            kw["teacher_logits"][0, 2, 2] = 4.0
            # Wrong +1 alignment would compare identical uniform positions.
        loss = answer_kl(**kw)
        target = torch.log_softmax(torch.tensor([0., 0., 4., 0.], dtype=torch.float64), -1)
        expected = (target.exp() * (target - torch.log(torch.tensor(.25)))).sum()
        torch.testing.assert_close(loss, expected)
        loss.backward()
        self.assertGreater(float(kw["student_logits"].grad[0, 1].abs().sum()), 0)
        self.assertEqual(float(kw["student_logits"].grad[0, 2:].abs().sum()), 0)

    def test_unrelated_prefix_and_padding_do_not_change_loss_or_gradients(self):
        kw = self.fixture()
        with torch.no_grad():
            kw["teacher_logits"][0, 2:4, 2] = 2.0
        baseline = answer_kl(**kw).detach()
        # Add a valid prompt token, 2 left pads and 3 right pads to each side.
        for side in ["teacher", "student"]:
            logits, ids = kw[side + "_logits"], kw[side + "_ids"]
            prefix = int(kw[side + "_prefix_lengths"][0])
            extra = torch.full((1, 3, 4), 99., dtype=torch.float64)
            suffix = torch.full((1, 3, 4), -77., dtype=torch.float64)
            kw[side + "_logits"] = torch.cat([extra, logits.detach(), suffix], 1).requires_grad_()
            kw[side + "_ids"] = torch.cat([torch.tensor([[0, 0, 1]]), ids, torch.zeros(1, 3, dtype=torch.long)], 1)
            kw[side + "_mask"] = torch.tensor([[False, False, True] + [True] * ids.shape[1] + [False] * 3])
            kw[side + "_prefix_lengths"] = torch.tensor([prefix + 1])
        loss = answer_kl(**kw)
        torch.testing.assert_close(loss, baseline)
        loss.backward()
        grad = kw["student_logits"].grad
        self.assertEqual(float(grad[:, :4].abs().sum()), 0)
        self.assertEqual(float(grad[:, 6:].abs().sum()), 0)
        self.assertIsNone(kw["teacher_logits"].grad)

    def test_batch_normalizes_valid_answer_tokens_not_examples_or_padding(self):
        kw = self.fixture()
        for side in ["teacher", "student"]:
            for field in ["logits", "ids", "mask", "prefix_lengths"]:
                key = side + "_" + field
                x = kw[key]
                kw[key] = torch.cat([x.detach(), x.detach()], 0)
        kw["student_logits"].requires_grad_()
        kw["answer_lengths"] = torch.tensor([1, 2])
        with torch.no_grad():
            kw["teacher_logits"][0, 2, 2] = 3
        target = torch.log_softmax(torch.tensor([0., 0., 3., 0.], dtype=torch.float64), -1)
        expected = (target.exp() * (target - torch.log(torch.tensor(.25)))).sum() / 3
        torch.testing.assert_close(answer_kl(**kw), expected)

    def test_sampled_answer_ids_do_not_backpropagate_into_sampling_policy(self):
        kw = self.fixture()
        sampling_policy = torch.zeros(4, dtype=torch.float64, requires_grad=True)
        with torch.no_grad():
            # This is a token-ID sample, not a differentiable sampling estimator.
            answer = torch.multinomial(sampling_policy.softmax(-1), 2, replacement=True).detach()
        kw["teacher_ids"][0, 3:] = answer
        kw["student_ids"][0, 2:] = answer
        answer_kl(**kw).backward()
        self.assertIsNone(sampling_policy.grad)

    def test_mismatching_answer_ids_and_vocab_are_rejected(self):
        for kind in ["answer", "vocab_dimension", "vocab_identity"]:
            with self.subTest(kind=kind):
                kw = self.fixture()
                if kind == "answer": kw["teacher_ids"][0, 3] = 1
                elif kind == "vocab_dimension": kw["teacher_logits"] = torch.zeros(1, 5, 5)
                else: kw["teacher_vocab_id"] = "different-token-mapping"
                with self.assertRaises(ValueError): answer_kl(**kw)

    def test_empty_nonfinite_bounds_and_oversize_are_rejected(self):
        for kind in ["empty_answer", "zero_prefix", "overflow", "nan", "inf", "interior_padding", "oversized", "bad_id"]:
            with self.subTest(kind=kind):
                kw = self.fixture()
                if kind == "empty_answer": kw["answer_lengths"] = torch.tensor([0])
                elif kind == "zero_prefix": kw["student_prefix_lengths"] = torch.tensor([0])
                elif kind == "overflow": kw["answer_lengths"] = torch.tensor([3])
                elif kind in ["nan", "inf"]:
                    with torch.no_grad(): kw["teacher_logits"][0, 2, 0] = float(kind)
                elif kind == "interior_padding": kw["teacher_mask"][0, 1] = False
                elif kind == "oversized": kw["limits"] = Limits(max_total_bytes=32)
                else: kw["student_ids"][0, 1] = 9
                with self.assertRaises(ValueError): answer_kl(**kw)


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main(verbosity=2)
