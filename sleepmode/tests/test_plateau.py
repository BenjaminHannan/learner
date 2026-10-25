import math
import unittest

from sleepmode.plateau import Plateau


class PlateauTest(unittest.TestCase):
    def feed(self, p, curve, n, dh=1.0):
        h = 0.0
        flat_at = None
        for i in range(n):
            h += dh
            p.add(curve(h), dh)
            if p.flat() and flat_at is None:
                flat_at = i
        return flat_at

    def test_diminishing_curve_goes_flat(self):
        p = Plateau(window=2, min_gain=0.5, patience=2, min_hours=2)
        at = self.feed(p, lambda h: 50 + 30 * (1 - math.exp(-h / 1.5)), 15)
        self.assertIsNotNone(at)
        self.assertGreater(at, 3)

    def test_steady_gain_never_flat(self):
        p = Plateau()
        self.assertIsNone(self.feed(p, lambda h: 50 + 3 * h, 20))

    def test_min_sleep_hours(self):
        p = Plateau(window=1, min_gain=1, patience=1, min_hours=5)
        at = self.feed(p, lambda h: 10.0, 10)
        self.assertEqual(at, 4)   # 5th chunk reaches 5 h

    def test_missing_quiz_never_flat(self):
        p = Plateau(window=1, min_gain=1, patience=1, min_hours=0)
        for _ in range(6):
            p.add(None, 1.0)
        self.assertFalse(p.flat())

    def test_missing_quiz_breaks_streak(self):
        p = Plateau(window=1, min_gain=1, patience=2, min_hours=0)
        for q in (10, 10, None):
            p.add(q, 1)
        self.assertEqual(p.streak, 0)

    def test_reset(self):
        p = Plateau(window=1, min_gain=1, patience=1, min_hours=0)
        for q in (10, 10, 10):
            p.add(q, 1)
        self.assertTrue(p.flat())
        p.reset()
        self.assertFalse(p.flat())
        self.assertEqual(p.hours, 0.0)


if __name__ == "__main__":
    unittest.main()
