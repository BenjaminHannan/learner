"""Tests for the move chooser in game/play.py. Run: python -m unittest game.tests.test_picker

The model-free tests patch play.move_logprobs with a fixed pseudo-random score table; the agreement test uses the real T1SDR checkpoint.
"""
import os
import unittest
import zlib
from unittest import mock

import numpy as np
import torch

from game import play
from game.crafter_text import TextEnv

CKPT = '/mnt/project-files/game-world/runs/gw-s200/night_4/checkpoint.pt'


def fake_logprobs(m, prompts, bs=64):
    return np.array([np.random.default_rng(zlib.crc32(p.encode())).normal(size=play.N_ACTIONS) * 2 for p in prompts])


def run_play(pol, seeds=(1_000_001, 1_000_002), acts=([3, 0], [3, 1]), cap=25):
    return play.play(pol, list(seeds), [list(a) for a in acts], 0.1, cap, log_steps=True)


def moves(eps):
    return [[s[1:3] for s in e['steps']] for e in eps]


class Chooser(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(play, 'move_logprobs', fake_logprobs)
        p.start()
        self.addCleanup(p.stop)

    def test_only_legal_words_and_top_is_argmax(self):
        views = [TextEnv(seed=1_000_000 + i, length=50).reset() for i in range(6)]
        top = play.move_policy(None, 'top')(views)
        self.assertEqual(top, [play.WORDS[int(np.argmax(r))] for r in fake_logprobs(None, views)])
        self.assertTrue(set(top) <= set(play.WORDS))
        smp = play.move_policy(None, 'sample')(views, [0.1, 0.5, 0.9, 0.0, 0.999999, 0.3])
        self.assertTrue(set(smp) <= set(play.WORDS))

    def test_top_ties_take_lowest_index(self):
        with mock.patch.object(play, 'move_logprobs', lambda m, p, bs=64: np.zeros((len(p), play.N_ACTIONS))):
            self.assertEqual(play.move_policy(None, 'top')(['x']), [play.WORDS[0]])

    def test_softmax_pick_follows_odds(self):
        s = np.log(np.array([0.2, 0.3, 0.5] + [1e-12] * 14))
        got = [play.softmax_pick(s, u) for u in (0.0, 0.19, 0.21, 0.49, 0.51, 0.999)]
        self.assertEqual(got, [0, 0, 1, 1, 2, 2])

    def test_sample_deterministic_per_act_seed(self):
        a, b = (moves(run_play(play.move_policy(None, 'sample'))) for _ in range(2))
        self.assertEqual(a, b)
        c = moves(run_play(play.move_policy(None, 'sample'), acts=([4, 0], [4, 1])))
        self.assertNotEqual(a, c)
        t = moves(run_play(play.move_policy(None, 'top')))
        self.assertNotEqual(a, t)
        self.assertTrue(all(src != 'invalid' for e in a for _, src in e))

    def test_greedy_style_play_unchanged_by_sample_stream(self):
        """A policy that ignores the sample stream plays the same episode whether or not play makes that stream."""
        def words(prompts):
            return [play.WORDS[zlib.crc32(p.encode()) % play.N_ACTIONS] if i % 5 else 'garble' for i, p in enumerate(prompts)]
        plain = run_play(words)

        def sampling(prompts, us):
            return words(prompts)
        sampling.samples = True
        self.assertEqual(moves(plain), moves(run_play(sampling)))
        self.assertEqual([e['unlocks'] for e in plain], [e['unlocks'] for e in run_play(sampling)])
        self.assertEqual(moves(plain), moves(run_play(words)))


@unittest.skipUnless(os.path.exists(CKPT), 'T1SDR checkpoint missing')
class Agreement(unittest.TestCase):
    def test_chooser_agrees_with_greedy(self):
        from custom_io.models import load_model
        from domain.mode import greedy
        torch.set_num_threads(4)
        m = load_model(CKPT).eval()
        views = [TextEnv(seed=1_000_000 + i, length=50).reset() for i in range(50)]
        lp = play.move_logprobs(m, views)
        self.assertEqual(lp.shape, (50, play.N_ACTIONS))
        self.assertTrue(np.isfinite(lp).all() and (lp <= 1e-6).all())
        ans = [a for _, a in greedy(m, views)]
        valid = [(a, r) for a, r in zip(ans, lp) if a in play.WORDS]
        ok = sum(r[play.WORDS.index(a)] >= r.max() - 1e-4 for a, r in valid)
        print(f'\nagreement: {ok}/{len(valid)} valid greedy answers are the chooser top ({len(views)} views)')
        self.assertEqual(ok, len(valid))
        # batch size must not matter
        self.assertTrue(np.allclose(lp[:7], play.move_logprobs(m, views[:7], bs=3), atol=1e-4))


if __name__ == '__main__':
    unittest.main()
