"""Tests for game/lookahead.py (GW-O, addendum A29). Run: python -m unittest game.tests.test_lookahead"""
import unittest

from game import lookahead, oracle, play
from game.crafter_text import TextEnv, parse_action

SEED = play.practice_seed(396, 0, 9)          # the hand-written labeller reaches its first `wpick` at step 11 on this world
CAP = 1000
WPICK = parse_action('wpick')


def oracle_game(seed, steps):
    env = TextEnv(seed=seed, length=CAP)
    view, game = env.reset(), dict(seed=seed, views=[], actions=[], first={})
    for t in range(steps):
        w, _ = oracle.label(view)
        game['views'].append(view)
        game['actions'].append(parse_action(w))
        view, _, done, info = env.step(parse_action(w))
        for n, c in info['achievements'].items():
            if c > 0:
                game['first'].setdefault(n, t)
        if done:
            break
    return game


class Labels(unittest.TestCase):
    def test_wpick_is_a_label_in_a_ready_state(self):
        env = TextEnv(seed=SEED, length=CAP)
        view = env.reset()
        for t in range(11):
            view, _, _, _ = env.step(parse_action(oracle.label(view)[0]))
        self.assertEqual(oracle.label(view)[0], 'wpick')
        labs = lookahead.label_words(env)
        self.assertEqual(labs[WPICK], ['make_wood_pickaxe'])
        self.assertTrue(all(isinstance(a, int) for a in labs))

    def test_label_words_leaves_the_world_alone(self):
        env = TextEnv(seed=SEED, length=CAP)
        view = env.reset()
        for t in range(11):
            view, _, _, _ = env.step(parse_action(oracle.label(view)[0]))
        a = lookahead.label_words(env)
        b = lookahead.label_words(env)
        self.assertEqual(a, b)
        _, _, _, info = env.step(WPICK)
        self.assertEqual(info['achievements']['make_wood_pickaxe'], 1)

    def test_executed_first_unlocks_are_labels_of_their_state(self):
        game = oracle_game(SEED, 60)
        env = TextEnv(seed=SEED, length=CAP)
        env.reset()
        for j, act in enumerate(game['actions']):
            labs = lookahead.label_words(env)
            unlocking = {n for n, t in game['first'].items() if t == j}
            if unlocking:
                self.assertIn(act, labs, (j, unlocking))
                self.assertTrue(unlocking <= set(labs[act]), (j, unlocking, labs[act]))
            env.step(act)
        self.assertIn('make_wood_pickaxe', game['first'])

    def test_label_game_replays_and_picks_one_row_a_step(self):
        game = oracle_game(SEED, 40)
        rows = lookahead.label_game(game, CAP)
        steps = [r['step'] for r in rows]
        self.assertEqual(steps, sorted(set(steps)))
        for r in rows:
            self.assertEqual(r['view'], game['views'][r['step']])
            self.assertIn(r['type'], {'collect_sapling', 'collect_wood', 'place_table', 'make_wood_pickaxe', 'make_wood_sword', 'collect_drink', 'eat_cow',
                                      'place_plant', 'wake_up', 'defeat_zombie', 'collect_stone', 'place_stone', 'collect_coal'})
        self.assertIn(WPICK, [r['action'] for r in rows])
        self.assertEqual(rows, lookahead.label_game(game, CAP))          # deterministic

    def test_label_game_catches_a_changed_replay(self):
        game = oracle_game(SEED, 20)
        game['actions'][3] = (game['actions'][3] + 1) % play.N_ACTIONS     # a different move: the saved views no longer match
        with self.assertRaises(AssertionError):
            lookahead.label_game(game, CAP)

    def test_pool_matches_single_process_and_refuses_sealed_worlds(self):
        games = [oracle_game(play.practice_seed(396, 0, i), 25) for i in (9, 1)]
        r1, s1 = lookahead.label_games(games, CAP, workers=1)
        r2, s2 = lookahead.label_games(games, CAP, workers=2)
        self.assertEqual(r1, r2)
        self.assertEqual(s1, s2)
        self.assertEqual(s1['states'], 50)
        sealed = dict(games[0], seed=play.SEALED_BASE)
        with self.assertRaises(AssertionError):
            lookahead.label_game(sealed, CAP)


if __name__ == '__main__':
    unittest.main()
