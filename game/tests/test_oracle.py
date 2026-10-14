"""Tests for game/oracle.py (the GW-L labeller). Run: python -m unittest game.tests.test_oracle"""
import copy
import unittest

from game import oracle, play
from game.crafter_text import TextEnv

REASONS = {'nav', 'act', 'craft', 'sleep', 'wander'}


def view(rows, items='none', stats='h9 f9 d9 e9'):
    assert len(rows) == 7 and all(len(r) == 9 for r in rows), rows
    return f"game: {'/'.join(rows)} | {stats} | {items}"


def grass(**cells):
    """7 rows of grass with the player facing `face` ('^v<>', default '^') at (4, 3) and cells {'r3c5': 'T'} placed."""
    g = [list('.' * 9) for _ in range(7)]
    g[3][4] = cells.pop('face', '^')
    for k, ch in cells.items():
        g[int(k[1])][int(k[3])] = ch
    return [''.join(r) for r in g]


class Parse(unittest.TestCase):
    def test_parse(self):
        v = oracle.parse_view(view(grass(face='>'), 'wood3 wpk1', 'h8 f7 d6 e5 zz dark'))
        self.assertEqual((v.facing, v.h, v.f, v.d, v.e, v.asleep, v.dark), ((1, 0), 8, 7, 6, 5, True, True))
        self.assertEqual(v.items, {'wood': 3, 'wood_pickaxe': 1})
        self.assertEqual(oracle.parse_view(view(grass())).items, {})


class Priorities(unittest.TestCase):
    def test_tree_adjacent_and_faced(self):
        self.assertEqual(oracle.label(view(grass(r2c4='T'))), ('do', 'act'))

    def test_tree_adjacent_not_faced_turns(self):
        self.assertEqual(oracle.label(view(grass(face='v', r3c5='T'))), ('right', 'nav'))
        self.assertEqual(oracle.label(view(grass(face='^', r4c4='T'))), ('down', 'nav'))

    def test_tree_three_cells_away(self):
        self.assertEqual(oracle.label(view(grass(r0c4='T'))), ('up', 'nav'))
        self.assertEqual(oracle.label(view(grass(r3c7='T'))), ('right', 'nav'))

    def test_path_around_blocking_cells(self):
        # tree two up, water straight above the player: the way is around it
        w, r = oracle.label(view(grass(r1c4='T', r2c4='~')))
        self.assertEqual(r, 'nav')
        self.assertIn(w, ('right', 'left'))
        # a wall of stone on the row above and the tree behind it: first step leads to the nearest gap (right, via col 6)
        rows = grass(r1c6='T')
        rows[2] = 'ooooo.ooo'[:9]
        rows[1] = rows[1][:6] + 'T' + rows[1][7:]
        self.assertEqual(oracle.label(view(rows)), ('right', 'nav'))
        # stone encloses the player on three sides and the tree is above: no path to it, rule skipped -> wander
        rows = grass(r0c4='T')
        for k in ('r3c3', 'r3c5', 'r2c4', 'r4c4'):
            rows[int(k[1])] = rows[int(k[1])][:int(k[3])] + 'o' + rows[int(k[1])][int(k[3]) + 1:]
        self.assertEqual(oracle.label(view(rows)), ('noop', 'wander'))

    def test_asleep(self):
        self.assertEqual(oracle.label(view(grass(r2c4='T'), stats='h9 f9 d9 e3 zz')), ('sleep', 'sleep'))

    def test_zombie_before_everything(self):
        self.assertEqual(oracle.label(view(grass(r2c4='Z', r3c5='T'), stats='h9 f9 d1 e9')), ('do', 'act'))
        self.assertEqual(oracle.label(view(grass(r3c3='Z', r2c4='T'))), ('left', 'nav'))
        # a zombie two cells away is not adjacent: the tree comes first
        self.assertEqual(oracle.label(view(grass(r1c4='Z', r3c3='T', face='<'))), ('do', 'act'))

    def test_drink_and_eat(self):
        self.assertEqual(oracle.label(view(grass(r3c2='~'), stats='h9 f9 d5 e9')), ('left', 'nav'))
        self.assertEqual(oracle.label(view(grass(r3c3='~', face='<'), stats='h9 f9 d4 e9')), ('do', 'act'))
        self.assertEqual(oracle.label(view(grass(r3c2='~', r2c4='T'), stats='h9 f9 d6 e9')), ('do', 'act'))   # not thirsty: tree
        self.assertEqual(oracle.label(view(grass(r1c4='C'), stats='h9 f5 d9 e9')), ('up', 'nav'))
        self.assertEqual(oracle.label(view(grass(r2c4='C'), stats='h9 f2 d9 e9')), ('do', 'act'))
        # thirst before hunger
        self.assertEqual(oracle.label(view(grass(r3c1='~', r1c4='C'), stats='h9 f2 d2 e9')), ('left', 'nav'))

    def test_table_when_two_wood_and_no_table(self):
        self.assertEqual(oracle.label(view(grass(), 'wood2')), ('table', 'craft'))
        self.assertEqual(oracle.label(view(grass(r2c4='T'), 'wood3')), ('do', 'act'))             # faced cell not placeable: tree
        self.assertEqual(oracle.label(view(grass(r2c4='~'), 'wood2'))[1], 'wander')
        self.assertNotEqual(oracle.label(view(grass(r0c0='t'), 'wood2')), ('table', 'craft'))    # a table is in view

    def test_tools_at_the_table(self):
        self.assertEqual(oracle.label(view(grass(r3c5='t'), 'wood1')), ('wpick', 'craft'))
        self.assertEqual(oracle.label(view(grass(r2c3='t'), 'wood2')), ('wpick', 'craft'))        # diagonal is within reach
        self.assertEqual(oracle.label(view(grass(r3c5='t'), 'wood1 wpk1')), ('wsword', 'craft'))
        self.assertEqual(oracle.label(view(grass(r3c5='t'), 'wood1 wpk1 wsw1')), ('up', 'wander'))

    def test_plant(self):
        self.assertEqual(oracle.label(view(grass(), 'sapl1')), ('plant', 'act'))
        self.assertNotEqual(oracle.label(view(grass(r2c4=':'), 'sapl1'))[0], 'plant')

    def test_stone_after_pickaxe(self):
        self.assertEqual(oracle.label(view(grass(r2c4='o', r6c0='t'), 'wood4 wpk1 wsw1')), ('do', 'act'))
        self.assertEqual(oracle.label(view(grass(r0c4='o', r6c0='t'), 'wood4 wpk1 wsw1')), ('up', 'nav'))
        self.assertEqual(oracle.label(view(grass(r2c4='o', r0c0='T', r6c8='t'), 'wood2 wpk1 wsw1'))[1], 'nav')   # wood < 4: tree first

    def test_wander(self):
        self.assertEqual(oracle.label(view(grass(face='>'))), ('right', 'wander'))
        rows = grass(face='>', r3c5='~')               # blocked ahead: next walkable after right is down
        self.assertEqual(oracle.label(view(rows)), ('down', 'wander'))
        rows = grass(face='^', r2c4='o', r3c5='o')     # up, right blocked: down
        self.assertEqual(oracle.label(view(rows)), ('down', 'wander'))
        rows = grass(face='<', r3c3='o', r4c4='o', r3c5='o')   # left, down, right blocked -> up
        self.assertEqual(oracle.label(view(rows)), ('up', 'wander'))
        rows = grass(face='<', r3c3='o', r4c4='o', r3c5='o', r2c4='o')
        self.assertEqual(oracle.label(view(rows)), ('noop', 'wander'))
        self.assertEqual(oracle.label(view(grass(face='v', r4c4=':'))), ('down', 'wander'))   # sand is walkable


class Purity(unittest.TestCase):
    def test_same_answer_and_input_unchanged(self):
        v = view(grass(r1c4='T'), 'wood1')
        before = copy.copy(v)
        self.assertEqual(oracle.label(v), oracle.label(v))
        self.assertEqual(v, before)
        pol = oracle.oracle_policy()
        self.assertEqual(pol([v, v]), [oracle.label(v)[0]] * 2)

    def test_valid_on_practice_episodes(self):
        for i in range(6):
            env = TextEnv(seed=play.practice_seed(390, 99, i), length=150)
            text, done, n = env.reset(), False, 0
            while not done:
                word, reason = oracle.label(text)
                self.assertIn(word, play.WORDS)
                self.assertIn(reason, REASONS)
                text, _, done, _ = env.step(play.WORDS.index(word))
                n += 1
            self.assertGreater(n, 5)


if __name__ == '__main__':
    unittest.main()
