"""Tests for the policy-gradient night (game/pg.py, play.move_logprobs_grad, mode.pg_day). Run: python -m unittest game.tests.test_pg

Model-free tests use hand-made tensors; the model tests use the real T1SDR checkpoint (skipped if missing).
"""
import json
import math
import os
import tempfile
import unittest
from unittest import mock

import numpy as np
import torch

from game import audit, mode, pg, play, score
from game.crafter_text import TextEnv

CKPT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'
EXPLORE = 0.1


class PureMath(unittest.TestCase):
    def test_normalise(self):
        a = pg.normalise(np.array([1., 2, 3, 10]))
        self.assertAlmostEqual(a.mean(), 0, places=9)
        self.assertAlmostEqual(a.std(), 1, places=6)

    def test_mixture_sums_to_one_and_matches_numpy(self):
        z = np.random.default_rng(0).normal(size=(5, 17)) * 3
        t = pg.mix_logp(torch.tensor(z), EXPLORE).exp()
        self.assertTrue(np.allclose(t.sum(-1).numpy(), 1))
        self.assertTrue(np.allclose(t.numpy(), np.exp(pg.mix_logp(z, EXPLORE))))
        self.assertTrue((t.numpy() >= EXPLORE / 17 - 1e-12).all())

    def test_ppo_step_moves_odds_toward_good_move_and_away_from_bad(self):
        torch.manual_seed(0)
        logits = torch.zeros(2, 17, requires_grad=True)       # two states, uniform odds
        acts = torch.tensor([3, 5])
        adv = torch.tensor([1.0, -1.0])
        log_mu = pg.mix_logp(logits.detach(), EXPLORE).gather(1, acts[:, None]).squeeze(1)
        loss, ratio, _, _ = pg.ppo_loss(logits, acts, adv, log_mu, EXPLORE)
        self.assertTrue(torch.allclose(ratio, torch.ones(2)))
        loss.backward()
        with torch.no_grad():
            new = logits - 0.5 * logits.grad
        before = torch.softmax(logits.detach(), -1)
        after = torch.softmax(new, -1)
        self.assertGreater(after[0, 3], before[0, 3])
        self.assertLess(after[1, 5], before[1, 5])


@unittest.skipUnless(os.path.exists(CKPT), 'T1SDR checkpoint missing')
class WithModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from custom_io.models import load_model
        from domain import mode as dm
        torch.set_num_threads(2)
        cls.m = load_model(CKPT).eval()
        cls.addon = dm.AddOn(cls.m, 8, 16, seed=1)
        cls.addon.on = True
        g = torch.Generator().manual_seed(5)
        with torch.no_grad():
            for _, _, A, B in cls.addon.layers:
                B.copy_(torch.randn(B.shape, generator=g))   # a non-trivial add-on; the parent alone is one-hot over the 17 words (gradients ~0)
        cls.views = [TextEnv(seed=1_000_000 + i, length=50).reset() for i in range(12)]

    def test_grad_logprobs_equal_no_grad(self):
        ref = play.move_logprobs(self.m, self.views, bs=64)
        with torch.no_grad():
            nog = play.move_logprobs_grad(self.m, self.views).double().numpy()
        self.assertTrue(np.array_equal(ref, nog))
        g = play.move_logprobs_grad(self.m, self.views)
        self.assertTrue(g.requires_grad)
        self.assertTrue(np.array_equal(ref, g.detach().double().numpy()))
        g.sum().backward()
        self.assertTrue(any(B.grad is not None and B.grad.abs().sum() > 0 for _, _, _, B in self.addon.layers))
        self.assertTrue(all(not p.requires_grad for p in self.m.parameters() if all(p is not t for t in self.addon.params())))
        for t in self.addon.params():
            t.grad = None

    def test_first_minibatch_ratio_is_one_and_pass_moves_toward_good_move(self):
        views = self.views[:4]
        old = play.move_logprobs(self.m, views)
        acts = [int(np.argsort(r)[-2]) for r in old[:2]] + [int(np.argmax(r)) for r in old[2:]]   # good moves: 2nd choice; bad: top
        adv = np.array([1.5, 1.5, -1.5, -1.5])
        snap = self.addon.snapshot()
        try:
            st, losses = pg.night(self.m, self.addon, views, acts, adv, EXPLORE, seed=3, passes=1, minibatch=4, lr=2e-3)
            self.assertLess(st['first_minibatch']['ratio_max_dev'], 1e-4)
            self.assertEqual(st['first_minibatch']['clipped'], 0.0)
            self.assertEqual(st['clipped_fraction'], 0.0)
            new = play.move_logprobs(self.m, views)
            lp = lambda z: pg.mix_logp(z, EXPLORE)[np.arange(4), acts]
            d = lp(new) - lp(old)
            self.assertGreater(d[:2].mean(), 0)
            self.assertLess(d[2:].mean(), 0)
            # deterministic for the seed
            self.addon.restore(snap)
            st2, losses2 = pg.night(self.m, self.addon, views, acts, adv, EXPLORE, seed=3, passes=1, minibatch=4, lr=2e-3)
            self.assertEqual(losses, losses2)
        finally:
            self.addon.restore(snap)


class Temperature(unittest.TestCase):
    def test_bisection_hits_target_entropy(self):
        rng = np.random.default_rng(1)
        lp = rng.normal(size=(300, 17)) * 25 - 40      # sharply peaked rows, like the parent's
        lp -= np.log(np.exp(lp).sum(-1, keepdims=True))
        for target in (math.log(17) / 2, 0.3, 2.0):
            T, ent = pg.find_temp(lp, target)
            self.assertLess(abs(ent - target), 1e-3)
            self.assertLess(abs(pg.entropy(lp, T) - target), 1e-3)
        T, _ = pg.find_temp(lp)
        self.assertGreater(T, 1.0)

    def test_temp_one_reproduces_old_sample_picker(self):
        rng = np.random.default_rng(2)
        def old(scores, u):
            p = np.exp(scores - scores.max())
            c = np.cumsum(p)
            return int(min(np.searchsorted(c, u * c[-1], side='right'), len(p) - 1))
        for _ in range(500):
            sc, u = rng.normal(size=17) * 5, rng.random()
            self.assertEqual(play.softmax_pick(sc, u), old(sc, u))
            self.assertEqual(play.softmax_pick(sc, u, 1.0), old(sc, u))
        table = lambda m, prompts, bs=64: np.array([np.random.default_rng(len(p)).normal(size=17) * 3 for p in prompts])
        prompts = [f'view {i}' * (i + 1) for i in range(20)]
        us = list(rng.random(20))
        with mock.patch.object(play, 'move_logprobs', table):
            a = play.move_policy(None, 'sample')(prompts, us)
            b = play.move_policy(None, 'sample', temp=1.0)(prompts, us)
            c = play.move_policy(None, 'sample', temp=50.0)(prompts, us)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_logT_gets_gradient_and_moves_the_right_way(self):
        torch.manual_seed(0)
        logits = torch.randn(32, 17) * 4
        acts = torch.randint(0, 17, (32,))
        logT = torch.tensor(0.5, requires_grad=True)
        log_mu = pg.mix_logp(logits, EXPLORE, math.exp(0.5)).gather(1, acts[:, None]).squeeze(1)
        adv = torch.randn(32)
        loss, ratio, _, _ = pg.ppo_loss(logits, acts, adv, log_mu, EXPLORE, logT=logT)
        self.assertTrue(torch.allclose(ratio, torch.ones(32), atol=1e-5))
        loss.backward()
        self.assertIsNotNone(logT.grad)
        self.assertGreater(float(logT.grad.abs()), 0)

    def test_score_picks_up_policy_temp(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as e:
            ck = os.path.join(d, 'checkpoint.pt')
            self.assertEqual(score.resolve_temp(ck, 'sample'), 1.0)            # no file: old behaviour
            json.dump(dict(T=3.5), open(os.path.join(d, 'policy_temp.json'), 'w'))
            self.assertEqual(score.resolve_temp(ck, 'sample'), 3.5)            # the checkpoint's folder
            self.assertEqual(score.resolve_temp(ck, 'top'), 1.0)               # not a sample run
            json.dump(dict(T=7.0), open(os.path.join(e, 'policy_temp.json'), 'w'))
            self.assertEqual(score.resolve_temp(ck, 'sample', temp_from=e), 7.0)
            self.assertEqual(score.resolve_temp(ck, 'sample', temp=2.0), 2.0)
            with self.assertRaises(AssertionError):
                score.resolve_temp(ck, 'top', temp=2.0)
            with self.assertRaises(AssertionError):
                score.resolve_temp(ck, 'sample', temp_from=os.path.join(e, 'nope'))


class PgDay(unittest.TestCase):
    def test_pg_day_drops_asleep_normalises_and_logs_every_move(self):
        seeds, acts = mode.world_seeds(200, 1, 2)
        eps = play.play(None, seeds, acts, 0.0, 30, log_steps=True)

        class G:
            def day(self, day, eps):
                n = sum(e['length'] for e in eps)
                return np.arange(n, dtype=float), dict(moves=n)
        logged = []
        rows, prompts, a, norm, by_src, dropped, info = mode.pg_day(None, eps, {}, 1, lambda **kw: logged.append(kw), G())
        self.assertEqual(len(rows), sum(e['length'] for e in eps) - dropped)
        self.assertEqual(len(logged), len(rows))
        self.assertAlmostEqual(float(norm.mean()), 0, places=6)
        self.assertTrue(all(r['kept_by'] == 'pg' and r['steps'] == [] for r in logged))
        self.assertTrue(all(play.WORDS[i] == r['answer'] for i, r in zip(a, logged)))


class AuditPg(unittest.TestCase):
    def _events(self, world, **over):
        row = dict(event='row', kind='game', id='x', day=1, world_seed=world, step=40, unlock=None, unlock_step=None,
                   steps=[], answer='noop', source='own', kept_by='pg', advantage=0.3)
        row.update(over)
        start = dict(event='start', seed=200, domain_constants_sha256=audit.sha256_file(audit.DOMAIN_CONST),
                     game_constants_sha256=audit.sha256_file(play.CONST_PATH))
        return [start, row]

    def test_accepts_pg_row(self):
        self.assertTrue(audit.audit_events(self._events(play.practice_seed(200, 1, 3)))['ok'])

    def test_rejects_pg_row_on_sealed_world(self):
        rep = audit.audit_events(self._events(7_000_000))
        self.assertFalse(rep['ok'])
        self.assertTrue(rep['proved_wrong'])


class Cli(unittest.TestCase):
    def test_default_night_is_copy_and_pg_needs_guess_and_sample(self):
        self.assertEqual(mode.parse_args(['--parent', 'p', '--out', 'o', '--seed', '1']).night, 'copy')
        with self.assertRaises(AssertionError):
            mode.main(['--parent', 'p', '--out', '/tmp/none-pg', '--seed', '1', '--night', 'pg'])


if __name__ == '__main__':
    unittest.main()
