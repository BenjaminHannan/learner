"""Tests for the view-blind arm (game/blind.py and score --arm blind). Run: python -m unittest game.tests.test_blind"""
import json
import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from game import blind, play, score


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


class Policy(unittest.TestCase):
    def test_one_hot(self):
        q = np.zeros(play.N_ACTIONS)
        q[play.WORDS.index('do')] = 1.0
        pol = blind.blind_policy(q)
        self.assertTrue(pol.samples and pol.picker == 'blind')
        us = [0.0, 0.3, 0.5, 0.999999]
        self.assertEqual(pol(['x'] * 4, us), ['do'] * 4)

    def test_frequencies(self):
        q = softmax(np.random.default_rng(0).normal(size=play.N_ACTIONS) * 2)
        n = 200_000
        got = blind.blind_policy(q)([''] * n, [(i + 0.5) / n for i in range(n)])
        freq = np.array([got.count(w) for w in play.WORDS]) / n
        self.assertLess(np.abs(freq - q).max(), 1e-3)


class Fit(unittest.TestCase):
    def fit(self, rows, temp):
        rows = np.array(rows, dtype=np.float64)
        with mock.patch('game.play.move_logprobs', lambda m, p, bs=64: rows):
            return blind.fit(None, ['v'] * len(rows), temp)

    def test_identical_rows(self):
        row = np.random.default_rng(1).normal(size=play.N_ACTIONS)
        r = self.fit([row] * 3, 0.7)
        self.assertLess(abs(r['mean_kl']), 1e-12)
        np.testing.assert_allclose(r['qbar'], softmax(row / 0.7), atol=1e-12)
        self.assertEqual((r['n_views'], r['word_len'][0], r['words']), (3, len(play.WORDS[0]), list(play.WORDS)))

    def test_two_rows(self):
        a, b = (np.random.default_rng(s).normal(size=play.N_ACTIONS) for s in (2, 3))
        r = self.fit([a, b], 1.5)
        qa, qb = softmax(a / 1.5), softmax(b / 1.5)
        qbar = (qa + qb) / 2
        want = (np.sum(qa * np.log(qa / qbar)) + np.sum(qb * np.log(qb / qbar))) / 2
        self.assertGreater(r['mean_kl'], 0)
        self.assertAlmostEqual(r['mean_kl'], want, places=12)
        np.testing.assert_allclose(r['mean_logp'], (a + b) / 2)
        p1, q1 = softmax(a), softmax(b)
        m1 = (p1 + q1) / 2
        self.assertAlmostEqual(r['mean_kl_t1'], (np.sum(p1 * np.log(p1 / m1)) + np.sum(q1 * np.log(q1 / m1))) / 2, places=12)
        same = int(np.argmax(a) == np.argmax(b))
        self.assertEqual((sum(r['top_counts']), r['top_share']), (2, 1.0 if same else 0.5))

    def test_views_from_moves_refuses_sealed(self):
        import gzip
        with tempfile.TemporaryDirectory() as td:
            ok, bad = os.path.join(td, 'ok.jsonl.gz'), os.path.join(td, 'bad.jsonl.gz')
            for p, seed in ((ok, 5), (bad, play.SEALED_BASE)):
                with gzip.open(p, 'wt') as f:
                    for v in ('a', 'b', 'a'):
                        f.write(json.dumps(dict(world_seed=seed, view=v)) + '\n')
            self.assertEqual(blind.views_from_moves(ok), ['a', 'b', 'a'])
            with self.assertRaises(AssertionError):
                blind.views_from_moves(bad)


class Score(unittest.TestCase):
    def test_blind_arm(self):
        q = softmax(np.random.default_rng(4).normal(size=play.N_ACTIONS))
        with tempfile.TemporaryDirectory() as td:
            qp, out = os.path.join(td, 'q.json'), os.path.join(td, 'o.json')
            with open(qp, 'w') as f:
                json.dump(dict(qbar=q.tolist()), f)
            score.main(['--arm', 'blind', '--probs', qp, '--worlds', '2', '--cap', '20', '--out', out])
            with open(out) as f:
                res = json.load(f)
        self.assertEqual((res['arm'], res['worlds'], len(res['per_world']), res['probs']), ('blind', 2, 2, qp))
        np.testing.assert_allclose(res['qbar'], q)
        self.assertTrue(all(play.is_sealed(w['seed']) for w in res['per_world']))
        self.assertEqual(sum(sum(w['sources'].values()) for w in res['per_world']), 40)
        self.assertEqual(sum(w['sources']['invalid'] for w in res['per_world']), 0)

    def test_flag_refusals(self):
        with self.assertRaises(AssertionError):
            score.main(['--arm', 'blind', '--worlds', '2', '--cap', '20', '--out', '/dev/null'])
        with self.assertRaises(AssertionError):
            score.main(['--arm', 'model', '--ckpt', 'x', '--probs', 'q.json', '--worlds', '2', '--cap', '20', '--out', '/dev/null'])


if __name__ == '__main__':
    unittest.main()
