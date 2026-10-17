"""Tests for game/gwls_report.py, game/gwls_final.py and game/gwls_checks.py (GW-LS, draft pending coordinator review). Run: python -m unittest game.tests.test_gwls

No checkpoint and no game is played: synthetic round folders in a temp dir. Nothing here touches a sealed world (the final scorer's subprocess is mocked to fail if called).
"""
import contextlib
import gzip
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import torch

from game import census_ready, gwls_checks, gwls_final, gwls_report
from game.tests.test_imitate import _view

PLAIN = _view(table=(3, 0), items='none')                       # no table within one cell: never a ready state
READY = _view(table=(1, 0), items='wood1')


def nh_game(n_nonhabit, habit=('wake_up',)):
    names = [f'n{j}' for j in range(n_nonhabit)]
    first = {n: j for j, n in enumerate(names + list(habit))}
    n = len(first) + 1
    return dict(seed=1, views=[PLAIN] * n, actions=[0] * n, events=[(t, n_) for n_, t in first.items()], first=first, length=n, end='dead')


def write_round(d, k, games, chunks=4, extra=None):
    os.makedirs(d, exist_ok=True)
    per = len(games) // chunks
    for c in range(chunks):
        with gzip.open(os.path.join(d, f'play-{k}-{c}.json.gz'), 'wt') as f:
            json.dump(games[c * per:(c + 1) * per], f)
    it = dict(iteration=k, temp=1.0, games=len(games), mean_unlocks=round(sum(len(g['first']) for g in games) / len(games), 3), g_stone=10, g_pick=20,
              oracle_agreement_all_played=dict(views=5, agreement=0.4), oracle_agreement_kept=dict(views=5, agreement=0.5))
    it.update(extra or {})
    with open(os.path.join(d, f'iter-{k}.json'), 'w') as f:
        json.dump(it, f)


def row(r, nh_sum, ratio, games=400):
    return dict(round=r, games=games, nonhabit_sum=nh_sum, ratio_w_exact=ratio)


class Report(unittest.TestCase):
    def test_nonhabit_counts_first_unlocks_not_in_the_habit_set(self):
        games = [nh_game(3, habit=('wake_up', 'collect_sapling', 'place_plant', 'eat_plant')), nh_game(0, habit=()), nh_game(5)]
        self.assertEqual(gwls_report.nonhabit_count(games), 8)
        self.assertEqual(gwls_report.nonhabit_per_game(games), 8 / 3)                       # unrounded

    def test_nonhabit_is_not_taken_from_rounded_numbers(self):
        # 400 games, mean_unlocks stored to 3 decimals: the old formula (mean_unlocks - habit share, rounded again) lands off the 0.0025 grid
        games = [nh_game(5)] * 399 + [nh_game(6)]
        with tempfile.TemporaryDirectory() as d:
            write_round(d, 1, games)
            r = gwls_report.round_row(d, 1)
        self.assertEqual(r['nonhabit_sum'], 5 * 399 + 6)
        self.assertEqual(r['nonhabit_exact'], (5 * 399 + 6) / 400)
        self.assertEqual(r['nonhabit'], round((5 * 399 + 6) / 400, 3))                        # rounded for display only

    def test_indicator_threshold_is_exact_on_the_grid(self):
        ref = gwls_report.REF
        # mean of rounds 3 and 4 = 4176 / 800 = 5.22 = ref(200) - 0.5 exactly: trips (<=); one more non-habit unlock in 800 games does not
        on = {200: [row(3, 2088, 2.0), row(4, 2088, 2.0)], 201: [row(3, 2300, 2.0), row(4, 2300, 2.0)]}
        self.assertTrue(gwls_report.indicator(on, ref)['per_seed'][200]['nonhabit_trips'])
        off = {200: [row(3, 2088, 2.0), row(4, 2089, 2.0)], 201: on[201]}
        self.assertFalse(gwls_report.indicator(off, ref)['per_seed'][200]['nonhabit_trips'])
        # seed 201: 5.37 -> 4296 / 800
        on201 = {200: on[200], 201: [row(3, 2148, 2.0), row(4, 2148, 2.0)]}
        self.assertTrue(gwls_report.indicator(on201, ref)['per_seed'][201]['nonhabit_trips'])
        self.assertEqual(gwls_report.indicator(on201, ref)['branch'], gwls_report.STOP)
        off201 = {200: on[200], 201: [row(3, 2148, 2.0), row(4, 2149, 2.0)]}
        self.assertEqual(gwls_report.indicator(off201, ref)['branch'], 'CONTINUE')

    def test_indicator_ratio_and_reading(self):
        ref = gwls_report.REF
        fine = [row(3, 2400, 3.0), row(4, 2400, 3.0)]
        ratio_low = [row(3, 2400, 0.4), row(4, 2400, 0.6)]                                    # mean 0.5 trips (<=)
        self.assertEqual(gwls_report.indicator({200: ratio_low, 201: ratio_low}, ref)['branch'], gwls_report.STOP)
        self.assertEqual(gwls_report.indicator({200: ratio_low, 201: fine}, ref)['branch'], 'CONTINUE')
        low_nh = [row(3, 2000, 3.0), row(4, 2000, 3.0)]
        mixed = gwls_report.indicator({200: ratio_low, 201: low_nh}, ref)                     # per-seed reading stops; "X on both or Y on both" does not
        self.assertEqual(mixed['branch'], gwls_report.STOP)
        self.assertEqual(mixed['alt_reading_branch'], 'CONTINUE')
        self.assertFalse(mixed['readings_agree'])
        self.assertIsNone(gwls_report.indicator({200: [row(3, 1, 1.0)], 201: fine}, ref)['branch'])
        self.assertIsNone(gwls_report.indicator({200: fine, 201: []}, ref)['branch'])

    def test_ratio_w_exact_is_unrounded_and_agrees_with_the_census(self):
        g = dict(seed=1, views=[READY] * 10, actions=[2] * 3 + [0] * 7, events=[(9, 'collect_wood')], first={'collect_wood': 9}, length=10, end='dead')
        wp = census_ready.WPICK
        g['actions'] = [wp] * 3 + [0] * 7
        exact = gwls_report.ratio_w_exact([g])
        self.assertAlmostEqual(exact, 3 / 7, places=12)
        shown = census_ready.one_round([g])['A27']['ratio_w']
        self.assertAlmostEqual(shown, exact, places=2)
        self.assertIsNone(gwls_report.ratio_w_exact([nh_game(2)]))

    def test_cache_goes_stale_never(self):
        with tempfile.TemporaryDirectory() as d:
            cache = {}
            write_round(d, 1, [nh_game(5)] * 8)
            a = gwls_report.round_row(d, 1, cache)
            self.assertEqual(len(cache), 1)
            gwls_report.round_row(d, 1, cache)
            self.assertEqual(len(cache), 1)                                                  # same files: same key
            # the round re-runs into the same folder: same abspath, round and game count, different games
            write_round(d, 1, [nh_game(2)] * 8)
            b = gwls_report.round_row(d, 1, cache)
            self.assertEqual(len(cache), 2)
            self.assertEqual((a['nonhabit_sum'], b['nonhabit_sum']), (40, 16))

    def test_play_files_that_disagree_with_iter_json_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            write_round(d, 1, [nh_game(5)] * 8)
            with open(os.path.join(d, 'iter-1.json')) as f:
                it = json.load(f)
            it['games'] = 9
            with open(os.path.join(d, 'iter-1.json'), 'w') as f:
                json.dump(it, f)
            with self.assertRaises(AssertionError):
                gwls_report.round_row(d, 1)


class ReportRobustness(unittest.TestCase):
    def test_ratio_consistency_bound_covers_census_rounding(self):
        # A_w ~ 12, ratio ~ 8: W_w and A_w rounded to 2 dp can move the ratio by ~(1 + 8) * 0.005 / 12 = 0.00375 (> the old 0.002 assert)
        W, A = 96.0049, 12.0049
        Wr, Ar = round(W, 2), round(A, 2)
        shown = round(Wr / Ar, 3)
        exact = W / A
        chk = gwls_report.ratio_consistency(shown, exact, Ar)
        self.assertTrue(chk['ratio_ok'])
        self.assertLessEqual(chk['ratio_gap'], chk['ratio_bound'])
        # worst case of the rounding: W up 0.005, A down 0.005 -> still inside the bound
        worst = gwls_report.ratio_consistency(round((96.004 + 0.005) / (12.004 - 0.005), 3), 96.004 / 12.004, 12.0)
        self.assertTrue(worst['ratio_ok'])
        # a real mismatch is flagged, not raised
        bad = gwls_report.ratio_consistency(8.5, 8.0, 12.0)
        self.assertFalse(bad['ratio_ok'])
        # undefined cases never raise
        for args in ((None, 1.0, 2.0), (1.0, None, 2.0), (1.0, 1.0, None)):
            self.assertIsNone(gwls_report.ratio_consistency(*args)['ratio_ok'])
        self.assertIsNone(gwls_report.ratio_consistency(1.0, 1.0, 0.0)['ratio_ok'])

    def test_round_row_does_not_raise_where_the_old_assert_did(self):
        census = dict(A27=dict(W_n=40, A_n=5, W_w=96.0, A_w=12.0, ratio_w=8.003), V=100, E=30)           # gap 0.003 >= the old 0.002
        with tempfile.TemporaryDirectory() as d:
            write_round(d, 1, [nh_game(5)] * 8)
            with mock.patch.object(gwls_report.census_ready, 'one_round', return_value=census), \
                    mock.patch.object(gwls_report, 'ratio_w_exact', return_value=8.0):
                r = gwls_report.round_row(d, 1)
        self.assertEqual(r['ratio_w_exact'], 8.0)                                            # the indicator keeps the unrounded value
        self.assertAlmostEqual(r['ratio_gap'], 0.003, places=9)
        self.assertGreater(r['ratio_bound'], 0.003)
        self.assertTrue(r['ratio_ok'])
        md = gwls_report.markdown({200: [r]}, dict(branch=None, note='n'))
        self.assertIn('gap 0.003', md)
        self.assertIn('ok', md)
        # and a flagged row still does not raise, and is visible in the markdown
        census2 = dict(A27=dict(census['A27'], ratio_w=9.5), V=100, E=30)
        with tempfile.TemporaryDirectory() as d:
            write_round(d, 1, [nh_game(5)] * 8)
            with mock.patch.object(gwls_report.census_ready, 'one_round', return_value=census2), \
                    mock.patch.object(gwls_report, 'ratio_w_exact', return_value=8.0):
                r2 = gwls_report.round_row(d, 1)
        self.assertFalse(r2['ratio_ok'])
        self.assertIn('FLAG', gwls_report.markdown({200: [r2]}, dict(branch=None, note='n')))

    def test_iter_json_half_written_is_retried_once_then_a_clear_error(self):
        with tempfile.TemporaryDirectory() as d:
            write_round(d, 1, [nh_game(5)] * 8)
            path = os.path.join(d, 'iter-1.json')
            with open(path) as f:
                good = f.read()
            with open(path, 'w') as f:
                f.write(good[:20])                                                           # torn write
            calls = []

            def finish_write(_s):
                calls.append(_s)
                with open(path, 'w') as f:
                    f.write(good)
            with mock.patch.object(gwls_report.time, 'sleep', side_effect=finish_write):
                self.assertEqual(gwls_report.read_iter(d, 1)['games'], 8)                    # the retry sees the finished file
            self.assertEqual(len(calls), 1)
            with open(path, 'w') as f:
                f.write(good[:20])
            with mock.patch.object(gwls_report.time, 'sleep') as sl:
                with self.assertRaises(gwls_report.RoundReadError) as cm:
                    gwls_report.read_iter(d, 1)
            self.assertEqual(sl.call_count, 1)                                               # exactly one retry
            self.assertIn('iter-1.json', str(cm.exception))


def write_gate_root(root, nh200, nh201, rounds=(3, 4)):
    for seed, n in ((200, nh200), (201, nh201)):
        for k in rounds:
            write_round(os.path.join(root, f's{seed}'), k, [nh_game(n)] * 8)


class Final(unittest.TestCase):
    def test_gate_refuses_stop_and_unfinished_and_passes_continue(self):
        with tempfile.TemporaryDirectory() as root:
            write_gate_root(root, 1, 1)                                                      # 1 non-habit unlock a game: both seeds far below ref - 0.5
            bad, ind = gwls_final.gate(root)
            self.assertEqual(ind['branch'], gwls_report.STOP)
            self.assertTrue(bad and 'STOP' in bad[0])
        with tempfile.TemporaryDirectory() as root:
            write_gate_root(root, 1, 6)                                                      # only one seed trips: CONTINUE
            bad, ind = gwls_final.gate(root)
            self.assertEqual((bad, ind['branch']), ([], 'CONTINUE'))
        with tempfile.TemporaryDirectory() as root:
            write_gate_root(root, 6, 6, rounds=(3,))
            bad, ind = gwls_final.gate(root)
            self.assertIsNone(ind['branch'])
            self.assertTrue(bad and 'cannot be read' in bad[0])

    def test_arm_c_checks(self):
        for s in gwls_final.SEEDS:
            b = gwls_final.synthetic_arm_c(s)
            raw = json.dumps(b).encode()
            self.assertEqual(gwls_final.arm_c_problems(s, raw, b, check_hash=False), [])
            self.assertTrue(any('sha256' in x for x in gwls_final.arm_c_problems(s, raw, b)))
            for key, val in (('picker', 'greedy'), ('temp', 0.7), ('ckpt', f'/x/glprobe/run/s{s}/n32000/checkpoint.pt'), ('worlds', 50)):
                self.assertTrue(gwls_final.arm_c_problems(s, raw, dict(b, **{key: val}), check_hash=False), key)
            self.assertTrue(gwls_final.arm_c_problems(s, raw, dict(b, mean_unlocks=b['mean_unlocks'] + 0.01), check_hash=False))
        self.assertTrue(gwls_final.arm_c_problems(200, b'x', gwls_final.synthetic_arm_c(201), check_hash=False))        # the other seed's file: means differ

    def test_the_real_arm_c_files_pass_when_present(self):
        for s in gwls_final.SEEDS:
            p = gwls_final.paths('/nonexistent', os.path.join(gwls_final.SCRATCH, 'glprobe'), s)
            if not os.path.exists(p['base']):
                self.skipTest('arm C files not in the scratch folder')
            self.assertEqual(gwls_final.load_arm_c(p, s)[1], [])

    def test_round8_needs_state_pt_with_k_8(self):
        with tempfile.TemporaryDirectory() as root:
            P = gwls_final.paths(root, root, 200)
            os.makedirs(P['dir'])
            self.assertEqual(len(gwls_final.round8_problems(200, P)), 3)                       # iter-8, checkpoint, state.pt all missing
            for name in ('iter8', 'ckpt'):
                open(P[name], 'w').close()
            st = dict(k=7, run_seed=398, day_offset=4, parent='/x/glprobe/s200/n64000/checkpoint.pt')
            torch.save(st, P['state'])
            self.assertTrue(any('not 8' in x for x in gwls_final.round8_problems(200, P)))
            torch.save(dict(st, k=8), P['state'])
            self.assertEqual(gwls_final.round8_problems(200, P), [])
            torch.save(dict(st, k=8, day_offset=0), P['state'])
            self.assertTrue(gwls_final.round8_problems(200, P))
            torch.save(dict(st, k=8, parent='/x/glprobe/s201/n64000/checkpoint.pt'), P['state'])
            self.assertTrue(gwls_final.round8_problems(200, P))

    def test_play_path_refuses_a_stopped_run_and_plays_nothing(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as armc:
            write_gate_root(root, 1, 1)
            for s in gwls_final.SEEDS:
                P = gwls_final.paths(root, armc, s)
                for name in ('iter8', 'ckpt'):
                    open(P[name], 'w').close()
                torch.save(dict(k=8, run_seed=gwls_final.RUN_SEED[s], day_offset=4, parent=f'/x/glprobe/s{s}/n64000/checkpoint.pt'), P['state'])
                os.makedirs(os.path.dirname(P['base']))
                with open(P['base'], 'w') as f:
                    json.dump(gwls_final.synthetic_arm_c(s), f)
            with mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=AssertionError('a sealed world would have been played')):
                with self.assertRaises(SystemExit) as cm:
                    gwls_final.main(['--root', root, '--arm-c', armc, '--persist-dir', os.path.join(root, 'persist')])
            msg = str(cm.exception)
            self.assertIn('STOP', msg)
            self.assertIn('sha256', msg)                                                     # the synthetic arm C is not the committed file either
            self.assertFalse(any(os.path.exists(gwls_final.paths(root, armc, s)['lock']) for s in gwls_final.SEEDS))


class FinalRobustness(unittest.TestCase):
    def test_relative_root_gives_absolute_child_paths_from_any_cwd(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as elsewhere:
            os.makedirs(os.path.join(base, 'run', 'gwls'))
            old = os.getcwd()
            try:
                os.chdir(base)
                a = gwls_final.parse_args(['--root', 'run/gwls', '--arm-c', 'run/armc', '--persist-dir', 'out'])
                expect = {s: gwls_final.command(gwls_final.paths(os.path.join(os.path.realpath(base), 'run', 'gwls'), os.path.join(os.path.realpath(base), 'run', 'armc'), s))
                          for s in gwls_final.SEEDS}
                os.chdir(elsewhere)                                                          # the path building must not depend on the cwd afterwards
                for s in gwls_final.SEEDS:
                    argv = gwls_final.command(gwls_final.paths(a.root, a.arm_c, s))
                    ckpt, out = argv[argv.index('--ckpt') + 1], argv[argv.index('--out') + 1]
                    self.assertTrue(os.path.isabs(ckpt) and os.path.isabs(out), argv)
                    self.assertEqual(argv, expect[s])                                        # the same files as seen from the cwd the user typed it in
                    self.assertEqual(ckpt, os.path.join(os.path.realpath(base), 'run', 'gwls', f's{s}', 'checkpoint-iter8.pt'))
                    self.assertTrue(all(os.path.isabs(v) for v in gwls_final.paths(a.root, a.arm_c, s).values()))
                self.assertTrue(os.path.isabs(a.persist_dir))
            finally:
                os.chdir(old)

    def test_gate_turns_inconsistencies_into_refusal_strings(self):
        with tempfile.TemporaryDirectory() as root:
            write_gate_root(root, 6, 6)
            d = os.path.join(root, 's200')
            write_round(d, 3, [nh_game(6)] * 8, extra=dict(games=9))                          # iter-3 says 9 games, the play files hold 8
            with open(os.path.join(root, 's201', 'iter-4.json'), 'w') as f:
                f.write('{"games": 8, "mean')                                                  # unparseable iter-4
            with mock.patch.object(gwls_report.time, 'sleep'):
                bad, ind = gwls_final.gate(root)
            self.assertIsNone(ind['branch'])
            self.assertEqual(len(bad), 2, bad)                                                 # both problems listed, none raised
            self.assertTrue(any('seed 200 round 3' in x and 'iter-3.json says 9 games' in x for x in bad), bad)
            self.assertTrue(any('seed 201 round 4' in x and 'iter-4.json' in x for x in bad), bad)
            # a mismatch on the mean unlocks too
            write_round(d, 3, [nh_game(6)] * 8, extra=dict(mean_unlocks=99.0))
            with mock.patch.object(gwls_report.time, 'sleep'):
                self.assertTrue(any('do not match' in x for x in gwls_final.gate(root)[0]))

    def test_dry_run_exits_1_and_lists_every_problem_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as armc:
            write_gate_root(root, 6, 6)
            write_round(os.path.join(root, 's200'), 3, [nh_game(6)] * 8, extra=dict(games=9))
            buf = io.StringIO()
            with mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=AssertionError('played')), contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    gwls_final.main(['--dry-run', '--root', root, '--arm-c', armc])
            self.assertEqual(cm.exception.code, 1)
            out = buf.getvalue()
            self.assertIn('WOULD REFUSE', out)
            self.assertIn('iter-3.json says 9 games', out)
            self.assertIn('round 8 is not complete', out)
            self.assertIn('arm C file missing', out)


class Persist(unittest.TestCase):
    SCRIPT = os.path.join(os.path.dirname(gwls_final.__file__), 'gwls_persist.sh')

    def run_persist(self, src, dest):
        return subprocess.run(['bash', self.SCRIPT, src, dest], capture_output=True, text=True, env=dict(os.environ, PY=sys.executable))

    def test_persist_validates_copies_play_files_and_records_checks(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dest:
            for seed in (200, 201):
                write_round(os.path.join(src, f's{seed}'), 1, [nh_game(5)] * 8)
                write_round(os.path.join(src, f's{seed}'), 2, [nh_game(5)] * 8)
            torn = os.path.join(src, 's201', 'iter-2.json')
            with open(torn) as f:
                good = f.read()
            with open(torn, 'w') as f:
                f.write(good[:15])
            r = self.run_persist(src, dest)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(torn, r.stderr)                                                    # the file is named
            self.assertFalse(os.path.exists(os.path.join(dest, 's201', 'iter-2.json')))      # a torn file is never persisted
            self.assertTrue(os.path.exists(os.path.join(dest, 's200', 'iter-2.json')))       # the rest still is
            self.assertTrue(os.path.exists(os.path.join(dest, 's201', 'play-2-3.json.gz')))
            self.assertEqual(sorted(x for x in os.listdir(os.path.join(dest, 's200')) if x.startswith('play-')),
                             sorted(x for x in os.listdir(os.path.join(src, 's200')) if x.startswith('play-')))
            self.assertFalse(any('.tmp.' in x for x in os.listdir(os.path.join(dest, 's201'))))
            with open(os.path.join(dest, 'checks.txt')) as f:
                self.assertIn('gwls_checks exit code:', f.read())
            with open(torn, 'w') as f:                                                       # the write finishes: now it all persists, exit 0
                f.write(good)
            mt = os.path.getmtime(os.path.join(dest, 's200', 'play-1-0.json.gz'))
            r = self.run_persist(src, dest)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(os.path.join(dest, 's201', 'iter-2.json')))
            self.assertEqual(os.path.getmtime(os.path.join(dest, 's200', 'play-1-0.json.gz')), mt)       # identical play file: not copied again
            # a changed play file is copied
            write_round(os.path.join(src, 's200'), 1, [nh_game(2)] * 8)
            self.assertEqual(self.run_persist(src, dest).returncode, 0)
            with open(os.path.join(src, 's200', 'play-1-0.json.gz'), 'rb') as a, open(os.path.join(dest, 's200', 'play-1-0.json.gz'), 'rb') as b:
                self.assertEqual(a.read(), b.read())


class Checks(unittest.TestCase):
    def test_decode_inverts_practice_seed(self):
        from game import play
        for rs, day, i in ((398, 4, 0), (399, 35, 99), (394, 0, 7)):
            self.assertEqual(gwls_checks.decode(play.practice_seed(rs, day, i)), (rs, day, i))
        self.assertEqual(gwls_checks.decode(gwls_checks.FIRST_SEED[200]), (398, 4, 0))
        self.assertEqual(gwls_checks.decode(gwls_checks.FIRST_SEED[201]), (399, 4, 0))


if __name__ == '__main__':
    unittest.main()
