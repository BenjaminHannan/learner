"""Tests for game/imitate.py (GW-F, addendum A26). Run: python -m unittest game.tests.test_imitate

The pure parts need nothing; the smoke runs use the real T1SDR parent (skipped if the file is missing; GWF_PARENT overrides the path).
"""
import json
import os
import random
import tempfile
import unittest

import numpy as np
import torch

from game import imitate, play

PARENT = os.environ.get('GWF_PARENT', '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt')


def _view(table, items):
    """A 9x7 text view: the player (facing up) at the centre, a table cell offset by `table`, status and items as given."""
    rows = [['.'] * 9 for _ in range(7)]
    rows[3][4] = '^'
    rows[3 + table[1]][4 + table[0]] = 't'
    return 'game: ' + '/'.join(''.join(r) for r in rows) + ' | h9 f9 d9 e9 | ' + items


class Pure(unittest.TestCase):
    def test_segments_run_between_events_of_any_type(self):
        segs = imitate.segments([(3, 'a'), (3, 'b'), (7, 'a'), (9, 'c')], game=4)
        key = [(s['type'], s['start'], s['end'], s['length']) for s in segs]
        self.assertEqual(key, [('a', 0, 3, 4), ('b', 0, 3, 4), ('a', 4, 7, 4), ('c', 8, 9, 2)])
        self.assertTrue(all(s['game'] == 4 for s in segs))
        self.assertEqual(imitate.segments([], 0), [])
        self.assertEqual(imitate.segments([(0, 'x')], 0)[0]['length'], 1)

    def test_keep_takes_fastest_30_percent_and_at_most_12(self):
        segs = [dict(type='X', game=g, start=0, end=g, length=g + 1) for g in range(10)]            # lengths 1..10
        segs += [dict(type='Y', game=g, start=0, end=19 + g, length=20 + g) for g in range(2)]       # both too long
        segs += [dict(type='Z', game=0, start=0, end=4, length=5)]
        kept, thr = imitate.keep_segments(segs)
        self.assertEqual(sorted(s['length'] for s in kept if s['type'] == 'X'), [1, 2, 3])
        self.assertEqual(thr, {'X': 3, 'Z': 5})
        self.assertFalse(any(s['type'] == 'Y' for s in kept))
        # ceil: 4 segments keep 2
        four = [dict(type='W', game=g, start=0, end=g, length=g + 1) for g in range(4)]
        self.assertEqual(len(imitate.keep_segments(four)[0]), 2)

    def test_rare_types_keep_every_segment_within_the_cap(self):
        segs = [dict(type='X', game=g, start=0, end=g, length=g + 1) for g in range(10)]            # 10 segments, lengths 1..10
        segs += [dict(type='Y', game=g, start=0, end=g, length=g + 1) for g in range(200)]           # common type
        segs += [dict(type='R', game=g, start=0, end=19 + g, length=10 + 6 * g) for g in range(4)]   # lengths 10, 16, 22, 28
        base, _ = imitate.keep_segments(segs)
        self.assertEqual(sum(s['type'] == 'X' for s in base), 3)                                      # A26 rule: fastest 30%
        kept, thr = imitate.keep_segments(segs, rare_below=100)
        self.assertEqual(sorted(s['length'] for s in kept if s['type'] == 'X'), list(range(1, 11)))
        self.assertEqual(sum(s['type'] == 'Y' for s in kept), 12)                                    # common types unchanged: fastest 60, of which 12 are within the cap
        self.assertEqual([s['length'] for s in kept if s['type'] == 'R'], [10])                      # 12-move cap still applies
        self.assertEqual(thr['X'], 10)
        self.assertEqual(imitate.keep_segments(segs, rare_below=0)[0], base)

    def test_ready_stats_counts_pickaxe_ready_states(self):
        ready = _view(table=(1, 0), items='wood1')                 # table next to the player, wood in hand
        far = _view(table=(3, 0), items='wood1')                   # table two cells away: not within crafter's `nearby`
        has_pick = _view(table=(1, 0), items='wood1 wpk1')
        no_wood = _view(table=(1, 0), items='none')
        games = [dict(views=[ready, ready, far, has_pick, no_wood], actions=[play.WORDS.index('wpick'), 0, 0, 0, 0])]
        self.assertEqual(imitate.ready_stats(games), dict(ready_games=1, ready_states=2, wpick_share=0.5))
        self.assertEqual(imitate.ready_stats([]), dict(ready_games=0, ready_states=0, wpick_share=None))

    def test_weights_are_rarity_with_a_20_to_1_floor(self):
        w = imitate.type_weights({'a': 100, 'b': 1, 'c': 1_000_000, 'd': 0})
        self.assertAlmostEqual(w['a'], 0.1)
        self.assertAlmostEqual(w['b'], 1.0)
        self.assertAlmostEqual(w['c'], 0.05)       # floor = largest / 20
        self.assertNotIn('d', w)
        self.assertEqual(imitate.type_weights({}), {})

    def test_rows_dedupe_a_step_shared_by_two_types(self):
        games = [dict(views=[f'v{i}' for i in range(6)], actions=list(range(6)))]
        kept = [dict(type='a', game=0, start=0, end=3, length=4), dict(type='b', game=0, start=0, end=3, length=4),
                dict(type='a', game=0, start=4, end=5, length=2)]
        rows = imitate.rows_of(kept, games, {'a': 0.5, 'b': 2.0})
        self.assertEqual([r['view'] for r in rows], [f'v{i}' for i in range(6)])
        self.assertEqual([r['weight'] for r in rows], [2.0] * 4 + [0.5] * 2)
        self.assertEqual([r['type'] for r in rows], ['b'] * 4 + ['a'] * 2)
        self.assertEqual([r['action'] for r in rows], list(range(6)))

    def test_prune_and_training_set(self):
        buf = [dict(type='a', seg_len=5), dict(type='a', seg_len=2), dict(type='b', seg_len=9)]
        self.assertEqual(imitate.prune_buffer(buf, {'a': 3}), [dict(type='a', seg_len=2), dict(type='b', seg_len=9)])
        self.assertEqual(imitate.prune_buffer(buf, {}), buf)
        new = [dict(i=i) for i in range(2)]
        ts = imitate.training_set(new, [dict(j=j) for j in range(5)], random.Random(0))
        self.assertEqual(len(ts), 4)
        self.assertEqual(ts[:2], new)
        self.assertEqual(len(imitate.training_set(new, [dict(j=0)], random.Random(0))), 3)
        self.assertEqual(imitate.training_set(new, [], random.Random(0)), new)

    def test_normalise_gives_mean_one(self):
        w = imitate.normalise([1.0, 3.0, 5.0])
        self.assertAlmostEqual(sum(w) / 3, 1.0)

    def test_days_stay_below_100_for_24_iterations(self):
        self.assertEqual(imitate.day_of(1, 0), 0)
        self.assertEqual(imitate.day_of(24, 3), 95)
        days = {imitate.day_of(k, c) for k in range(1, 25) for c in range(4)}
        self.assertEqual(len(days), 96)

    def test_day_offset_zero_is_unchanged_and_four_shifts_by_four(self):
        # DRAFT pending coordinator review (GW-LS)
        for k in range(1, 25):
            for c in range(4):
                self.assertEqual(imitate.day_of(k, c, 0), imitate.day_of(k, c))
                self.assertEqual(imitate.day_of(k, c, 4), imitate.day_of(k, c) + 4)
        self.assertEqual([imitate.day_of(k, c, 4) for k in (1, 2) for c in range(4)], [4, 5, 6, 7, 8, 9, 10, 11])
        self.assertEqual(imitate.day_of(8, 3, 4), 35)


class Playing(unittest.TestCase):
    def test_play_games_matches_play_play(self):
        # a policy that always answers 'do' (sampling flag on so play.play hands it the uniform numbers too)
        def pol(prompts, us=None):
            return ['do'] * len(prompts)
        pol.samples = True
        seeds = [play.practice_seed(394, 0, i) for i in range(3)]
        acts = [[imitate.ACT_TAG, 394, 0, i] for i in range(3)]
        mine = imitate.play_games(pol, seeds, acts, 0.1, 60)
        ref = play.play(pol, seeds, acts, 0.1, 60, log_steps=True)
        for g, e in zip(mine, ref):
            self.assertEqual(g['length'], e['length'])
            self.assertEqual(g['actions'], [play.WORDS.index(w) for _, w, _, _ in e['steps']])
            self.assertEqual(g['views'], [p for p, _, _, _ in e['steps']])
            self.assertEqual(sorted((t, n) for n, t in g['first'].items()), sorted(e['unlocks']))
            self.assertTrue(all(g['events'][i][0] <= g['events'][i + 1][0] for i in range(len(g['events']) - 1)))
            self.assertTrue(set(g['first']) <= {n for _, n in g['events']})

    def test_sealed_world_refused(self):
        with self.assertRaises(AssertionError):
            imitate.play_games(lambda p, u=None: ['do'] * len(p), [play.SEALED_BASE], [[1]], 0.1, 5)


@unittest.skipUnless(os.path.exists(PARENT), 'parent checkpoint missing')
class Smoke(unittest.TestCase):
    def test_smoke_runs_and_resumes_to_the_same_weights(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            imitate.run(PARENT, 200, 394, 19.69, a, iterations=2, smoke=True)
            imitate.run(PARENT, 200, 394, 19.69, b, iterations=1, smoke=True)
            imitate.run(PARENT, 200, 394, 19.69, b, iterations=2, smoke=True)    # continues from state.pt
            for d in (a, b):
                self.assertTrue(os.path.exists(os.path.join(d, 'iter-2.json')))
                self.assertTrue(os.path.exists(os.path.join(d, 'checkpoint-iter2.pt')))
            sa = torch.load(os.path.join(a, 'state.pt'), weights_only=False)
            sb = torch.load(os.path.join(b, 'state.pt'), weights_only=False)
            self.assertEqual(sa['k'], 2)
            self.assertTrue(all(torch.equal(x, y) for x, y in zip(sa['addon'], sb['addon'])))
            with open(os.path.join(a, 'iter-1.json')) as f:
                st = json.load(f)
            self.assertEqual(st['temp'], 19.69)
            self.assertEqual(st['games'], 3)
            with open(os.path.join(a, 'iter-2.json')) as f:
                self.assertEqual(json.load(f)['temp'], 1.0)

    def test_lookahead_smoke_writes_labels_and_trains(self):
        with tempfile.TemporaryDirectory() as a:
            imitate.run(PARENT, 200, 394, 19.69, a, iterations=1, smoke=True, label_rule='lookahead', epochs=1, workers=1)
            with open(os.path.join(a, 'iter-1.json')) as f:
                st = json.load(f)
            self.assertEqual(st['segments'], {})
            self.assertGreater(st['lookahead']['states'], 0)
            self.assertEqual(st['new_rows'], st['lookahead']['labelled'])
            self.assertTrue(os.path.exists(os.path.join(a, 'labels-1-0.json.gz')))
            self.assertTrue(os.path.exists(os.path.join(a, 'checkpoint-iter1.pt')))

    def test_sealed_run_seed_refused_outside_smoke(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(AssertionError):
                imitate.run(PARENT, 200, 7, 19.69, d, iterations=1)


if __name__ == '__main__':
    unittest.main()
