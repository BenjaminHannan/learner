import re
from unittest import mock
import unittest

import numpy as np

import crafter
from crafter import constants as crafter_constants

from game import crafter_text as ct


WORLD_SEEDS = (11, 12, 13)
STEPS = 500
ALLOWED = frozenset(
    " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
    "abcdefghijklmnopqrstuvwxyz{|}~")
TEXT_FORMAT = re.compile(
    r'^game: ([^/|]{9}/){6}[^/|]{9} \| h[0-9] f[0-9] d[0-9] e[0-9]'
    r'( zz)?( dark)? \| (none|[a-z]+[0-9]( [a-z]+[0-9])*)$')
PLAYER_CHARS = '^v<>'


class TextEnvMatchesCrafterTest(unittest.TestCase):

    def setUp(self):
        # crafter.Env itself orders a chunk's creatures by memory address, so
        # the stock env is compared with the same position order that TextEnv
        # uses. The patch covers only this test and is undone afterwards.
        original = crafter.Env._balance_chunk

        def balance_chunk(env, chunk, objs):
            original(env, chunk, ct.creature_order(objs))

        patch = mock.patch.object(crafter.Env, '_balance_chunk', balance_chunk)
        patch.start()
        self.addCleanup(patch.stop)

    def test_text_env_is_repeatable(self):
        runs = []
        for _ in range(2):
            env = ct.TextEnv(seed=WORLD_SEEDS[0])
            texts = [env.reset()]
            for action in np.random.default_rng(7).integers(0, 17, 300):
                texts.append(env.step(int(action))[0])
            runs.append(texts)
        self.assertEqual(runs[0], runs[1])

    def test_same_game_as_stock_env(self):
        for seed in WORLD_SEEDS:
            with self.subTest(seed=seed):
                stock = crafter.Env(seed=seed, length=10000)
                text_env = ct.TextEnv(seed=seed, length=10000)
                stock.reset()
                text_env.reset()
                actions = np.random.default_rng(seed).integers(
                    0, len(ct.ACTIONS), STEPS)
                saw_night = False
                for step, action in enumerate(actions):
                    action = int(action)
                    _, reward, done, info = stock.step(action)
                    _, text_reward, text_done, text_info = text_env.step(action)
                    saw_night = saw_night or stock._world.daylight < 0.5
                    where = f'step {step + 1}'
                    self.assertEqual(reward, text_reward, where)
                    self.assertEqual(done, text_done, where)
                    self.assertEqual(
                        info['achievements'], text_info['achievements'], where)
                    self.assertEqual(
                        info['inventory'], text_info['inventory'], where)
                    np.testing.assert_array_equal(
                        info['player_pos'], text_info['player_pos'], where)
                    np.testing.assert_array_equal(
                        info['semantic'], text_info['semantic'], where)
                    if done:
                        break
                self.assertTrue(saw_night, 'night (noise draws) not exercised')


class ViewTextTest(unittest.TestCase):

    def test_size_digits_and_characters(self):
        for seed in WORLD_SEEDS:
            with self.subTest(seed=seed):
                env = ct.TextEnv(seed=seed)
                texts = [env.reset()]
                actions = np.random.default_rng(seed + 100).integers(
                    0, len(ct.ACTIONS), STEPS)
                for action in actions:
                    text, _, done, _ = env.step(int(action))
                    texts.append(text)
                    if done:
                        break
                for text in texts:
                    self.assertLessEqual(len(text), 208)
                    self.assertLessEqual(len(re.findall(r'\d+', text)), 16)
                    self.assertTrue(set(text) <= ALLOWED, repr(text))
                    self.assertRegex(text, TEXT_FORMAT)

    def test_player_and_status_match_game(self):
        env = ct.TextEnv(seed=WORLD_SEEDS[0])
        text = env.reset()
        rows = text[len('game: '):].split(' | ')[0].split('/')
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(len(row) == 9 for row in rows))
        self.assertIn(rows[3][4], PLAYER_CHARS)
        inventory = env._player.inventory
        status = text.split(' | ')[1].split(' ')
        self.assertEqual(
            status[:4],
            [f"h{inventory['health']}", f"f{inventory['food']}",
             f"d{inventory['drink']}", f"e{inventory['energy']}"])

    def test_material_chars_cover_crafter_materials(self):
        self.assertEqual(
            set(ct.MATERIAL_CHARS), set(crafter_constants.materials))

    def test_grid_is_crafter_local_view(self):
        self.assertEqual(ct.GRID, (9, 7))
        self.assertEqual(ct.OFFSET, (4, 3))

    def test_asleep_mark_is_exact(self):
        sleep = ct.parse_action('sleep')
        steps = slept = 0
        for i in range(6):
            env = ct.TextEnv(seed=1_000_000 + i)
            view = env.reset()
            rng = np.random.default_rng(i)
            for _ in range(60):
                action = sleep if rng.random() < 0.3 \
                    else int(rng.integers(0, len(ct.ACTIONS)))
                self.assertEqual(ct.asleep(view), bool(env._player.sleeping))
                steps += 1
                slept += ct.asleep(view)
                view, _, done, _ = env.step(action)
                if done:
                    break
        self.assertGreater(slept, 0)
        print(f'asleep mark: {steps} steps, {slept} asleep, all agree')


class ParseActionTest(unittest.TestCase):

    def test_round_trip_all_17_words(self):
        self.assertEqual(len(ct.ACTIONS), 17)
        self.assertEqual(
            [name for name, _ in ct.ACTIONS], list(crafter_constants.actions))
        for index, (_, word) in enumerate(ct.ACTIONS):
            self.assertEqual(ct.parse_action(word), index)
            self.assertEqual(ct.parse_action(f'  {word}\n'), index)

    def test_rejects_other_text(self):
        for text in ['', ' ', 'Left', 'LEFT', 'move_left', 'left up',
                     'stone pickaxe', 'wood', 'leftt', 'noop noop', 'stone,',
                     None, 7]:
            with self.subTest(text=text):
                self.assertIsNone(ct.parse_action(text))


if __name__ == '__main__':
    unittest.main()
