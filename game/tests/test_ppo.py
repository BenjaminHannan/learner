import json
import os
import tempfile
import unittest

import numpy as np

from game import ppo, play


HAND = ('game: ' + '/'.join(['.........'] * 3 + ['....^..T.'] + ['.........'] * 3)
        + ' | h9 f5 d3 e7 zz dark | wood3 wpk1')


class ParseTest(unittest.TestCase):

    def test_hand_example(self):
        v = ppo.parse_obs(HAND)
        self.assertEqual(v.shape, (ppo.OBS_DIM,))
        n = len(ppo.CHARS)
        cells = v[:ppo.N_CELLS * n].reshape(ppo.N_CELLS, n)
        self.assertTrue((cells.sum(1) == 1).all())
        self.assertEqual(cells[3 * 9 + 4].argmax(), ppo.CHAR_INDEX['^'])
        self.assertEqual(cells[3 * 9 + 7].argmax(), ppo.CHAR_INDEX['T'])
        self.assertEqual(cells[0].argmax(), ppo.CHAR_INDEX['.'])
        b = ppo.N_CELLS * n
        np.testing.assert_allclose(v[b:b + 4], np.array([9, 5, 3, 7]) / 9, rtol=1e-6)
        inv = v[b + 4:b + 4 + ppo.N_ITEMS]
        want = np.zeros(ppo.N_ITEMS); want[ppo.ITEM_INDEX['wood']] = 3 / 9; want[ppo.ITEM_INDEX['wpk']] = 1 / 9
        np.testing.assert_allclose(inv, want, rtol=1e-6)
        self.assertEqual(list(v[-2:]), [1.0, 1.0])
        v2 = ppo.parse_obs(HAND.replace(' zz dark', '').replace('wood3 wpk1', 'none'))
        self.assertEqual(list(v2[-2:]), [0.0, 0.0])
        self.assertEqual(v2[b + 4:b + 4 + ppo.N_ITEMS].sum(), 0)


class TrainSmokeTest(unittest.TestCase):

    def test_smoke_and_policy(self):
        with tempfile.TemporaryDirectory() as d:
            res = ppo.train(3000, d, seed=0, threads=2)
            self.assertGreaterEqual(res['steps'], 3000)
            self.assertTrue(os.path.exists(f'{d}/ppo.pt'))
            rows = [json.loads(l) for l in open(f'{d}/log.jsonl')]
            self.assertEqual(len(rows), 3)
            pol = ppo.load_policy(f'{d}/ppo.pt')
            from game.crafter_text import TextEnv, parse_action
            e = TextEnv(seed=5_000_001, length=50)
            txt = e.reset()
            words = pol([txt, txt, txt])
            self.assertEqual(len(words), 3)
            self.assertTrue(all(parse_action(w) is not None for w in words))
            eps = play.play(pol, [5_000_002], [[1, 2]], 0.0, 30)
            self.assertEqual(eps[0]['sources']['invalid'], 0)
            self.assertFalse(pol.samples)
            self.assertEqual(eps[0]['unlocks'], play.play(pol, [5_000_002], [[1, 2]], 0.0, 30)[0]['unlocks'])
            sp = ppo.load_policy(f'{d}/ppo.pt', sample=True)
            self.assertTrue(sp.samples)
            run = lambda act: [s[1] for s in play.play(sp, [5_000_002], [act], 0.0, 30, log_steps=True)[0]['steps']]
            self.assertEqual(run([1, 2]), run([1, 2]))
            self.assertNotEqual(run([1, 2]), run([9, 9]))
            self.assertEqual(sp([txt], [0.0]), sp([txt], [0.0]))

    def test_save_every(self):
        with tempfile.TemporaryDirectory() as d:
            ppo.train(3000, d, seed=0, threads=1, save_every=1024)
            rows = [json.loads(l) for l in open(f'{d}/log.jsonl')]
            saves = [r for r in rows if r.get('event') == 'save']
            self.assertGreaterEqual(len(saves), 2)
            for r in saves:
                self.assertTrue(os.path.exists(r['path']))
                self.assertEqual(r['path'], f"{d}/ppo_steps_{r['steps']}.pt")
            self.assertEqual(sorted(f for f in os.listdir(d) if f.startswith('ppo_steps_')),
                             sorted(os.path.basename(r['path']) for r in saves))
            self.assertTrue(os.path.exists(f'{d}/ppo.pt'))
            pol = ppo.load_policy(saves[0]['path'])
            from game.crafter_text import TextEnv
            txt = TextEnv(seed=5_000_001, length=50).reset()
            self.assertEqual(len(pol([txt])), 1)


if __name__ == '__main__':
    unittest.main()
