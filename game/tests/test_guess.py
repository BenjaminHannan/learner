import unittest
from unittest import mock

import numpy as np
import torch

from game import audit, guess, mode, play
from game.ppo import OBS_DIM, parse_obs


def episode(seed, views, rewards):
    return dict(seed=seed, act_seed=[0, 0, 0], steps=[(v, 'noop', 'own', r) for v, r in zip(views, rewards)], unlocks=[], end='cap')


class GaeTest(unittest.TestCase):

    def test_hand_computation(self):
        r, v = [0.0, 1.0, 2.0], [0.5, 1.0, 0.25]
        g, l = 0.99, 0.95
        d2 = 2.0 - 0.25
        d1 = 1.0 + g * 0.25 - 1.0
        d0 = 0.0 + g * 1.0 - 0.5
        a2 = d2
        a1 = d1 + g * l * a2
        a0 = d0 + g * l * a1
        np.testing.assert_allclose(guess.gae(r, v), [a0, a1, a2])

    def test_returns(self):
        np.testing.assert_allclose(guess.discounted_returns([1.0, 0.0, 2.0]), [1 + 0.99 ** 2 * 2, 0.99 * 2, 2.0])

    def test_spearman(self):
        self.assertAlmostEqual(guess.spearman([1, 2, 3, 4], [10, 20, 25, 90]), 1.0)
        self.assertAlmostEqual(guess.spearman([1, 2, 3], [3, 2, 1]), -1.0)
        self.assertIsNone(guess.spearman([1, 1, 1], [1, 2, 3]))


class SelectTest(unittest.TestCase):

    def test_exactly_n_awake_highest_deterministic(self):
        adv = [0.1, 0.9, 0.5, 0.9, 0.7, 0.2]
        keys = [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        awake = [True, True, True, False, True, True]
        a = guess.select(adv, keys, awake, 3)
        self.assertEqual(a, [1, 2, 4])
        self.assertEqual(a, guess.select(adv, keys, awake, 3))

    def test_tie_by_key_and_short(self):
        adv = [0.5, 0.5, 0.5]
        keys = [(2, 0), (1, 5), (1, 3)]
        self.assertEqual(guess.select(adv, keys, [True] * 3, 2), [1, 2])
        self.assertEqual(guess.select(adv, keys, [True, False, False], 5), [0])

    def test_day_selection_on_real_episodes(self):
        seeds, acts = mode.world_seeds(200, 1, 3)
        eps = play.play(None, seeds, acts, 0.0, 25, log_steps=True)
        g = guess.Guesser(200)
        adv, info = g.day(1, eps)
        n = sum(len(e['steps']) for e in eps)
        self.assertEqual(len(adv), n)
        keys, awake = guess.episode_moves(eps, True)
        pick = guess.select(adv, keys, awake, 10)
        self.assertEqual(len(pick), 10)
        self.assertTrue(all(awake[i] for i in pick))
        self.assertIsNone(info['rank_corr'])
        g2 = guess.Guesser(200)
        adv2, _ = g2.day(1, eps)
        np.testing.assert_allclose(adv, adv2)
        _, info2 = g.day(2, eps)
        self.assertIn('rank_corr', info2)


class RndTest(unittest.TestCase):

    def test_unseen_view_is_more_novel(self):
        seeds, acts = mode.world_seeds(200, 1, 2)
        eps = play.play(None, seeds, acts, 0.0, 12, log_steps=True)
        seen = torch.from_numpy(np.stack([parse_obs(st[0]) for e in eps for st in e['steps']]))[:8]
        other = play.play(None, [seeds[0] + 1000], [[1, 2, 3]], 0.0, 3, log_steps=True)
        new = torch.from_numpy(parse_obs(other[0]['steps'][0][0]))[None]
        g = guess.Guesser(5)
        for _ in range(300):
            loss = ((g.pred(seen) - g.target(seen)) ** 2).mean()
            g.opt_pred.zero_grad(); loss.backward(); g.opt_pred.step()
        self.assertGreater(g.errors(new)[0], 3 * g.errors(seen).mean())
        c = g.curiosity(torch.cat([seen, new]))
        self.assertGreater(c[-1], c[:-1].max())


class WindowRowsTest(unittest.TestCase):

    def test_window_rows_have_no_guess_fields(self):
        seeds, acts = mode.world_seeds(200, 1, 2)
        eps = play.play(None, seeds, acts, 0.0, 30, log_steps=True)
        eps[0]['unlocks'], eps[1]['unlocks'] = [(20, 'collect_wood')], []
        logged = []
        with mock.patch.object(mode.dm, 'make_row', lambda m, fam, p, w, steps, cons, src, allow_zero: (dict(id=p[:5]), None)):
            rows, _, by_name, _, _ = mode.keep_rows(None, eps, {'credit_window': 8}, 1, lambda **kw: logged.append(kw))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all('kept_by' not in r and r['unlock'] == 'collect_wood' and r['unlock_step'] == 20 for r in logged))


class AuditGuessTest(unittest.TestCase):

    def _events(self, world, day=1, **over):
        row = dict(event='row', kind='game', id='x', day=day, world_seed=world, step=40, unlock=None, unlock_step=None,
                   steps=[], answer='noop', source='own', kept_by='guess', advantage=0.3)
        row.update(over)
        start = dict(event='start', seed=200, domain_constants_sha256=audit.sha256_file(audit.DOMAIN_CONST),
                     game_constants_sha256=audit.sha256_file(play.CONST_PATH))
        return [start, row]

    def test_accepts_guess_row(self):
        w = play.practice_seed(200, 1, 3)
        rep = audit.audit_events(self._events(w))
        self.assertTrue(rep['ok'], rep['problems'])

    def test_rejects_sealed_world_guess_row(self):
        rep = audit.audit_events(self._events(7_000_000))
        self.assertFalse(rep['ok'])
        self.assertTrue(rep['proved_wrong'])

    def test_window_row_still_checked(self):
        w = play.practice_seed(200, 1, 3)
        rep = audit.audit_events(self._events(w, kept_by=None, unlock='a', unlock_step=10, step=40))
        self.assertFalse(rep['ok'])
        rep = audit.audit_events(self._events(w, kept_by=None, unlock='a', unlock_step=40, step=40))
        self.assertTrue(rep['ok'])


if __name__ == '__main__':
    unittest.main()
