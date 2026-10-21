"""Acceptance tests for domain/far/slip.py, the paired slip analysis (hand-computed cases; no torch).

  python3 -m domain.far.test_slip

Covers: McNemar exact p on small known cases; run_slip on a 10-row synthetic pair (b, c, drop, item SE, z, p, family table);
the by-#steps table and the single-p survival fit (steps given as lists and as ints); Student t quantiles against the printed
table (df 1-30 at 0.975, a spread at 0.95 / 0.995, and the large-df fallback); paired_contrast on hand data for each verdict
(pass / equivalent / fail / open), its interval, and n_needed; the CLI on synthetic run folders (runs, contrast, refusal of
unmatched and duplicate seeds, each refusal checked for its own reason), the same-rows guard of a 'drop' contrast, the --dev
guard (family / sha256; a superset only when its raw lines for the rows' ids re-hash to the rows' dev_sha256, on a synthetic pair and on the real 1,360 / 6,800-row skills DEVs, accepted and tampered), pair mode on a committed m0-format fixture with shuffled child ids (always runs), and, when the m0 per-row
files are present, pair mode on the real parent / L13 / L12 files (L13-LBsoft10 b=12 c=6 drop 0.44; L12-LB b=786 c=10).
The real-file test reads the folder named by SLIP_M0 (default: the build session's scratchpad); when it is absent it SKIPs (not
counted as passed) and SLIP_REQUIRE_M0=1 turns the skip into a failure.
"""
import contextlib
import hashlib
import io
import json
import math
import os
import tempfile

from domain.far import slip as S

M0 = os.environ.get('SLIP_M0', '/tmp/claude-0/-home-user/6e3fd48b-869d-5cdd-b158-7710e164d592/scratchpad/m0')
DEV = '/home/user/sk200k/dev/in_dist.jsonl'


def file_sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()

PARENT = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0]
CHILD = [1, 1, 1, 0, 0, 0, 1, 1, 1, 0]
FAMILY = ['A'] * 5 + ['B'] * 5
STEPS = [['s'], ['s'], 1, ['s'], ['s', 't'], ['s'], 1, 2, ['s', 't'], 2]


class Skip(Exception):
    pass


def close(x, y, tol=1e-9):
    return abs(x - y) <= tol


def test_mcnemar_exact():
    assert close(S.mcnemar_exact_p(0, 5), 2 / 32)
    assert close(S.mcnemar_exact_p(5, 0), 2 / 32)
    assert close(S.mcnemar_exact_p(1, 5), 14 / 64)
    assert close(S.mcnemar_exact_p(2, 10), 2 * 79 / 4096)
    assert S.mcnemar_exact_p(3, 3) == 1.0 and S.mcnemar_exact_p(0, 0) == 1.0
    assert S.mcnemar_exact_p(786, 10) < 1e-100 and S.mcnemar_exact_p(500, 500) == 1.0
    return 'p(0,5)=0.0625, p(1,5)=0.21875, p(2,10)=0.03857, p(3,3)=1, p(0,0)=1, p(786,10)<1e-100 (big ints exact)'


def test_run_slip_synthetic():
    s = S.run_slip(PARENT, CHILD, FAMILY)
    assert s['n'] == 10 and s['b'] == 3 and s['c'] == 1, s
    assert close(s['parent_pct'], 80) and close(s['child_pct'], 60) and close(s['drop'], 20)
    assert close(s['item_se'], 20) and close(s['z'], 1.0) and close(s['mcnemar_p'], 10 / 16)
    assert close(s['se_drop'], 100 * math.sqrt(4 - 4 / 10) / 10)   # unrestricted paired SE, not the null item_se
    assert 'by_steps' not in s
    z = S.run_slip([1, 1], [1, 1], ['A', 'A'])
    assert z['b'] == z['c'] == 0 and z['item_se'] == 0 and z['z'] == 0.0 and z['mcnemar_p'] == 1.0
    par = [1] * 1227 + [0] * 133   # the L12-LB shape: b=786 lost, c=10 gained, n=1360
    chd = [0] * 786 + [1] * 441 + [1] * 10 + [0] * 123
    big = S.run_slip(par, chd, ['A'] * 1360)
    assert (big['b'], big['c']) == (786, 10) and abs(big['item_se'] - 2.074) < 1e-3 and abs(big['se_drop'] - 1.382) < 1e-3, big
    return 'b=3 c=1 drop 20.0 item_se 20.0 se_drop 18.97 z 1.0 p 0.625; no discordant rows -> se 0, z 0, p 1'


def test_family_table():
    f = S.run_slip(PARENT, CHILD, FAMILY)['families']
    assert list(f) == ['A', 'B']
    assert f['A'] == dict(n=5, parent=100.0, child=60.0, drop=40.0, b=2, c=0), f['A']
    assert f['B'] == dict(n=5, parent=60.0, child=60.0, drop=0.0, b=1, c=1), f['B']
    return 'A: parent 100 child 60 drop 40 b2 c0; B: 60 -> 60 drop 0 b1 c1'


def test_steps_survival():
    s = S.run_slip(PARENT, CHILD, FAMILY, STEPS)
    b1, b2 = s['by_steps'][1], s['by_steps'][2]
    assert (b1['n'], b1['b'], b1['c'], b1['parent_right'], b1['child_right']) == (6, 2, 0, 6, 4), b1
    assert (b2['n'], b2['b'], b2['c'], b2['parent_right'], b2['child_right']) == (4, 1, 1, 2, 1), b2
    assert close(b1['drop'], 100 * 2 / 6) and close(b2['drop'], 0.0)
    assert close(s['p1'], 4 / 6)
    sv = s['survival']
    assert close(sv[1]['observed'], 4 / 6) and close(sv[1]['predicted'], 4 / 6)
    assert close(sv[2]['observed'], 0.5) and close(sv[2]['predicted'], (4 / 6) ** 2)
    nop1 = S.run_slip([1, 1], [1, 0], ['A', 'A'], [2, 2])
    assert nop1['p1'] is None and nop1['survival'][2]['predicted'] is None
    return '1-step survival 4/6, 2-step observed 0.5 vs p1**2 0.444 (steps as lists and as ints); no 1-step rows -> p1 None'


def test_t_quantiles():
    table = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131, 2.120,
             2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]
    for df, want in enumerate(table, 1):
        got = S.t_quantile(df, 0.975)
        assert abs(got - want) < 5.01e-4, (df, got, want)
    for df, p, want in [(1, 0.95, 6.314), (2, 0.95, 2.920), (5, 0.95, 2.015), (10, 0.95, 1.812), (30, 0.95, 1.697),
                        (10, 0.995, 3.169), (5, 0.995, 4.032), (1000, 0.975, 1.962), (250, 0.975, 1.969)]:
        got = S.t_quantile(df, p)
        assert abs(got - want) < 5.01e-4, (df, p, got, want)
    return 'df 1-30 at 0.975 match the table to 3 dp (df1 12.706, df5 2.571, df10 2.228, df30 2.042); 0.95 and 0.995 spots; df 250 / 1000 fallback'


def test_paired_contrast_verdicts():
    x, y = [10, 12, 11, 13], [8, 9, 9, 10]   # d = 2, 3, 2, 3: mean 2.5, sd sqrt(1/3), se 0.288675, t3 3.182
    r = S.paired_contrast(x, y, sesoi=2)
    assert r['n'] == 4 and close(r['mean_d'], 2.5) and close(r['sd_d'], math.sqrt(1 / 3)) and close(r['se'], math.sqrt(1 / 3) / 2)
    assert abs(r['t'] - 3.182) < 5.01e-4 and abs(r['ci_low'] - 1.581) < 2e-3 and abs(r['ci_high'] - 3.419) < 2e-3, r
    assert r['verdict'] == 'pass', r
    assert S.paired_contrast(x, y, sesoi=5)['verdict'] == 'equivalent'
    assert S.paired_contrast([-10, -12, -11, -13], [0, 0, 0, 0], sesoi=5)['verdict'] == 'fail'
    o = S.paired_contrast([1, 6, -2, 5], [0, 0, 0, 0], sesoi=5)
    assert o['verdict'] == 'open' and abs(o['sd_d'] - 3.697) < 1e-3, o
    assert S.paired_contrast(x, y)['verdict'] is None
    return 'd=(2,3,2,3): mean 2.5 interval [1.581, 3.419]; sesoi 2 pass, sesoi 5 equivalent; wide negative fail; wide straddling open'


def test_n_needed():
    o = S.paired_contrast([1, 6, -2, 5], [0, 0, 0, 0], sesoi=5)
    assert o['n_needed'] == 11, o['n_needed']   # n=10: 2.262*3.697/sqrt(10)=2.645 > 2.5; n=11: 2.228*3.697/sqrt(11)=2.483 <= 2.5
    assert S.paired_contrast([2, 3, 2, 3], [0, 0, 0, 0])['n_needed'] == 3   # n=2: 12.706*0.577/1.414=5.18 > 2.5; n=3: 4.303*0.577/1.732=1.43
    assert S.paired_contrast([2, 2.01], [0, 0])['n_needed'] == 2   # already clear at n=2
    assert S.paired_contrast([1, -1, 1, -1], [0, 0, 0, 0])['n_needed'] is None   # mean 0
    one = S.paired_contrast([3], [1], sesoi=1)
    assert one['n_needed'] is None and one['verdict'] is None and one['ci_low'] is None
    big = S.paired_contrast([1, 0, 2, -1, 0.5, 0.2], [0, 0, 0, 0, 0, 0])
    assert big['n_needed'] > 6
    return 'n_needed 11 for d=(1,6,-2,5), 3 for d=(2,3,2,3); 2 when already clear; None when mean 0 or n<2'


def write_run(td, name, seed, step, pct, parent, child, family=FAMILY, big=False, sha='ab' * 32, rows=True, harm_big=None, ids=None, harm_n=10):
    d = os.path.join(td, name)
    os.makedirs(d)
    rec = dict(arm='LB', step=step, cells={'HO': dict(n=100, hits=int(pct), pct=pct), 'S5': dict(n=100, hits=50, pct=50.0)},
               seed=seed, harm=dict(in_dist_a=80.0, in_dist_b=60.0, in_dist_drop=20.0, n=harm_n))
    if harm_big:
        rec['harm_big'] = harm_big
    with open(os.path.join(d, 'scores.jsonl'), 'w') as f:
        f.write(json.dumps(dict(rec, step=step - 1)) + '\n' + json.dumps(rec) + '\n')
    if rows:
        h = dict(step=step, dev='x', dev_sha256=sha, ids=ids or [f'r{i}' for i in range(len(parent))], family=family,
                 parent_hits=parent, child_hits=child)
        with open(os.path.join(d, f'harm-rows-{"big-" if big else ""}step{step}.json'), 'w') as f:
            json.dump(h, f)
    return d


def refuses(argv, *needles):
    """The command must exit through a message (not an argparse usage error, whose code is the int 2) naming every needle."""
    try:
        run_cli(argv)
    except SystemExit as e:
        assert not isinstance(e.code, int), ('argparse / bare exit, not a refusal message', argv, e.code)
        for n in needles:
            assert n in str(e.code), (n, str(e.code))
        return str(e.code)
    raise AssertionError(f'should have refused {needles}: {argv}')


def run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        S.main(argv)
    return buf.getvalue()


def test_cli_runs_and_contrast():
    with tempfile.TemporaryDirectory() as td:
        x = [write_run(td, f'x{i}', 100 + i, 4000, 60 + i, PARENT, CHILD) for i in range(3)]
        child2 = [1, 1, 1, 1, 0, 1, 1, 1, 1, 0]   # b=1 (row 4), c=1 (row 8): drop 0
        y = [write_run(td, f'y{i}', 100 + i, 4000, 50 + 2 * i, PARENT, child2) for i in (2, 1, 0)]   # shuffled order
        out = os.path.join(td, 'runs.json')
        text = run_cli(['runs', x[0], '--step', '4000', '--out', out])
        res = json.load(open(out))
        sl = res[x[0]]['slip']
        assert sl['b'] == 3 and sl['c'] == 1 and res[x[0]]['seed'] == 100 and res[x[0]]['cells']['HO'] == 60, res
        assert 'HO 60.00' in text and 'mcnemar_p 0.625' in text
        c = os.path.join(td, 'c.json')
        run_cli(['contrast', '--x', *x, '--y', *y, '--metric', 'drop', '--step', '4000', '--sesoi', '5', '--out', c])
        r = json.load(open(c))
        assert r['seeds'] == [100, 101, 102] and r['x'] == [20.0] * 3 and r['y'] == [0.0] * 3 and r['d'] == [20.0] * 3, r
        run_cli(['contrast', '--x', *x, '--y', *y, '--metric', 'HO', '--step', '4000', '--sesoi', '1', '--out', c])
        r = json.load(open(c))
        assert r['d'] == [10.0, 9.0, 8.0] and r['verdict'] == 'pass', r   # y HO by seed: 100 -> 50, 101 -> 52, 102 -> 54
        refuses(['contrast', '--x', *x[:2], '--y', *y, '--metric', 'HO', '--step', '4000'], 'unmatched seeds')
        refuses(['contrast', '--x', x[0], x[0], '--y', *y[:2], '--metric', 'HO', '--step', '4000'], 'appears twice')
        refuses(['runs', x[0], '--step', '999'], 'no record at step 999')
        refuses(['contrast', '--x', *x, '--y', *y, '--metric', 'nope', '--step', '4000'], "no cell 'nope'")
    return 'runs reads cells + slip (b3 c1); contrast pairs by recorded seed regardless of order (drop d=20 x3; HO pass); refuses unmatched / duplicate seeds, absent step, absent cell'


def write_dev(td, name='dev.jsonl', family=FAMILY):
    dev = os.path.join(td, name)
    with open(dev, 'w') as f:
        for i, st in enumerate(STEPS):
            f.write(json.dumps(dict(id=f'r{i}', family=family[i], steps=st if isinstance(st, list) else ['s'] * st)) + '\n')
    return dev, hashlib.sha256(open(dev, 'rb').read()).hexdigest()


def test_cli_dev_strata_and_big():
    with tempfile.TemporaryDirectory() as td:
        dev, sha = write_dev(td)
        d = write_run(td, 'a', 1, 4000, 60, PARENT, CHILD, sha=sha)
        out = os.path.join(td, 'o.json')
        run_cli(['runs', d, '--step', '4000', '--dev', dev, '--out', out])
        s = json.load(open(out))[d]['slip']
        assert s['survival']['2']['observed'] == 0.5 and s['p1'] == 4 / 6, s
        refuses(['runs', d, '--step', '4000', '--big'], 'missing')
        hb = dict(in_dist_a=70.0, in_dist_b=65.0, in_dist_drop=5.0, n=6800)
        write_run(td, 'b', 1, 4000, 60, PARENT, CHILD, big=True, harm_big=hb)
        text = run_cli(['runs', os.path.join(td, 'b'), '--step', '4000', '--big', '--out', out])
        assert 'recorded harm (big DEV): in_dist 70.0 -> 65.0 (drop 5.0), n 6800' in text and 'n 10' not in text.split('recorded harm')[1].split('\n')[0], text
        assert json.load(open(out))[os.path.join(td, 'b')]['harm'] == hb
        assert 'recorded harm: in_dist 80.0' in run_cli(['runs', os.path.join(td, 'a'), '--step', '4000'])
        # --dev guard: a different build reuses the ids with other content
        d2 = write_run(td, 'c', 1, 4000, 60, PARENT, CHILD, sha=sha)
        other, _ = write_dev(td, 'other.jsonl', family=['A'] * 4 + ['B'] * 6)
        refuses(['runs', d2, '--step', '4000', '--dev', other], 'family differs', 'not the same DEV')
        d3 = write_run(td, 'd', 1, 4000, 60, PARENT, CHILD, sha='cd' * 32)   # same ids and families, other content: sha differs, not a superset
        refuses(['runs', d3, '--step', '4000', '--dev', dev], 'sha256', 'not a superset')
        short = os.path.join(td, 'short.jsonl')
        open(short, 'w').write(open(dev).read().split('\n', 1)[1])
        refuses(['runs', d2, '--step', '4000', '--dev', short], '--dev lacks 1 of 10 rows')
        sup = os.path.join(td, 'sup.jsonl')   # a strict superset (the big DEV case) with a different sha is accepted when its lines for the rows' ids hash to the rows' sha
        open(sup, 'w').write(open(dev).read() + json.dumps(dict(id='r99', family='B', steps=['s'])) + '\n')
        run_cli(['runs', d2, '--step', '4000', '--dev', sup])
        refuses(['runs', d3, '--step', '4000', '--dev', sup], 'raw lines', 'not the same DEV rows')   # ... and refused when they do not (rows' sha is another one)
        tam = os.path.join(td, 'tam.jsonl')   # a superset with the same ids and families but one row's content changed (steps)
        lines = open(dev).read().split('\n')
        lines[3] = json.dumps(dict(id='r3', family='A', steps=['s', 'x']))
        open(tam, 'w').write('\n'.join(lines) + json.dumps(dict(id='r99', family='B', steps=['s'])) + '\n')
        refuses(['runs', d2, '--step', '4000', '--dev', tam], 'raw lines', 'not the same DEV rows')
    return '--dev supplies the steps strata (survival 0.5 at 2 steps); --big reads harm-rows-big and the harm_big record (n 6800) and refuses when absent; --dev refused on family / sha mismatch or missing ids; a superset accepted only when its raw lines for the rows\' ids hash to the rows\' dev_sha256 (a tampered superset and a wrong rows sha are refused)'


BIG = '/home/user/sk200k_big/dev/in_dist.jsonl'
SMALL_SHA = 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86'


def test_check_dev_superset_real():
    """The real skills DEVs: the 1,360-row in_dist (sha f975d9fb...) against the 6,800-row big DEV. A rows header carrying f975d9fb... accepts
    the big file (its lines for the 1,360 ids, in order, hash to f975d9fb...); a copy with one byte changed in one of those lines is refused."""
    if not (os.path.exists(BIG) and os.path.exists(DEV)):
        raise Skip(f'real DEVs absent ({BIG})')
    assert file_sha(DEV) == SMALL_SHA, 'the small DEV is not the skills seed-1 file'
    small = S.load_dev(DEV)
    ids = [json.loads(x)['id'] for x in open(DEV) if x.strip()]
    fam = [small[i][1] for i in ids]
    big = S.load_dev(BIG)
    assert len(big) > len(ids) and file_sha(BIG) != SMALL_SHA
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        got = S.check_dev(big, BIG, ids, fam, SMALL_SHA, 'big: ')
    assert list(got) == ids and 'accepted as a superset' in buf.getvalue(), buf.getvalue()
    assert S.subset_sha256(BIG, ids) == SMALL_SHA
    with tempfile.TemporaryDirectory() as td:
        tam = os.path.join(td, 'tam.jsonl')
        raw = open(BIG, 'rb').read().split(b'\n')
        k = next(j for j, ln in enumerate(raw) if ln.strip() and json.loads(ln)['id'] == ids[700])
        assert b'"' in raw[k]
        raw[k] = raw[k][:-1] + (b' }' if raw[k].endswith(b'}') else b'}')   # same id / family / fields, one extra space: other content, same parse
        open(tam, 'wb').write(b'\n'.join(raw))
        t = S.load_dev(tam)
        assert t[ids[700]] == big[ids[700]], 'the tamper must leave the parsed row (id, family, steps) as it was'
        try:
            S.check_dev(t, tam, ids, fam, SMALL_SHA, 'tam: ')
        except SystemExit as e:
            assert 'raw lines' in str(e) and 'not the same DEV rows' in str(e), str(e)
        else:
            raise AssertionError('the tampered superset was accepted')
    return f'big DEV ({len(big)} rows, sha {file_sha(BIG)[:8]}) accepted for a rows header f975d9fb... (its {len(ids)} lines hash back); a one-space-tampered copy refused'


def test_contrast_same_rows_guard():
    with tempfile.TemporaryDirectory() as td:
        child2 = [1, 1, 1, 1, 0, 1, 1, 1, 1, 0]
        x = [write_run(td, f'x{i}', i, 4000, 60, PARENT, CHILD) for i in range(3)]
        base = ['contrast', '--metric', 'drop', '--step', '4000']

        def y_with(tag, **kw):
            parent = kw.pop('parent', PARENT)
            return [write_run(td, f'y{tag}{i}', i, 4000, 50, parent, child2, **kw) for i in range(3)]
        ok = y_with('ok')
        c = os.path.join(td, 'c.json')
        run_cli(base + ['--x', *x, '--y', *ok, '--out', c])
        assert json.load(open(c))['source']['kind'] == 'rows'
        refuses(base + ['--x', *x, '--y', *y_with('sha', sha='cd' * 32)], 'not on the same rows')
        refuses(base + ['--x', *x, '--y', *y_with('ids', ids=[f's{i}' for i in range(10)])], 'not on the same rows')
        refuses(base + ['--x', *x, '--y', *y_with('par', parent=[1, 1, 1, 1, 1, 1, 1, 0, 0, 0])], 'not on the same rows')
        # a run with only the rounded harm record: refused by default, usable alone behind the flag, never mixed with per-row runs
        old = [write_run(td, f'o{i}', i, 4000, 50, PARENT, child2, rows=False) for i in range(3)]
        refuses(base + ['--x', *x, '--y', *old], 'rounded', '--allow-recorded')
        refuses(base + ['--x', *x, '--y', *old, '--allow-recorded'], 'not on the same rows')
        old_x = [write_run(td, f'ox{i}', i, 4000, 50, PARENT, CHILD, rows=False) for i in range(3)]
        run_cli(base + ['--x', *old_x, '--y', *old, '--allow-recorded', '--out', c])
        assert json.load(open(c))['source']['kind'] == 'recorded'
        refuses(base + ['--x', *old_x, '--y', *[write_run(td, f'on{i}', i, 4000, 50, PARENT, CHILD, rows=False, harm_n=99) for i in range(3)],
                        '--allow-recorded'], 'not on the same rows')
        run_cli(['contrast', '--metric', 'HO', '--step', '4000', '--x', *x, '--y', *y_with('cell', sha='cd' * 32)])   # cells are not row-bound
    return "drop contrast refuses a different dev_sha256 / ids / parent hits, the recorded-harm fallback without --allow-recorded, and mixed kinds; cells unaffected"


def make_m0(ids, hits, family, steps, order=None):
    order = order if order is not None else list(range(len(ids)))
    return dict(split='in_dist', n=len(ids), ids=[ids[k] for k in order], hits=[hits[k] for k in order],
                family=[family[k] for k in order], steps=[steps[k] for k in order])


def test_pair_m0_fixture_shuffled():
    """The m0 format (ids, hits, family, steps) with the child's rows in another order: align_pair must match by id."""
    ids = [f'r{i}' for i in range(10)]
    steps = [s if isinstance(s, list) else ['s'] * s for s in STEPS]
    p = make_m0(ids, PARENT, FAMILY, steps)
    order = [7, 2, 9, 0, 5, 1, 8, 3, 6, 4]
    c = make_m0(ids, CHILD, FAMILY, steps, order)
    assert c['ids'] != p['ids']
    with tempfile.TemporaryDirectory() as td:
        pf, cf, out = (os.path.join(td, n) for n in ('p.json', 'c.json', 'o.json'))
        json.dump(p, open(pf, 'w'))
        json.dump(c, open(cf, 'w'))
        run_cli(['pair', '--parent-rows', pf, '--child-rows', cf, '--out', out])
        got = json.load(open(out))
        want = S.run_slip(PARENT, CHILD, FAMILY, steps)
        assert (got['b'], got['c']) == (3, 1) and got['families'] == want['families'] and close(got['drop'], 20.0), got
        assert got['survival']['2']['observed'] == 0.5 and got['p1'] == 4 / 6, got
        dev, _ = write_dev(td)
        run_cli(['pair', '--parent-rows', pf, '--child-rows', cf, '--dev', dev, '--out', out])
        assert json.load(open(out))['survival'] == got['survival']
        other, _ = write_dev(td, 'other.jsonl', family=['A'] * 4 + ['B'] * 6)
        refuses(['pair', '--parent-rows', pf, '--child-rows', cf, '--dev', other], 'family differs')
        c['ids'][0] = 'zzz'
        json.dump(c, open(cf, 'w'))
        refuses(['pair', '--parent-rows', pf, '--child-rows', cf], 'not the same set of ids')
        c['ids'][0] = 'r7'   # restore; two DEV builds reusing the positional ids: ids align, the content differs
        p['dev_sha256'], c['dev_sha256'] = 'ab' * 32, 'cd' * 32
        json.dump(p, open(pf, 'w'))
        json.dump(c, open(cf, 'w'))
        refuses(['pair', '--parent-rows', pf, '--child-rows', cf], 'different dev_sha256')
        c['dev_sha256'] = p['dev_sha256']
        json.dump(c, open(cf, 'w'))
        run_cli(['pair', '--parent-rows', pf, '--child-rows', cf, '--out', out])   # equal shas pair; so does a file with none (above)
        assert json.load(open(out))['b'] == 3
    return 'child rows shuffled: aligned by id (b3 c1 drop 20, family and survival tables identical to the unshuffled run); a foreign --dev or a foreign id is refused; parent and child with different dev_sha256 are refused, equal ones pair'


def pair(child, dev=None):
    args = ['pair', '--parent-rows', f'{M0}/parent.in_dist.json', '--child-rows', f'{M0}/{child}.in_dist.json']
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, 'o.json')
        run_cli(args + (['--dev', dev] if dev else []) + ['--out', out])
        return json.load(open(out))


def test_pair_m0_real_files():
    if not os.path.exists(f'{M0}/parent.in_dist.json'):
        if os.environ.get('SLIP_REQUIRE_M0'):
            raise AssertionError(f'SLIP_REQUIRE_M0 is set but {M0}/parent.in_dist.json is missing')
        raise Skip(f'm0 files not present at {M0} (set SLIP_M0)')
    a = pair('L13-LBsoft10')
    assert (a['n'], a['b'], a['c']) == (1360, 12, 6) and round(a['drop'], 2) == 0.44, a
    assert abs(a['item_se'] - 100 * math.sqrt(18) / 1360) < 1e-9 and round(a['z'], 2) == 1.41
    b = pair('L12-LB', DEV if os.path.exists(DEV) else None)
    assert (b['b'], b['c']) == (786, 10) and round(b['drop'], 2) == 57.06 and b['mcnemar_p'] < 1e-100, b
    assert round(b['z'], 2) == 27.50
    return f"L13-LBsoft10 b=12 c=6 drop {a['drop']:.2f} z {a['z']:.2f} p {a['mcnemar_p']:.3g}; L12-LB b=786 c=10 drop {b['drop']:.2f} z {b['z']:.2f}"


TESTS = [test_mcnemar_exact, test_run_slip_synthetic, test_family_table, test_steps_survival, test_t_quantiles,
         test_paired_contrast_verdicts, test_n_needed, test_cli_runs_and_contrast, test_cli_dev_strata_and_big, test_check_dev_superset_real,
         test_contrast_same_rows_guard, test_pair_m0_fixture_shuffled, test_pair_m0_real_files]

if __name__ == '__main__':
    passed = skipped = 0
    for t in TESTS:
        try:
            msg = t()
        except Skip as e:
            skipped += 1
            print(f'SKIP {t.__name__}: {e}', flush=True)
            continue
        passed += 1
        print(f'PASS {t.__name__}: {msg}', flush=True)
    print(f'all {passed} tests passed' + (f' ({skipped} skipped)' if skipped else ''))
