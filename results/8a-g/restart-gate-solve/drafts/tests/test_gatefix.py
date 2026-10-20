#!/usr/bin/env python3
"""python3 tests/test_gatefix.py   (Linux, no GPU, about a minute; run from a pack folder that holds the DRAFT g2fa4_supervisor.py / install_g2fa4.py / rejudge_probe.py, see tests/run_all.py).
Tests of the four gate-fix changes, plain asserts like the pack's own tests:
  A  probe checkpoint guard: keep_guard / queue_accum / main_run_hashes, and `probe-resume` refusing (exit 2, nothing run) a checkpoint of another accum, a wrong step, another config hash; a resume_warning about
     accum in a probe's events -> FAIL without judging
  B  resume_probe_verdict: new fields, Nbar = 0 cases, `verdict` and every old key identical to the ORIGINAL pack function over 1000 random traces; md_probe shows the new heading
  C  trace A: resume_mean_abs routed through miss(); installer --soft-trace-a-mean; no default changed; the three variants are never mixed
  D  rejudge_probe.py: INSIDE / UNRESOLVED / OUTSIDE synthetic cases, the verbatim pre-registered text, REJUDGE-<job>.json, --trace-a-json
  E  Amendment 1 (PREREG-trace-a2.md): trace A opt-in rule keys resume_early_abs / resume_exact_fields (absent = the same result as the original, plus the recorded early_max), probe early_max / early_limit /
     early_verdict, installer --trace-a-early (+ idempotency, variants never mixed), rejudge_probe.py amended reading (INSIDE / UNRESOLVED / UNRESOLVED_CALIBRATE / OUTSIDE by P1 / by P1b) and --calibration
  H  item 7 (ruling Q95): the early window (updates step+2 and step+3) is refused when it cannot be computed (< 3 updates): probe-resume --upto < step+3 exits 3 and touches nothing, resume_probe_verdict / md_probe /
     trace_a emit no early field below 3 updates, and the supervisor agrees with rejudge_probe.py (same 2-update data: both exit 3; from 3 updates: the same early_max)
  I  ruling B2: an early window trace A cannot compute (under 3 redone updates, with resume_early_abs set) is deferred to probe P1b (early_window computed False, no early_max, a verbatim line in the TRACE-A md,
     status.md and the finish message), not a stop; first-update gaps / exact-field mismatches / early_max > 0.005 (>= 3 redone updates) still FAIL; end to end against the fake runner
  J  ruling B3: a window whose 2nd / 3rd redone update is not rstep+2 / rstep+3 is not computable (same deferral, no early_max); with an opt-in key set, a missing first redone update rstep+1 fails closed
     (the first-update item would be computed on another update); without the opt-in keys trace_a is the original's
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
        added = {'first_r1_c', 'first_r2_c', 'first_r1_r2', 'Dbar', 'Nbar', 'ratio', 'mean_form_limit', 'mean_form_verdict', 'lag1_autocorr'}
        assert set(new) - set(old) == added | ({'early_max', 'early_limit', 'early_verdict'} if L >= 3 else set()), (L, set(new) - set(old))          # (Q95: the early keys only with >= 3 updates)
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
    print(f'ok `verdict` and every old key identical to the original pack function over 1000 random traces ({n_pass} PASS, {n_fail} FAIL); only the new keys are added (9 mean-form, + 3 early-window when there are >= 3 updates)')


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
        assert 'early window (the 2nd and 3rd probe updates = 202 and 203, P1b): max |R - C| = ' in md and 'limit 0.005: ' in md and 'P1b' in md, md          # (the jittered fixture may sit either side of 0.005)
    old_style = dict(job='j', verdict='PASS', step=200, upto=201, why_fail=[], n=0.0, d=0.0, limit=0.1, mean_abs_r1_r2=0, mean_abs_r1_c=0, mean_abs_r2_c=0, steps=[201], C=[1.0], R1=[1.0], R2=[1.0],
                     diff_r1_r2=[0], diff_r1_c=[0], diff_r2_c=[0])
    assert 'recorded beside' not in S.Sup.md_probe(old_style)                          # a PROBE json of the old format still renders
    inf = dict(old_style, Dbar=0.1, Nbar=0.0, ratio=float('inf'), first_r1_c=0, first_r2_c=0, first_r1_r2=0, mean_form_limit=0.02, mean_form_verdict='FAIL', lag1_autocorr=None)
    assert 'ratio Dbar/Nbar = inf' in S.Sup.md_probe(inf) and 'not defined' in S.Sup.md_probe(inf) and 'early window' not in S.Sup.md_probe(inf)      # (a report from before Amendment 1 has no early_max)
    assert 'early window (the 2nd and 3rd probe updates, P1b): max |R - C| = 0.012000; limit 0.005: FAIL' in S.Sup.md_probe(dict(inf, early_max=0.012, early_limit=0.005, early_verdict='FAIL')), 'no steps key: no update numbers'
    print('ok md_probe: the "recorded beside (pre-registered mean form, not the registered gate)" section after the table; old-format reports still render; inf ratio renders')


# ================================================================ C: trace A mean item, installer flag
RULES = dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10)
SOFT3 = ['peak', 'resume_max_abs', 'resume_mean_abs']


def strip_early(r):
    """trace_a result without the always-recorded Amendment-1 key resume.early_max (the one addition to the default output); the original never has it"""
    r = json.loads(json.dumps(r))
    if r.get('resume'):
        r['resume'].pop('early_max', None)
    return r


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
        assert json.dumps(a, sort_keys=True) == json.dumps(strip_early(b), sort_keys=True), (a, b)
        a, b = O.trace_a(ev, dict(RULES, soft=['peak', 'resume_max_abs']), 15757), S.trace_a(ev, dict(RULES, soft=['peak', 'resume_max_abs']), 15757)
        assert a['verdict'] == b['verdict'] or a['why_fail'] != [] and b['why_fail'] == [], (a, b)    # (only the mean item may now be released, and only by naming it)
    for ev in (AJ.FakeEv(0.119), AJ.FakeEv(0.0), AJ.FakeEv(0.05)):                                                                # without the mean item in soft the result is identical to the original, soft or not
        for sl in (None, ['peak', 'resume_max_abs']):
            rr = dict(RULES, soft=sl) if sl else RULES
            assert json.dumps(O.trace_a(ev, rr, 15757), sort_keys=True) == json.dumps(strip_early(S.trace_a(ev, rr, 15757)), sort_keys=True)
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


def alt(a, first_exact=True, early=1e-4):
    """R1 = C + a_i, R2 = C - a_i (|R1-R2| = 2 a_i, Dbar = mean a, ratio 0.5); the first update exact, the 2nd and 3rd update `early` (healthy: well under 0.005)."""
    am = [0.0 if (first_exact and i == 0) else early if i in (1, 2) else a for i in range(50)]
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
    # (b) exchangeability fails by the ratio: both restarts agree with each other but differ from the run (Nbar 0 -> ratio inf). Amended reading: with P1 and P1b holding this is UNRESOLVED_CALIBRATE, not OUTSIDE
    r1 = [c + (0 if i in (0, 1, 2) else 0.05) for i, c in enumerate(CL)]
    r = R.rejudge(CL, r1, list(r1))
    assert r['verdict'] == 'UNRESOLVED_CALIBRATE' and r['restore_ok'] and r['early_ok'] and r['ratio'] == float('inf') and not r['exchangeability_ok'] and r['Nbar'] == 0, r
    assert r['original_reading_verdict'] == 'OUTSIDE', r
    # ratio above 2 while the registered rule passes: both restarts are off the run by nearly the same amount
    r1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(CL)]
    r2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(CL)]           # Dbar ~ 0.0277, Nbar ~ 0.0044 -> ratio ~ 6 but the registered rule passes
    r = R.rejudge(CL, r1, r2)
    assert r['registered_verdict'] == 'PASS' and r['ratio'] > 2 and r['verdict'] == 'UNRESOLVED_CALIBRATE' and not r['exchangeability_ok'] and not r['p23_ok'], r
    # (c) the registered max rule fails with a ratio <= 2 (one spike both restarts share): UNRESOLVED_CALIBRATE too (P1, P1b hold)
    a = [0.0, 1e-4, 1e-4] + [0.015 * (-1) ** i for i in range(3, 50)]
    s1 = [c + x for c, x in zip(CL, a)]
    s2 = [c - x for c, x in zip(CL, a)]
    s1[10] += 0.5
    s2[10] += 0.5
    r = R.rejudge(CL, s1, s2)
    assert r['registered_verdict'] == 'FAIL' and r['ratio'] <= 2.0 and r['verdict'] == 'UNRESOLVED_CALIBRATE' and not r['exchangeability_ok'] and r['restore_ok'] and r['early_ok'] and not r['p23_ok'], r
    # all identical
    r = R.rejudge(CL, list(CL), list(CL))
    assert r['ratio'] == 1.0 and r['Dbar'] == 0 and r['verdict'] == 'UNRESOLVED', r        # v = 0.0282 > 0.02
    assert R.rejudge(CL, list(CL), list(CL), 0.01)['verdict'] == 'INSIDE healthy noise'
    for bad in (([], [], []), ([1.0], [1.0, 2.0], [1.0]), ([1.0, 2.0], [1.0, 2.0], [1.0, 2.0])):       # (the last: under 3 updates, no early window)
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
    print('ok rejudge: INSIDE / UNRESOLVED (window) / UNRESOLVED_CALIBRATE (ratio, P3, registered rule) / OUTSIDE (restore check) and the boundaries v <= limit, exact zero at the first update; agrees with the supervisor\'s numbers')


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


# ================================================================ E: Amendment 1 (early window, exact fields, calibration)
EARLY_RULES = dict(RULES, resume_early_abs=0.005, resume_exact_fields=['lr', 'rounds', 'plan_'])
EARLY_ONLY = dict(RULES, resume_early_abs=0.005)                       # the early-window item alone (no listed exact fields)


def with_fields(ev, **extra):
    """give every line of a FakeEv the logged fields train.py has besides the loss (identical in both segments)"""
    for e in ev.train:
        e.update(lr=1e-3, rounds=3.0, plan_rows=5.0, plan_gapped=1.0, **extra)
    return ev


def bump(ev, seg, step, **kw):
    for e in ev.train:
        if e['seg'] == seg and e['step'] == step:
            for k, v in kw.items():
                e[k] = e.get(k, 0) + v if k == 'loss' else v
    return ev


def t_trace_a_early_optin():
    # opt-in absent: same result as the original in every outcome (plus the recorded early_max), whatever the early updates do
    for ev in (AJ.FakeEv(0.0), AJ.FakeEv(0.119), AJ.FakeEv(0.05, 0.03), AJ.FakeEv(0.0, 0.2)):
        for rules in (RULES, dict(RULES, soft=['peak', 'resume_max_abs'])):
            a, b = O.trace_a(ev, rules, 15757), S.trace_a(ev, rules, 15757)
            assert json.dumps(a, sort_keys=True) == json.dumps(strip_early(b), sort_keys=True), (a, b)
            assert 'exact_checked' not in b['resume'] and 'exact_mismatch' not in b['resume']                 # (only the opt-in rule adds these)
    ev = bump(AJ.FakeEv(0.0), 2, 103, loss=0.04)                                         # a large early difference, no rule: PASS as before (mean 0.001 + one 0.04, max 0.04 < 0.10)
    r = S.trace_a(ev, RULES, 9000)
    assert r['verdict'] == 'PASS' and abs(r['resume']['early_max'] - 0.041) < 1e-9, r
    # early_max recorded for the 2nd and 3rd redone updates only (steps 102 and 103), not the first and not the 4th
    ev = bump(bump(AJ.FakeEv(0.0, 0.0), 2, 101, loss=0.009), 2, 104, loss=0.05)
    assert S.trace_a(ev, RULES, 9000)['resume']['early_max'] == 0.0
    ev = bump(AJ.FakeEv(0.0, 0.0), 2, 102, loss=0.003)
    assert abs(S.trace_a(ev, RULES, 9000)['resume']['early_max'] - 0.003) < 1e-9
    # the rule keys do not change the loss statistics
    a, b = S.trace_a(AJ.FakeEv(0.05, 0.003), RULES, 9000), S.trace_a(with_fields(AJ.FakeEv(0.05, 0.003)), EARLY_RULES, 9000)
    assert all(a['resume'][k] == b['resume'][k] for k in ('resumed_step', 'n_redone', 'first_diff', 'mean_abs', 'max_abs', 'early_max')) and a['verdict'] == b['verdict'] == 'PASS'
    # the early item: pass below, fail above; hard
    r = S.trace_a(AJ.FakeEv(0.0, 0.004), EARLY_ONLY, 9000)                              # 0.004 at every redone update 102..150: mean 0.004 < 0.02
    assert r['verdict'] == 'PASS' and r['why_fail'] == [] and abs(r['resume']['early_max'] - 0.004) < 1e-9, r
    r = S.trace_a(AJ.FakeEv(0.0, 0.006), EARLY_ONLY, 9000)                              # mean 0.006 < 0.02 would pass the old rules
    assert S.trace_a(AJ.FakeEv(0.0, 0.006), RULES, 9000)['verdict'] == 'PASS'
    assert r['verdict'] == 'FAIL' and len(r['why_fail']) == 1 and 'early redone updates 102 and 103' in r['why_fail'][0] and '(limit 0.005)' in r['why_fail'][0], r
    ev = bump(AJ.FakeEv(0.0, 0.0), 2, 103, loss=0.007)                                   # only the 3rd redone update: named
    r = S.trace_a(ev, EARLY_ONLY, 9000)
    assert r['verdict'] == 'FAIL' and 'at update 103' in r['why_fail'][0] and '102 and 103' in r['why_fail'][0], r
    ev = bump(AJ.FakeEv(0.0, 0.0), 2, 102, loss=0.007)                                   # only the 2nd
    assert 'at update 102' in S.trace_a(ev, EARLY_ONLY, 9000)['why_fail'][0]
    for step, ok in ((101, True), (104, True), (150, True)):                              # outside the window: not this item (the first update has its own bar 0.01)
        assert S.trace_a(bump(AJ.FakeEv(0.0, 0.0), 2, step, loss=0.0099), EARLY_ONLY, 9000)['verdict'] == 'PASS', step
    assert S.trace_a(bump(AJ.FakeEv(0.0, 0.0), 2, 102, loss=0.0049), EARLY_ONLY, 9000)['verdict'] == 'PASS'      # just under
    assert S.trace_a(bump(AJ.FakeEv(0.0, 0.0), 2, 102, loss=0.0051), EARLY_ONLY, 9000)['verdict'] == 'FAIL'      # just over
    # hard in every soft variant, even when the key is named in soft
    for soft in (['peak', 'resume_max_abs'], SOFT3, SOFT3 + ['resume_early_abs']):
        assert S.trace_a(AJ.FakeEv(0.0, 0.006), dict(EARLY_ONLY, soft=soft), 9000)['verdict'] == 'FAIL', soft
    # a trace with exactly two redone updates: the early window (2nd AND 3rd) is not computable, so nothing about its value is recorded (Q95); with the rule set it is deferred to the probe's P1b (ruling B2), not a failure
    ev = AJ.FakeEv(0.0, 0.0)
    ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > 102)]
    r = S.trace_a(ev, EARLY_ONLY, 9000)
    assert r['resume']['n_redone'] == 2 and 'early_max' not in r['resume'], r
    assert r['verdict'] == 'PASS' and r['why_fail'] == [] and r['resume']['early_window'] == dict(computed=False, redone=2, deferred_to='probe P1b'), r
    assert S.trace_a(ev, RULES, 9000)['verdict'] == 'PASS' and S.trace_a(ev, RULES, 9000)['resume']['n_redone'] == 2 and 'early_window' not in S.trace_a(ev, RULES, 9000)['resume']          # without the rule: as before
    assert S.trace_a(ev, dict(EARLY_ONLY, soft=SOFT3 + ['resume_early_abs']), 9000)['verdict'] == 'PASS'                         # (nothing to gate)
    ev = bump(ev, 2, 102, loss=0.01)                                                     # two updates and the 2nd is over the bar: the window is still not computed (Q95), so neither a value nor a failure about it
    r = S.trace_a(ev, EARLY_ONLY, 9000)
    assert r['verdict'] == 'PASS' and 'early_max' not in r['resume'] and r['why_fail'] == [] and r['resume']['early_window']['computed'] is False, r
    # exactly three: checkable
    ev = AJ.FakeEv(0.0, 0.0)
    ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > 103)]
    r = S.trace_a(ev, EARLY_ONLY, 9000)
    assert r['resume']['n_redone'] == 3 and r['verdict'] == 'PASS', r
    assert S.trace_a(bump(ev, 2, 103, loss=0.007), EARLY_ONLY, 9000)['verdict'] == 'FAIL'
    # one redone update: no early_max; with the rule: deferred (ruling B2); without it: PASS as before
    ev = AJ.FakeEv(0.0, 0.0)
    ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > 101)]
    r = S.trace_a(ev, EARLY_ONLY, 9000)
    assert r['resume']['n_redone'] == 1 and 'early_max' not in r['resume'] and r['verdict'] == 'PASS' and r['resume']['early_window'] == dict(computed=False, redone=1, deferred_to='probe P1b'), r
    r = S.trace_a(ev, RULES, 9000)
    assert r['resume']['n_redone'] == 1 and 'early_max' not in r['resume'] and r['verdict'] == 'PASS', r
    # first_diff stays a bar of its own (0.01) and keeps its default
    assert S.trace_a(bump(AJ.FakeEv(0.0), 2, 101, loss=0.02), EARLY_ONLY, 9000)['why_fail'][0].startswith('first redone update differs by 0.0200')
    print('ok trace A early window: resume_early_abs absent = the original result (+ early_max recorded); 2nd-3rd redone updates only; names the updates; just under/over 0.005; hard even if named in soft; 1-2 redone updates')


def t_trace_a_exact_fields():
    ev = with_fields(AJ.FakeEv(0.0))
    r = S.trace_a(ev, EARLY_RULES, 9000)
    assert r['verdict'] == 'PASS' and r['resume']['exact_checked'] == ['lr', 'plan_gapped', 'plan_rows', 'rounds'] and r['resume']['exact_mismatch'] == [], r
    # absent rule: nothing checked, mismatch ignored (identical to the original apart from early_max)
    ev = bump(with_fields(AJ.FakeEv(0.0)), 2, 101, plan_rows=6.0)
    a, b = O.trace_a(ev, RULES, 9000), S.trace_a(ev, RULES, 9000)
    assert json.dumps(a, sort_keys=True) == json.dumps(strip_early(b), sort_keys=True) and b['verdict'] == 'PASS'
    # each kind of field: prefix, plain name
    for field, val in (('plan_rows', 6.0), ('plan_gapped', 0.0), ('rounds', 4.0), ('lr', 2e-3)):
        ev = bump(with_fields(AJ.FakeEv(0.0)), 2, 101, **{field: val})
        r = S.trace_a(ev, EARLY_RULES, 9000)
        assert r['verdict'] == 'FAIL' and len(r['why_fail']) == 1 and field in r['why_fail'][0] and 'update 101' in r['why_fail'][0], (field, r)
        assert [m['field'] for m in r['resume']['exact_mismatch']] == [field] and r['resume']['exact_mismatch'][0]['resumed'] == val, r
        assert S.trace_a(ev, dict(EARLY_RULES, soft=SOFT3 + ['resume_exact_fields']), 9000)['verdict'] == 'FAIL'                  # hard
    # only the FIRST redone update is compared (a mismatch at 102 is the loss's business)
    assert S.trace_a(bump(with_fields(AJ.FakeEv(0.0)), 2, 102, plan_rows=9.0), EARLY_RULES, 9000)['verdict'] == 'PASS'
    # a field not listed is ignored; a prefix needs its underscore; a name is exact
    ev = bump(with_fields(AJ.FakeEv(0.0), cap_hits=1), 2, 101, cap_hits=7, plan_rows=6.0)
    assert S.trace_a(ev, dict(RULES, resume_exact_fields=['lr', 'rounds']), 9000)['verdict'] == 'PASS'
    ev = bump(with_fields(AJ.FakeEv(0.0), rounds_total=1), 2, 101, rounds_total=2)
    assert S.trace_a(ev, dict(RULES, resume_exact_fields=['rounds']), 9000)['resume']['exact_checked'] == ['rounds']        # 'rounds' does not match 'rounds_total'
    assert S.trace_a(ev, dict(RULES, resume_exact_fields=['rounds_']), 9000)['verdict'] == 'FAIL'
    ev = bump(with_fields(AJ.FakeEv(0.0)), 2, 101, plan_rows=6.0)
    r = S.trace_a(ev, dict(RULES, resume_exact_fields=['plan']), 9000)                                                      # 'plan' (no underscore) is a field name, not a prefix: no such field -> missing (hard)
    assert r['resume']['exact_checked'] == [] and [m['field'] for m in r['resume']['exact_missing']] == ['plan'] and r['verdict'] == 'FAIL', r
    # a listed field in only one of the two lines cannot be compared: a hard failure (item 4), see t_trace_a_exact_missing
    # NaN equals NaN, a float that differs by 1e-12 does not
    ev = with_fields(AJ.FakeEv(0.0), stop_w=float('nan'))
    assert S.trace_a(ev, dict(RULES, resume_exact_fields=['stop_w']), 9000)['verdict'] == 'PASS'
    assert S.trace_a(bump(with_fields(AJ.FakeEv(0.0)), 2, 101, lr=1e-3 + 1e-12), EARLY_RULES, 9000)['verdict'] == 'FAIL'
    # the loss comparison is untouched by the fields: same first/mean/max, and a loss-only fault is still found by the old items
    a, b = S.trace_a(with_fields(AJ.FakeEv(0.05, 0.003)), EARLY_RULES, 9000), S.trace_a(AJ.FakeEv(0.05, 0.003), RULES, 9000)
    assert all(a['resume'][k] == b['resume'][k] for k in ('first_diff', 'mean_abs', 'max_abs', 'early_max'))
    # the latest earlier line of the step is the one compared (a step logged twice in the earlier segments)
    ev = with_fields(AJ.FakeEv(0.0))
    dup = dict(next(e for e in ev.train if e['seg'] == 1 and e['step'] == 101), plan_rows=99.0)
    ev.train.insert(0, dict(dup, seg=0))                                                  # an older line (seg 0), then the real seg-1 line which equals seg 2
    assert S.trace_a(ev, EARLY_RULES, 9000)['verdict'] == 'PASS'
    print('ok trace A exact fields: lr / rounds / plan_* equal at the first redone update or FAIL (hard, names the field and values); only the first update; prefix vs name; losses untouched')


def t_trace_a_exact_missing():
    """item 4: a listed exact field that is missing from either line, or a listed prefix that matches no key / different keys in the two lines, is a HARD failure (never a skip or a note); the missing ones are recorded."""
    def drop(ev, seg, *keys):
        for e in ev.train:
            if e['seg'] == seg:
                for k in keys:
                    e.pop(k, None)
        return ev
    # all present: no missing
    r = S.trace_a(with_fields(AJ.FakeEv(0.0)), EARLY_RULES, 9000)
    assert r['verdict'] == 'PASS' and r['resume']['exact_missing'] == [], r
    # a name missing from the EARLIER line / from the RESUMED line / from both
    for seg, where in ((1, 'the earlier line'), (2, 'the resumed line')):
        r = S.trace_a(drop(with_fields(AJ.FakeEv(0.0)), seg, 'rounds'), EARLY_RULES, 9000)
        assert r['verdict'] == 'FAIL' and [m['field'] for m in r['resume']['exact_missing']] == ['rounds'] and where in r['resume']['exact_missing'][0]['reason'], r
        assert any('cannot be compared' in w and 'rounds' in w for w in r['why_fail']) and 'rounds' not in r['resume']['exact_checked'] and not r['notes'], r
        assert S.trace_a(drop(with_fields(AJ.FakeEv(0.0)), seg, 'rounds'), dict(EARLY_RULES, soft=SOFT3 + ['resume_exact_fields']), 9000)['verdict'] == 'FAIL'     # hard
    r = S.trace_a(drop(drop(with_fields(AJ.FakeEv(0.0)), 1, 'lr'), 2, 'lr'), EARLY_RULES, 9000)
    assert r['verdict'] == 'FAIL' and [m['field'] for m in r['resume']['exact_missing']] == ['lr'] and 'both lines' in r['resume']['exact_missing'][0]['reason'], r
    # a prefix matching nothing in either line
    r = S.trace_a(drop(drop(with_fields(AJ.FakeEv(0.0)), 1, 'plan_rows', 'plan_gapped'), 2, 'plan_rows', 'plan_gapped'), EARLY_RULES, 9000)
    assert r['verdict'] == 'FAIL' and [m['field'] for m in r['resume']['exact_missing']] == ['plan_'] and 'no key in either line' in r['resume']['exact_missing'][0]['reason'], r
    # a prefix matching in only one line, or different key sets (one key each side)
    r = S.trace_a(drop(with_fields(AJ.FakeEv(0.0)), 1, 'plan_rows', 'plan_gapped'), EARLY_RULES, 9000)
    assert r['verdict'] == 'FAIL' and [m['field'] for m in r['resume']['exact_missing']] == ['plan_'] and 'different keys' in r['resume']['exact_missing'][0]['reason'], r
    r = S.trace_a(drop(with_fields(AJ.FakeEv(0.0)), 1, 'plan_rows'), EARLY_RULES, 9000)                                   # earlier has plan_gapped only, resumed has both
    assert r['verdict'] == 'FAIL' and [m['field'] for m in r['resume']['exact_missing']] == ['plan_'] and r['resume']['exact_checked'] == ['lr', 'plan_gapped', 'rounds'], r
    # the fake runner / FakeEv lines carry no such fields at all: all three listed entries are missing -> FAIL (it used to be a note and PASS)
    r = S.trace_a(AJ.FakeEv(0.0), EARLY_RULES, 9000)
    assert r['verdict'] == 'FAIL' and [m['field'] for m in r['resume']['exact_missing']] == ['lr', 'rounds', 'plan_'] and r['resume']['exact_checked'] == [] and not r['notes'], r
    # a mismatch AND a missing field: both reported
    r = S.trace_a(bump(drop(with_fields(AJ.FakeEv(0.0)), 2, 'rounds'), 2, 101, lr=2e-3), EARLY_RULES, 9000)
    assert len(r['why_fail']) == 2 and r['resume']['exact_mismatch'] and r['resume']['exact_missing'], r
    # the rule absent / the list empty: nothing is required
    assert S.trace_a(AJ.FakeEv(0.0), RULES, 9000)['verdict'] == 'PASS' and S.trace_a(AJ.FakeEv(0.0), dict(RULES, resume_exact_fields=[]), 9000)['verdict'] == 'PASS'
    print('ok trace A exact fields, missing = hard failure: a listed name absent from either/both lines, a prefix matching no key or different keys; recorded in exact_missing, hard even if named in soft; no rule / empty list: nothing required')


def t_verdict_early():
    C = [3.0 - 0.01 * i for i in range(10)]
    r = S.resume_probe_verdict(C, list(C), list(C))
    assert r['early_max'] == 0 and r['early_limit'] == 0.005 and r['early_verdict'] == 'PASS', r
    R1 = list(C); R2 = list(C)
    R1[1] += 0.004; R2[2] -= 0.0049
    r = S.resume_probe_verdict(C, R1, R2)
    assert abs(r['early_max'] - 0.0049) < 1e-12 and r['early_verdict'] == 'PASS', r
    for idx, who in ((1, 1), (2, 1), (1, 2), (2, 2)):                                      # either resume, either of the two updates
        R1 = list(C); R2 = list(C)
        (R1 if who == 1 else R2)[idx] += 0.0051
        r = S.resume_probe_verdict(C, R1, R2)
        assert r['early_verdict'] == 'FAIL' and abs(r['early_max'] - 0.0051) < 1e-12 and r['verdict'] == 'PASS', (idx, who, r)          # registered verdict untouched
    R1 = list(C); R1[0] += 0.5; R1[3] += 0.004                                              # the first and 4th update are not the early window
    r = S.resume_probe_verdict(C, R1, list(C))
    assert r['early_max'] == 0 and r['early_verdict'] == 'PASS' and r['first_r1_c'] == 0.5
    r = S.resume_probe_verdict([1.0, 2.0, 3.0], [1.0, 2.0, 3.01], [1.0, 2.0, 3.0])           # three updates: the smallest computable window
    assert abs(r['early_max'] - 0.01) < 1e-12 and r['early_verdict'] == 'FAIL'
    for C2, R1_ in (([1.0, 2.0], [1.0, 2.01]), ([1.0], [1.0])):                              # under three updates: no early keys at all (Q95; see t_early_not_computable)
        r = S.resume_probe_verdict(C2, R1_, list(C2))
        assert not {'early_max', 'early_limit', 'early_verdict'} & set(r), r
        json.dumps(r)
    print('ok probe verdict early window: early_max over probe updates 2-3 of both resumes, limit 0.005, verdict; the registered verdict is unchanged; absent below 3 updates')


def t_installer_trace_a_early():
    EARLY = dict(resume_early_abs=0.005, resume_exact_fields=['lr', 'rounds', 'plan_'])
    def want(I, soft=None, early=True):
        w = AJ.expected_g2fa8(I)
        if soft:
            w['trace_a']['soft'] = list(soft)
        if early:
            w['trace_a'].update(json.loads(json.dumps(EARLY)))
        return w
    with tempfile.TemporaryDirectory() as tmp:
        I = AJ.installed_pc(tmp)
        assert I.TRACE_A_EARLY == EARLY
        g4 = json.loads((I.STATE / 'plan.json').read_text())['jobs'][0]
        assert 'resume_early_abs' not in g4['trace_a'] and 'resume_exact_fields' not in g4['trace_a']
        assert I.new_job_entry('g2fa8', g4) == AJ.expected_g2fa8(I)                                         # default unchanged
        assert I.new_job_entry('g2fa8', g4, early=True) == want(I)
        assert I.new_job_entry('g2fa8', g4, True, False, True) == want(I, ['peak', 'resume_max_abs'])
        assert I.new_job_entry('g2fa8', g4, True, True, True) == want(I, SOFT3)
        assert I.TRACE_A_EARLY == EARLY and I.new_job_entry('g2fa8', g4, early=True)['trace_a']['resume_exact_fields'] is not I.TRACE_A_EARLY['resume_exact_fields'], 'the module constant is copied, not shared'
        assert g4['trace_a']['resume_first_diff'] == 0.01 and I.new_job_entry('g2fa8', g4, early=True)['trace_a']['resume_first_diff'] == 0.01
    # usage errors: not with another job / without --add-job
    for args in (['--trace-a-early'], ['--skip-tests', '--trace-a-early']):
        with tempfile.TemporaryDirectory() as tmp:
            I = AJ.load_installer(tmp)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = raises_exit(lambda: I.main(args))
            assert code == 2 and '--trace-a-early only go with --add-job g2fa8' in err.getvalue(), (args, code, err.getvalue())
    # alone, with --check, then for real, idempotent
    with tempfile.TemporaryDirectory() as tmp:
        I = AJ.installed_pc(tmp)
        before = AJ.pc_files(I)
        I.STAMP = 'E1'
        rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--trace-a-early', '--check'])
        assert rc == 0 and 'CHECK ONLY' in out and AJ.pc_files(I) == before and '--trace-a-early' in out, out
        rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--trace-a-early'])
        assert rc == 0 and 'ADD-JOB g2fa8 DONE' in out, out
        new = json.loads((I.STATE / 'plan.json').read_text())
        assert new['jobs'][1] == want(I) and new['jobs'][0].get('skip') is True, new['jobs'][1]
        sup = S.Sup(I.STATE / 'plan.json')
        rules = sup.plan['jobs'][1]['trace_a']
        assert 'soft' not in rules and S.trace_a(AJ.FakeEv(0.0, 0.006), rules, 9000)['verdict'] == 'FAIL' and S.trace_a(with_fields(AJ.FakeEv(0.0, 0.004)), rules, 9000)['verdict'] == 'PASS'      # the installed rules act
        before2 = AJ.pc_files(I)
        I.STAMP = 'E2'
        rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--trace-a-early'])
        after2 = AJ.pc_files(I)
        assert rc == 0 and {k for k in set(before2) | set(after2) if before2.get(k) != after2.get(k)} == {'add-job-g2fa8-E2.txt'}, out
        # every other variant is refused afterwards, nothing changes
        for args in ([], ['--soft-trace-a'], ['--soft-trace-a', '--soft-trace-a-mean']):
            b = AJ.pc_files(I)
            I.STAMP = 'E3'
            rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'] + args)
            assert rc == 1 and 'differs from the expected entry' in out and AJ.pc_files(I) == b, (args, out)
    # combined with the soft flags, idempotent; and every pair of variants refuses the other (both orders)
    variants = [[], ['--trace-a-early'], ['--soft-trace-a'], ['--soft-trace-a', '--trace-a-early'], ['--soft-trace-a', '--soft-trace-a-mean'], ['--soft-trace-a', '--soft-trace-a-mean', '--trace-a-early']]
    for i, first in enumerate(variants):
        with tempfile.TemporaryDirectory() as tmp:
            I = AJ.installed_pc(tmp)
            I.STAMP = 'V1'
            rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'] + first)
            assert rc == 0, (first, out)
            e = json.loads((I.STATE / 'plan.json').read_text())['jobs'][1]['trace_a']
            assert ('resume_early_abs' in e) == ('--trace-a-early' in first) and e.get('soft') == (None if '--soft-trace-a' not in first else SOFT3 if '--soft-trace-a-mean' in first else ['peak', 'resume_max_abs']), (first, e)
            for j, second in enumerate(variants):
                b = AJ.pc_files(I)
                I.STAMP = f'V2{j}'
                rc, out = AJ.quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'] + second)
                a = AJ.pc_files(I)
                if i == j:
                    assert rc == 0 and {k for k in set(a) | set(b) if a.get(k) != b.get(k)} == {f'add-job-g2fa8-V2{j}.txt'}, (first, second, out)
                else:
                    assert rc == 1 and 'differs from the expected entry' in out and a == b, (first, second, out)
    print('ok installer --trace-a-early: opt-in, only with --add-job g2fa8, entry gets resume_early_abs 0.005 and resume_exact_fields [lr, rounds, plan_] (copied), check changes nothing, idempotent, installed rules act; all 6 variants (strict/soft/soft+mean x early) are mutually refused, never mixed; defaults unchanged')


def amend_probe(C, Rs, **kw):
    """the dict a probe JSON holds, for R1..Rn"""
    return dict(dict(job='g2fa8', step=200, upto=250, why_fail=[], verdict='PASS', C=C, R1=Rs[0], R2=Rs[1]), **kw)


def t_rejudge_amended():
    # INSIDE: P1, P1b, P2, P3 hold, ratio <= 2, v <= limit
    r1, r2 = alt(0.015)
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'INSIDE healthy noise' and r['restore_ok'] and r['early_ok'] and r['p23_ok'] and r['calibration'] is None and r['original_reading_verdict'] == 'INSIDE healthy noise', r
    # UNRESOLVED (window): same but v above the limit
    r1, r2 = alt(0.003)
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'UNRESOLVED' and r['p23_ok'] and r['noise_limit'] == 0.02, r
    # UNRESOLVED_CALIBRATE: P1, P1b hold, P3 / ratio fail (both restarts the same side of the run by different amounts)
    r1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(CL)]
    r2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(CL)]
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'UNRESOLVED_CALIBRATE' and r['restore_ok'] and r['early_ok'] and not r['p3_ok'] and r['ratio'] > 2 and r['registered_verdict'] == 'PASS', r
    # ... P2 (the registered max rule) fails
    a = [0.0, 1e-4, 1e-4] + [0.015 * (-1) ** i for i in range(3, 50)]
    s1 = [c + x for c, x in zip(CL, a)]; s2 = [c - x for c, x in zip(CL, a)]
    s1[10] += 0.5; s2[10] += 0.5
    r = R.rejudge(CL, s1, s2)
    assert r['verdict'] == 'UNRESOLVED_CALIBRATE' and r['registered_verdict'] == 'FAIL', r
    # ... both restarts off the run by 0.03 and almost equal to each other (Dbar 0.03, Nbar 0.0001): ratio ~ 300, P3 fails
    r1 = [c + (0 if i in (0, 1, 2) else 0.0301) for i, c in enumerate(CL)]; r2 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(CL)]
    assert R.rejudge(CL, r1, r2)['verdict'] == 'UNRESOLVED_CALIBRATE'
    # OUTSIDE by P1 (first update not exact), also when everything else is perfect
    r1, r2 = alt(0.015, first_exact=False)
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'OUTSIDE' and not r['restore_ok'] and r['early_ok'], r
    # OUTSIDE by P1b: first update exact, a lost-optimizer-state-like jump at the 2nd or 3rd update, rest healthy
    for idx in (1, 2):
        for who in (1, 2):
            r1, r2 = alt(0.015)
            (r1 if who == 1 else r2)[idx] += 0.0051 if who == 1 else -0.0051                  # (R2 = C - 1e-4 there: away from C by 0.0052)
            r = R.rejudge(CL, r1, r2)
            assert r['verdict'] == 'OUTSIDE' and r['restore_ok'] and not r['early_ok'] and r['early_max'] > 0.005, (idx, who, r)
    r1, r2 = alt(0.015)
    r1[1] += 0.005 - 1e-4                                                                    # exactly at the limit (0.005 up to float rounding): early_max <= 0.005 holds iff the sum does
    assert abs(R.rejudge(CL, r1, r2)['early_max'] - 0.005) < 1e-12
    r1, r2 = alt(0.015, early=0.00499)                                                       # just under: INSIDE
    assert R.rejudge(CL, r1, r2)['verdict'] == 'INSIDE healthy noise'
    r1, r2 = alt(0.015, early=0.00501)
    assert R.rejudge(CL, r1, r2)['verdict'] == 'OUTSIDE'
    # P1b beats a ratio failure and a P2 failure (OUTSIDE, not UNRESOLVED_CALIBRATE); the 4th update is not the early window
    s1 = list(CL); s1[1] += 0.01
    assert R.rejudge(CL, s1, list(s1))['verdict'] == 'OUTSIDE'
    s1 = [c + (0 if i in (0, 1, 2) else 0.05) for i, c in enumerate(CL)]; s1[3] += 0.3
    assert R.rejudge(CL, s1, list(s1))['verdict'] == 'UNRESOLVED_CALIBRATE'
    # the original reading is recorded beside, unchanged
    r1, r2 = alt(0.015); r1[1] += 0.02
    r = R.rejudge(CL, r1, r2)
    assert r['verdict'] == 'OUTSIDE' and r['original_reading_verdict'] == 'INSIDE healthy noise', r
    print('ok rejudge amended reading: INSIDE / UNRESOLVED (window) / UNRESOLVED_CALIBRATE (P2, P3 or ratio fails) / OUTSIDE by P1 / OUTSIDE by P1b (2nd and 3rd update, both resumes, 0.005 boundary); original reading recorded beside')


def t_rejudge_calibration():
    C = CL
    def four(a_pairs=0.015, off=None):
        """R1..R4 = C + s_k * a for signs (+,-,+,-): pairwise gaps 2a or 0; all tiny early; optional constant offset of every resume from C (after the first 3 updates)"""
        out = []
        for sgn in (1, -1, 1, -1):
            out.append([c + (0 if i == 0 else 1e-4 * sgn if i in (1, 2) else sgn * a_pairs + (off or 0)) for i, c in enumerate(C)])
        return out
    # a) the 2-resume reading is UNRESOLVED_CALIBRATE (ratio failure), the 4-resume calibration says INSIDE
    Rs = four(0.015)
    pr = amend_probe(C, Rs)
    # make the first pair look unlike the run by sharing an offset while R3, R4 differ: R1, R2 same side
    R1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    R3 = [c - (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R4 = [c - (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    assert R.rejudge(C, R1, R2)['verdict'] == 'UNRESOLVED_CALIBRATE'
    r = R.rejudge(C, R1, R2, 0.0282, (R3, R4))
    cal = r['calibration']
    exp_pairs = {f'R{i + 1}-R{j + 1}': sum(abs(x - y) for x, y in zip(a, b)) / 50 for (i, a) in enumerate((R1, R2, R3, R4)) for (j, b) in enumerate((R1, R2, R3, R4)) if i < j}
    assert set(cal['pair_means']) == set(exp_pairs) and len(exp_pairs) == 6 and all(abs(cal['pair_means'][k] - exp_pairs[k]) < 1e-12 for k in exp_pairs), cal
    mp = max(exp_pairs.values())
    assert abs(cal['L'] - max(0.02, 2 * mp)) < 1e-12 and cal['max_pair'] == mp
    d4 = sum(sum(abs(x - c) for x, c in zip(Rk, C)) / 50 for Rk in (R1, R2, R3, R4)) / 4
    assert abs(cal['Dbar4'] - d4) < 1e-12, cal
    assert cal['Dbar4'] <= cal['L'] and 0.0282 <= cal['L'] and r['verdict'] == 'INSIDE healthy noise', (r['verdict'], cal)          # L ~ 0.11: bigger than v
    r = R.rejudge(C, R1, R2, 0.5, (R3, R4))
    assert r['verdict'] == 'UNRESOLVED' and r['calibration']['verdict'] == 'UNRESOLVED', r                                          # v above L: window
    # b) OUTSIDE: all four restarts agree with each other but sit away from the run (max pair ~ 0): Dbar4 > L = 0.02
    off = [c + (0 if i in (0, 1, 2) else 0.05) for i, c in enumerate(C)]
    r = R.rejudge(C, off, list(off), 0.0282, (list(off), list(off)))
    assert r['verdict'] == 'OUTSIDE' and r['calibration']['L'] == 0.02 and r['calibration']['Dbar4'] > 0.02 and r['restore_ok'] and r['early_ok'], r
    # boundary: Dbar4 == L is not outside (<=): all four at distance exactly 0.02 (mean over 47 updates of 0.02... use a constant 0.02 for all updates after the third)
    just = [c + (0 if i in (0, 1, 2) else 0.02) for i, c in enumerate(C)]
    cal = R.calibration(C, [just] * 4, 0.0282)
    assert cal['L'] == 0.02 and abs(cal['Dbar4'] - 0.02 * 47 / 50) < 1e-12 and cal['verdict'] == 'UNRESOLVED', cal           # Dbar4 = 0.0188 <= 0.02, v 0.0282 > 0.02
    far = [c + (0 if i in (0, 1, 2) else 0.0214) for i, c in enumerate(C)]                                                       # 0.0214 * 47/50 = 0.02012 > 0.02
    assert R.calibration(C, [far] * 4, 0.0282)['verdict'] == 'OUTSIDE'
    # c) INSIDE needs v <= L: calm window, small L, v above it -> UNRESOLVED (window); v below -> INSIDE
    calm = [list(C) for _ in range(4)]
    assert R.calibration(C, calm, 0.0282)['verdict'] == 'UNRESOLVED' and R.calibration(C, calm, 0.02)['verdict'] == 'INSIDE healthy noise'
    # d) P1 / P1b of R3 or R4 fail -> OUTSIDE (even though R1, R2 pass); of R1, R2 -> OUTSIDE regardless
    bad3 = list(R3); bad3[0] += 1e-6
    r = R.rejudge(C, R1, R2, 0.0282, (bad3, R4))
    assert r['verdict'] == 'OUTSIDE' and r['restore_ok'] and not r['calibration']['p1_all'], r
    assert 'R3, R4' in R.words(dict(r, job='j'), 'j')
    bad4 = list(R4); bad4[2] += 0.006
    r = R.rejudge(C, R1, R2, 0.0282, (R3, bad4))
    assert r['verdict'] == 'OUTSIDE' and not r['calibration']['p1b_all'] and r['early_ok'], r
    r1, r2 = alt(0.015, first_exact=False)
    assert R.rejudge(C, r1, r2, 0.0282, (list(r1), list(r2)))['verdict'] == 'OUTSIDE'
    try:
        R.rejudge(C, R1, R2, 0.0282, (R3[:-1], R4))
    except ValueError:
        pass
    else:
        raise AssertionError('R3 / R4 of the wrong length')
    # e) through the CLI: file handling, exit codes, JSON
    with tempfile.TemporaryDirectory() as tmp:
        f1 = write_probe(tmp, 'g2fa8', C, R1, R2)
        rc, out = AJ.quiet(R.main, [str(f1)])
        assert rc == 1 and 'UNRESOLVED_CALIBRATE' in out and '--calibration PROBE2.json' in out and R.AMEND1 in out and R.PREREG in out, (rc, out)
        j = json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())
        assert j['verdict'] == 'UNRESOLVED_CALIBRATE' and j['calibration'] is None and j['amendment_1_reading'] == R.AMEND1 and j['preregistered_reading'] == R.PREREG and j['original_reading_verdict'] == 'OUTSIDE', j
        sub = Path(tmp) / 'p2'; sub.mkdir()
        f2 = write_probe(sub, 'g2fa8', C, R3, R4)
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(f2)])
        assert rc == 0 and 'INSIDE healthy noise' in out and 'calibration (' in out and 'Dbar4' in out, (rc, out)
        j = json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())
        assert j['verdict'] == 'INSIDE healthy noise' and len(j['calibration']['pair_means']) == 6 and j['calibration_source'] == str(f2), j
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(f2), '--trace-a-mean', '0.5'])
        assert rc == 1 and 'UNRESOLVED (window)' in out and json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())['verdict'] == 'UNRESOLVED'
        f3 = write_probe(sub, 'g2fa8', C, off, list(off))
        rc, out = AJ.quiet(R.main, [str(f3), '--calibration', str(write_probe(Path(tmp), 'g2fa8x', C, off, list(off)))])        # job differs between the files -> unreadable
        assert rc == 3 and "job is 'g2fa8x'" in out, out
        off2 = [x + 1e-6 for x in off]                                                                                           # (a file of its own resumes: not a copy of f3)
        (Path(tmp) / 'p3').mkdir()
        f3b = write_probe(Path(tmp) / 'p3', 'g2fa8', C, off2, [x + 2e-6 for x in off])
        rc, out = AJ.quiet(R.main, [str(f3), '--calibration', str(f3b)])                                                        # four almost identical, all off the run -> OUTSIDE
        assert rc == 2 and 'OUTSIDE' in out and 'Dbar4' in out, (rc, out)
        f4 = write_probe(sub, 'g2fa8', [x + 1 for x in C], R3, R4)                                                              # another C
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(f4)])
        assert rc == 3 and 'its C' in out, out
        f5 = write_probe(sub, 'g2fa8', C, R3, R4, upto=260)
        assert AJ.quiet(R.main, [str(f1), '--calibration', str(f5)])[0] == 3
        f6 = write_probe(sub, 'g2fa8', C, R3, R4, why_fail=['n2: x'])
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(f6)])
        assert rc == 3 and 'did not judge' in out, out
        assert AJ.quiet(R.main, [str(f1), '--calibration', str(Path(tmp) / 'nope.json')])[0] == 3
        # OUTSIDE by P1 / P1b through the CLI, exit 2, with the message
        r1_, r2_ = alt(0.015, first_exact=False)
        rc, out = AJ.quiet(R.main, [write_probe(tmp, 'g2fa6', C, r1_, r2_).as_posix()])
        assert rc == 2 and R.RESTORE_MSG in out
        r1_, r2_ = alt(0.015); r1_[2] += 0.02
        rc, out = AJ.quiet(R.main, [write_probe(tmp, 'g2fa5', C, r1_, r2_).as_posix()])
        assert rc == 2 and 'OUTSIDE' in out and 'early window' in out and 'optimizer' in out and json.loads((Path(tmp) / 'REJUDGE-g2fa5.json').read_text())['early_ok'] is False, (rc, out)
    # the docstring holds both texts verbatim, the original first
    doc = R.__doc__
    for line in R.AMEND1.splitlines():
        assert line in doc, line
    assert doc.index(R.PREREG.splitlines()[0]) < doc.index('AMENDMENT 1') < doc.index(R.AMEND1.splitlines()[0])
    print('ok rejudge --calibration: 6 pairwise means, L = max(0.02, 2 x largest), Dbar4; INSIDE / UNRESOLVED (window) / OUTSIDE (Dbar4 > L, boundary); R3/R4 P1 and P1b; file mismatches -> exit 3; docstring has the original text then the amendment')



# ================================================================ F: the code-review fix round (2026-10-18), items 1-6 and 9
def t_probe_report_aside():
    """item 1: PROBE-RESUME-<job>.json and .md are renamed aside (.aside-<stamp>) before a new report is written: nothing is overwritten, also within one second."""
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp)
        sd = Path(json.loads(p.read_text())['state_dir'])
        js, md = sd / 'PROBE-RESUME-g2fa4.json', sd / 'PROBE-RESUME-g2fa4.md'
        assert probe_out(p, keep)[0] == 0
        assert not list(sd.glob('PROBE-RESUME-*.aside-*')), 'the first report has nothing to move aside'
        first = (js.read_bytes(), md.read_bytes())
        assert probe_out(p, keep)[0] == 0
        a1, a2 = sorted(sd.glob('PROBE-RESUME-g2fa4.json.aside-*')), sorted(sd.glob('PROBE-RESUME-g2fa4.md.aside-*'))
        assert len(a1) == 1 and len(a2) == 1 and a1[0].read_bytes() == first[0] and a2[0].read_bytes() == first[1], (a1, a2)
        assert js.exists() and md.exists() and 'moved aside' in (sd / 'supervisor.log').read_text()
        second = (js.read_bytes(), md.read_bytes())
        assert probe_out(p, keep)[0] == 0                                                   # a third run, probably within the same second as the second: still nothing lost
        a1 = sorted(sd.glob('PROBE-RESUME-g2fa4.json.aside-*'))
        assert len(a1) == 2 and len(sorted(sd.glob('PROBE-RESUME-g2fa4.md.aside-*'))) == 2 and sorted(x.read_bytes() for x in a1) == sorted([first[0], second[0]]), a1
        # a refused probe writes nothing and moves nothing
        n = len(list(sd.glob('PROBE-RESUME-*')))
        set_sidecar(keep, step=100)
        assert probe_out(p, keep)[0] == 2 and len(list(sd.glob('PROBE-RESUME-*'))) == n
    # the helper itself: two asides of one name within one second never replace each other
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'x.json'
        names = []
        for i in range(3):
            f.write_text(f'v{i}')
            names.append(S.aside(f))
        assert len(set(names)) == 3 and sorted(q.read_text() for q in names) == ['v0', 'v1', 'v2'] and not f.exists() and S.aside(f) is None
    print('ok probe-resume: an earlier PROBE-RESUME-<job>.json and .md are moved aside (.aside-<stamp>) before the new report; nothing overwritten, even within one second; a refused probe touches nothing')


def t_rejudge_calibration_gated():
    """item 3: the calibration is applied ONLY to UNRESOLVED_CALIBRATE; otherwise the two-resume verdict stands, calibration None, calibration_not_applied says why."""
    C = CL
    R3 = [c - (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R4 = [c - (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    cases = {}
    cases['INSIDE healthy noise'] = alt(0.015)
    cases['UNRESOLVED'] = alt(0.003)
    cases['OUTSIDE'] = alt(0.015, first_exact=False)                                                          # P1 fails
    e1, e2 = alt(0.015); e1[2] += 0.02
    cases['OUTSIDE '] = (e1, e2)                                                                              # P1b fails
    for name, (r1, r2) in cases.items():
        name = name.strip()
        base = R.rejudge(C, r1, r2)
        assert base['verdict'] == name and base['calibration'] is None and base['calibration_not_applied'] is None, (name, base['verdict'])
        r = R.rejudge(C, r1, r2, 0.0282, (R3, R4))
        assert r['verdict'] == name and r['calibration'] is None, (name, r['verdict'])
        kind = 'UNRESOLVED (window)' if name == 'UNRESOLVED' else name
        assert r['calibration_not_applied'] == f'two-resume verdict is {kind}; the calibration resolves only UNRESOLVED_CALIBRATE (PREREG Amendment 1 clarification)', r['calibration_not_applied']
        assert {k: v for k, v in r.items() if k != 'calibration_not_applied'} == {k: v for k, v in base.items() if k != 'calibration_not_applied'}      # nothing else changes
    # the borderline case: applied, nothing "not applied"
    r1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    r2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    r = R.rejudge(C, r1, r2, 0.0282, (R3, R4))
    assert r['calibration'] is not None and r['calibration_not_applied'] is None and r['verdict'] == 'INSIDE healthy noise', r
    # through the CLI: the exit code and the verdict are the two-resume ones, the note is printed and recorded; both calibrations are real, different files
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / 'p2'; sub.mkdir()
        f2 = write_probe(sub, 'g2fa8', C, R3, R4)
        for name, (r1_, r2_), code in (('INSIDE healthy noise', cases['INSIDE healthy noise'], 0), ('UNRESOLVED', cases['UNRESOLVED'], 1), ('OUTSIDE', cases['OUTSIDE'], 2)):
            f1 = write_probe(tmp, 'g2fa8', C, r1_, r2_)
            rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(f2)])
            j = json.loads((Path(tmp) / 'REJUDGE-g2fa8.json').read_text())
            assert rc == code and j['verdict'] == name and j['calibration'] is None and 'resolves only UNRESOLVED_CALIBRATE' in j['calibration_not_applied'], (name, rc, out)
            assert 'NOTE: --calibration' in out and 'was NOT applied' in out and str(f2) in out and 'calibration (' not in out, out
            assert j['plain_words'].endswith('.)') and 'not applied' in j['plain_words']
    # the clarification sentence is in the docstring and the printed amendment text, verbatim from the PREREG
    clar = ('Clarification (2026-10-18, after the code review; coordinator ruling): the 4-resume calibration resolves only the borderline UNRESOLVED_CALIBRATE case. It is never applied to a two-resume verdict of INSIDE, OUTSIDE or UNRESOLVED (window). '
            'An UNRESOLVED (window) still needs the same-window measurement of §4, so adding resumes cannot turn it into INSIDE.')
    assert clar in R.AMEND1 and clar in R.__doc__
    prereg = ORIG_PACK.parent.parent / 'restart-gate-solve' / 'PREREG-trace-a2.md'
    if prereg.exists():
        line = next(x for x in prereg.read_text(encoding='utf-8').splitlines() if x.startswith('- **Clarification (2026-10-18'))
        assert line[2:].replace('**', '') == clar, line
    print('ok rejudge --calibration is applied only to UNRESOLVED_CALIBRATE; INSIDE / UNRESOLVED (window) / OUTSIDE (P1, P1b) keep the two-resume verdict, calibration None, calibration_not_applied + printed note; clarification verbatim' + ('' if prereg.exists() else ' (PREREG file not found: text checked against the copy in the test only)'))


def t_rejudge_calibration_refused():
    """item 2: --calibration refused (exit 3, message names the calibration file) if it is the same file or content as the probe, or its R1/R2 equal the probe's (either order)."""
    C = CL
    R1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    R3 = [c - (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R4 = [c - (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / 'calib'; sub.mkdir()
        f1 = write_probe(tmp, 'g2fa8', C, R1, R2)
        good = write_probe(sub, 'g2fa8', C, R3, R4)
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(good)])
        assert rc == 0 and 'INSIDE healthy noise' in out, (rc, out)
        (Path(tmp) / 'REJUDGE-g2fa8.json').unlink()
        bad = {}
        bad['same path'] = f1
        link = sub / 'alias.json'; link.symlink_to(f1)
        bad['same path via a symlink'] = link
        bad['same path spelled differently'] = Path(tmp) / 'calib' / '..' / f1.name
        copy = sub / 'copy-of-probe.json'; copy.write_bytes(f1.read_bytes())
        bad['same content, another file'] = copy
        reform = sub / 'reformatted.json'; reform.write_text(json.dumps(json.loads(f1.read_text()), indent=2))
        bad['same content, reformatted'] = reform
        so = sub / 'sameorder'; so.mkdir()
        bad['R1/R2 equal (same order)'] = write_probe(so, 'g2fa8', C, list(R1), list(R2), verdict='FAIL')
        sw = sub / 'swapped'; sw.mkdir()
        bad['R1/R2 equal (swapped)'] = write_probe(sw, 'g2fa8', C, list(R2), list(R1))
        for what, cf in bad.items():
            rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(cf)])
            assert rc == 3 and str(cf) in out and '--calibration' in out and not (Path(tmp) / 'REJUDGE-g2fa8.json').exists(), (what, rc, out)
        # only ONE of the two equal (a deterministic card can repeat a resume) is not the same pair: accepted
        (sub / 'one').mkdir()
        one = write_probe(sub / 'one', 'g2fa8', C, list(R1), list(R4))
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(one)])
        assert rc == 0, (rc, out)
        # the message says what is wrong
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(copy)])
        assert 'same file (or the same content)' in out and str(copy) in out
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(bad['R1/R2 equal (swapped)'])])
        assert 'equal the probe' in out and str(bad['R1/R2 equal (swapped)']) in out
    print('ok rejudge --calibration refuses (exit 3, names the calibration file, writes nothing): same path (also symlink / ..), same content (copy, reformatted), R1/R2 equal in either order; one repeated resume is accepted')


def t_rejudge_aside():
    """item 6: an existing REJUDGE-<job>.json is renamed .aside-<stamp> before the new one is written: the first reading is never lost."""
    C = CL
    with tempfile.TemporaryDirectory() as tmp:
        out_f = Path(tmp) / 'REJUDGE-g2fa8.json'
        r1, r2 = alt(0.015)
        f = write_probe(tmp, 'g2fa8', C, r1, r2)
        rc, out = AJ.quiet(R.main, [str(f)])
        assert rc == 0 and not list(Path(tmp).glob('REJUDGE-*.aside-*')) and 'moved aside' not in out
        first = out_f.read_bytes()
        rc, out = AJ.quiet(R.main, [str(f), '--trace-a-mean', '0.5'])                       # a second reading of the same probe: a different verdict
        asides = sorted(Path(tmp).glob('REJUDGE-g2fa8.json.aside-*'))
        assert rc == 1 and len(asides) == 1 and asides[0].read_bytes() == first and out_f.read_bytes() != first and str(asides[0]) in out, (rc, out)
        assert json.loads(asides[0].read_text())['verdict'] == 'INSIDE healthy noise' and json.loads(out_f.read_text())['verdict'] == 'UNRESOLVED'
        second = out_f.read_bytes()
        AJ.quiet(R.main, [str(f)])                                                          # a third reading, almost certainly within the same second as the second: nothing replaced
        asides = sorted(Path(tmp).glob('REJUDGE-g2fa8.json.aside-*'))
        assert len(asides) == 2 and {a.read_bytes() for a in asides} == {first, second}, asides
        # a refused reading (exit 3) leaves the existing file alone
        before = out_f.read_bytes()
        AJ.quiet(R.main, [str(Path(tmp) / 'nope.json')])
        assert out_f.read_bytes() == before and len(list(Path(tmp).glob('REJUDGE-g2fa8.json.aside-*'))) == 2
        # the helper uses the pack's naming (name.aside-YYYYmmdd-HHMMSS)
        import re
        assert all(re.fullmatch(r'REJUDGE-g2fa8\.json\.aside-\d{8}-\d{6}(-\d+)?', a.name) for a in asides), [a.name for a in asides]
    print('ok rejudge: an existing REJUDGE-<job>.json is moved to .aside-<stamp> before the new reading (first reading kept, also within one second); a refused reading leaves it alone')


def t_trace_a_early_needs_three():
    """item 5 + ruling B2: the early window with fewer than 3 redone updates is NOT computed and NOT a failure: early_window = {computed: False, redone: k, deferred_to: 'probe P1b'}, no early_max; the other items still judge."""
    for keep_to, n in ((101, 1), (102, 2)):
        ev = AJ.FakeEv(0.0, 0.0)
        ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > keep_to)]
        for rules in (EARLY_ONLY, dict(EARLY_ONLY, soft=SOFT3 + ['resume_early_abs', 'resume_exact_fields'])):
            r = S.trace_a(ev, rules, 9000)
            assert r['verdict'] == 'PASS' and r['why_fail'] == [] and r['resume']['n_redone'] == n and 'early_max' not in r['resume'], r
            assert r['resume']['early_window'] == dict(computed=False, redone=n, deferred_to='probe P1b'), r
        assert S.trace_a(ev, RULES, 9000)['verdict'] == 'PASS'                                # no rule: as before
        bad = bump(ev, 2, 101, loss=0.02)                                                       # the first-update bar (0.01) still fails, deferral or not
        r = S.trace_a(bad, EARLY_ONLY, 9000)
        assert r['verdict'] == 'FAIL' and r['why_fail'][0].startswith('first redone update differs by 0.0200') and 'early_max' not in r['resume'], r
    assert 'early_max' not in S.trace_a(_two_updates(), RULES, 9000)['resume']             # Q95: not recorded with 2 redone updates
    print('ok trace A: resume_early_abs with under 3 redone updates is deferred to the probe (not a failure, no early_max); the first-update bar still fails')


def _two_updates():
    ev = AJ.FakeEv(0.0, 0.0)
    ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > 102)]
    return ev


def t_early_limit_single_source():
    """item 9: EARLY_LIMIT is defined once (supervisor); the installer takes TRACE_A_EARLY from that file's text; rejudge uses the probe JSON's early_limit, and its default and its early computation agree with the supervisor's."""
    # installer
    with tempfile.TemporaryDirectory() as tmp:
        I = AJ.load_installer(tmp)
        assert I.TRACE_A_EARLY['resume_early_abs'] == S.EARLY_LIMIT == I.supervisor_early_limit(), (I.TRACE_A_EARLY, S.EARLY_LIMIT)
        assert I.new_job_entry('g2fa8', json.loads(json.dumps(dict(src='x', trace_a={}, compare={}))), early=True)['trace_a']['resume_early_abs'] == S.EARLY_LIMIT
        d = Path(tmp) / 'sup'; d.mkdir()
        for text, want in (('EARLY_LIMIT = 0.007\n', 0.007), ('x = 1\nEARLY_LIMIT = 0.007          # a comment 0.1\ny = 2\n', 0.007), ('EARLY_LIMIT=1e-3\n', 0.001)):
            (d / 'g.py').write_text(text)
            assert I.supervisor_early_limit(d / 'g.py') == want, text
        for text in ('# EARLY_LIMIT = 0.007\n', '    EARLY_LIMIT = 0.007\n', 'EARLY_LIMIT = limit()\n', 'x = 1\n'):
            (d / 'g.py').write_text(text)
            try:
                I.supervisor_early_limit(d / 'g.py')
            except SystemExit as e:
                assert 'EARLY_LIMIT' in str(e.code), e
            else:
                raise AssertionError(text)
        try:
            I.supervisor_early_limit(d / 'missing.py')
        except SystemExit as e:
            assert 'cannot read' in str(e.code)
        else:
            raise AssertionError
        # the installer reads the supervisor in ITS OWN folder: a scratch copy of the pair with another number gives another bar
        pair = Path(tmp) / 'pair'; pair.mkdir()
        (pair / 'g2fa4_supervisor.py').write_text((HERE.parent / 'g2fa4_supervisor.py').read_text(encoding='utf-8').replace('EARLY_LIMIT = 0.005 ', 'EARLY_LIMIT = 0.0123 ', 1))
        (pair / 'install_g2fa4.py').write_text((HERE.parent / 'install_g2fa4.py').read_text(encoding='utf-8'))
        spec = importlib.util.spec_from_file_location('install_pair', pair / 'install_g2fa4.py')
        I2 = importlib.util.module_from_spec(spec)
        os.environ['G2FA4_CIO'] = str(Path(tmp) / 'cio2')
        try:
            spec.loader.exec_module(I2)
        finally:
            os.environ.pop('G2FA4_CIO', None)
        assert I2.TRACE_A_EARLY['resume_early_abs'] == 0.0123, I2.TRACE_A_EARLY
    assert S.EARLY_LIMIT == 0.005 and S.resume_probe_verdict([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0])['early_limit'] == S.EARLY_LIMIT
    # rejudge: its default equals the supervisor's; the early computation agrees with the supervisor's on random inputs
    assert R.EARLY_LIMIT == S.EARLY_LIMIT
    rnd = random.Random(9)
    for _ in range(500):
        n = rnd.randint(3, 40)
        C = [3 - 0.01 * i + rnd.gauss(0, 0.01) for i in range(n)]
        sc = rnd.choice([1e-4, 1e-3, 4e-3, 1e-2])
        R1 = [c + rnd.gauss(0, sc) for c in C]; R2 = [c + rnd.gauss(0, sc) for c in C]
        sv = S.resume_probe_verdict(C, R1, R2)
        d1, d2 = R.absdiff(R1, C), R.absdiff(R2, C)
        assert R.early_of([d1, d2]) == sv['early_max'], (R.early_of([d1, d2]), sv['early_max'])
        assert (R.early_of([d1, d2]) <= R.EARLY_LIMIT) == (sv['early_verdict'] == 'PASS')
        rj = R.rejudge(C, R1, R2, early_limit=sv['early_limit'])
        assert rj['early_max'] == sv['early_max'] and rj['early_ok'] == (sv['early_verdict'] == 'PASS') and rj['early_limit'] == sv['early_limit']
    # rejudge uses the early_limit recorded in the probe JSON; the default only for an old-format probe
    C = CL
    r1, r2 = alt(0.015, early=0.007)                                                        # early gap ~ 0.007: over 0.005, under 0.01
    with tempfile.TemporaryDirectory() as tmp:
        old = write_probe(tmp, 'oldfmt', C, r1, r2)                                        # no early_limit in the file: this tool's default (0.005)
        rc, out = AJ.quiet(R.main, [str(old)])
        j = json.loads((Path(tmp) / 'REJUDGE-oldfmt.json').read_text())
        assert rc == 2 and j['early_limit'] == R.EARLY_LIMIT and 'old format' in j['early_limit_from'], (rc, j['early_limit'])
        wide = write_probe(tmp, 'wide', C, r1, r2, early_limit=0.01)
        rc, out = AJ.quiet(R.main, [str(wide)])
        j = json.loads((Path(tmp) / 'REJUDGE-wide.json').read_text())
        assert rc == 0 and j['early_limit'] == 0.01 and j['early_ok'] and j['early_limit_from'] == 'the probe json', (rc, out)
        a, b = alt(0.015, early=0.003)
        tight = write_probe(tmp, 'tight', C, a, b, early_limit=0.002)
        rc, out = AJ.quiet(R.main, [str(tight)])
        assert rc == 2 and json.loads((Path(tmp) / 'REJUDGE-tight.json').read_text())['early_limit'] == 0.002
        for bad in ('0.005', None, True, -1, float('nan')):
            f = write_probe(tmp, 'badlim', C, r1, r2, early_limit=bad)
            rc, out = AJ.quiet(R.main, [str(f)])
            assert rc == 3 and 'early_limit' in out, (bad, rc, out)
        # a calibration file: same limit is used for R3 / R4; a different recorded limit is refused (names the calibration file)
        R1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
        R2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
        R3 = [c - (0 if i in (0, 1) else 0.007 if i == 2 else 0.03) for i, c in enumerate(C)]
        R4 = [c - (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
        sub = Path(tmp) / 'c'; sub.mkdir()
        p1 = write_probe(tmp, 'cal', C, R1, R2, early_limit=0.01)
        c1 = write_probe(sub, 'cal', C, R3, R4, early_limit=0.01)
        rc, out = AJ.quiet(R.main, [str(p1), '--calibration', str(c1)])
        assert rc == 0, (rc, out)                                                          # R3's 0.007 early gap is inside the probe's 0.01
        c2 = write_probe(sub, 'cal', C, R3, R4, early_limit=0.005)
        rc, out = AJ.quiet(R.main, [str(p1), '--calibration', str(c2)])
        assert rc == 3 and str(c2) in out and 'early_limit' in out, (rc, out)
        p0 = write_probe(tmp, 'cal0', C, R1, R2)                                           # old-format probe + calibration with the default limit: R3's 0.007 is over it -> OUTSIDE
        c0 = write_probe(sub, 'cal0', C, R3, R4)
        rc, out = AJ.quiet(R.main, [str(p0), '--calibration', str(c0)])
        assert rc == 2, (rc, out)
    # a REAL probe report records the supervisor's limit, and rejudge reads it
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp, main_extra=['--jitter', '0.01'])
        assert probe_out(p, keep)[0] == 0
        rep = P.report(p)
        assert rep['early_limit'] == S.EARLY_LIMIT
        pj = Path(json.loads(p.read_text())['state_dir']) / 'PROBE-RESUME-g2fa4.json'
        rc, out = AJ.quiet(R.main, [str(pj)])
        assert json.loads((pj.parent / 'REJUDGE-g2fa4.json').read_text())['early_limit'] == S.EARLY_LIMIT and json.loads((pj.parent / 'REJUDGE-g2fa4.json').read_text())['early_limit_from'] == 'the probe json'
    print('ok EARLY_LIMIT has one definition: installer reads it from the supervisor file (parse cases, another number in a copied pair), rejudge default == supervisor, early computation agrees on 500 random inputs, rejudge uses the probe JSON\'s early_limit (default only for old format; bad value / differing calibration limit -> exit 3)')


# ================================================================ G: zero-risk cleanups (items 8 and 10)
def t_rejudge_calibration_errors_named():
    """item 8: every error that comes from the --calibration file names THAT file (not the first probe); errors of the first probe still name the probe."""
    C = CL
    R1 = [c + (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R2 = [c + (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    R3 = [c - (0 if i in (0, 1, 2) else 0.03) for i, c in enumerate(C)]
    R4 = [c - (0 if i in (0, 1, 2) else 0.0255) for i, c in enumerate(C)]
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp) / 'c'; sub.mkdir()
        f1 = write_probe(tmp, 'g2fa8', C, R1, R2)
        cal = sub / 'PROBE-RESUME-g2fa8.json'
        def run(text, **kw):
            if isinstance(text, dict):
                text = json.dumps(dict(dict(job='g2fa8', step=200, upto=250, why_fail=[], verdict='PASS', C=C, R1=R3, R2=R4), **text))
            cal.write_text(text)
            return AJ.quiet(R.main, [str(f1), '--calibration', str(cal)])
        cases = {
            'not json': 'not json {',
            'a json list': '[1, 2, 3]',
            'a json number': '5',
            'R1 null': dict(R1=None),
            'R1 a number': dict(R1=5),
            'R2 a string': dict(R2='abc'),
            'R1 strings': dict(R1=['a'] * 50),
            'R1 booleans': dict(R1=[True] * 50),
            'R1 too short': dict(R1=R3[:-1]),
            'R2 too long': dict(R2=R4 + [1.0]),
            'R1 nested lists': dict(R1=[[1.0]] * 50),
            'C not a list': dict(C=3),
            'no R2': dict(R2=None),
        }
        for what, text in cases.items():
            if what == 'no R2':
                cal.write_text(json.dumps(dict(job='g2fa8', step=200, upto=250, C=C, R1=R3)))
                rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(cal)])
            else:
                rc, out = run(text)
            assert rc == 3 and str(cal) in out and f'cannot re-read {f1}' not in out and 'Traceback' not in out and not (Path(tmp) / 'REJUDGE-g2fa8.json').exists(), (what, rc, out)
        rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(sub / 'missing.json')])
        assert rc == 3 and str(sub / 'missing.json') in out and f'cannot re-read {f1}' not in out, out
        # the messages that name the calibration file use the one wording
        rc, out = run(dict(upto=300))
        assert out.startswith(f'cannot use --calibration {cal}: ') and 'upto' in out, out
        # a KeyError / TypeError raised from inside the calibration file's handling is named too (simulated: read_probe hands back a broken dict / object)
        real = R.read_probe
        class Odd(dict):
            def get(self, k, d=None):
                raise TypeError('odd')
        for odd, word in ((dict(job='g2fa8', step=200, upto=250, R1=R3, R2=R4), 'KeyError'), (Odd(C=C, R1=R3, R2=R4), 'TypeError')):
            R.read_probe = lambda path, odd=odd, real=real: odd if str(path) == str(cal) else real(path)
            try:
                rc, out = AJ.quiet(R.main, [str(f1), '--calibration', str(cal)])
            finally:
                R.read_probe = real
            assert rc == 3 and out.startswith(f'cannot use --calibration {cal}: ') and word in out, (word, rc, out)
        # errors of the FIRST probe still name the probe
        bad = Path(tmp) / 'bad.json'; bad.write_text('nope')
        rc, out = AJ.quiet(R.main, [str(bad), '--calibration', str(cal)])
        assert rc == 3 and out.startswith(f'cannot re-read {bad}') and 'cannot use --calibration' not in out, out
        bad.write_text('[1]')
        rc, out = AJ.quiet(R.main, [str(bad)])
        assert rc == 3 and out.startswith(f'cannot re-read {bad}'), out
        # a good calibration still works
        cal.write_text(json.dumps(dict(job='g2fa8', step=200, upto=250, why_fail=[], verdict='PASS', C=C, R1=R3, R2=R4)))
        assert AJ.quiet(R.main, [str(f1), '--calibration', str(cal)])[0] == 0
    print('ok rejudge: errors from the --calibration file (unreadable, not JSON, wrong types / lengths, KeyError, TypeError, AttributeError, mismatches) are reported as "cannot use --calibration <that file>: ..." with exit 3; the first probe\'s errors still name the probe')


def t_rejudge_p23_unchanged():
    """item 10: p23_ok = exch_ok and p3 is the old `reg == PASS and p3 and ratio <= 2.0`: same p23_ok and the same verdicts (with and without --calibration) over random traces of every class."""
    rnd = random.Random(2026)
    seen = {}
    for _ in range(3000):
        n = rnd.randint(3, 30)
        C = [3 - 0.01 * i + rnd.gauss(0, 0.02) for i in range(n)]
        a, b = rnd.choice([0, 1e-4, 0.003, 0.015, 0.03, 0.08]), rnd.choice([0, 1e-4, 0.003, 0.015, 0.03])
        off = rnd.choice([0, 0, 0.02, 0.05])
        def resume(scale, shift):
            R_ = [c + rnd.gauss(0, scale) + shift for c in C]
            if rnd.random() < 0.9:
                R_[0] = C[0]
            for i in (1, 2):
                if i < n and rnd.random() < 0.9:
                    R_[i] = C[i] + rnd.gauss(0, 1e-3)
            if rnd.random() < 0.15:
                R_[rnd.randrange(n)] += rnd.choice([0.5, -0.5, 0.2])
            return R_
        R1_, R2_ = resume(a, off), resume(b, off * rnd.choice([0, 1]))
        v = rnd.choice([0.01, 0.0282, 0.05, 0.2])
        # the old reading, written out from the definitions
        d12, d1, d2 = ([abs(x - y) for x, y in zip(u, w)] for u, w in ((R1_, R2_), (R1_, C), (R2_, C)))
        m = lambda xs: sum(xs) / len(xs)
        nn, dd = max(d12), max(d1 + d2)
        reg = 'PASS' if dd <= max(0.10, 3 * nn) else 'FAIL'
        dbar, nbar = m([m(d1), m(d2)]), m(d12)
        ratio = (float('inf') if dbar > 0 else 1.0) if nbar == 0 else dbar / nbar
        limit = max(0.02, 2 * nbar)
        old_p23 = reg == 'PASS' and dbar <= limit and ratio <= 2.0
        em = max(d1[1], d1[2], d2[1], d2[2])
        if not (d1[0] == 0 and d2[0] == 0 and em <= 0.005):
            old_v = 'OUTSIDE'
        elif old_p23:
            old_v = 'INSIDE healthy noise' if v <= limit else 'UNRESOLVED'
        else:
            old_v = 'UNRESOLVED_CALIBRATE'
        r = R.rejudge(C, R1_, R2_, v)
        assert r['p23_ok'] is old_p23 and r['verdict'] == old_v, (r['p23_ok'], old_p23, r['verdict'], old_v)
        assert r['p23_ok'] == (r['exchangeability_ok'] and r['p3_ok'])
        seen[old_v] = seen.get(old_v, 0) + 1
        # with a calibration the gated verdict is the two-resume one unless it is UNRESOLVED_CALIBRATE (then the calibration's, whose own logic is untouched)
        R3_, R4_ = resume(a, off), resume(b, off)
        rc_ = R.rejudge(C, R1_, R2_, v, (R3_, R4_))
        if old_v == 'UNRESOLVED_CALIBRATE':
            assert rc_['calibration'] is not None and rc_['verdict'] == R.calibration(C, [R1_, R2_, R3_, R4_], v)['verdict']
        else:
            assert rc_['verdict'] == old_v and rc_['calibration'] is None and rc_['calibration_not_applied']
    assert set(seen) == {'INSIDE healthy noise', 'UNRESOLVED', 'UNRESOLVED_CALIBRATE', 'OUTSIDE'} and min(seen.values()) >= 20, seen
    print('ok rejudge: p23_ok = exch_ok and p3 gives the same p23_ok and the same verdict as the old formula over 3000 random traces ' + str(dict(sorted(seen.items()))))


# ================================================================ H: item 7 (ruling Q95): the early window is refused when it cannot be computed; supervisor aligned to rejudge_probe.py
def tree_state(root):
    """every file and folder under root with its sha256 (a refused probe must change none of it, add none, rename none)"""
    import hashlib
    out = {}
    for f in sorted(Path(root).rglob('*')):
        out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else 'dir'
    return out


def t_early_not_computable_probe():
    """(a) probe-resume with --upto < step+3: exit 3 with the message, before anything is run, written, renamed aside or logged."""
    import hashlib
    calls = []
    real_run, real_spawn = S.Sup.probe_run, S.spawn_detached
    S.Sup.probe_run = lambda *a, **k: calls.append('probe_run') or real_run(*a, **k)
    S.spawn_detached = lambda *a, **k: calls.append('spawn') or real_spawn(*a, **k)
    try:
        for upto in (202, 201, 200, 150):
            with tempfile.TemporaryDirectory() as tmp:
                p, keep = P.setup(tmp)
                before = tree_state(tmp)
                rc, out = AJ.quiet(P.probe, p, keep, upto=upto)
                assert rc == 3 and 'early window' in out and '202 and 203' in out and f'--upto {upto}' in out and 'step+3' in out, (upto, rc, out)
                assert tree_state(tmp) == before, f'--upto {upto}: the refusal changed files'
                assert calls == [] and no_probe_files(tmp)
        # an earlier report is not moved aside by the refusal (a good probe first, then the refused one)
        with tempfile.TemporaryDirectory() as tmp:
            p, keep = P.setup(tmp)
            assert probe_out(p, keep)[0] == 0
            calls.clear()
            before = tree_state(tmp)
            rc, out = AJ.quiet(P.probe, p, keep, upto=202)
            sd = Path(json.loads(p.read_text())['state_dir'])
            assert rc == 3 and tree_state(tmp) == before and not list(sd.glob('PROBE-RESUME-*.aside-*')) and calls == [], (rc, sorted(sd.glob('PROBE-RESUME-*.aside-*')))
            # the refusal comes first: even where an exit-2 reason also holds (the run armed and not finished), the answer is 3 and nothing is touched
        with tempfile.TemporaryDirectory() as tmp:
            p, keep = P.setup(tmp, armed=True)
            before = tree_state(tmp)
            assert AJ.quiet(P.probe, p, keep, upto=202)[0] == 3 and AJ.quiet(P.probe, p, keep)[0] == 2 and tree_state(tmp) == before
        # the smallest computable window: --upto step+3 runs
        with tempfile.TemporaryDirectory() as tmp:
            p, keep = P.setup(tmp)
            rc, out = AJ.quiet(P.probe, p, keep, upto=203)
            rep = P.report(p)
            assert rc == 0 and rep['steps'] == [201, 202, 203] and 'early_max' in rep and rep['early_limit'] == S.EARLY_LIMIT and calls, (rc, out)
    finally:
        S.Sup.probe_run, S.spawn_detached = real_run, real_spawn
    assert 'exit 3' in S.__doc__.split('"""')[0] or 'early window' in S.__doc__
    assert 'Exit 0 PASS, 1 FAIL, 2 refused' in S.probe_resume.__doc__ and '3 refused' in S.probe_resume.__doc__
    print('ok probe-resume --upto < step+3: exit 3, message names updates 202 and 203, no file written / renamed / logged, no probe started (also before the exit-2 reasons); --upto step+3 runs')


def t_early_not_computable_verdict():
    """(b) resume_probe_verdict on lists of under 3 updates emits no early keys; md_probe prints no early line; verdict and every old key are the original's."""
    rng = random.Random(7)
    for L in (1, 2):
        for _ in range(50):
            C = [rng.uniform(1, 5) for _ in range(L)]
            R1 = [c + rng.uniform(-0.3, 0.3) for c in C]
            R2 = [c + rng.uniform(-0.3, 0.3) for c in C]
            old, new = O.resume_probe_verdict(C, R1, R2), S.resume_probe_verdict(C, R1, R2)
            assert not {'early_max', 'early_limit', 'early_verdict'} & set(new), new
            assert json.dumps(old, sort_keys=True) == json.dumps({k: new[k] for k in old}, sort_keys=True) and old['verdict'] == new['verdict']
            r = dict(job='g2fa4', step=200, upto=200 + L, keep='k', why_fail=[], resume_warnings={}, steps=list(range(201, 201 + L)), C=C, R1=R1, R2=R2, **new)
            md = S.Sup.md_probe(r)
            assert 'early' not in md.lower() and 'P1b' not in md and 'recorded beside' in md, md
            json.dumps(r)
    # a None early_max (a hand-made or older report) prints no line either
    assert 'early window' not in S.Sup.md_probe(dict(r, early_max=None, early_limit=0.005, early_verdict=None))
    # three updates: computed and printed
    C = [1.0, 2.0, 3.0]
    new = S.resume_probe_verdict(C, [1.0, 2.001, 3.0], list(C))
    md = S.Sup.md_probe(dict(job='g2fa4', step=200, upto=203, keep='k', why_fail=[], resume_warnings={}, steps=[201, 202, 203], C=C, R1=[1.0, 2.001, 3.0], R2=list(C), **new))
    assert abs(new['early_max'] - 0.001) < 1e-12 and 'early window (the 2nd and 3rd probe updates = 202 and 203, P1b): max |R - C| = 0.001000' in md, md
    print('ok resume_probe_verdict under 3 updates: no early keys, md_probe prints no early line, verdict and all old keys equal the original\'s (100 random 1- and 2-update lists); 3 updates: computed and printed')


def t_early_not_computable_trace_a():
    """(c) trace A with exactly 2 redone updates records and prints no early value; with 3 it records early_max; resume_early_abs defers the window to the probe's P1b below 3 (ruling B2)."""
    for n_redone, keep_to in ((1, 101), (2, 102)):
        ev = AJ.FakeEv(0.0, 0.003)
        ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > keep_to)]
        for rules in (RULES, dict(RULES, soft=['peak', 'resume_max_abs'])):
            r = S.trace_a(ev, rules, 9000)
            assert r['resume']['n_redone'] == n_redone and 'early_max' not in r['resume'], r
            assert json.dumps(r, sort_keys=True) == json.dumps(O.trace_a(ev, rules, 9000), sort_keys=True), 'with no opt-in key the result is exactly the original\'s'
            assert 'early' not in json.dumps(r).lower(), r
        r = S.trace_a(ev, EARLY_ONLY, 9000)                                                 # opt-in: deferred to the probe's P1b (ruling B2), no failure, and still no early_max
        assert r['verdict'] == 'PASS' and 'early_max' not in r['resume'] and r['why_fail'] == [] and r['resume']['early_window'] == dict(computed=False, redone=n_redone, deferred_to='probe P1b'), r
    ev = AJ.FakeEv(0.0, 0.003)
    ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > 103)]
    r = S.trace_a(ev, RULES, 9000)
    assert r['resume']['n_redone'] == 3 and abs(r['resume']['early_max'] - 0.003) < 1e-9 and r['verdict'] == 'PASS', r
    assert S.trace_a(ev, EARLY_ONLY, 9000)['verdict'] == 'PASS'
    print('ok trace A: 1-2 redone updates record no early_max and mention no early window (the result equals the original\'s; resume_early_abs defers the window to the probe, no failure); 3 redone updates record it')


def t_early_agreement():
    """(d) supervisor and rejudge_probe.py agree: the same 2-update probe data is refused by both with exit 3; with 3+ updates both compute the same early_max."""
    with tempfile.TemporaryDirectory() as tmp:
        p, keep = P.setup(tmp, main_extra=['--jitter', '0.01'])
        rc, out = AJ.quiet(P.probe, p, keep)                                               # a real 50-update probe: the data
        full = P.report(p)
        assert rc in (0, 1) and len(full['C']) == 50 and full['early_max'] > 0, (rc, full.get('early_max'))
        sd = Path(json.loads(p.read_text())['state_dir'])
        # 2 updates of that very data
        two = Path(tmp) / 'two'; two.mkdir()
        f2 = write_probe(two, 'g2fa4', full['C'][:2], full['R1'][:2], full['R2'][:2], steps=full['steps'][:2], upto=202, early_limit=0.005)
        rc_r, out_r = AJ.quiet(R.main, [str(f2)])
        assert rc_r == 3 and 'at least 3 probe updates' in out_r and not list(two.glob('REJUDGE*')), (rc_r, out_r)
        with tempfile.TemporaryDirectory() as tmp2:
            p2, keep2 = P.setup(tmp2, main_extra=['--jitter', '0.01'])
            before = tree_state(tmp2)
            rc_s, out_s = AJ.quiet(P.probe, p2, keep2, upto=202)                           # the supervisor path for a probe of those 2 updates
            assert rc_s == 3 and tree_state(tmp2) == before, (rc_s, out_s)
        assert rc_s == rc_r == 3
        # 1 update: both refuse as well
        f1 = write_probe(two, 'one', full['C'][:1], full['R1'][:1], full['R2'][:1], upto=201)
        assert AJ.quiet(R.main, [str(f1)])[0] == 3
        # 3 and more updates: the same early_max from the two paths
        for k in (3, 4, 10, 50):
            sv = S.resume_probe_verdict(full['C'][:k], full['R1'][:k], full['R2'][:k])
            fk = write_probe(Path(tmp), f'k{k}', full['C'][:k], full['R1'][:k], full['R2'][:k], steps=full['steps'][:k], upto=200 + k)
            rc_k, _ = AJ.quiet(R.main, [str(fk)])
            j = json.loads((Path(tmp) / f'REJUDGE-k{k}.json').read_text())
            assert rc_k in (0, 1, 2) and j['early_max'] == sv['early_max'] and j['early_ok'] == (sv['early_verdict'] == 'PASS') and j['early_limit'] == sv['early_limit'], (k, j['early_max'], sv['early_max'])
        # and the real supervisor probe at the smallest window (--upto step+3) reproduces what rejudge computes from its own report
        with tempfile.TemporaryDirectory() as tmp3:
            p3, keep3 = P.setup(tmp3, main_extra=['--jitter', '0.01'])
            rc3, _ = AJ.quiet(P.probe, p3, keep3, upto=203)
            rep = P.report(p3)
            pj = Path(json.loads(p3.read_text())['state_dir']) / 'PROBE-RESUME-g2fa4.json'
            rc_j, _ = AJ.quiet(R.main, [str(pj)])
            j = json.loads((pj.parent / 'REJUDGE-g2fa4.json').read_text())
            assert len(rep['C']) == 3 and rc_j in (0, 1, 2) and j['early_max'] == rep['early_max'] > 0 and j['early_ok'] == (rep['early_verdict'] == 'PASS'), (rep['early_max'], j['early_max'])
    print('ok agreement: the same 1- and 2-update data is refused by probe-resume (exit 3, nothing touched) and by rejudge_probe.py (exit 3, nothing written); from 3 updates both give the same early_max (3, 4, 10, 50 updates, and a real --upto step+3 probe)')


# ================================================================ I: ruling B2 (early window not computable in the running gate = deferred to probe P1b, not a stop)
B2_RULES = dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10, resume_early_abs=0.005, resume_exact_fields=['lr'])


def b2_run(crash_at, *extra, rules=B2_RULES):
    """one supervisor run against the fake runner; crash_at = an unplanned crash at that update (the planned kill at 150 never happens after it: not ev.resumed); crash_at 0 = only the planned kill.
    Returns (sup, js, texts) where texts = every file of the state folder (name -> text)."""
    T.GPU[0] = 2000
    with tempfile.TemporaryDirectory() as tmp:
        sup = S.Sup(T.plan_for(tmp, steps=320, main_extra=(['--crash-at', str(crash_at)] if crash_at else []) + list(extra), trace_a=dict(rules), baseline=None, compare=None))
        T.drive(sup, lambda x: False, 150)
        texts = {f.name: f.read_text(encoding='utf-8', errors='replace') for f in sup.sd.iterdir() if f.is_file()}
        return sup, T.js(sup), texts


def t_b2_deferral_unit():
    """pass marks (1)-(3) at the level of trace_a / md_trace_a: the deferred window is recorded and printed, never a value or a PASS of the window."""
    for keep_to, n in ((101, 1), (102, 2)):
        ev = with_fields(AJ.FakeEv(0.0, 0.0))
        ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > keep_to)]
        r = S.trace_a(ev, EARLY_RULES, 9000)
        assert r['verdict'] == 'PASS' and r['why_fail'] == [] and r['resume']['early_window'] == dict(computed=False, redone=n, deferred_to='probe P1b'), r
        assert 'early_max' not in json.dumps(r)
        md = S.Sup.md_trace_a(dict(id='g2fa4'), r)
        assert S.EARLY_DEFERRED in md and 'early_max' not in md and md.count(S.EARLY_DEFERRED) == 1, md
        assert S.EARLY_DEFERRED == "early window not checked by the running gate; do not read this result until the probe's P1b passes."
        # (2) a first-update gap above 0.01, or an exact-field mismatch, still FAIL
        r = S.trace_a(bump(ev, 2, 101, loss=0.02), EARLY_RULES, 9000)
        assert r['verdict'] == 'FAIL' and any('first redone update differs by 0.0200' in w for w in r['why_fail']) and 'early_max' not in r['resume'], r
        ev2 = with_fields(AJ.FakeEv(0.0, 0.0))
        ev2.train = [e for e in ev2.train if not (e['seg'] == 1 and e['step'] > keep_to)]
        r = S.trace_a(bump(ev2, 2, 101, lr=2e-3), EARLY_RULES, 9000)
        assert r['verdict'] == 'FAIL' and any('must be exactly equal' in w and 'lr' in w for w in r['why_fail']) and 'early_max' not in r['resume'], r
    # (3) a planned resume (>= 3 redone updates): the window is computed; over 0.005 FAILs, healthy PASSes; no deferral
    r = S.trace_a(with_fields(AJ.FakeEv(0.0, 0.004)), EARLY_RULES, 9000)
    assert r['verdict'] == 'PASS' and r['resume']['early_window'] == dict(computed=True, steps=[102, 103]) and abs(r['resume']['early_max'] - 0.004) < 1e-9, r
    assert S.EARLY_DEFERRED not in S.Sup.md_trace_a(dict(id='g2fa4'), r) and S.early_deferred(r['resume']) is None
    r = S.trace_a(with_fields(AJ.FakeEv(0.0, 0.006)), EARLY_RULES, 9000)
    assert r['verdict'] == 'FAIL' and 'early redone updates 102 and 103' in r['why_fail'][0] and r['resume']['early_max'] > 0.005, r
    # without the opt-in keys: no early_window key at all
    assert 'early_window' not in S.trace_a(AJ.FakeEv(0.0, 0.004), RULES, 9000)['resume']
    print('ok B2 unit: 1 and 2 redone updates with the opt-in rules: PASS, early_window deferred (computed False), no early_max, the verbatim line in the TRACE-A md; first-update gap and exact-field mismatch still FAIL; 3+ redone: computed, over 0.005 FAILs')


def t_b2_running_gate():
    """pass marks (1)-(3) end to end: the supervisor against the fake runner with the --trace-a-early rules."""
    for crash_at, n in ((102, 1), (103, 2)):                          # crash n updates after the save at update 100, before the planned kill at 150
        sup, j, texts = b2_run(crash_at)
        assert j['status'] == 'done' and j['traceA']['verdict'] == 'PASS' and j['traceA']['why_fail'] == [], (crash_at, j)
        assert not any(k.startswith('STOPPED') for k in texts), crash_at
        r = json.loads(texts['TRACE-A-g2fa4.json'])
        assert r['resume']['n_redone'] == n and r['resume']['early_window'] == dict(computed=False, redone=n, deferred_to='probe P1b'), r['resume']
        assert not [x for x in j['restarts'] if x.get('planned')], j['restarts']
        for name in ('TRACE-A-g2fa4.md', 'status.md', 'DONE-g2fa4.txt', 'supervisor.log'):    # recorded and printed: the TRACE-A md, status.md, the finish message (DONE file and log line)
            assert S.EARLY_DEFERRED in texts[name], (crash_at, name, texts[name][-600:])
        assert not [k for k, v in texts.items() if 'early_max' in v], (crash_at, [k for k, v in texts.items() if 'early_max' in v])        # no early value anywhere
    # (2) the same runs with a first-update gap > 0.01, or an exact-field mismatch: FAIL and stop
    for crash_at in (102, 103):
        for extra, want in ((['--seg2-offset', '0.02'], 'first redone update differs by'), (['--seg2-lr', '0.002'], 'must be exactly equal')):
            sup, j, texts = b2_run(crash_at, *extra)
            assert j['status'] == 'stopped' and j['traceA']['verdict'] == 'FAIL' and any(want in w for w in j['traceA']['why_fail']), (crash_at, extra, j)
            assert 'STOPPED.txt' in texts and 'trace A FAILED' in j['why'], j['why']
            assert not [k for k, v in texts.items() if 'early_max' in v], (crash_at, extra)
    # (3) a planned resume (>= 3 redone updates): early_max > 0.005 still FAILs and stops; a healthy one PASSes with the window computed
    sup, j, texts = b2_run(0, '--seg2-offset', '0.007')                  # first update 0.007 <= 0.01, mean 0.007 <= 0.02, but 0.007 > 0.005 at updates 102 and 103
    r = json.loads(texts['TRACE-A-g2fa4.json'])
    assert j['status'] == 'stopped' and j['traceA']['verdict'] == 'FAIL' and any('early redone updates 102 and 103' in w for w in j['traceA']['why_fail']), j
    assert r['resume']['n_redone'] >= 3 and abs(r['resume']['early_max'] - 0.007) < 1e-6 and r['resume']['early_window']['computed'] is True and S.EARLY_DEFERRED not in texts['TRACE-A-g2fa4.md'], r['resume']
    sup, j, texts = b2_run(0)
    r = json.loads(texts['TRACE-A-g2fa4.json'])
    assert j['status'] == 'done' and j['traceA']['verdict'] == 'PASS' and r['resume']['n_redone'] >= 3 and r['resume']['early_max'] == 0.0 and r['resume']['early_window']['computed'] is True, (j, r['resume'])
    assert not [k for k, v in texts.items() if S.EARLY_DEFERRED in v], 'a computed window prints no deferral'
    print('ok B2 running gate: crash 1 and 2 updates after a save -> not stopped, PASS, deferral in TRACE-A md / status.md / DONE file / log, no early_max anywhere; gap > 0.01 or exact-field mismatch -> FAIL + stop; planned resume: early_max 0.007 FAILs + stops, healthy PASSes')



# ================================================================ J: ruling B3 (a window that is not contiguous is "not computable": deferred; a missing first redone update fails closed)
def drop(ev, seg, *steps):
    """remove the train lines of the given steps from one segment of a FakeEv"""
    ev.train = [e for e in ev.train if not (e['seg'] == seg and e['step'] in steps)]
    return ev


EXACT_ONLY = dict(RULES, resume_exact_fields=['lr'])


def t_b3_contiguity_unit():
    # missing rstep+1 (update 101): fail closed when an opt-in key is set, in every soft variant; the message names the steps
    for where, seg, who in (('resumed', 2, 'the resumed segment'), ('earlier', 1, 'the earlier segment')):
        for rules in (EARLY_ONLY, EARLY_RULES, EXACT_ONLY, dict(EARLY_RULES, soft=SOFT3 + ['resume_early_abs', 'resume_exact_fields'])):
            ev = with_fields(drop(AJ.FakeEv(0.0, 0.0), seg, 101))
            r = S.trace_a(ev, rules, 9000)
            assert r['verdict'] == 'FAIL' and len(r['why_fail']) == 1, (where, r['why_fail'])
            w = r['why_fail'][0]
            assert f'the first redone update 101 (the first update after the restore at 100) is missing from {who}; the first redone update present is 102: the first-update check cannot be computed as defined' == w, w
            assert r['resume']['first_diff'] is None and 'early_max' not in r['resume'] and 'exact_checked' not in r['resume'], r['resume']
            if 'resume_early_abs' in rules:
                ew = r['resume']['early_window']
                assert ew['computed'] is False and ew['deferred_to'] == 'probe P1b' and '102' in ew['reason'] and '103' in ew['reason'], ew
    ev = drop(drop(AJ.FakeEv(0.0, 0.0), 1, 101), 2, 101)                                  # missing from both: not in the intersection, so the first present is 102 again
    r = S.trace_a(ev, EARLY_ONLY, 9000)
    assert r['verdict'] == 'FAIL' and any('missing from the earlier segment and the resumed segment' in w for w in r['why_fail']), r['why_fail']          # (the merged trace has a hole as well)
    ev = drop(AJ.FakeEv(0.0, 0.0), 2, 101, 102, 103)                                      # first present is 104: named
    assert 'the first redone update present is 104' in S.trace_a(ev, EARLY_ONLY, 9000)['why_fail'][0]
    # without the opt-in keys the function is the original's, byte for byte (no failure, no early_max: the window steps are not contiguous from 101)
    for rules in (RULES, dict(RULES, soft=['peak', 'resume_max_abs']), dict(RULES, soft=SOFT3)):
        for seg in (1, 2):
            ev = drop(AJ.FakeEv(0.0, 0.0), seg, 101)
            a, b = O.trace_a(ev, rules, 9000), S.trace_a(ev, rules, 9000)
            assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) and b['verdict'] == 'PASS' and 'early_window' not in b['resume'], (a, b)
    # a gap at rstep+2 or rstep+3: the window is not computable -> the B2 deferral (PASS if otherwise healthy), no early_max, the steps named
    for gap in (102, 103):
        for seg in (1, 2):
            ev = with_fields(drop(AJ.FakeEv(0.0, 0.0), seg, gap))
            for rules in (EARLY_ONLY, EARLY_RULES):
                r = S.trace_a(ev, rules, 9000)
                ew = r['resume']['early_window']
                assert r['verdict'] == 'PASS' and r['why_fail'] == [] and 'early_max' not in r['resume'], (gap, r)
                assert ew['computed'] is False and ew['deferred_to'] == 'probe P1b' and ew['redone'] == r['resume']['n_redone'] >= 3 and str(gap) in ew['reason'] and 'must be updates 102 and 103' in ew['reason'], ew
                assert S.EARLY_DEFERRED in S.Sup.md_trace_a(dict(id='g2fa4'), r) and 'early_max' not in S.Sup.md_trace_a(dict(id='g2fa4'), r)
            assert S.trace_a(ev, EARLY_RULES, 9000)['resume']['exact_checked'] == ['lr', 'plan_gapped', 'plan_rows', 'rounds']          # the first-update item is still computed (update 101 is there)
            # no opt-in: the original's result (no early_max: not recorded for a non-contiguous window)
            assert json.dumps(O.trace_a(ev, RULES, 9000), sort_keys=True) == json.dumps(S.trace_a(ev, RULES, 9000), sort_keys=True)
            # other items still judge: a first-update gap or a window-independent miss FAILs, no value printed
            r = S.trace_a(bump(ev, 2, 101, loss=0.02), EARLY_ONLY, 9000)
            assert r['verdict'] == 'FAIL' and r['why_fail'][0].startswith('first redone update differs by') and 'early_max' not in r['resume'], r
    # a gap outside the window (update 104 or later): unchanged, the window is computed
    for gap in (104, 110):
        r = S.trace_a(drop(AJ.FakeEv(0.0, 0.004), 2, gap), EARLY_ONLY, 9000)
        assert r['verdict'] == 'PASS' and abs(r['resume']['early_max'] - 0.004) < 1e-9 and r['resume']['early_window'] == dict(computed=True, steps=[102, 103]), (gap, r)
    # a gap at 102 with only two updates before it (101, then 103): counted by the B2 rule alone (redone < 3 is the plain deferral, no reason)
    ev = AJ.FakeEv(0.0, 0.0)
    ev.train = [e for e in ev.train if not (e['seg'] == 1 and e['step'] > 103)]
    r = S.trace_a(drop(ev, 2, 102), EARLY_ONLY, 9000)
    assert r['resume']['n_redone'] == 2 and r['resume']['early_window'] == dict(computed=False, redone=2, deferred_to='probe P1b') and r['verdict'] == 'PASS', r
    # contiguous: unchanged (computed, over the bar fails, under passes), the exact-field item is run
    r = S.trace_a(with_fields(AJ.FakeEv(0.0, 0.004)), EARLY_RULES, 9000)
    assert r['verdict'] == 'PASS' and r['resume']['early_window']['computed'] is True and 'exact_checked' in r['resume'] and r['resume']['first_diff'] is not None
    assert S.trace_a(with_fields(AJ.FakeEv(0.0, 0.006)), EARLY_RULES, 9000)['verdict'] == 'FAIL'
    print('ok B3 unit: missing update 101 (either segment or both) fails closed under the opt-in rules (names the steps, no early value, hard in soft variants) and changes nothing without them; a gap at 102 or 103 is deferred (no early_max); a gap outside the window or none: computed as before')


def t_b3_running_gate():
    """end to end with the fake runner: a hole in the resumed segment's train lines."""
    # missing update 101 (rstep+1) after an unplanned crash and after the planned kill: FAIL and stop
    for crash_at in (103, 0):
        sup, j, texts = b2_run(crash_at, '--skip-log-seg2-at', '101')
        assert j['status'] == 'stopped' and j['traceA']['verdict'] == 'FAIL' and len(j['traceA']['why_fail']) == 1, (crash_at, j)
        assert 'first redone update 101 (the first update after the restore at 100) is missing from the resumed segment' in j['traceA']['why_fail'][0] and 'STOPPED.txt' in texts, j['traceA']
        assert not [k for k, v in texts.items() if 'early_max' in v]
    # a hole at 102 or 103 in a planned resume (>= 3 redone updates): deferred, PASS, printed three times, no early_max anywhere
    for gap in (102, 103):
        sup, j, texts = b2_run(0, '--skip-log-seg2-at', str(gap))
        r = json.loads(texts['TRACE-A-g2fa4.json'])
        assert j['status'] == 'done' and j['traceA']['verdict'] == 'PASS' and r['resume']['n_redone'] >= 3 and r['resume']['early_window']['computed'] is False and str(gap) in r['resume']['early_window']['reason'], (gap, j, r['resume'])
        for name in ('TRACE-A-g2fa4.md', 'status.md', 'DONE-g2fa4.txt', 'supervisor.log'):
            assert S.EARLY_DEFERRED in texts[name], (gap, name)
        assert not [k for k, v in texts.items() if 'early_max' in v], gap
    print('ok B3 running gate: missing update 101 -> FAIL + stop (after a crash and after the planned kill); a hole at 102 or 103 -> deferral printed in the TRACE-A md, status.md, DONE file and log, PASS, no early_max anywhere')



if __name__ == '__main__':
    todo = [t_queue_accum, t_keep_guard_unit, t_main_run_hashes, t_events_resume_warning, t_probe_refuses, t_probe_accum_warning,
            t_verdict_fields, t_verdict_nbar_zero, t_lag1, t_verdict_identical_to_original, t_md_probe,
            t_trace_a_mean_routing, t_installer_soft_mean, t_rejudge_cases, t_rejudge_cli,
            t_trace_a_early_optin, t_trace_a_exact_fields, t_trace_a_exact_missing, t_verdict_early, t_installer_trace_a_early, t_rejudge_amended, t_rejudge_calibration,
            t_probe_report_aside, t_rejudge_calibration_gated, t_rejudge_calibration_refused, t_rejudge_aside, t_trace_a_early_needs_three, t_early_limit_single_source,
            t_rejudge_calibration_errors_named, t_rejudge_p23_unchanged, t_early_not_computable_probe, t_early_not_computable_verdict, t_early_not_computable_trace_a, t_early_agreement,
            t_b2_deferral_unit, t_b2_running_gate, t_b3_contiguity_unit, t_b3_running_gate]
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
