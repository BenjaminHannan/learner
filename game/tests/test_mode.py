import gzip
import json
import os
import tempfile
import unittest

from game import mode, play


class KeepWindowsTest(unittest.TestCase):

    def test_single_unlock_window(self):
        self.assertEqual(mode.keep_windows([(20, 'a')], 8), [(s, 'a', 20) for s in range(13, 21)])

    def test_unlock_at_step_zero(self):
        self.assertEqual(mode.keep_windows([(0, 'a')], 8), [(0, 'a', 0)])

    def test_early_unlock_starts_at_zero(self):
        self.assertEqual(mode.keep_windows([(3, 'a')], 8), [(s, 'a', 3) for s in range(0, 4)])

    def test_overlapping_windows_do_not_overlap(self):
        out = mode.keep_windows([(10, 'a'), (14, 'b')], 8)
        self.assertEqual([x[0] for x in out], list(range(3, 15)))
        self.assertEqual([x for x in out if x[1] == 'b'], [(s, 'b', 14) for s in range(11, 15)])

    def test_two_unlocks_on_one_step(self):
        out = mode.keep_windows([(5, 'a'), (5, 'b')], 3)
        self.assertEqual(out, [(3, 'a', 5), (4, 'a', 5), (5, 'a', 5)])

    def test_no_unlocks(self):
        self.assertEqual(mode.keep_windows([], 8), [])

    def test_awake_only_drops_exactly_the_asleep_steps(self):
        unlocks = [(10, 'a'), (14, 'b')]
        asleep = {4, 5, 12, 20}
        plain = mode.keep_windows(unlocks, 8)
        out = mode.keep_windows(unlocks, 8, asleep)
        self.assertEqual(out, [x for x in plain if x[0] not in asleep])
        self.assertEqual({x[0] for x in plain} - {x[0] for x in out}, {4, 5, 12})

    def test_awake_only_without_sleep_or_flag_is_unchanged(self):
        unlocks = [(10, 'a'), (14, 'b'), (30, 'c')]
        plain = mode.keep_windows(unlocks, 8)
        self.assertEqual(mode.keep_windows(unlocks, 8, set()), plain)
        self.assertEqual(mode.keep_windows(unlocks, 8, None), plain)


class MovesTest(unittest.TestCase):

    def test_rewards_and_roundtrip(self):
        seeds, acts = mode.world_seeds(200, 1, 2)
        eps = play.play(None, seeds, acts, 0.0, 30, log_steps=True)
        for e in eps:
            self.assertEqual(len(e['steps']), e['length'])
            self.assertTrue(all(len(s) == 4 for s in e['steps']))
            tot = sum(s[3] for s in e['steps'])
            self.assertAlmostEqual(tot, len(e['unlocks']) + (e['final_health'] - 9) / 10, delta=1e-6)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'moves', 'day_1.jsonl.gz')
            n = mode.write_moves(p, eps)
            self.assertEqual(n, sum(e['length'] for e in eps))
            with gzip.open(p, 'rt') as f:
                recs = [json.loads(x) for x in f]
        self.assertEqual(len(recs), n)
        k = 0
        for e in eps:
            for t, (view, word, src, rew) in enumerate(e['steps']):
                r = recs[k]
                k += 1
                self.assertEqual((r['world_seed'], r['step'], r['view'], r['move'], r['source']), (e['seed'], t, view, word, src))
                self.assertEqual(r['reward'], rew)
                self.assertEqual(r['unlocks'], [nm for u, nm in e['unlocks'] if u == t])
                self.assertEqual(r['end'], e['end'] if t == e['length'] - 1 else None)


class SeedsTest(unittest.TestCase):

    def test_disjoint_and_not_sealed(self):
        seen = set()
        for day in range(0, 13):
            n = 32 if day == 0 else 64
            seeds, acts = mode.world_seeds(200, day, n)
            self.assertEqual(len(acts), n)
            for s in seeds:
                self.assertNotIn(s, seen)
                self.assertFalse(play.is_sealed(s))
                seen.add(s)
        self.assertEqual(len(seen), 32 + 12 * 64)


class StopDecisionTest(unittest.TestCase):

    def test_fixed_nights_ignores_stop_rule(self):
        cons = dict(stop_min_rise_points=1.0, max_nights=5)
        self.assertEqual(mode.stop_decision(0.0, 3, cons), ('quiz_rise_below_1_over_2_nights', False))
        self.assertEqual(mode.stop_decision(0.0, 3, cons, fixed_nights=4), (None, True))
        self.assertEqual(mode.stop_decision(0.0, 4, cons, fixed_nights=4), ('fixed_nights', True))
        self.assertEqual(mode.stop_decision(5.0, 3, cons, fixed_nights=4), (None, False))


if __name__ == '__main__':
    unittest.main()
