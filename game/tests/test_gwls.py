"""Tests for game/gwls_report.py, game/gwls_final.py and game/gwls_checks.py (GW-LS, draft pending coordinator review). Run: python -m unittest game.tests.test_gwls

No checkpoint and no game is played: synthetic round folders in a temp dir. Nothing here touches a sealed world (the final scorer's subprocess is mocked to fail if called).
"""
import contextlib
import gzip
import io
import json
import os
import pathlib
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


BAD_MARK = 8                                    # a game with this many first-unlocks (7 non-habit + wake_up) marks the round whose census ratio is made inconsistent


@contextlib.contextmanager
def census_stub():
    """one_round / ratio_w_exact stubbed: every round is consistent (ratio 8.0, gap 0) except rounds whose games have BAD_MARK first-unlocks (census says 9.5)."""
    def one_round(games):
        ratio = 9.5 if len(games[0]['first']) == BAD_MARK else 8.0
        return dict(A27=dict(W_n=40, A_n=5, W_w=96.0, A_w=12.0, ratio_w=ratio), V=100, E=30)
    with mock.patch.object(gwls_report.census_ready, 'one_round', side_effect=one_round), mock.patch.object(gwls_report, 'ratio_w_exact', return_value=8.0):
        yield


def corrupt_gzip_header(path):
    with open(path, 'wb') as f:
        f.write(b'this is not gzip data at all')


def corrupt_gzip_body(path):
    with open(path, 'rb') as f:
        raw = bytearray(f.read())
    for i in range(12, len(raw) - 8):                                                          # valid header and trailer, damaged deflate stream
        raw[i] ^= 0xFF
    with open(path, 'wb') as f:
        f.write(bytes(raw))


def truncate(path):
    with open(path, 'rb') as f:
        raw = f.read()
    with open(path, 'wb') as f:
        f.write(raw[:len(raw) // 2])


class GateReadSide(unittest.TestCase):
    """Round-2 read-side fixes: ratio_ok is honoured, and no read failure is a crash."""

    def root(self, nh=6):
        r = tempfile.TemporaryDirectory()
        self.addCleanup(r.cleanup)
        write_gate_root(r.name, nh, nh)
        return r.name

    def test_read_errors_tuple_is_complete(self):
        import zlib
        for e in (AssertionError, ValueError, json.JSONDecodeError, gwls_report.RoundReadError, OSError, KeyError, TypeError, EOFError, zlib.error,
                  gzip.BadGzipFile, ZeroDivisionError, IndexError):
            self.assertTrue(issubclass(e, gwls_report.READ_ERRORS), e)

    def test_happy_path_with_consistent_ratios_continues(self):
        root = self.root()
        with census_stub():
            bad, ind = gwls_final.gate(root)
        self.assertEqual((bad, ind['branch']), ([], 'CONTINUE'))

    def test_1_a_round_with_ratio_ok_false_is_refused_for_every_seed_and_round(self):
        for seed in gwls_final.SEEDS:
            for k in (3, 4):
                with self.subTest(seed=seed, round=k):
                    root = self.root()
                    write_round(os.path.join(root, f's{seed}'), k, [nh_game(BAD_MARK - 1)] * 8)
                    with census_stub():
                        bad, ind = gwls_final.gate(root)
                    self.assertEqual(ind['branch'], 'CONTINUE')                              # the indicator itself is fine; the gate still refuses
                    self.assertEqual(len(bad), 1, bad)
                    self.assertIn(f'seed {seed} round {k}', bad[0])
                    self.assertIn('ratio_ok False', bad[0])
                    self.assertRegex(bad[0], r'= 1\.5 > bound 0\.\d+')                         # the gap and the bound are in the message

    def test_1_ratio_ok_none_refuses_only_where_the_indicator_uses_the_ratio(self):
        def r(k, exact, ok, a_w=None, census=None):
            return dict(round=k, ratio_w_exact=exact, ratio_w=census, A_w=a_w, ratio_gap=None, ratio_bound=None, ratio_ok=ok)
        ok = lambda k: r(k, 2.0, True, 12.0, 2.0)
        # both rounds have an unrounded ratio but round 3's cannot be cross-checked: refused
        bad = gwls_report.ratio_problems({200: [r(3, 2.0, None, None, 2.0), ok(4)], 201: [ok(3), ok(4)]})
        self.assertEqual(len(bad), 1)
        self.assertIn('seed 200 round 3', bad[0])
        self.assertIn('ratio_ok None', bad[0])
        # no unrounded ratio in one round: the indicator uses no ratio for that seed, so None there is not a refusal
        self.assertEqual(gwls_report.ratio_problems({200: [r(3, None, None), r(4, 2.0, None, None, 2.0)], 201: [ok(3), ok(4)]}), [])
        # rounds outside 3-4 are not looked at
        self.assertEqual(gwls_report.ratio_problems({200: [r(1, 2.0, False)], 201: []}), [])

    def test_3_ratio_existence_mismatch_is_refused(self):
        def r(k, exact, census, a_w=3.1, ok=None):
            return dict(round=k, ratio_w_exact=exact, ratio_w=census, A_w=a_w, ratio_gap=None, ratio_bound=None, ratio_ok=ok)
        good = lambda k: r(k, 2.0, 2.0, 12.0, True)
        # (1) unrounded None, census has a ratio: refused with the mismatch reason (naming seed, round and both values)
        bad = gwls_report.ratio_problems({200: [r(3, None, 0.4), good(4)], 201: [good(3), good(4)]})
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('seed 200 round 3', bad[0])
        self.assertIn('existence mismatch', bad[0])
        self.assertIn('ratio_w_exact None', bad[0])
        self.assertIn('census ratio_w 0.4', bad[0])
        # also on round 4 and on the other seed
        bad = gwls_report.ratio_problems({200: [good(3), good(4)], 201: [good(3), r(4, None, 0.4)]})
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('seed 201 round 4', bad[0])
        self.assertIn('existence mismatch', bad[0])
        # (2) the reverse: unrounded present, census ratio_w None: refused (mismatch reason among the refusals)
        bad = gwls_report.ratio_problems({200: [r(3, 2.0, None), good(4)], 201: [good(3), good(4)]})
        self.assertTrue(any('existence mismatch' in b and 'seed 200 round 3' in b and 'census ratio_w None' in b for b in bad), bad)
        # (3) both None: not refused by this rule (the indicator uses no ratio there)
        bad = gwls_report.ratio_problems({200: [r(3, None, None, None), r(4, None, None, None)], 201: [good(3), good(4)]})
        self.assertEqual(bad, [])
        # rounds outside 3-4 are not looked at
        self.assertEqual(gwls_report.ratio_problems({200: [r(1, None, 0.4)], 201: []}), [])

    def test_3_ratio_existence_mismatch_refuses_through_the_gate_and_happy_path_holds(self):
        root = self.root()
        with census_stub():
            bad, ind = gwls_final.gate(root)
        self.assertEqual((bad, ind['branch']), ([], 'CONTINUE'))                                  # (4) live-like happy path unchanged
        real = gwls_report.ratio_w_exact
        with census_stub(), mock.patch.object(gwls_report, 'ratio_w_exact', lambda games: None):
            bad, ind = gwls_final.gate(root)
        self.assertTrue(any('existence mismatch' in b for b in bad), bad)

    def test_2_truncated_play_file_is_a_listed_refusal(self):
        root = self.root()
        truncate(os.path.join(root, 's200', 'play-3-1.json.gz'))
        with census_stub():
            bad, ind = gwls_final.gate(root)
        self.assertIsNone(ind['branch'])
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('seed 200 round 3', bad[0])
        self.assertIn('EOFError', bad[0])

    def test_3_corrupt_gzip_bytes_are_a_listed_refusal(self):
        for damage, name in ((corrupt_gzip_header, 'BadGzipFile'), (corrupt_gzip_body, 'error')):
            with self.subTest(name=name):
                root = self.root()
                damage(os.path.join(root, 's201', 'play-3-0.json.gz'))
                with census_stub():
                    bad, ind = gwls_final.gate(root)
                self.assertEqual(len(bad), 1, bad)
                self.assertIn('seed 201 round 3', bad[0])
                self.assertIn(name, bad[0])

    def test_4_zero_games_in_iter_json_is_a_clear_refusal(self):
        root = self.root()
        path = os.path.join(root, 's201', 'iter-4.json')
        with open(path) as f:
            it = json.load(f)
        with open(path, 'w') as f:
            json.dump(dict(it, games=0), f)
        with census_stub():
            bad, ind = gwls_final.gate(root)
        self.assertIsNone(ind['branch'])
        self.assertEqual(len(bad), 1, bad)
        self.assertIn('seed 201 round 4', bad[0])
        self.assertIn('games = 0', bad[0])
        self.assertNotIn('ZeroDivisionError', bad[0])                                            # checked before dividing
        # and with no play files at all as well (len(games) == 0 == games would otherwise reach the division)
        for fn in os.listdir(os.path.join(root, 's201')):
            if fn.startswith('play-4-'):
                os.remove(os.path.join(root, 's201', fn))
        with census_stub():
            self.assertTrue(any('games = 0' in x for x in gwls_final.gate(root)[0]))

    def test_other_unreadable_things_are_refusals_too(self):
        root = self.root()
        os.makedirs(os.path.join(root, 's200'), exist_ok=True)
        with open(os.path.join(root, 's200', 'iter-x.json'), 'w') as f:                          # a stray name that is not iter-<k>.json
            f.write('{}')
        with open(os.path.join(root, 's200', 'iter-4.json'), 'w') as f:
            f.write('[1, 2]')                                                                    # valid JSON, not the expected object
        with mock.patch.object(gwls_report.time, 'sleep'), census_stub():
            bad, _ = gwls_final.gate(root)
        self.assertTrue(any('iter-x.json' in x for x in bad), bad)
        self.assertTrue(any('seed 200 round 4' in x for x in bad), bad)

    def test_5_dry_run_with_everything_wrong_exits_1_and_lists_every_problem(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as armc:
            write_gate_root(root, 6, 6)
            write_round(os.path.join(root, 's200'), 3, [nh_game(BAD_MARK - 1)] * 8)                 # s200 r3: ratio_ok False
            truncate(os.path.join(root, 's200', 'play-4-2.json.gz'))                               # s200 r4: EOFError
            corrupt_gzip_header(os.path.join(root, 's201', 'play-3-0.json.gz'))                    # s201 r3: BadGzipFile
            p = os.path.join(root, 's201', 'iter-4.json')                                          # s201 r4: games 0
            with open(p) as f:
                it = json.load(f)
            with open(p, 'w') as f:
                json.dump(dict(it, games=0), f)
            for s in gwls_final.SEEDS:                                                             # a malformed arm C too: mean_unlocks missing
                b = gwls_final.synthetic_arm_c(s)
                del b['mean_unlocks']
                os.makedirs(os.path.dirname(gwls_final.paths(root, armc, s)['base']))
                with open(gwls_final.paths(root, armc, s)['base'], 'w') as f:
                    json.dump(b, f)
            buf = io.StringIO()
            with mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=AssertionError('played')), contextlib.redirect_stdout(buf), census_stub():
                with self.assertRaises(SystemExit) as cm:
                    gwls_final.main(['--dry-run', '--root', root, '--arm-c', armc])
            self.assertEqual(cm.exception.code, 1)
            out = buf.getvalue()
            self.assertNotIn('Traceback', out)
            self.assertIn('WOULD REFUSE', out)
            for needle in ('seed 200 round 3', 'ratio_ok False', 'seed 200 round 4', 'EOFError', 'seed 201 round 3', 'BadGzipFile', 'seed 201 round 4', 'games = 0',
                           'round 8 is not complete', 'arm C seed 200', 'arm C seed 201'):
                self.assertIn(needle, out)

    def test_6_live_like_happy_path_dry_run_says_all_preconditions_hold(self):
        import hashlib
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as armc:
            write_gate_root(root, 6, 6)
            sha = {}
            for s in gwls_final.SEEDS:
                P = gwls_final.paths(root, armc, s)
                for name in ('iter8', 'ckpt'):
                    open(P[name], 'w').close()
                torch.save(dict(k=8, run_seed=gwls_final.RUN_SEED[s], day_offset=4, parent=f'/x/glprobe/s{s}/n64000/checkpoint.pt'), P['state'])
                os.makedirs(os.path.dirname(P['base']))
                raw = json.dumps(gwls_final.synthetic_arm_c(s)).encode()
                with open(P['base'], 'wb') as f:
                    f.write(raw)
                sha[s] = hashlib.sha256(raw).hexdigest()
            buf = io.StringIO()
            with mock.patch.dict(gwls_final.ARM_C_SHA256, sha), mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=AssertionError('played')), \
                    contextlib.redirect_stdout(buf), census_stub():
                gwls_final.main(['--dry-run', '--root', root, '--arm-c', armc])              # returns (no SystemExit) when nothing refuses
            self.assertIn('all preconditions hold', buf.getvalue())
            self.assertIn('round-4 branch: CONTINUE', buf.getvalue())


REAL_PROBE = gwls_final.training_processes                  # the fixture below patches the module attribute


class SealedFixture(unittest.TestCase):
    """A synthetic, complete round-8 root + arm C (all in temp dirs; the sealed worlds are never played, game.score is a mock)."""

    def setUp(self):
        import hashlib
        self.rootd, self.armcd = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        self.addCleanup(self.rootd.cleanup)
        self.addCleanup(self.armcd.cleanup)
        self.root, self.armc = self.rootd.name, self.armcd.name
        write_gate_root(self.root, 6, 6)
        sha = {}
        self.P = {s: gwls_final.paths(self.root, self.armc, s) for s in gwls_final.SEEDS}
        for s, P in self.P.items():
            for name in ('iter8', 'ckpt'):
                open(P[name], 'w').close()
            torch.save(dict(k=8, run_seed=gwls_final.RUN_SEED[s], day_offset=4, parent=f'/x/glprobe/s{s}/n64000/checkpoint.pt'), P['state'])
            self.set_times(s)
            os.makedirs(os.path.dirname(P['base']))
            raw = json.dumps(gwls_final.synthetic_arm_c(s)).encode()
            with open(P['base'], 'wb') as f:
                f.write(raw)
            sha[s] = hashlib.sha256(raw).hexdigest()
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.dict(gwls_final.ARM_C_SHA256, sha))
        stack.enter_context(census_stub())
        self.probe = stack.enter_context(mock.patch.object(gwls_final, 'training_processes', return_value=[]))     # no live game.imitate
        self.persist_dir = os.path.join(self.root, 'persist')

    def set_times(self, s, state=1000, iter8=900, ckpt=900):
        P = self.P[s]
        for name, t in (('state', state), ('iter8', iter8), ('ckpt', ckpt)):
            os.utime(P[name], (t, t))

    def result(self, s, **over):
        return {**gwls_final.synthetic_arm_c(s), 'ckpt': self.P[s]['ckpt'], **over}

    def write_result(self, s, m=None):
        with open(self.P[s]['out'], 'w') as f:
            json.dump(m if m is not None else self.result(s), f)

    def write_all_results(self):
        for s in gwls_final.SEEDS:
            self.write_result(s)

    def analyze(self):
        """-> (stdout, SystemExit message or None)"""
        buf = io.StringIO()
        msg = None
        with contextlib.redirect_stdout(buf), mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=AssertionError('played')):
            try:
                gwls_final.main(['--analyze-only', '--root', self.root, '--arm-c', self.armc, '--persist-dir', self.persist_dir])
            except SystemExit as e:
                msg = str(e)
        return buf.getvalue(), msg

    def no_final(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, 'final.json')))


class TrainingStopped(SealedFixture):
    """B3: state.pt k == 8 is not proof that training stopped."""

    def problems(self, s=200):
        return gwls_final.round8_problems(s, self.P[s])

    def test_clean_case_passes(self):
        self.assertEqual(self.problems(), [])

    def test_iter_9_json_refuses(self):
        open(os.path.join(self.P[200]['dir'], 'iter-9.json'), 'w').close()
        bad = self.problems()
        self.assertTrue(any('iter-9.json' in x and 'has not stopped' in x for x in bad), bad)

    def test_play_9_file_refuses(self):
        open(os.path.join(self.P[200]['dir'], 'play-9-0.json.gz'), 'w').close()
        self.assertTrue(any('play-9-0.json.gz' in x for x in self.problems()))

    def test_checkpoint_of_a_later_round_refuses(self):
        open(os.path.join(self.P[201]['dir'], 'checkpoint-iter12.pt'), 'w').close()
        self.assertTrue(any('checkpoint-iter12.pt' in x for x in self.problems(201)))
        self.assertEqual(self.problems(200), [])                                             # per seed folder

    def test_earlier_round_files_are_fine(self):
        for n in ('iter-7.json', 'play-8-3.json.gz', 'checkpoint-iter3.pt'):
            open(os.path.join(self.P[200]['dir'], n), 'w').close()
        self.assertEqual(self.problems(), [])

    def test_live_process_refuses(self):
        self.probe.return_value = [4242]
        bad = self.problems()
        self.assertTrue(any('live game.imitate process' in x and '4242' in x for x in bad), bad)

    def test_probe_unavailable_refuses(self):
        self.probe.side_effect = RuntimeError('neither /proc nor pgrep')
        bad = self.problems()
        self.assertTrue(any('probe cannot be evaluated' in x for x in bad), bad)

    def test_state_older_than_iter8_or_checkpoint_refuses(self):
        self.set_times(200, state=800, iter8=900, ckpt=700)
        self.assertTrue(any('older than' in x for x in self.problems()))
        self.set_times(200, state=800, iter8=700, ckpt=900)
        self.assertTrue(any('older than' in x for x in self.problems()))
        self.set_times(200, state=900, iter8=900, ckpt=900)                                  # equal is fine (state.pt is written last)
        self.assertEqual(self.problems(), [])

    def test_unlistable_folder_refuses(self):
        with mock.patch.object(gwls_final.os, 'listdir', side_effect=PermissionError('no')):
            self.assertTrue(any('cannot be evaluated' in x for x in self.problems()))

    def test_real_probe_finds_a_game_imitate_process_for_this_folder_only(self):
        d = self.P[200]['dir']
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', 'game.imitate', 'train', '--out', d])
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        import time
        for _ in range(100):                                                                 # until the child has exec'd
            if child.pid in REAL_PROBE(d):
                break
            time.sleep(0.05)
        self.assertIn(child.pid, REAL_PROBE(d))
        self.assertNotIn(child.pid, REAL_PROBE(self.P[201]['dir']))
        self.assertNotIn(os.getpid(), REAL_PROBE(d))

    def test_probe_without_proc_or_pgrep_raises(self):
        with mock.patch.object(gwls_final.os.path, 'isdir', return_value=False), mock.patch.object(gwls_final.shutil, 'which', return_value=None):
            with self.assertRaises(RuntimeError):
                REAL_PROBE('/x')

    def test_play_and_analyze_both_refuse_through_the_stop_proof(self):
        open(os.path.join(self.P[200]['dir'], 'iter-9.json'), 'w').close()
        self.write_all_results()
        out, msg = self.analyze()
        self.assertTrue(msg and 'iter-9.json' in msg, msg)
        self.no_final()
        bad, _ = gwls_final.play_problems(self.P, self.root, [])
        self.assertTrue(any('iter-9.json' in x for x in bad))


class OneShotLock(SealedFixture):
    """B1: the lock is taken atomically before any precondition check, and a second invocation never plays."""

    def fake_popen(self, calls):
        def popen(argv, **kw):
            calls.append(argv)
            s = 200 if f's200{os.sep}' in argv[argv.index('--ckpt') + 1] else 201
            self.write_result(s)                                                              # the (mocked) scorer's output
            return mock.Mock(wait=mock.Mock(return_value=0))
        return popen

    def run_main(self, calls):
        with mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=self.fake_popen(calls)), contextlib.redirect_stdout(io.StringIO()):
            gwls_final.main(['--root', self.root, '--arm-c', self.armc, '--persist-dir', self.persist_dir])

    def test_acquire_twice_second_refuses_and_keeps_the_first_locks(self):
        held, bad = gwls_final.acquire_locks(self.P)
        self.assertEqual((len(held), bad), (2, []))
        held2, bad2 = gwls_final.acquire_locks(self.P)
        self.assertEqual(held2, [])
        self.assertEqual(len(bad2), 2)
        self.assertTrue(all(os.path.exists(p['lock']) for p in self.P.values()))             # the first holder's locks survive the second's refusal

    def test_acquire_is_exclusive_even_when_the_lock_appears_between_check_and_act(self):
        real_open = os.open
        def racing_open(path, flags, mode=0o777):
            if path == self.P[201]['lock']:
                real_open(path, os.O_CREAT | os.O_WRONLY, 0o644)                              # the other invocation wins the race on s201
            return real_open(path, flags, mode)
        with mock.patch.object(gwls_final.os, 'open', side_effect=racing_open):
            held, bad = gwls_final.acquire_locks(self.P)
        self.assertEqual(held, [])
        self.assertEqual(len(bad), 1)
        self.assertFalse(os.path.exists(self.P[200]['lock']))                                 # only OUR lock was released
        self.assertTrue(os.path.exists(self.P[201]['lock']))                                  # the winner's lock is untouched

    def test_main_refuses_on_a_foreign_lock_plays_nothing_and_keeps_it(self):
        pathlib.Path(self.P[201]['lock']).write_text('other invocation\n')
        calls = []
        with self.assertRaises(SystemExit) as cm:
            self.run_main(calls)
        self.assertIn('already exists', str(cm.exception))
        self.assertEqual(calls, [])
        self.assertFalse(os.path.exists(self.P[200]['lock']))
        self.assertEqual(pathlib.Path(self.P[201]['lock']).read_text(), 'other invocation\n')

    def test_a_failed_precondition_releases_only_our_locks(self):
        open(os.path.join(self.P[200]['dir'], 'iter-9.json'), 'w').close()                    # B3 refusal after the locks were taken
        calls = []
        with self.assertRaises(SystemExit) as cm:
            self.run_main(calls)
        self.assertIn('iter-9.json', str(cm.exception))
        self.assertEqual(calls, [])
        self.assertFalse(any(os.path.exists(p['lock']) for p in self.P.values()))

    def test_clean_run_plays_each_seed_once_and_leaves_no_lock(self):
        calls = []
        self.run_main(calls)
        self.assertEqual(len(calls), 2)
        self.assertFalse(any(os.path.exists(p['lock']) for p in self.P.values()))
        self.assertTrue(os.path.exists(os.path.join(self.root, 'final.json')))

    def test_two_concurrent_invocations_play_at_most_once_per_seed(self):
        import threading
        calls, outcomes, barrier = [], [], threading.Barrier(2)
        def popen(argv, **kw):
            calls.append(argv)
            return self.fake_popen([])(argv, **kw)
        def invocation():
            barrier.wait()
            try:
                gwls_final.main(['--root', self.root, '--arm-c', self.armc, '--persist-dir', self.persist_dir])
                outcomes.append('played')
            except SystemExit as e:
                outcomes.append('refused' if 'refusing to play' in str(e) else str(e))
        with mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=popen), contextlib.redirect_stdout(io.StringIO()):
            ts = [threading.Thread(target=invocation) for _ in range(2)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        # interleaved acquisition may make BOTH refuse (each holds one seed's lock, each releases its own): safe. What must never happen is two plays.
        self.assertLessEqual(outcomes.count('played'), 1, outcomes)
        self.assertEqual(len(calls), 2 * outcomes.count('played'), (outcomes, len(calls)))     # at most one scorer per seed, in total
        self.assertEqual(len({c[c.index('--ckpt') + 1] for c in calls}), len(calls))
        self.assertTrue(all(o in ('played', 'refused') for o in outcomes), outcomes)

    def test_a_left_lock_still_blocks_replay(self):
        calls = []
        open(self.P[200]['lock'], 'w').close()
        open(self.P[201]['lock'], 'w').close()
        with self.assertRaises(SystemExit):
            self.run_main(calls)
        self.assertEqual(calls, [])
        self.assertTrue(all(os.path.exists(p['lock']) for p in self.P.values()))

    def test_dry_run_takes_no_lock(self):
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=AssertionError('played')):
            gwls_final.main(['--dry-run', '--root', self.root, '--arm-c', self.armc])
        self.assertFalse(any(os.path.exists(p['lock']) for p in self.P.values()))

    def test_play_path_applies_the_identity_check_to_the_fresh_result(self):
        def popen(argv, **kw):
            s = 200 if f's200{os.sep}' in argv[argv.index('--ckpt') + 1] else 201
            self.write_result(s, self.result(s, ckpt='/elsewhere/checkpoint-iter8.pt'))
            return mock.Mock(wait=mock.Mock(return_value=0))
        with mock.patch.object(gwls_final.subprocess, 'Popen', side_effect=popen), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                gwls_final.main(['--root', self.root, '--arm-c', self.armc, '--persist-dir', self.persist_dir])
        self.assertIn('identity check', str(cm.exception))
        self.no_final()


class AnalyzeOnly(SealedFixture):
    """B2: --analyze-only goes through the same gate / completeness / lock rule and checks the result's identity."""

    def test_passes_on_a_clean_completed_attempt(self):
        self.write_all_results()
        out, msg = self.analyze()
        self.assertIsNone(msg)
        self.assertIn('VERDICT:', out)
        self.assertTrue(os.path.exists(os.path.join(self.root, 'final.json')))

    def test_refuses_on_stop(self):
        write_gate_root(self.root, 1, 1)
        self.write_all_results()
        out, msg = self.analyze()
        self.assertTrue(msg and 'STOP' in msg, msg)
        self.no_final()

    def test_refuses_on_a_leftover_lock(self):
        self.write_all_results()
        open(self.P[201]['lock'], 'w').close()
        out, msg = self.analyze()
        self.assertTrue(msg and 'unresolved scoring attempt' in msg, msg)
        self.no_final()

    def test_refuses_when_the_ckpt_points_elsewhere(self):
        self.write_all_results()
        for bad_ckpt in ('/elsewhere/s200/checkpoint-iter8.pt', self.P[201]['ckpt'], self.P[200]['ckpt'] + '.bak', None, 5):
            self.write_result(200, self.result(200, ckpt=bad_ckpt))
            out, msg = self.analyze()
            self.assertTrue(msg and 'result ckpt' in msg, (bad_ckpt, msg))
            self.no_final()

    def test_a_symlinked_ckpt_that_resolves_to_this_checkpoint_is_the_same_file(self):
        self.write_all_results()
        link = os.path.join(self.root, 'link.pt')
        os.symlink(self.P[200]['ckpt'], link)
        self.write_result(200, self.result(200, ckpt=link))
        self.assertIsNone(self.analyze()[1])

    def test_refuses_when_arm_is_not_model(self):
        self.write_all_results()
        self.write_result(201, self.result(201, arm='random'))
        out, msg = self.analyze()
        self.assertTrue(msg and 'result arm' in msg, msg)
        self.no_final()

    def test_refuses_on_picker_temp_worlds_and_seeds(self):
        self.write_all_results()
        pw = self.result(200)['per_world']
        cases = [dict(picker='top'), dict(temp=0.5), dict(worlds=99), dict(per_world=pw[:99]),
                 dict(per_world=[dict(pw[0], seed=7000001)] + pw[1:]),                       # a seed twice, one missing
                 dict(per_world=[dict(pw[0], seed=6999999)] + pw[1:]),                       # a non-sealed seed
                 dict(per_world=[dict(w, seed=float(w['seed'])) for w in pw]),
                 dict(per_world=['x'] * 100), dict(per_world=None)]
        for over in cases:
            self.write_result(200, self.result(200, **over))
            out, msg = self.analyze()
            self.assertTrue(msg and 'seed 200' in msg, (list(over), msg))
            self.assertNotIn('Traceback', msg)
            self.no_final()

    def test_refuses_on_a_missing_or_torn_result_without_a_traceback(self):
        self.write_result(200)
        out, msg = self.analyze()
        self.assertTrue(msg and 'no result file' in msg, msg)
        with open(self.P[201]['out'], 'w') as f:
            f.write('{"arm": "mod')
        out, msg = self.analyze()
        self.assertTrue(msg and 'cannot be read' in msg, msg)
        self.no_final()

    def test_refuses_on_incomplete_round_8(self):
        self.write_all_results()
        torch.save(dict(k=7, run_seed=398, day_offset=4, parent='/x/glprobe/s200/n64000/checkpoint.pt'), self.P[200]['state'])
        out, msg = self.analyze()
        self.assertTrue(msg and 'not 8' in msg, msg)
        self.no_final()
        torch.save(dict(k=8, run_seed=398, day_offset=4, parent='/x/glprobe/s200/n64000/checkpoint.pt'), self.P[200]['state'])
        os.remove(self.P[201]['iter8'])
        out, msg = self.analyze()
        self.assertTrue(msg and 'round 8 is not complete' in msg, msg)
        self.no_final()

    def test_refuses_when_training_is_not_proved_stopped(self):
        self.write_all_results()
        self.probe.return_value = [1]
        out, msg = self.analyze()
        self.assertTrue(msg and 'live game.imitate process' in msg, msg)
        self.no_final()

    def test_refuses_on_a_wrong_arm_c(self):
        self.write_all_results()
        with mock.patch.dict(gwls_final.ARM_C_SHA256, {200: '0' * 64}):
            out, msg = self.analyze()
        self.assertTrue(msg and 'sha256' in msg, msg)
        self.no_final()

    def test_lists_every_problem_at_once(self):
        write_gate_root(self.root, 1, 1)
        open(self.P[200]['lock'], 'w').close()
        self.write_result(200, self.result(200, arm='random'))
        out, msg = self.analyze()
        for needle in ('STOP', 'unresolved scoring attempt', 'result arm', 'no result file'):
            self.assertIn(needle, msg)


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
