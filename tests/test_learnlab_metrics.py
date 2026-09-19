"""Step 0 metrics: exact tests, forgetting variants, validation and learning speed."""
from __future__ import annotations

import math
import random
import unittest

from learnlab import policy
from learnlab.metrics import (
    ContinualMatrix,
    binomial_greater,
    bootstrap_ci,
    expected_calibration_error,
    mcnemar_greater,
    paired_difference_ci,
    paired_greater_pvalue,
    paired_permutation_greater,
    recall_at_k,
    steps_to_threshold,
    wilson_interval,
)


class PolicyTests(unittest.TestCase):
    def test_defaults_are_recorded(self):
        self.assertEqual(policy.ALPHA, 0.01)
        self.assertEqual(policy.MIN_ITEMS, 100)
        self.assertGreater(policy.MIN_EFFECT, 0.0)
        self.assertEqual(policy.LESION_GAIN_FRACTION, 0.5)
        self.assertEqual(policy.LEAK_MIN_ITEMS, 100)
        self.assertEqual(policy.BUDGET_TOLERANCE, 0.05)


class ExactTestTests(unittest.TestCase):
    def test_binomial_known_values(self):
        self.assertEqual(binomial_greater(8, 10, 0.5), 56 / 1024)
        self.assertEqual(binomial_greater(3, 3, 0.5), 0.125)
        self.assertEqual(binomial_greater(0, 7, 0.3), 1.0)
        self.assertAlmostEqual(binomial_greater(2, 5, 0.2), 1 - 0.8**5 - 5 * 0.2 * 0.8**4, places=12)
        self.assertAlmostEqual(binomial_greater(1, 10, 0.1), 1 - 0.9**10, places=12)
        # Large n stays finite and sensible.
        self.assertLess(binomial_greater(700, 1000, 0.5), 1e-30)
        half = 0.5 + 0.5 * math.comb(1000, 500) / 2**1000
        self.assertAlmostEqual(binomial_greater(500, 1000, 0.5), half, places=12)

    def test_binomial_rejects_bad_input(self):
        bad = [(-1, 5, 0.5), (6, 5, 0.5), (1, -1, 0.5), (1, 5, 1.5), (1, 5, float("nan")), (1.0, 5, 0.5)]
        for args in bad:
            with self.assertRaises((ValueError, TypeError), msg=args):
                binomial_greater(*args)

    def test_mcnemar_three_of_three_is_one_eighth(self):
        a = [1, 1, 1] + [1, 0] * 10
        b = [0, 0, 0] + [1, 0] * 10
        self.assertEqual(mcnemar_greater(a, b), 0.125)
        self.assertEqual(mcnemar_greater([1, 1, 1, 1], [0, 0, 0, 0]), 0.0625)
        # 5 wins, 1 loss: P(X >= 5 | 6) = 7/64.
        self.assertEqual(mcnemar_greater([1] * 5 + [0], [0] * 5 + [1]), 7 / 64)
        # No discordant pairs: no evidence.
        self.assertEqual(mcnemar_greater([1, 0, 1], [1, 0, 1]), 1.0)

    def test_mcnemar_rejects_non_binary_and_unpaired(self):
        with self.assertRaises(ValueError):
            mcnemar_greater([0.5, 1.0], [0.0, 1.0])
        with self.assertRaises(ValueError):
            mcnemar_greater([1, 0], [1])

    def test_four_of_three_hundred_discordant_is_not_significant(self):
        rng = random.Random(0)
        base = [1.0 if rng.random() < 0.6 else 0.0 for _ in range(300)]
        full = list(base)
        for i in [i for i, value in enumerate(base) if value == 0.0][:4]:
            full[i] = 1.0
        self.assertEqual(paired_greater_pvalue(full, base), 0.0625)
        self.assertGreater(paired_greater_pvalue(full, base, margin=policy.MIN_EFFECT), 0.5)

    def test_permutation_exact_small_n(self):
        # All four positive: only the identity flip reaches the observed sum.
        self.assertEqual(paired_permutation_greater([1.0, 1.0, 1.0, 1.0]), 1 / 16)
        # Brute-force check against full enumeration of 2^n sign flips.
        diffs = [0.3, -0.1, 0.25, 0.3, 0.05, -0.2, 0.4]
        observed = sum(diffs)
        count = 0
        for mask in range(2 ** len(diffs)):
            total = sum(d if mask >> i & 1 else -d for i, d in enumerate(diffs))
            count += total >= observed - 1e-12
        self.assertAlmostEqual(paired_permutation_greater(diffs), count / 2 ** len(diffs), places=12)
        self.assertEqual(paired_permutation_greater([0.0, 0.0]), 1.0)

    def test_permutation_monte_carlo_is_seeded_and_calibrated(self):
        rng = random.Random(1)
        diffs = [rng.gauss(0.0, 1.0) for _ in range(200)]
        first = paired_permutation_greater(diffs, samples=2000, seed=3)
        self.assertEqual(first, paired_permutation_greater(diffs, samples=2000, seed=3))
        self.assertGreater(first, 0.0)
        shifted = [d + 1.0 for d in diffs]
        self.assertLess(paired_permutation_greater(shifted, samples=2000), 0.001)

    def test_permutation_and_bootstrap_reject_zero_samples(self):
        with self.assertRaises(ValueError):
            paired_permutation_greater([0.1] * 30, samples=0)
        with self.assertRaises(ValueError):
            paired_permutation_greater([])
        with self.assertRaises(ValueError):
            bootstrap_ci([0.0, 1.0], samples=0)
        with self.assertRaises(ValueError):
            bootstrap_ci([0.0, 1.0], alpha=0.0)
        with self.assertRaises(ValueError):
            bootstrap_ci([0.0, 1.0], alpha=1.0)
        with self.assertRaises(ValueError):
            paired_difference_ci([1.0], [0.0, 1.0])

    def test_margin_uses_permutation_test(self):
        a = [0.501] * 100
        b = [0.5] * 100
        self.assertEqual(paired_greater_pvalue(a, b, margin=0.03), 1.0)
        self.assertLess(paired_greater_pvalue([0.9] * 100, b, margin=0.03), 1e-20)

    def test_wilson_interval_known_values(self):
        low, high = wilson_interval(0, 10)
        self.assertEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.27753, places=4)
        low, high = wilson_interval(5, 10)
        self.assertAlmostEqual(low, 0.23659, places=4)
        self.assertAlmostEqual(high, 0.76341, places=4)
        self.assertEqual(wilson_interval(10, 10)[1], 1.0)
        with self.assertRaises(ValueError):
            wilson_interval(3, 0)
        with self.assertRaises(ValueError):
            wilson_interval(3, 10, alpha=0.0)


class ContinualMatrixTests(unittest.TestCase):
    @staticmethod
    def _matrix(rows):
        matrix = ContinualMatrix(len(rows))
        for stage, row in enumerate(rows):
            for task, score in enumerate(row):
                matrix.record(stage, task, score)
        return matrix

    def test_chaudhry_and_post_acquisition_differ_on_crafted_matrix(self):
        # Task 1 scored 0.9 before it was trained (forward transfer), then fell to 0.6 and 0.5.
        matrix = self._matrix([[0.8, 0.9, 0.1], [0.8, 0.6, 0.1], [0.8, 0.5, 0.9]])
        self.assertAlmostEqual(matrix.forgetting(), 0.05)
        self.assertAlmostEqual(matrix.forgetting("post_acquisition"), 0.05)
        self.assertAlmostEqual(matrix.forgetting("chaudhry"), 0.20)
        report = matrix.forgetting_report()
        self.assertAlmostEqual(report["post_acquisition"], 0.05)
        self.assertAlmostEqual(report["chaudhry"], 0.20)
        self.assertEqual(len(report["chaudhry_per_task"]), 2)
        self.assertAlmostEqual(report["backward_transfer"], ((0.8 - 0.8) + (0.5 - 0.6)) / 2)
        with self.assertRaises(ValueError):
            matrix.forgetting("best_ever")

    def test_review2_matrix(self):
        matrix = self._matrix([[0.2, 0.9, 0.1], [0.1, 0.6, 0.2], [0.1, 0.5, 0.9]])
        self.assertAlmostEqual(matrix.forgetting("post_acquisition"), 0.10)
        self.assertAlmostEqual(matrix.forgetting("chaudhry"), 0.25)
        self.assertAlmostEqual(matrix.forward_transfer(reference=[0.0, 0.0, 0.0]), (0.9 + 0.2) / 2)

    def test_indices_are_validated(self):
        matrix = ContinualMatrix(2)
        for stage, task in [(-1, 0), (0, -1), (2, 0), (0, 2)]:
            with self.assertRaises(IndexError):
                matrix.record(stage, task, 0.5)
        with self.assertRaises(TypeError):
            matrix.record(0.0, 0, 0.5)
        with self.assertRaises(TypeError):
            matrix.record(True, 0, 0.5)
        with self.assertRaises(ValueError):
            matrix.record(0, 0, float("nan"))
        self.assertEqual(matrix.scores, [[None, None], [None, None]])
        with self.assertRaises(ValueError):
            ContinualMatrix(0)
        with self.assertRaises(ValueError):
            matrix.forward_transfer([0.1])


class LearningSpeedAndOtherMetricTests(unittest.TestCase):
    def test_unsorted_curve_is_sorted(self):
        self.assertEqual(steps_to_threshold([(30, 0.95), (10, 0.2), (20, 0.9)], 0.9), 20)

    def test_spiky_curve_needs_sustain(self):
        curve = [(10, 0.2), (20, 0.91), (30, 0.4), (40, 0.5), (90, 0.92), (100, 0.93)]
        self.assertEqual(steps_to_threshold(curve, 0.9), 20)
        self.assertEqual(steps_to_threshold(curve, 0.9, sustain=2), 90)
        self.assertIsNone(steps_to_threshold(curve, 0.9, sustain=3))
        self.assertIsNone(steps_to_threshold(curve[:5], 0.9, sustain=2))

    def test_steps_to_threshold_validation(self):
        with self.assertRaises(ValueError):
            steps_to_threshold([(10, 0.5), (10, 0.9)], 0.9)
        with self.assertRaises(ValueError):
            steps_to_threshold([(10, 0.5)], 0.9, sustain=0)
        with self.assertRaises(ValueError):
            steps_to_threshold([(10, float("nan"))], 0.9)

    def test_ece_rejects_zero_bins_and_nan(self):
        with self.assertRaises(ValueError):
            expected_calibration_error([0.9, 0.1], [True, False], bins=0)
        with self.assertRaises(ValueError):
            expected_calibration_error([float("nan")], [True])
        self.assertAlmostEqual(expected_calibration_error([1.0] * 4, [True] * 4), 0.0)
        self.assertAlmostEqual(expected_calibration_error([0.9] * 10, [True] * 5 + [False] * 5), 0.4)

    def test_recall_at_k(self):
        self.assertEqual(recall_at_k([["a", "b"], ["c", "d"]], ["b", "x"], 2), 0.5)
        with self.assertRaises(ValueError):
            recall_at_k([["a"]], ["a"], 0)


if __name__ == "__main__":
    unittest.main()
