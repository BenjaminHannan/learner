#!/usr/bin/env python3
"""python3 tests/test_gatefix.py   (Linux, no GPU, about a minute; run from a pack folder that holds the DRAFT g2fa4_supervisor.py / install_g2fa4.py / rejudge_probe.py, see tests/run_all.py).
Tests of the four gate-fix changes, plain asserts like the pack's own tests:
  A  probe checkpoint guard: keep_guard / queue_accum / main_run_hashes, and `probe-resume` refusing (exit 2, nothing run) a checkpoint of another accum, a wrong step, another config hash; a resume_warning about
     accum in a probe's events -> FAIL without judging
  B  resume_probe_verdict: new fields, Nbar = 0 cases, `verdict` and every old key identical to the ORIGINAL pack function over 1000 random traces; md_probe shows the new heading
  C  trace A: resume_mean_abs routed through miss(); installer --soft-trace-a-mean; no default changed; the three variants are never mixed
  D  rejudge_probe.py: INSIDE / UNRESOLVED / OUTSIDE synthetic cases, the verbatim pre-registered text, REJUDGE-<job>.json, --trace-a-json
The ORIGINAL pack's supervisor is loaded from G2FA4_ORIG_PACK (default: results/8a-g/pc-job-cards/g2fa4 next to the drafts) only to compare."""
import contextlib, importlib.util, io, json, os, random, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_supervisor as T
import test_probe as P
import test_addjob as AJ
import fake_runner as F
S = T.S                                                   # the DRAFT supervisor (HERE.parent)
ORIG_PACK = Path(os.environ.get('G2FA4_ORIG_PACK') or HERE.parent.parent.parent / 'pc-job-cards' / 'g2fa4')


def load_orig():
    spec = importlib.util.spec_from_file_location('orig_g2fa4_supervisor', ORIG_PACK / 'g2fa4_supervisor.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


O = load_orig()
assert O.__file__ != S.__file__, 'the original and the draft supervisor must be two different files'


def raises_exit(fn):
    try:
        fn()
    except SystemExit as e:
        return e.code
    return None


# ================================================================ A: the checkpoint guard
JOB4 = dict(id='g2fa4', arm='B3G2', accum=4, queue='8aB3G2A4-pc')
JOB8 = dict(id='g2fa8', arm='B3G2', accum=8, queue='8aB3G2A8-pc')
Q4 = '# x\ng8a-data: 8a-data\ng8a: J --rung 3M --arms B3G2 --accum B3G2=4 --device cuda --train-extra \'--ckpt-every 100 --log-every 1 --resume\'\n'
Q8 = Q4.replace('B3G2=4', 'B3G2=8')
HASH = 'ab' * 32


def t_queue_accum():
    assert S.queue_accum(Q4, 'B3G2') == (4, None) and S.queue_accum(Q8, 'B3G2') == (8, None)
    assert S.queue_accum('g8a: J --accum 16\n', 'B3G2') == (16, None)                          # a bare --accum counts for every arm
    assert S.queue_accum('g8a: J --accum G2=2 --accum B3G2=8\n', 'B3G2') == (8, None)          # another arm's value is ignored
    assert S.queue_accum('g8a: J --arms B3G2\n', 'B3G2') == (None, None)
    assert S.queue_accum('# --accum B3G2=99 in a comment\ng8a-data: --accum B3G2=98\n', 'B3G2') == (None, None)       # only g8a: lines
    v, prob = S.queue_accum(Q4 + Q8.splitlines()[-1] + '\n', 'B3G2')
    assert v is None and 'several' in prob, (v, prob)
    # the real queue files of the pack
    for name, want in (('8aB3G2A4-pc', 4), ('8aB3G2A8-pc', 8), ('8aB3G2A4b32-pc', 32)):
        assert S.queue_accum((ORIG_PACK / 'queue' / (name + '.txt')).read_text(encoding='utf-8'), 'B3G2') == (want, None), name
    print('ok queue_accum: --accum B3G2=<n> of the g8a: line (the three real queue files give 4, 8, 32)')


def t_keep_guard_unit():
    side = dict(step=200, accum=4, config_hash=HASH)
    nohash = (set(), set())
    assert S.keep_guard(JOB4, 200, side, Q4, nohash) == ([], ['config_hash not compared: the main run has no checkpoint sidecar and no resumed event to take its hash from'])
    bad, _ = S.keep_guard(JOB8, 200, side, Q8, nohash)                                      # the README case: g2fa4's accum-4 step 200 under g2fa8
    assert len(bad) == 1 and 'accum 4' in bad[0] and 'accum 8' in bad[0] and 'another job' in bad[0], bad
    bad, _ = S.keep_guard(JOB4, 100, side, Q4, nohash)                                      # --step 100 but the sidecar says 200
    assert len(bad) == 1 and 'step 200' in bad[0] and '--step' in bad[0], bad
    bad, _ = S.keep_guard(JOB4, 200, dict(side, step=None), Q4, nohash)
    assert len(bad) == 1, bad
    bad, _ = S.keep_guard(JOB4, 200, {'step': 200}, Q4, nohash)                             # a sidecar without accum cannot be checked: refused
    assert len(bad) == 1 and 'None' in bad[0], bad
    bad, _ = S.keep_guard(JOB4, 200, 'x', Q4, nohash)
    assert len(bad) == 1
    bad, _ = S.keep_guard(JOB8, 200, dict(side, accum=8), Q4, nohash)                       # queue says 4, plan says 8
    assert any('queue file says --accum 4 but plan.json says accum 8' in b for b in bad), bad
    bad, _ = S.keep_guard(dict(JOB4, accum=None), 200, side, '# x\n', nohash)                # no accum anywhere
    assert len(bad) == 1 and 'no accum found' in bad[0], bad
    assert S.keep_guard(dict(JOB4, accum=None), 200, side, Q4, nohash)[0] == []             # the queue alone is enough
    assert S.keep_guard(JOB4, 200, side, '# x\n', nohash)[0] == []                          # the plan alone is enough
    assert S.keep_guard(JOB4, 200, side, Q4, ({HASH, 'cd' * 32}, set()))[0] == []           # the hash is one of the main run's
    bad, _ = S.keep_guard(JOB4, 200, side, Q4, ({'cd' * 32}, set()))
    assert len(bad) == 1 and 'config_hash' in bad[0], bad
    assert S.keep_guard(JOB4, 200, side, Q4, (set(), {HASH[:12]}))[0] == []                 # no sidecar, but a resumed event with the 12-character prefix
    bad, _ = S.keep_guard(JOB4, 200, side, Q4, (set(), {'cd' * 6}))
    assert len(bad) == 1 and 'config_hash' in bad[0], bad
    bad, _ = S.keep_guard(JOB8, 100, dict(side, step=200), Q8, ({'cd' * 32}, set()))        # several problems are all named
    assert len(bad) == 3, bad
    print('ok keep_guard: matching passes; accum mismatch, wrong step, no accum, queue/plan conflict, other config hash are refused; no hash source is a note')


def t_main_run_hashes():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp)
        sup = S.Sup(p)
        job = sup.plan['jobs'][0]
        assert S.main_run_hashes(sup, job) == (set(), set())                                  # the fixture's main run has neither a sidecar nor a hash on its resumed event
        arm = sup.arm_dir(job)
        (arm / 'ckpt').mkdir()
        (arm / 'ckpt' / 'step-300.json').write_text(json.dumps(dict(step=300, config_hash=HASH)))
        (arm / 'ckpt' / 'step-290.json').write_text('not json')
        with open(arm / 'events.jsonl', 'a') as f:
            f.write(json.dumps(dict(event='resumed', step=100, config_hash=HASH[:12])) + '\n')
        assert S.main_run_hashes(sup, job) == ({HASH}, {HASH[:12]})
    print('ok main_run_hashes: full hashes from the sidecars of the main run\'s ckpt folder, 12-character prefixes from its resumed events')


def t_events_resume_warning():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'events.jsonl'
        f.write_text(''.join(json.dumps(x) + '\n' for x in (dict(event='segment'), dict(event='resume_warning', warning='--accum was 4 at the save, now 8'),
                                                            dict(event='resumed', step=200), dict(event='train', step=201, loss=1.0, elapsed=1))))
        ev = S.Events(f).update()
        assert [w['warning'] for w in ev.warnings] == ['--accum was 4 at the save, now 8'] and ev.resumed == [(1, 200)] and ev.last_step == 201
        ev.reset()
        assert ev.warnings == []
    print('ok Events keeps the resume_warning lines')


def probe_out(p, keep, **kw):
    return AJ.quiet(P.probe, p, keep, **kw)


def set_sidecar(keep, **kw):
    (keep / 'step-200.json').write_text(json.dumps(dict(dict(step=200, accum=4, config_hash='c0ffee' * 10), **kw)))


def no_probe_files(tmp):
    q = Path(tmp) / 'src' / 'custom_io' / 'queue_local'
    return not list(q.glob('MAINn*')) and not list((Path(tmp) / 'work' / 'results').glob('MAINn*'))


def t_probe_refuses():
    # 1. the README case: a plan whose job runs at accum 8 (queue and plan), a keep folder that holds the accum-4 checkpoint
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp, accum=8)
        (Path(tmp) / 'src' / 'custom_io' / 'queue_local' / 'MAIN-pc.txt').write_text(P.QUEUE.replace('--arms B3G2', '--arms B3G2 --accum B3G2=8'))
        set_sidecar(keep, accum=4)
        rc, out = probe_out(p, keep)
        assert rc == 2 and 'accum 4' in out and 'accum 8' in out and 'refused' in out, (rc, out)
        assert no_probe_files(tmp), 'a refused probe must not create probe queues or folders'
        set_sidecar(keep, accum=8)                                                        # the same job with its own checkpoint is accepted
        rc, out = probe_out(p, keep)
        assert rc == 0, (rc, out)
    # 2. wrong step
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp)
        set_sidecar(keep, step=100)
        rc, out = probe_out(p, keep)
        assert rc == 2 and 'not that checkpoint' in out and no_probe_files(tmp), (rc, out)
    # 3. sidecar without accum (the old fixture `{}`), unreadable sidecar
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp)
        (keep / 'step-200.json').write_text('{}')
        rc, out = probe_out(p, keep)
        assert rc == 2 and no_probe_files(tmp), (rc, out)
        (keep / 'step-200.json').write_text('not json')
        rc, out = probe_out(p, keep)
        assert rc == 2 and no_probe_files(tmp), (rc, out)
    # 4. plan says accum 4, the queue file says 8
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp)
        (Path(tmp) / 'src' / 'custom_io' / 'queue_local' / 'MAIN-pc.txt').write_text(P.QUEUE.replace('--arms B3G2', '--arms B3G2 --accum B3G2=8'))
        set_sidecar(keep)
        rc, out = probe_out(p, keep)
        assert rc == 2 and 'plan.json says accum 4' in out and no_probe_files(tmp), (rc, out)
    # 5. config hash of the main run's own checkpoint differs
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp)
        arm = Path(tmp) / 'work' / 'results' / 'MAIN-pc' / 'MAIN-3M' / 'B3G2'
        (arm / 'ckpt').mkdir()
        (arm / 'ckpt' / 'step-900.json').write_text(json.dumps(dict(step=900, accum=4, config_hash='dd' * 32)))
        set_sidecar(keep)
        rc, out = probe_out(p, keep)
        assert rc == 2 and 'config_hash' in out and no_probe_files(tmp), (rc, out)
        (arm / 'ckpt' / 'step-900.json').write_text(json.dumps(dict(step=900, accum=4, config_hash='c0ffee' * 10)))       # the same hash: accepted
        rc, out = probe_out(p, keep)
        assert rc == 0, (rc, out)
    print('ok probe-resume refuses (exit 2, no probe queue or folder made) a checkpoint of another accum, a wrong step, no accum / unreadable sidecar, a queue/plan accum conflict, another config hash; accepts the job\'s own')


def t_probe_accum_warning():
    """a resume_warning about --accum in a probe's events: verdict FAIL with the reason, no statistics."""
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp, main_extra=['--jitter', '0.01'])
        set_sidecar(keep)
        real = S.Sup.probe_run

        def with_warning(self, job, pj, keep_, step, upto):
            ev, why = real(self, job, pj, keep_, step, upto)
            ev.warnings.append(dict(event='resume_warning', warning='--accum was 4 at the save, now 8 (same rows per update; the loss is a mean of micro-batches)'))
            return ev, why
        S.Sup.probe_run = with_warning
        try:
            rc, out = probe_out(p, keep)
        finally:
            S.Sup.probe_run = real
        r = P.report(p)
        assert rc == 1 and r['verdict'] == 'FAIL' and 'n' not in r and r['why_fail'] and all('accum' in w and 'not judged' in w for w in r['why_fail']) and len(r['why_fail']) == 2, r
        assert set(r['resume_warnings']) == {'n1', 'n2'}, r
        sd = Path(json.loads(p.read_text())['state_dir'])
        assert 'Problems:' in (sd / 'PROBE-RESUME-g2fa4.md').read_text() and 'resume_warning lines' in (sd / 'PROBE-RESUME-g2fa4.md').read_text()
        # a warning that is not about accum (other code id) is recorded and does not stop the judging
        def other_warning(self, job, pj, keep_, step, upto):
            ev, why = real(self, job, pj, keep_, step, upto)
            ev.warnings.append(dict(event='resume_warning', warning='code id a at the save, b now: other code can change the run'))
            return ev, why
        S.Sup.probe_run = other_warning
        try:
            rc, out = probe_out(p, keep)
        finally:
            S.Sup.probe_run = real
        r = P.report(p)
        assert rc == 0 and r['verdict'] == 'PASS' and set(r['resume_warnings']) == {'n1', 'n2'}, r
    print('ok an accum resume_warning in a probe\'s events -> FAIL, not judged; another warning is recorded only')


# ================================================================ B: the verdict function
def t_verdict_fields():
    C = [1.0, 2.0, 3.0, 4.0]
    r = S.resume_probe_verdict(C, [1.0, 2.02, 3.0, 4.04], [1.0, 2.0, 3.02, 4.0])
    assert r['verdict'] == 'PASS'
    assert r['first_r1_c'] == 0 and r['first_r2_c'] == 0 and r['first_r1_r2'] == 0
    d1, d2, d12 = [0, 0.02, 0, 0.04], [0, 0, 0.02, 0], [0, 0.02, 0.02, 0.04]
    ab = lambda x, y: abs(x - y)
    assert abs(r['Dbar'] - (sum(d1) / 4 + sum(d2) / 4) / 2) < 1e-12 and abs(r['Nbar'] - sum(d12) / 4) < 1e-12, r
    assert abs(r['ratio'] - r['Dbar'] / r['Nbar']) < 1e-12 and abs(r['mean_form_limit'] - max(0.02, 2 * r['Nbar'])) < 1e-12
    assert r['mean_form_verdict'] == ('PASS' if r['Dbar'] <= r['mean_form_limit'] else 'FAIL')
    # the first update off
    r = S.resume_probe_verdict(C, [1.001, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
    assert abs(r['first_r1_c'] - 0.001) < 1e-12 and r['first_r2_c'] == 0 and abs(r['first_r1_r2'] - 0.001) < 1e-12
    # mean form can differ from the registered max rule: a single spike
    C = [1.0] * 50
    R1 = [1.0 + (0.5 if i == 10 else 0.015 * (-1) ** i) for i in range(50)]
    R2 = [1.0 + (0.5 if i == 10 else -0.015 * (-1) ** i) for i in range(50)]
    r = S.resume_probe_verdict(C, R1, R2)
    assert r['verdict'] == 'FAIL' and r['mean_form_verdict'] == 'PASS' and r['ratio'] < 1, r
    print('ok verdict fields: first-update gaps, Dbar, Nbar, ratio, mean-form limit and verdict (a spike fails the registered rule, passes the mean form)')


def t_verdict_nbar_zero():
    C = [1.0, 2.0, 3.0]
    r = S.resume_probe_verdict(C, [1.1, 2.0, 3.0], [1.1, 2.0, 3.0])                 # R1 == R2, both off C: Nbar = 0, Dbar > 0
    assert r['Nbar'] == 0 and r['Dbar'] > 0 and r['ratio'] == float('inf') and r['mean_form_limit'] == 0.02, r
    assert r['mean_form_verdict'] == 'FAIL' and r['lag1_autocorr'] is None and r['first_r1_r2'] == 0, r
    r = S.resume_probe_verdict(C, list(C), list(C))                                 # everything equal
    assert r['Nbar'] == 0 and r['Dbar'] == 0 and r['ratio'] == 1.0 and r['mean_form_verdict'] == 'PASS' and r['lag1_autocorr'] is None and r['verdict'] == 'PASS', r
    r = S.resume_probe_verdict(C, [1.0, 2.0, 3.0], [1.0, 2.0, 3.0 + 1e-9])        # tiny Nbar, Dbar 0..: ratio is a real number
    assert r['ratio'] > 0 and r['ratio'] < 1, r
    r = S.resume_probe_verdict([5.0], [5.0], [5.0])                                 # one update
    assert r['lag1_autocorr'] is None and r['ratio'] == 1.0
    json.dumps(r)
    print('ok Nbar = 0: ratio inf when Dbar > 0, 1.0 when both are 0; lag-1 undefined without variance')


def t_lag1():
    xs = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
    assert abs(S.lag1_autocorr(xs) - (-5 / 6)) < 1e-12                               # alternating: sum(x_t x_t+1) = -5, sum x^2 = 6
    assert S.lag1_autocorr(list(range(200))) > 0.97                          # a trend: strongly positive
    assert S.lag1_autocorr([1, 2]) is None and S.lag1_autocorr([3, 3, 3]) is None
    rng = random.Random(5)
    xs = [rng.gauss(0, 1) for _ in range(2000)]
    assert abs(S.lag1_autocorr(xs)) < 0.1                                            # white noise: near 0
    print('ok lag-1 autocorrelation: alternating -5/6, trend ~ +1, white noise ~ 0, undefined for < 3 points / no variance')


def t_verdict_identical_to_original():
    rng = random.Random(20261017)
    n_pass = n_fail = 0
    for i in range(1000):
        L = rng.choice([1, 2, 5, 20, 50, 51])
        C = [rng.uniform(0.5, 20) for _ in range(L)]
        scale = rng.choice([0, 1e-6, 1e-3, 0.01, 0.05, 0.2, 1.0])
        mode = rng.randrange(6)
        R1 = [c + rng.uniform(-scale, scale) for c in C]
        if mode == 0:
            R2 = list(R1)                                                           # n == 0
        elif mode == 1:
            R2 = [c + rng.uniform(-scale, scale) for c in C]
        elif mode == 2:
            R2 = [c + s for c, s in zip(R1, [rng.choice([0, 0.01, 0.1]) for _ in C])]
        elif mode == 3:
            R1, R2 = list(C), list(C)                                               # everything equal
        elif mode == 5:
            off = rng.choice([0.0, 0.05, 0.1, 0.12, 0.3, 0.6])                         # both resumes off the run by the same amount (n tiny, d large)
            R1 = [c + off + rng.uniform(-scale, scale) * 0.01 for c in C]
            R2 = [r + rng.uniform(-scale, scale) * 0.01 for r in R1]
        else:
            R2 = [c + rng.uniform(-scale, scale) for c in C]
            R1[rng.randrange(L)] += rng.choice([0.0, 0.1, 0.3])                      # a spike, sometimes right at a limit
        old, new = O.resume_probe_verdict(C, R1, R2), S.resume_probe_verdict(C, R1, R2)
        assert json.dumps(old, sort_keys=True) == json.dumps({k: new[k] for k in old}, sort_keys=True), (i, old, new)
        assert old['verdict'] == new['verdict'] and repr(old['limit']) == repr(new['limit']) and repr(old['n']) == repr(new['n']) and repr(old['d']) == repr(new['d'])
        assert set(new) - set(old) == {'first_r1_c', 'first_r2_c', 'first_r1_r2', 'Dbar', 'Nbar', 'ratio', 'mean_form_limit', 'mean_form_verdict', 'lag1_autocorr'}
        n_pass += old['verdict'] == 'PASS'
        n_fail += old['verdict'] == 'FAIL'
    assert n_pass > 100 and n_fail > 100, (n_pass, n_fail)                           # both branches were exercised
    # exactly at the limit (d == limit): same side as before
    C = [1.0, 1.0]
    for R1, R2 in (([1.1, 1.0], [1.0, 1.0]), ([1.3, 1.0], [1.0, 1.0]), ([1.0, 1.0], [1.0, 1.0])):
        assert O.resume_probe_verdict(C, R1, R2)['verdict'] == S.resume_probe_verdict(C, R1, R2)['verdict']
    for bad in (([], [], []), ([1.0], [1.0, 2.0], [1.0])):
        for mod in (O, S):
            try:
                mod.resume_probe_verdict(*bad)
            except AssertionError:
                pass
            else:
                raise AssertionError('unequal / empty lists must still be refused')
    print(f'ok `verdict` and every old key identical to the original pack function over 1000 random traces ({n_pass} PASS, {n_fail} FAIL); only the 9 new keys are added')


def t_md_probe():
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp, main_extra=['--jitter', '0.01'])
        set_sidecar(keep)
        assert probe_out(p, keep)[0] == 0
        r = P.report(p)
        assert 'Dbar' in r and 'first_r1_c' in r and r['mean_form_verdict'] in ('PASS', 'FAIL') and 'lag1_autocorr' in r
        sd = Path(json.loads(p.read_text())['state_dir'])
        md = (sd / 'PROBE-RESUME-g2fa4.md').read_text()
        assert '## recorded beside (pre-registered mean form, not the registered gate)' in md and 'Dbar' in md and 'Nbar' in md and 'lag-1' in md, md
        assert md.index('registered gate') > md.index('| 201 |'), 'the new section goes after the table'
    old_style = dict(job='j', verdict='PASS', step=200, upto=201, why_fail=[], n=0.0, d=0.0, limit=0.1, mean_abs_r1_r2=0, mean_abs_r1_c=0, mean_abs_r2_c=0, steps=[201], C=[1.0], R1=[1.0], R2=[1.0],
                     diff_r1_r2=[0], diff_r1_c=[0], diff_r2_c=[0])
    assert 'recorded beside' not in S.Sup.md_probe(old_style)                          # a PROBE json of the old format still renders
    inf = dict(old_style, Dbar=0.1, Nbar=0.0, ratio=float('inf'), first_r1_c=0, first_r2_c=0, first_r1_r2=0, mean_form_limit=0.02, mean_form_verdict='FAIL', lag1_autocorr=None)
    assert 'ratio Dbar/Nbar = inf' in S.Sup.md_probe(inf) and 'not defined' in S.Sup.md_probe(inf)
    print('ok md_probe: the "recorded beside (pre-registered mean form, not the registered gate)" section after the table; old-format reports still render; inf ratio renders')


# ================================================================ C: trace A mean item, installer flag
RULES = dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10)
SOFT3 = ['peak', 'resume_max_abs', 'resume_mean_abs']


def t_trace_a_mean_routing():
    ev_mean = AJ.FakeEv(0.05, mean_diff_each=0.03)                                   # mean of the 50 redone diffs ~ 0.03 > 0.02; the largest 0.05 < 0.10
    hard = S.trace_a(ev_mean, RULES, 9000)
    assert hard['verdict'] == 'FAIL' and len(hard['why_fail']) == 1 and 'on average' in hard['why_fail'][0] and hard['soft_misses'] == [], hard
    for soft in (['peak', 'resume_max_abs'], ['resume_max_abs'], []):                  # the existing soft lists do NOT release the mean item
        assert S.trace_a(ev_mean, dict(RULES, soft=soft), 9000)['verdict'] == 'FAIL', soft
    r = S.trace_a(ev_mean, dict(RULES, soft=SOFT3), 9000)
    assert r['verdict'] == 'PASS' and r['why_fail'] == [] and len(r['soft_misses']) == 1 and 'on average' in r['soft_misses'][0], r
    assert S.trace_a(ev_mean, dict(RULES, soft=['resume_mean_abs']), 9000)['verdict'] == 'PASS'
    # everything else stays hard in the most permissive variant
    soft = dict(RULES, soft=SOFT3)
    ev = AJ.FakeEv(0.0)
    for e in ev.train:
        if e['seg'] == 2 and e['step'] == 101:
            e['loss'] += 0.02
    assert S.trace_a(ev, soft, 9000)['verdict'] == 'FAIL' and 'first redone' in S.trace_a(ev, soft, 9000)['why_fail'][0]          # the first redone update (0.01)
    ev = AJ.FakeEv(0.0)
    ev.nonfinite = True
    assert S.trace_a(ev, soft, 9000)['verdict'] == 'FAIL'                                                                       # NaN / Inf
    flat = AJ.FakeEv(0.0)
    for e in flat.train:
        e['loss'] = 5.0
    assert S.trace_a(flat, soft, 9000)['verdict'] == 'FAIL'                                                                     # the loss does not fall
    # peak and max stay recordable alongside; all three trip together and are only recorded
    r = S.trace_a(AJ.FakeEv(0.119, mean_diff_each=0.03), soft, 15757)
    assert r['verdict'] == 'PASS' and len(r['soft_misses']) == 3, r
    # the g2fa4 case as registered (no soft list): same result as the ORIGINAL function
    for ev in (AJ.FakeEv(0.119), AJ.FakeEv(0.05, 0.03), AJ.FakeEv(0.0)):
        a, b = O.trace_a(ev, RULES, 15757), S.trace_a(ev, RULES, 15757)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), (a, b)
        a, b = O.trace_a(ev, dict(RULES, soft=['peak', 'resume_max_abs']), 15757), S.trace_a(ev, dict(RULES, soft=['peak', 'resume_max_abs']), 15757)
        assert a['verdict'] == b['verdict'] or a['why_fail'] != [] and b['why_fail'] == [], (a, b)    # (only the mean item may now be released, and only by naming it)
    for ev in (AJ.FakeEv(0.119), AJ.FakeEv(0.0), AJ.FakeEv(0.05)):                                                                # without the mean item in soft the result is identical to the original, soft or not
        for sl in (None, ['peak', 'resume_max_abs']):
            rr = dict(RULES, soft=sl) if sl else RULES
            assert json.dumps(O.trace_a(ev, rr, 15757), sort_keys=True) == json.dumps(S.trace_a(ev, rr, 15757), sort_keys=True)
    print('ok trace A: resume_mean_abs is hard unless listed in rules.soft (then recorded in soft_misses); first-update, NaN, loss-falls hard in every variant; no soft list or the existing soft list = the original behaviour')


def t_installer_soft_mean():
    with tempfile.TemporaryDirectory() as tmp:                                       # defaults unchanged
        I = AJ.installed_pc(tmp)
        assert I.SOFT_TRACE_A == ['peak', 'resume_max_abs'] and I.SOFT_TRACE_A_MEAN == SOFT3
        g4 = json.loads((I.STATE / 'plan.json').read_text())['jobs'][0]
        assert 'soft' not in g4['trace_a']
        assert I.new_job_entry('g2fa8', g4) == AJ.expected_g2fa8(I) and I.new_job_entry('g2fa8', g4, True) == AJ.expected_g2fa8(I, soft=True)
        want = AJ.expected_g2fa8(I, soft=True)
        want['trace_a']['soft'] = SOFT3
        assert I.new_job_entry('g2fa8', g4, True, True) == want and I.new_job_entry('g2fa8', g4, False, True) == AJ.expected_g2fa8(I), 'soft_mean without soft changes nothing'
    # the flag alone is a usage error
    for args in (['--soft-trace-a-mean'], ['--add-job', 'g2fa8', '--soft-trace-a-mean'], ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a-mean']):
        with tempfile.TemporaryDirectory() as tmp:
            I = AJ.load_installer(tmp)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = raises_exit(lambda: I.main(args))
            assert code == 2 and 'only goes together with --soft-trace-a' in err.getvalue(), (args, code, err.getvalue())
    with tempfile.TemporaryDirectory() as tmp:
        I = AJ.installed_pc(tmp)
        before = AJ.pc_files(I)
        I.STAMP = 'M1'
        rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a', '--soft-trace-a-mean', '--check'])
        assert rc == 0 and 'CHECK ONLY' in out and AJ.pc_files(I) == before and '--soft-trace-a-mean' in out, out
        rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a', '--soft-trace-a-mean'])
        assert rc == 0 and 'ADD-JOB g2fa8 DONE' in out, out
        new = json.loads((I.STATE / 'plan.json').read_text())
        want = AJ.expected_g2fa8(I, soft=True)
        want['trace_a']['soft'] = SOFT3
        assert new['jobs'][1] == want and new['jobs'][0].get('skip') is True, new['jobs'][1]
        sup = S.Sup(I.STATE / 'plan.json')
        assert sup.plan['jobs'][1]['trace_a']['soft'] == SOFT3
        assert S.trace_a(AJ.FakeEv(0.05, 0.03), sup.plan['jobs'][1]['trace_a'], 9000)['verdict'] == 'PASS'      # the installed rules release the mean item
        # idempotent
        before2 = AJ.pc_files(I)
        I.STAMP = 'M2'
        rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a', '--soft-trace-a-mean'])
        after2 = AJ.pc_files(I)
        assert rc == 0 and {k for k in set(before2) | set(after2) if before2.get(k) != after2.get(k)} == {'add-job-g2fa8-M2.txt'}, out
        # the other two variants after this one are refused, nothing changes
        for args in (['--skip-g2fa4', '--soft-trace-a'], ['--skip-g2fa4']):
            b = AJ.pc_files(I)
            I.STAMP = 'M3'
            rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8'] + args)
            assert rc == 1 and 'differs from the expected entry' in out and AJ.pc_files(I) == b, (args, out)
    # the other direction: soft first, then soft + mean; strict first, then soft + mean
    for first in (['--soft-trace-a'], []):
        with tempfile.TemporaryDirectory() as tmp:
            I = AJ.installed_pc(tmp)
            I.STAMP = 'N1'
            rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'] + first)
            assert rc == 0, out
            b = AJ.pc_files(I)
            I.STAMP = 'N2'
            rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a', '--soft-trace-a-mean'])
            assert rc == 1 and 'differs from the expected entry' in out and AJ.pc_files(I) == b, (first, out)
    print('ok installer --soft-trace-a-mean: only with --soft-trace-a; entry soft = [peak, resume_max_abs, resume_mean_abs]; check changes nothing; idempotent; the three variants are never mixed; defaults unchanged')


# ================================================================ D: rejudge_probe.py
def load_rejudge():
    spec = importlib.util.spec_from_file_location('rejudge_probe', HERE.parent / 'rejudge_probe.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


R = load_rejudge()
CL = [3.0 - 0.01 * i for i in range(50)]


def alt(a, first_exact=True):
    """R1 = C + a_i, R2 = C - a_i (|R1-R2| = 2 a_i, Dbar = mean a, ratio 0.5); the first update exact."""
    am = [0.0 if (first_exact and i == 0) else a for i in range(50)]
    return [c + x for c, x in zip(CL, am)], [c - x for c, x in zip(CL, am)]


def t_rejudge_cases():
    r1, r2 = alt(0.015)                                                              # noise 0.015: Nbar ~ 0.029, limit ~ 0.059 >= 0.0282
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'INSIDE healthy noise' and r['restore_ok'] and r['exchangeability_ok'] and r['noise_limit'] > 0.0282 and r['ratio'] < 1, r
    r1, r2 = alt(0.003)                                                              # calm window: Nbar ~ 0.006, limit 0.02 < 0.0282
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'UNRESOLVED' and r['restore_ok'] and r['exchangeability_ok'] and r['noise_limit'] == 0.02, r
    assert R.rejudge(CL, r1, r2, 0.0199)['verdict'] == 'INSIDE healthy noise' and R.rejudge(CL, r1, r2, 0.02)['verdict'] == 'INSIDE healthy noise' and R.rejudge(CL, r1, r2, 0.0201)['verdict'] == 'UNRESOLVED'   # v <= limit
    # OUTSIDE (a): the restore check fails at the first update
    r1, r2 = alt(0.015, first_exact=False)
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'OUTSIDE' and not r['restore_ok'] and r['exchangeability_ok'], r
    r1, r2 = alt(0.015)
    r1[0] += 1e-9                                                                    # "exactly" 0, not nearly
    assert R.rejudge(CL, r1, r2)['verdict'] == 'OUTSIDE'
    r1, r2 = alt(0.015)
    r2[0] -= 1e-9
    assert R.rejudge(CL, r1, r2)['verdict'] == 'OUTSIDE'
    # OUTSIDE (b): exchangeability fails by the ratio: both restarts agree with each other but differ from the run (Nbar 0 -> ratio inf)
    r1 = [c + (0 if i == 0 else 0.05) for i, c in enumerate(CL)]
    r = R.rejudge(CL, r1, list(r1))
    assert r['verdict'] == 'OUTSIDE' and r['restore_ok'] and r['ratio'] == float('inf') and not r['exchangeability_ok'] and r['Nbar'] == 0, r
    # ratio above 2 while the registered rule passes: both restarts are off the run by nearly the same amount
    r1 = [c + (0 if i == 0 else 0.03) for i, c in enumerate(CL)]
    r2 = [c + (0 if i == 0 else 0.0255) for i, c in enumerate(CL)]                   # Dbar ~ 0.0277, Nbar ~ 0.0044 -> ratio ~ 6 but the registered rule passes
    r = R.rejudge(CL, r1, r2)
    assert r['registered_verdict'] == 'PASS' and r['ratio'] > 2 and r['verdict'] == 'OUTSIDE' and not r['exchangeability_ok'], r
    # OUTSIDE (c): the registered max rule fails with a ratio <= 2 (one spike both restarts share)
    a = [0.0] + [0.015 * (-1) ** i for i in range(1, 50)]
    s1 = [c + x for c, x in zip(CL, a)]
    s2 = [c - x for c, x in zip(CL, a)]
    s1[10] += 0.5
    s2[10] += 0.5
    r = R.rejudge(CL, s1, s2)
    assert r['registered_verdict'] == 'FAIL' and r['ratio'] <= 2.0 and r['verdict'] == 'OUTSIDE' and not r['exchangeability_ok'] and r['restore_ok'], r
    # all identical
    r = R.rejudge(CL, list(CL), list(CL))
    assert r['ratio'] == 1.0 and r['Dbar'] == 0 and r['verdict'] == 'UNRESOLVED', r        # v = 0.0282 > 0.02
    assert R.rejudge(CL, list(CL), list(CL), 0.01)['verdict'] == 'INSIDE healthy noise'
    for bad in (([], [], []), ([1.0], [1.0, 2.0], [1.0])):
        try:
            R.rejudge(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError
    # the pure function agrees with the supervisor's recorded numbers
    for a_ in (0.003, 0.015):
        r1, r2 = alt(a_)
        x, y = R.rejudge(CL, r1, r2), S.resume_probe_verdict(CL, r1, r2)
        for k_x, k_y in (('Dbar', 'Dbar'), ('Nbar', 'Nbar'), ('ratio', 'ratio'), ('first_r1_c', 'first_r1_c'), ('first_r2_c', 'first_r2_c'), ('registered_verdict', 'verdict'), ('n', 'n'), ('d', 'd')):
            assert x[k_x] == y[k_y], (k_x, x[k_x], y[k_y])
        assert x['noise_limit'] == y['mean_form_limit']
    print('ok rejudge: INSIDE / UNRESOLVED / OUTSIDE (restore check, ratio, registered rule) and the boundaries v <= limit, exact zero at the first update; agrees with the supervisor\'s numbers')


def write_probe(d, job, C, R1, R2, **kw):
    f = Path(d) / f'PROBE-RESUME-{job}.json'
    f.write_text(json.dumps(dict(dict(job=job, step=200, upto=250, why_fail=[], verdict='PASS', C=C, R1=R1, R2=R2), **kw)))
    return f


def t_rejudge_cli():
    doc = R.__doc__
    for line in R.PREREG.splitlines():
        assert line in doc, line                                                       # the pre-registered text is in the docstring verbatim
    with tempfile.TemporaryDirectory() as tmp:
        r1, r2 = alt(0.003)
        f = write_probe(tmp, 'g2fa8', CL, r1, r2)
        rc, out = AJ.quiet(R.main, [str(f)])
        assert rc == 1 and 'UNRESOLVED' in out and R.PREREG in out and 'only a same-window measurement' in out, (rc, out)
        j = json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())
        assert j['verdict'] == 'UNRESOLVED' and j['job'] == 'g2fa8' and j['trace_a_value'] == 0.0282 and j['trace_a_value_from'] == 'default' and j['preregistered_reading'] == R.PREREG and j['plain_words'] in out, j
        rc, out = AJ.quiet(R.main, [str(f), '--trace-a-mean', '0.015'])
        assert rc == 0 and 'INSIDE healthy noise' in out and json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())['trace_a_value_from'] == '--trace-a-mean'
        # --trace-a-json: a TRACE-A json and a state.json
        ta = Path(tmp) / 'TRACE-A-g2fa8.json'
        ta.write_text(json.dumps(dict(verdict='PASS', resume=dict(mean_abs=0.0167, max_abs=0.119))))
        rc, out = AJ.quiet(R.main, [str(f), '--trace-a-json', str(ta)])
        assert rc == 0 and json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())['trace_a_value'] == 0.0167
        st = Path(tmp) / 'state.json'
        st.write_text(json.dumps(dict(jobs=dict(g2fa8=dict(traceA=dict(resume=dict(mean_abs=0.0282)))))))
        rc, out = AJ.quiet(R.main, [str(f), '--trace-a-json', str(st)])
        assert rc == 1 and json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())['trace_a_value'] == 0.0282
        rc, out = AJ.quiet(R.main, [str(f), '--trace-a-json', str(st), '--trace-a-mean', '0.01'])          # the flag wins
        assert rc == 0 and json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())['trace_a_value'] == 0.01
        ta.write_text(json.dumps(dict(verdict='FAIL', resume=None)))
        rc, out = AJ.quiet(R.main, [str(f), '--trace-a-json', str(ta)])
        assert rc == 3 and 'no resume.mean_abs' in out
        # OUTSIDE
        r1, r2 = alt(0.015, first_exact=False)
        f2 = write_probe(tmp, 'g2fa9', CL, r1, r2)
        rc, out = AJ.quiet(R.main, [str(f2)])
        assert rc == 2 and 'OUTSIDE' in out and R.RESTORE_MSG in out and (Path(tmp) / 'REJUDGE-g2fa9.json').exists(), out
        # a probe that was refused to judge / a missing file / not json
        f3 = write_probe(tmp, 'g2fa7', CL, r1, r2, why_fail=['n1: train.py warned about --accum on resume'])
        rc, out = AJ.quiet(R.main, [str(f3)])
        assert rc == 3 and 'did not judge' in out and not (Path(tmp) / 'REJUDGE-g2fa7.json').exists()
        assert AJ.quiet(R.main, [str(Path(tmp) / 'nope.json')])[0] == 3
        (Path(tmp) / 'bad.json').write_text('{')
        assert AJ.quiet(R.main, [str(Path(tmp) / 'bad.json')])[0] == 3
        # the report of a real probe run by the draft supervisor (fake runner) can be re-read
        Path(tmp, 'pr').mkdir()
        p, keep = P.setup(str(Path(tmp, 'pr')))                                    # no jitter: the two resumes and the run agree exactly
        set_sidecar(keep)
        assert probe_out(p, keep)[0] == 0
        sd = Path(json.loads(p.read_text())['state_dir'])
        rc, out = AJ.quiet(R.main, [str(sd / 'PROBE-RESUME-g2fa4.json'), '--trace-a-mean', '0.0282'])
        # (the fake runner rounds its losses to 5 decimals, the fixture's C is not rounded: the first update differs by ~1e-6, and the exact-zero restore check says so)
        assert rc == 2 and 'OUTSIDE' in out and R.RESTORE_MSG in out and (sd / 'REJUDGE-g2fa4.json').exists(), (rc, out)
        pj = json.loads((sd / 'PROBE-RESUME-g2fa4.json').read_text())
        assert 0 < pj['first_r1_c'] < 1e-5 and pj['first_r1_c'] == pj['first_r2_c'], pj['first_r1_c']
        fx = write_probe(tmp, 'fixture', pj['R1'], pj['R1'], pj['R2'])                                        # C := R1: now R1 is exactly the run
        rc, out = AJ.quiet(R.main, [str(fx)])
        assert rc == 1 and (Path(tmp) / 'REJUDGE-fixture.json').exists()
    # runs as a script
    with tempfile.TemporaryDirectory() as tmp:
        r1, r2 = alt(0.015)
        f = write_probe(tmp, 'g2fa8', CL, r1, r2)
        cp = subprocess.run([sys.executable, str(HERE.parent / 'rejudge_probe.py'), str(f)], capture_output=True, text=True)
        assert cp.returncode == 0 and 'INSIDE healthy noise' in cp.stdout, (cp.returncode, cp.stdout, cp.stderr)
    print('ok rejudge_probe.py: verbatim text in docstring and output, REJUDGE-<job>.json, exit codes 0/1/2/3, --trace-a-mean / --trace-a-json (TRACE-A and state.json), runs as a script')


if __name__ == '__main__':
    todo = [t_queue_accum, t_keep_guard_unit, t_main_run_hashes, t_events_resume_warning, t_probe_refuses, t_probe_accum_warning,
            t_verdict_fields, t_verdict_nbar_zero, t_lag1, t_verdict_identical_to_original, t_md_probe,
            t_trace_a_mean_routing, t_installer_soft_mean, t_rejudge_cases, t_rejudge_cli]
    only = sys.argv[1:]
    try:
        for t in todo:
            if not only or t.__name__ in only:
                try:
                    t()
                finally:
                    T.cleanup()
        print('GATEFIX TESTS OK (%d tests)' % len([t for t in todo if not only or t.__name__ in only]))
    finally:
        T.cleanup()
