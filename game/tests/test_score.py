"""Tests for game/score.py, game/analyze.py and game/audit.py. Run: python -m unittest game.tests.test_score

Rules and audit use synthetic data; the score runs use the real parent checkpoint (if present) with --worlds 2 and the
hidden --cap 20 (tests only).
"""
import json
import math
import os
import tempfile
import unittest

from game import analyze, audit, play, score

PARENT = '/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'


def arm(name, vals, pick=0.0):
    pw = [dict(seed=play.SEALED_BASE + k, unlocks=[], n_unlocks=v, length=10, end='cap',
               sources=dict(own=5, explore=5, invalid=0), ach_rate={a: 0.0 for a in score.ACH}) for k, v in enumerate(vals)]
    for w in pw:
        w['ach_rate']['make_wood_pickaxe'] = 1.0 if w['seed'] - play.SEALED_BASE < pick else 0.0
    return score.summarize(name, None, pw, 1000, 1.0)


def write(path, obj):
    with open(path, 'w') as f:
        json.dump(obj, f)


class Rules(unittest.TestCase):
    def test_gw1(self):
        self.assertEqual(analyze.gw1_rule(1.6, 0.2)['verdict'], 'PASS')
        self.assertEqual(analyze.gw1_rule(1.6, -0.1)['verdict'], 'FAIL')
        self.assertEqual(analyze.gw1_rule(1.0, 0.5)['verdict'], 'FAIL')
        self.assertEqual(analyze.gw1_rule(0.4, 0.1)['verdict'], 'PROVED WRONG')
        r = analyze.gw1_rule(1.495, 0.3)
        self.assertEqual((r['verdict'], r['hair_miss_used']), ('PASS', True))

    def test_gw2(self):
        for s, v in [(10, 'PASS'), (9.2, 'PASS'), (5, 'FAIL'), (2, 'PROVED WRONG'), (0, 'PROVED WRONG')]:
            self.assertEqual(analyze.gw2_rule(s)['verdict'], v, s)

    def test_gw3(self):
        for e, hi, v in [(0.5, 1, 'PASS'), (-0.005, 0.5, 'PASS'), (-0.5, 0.2, 'FAIL'), (-1.2, 0.1, 'FAIL'),
                         (-1.2, -0.3, 'PROVED WRONG')]:
            self.assertEqual(analyze.gw3_rule(e, hi)['verdict'], v, (e, hi))

    def test_gw4(self):
        ok = dict(in_dist_drop=1.0, fired=[], passes=True)
        self.assertEqual(analyze.gw4_rule(ok)['verdict'], 'PASS')
        self.assertEqual(analyze.gw4_rule(dict(ok, in_dist_drop=3.0, passes=False))['verdict'], 'FAIL')
        self.assertEqual(analyze.gw4_rule(dict(ok, in_dist_drop=5.5, passes=False))['verdict'], 'PROVED WRONG')

    def test_gw6(self):
        self.assertEqual(analyze.gw6_rule([5, 10, 12, 13])['verdict'], 'PASS')
        self.assertEqual(analyze.gw6_rule([5, 10, 12, 18])['verdict'], 'PROVED WRONG')     # rise 6 > 5
        self.assertEqual(analyze.gw6_rule([5, 10, 14, 12.5])['verdict'], 'PASS')
        self.assertEqual(analyze.gw6_rule([5, 10, 15, 11])['verdict'], 'FAIL')             # 4 below best
        self.assertEqual(analyze.gw6_rule([5, 15, 14, 13, 12, 8])['verdict'], 'PROVED WRONG')   # 4 past best, 7 below
        self.assertEqual(analyze.gw6_rule([5, 10, 12, 15.5])['verdict'], 'FAIL')         # rise 3.5, best-ok

    def test_bootstrap_paired(self):
        d, lo, hi = analyze.boot_diff([3, 3, 3, 3], [1, 1, 1, 1])
        self.assertEqual((d, lo, hi), (2.0, 2.0, 2.0))
        d, lo, hi = analyze.boot_diff([1, 2, 3, 4] * 25, [1, 1, 1, 1] * 25)
        self.assertTrue(lo < d < hi and abs(d - 1.5) < 1e-9)

    def test_crafter_score(self):
        self.assertAlmostEqual(score.crafter_score({a: 0.0 for a in score.ACH}), 0.0)
        self.assertAlmostEqual(score.crafter_score({a: 1.0 for a in score.ACH}), 100.0)   # exp(ln 101) - 1

    def test_summarize_crafter(self):
        pw = [dict(seed=1, unlocks=[], n_unlocks=2, length=10, end='cap', sources=dict(own=5, explore=5, invalid=0),
                   ach_rate={a: (1.0 if i < 2 and k == 0 else 0.0) for i, a in enumerate(score.ACH)}) for k in range(2)]
        r = score.summarize('x', None, pw, 100, 1.0)      # two achievements at 50% share, the rest 0
        self.assertAlmostEqual(r['crafter_score'], math.exp(2 * math.log(51) / 22) - 1)


def tiny_log(seed=3, bad=None):
    sd, cons = audit.sha256_file(audit.DOMAIN_CONST), audit.sha256_file(play.CONST_PATH)
    ev = [dict(event='start', seed=seed, constants_sha256=sd, game_constants_sha256=cons),
          dict(event='row', kind='diary', source='diary', id='d0', day=0, prompt='x', answer='y', steps=[])]
    for i, t in enumerate((10, 12)):
        ev.append(dict(event='row', kind='game', id=f'g{i}', day=2, source='own', prompt='p', answer='do', steps=[],
                       world_seed=play.practice_seed(seed, 2, 5), act_seed=[seed, 2, 5], step=t, unlock='collect_wood',
                       unlock_step=12))
    if bad:
        ev[-1].update(bad)
    return ev


class Audit(unittest.TestCase):
    def test_clean(self):
        rep = audit.audit_events(tiny_log())
        self.assertTrue(rep['ok'], rep['problems'])
        self.assertEqual(rep['by_source'], {'diary': 1, 'own': 2})

    def test_problems(self):
        sealed = audit.audit_events(tiny_log(bad=dict(world_seed=play.SEALED_BASE + 3)))
        self.assertTrue(sealed['proved_wrong'] and not sealed['ok'])
        quiz = audit.audit_events(tiny_log(bad=dict(world_seed=play.practice_seed(3, 0, 4))))
        self.assertTrue(quiz['proved_wrong'])
        late = audit.audit_events(tiny_log(bad=dict(step=3)))      # outside the credit window, not proved wrong
        self.assertTrue(not late['ok'] and not late['proved_wrong'])
        far = audit.audit_events(tiny_log(bad=dict(world_seed=play.practice_seed(3, 2, 80), act_seed=[3, 2, 80])))
        self.assertTrue(not far['ok'] and not far['proved_wrong'])      # world i=80 >= episodes_per_day
        for bad in (dict(answer='jump'), dict(source='tool'), dict(steps=['a']), dict(day=3)):
            rep = audit.audit_events(tiny_log(bad=bad))
            self.assertFalse(rep['ok'], bad)
        ev = tiny_log()
        ev[0]['game_constants_sha256'] = 'abc'
        rep = audit.audit_events(ev)
        self.assertTrue(rep['constants_changed'] and rep['proved_wrong'])


class Analyze(unittest.TestCase):
    def test_end_to_end_without_models(self):
        with tempfile.TemporaryDirectory() as td:
            run, nd = os.path.join(td, 'run'), os.path.join(td, 'nights')
            os.makedirs(run), os.makedirs(nd)
            with open(os.path.join(run, 'log.jsonl'), 'w') as f:
                f.write('\n'.join(json.dumps(e) for e in tiny_log()) + '\n')
            write(os.path.join(run, 'summary.json'), dict(nights_run=2, stop_reason='rise', quiz_history=[1, 3, 4],
                                                          rows_per_night=[10, 12], game_steps=100, quiz_steps=50))
            before, after = arm('model', [0] * 100), arm('model', [2] * 100, pick=15)
            rnd, ppo = arm('random', [1] * 100), arm('ppo', [1] * 100)
            paths = {}
            for n, x in dict(before=before, after=after, random=rnd, ppo=ppo).items():
                paths[n] = os.path.join(td, n + '.json')
                write(paths[n], x)
            for k, v in enumerate((0, 1.0, 1.5)):
                write(os.path.join(nd, f'night_{k}.json'), arm('m', [v] * 50))
            out = os.path.join(td, 'out')
            analyze.main(['--run', run, '--parent', 'none', '--before', paths['before'], '--after', paths['after'],
                              '--random', paths['random'], '--ppo', paths['ppo'], '--nights-dir', nd, '--out', out])
            with open(os.path.join(out, 'RESULT.json')) as f:
                res = json.load(f)
            m = res['marks']
            self.assertEqual(m['GW1']['verdict'], 'PASS')
            self.assertEqual(m['GW2']['verdict'], 'PASS')
            self.assertEqual(m['GW3']['verdict'], 'PASS')
            self.assertEqual(m['GW4']['verdict'], 'UNSCORED')
            self.assertEqual(m['GW5']['verdict'], 'PASS')
            self.assertEqual(m['GW6']['verdict'], 'PASS')   # 0, 4.5, 6.8: last is best, rise 2.3
            self.assertTrue(os.path.exists(os.path.join(out, 'RESULT.md')))


class OracleArm(unittest.TestCase):
    def test_oracle_arm(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 'oracle.json')
            score.main(['--arm', 'oracle', '--worlds', '2', '--cap', '30', '--out', p])
            with open(p) as f:
                res = json.load(f)
        self.assertEqual((res['arm'], res['worlds'], len(res['per_world'])), ('oracle', 2, 2))
        self.assertTrue(all(play.is_sealed(w['seed']) for w in res['per_world']))
        self.assertEqual(sum(res['sources_share'].values()), 1.0)
        self.assertEqual(res['sources_share']['invalid'], 0.0)
        self.assertGreater(res['sources_share']['own'], 0.8)


@unittest.skipUnless(os.path.exists(PARENT), 'parent checkpoint not available')
class Scoring(unittest.TestCase):
    def check(self, res, arm_name):
        self.assertEqual((res['arm'], res['worlds'], len(res['per_world'])), (arm_name, 2, 2))
        self.assertEqual(set(res['share']), set(score.ACH))
        self.assertTrue(all(play.is_sealed(w['seed']) for w in res['per_world']))
        self.assertAlmostEqual(res['progress'], 100 * res['mean_unlocks'] / 22)

    def test_random_and_model(self):
        with tempfile.TemporaryDirectory() as td:
            for name, extra in (('random', []), ('model', ['--ckpt', PARENT])):
                p = os.path.join(td, name + '.json')
                score.main(['--arm', name, '--worlds', '2', '--cap', '20', '--out', p] + extra)
                with open(p) as f:
                    res = json.load(f)
                self.check(res, name)
                if name == 'random':
                    self.assertEqual(res['sources_share']['explore'], 1.0)
                else:
                    self.assertAlmostEqual(sum(res['sources_share'].values()), 1.0)


if __name__ == '__main__':
    unittest.main()
