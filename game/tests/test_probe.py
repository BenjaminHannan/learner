"""Tests for game/probe.py (GW-L). Run: python -m unittest game.tests.test_probe

gen runs on practice worlds only (smoke size); train/eval use the real T1SDR parent (skipped if missing).
"""
import json
import os
import tempfile
import unittest

from game import oracle, play, probe

PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'


def lines(path):
    with open(path) as f:
        return [json.loads(x) for x in f]


class Pure(unittest.TestCase):
    def test_default_epochs(self):
        self.assertEqual([probe.default_epochs(n) for n in (1000, 4000, 16000)], [40, 20, 10])
        self.assertEqual([probe.default_epochs(n) for n in (64, 1001, 4001, 64000)], [40, 20, 10, 10])

    def test_best_fixed_word_ties_to_lowest_index(self):
        rows = [dict(label=w) for w in ('up', 'left', 'up', 'left', 'do')]
        self.assertEqual(probe.best_fixed(rows), 'left')
        self.assertIsNone(probe.best_fixed([]))

    def test_episode_is_deterministic_and_uses_labeller_words(self):
        seed = play.practice_seed(probe.TRAIN_RUN, 0, 0)
        a, b = probe.episode(seed, 60), probe.episode(seed, 60)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 60)
        self.assertTrue(all((w, r) == oracle.label(v) for v, w, r in a))

    def test_sealed_seed_refused(self):
        with self.assertRaises(AssertionError):
            probe.episode(play.SEALED_BASE, 10)


class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.data = os.path.join(cls.td.name, 'data')
        cls.info = probe.gen(cls.data, smoke=True)

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def test_gen_bigger_train_with_the_same_heldout(self):
        out = os.path.join(self.td.name, 'data-big')
        probe.gen(out, smoke=True, train_views=300, reuse_heldout=self.data)
        tr, ho = lines(os.path.join(out, 'train.jsonl')), lines(os.path.join(out, 'heldout.jsonl'))
        self.assertEqual(ho, lines(os.path.join(self.data, 'heldout.jsonl')))
        self.assertEqual(len(tr), 300)
        self.assertEqual(len({r['view'] for r in tr}), 300)
        self.assertFalse({r['view'] for r in tr} & {r['view'] for r in ho})
        for r in tr:
            self.assertEqual((r['label'], r['reason']), oracle.label(r['view']))

    def test_gen(self):
        tr, ho = lines(os.path.join(self.data, 'train.jsonl')), lines(os.path.join(self.data, 'heldout.jsonl'))
        self.assertEqual((len(tr), len(ho)), (200, 40))
        self.assertEqual(len({r['view'] for r in tr}), 200)
        self.assertEqual(len({r['view'] for r in ho}), 40)
        self.assertFalse({r['view'] for r in tr} & {r['view'] for r in ho})
        for r in tr + ho:
            self.assertEqual((r['label'], r['reason']), oracle.label(r['view']))
            self.assertIn(r['label'], play.WORDS)
        seeds = self.info['train']['seeds'] + self.info['heldout']['seeds']
        self.assertTrue(seeds and not any(play.is_sealed(s) for s in seeds))
        self.assertTrue(all(1_000_000 + 390 * 10_000 <= s < 1_000_000 + 391 * 10_000 for s in self.info['train']['seeds']))
        self.assertTrue(all(1_000_000 + 391 * 10_000 <= s < 1_000_000 + 392 * 10_000 for s in self.info['heldout']['seeds']))
        with open(os.path.join(self.data, 'gen.json')) as f:
            g = json.load(f)
        self.assertEqual(sum(g['train']['labels'].values()), 200)
        self.assertEqual(sum(g['heldout']['reasons'].values()), 40)

    def test_gen_is_reproducible(self):
        with tempfile.TemporaryDirectory() as td:
            probe.gen(td, smoke=True)
            for name in ('train.jsonl', 'heldout.jsonl'):
                with open(os.path.join(td, name)) as f, open(os.path.join(self.data, name)) as g:
                    self.assertEqual(f.read(), g.read())

    @unittest.skipUnless(os.path.exists(PARENT), 'parent checkpoint not available')
    def test_train_and_eval(self):
        from custom_io.models import load_model
        out = os.path.join(self.td.name, 'run')
        probe.main(['train', '--parent', PARENT, '--data', self.data, '--n', '64', '--epochs', '1', '--seed', '200',
                    '--out', out, '--threads', '3'])
        with open(os.path.join(out, 'train.json')) as f:
            tj = json.load(f)
        self.assertEqual((tj['n'], tj['epochs'], tj['seed'], tj['updates'], tj['parent']), (64, 1, 200, 1, PARENT))
        self.assertEqual(len(tj['per_epoch']), 1)
        self.assertGreater(tj['per_epoch'][0]['loss'], 0)
        ck = os.path.join(out, 'checkpoint.pt')
        self.assertTrue(os.path.exists(ck))
        load_model(ck).eval()
        ev = os.path.join(self.td.name, 'eval.json')
        probe.main(['eval', '--ckpt', ck, '--ckpt', PARENT, '--names', 'tuned', 'parent', '--data', self.data,
                    '--train-n', '64', '--out', ev, '--threads', '3'])
        with open(ev) as f:
            res = json.load(f)
        self.assertEqual(res['heldout'], 40)
        self.assertEqual(set(res['checkpoints']), {'tuned', 'parent'})
        ho = lines(os.path.join(self.data, 'heldout.jsonl'))
        self.assertEqual(res['subset'], sum(r['reason'] in ('nav', 'act') for r in ho))
        for r in res['checkpoints'].values():
            self.assertTrue(0 <= r['accuracy_all'] <= 1 and 0 <= r['accuracy_subset'] <= 1)
            self.assertLessEqual(len(r['top_confusions_subset']), 5)
        self.assertIn(res['baseline']['word_subset'], play.WORDS)


if __name__ == '__main__':
    unittest.main()
