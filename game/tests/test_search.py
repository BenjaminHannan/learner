"""Tests for game/search.py (SQ, addendum A24). Run: python -m unittest game.tests.test_search

Practice worlds only (run seed 392); small search budgets so the suite stays quick.
"""
import json
import os
import tempfile
import unittest

import numpy as np

from game import oracle, play, search
from game.crafter_text import TextEnv


def mixed_env(steps, seed_i=0):
    """A live env after `steps` oracle moves in practice world seed_i of run 392."""
    env = TextEnv(seed=play.practice_seed(search.RUN_SEED, 0, seed_i), length=1000)
    view = env.reset()
    for _ in range(steps):
        view, _, done, _ = env.step(play.WORDS.index(oracle.label(view)[0]))
        assert not done
    return env, view


class Pure(unittest.TestCase):
    def test_pick_needs_both_conditions(self):
        flat = [0.1] * 17
        self.assertIsNone(search.pick(flat))                       # nothing stands out
        low = [0.0] * 16 + [0.19]
        self.assertIsNone(search.pick(low))                        # best below 0.20
        weak = [0.19] * 16 + [0.25]
        self.assertIsNone(search.pick(weak))                       # best - mean < 0.10
        ok = [0.0] * 16 + [0.5]
        self.assertEqual(search.pick(ok), 16)
        tie = [0.0, 0.6, 0.0, 0.6] + [0.0] * 13
        self.assertEqual(search.pick(tie), 1)                      # ties to the lowest index

    def test_verdict(self):
        v = search.verdict
        self.assertEqual(v(0.9, 0.3, 0.7), 'pass')
        self.assertEqual(v(0.9, 0.05, 0.9), 'proved wrong')
        self.assertEqual(v(0.9, 0.5, 0.3), 'proved wrong')
        self.assertEqual(v(0.9, 0.2, 0.7), 'no verdict')
        self.assertEqual(v(0.9, 0.3, 0.5), 'no verdict')
        self.assertEqual(v(0.5, 0.3, 0.7), 'instrument check failed (SQ-0)')
        self.assertEqual(v(0.9, 0.3, None), 'no verdict')
        self.assertEqual(v(0.9, 0.05, None), 'proved wrong')

    def test_stats_counts(self):
        def row(reason, oracle_word, search_word):
            return dict(reason=reason, oracle=oracle_word, search=search_word, seconds=1.0)
        rows = [row('act', 'do', 'do'), row('act', 'do', 'up'), row('nav', 'up', 'up'), row('nav', 'up', None),
                row('nav', 'left', 'right'), row('nav', 'right', 'right'), row('craft', 'table', None)]
        st = search.stats(rows)
        self.assertEqual(st['by_reason']['nav']['views'], 4)
        self.assertEqual(st['by_reason']['nav']['labelled'], 3)
        self.assertAlmostEqual(st['SQ1'], 0.75)
        self.assertAlmostEqual(st['SQ2'], 2 / 3)
        self.assertAlmostEqual(st['SQ0'], 0.5)
        self.assertEqual(st['verdict'], 'instrument check failed (SQ-0)')
        self.assertEqual(st['by_reason']['craft']['coverage'], 0.0)
        self.assertEqual(st['by_reason']['sleep']['views'], 0)


class Rollouts(unittest.TestCase):
    def test_rollout_leaves_the_env_alone(self):
        env, _ = mixed_env(20)
        before = (env._step, tuple(env._player.pos), env._world.random.get_state()[1].tolist(), env._world.daylight)
        rng = np.random.default_rng(0)
        search.rollout_return(env, 1, rng, h=10)
        search.search_means(env, rng, k=2, h=5)
        after = (env._step, tuple(env._player.pos), env._world.random.get_state()[1].tolist(), env._world.daylight)
        self.assertEqual(before, after)

    def test_same_rng_same_result_and_different_futures(self):
        env, _ = mixed_env(20)
        a = search.search_means(env, np.random.default_rng(5), k=3, h=8)
        b = search.search_means(env, np.random.default_rng(5), k=3, h=8)
        self.assertEqual(a, b)
        self.assertEqual(len(a), play.N_ACTIONS)

    def test_search_finds_do_when_facing_a_tree(self):
        # first state of the oracle's play where the answer is `do` on a tree with no wood yet
        env = TextEnv(seed=play.practice_seed(search.RUN_SEED, 0, 0), length=1000)
        view = env.reset()
        for _ in range(200):
            word, reason = oracle.label(view)
            v = oracle.parse_view(view)
            if word == 'do' and reason == 'act' and not v.items.get('wood'):
                break
            view, _, done, _ = env.step(play.WORDS.index(word))
            self.assertFalse(done)
        else:
            self.fail('no tree reached in 200 oracle moves')
        means = search.search_means(env, np.random.default_rng(1))
        self.assertEqual(play.WORDS[search.pick(means)], 'do')


class OneWorld(unittest.TestCase):
    def test_run_world_writes_once_and_is_resumable(self):
        with tempfile.TemporaryDirectory() as d:
            rows = search.run_world(0, d, k=1, h=3, cap=14)
            self.assertEqual([r['step'] for r in rows], [3, 7, 11])
            self.assertTrue(all(r['reason'] == oracle.label(r['view'])[1] for r in rows))
            self.assertTrue(all(len(r['means']) == play.N_ACTIONS for r in rows))
            path = os.path.join(d, 'world-0.json')
            stamp = os.path.getmtime(path)
            again = search.run_world(0, d, k=1, h=3, cap=14)
            self.assertEqual(rows, again)
            self.assertEqual(stamp, os.path.getmtime(path))
            with open(path) as f:
                self.assertEqual(json.load(f)['seed'], play.practice_seed(search.RUN_SEED, 0, 0))

    def test_no_sealed_world(self):
        self.assertFalse(play.is_sealed(play.practice_seed(search.RUN_SEED, 0, 99)))


class Expert(unittest.TestCase):
    def test_expert_verdict(self):
        v = search.expert_verdict
        self.assertEqual([v(6.0), v(5.99), v(4.51), v(4.5), v(2.31), v(8.23)],
                         ['pass', 'no verdict', 'no verdict', 'proved wrong', 'proved wrong', 'pass'])

    def test_expert_episode_is_deterministic_and_follows_the_act_rule(self):
        a = search.expert_episode(0, k=1, h=3, max_steps=8)
        b = search.expert_episode(0, k=1, h=3, max_steps=8)
        a.pop('seconds'), b.pop('seconds')
        self.assertEqual(a, b)
        self.assertEqual(a['length'], 8)
        self.assertEqual(sum(a['sources'].values()), 8)
        self.assertEqual(a['seed'], play.practice_seed(search.EXPERT_RUN, 0, 0))
        # explore = 1 makes every step the act stream's random action
        c = search.expert_episode(0, k=1, h=3, max_steps=5, explore=1.0)
        self.assertEqual(c['sources'], dict(search=0, fallback=0, explore=5))

    def test_act_stream_matches_play_play(self):
        # the expert's random actions must be the ones play.play draws for act seed [7, i] (same stream, same order)
        seed = play.practice_seed(search.EXPERT_RUN, 0, 3)
        ref = play.play(None, [seed], [[7, 3]], 0.1, 12, log_steps=True)[0]['steps']
        rng = np.random.default_rng([7, 3])
        draws = [(rng.random(), int(rng.integers(play.N_ACTIONS))) for _ in range(12)]
        self.assertEqual([play.WORDS[r] for _, r in draws], [w for _, w, _, _ in ref])

    def test_run_expert_world_resumable(self):
        with tempfile.TemporaryDirectory() as d:
            a = search.run_expert_world(1, d, k=1, h=3, max_steps=4)
            path = os.path.join(d, 'expert-1.json')
            stamp = os.path.getmtime(path)
            self.assertEqual(a, search.run_expert_world(1, d, k=1, h=3, max_steps=4))
            self.assertEqual(stamp, os.path.getmtime(path))

    def test_reference_arms_use_the_same_worlds(self):
        ref = search.reference_arms(2, 0, 30)
        self.assertEqual(sorted(ref), ['oracle', 'random'])
        self.assertTrue(all(len(v) == 2 for v in ref.values()))
        self.assertEqual([e['seed'] for e in ref['oracle']], [play.practice_seed(search.EXPERT_RUN, 0, i) for i in range(2)])


if __name__ == '__main__':
    unittest.main()
