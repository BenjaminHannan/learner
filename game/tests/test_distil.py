"""Tests for the distil day (game/distil.py, audit of kept_by 'distil'). Run: python -m unittest game.tests.test_distil

Model-free tests patch play.move_logprobs; the model test uses the real T1SDR checkpoint (skipped if missing).
"""
import os
import unittest
from unittest import mock

import numpy as np
import torch

from game import audit, distil, play
from game.crafter_text import TextEnv

CKPTS = ['/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt',
         '/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/inputs/T1SDR_s200/checkpoint.pt']


def ckpt():
    for p in CKPTS:
        try:
            if os.path.exists(p):
                return p
        except OSError:
            pass
    return None


class Pure(unittest.TestCase):
    def test_targets_rows_sum_to_one_and_equal_softmax_over_T0(self):
        lp = np.random.default_rng(0).normal(size=(6, 17)) * 8 - 20
        with mock.patch.object(play, 'move_logprobs', lambda m, v, bs=64: lp):
            p = distil.targets(None, ['v'] * 6, 4.0)
        z = np.exp(lp / 4.0)
        self.assertTrue(np.allclose(p.sum(-1), 1))
        self.assertTrue(np.allclose(p, z / z.sum(-1, keepdims=True)))
        self.assertEqual(p.dtype, np.float64)

    def test_kl(self):
        p = np.array([[0.5, 0.5, 0.0], [1.0, 0.0, 0.0]])
        self.assertEqual(distil.kl(p, np.log(p.clip(1e-300))), 0.0)
        q = np.log(np.array([[0.25, 0.75, 0.0], [0.5, 0.25, 0.25]]).clip(1e-300))
        hand = (0.5 * np.log(2) + 0.5 * np.log(2 / 3) + np.log(2)) / 2
        self.assertAlmostEqual(distil.kl(p, q), hand, places=9)
        self.assertAlmostEqual(float(distil.kl_torch(torch.tensor(p), torch.tensor(q))), hand, places=9)


@unittest.skipUnless(ckpt(), 'T1SDR checkpoint missing')
class WithModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from custom_io.models import load_model
        from domain import mode as dm
        torch.set_num_threads(1)
        cls.m = load_model(ckpt()).eval()
        cls.addon = dm.AddOn(cls.m, 8, 16, seed=1)
        cls.addon.on = True
        g = torch.Generator().manual_seed(5)
        with torch.no_grad():
            for _, _, A, B in cls.addon.layers:
                B.copy_(torch.randn(B.shape, generator=g))   # non-trivial add-on, as test_pg
        cls.views = [TextEnv(seed=1_000_000 + i, length=50).reset() for i in range(20)]
        cls.p = distil.targets(cls.m, cls.views, 20.0)

    def test_run_lowers_heldout_kl_and_is_deterministic(self):
        snap = self.addon.snapshot()
        try:
            held = [self.views[i] for i in np.random.default_rng(3).permutation(20)[:2]]
            hp = self.p[np.random.default_rng(3).permutation(20)[:2]]
            before, _ = distil.heldout(self.m, held, hp)
            with mock.patch.object(distil, 'MAX_PASSES', 3), mock.patch.object(distil, 'KL_STOP', -1.0):
                st, losses = distil.run(self.m, self.addon, self.views, self.p, seed=3)
                after, _ = distil.heldout(self.m, held, hp)
                self.addon.restore(snap)
                st2, losses2 = distil.run(self.m, self.addon, self.views, self.p, seed=3)
            self.assertLess(after, before)
            for k in ('passes', 'train_kl_per_pass', 'heldout_kl_per_pass', 'heldout_kl', 'heldout_entropy', 'n_train', 'n_heldout',
                      'updates', 'seconds'):
                self.assertIn(k, st)
            self.assertEqual((st['n_train'], st['n_heldout'], st['passes']), (18, 2, 3))
            self.assertEqual(st['heldout_kl_per_pass'], st2['heldout_kl_per_pass'])
            self.assertEqual(losses, losses2)
        finally:
            self.addon.restore(snap)


class AuditDistil(unittest.TestCase):
    def _events(self, world):
        row = dict(event='row', kind='game', id='distil_0', day=50, world_seed=world, step=7, unlock=None, unlock_step=None,
                   steps=[], answer='noop', source='own', kept_by='distil')
        start = dict(event='start', seed=200, domain_constants_sha256=audit.sha256_file(audit.DOMAIN_CONST),
                     game_constants_sha256=audit.sha256_file(play.CONST_PATH))
        return [start, row]

    def test_accepts_distil_row_on_day_50(self):
        self.assertTrue(audit.audit_events(self._events(play.practice_seed(200, 50, 5)))['ok'])

    def test_refuses_quiz_world(self):
        rep = audit.audit_events(self._events(play.practice_seed(200, 0, 5)))
        self.assertFalse(rep['ok'])
        self.assertTrue(rep['proved_wrong'])


if __name__ == '__main__':
    unittest.main()
