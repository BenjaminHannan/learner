#!/usr/bin/env python3
"""python3 tests/test_addjob.py   (Linux, no GPU, a few minutes; test_supervisor.py runs it at its end): the second job (g2fa8) next to a stopped, skipped g2fa4.
Supervisor: a two-job plan where job 1 is 'stopped' with a recorded trace A FAIL (made by the real supervisor, not written by hand) and skip=true; job 2 has NO baseline and runs to
ALL-DONE with the planned kill at 150 and the resume; job 1's files and state are byte-identical before / after; an old ARMED.txt does not arm job 2, `arm` does; a STOPPED.txt of the
skipped job does not block job 2, a stop of job 2 gets its own file; `clear` leaves the skipped job alone; preflight and probe-resume ignore / refuse the skipped job.
Installer: `--add-job g2fa8 [--skip-g2fa4] [--check]` on a simulated PC folder (the installer's own env overrides; the pinned hashes are replaced by those of small fake files):
the expected plan.json, the old plan / supervisor kept aside, the A4 files and the recorded state of g2fa4 untouched, idempotence, refusals."""
import contextlib, hashlib, importlib.util, io, json, os, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_supervisor as T
S = T.S

SKIP_REASON = 'trace A FAIL recorded, gate 3 FAIL on the 4090; replaced by g2fa8'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(root):
    """{relative path: sha256} of every file under root."""
    root = Path(root)
    return {str(f.relative_to(root)): sha(f) for f in sorted(root.rglob('*')) if f.is_file()}


def quiet(fn, *a, **k):
    """-> (return value, stdout text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*a, **k)
    return r, buf.getvalue()


def main_cmd(pp, *args):
    return quiet(S.main, ['--plan', str(pp)] + list(args))


# ---------------------------------------------------------------- the supervisor
def stopped_g2fa4(tmp, steps=900):
    """a one-job plan whose job g2fa4 the REAL supervisor runs into 'stopped' (trace A FAIL: a resume that does not match). -> plan path. This is the recorded state the PC has."""
    T.GPU[0] = 2000
    pp = T.plan_for(tmp, steps=steps, main_extra=['--seg2-offset', '0.3'])
    sup = S.Sup(pp)
    s = T.drive(sup, lambda x: False, 90)
    j = sup.st['jobs']['g2fa4']
    assert s is None and j['status'] == 'stopped' and j['traceA']['verdict'] == 'FAIL', j
    assert (sup.sd / 'STOPPED.txt').exists() and (sup.sd / 'TRACE-A-g2fa4.json').exists()
    T.cleanup()
    return pp


def add_second_job(pp, steps=900, job2_extra=(), skip=True, baseline=False):
    """plan.json becomes [g2fa4 (+ skip keys), g2fa8 (no baseline)]; the old ARMED.txt (the go line of g2fa4) stays."""
    plan = json.loads(Path(pp).read_text())
    j1 = plan['jobs'][0]
    if skip:
        j1['skip'], j1['skip_reason'] = True, SKIP_REASON
    common = ['{python}', T.FAKE, '--work', '{work}', '--queue', '{qpath}', '--busy', '{busy}', '--steps', str(steps), '--step-s', '0.02', '--ckpt-every', '100']
    j2 = dict(id='g2fa8', title='G2f-a8 (test)', src=j1['src'], queue='ACC8-pc', job='ACC8-3M', arm='B3G2', steps=steps, accum=8, runner_match='fake_runner', kill_resume_at=150,
              runner_cmd=common + ['--job', 'ACC8-3M'] + list(job2_extra), trace_a=dict(j1['trace_a']), compare=dict(j1['compare']))
    if baseline:
        j2['baseline'] = dict(queue='BASE-pc', job='BASE-3M', upto=300, need_free_mib=4000, runner_cmd=common + ['--job', 'BASE-3M'])
    plan['jobs'].append(j2)
    (Path(plan['jobs'][0]['src']) / 'custom_io' / 'queue_local' / 'ACC8-pc.txt').write_text('# fake\n')
    Path(pp).write_text(json.dumps(plan))
    return plan


def record_of_job1(tmp):
    """sha256 of everything that belongs to g2fa4: its results folder, its queue files, STOPPED.txt, its trace A files, and its entry of state.json (canonical json)."""
    tmp = Path(tmp)
    out = {}
    for root in (tmp / 'work' / 'results' / 'MAIN-pc', tmp / 'src' / 'custom_io' / 'queue_local' / 'MAIN-pc.txt', tmp / 'src' / 'custom_io' / 'queue_local' / 'BASE-pc.txt'):
        for f in ([root] if root.is_file() else sorted(root.rglob('*'))):
            if f.is_file():
                out[str(f.relative_to(tmp))] = sha(f)
    for n in ('STOPPED.txt', 'TRACE-A-g2fa4.json', 'TRACE-A-g2fa4.md'):
        out['state/' + n] = sha(tmp / 'state' / n)
    ent = json.loads((tmp / 'state' / 'state.json').read_text())['jobs']['g2fa4']
    out['state.json:g2fa4'] = hashlib.sha256(json.dumps(ent, sort_keys=True).encode()).hexdigest()
    return out


def t_two_jobs_skip_no_baseline():
    with tempfile.TemporaryDirectory() as tmp:
        pp = stopped_g2fa4(tmp)
        sd = Path(tmp) / 'state'
        add_second_job(pp)
        before = record_of_job1(tmp)
        log0 = (sd / 'supervisor.log').read_text()
        old_armed = (sd / 'ARMED.txt').read_text()
        assert not (sd / 'ALL-DONE.txt').exists()
        # 1. the old go line (no jobs line) arms the plan's first job only: g2fa8 is NOT started by it, and the stop file of the skipped job does not matter
        sup = S.Sup(pp)
        assert sup.blocking_stops() == [], sup.blocking_stops()
        assert sup.cycle() is None and not sup.find('fake_runner', 'ACC8-pc'), 'g2fa8 started on the old go line'
        assert 'does not arm job g2fa8' in (sd / 'supervisor.log').read_text()
        r, out = main_cmd(pp, 'run')
        assert r == 0 and 'nothing to do' in out and 'does not arm job g2fa8' in out and not sup.find('fake_runner', 'ACC8-pc'), out
        # 2. `arm` arms the active (non-skipped) job: the jobs line names g2fa8 only; the old ARMED.txt is kept aside
        r, _ = main_cmd(pp, 'arm', 'Ben 4:00 PM ET: go g2fa8')
        assert r == 0
        armed = (sd / 'ARMED.txt').read_text()
        assert 'Ben 4:00 PM ET: go g2fa8' in armed and armed.splitlines()[1] == 'jobs: g2fa8', armed
        assert [f.read_text() for f in sd.glob('ARMED.txt.aside-*')] == [old_armed]
        # 3. g2fa8 runs to the end: planned kill at 150, resume, trace A, no baseline, ALL-DONE; g2fa4 is never started
        log1 = (sd / 'supervisor.log').read_text()
        sup = S.Sup(pp)
        T.drive(sup, lambda x: False, 120)
        j2, ev = sup.st['jobs']['g2fa8'], sup.events(sup.plan['jobs'][1])
        assert j2['status'] == 'done', j2
        assert j2['kill_done'].startswith('killed at update') and ev.seg == 2 and ev.resumed and ev.resumed[0][1] == 100, (j2['kill_done'], ev.seg, ev.resumed)
        assert j2['traceA']['verdict'] == 'PASS', j2['traceA']
        assert j2['base']['status'] == 'none' and 'compare' not in j2, j2
        assert 'baseline' not in sup.plan['jobs'][1]
        assert (sd / 'ALL-DONE.txt').exists() and (sd / 'DONE-g2fa8.txt').exists() and (sd / 'TRACE-A-g2fa8.md').exists()
        assert not list(sd.glob('COMPARE-*')) and not list(sd.glob('ATTENTION*')), sorted(p.name for p in sd.iterdir())
        assert 'no baseline' in (sd / 'DONE-g2fa8.txt').read_text() and 'baseline: none' in (sd / 'status.md').read_text()
        new_log = (sd / 'supervisor.log').read_text()[len(log1):]
        assert 'BASE-pc' not in new_log and 'MAIN-pc' not in new_log, 'a runner of the baseline or of the skipped job was touched'
        assert not [1 for pid, cmd in S.list_procs() if 'fake_runner' in cmd and ('MAIN-3M' in cmd or 'BASE-3M' in cmd)]
        # 4. g2fa4's files and state are byte-identical; its stop file did not block; the skip is logged once; its last status is kept next to the shared status.md
        after = record_of_job1(tmp)
        assert after == before, {k: (before.get(k), after.get(k)) for k in set(before) | set(after) if before.get(k) != after.get(k)}
        assert (sd / 'STOPPED.txt').exists() and not list(sd.glob('STOPPED*.aside-*')) and not (sd / 'STOPPED-g2fa8.txt').exists()
        assert new_log.count('is skipped') == 1, new_log.count('is skipped')                      # one line for the whole run of this supervisor, not one per cycle
        assert (sd / 'supervisor.log').read_text()[len(log0):].count('is skipped') == 2           # (plus the one of the first look above)
        snap = sd / 'status-g2fa4.md'
        assert snap.exists() and 'job g2fa4 (test job): **stopped**' in snap.read_text() and 'job g2fa8' in (sd / 'status.md').read_text()
        print('ok two jobs: g2fa4 stopped + skipped is byte-identical; the old go line did not arm g2fa8, `arm` did; g2fa8 (no baseline) ran kill@150 -> resume -> trace A PASS -> ALL-DONE, no ATTENTION')


def t_skip_never_run_not_pending():
    with tempfile.TemporaryDirectory() as tmp:
        T.GPU[0] = 2000
        pp = T.plan_for(tmp, steps=400)                                      # g2fa4 is in the plan and skipped, and has never run: no results, no state
        plan = add_second_job(pp, steps=400)
        main_cmd(pp, 'arm', 'Ben: go g2fa8')
        sup = S.Sup(pp)
        T.drive(sup, lambda x: False, 90)
        assert sup.st['jobs']['g2fa8']['status'] == 'done' and (sup.sd / 'ALL-DONE.txt').exists()
        assert 'skipped: g2fa4' in (sup.sd / 'ALL-DONE.txt').read_text()
        assert 'g2fa4' not in json.loads((sup.sd / 'state.json').read_text())['jobs'], 'a state entry was made for the skipped job'
        assert not (Path(plan['work']) / 'results' / 'MAIN-pc').exists() and not (sup.sd / 'status-g2fa4.md').exists()
        print('ok a skipped job that never ran is not counted as pending (ALL-DONE) and gets no state entry')


def t_stop_files_and_clear():
    with tempfile.TemporaryDirectory() as tmp:
        pp = stopped_g2fa4(tmp)
        sd = Path(tmp) / 'state'
        add_second_job(pp, job2_extra=['--nan-at', '200'])
        main_cmd(pp, 'arm', 'Ben: go g2fa8')
        before = record_of_job1(tmp)
        sup = S.Sup(pp)
        s = T.drive(sup, lambda x: False, 90)
        j2 = sup.st['jobs']['g2fa8']
        assert s is None and j2['status'] == 'stopped' and 'nonfinite_loss' in j2['why'], j2
        # the stop of g2fa8 got its own file (STOPPED.txt is g2fa4's and stays as it was); both are readable; only g2fa8's blocks
        mine = sd / 'STOPPED-g2fa8.txt'
        assert mine.exists() and 'job g2fa8:' in mine.read_text() and 'clear g2fa8' in mine.read_text()
        assert record_of_job1(tmp) == before
        assert [p.name for p in sup.blocking_stops()] == ['STOPPED-g2fa8.txt'], sup.blocking_stops()
        assert sup.cycle() is None
        # clear: an unknown id and the skipped job are refused (nothing changes); clear without an id releases g2fa8 only
        for bad in ('nosuchjob', 'g2fa4'):
            r, out = main_cmd(pp, 'clear', bad)
            assert r == 2 and mine.exists() and record_of_job1(tmp) == before, (bad, r, out)
        r, _ = main_cmd(pp, 'clear')
        sup = S.Sup(pp)
        assert r == 0 and not mine.exists() and list(sd.glob('STOPPED-g2fa8.txt.aside-*')), sorted(p.name for p in sd.iterdir())
        assert sup.st['jobs']['g2fa8']['status'] == 'pending' and 'why' not in sup.st['jobs']['g2fa8']
        assert record_of_job1(tmp) == before and sup.blocking_stops() == []
        # an unreadable stop file blocks (nobody knows whose it is); `clear g2fa8` moves it aside
        (sd / 'STOPPED.txt').rename(sd / 'keep-STOPPED.txt')
        (sd / 'STOPPED.txt').write_text('garbage\n')
        assert [p.name for p in S.Sup(pp).blocking_stops()] == ['STOPPED.txt']
        r, _ = main_cmd(pp, 'clear', 'g2fa8')
        assert r == 0 and not (sd / 'STOPPED.txt').exists()
        T.cleanup()
        print('ok a stop of g2fa8 writes STOPPED-g2fa8.txt and blocks only itself; clear leaves the skipped job and its STOPPED.txt alone; unknown / skipped ids are refused')


def t_arm_rules():
    with tempfile.TemporaryDirectory() as tmp:
        pp = T.plan_for(tmp)
        add_second_job(pp)
        sd = Path(tmp) / 'state'
        sup = S.Sup(pp)
        g4, g8 = sup.plan['jobs']
        assert sup.armed_for(g4) and not sup.armed_for(g8), 'an ARMED.txt without a jobs line arms the first job only'
        main_cmd(pp, 'arm', 'a')
        assert not sup.armed_for(g4) and sup.armed_for(g8) and (sd / 'ARMED.txt').read_text().splitlines()[1] == 'jobs: g2fa8'
        # one job, no skip: the same as before (the jobs line names it)
        pp1 = T.plan_for(tmp + '/one')
        assert main_cmd(pp1, 'arm', 'Ben: go')[0] == 0
        s1 = S.Sup(pp1)
        assert (Path(tmp) / 'one' / 'state' / 'ARMED.txt').read_text().splitlines()[1] == 'jobs: g2fa4' and s1.armed_for(s1.plan['jobs'][0])
        # nothing armed at all
        (sd / 'ARMED.txt').unlink()
        assert not S.Sup(pp).armed_for(g8)
        # the jobs line is line 2 only: "jobs:" inside line 1 or on a later line arms nothing (an old go line stays an old go line)
        (sd / 'ARMED.txt').write_text('2026-10-14 15:55:00 armed: Ben go\nsome text\njobs: g2fa8\n')
        assert S.Sup(pp).armed_ids() == 'first' and not S.Sup(pp).armed_for(g8)
        (sd / 'ARMED.txt').write_text('2026-10-14 15:55:00 armed: jobs: g2fa8\n')
        assert S.Sup(pp).armed_ids() == 'first'
        (sd / 'ARMED.txt').write_text('2026-10-14 15:55:00 armed: go\r\njobs: g2fa8\r\n')                            # CRLF still reads
        assert S.Sup(pp).armed_ids() == ['g2fa8']
        # an ARMED.txt that cannot be read for a moment (Windows: open elsewhere): retried; if it stays unreadable the decision of the last look stands (a running loop does not leave)
        sup2 = S.Sup(pp)
        assert sup2.armed_ids() == ['g2fa8']
        real_read, calls = Path.read_text, []
        def locked(self, *a, **k):
            if self.name == 'ARMED.txt':
                calls.append(1)
                raise PermissionError('open elsewhere')
            return real_read(self, *a, **k)
        old_sleep = S.time.sleep
        Path.read_text, S.time.sleep = locked, (lambda t: None)
        try:
            assert sup2.armed_ids() == ['g2fa8'] and len(calls) == 5, (sup2.armed_ids(), len(calls))
            assert S.Sup(pp).armed_ids() is None                                                      # never looked before and unreadable: not armed (fails safe)
        finally:
            Path.read_text, S.time.sleep = real_read, old_sleep
        print('ok arm: the jobs line names the non-skipped jobs; an old ARMED.txt arms the first job only; the jobs line is line 2 only; an unreadable ARMED.txt is retried and the last decision stands; a one-job plan is armed as before')


def t_preflight_and_probe_skip():
    with tempfile.TemporaryDirectory() as tmp:
        pp = stopped_g2fa4(tmp)
        add_second_job(pp)
        r, out = main_cmd(pp, 'preflight')
        lines = out.splitlines()
        assert any('skipped' in ln and 'g2fa4' in ln for ln in lines), out
        assert not any('FIX' in ln and ('g2fa4' in ln or 'STOPPED' in ln or 'MAIN-pc' in ln or 'MAIN-3M' in ln) for ln in lines), out        # the skipped job's output and STOPPED.txt are no problem
        assert any('ACC8' in ln for ln in lines), out                                                                                         # the active job is checked
        # probe-resume: the skipped job is refused (also named explicitly); the default job is the first active one
        keep = Path(tmp) / 'keep'
        keep.mkdir()
        for ext in ('pt', 'json'):
            (keep / f'step-200.{ext}').write_bytes(b'x')
        sd = Path(tmp) / 'state'
        (sd / 'ARMED.txt').rename(sd / 'ARMED.txt.aside-old')
        (sd / 'ALL-DONE.txt').write_text('done\n')                                         # (so that the only reasons left to refuse are about the job)
        r, out = main_cmd(pp, 'probe-resume', '--keep', str(keep), '--step', '200', '--upto', '250', '--job', 'g2fa4')
        assert r == 2 and 'skipped' in out, out
        r, out = main_cmd(pp, 'probe-resume', '--keep', str(keep), '--step', '200', '--upto', '250')
        assert r == 2 and 'ACC8-3M' in out and 'MAIN-3M' not in out, out                  # no --job: the first job that is not skipped (g2fa8), refused because it has no logged updates 201..250
        print('ok preflight ignores the skipped job (no FIX for its output or STOPPED.txt); probe-resume refuses it')


# ---------------------------------------------------------------- the installer
def load_installer(tmp):
    """a fresh copy of install_g2fa4.py aimed at a simulated PC folder; the pinned hashes are replaced by those of small fake files (the real ones need the real custom_io)."""
    cio = Path(tmp) / 'custom-io'
    os.environ['G2FA4_MINFREE_GB'] = '0'                                     # (read when the checks run, not at import: this sandbox has little disk)
    env = {'G2FA4_CIO': str(cio), 'G2FA4_PY': sys.executable, 'G2FA4_BUSY': str(Path(tmp) / 'GPU-BUSY.txt')}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        spec = importlib.util.spec_from_file_location('install_g2fa4_t', HERE.parent / 'install_g2fa4.py')
        I = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(I)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    src0 = I.SRC0 / 'custom_io'
    for rel in I.PINS0:
        f = src0 / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f'fake {rel}\n')
    (src0 / 'tests').mkdir(exist_ok=True)
    (I.SRC0 / 'G2-SETUP-OK.txt').write_text('commit 74d6e92c75\n')
    caps = I.WORK / 'b3-inputs' / 'caps_b3g2.json'
    caps.parent.mkdir(parents=True)
    caps.write_text('{"fake": 1}\n')
    I.PINS0 = {rel: I.sha(src0 / rel) for rel in I.PINS0}
    I.CAPS_B3G2_WORK = I.sha(caps)
    return I


def installed_pc(tmp):
    """the simulated PC after the G2f-a4 install and the stop of g2fa4. -> installer module"""
    I = load_installer(tmp)
    I.STAMP = 'T0'
    rc, out = quiet(I.main, ['--skip-tests'])
    assert rc == 0 and 'G2FA4 INSTALL DONE' in out, out
    (I.SRC / 'G2FA4-SETUP-OK.txt').write_text(f'T0 installed: src-b3g2 (74d6e92c75) + overlay train.py {I.OVERLAY_TRAIN}; tests passed\n', encoding='ascii')      # what the real install writes after its CPU test
    sd = I.STATE
    (sd / 'g2fa4_supervisor.py').write_text('# the older supervisor of the first install\n')
    (sd / 'state.json').write_text(json.dumps({'jobs': {'g2fa4': {'status': 'stopped', 'why': 'trace A FAILED: x', 'traceA': {'verdict': 'FAIL', 'why_fail': ['x']}, 'restarts': [], 'kill_done': 'killed at update 151'}}}, indent=1))
    (sd / 'STOPPED.txt').write_text('2026-10-14 21:30:00 job g2fa4: trace A FAILED: x\nread status.md and supervisor.log; after the cause is removed: python g2fa4_supervisor.py clear g2fa4\n')
    (sd / 'ARMED.txt').write_text('2026-10-14 15:55:00 armed: Ben go\n')
    (sd / 'TRACE-A-g2fa4.json').write_text('{"verdict": "FAIL"}\n')
    (sd / 'status.md').write_text('job g2fa4 (G2f-a4): **stopped**\n')
    return I


def pc_files(I):
    d = tree(I.STATE)
    d.update({'queue_local/' + k: v for k, v in tree(I.SRC / 'custom_io' / 'queue_local').items()})
    return d


def expected_g2fa8(I, soft=False):
    d = dict(id='g2fa8', title='G2f-a8 (B3G2 3M seed 400, accum 8)', src=str(I.SRC), queue='8aB3G2A8-pc', job='8aB3G2A8-3M-s400', arm='B3G2', steps=24000, accum=8, kill_resume_at=150,
                trace_a=dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10),
                compare=dict(upto=300, last_n=50, diff_mean_pass=0.03, diff_mean_fail=0.06, last_n_pass=0.05, last_n_fail=0.10, report_from=101))
    if soft:
        d['trace_a']['soft'] = ['peak', 'resume_max_abs']
    return d


class FakeEv:
    """just enough of the events object for trace_a(): 300 updates, a resume at 100 whose redone updates 101-150 differ from the first segment by `maxdiff` at one update."""
    def __init__(self, maxdiff, mean_diff_each=0.001):
        self.nonfinite = False
        self.resumed = [(2, 100)]
        self.train = []
        for s in range(1, 301):
            loss = 18.0 - 0.05 * s
            if s <= 150:
                self.train.append(dict(seg=1, step=s, loss=loss))
            if s > 100:
                self.train.append(dict(seg=2, step=s, loss=loss + (maxdiff if s == 147 else (mean_diff_each if 101 < s <= 150 else 0.0))))

    def merged(self):
        return {e['step']: e['loss'] for e in self.train}


def t_trace_a_soft_items():
    """the two soft items are recorded, not gated; everything else still stops; with no soft list the verdict is as registered."""
    rules = dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10)
    hard = S.trace_a(FakeEv(0.119), rules, 15757)
    assert hard['verdict'] == 'FAIL' and len(hard['why_fail']) == 2 and hard['soft_misses'] == [], hard['why_fail']                  # the g2fa4 case: both items trip (as registered)
    soft = S.trace_a(FakeEv(0.119), dict(rules, soft=['peak', 'resume_max_abs']), 15757)
    assert soft['verdict'] == 'PASS' and soft['why_fail'] == [] and len(soft['soft_misses']) == 2, soft
    # the other items are still hard with soft on: a non-finite loss, a loss that does not fall, a first redone update off by more than 0.01, a mean difference over 0.02
    ev = FakeEv(0.119)
    ev.nonfinite = True
    assert S.trace_a(ev, dict(rules, soft=['peak', 'resume_max_abs']), 9000)['verdict'] == 'FAIL'
    assert S.trace_a(FakeEv(0.0, mean_diff_each=0.03), dict(rules, soft=['peak', 'resume_max_abs']), 9000)['verdict'] == 'FAIL'
    ev = FakeEv(0.0)
    for e in ev.train:
        if e['seg'] == 2 and e['step'] == 101:
            e['loss'] += 0.02
    assert S.trace_a(ev, dict(rules, soft=['peak', 'resume_max_abs']), 9000)['verdict'] == 'FAIL'
    flat = FakeEv(0.0)
    for e in flat.train:
        e['loss'] = 5.0
    assert S.trace_a(flat, dict(rules, soft=['peak', 'resume_max_abs']), 9000)['verdict'] == 'FAIL'
    assert S.trace_a(FakeEv(0.05), dict(rules, soft=['peak', 'resume_max_abs']), 9000)['verdict'] == 'PASS' and S.trace_a(FakeEv(0.05), rules, 9000)['verdict'] == 'PASS'
    md = S.Sup.md_trace_a(dict(id='g2fa8'), soft)
    assert 'recorded, not gated' in md and '15757' in md
    print('ok trace A soft items: peak and the largest single resume difference are recorded (not gated) with rules.soft; NaN / no fall / first-update / mean difference still stop; without rules.soft nothing changed')


def t_attention_names():
    """ATTENTION-<kind>.txt stays g2fa4's name; every other job writes ATTENTION-<kind>-<id>.txt."""
    with tempfile.TemporaryDirectory() as tmp:
        pp = stopped_g2fa4(tmp)
        add_second_job(pp)
        sup = S.Sup(pp)
        j4, j8 = sup.plan['jobs']
        for kind in ('stall', 'ckpt', 'baseline', 'compare'):
            assert sup.attn_path(kind, j4).name == f'ATTENTION-{kind}.txt' and sup.attn_path(kind, j8).name == f'ATTENTION-{kind}-g2fa8.txt', kind
        # arm swaps ARMED.txt in with the retrying replace (a PermissionError for a moment, as on Windows with the file open, is survived)
        real, calls = os.replace, []
        def flaky(src, dst):
            calls.append(1)
            if len(calls) <= 2 and str(dst).endswith('ARMED.txt'):
                raise PermissionError('the file is open')
            return real(src, dst)
        os.replace = flaky
        old_sleep = S.time.sleep
        S.time.sleep = lambda t: None
        try:
            rc, _ = main_cmd(pp, 'arm', 'Ben test words')
        finally:
            os.replace = real
            S.time.sleep = old_sleep
        assert rc == 0 and len(calls) >= 3 and (sup.sd / 'ARMED.txt').read_text().splitlines()[1] == 'jobs: g2fa8', (rc, len(calls))
        print('ok ATTENTION files: g2fa4 keeps the old names, other jobs get -<id>; `arm` survives a locked ARMED.txt (retry)')
    T.cleanup()


def t_installer_add_job():
    with tempfile.TemporaryDirectory() as tmp:
        I = installed_pc(tmp)
        pack_sup = I.IN / 'g2fa4_supervisor.py'
        old_plan_bytes = (I.STATE / 'plan.json').read_bytes()
        old_plan = json.loads(old_plan_bytes)
        assert [j['id'] for j in old_plan['jobs']] == ['g2fa4'] and 'baseline' in old_plan['jobs'][0] and 'skip' not in old_plan['jobs'][0]
        before = pc_files(I)
        # --check changes nothing
        I.STAMP = 'T1'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--check'])
        assert rc == 0 and 'CHECK ONLY' in out and 'append job g2fa8; g2fa4: skip = true' in out and pc_files(I) == before, out
        assert 'stop file naming g2fa4: STOPPED.txt' in out and 'ARMED.txt: present, no jobs line' in out, out                # the real ARMED.txt and stop file are read and shown
        # the real run
        I.STAMP = 'T2'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])
        assert rc == 0 and 'ADD-JOB g2fa8 DONE' in out, out
        new = json.loads((I.STATE / 'plan.json').read_text())
        assert [j['id'] for j in new['jobs']] == ['g2fa4', 'g2fa8']
        assert {k: v for k, v in new.items() if k != 'jobs'} == {k: v for k, v in old_plan.items() if k != 'jobs'}, 'plan keys other than jobs changed'
        g4 = new['jobs'][0]
        assert g4['skip'] is True and g4['skip_reason'] == SKIP_REASON and {k: v for k, v in g4.items() if k not in ('skip', 'skip_reason')} == old_plan['jobs'][0], g4
        assert new['jobs'][1] == expected_g2fa8(I) and 'baseline' not in new['jobs'][1], new['jobs'][1]
        assert new['jobs'][1]['trace_a']['peak_limit_mib'] == 12288
        # kept aside / copied
        assert (I.STATE / 'plan.json.aside-T2').read_bytes() == old_plan_bytes
        assert (I.STATE / 'g2fa4_supervisor.py.aside-T2').read_text() == '# the older supervisor of the first install\n' and sha(I.STATE / 'g2fa4_supervisor.py') == sha(pack_sup)
        ql = I.SRC / 'custom_io' / 'queue_local'
        assert sha(ql / '8aB3G2A8-pc.txt') == sha(I.IN / 'queue' / '8aB3G2A8-pc.txt') and not list(ql.glob('*.aside-*'))
        log = (I.STATE / 'add-job-g2fa8-T2.txt').read_text()
        assert sha(ql / '8aB3G2A8-pc.txt') in log and 'not touched' in log and 'same as the pack' in log and '[ok] src-b3g2 models/b3g2.py' in log and 'sha256' in log, log
        # everything else of the recorded state is byte-identical
        after = pc_files(I)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        assert changed == {'plan.json', 'plan.json.aside-T2', 'g2fa4_supervisor.py', 'g2fa4_supervisor.py.aside-T2', 'add-job-g2fa8-T2.txt', 'queue_local/8aB3G2A8-pc.txt'}, changed
        for n in ('STOPPED.txt', 'ARMED.txt', 'state.json', 'TRACE-A-g2fa4.json', 'status.md'):
            assert before[n] == after[n], n
        assert 'does NOT arm g2fa8' in out
        # the new supervisor reads the plan: g2fa4 skipped, its STOPPED.txt does not block, the old ARMED.txt does not arm g2fa8
        sup = S.Sup(I.STATE / 'plan.json')
        assert [j['id'] for j in sup.active_jobs()] == ['g2fa8'] and sup.blocking_stops() == [] and not sup.armed_for(sup.plan['jobs'][1])
        # idempotent: the same command again, with and without --skip-g2fa4, changes nothing but its own log
        for flags in (['--skip-g2fa4'], []):
            before2 = pc_files(I)
            I.STAMP = 'T3' if flags else 'T4'
            rc, out = quiet(I.main, ['--add-job', 'g2fa8'] + flags)
            assert rc == 0 and 'already as wanted' in out and 'not rewritten' in out, out
            after2 = pc_files(I)
            assert {k for k in set(before2) | set(after2) if before2.get(k) != after2.get(k)} == {f'add-job-g2fa8-{I.STAMP}.txt'}, sorted(set(after2) ^ set(before2))
        # a plain install run later keeps the longer plan
        I.STAMP = 'T5'
        plan_before = (I.STATE / 'plan.json').read_bytes()
        rc, out = quiet(I.main, ['--skip-tests'])
        assert rc == 0 and 'kept as it is' in out and (I.STATE / 'plan.json').read_bytes() == plan_before and not list(I.STATE.glob('plan.json.aside-T5')), out
        print('ok installer --add-job: --check changes nothing; the plan is [g2fa4 + skip, g2fa8 without baseline]; old plan and supervisor kept aside; g2fa4 state untouched; idempotent; a plain install keeps the plan')


def t_installer_soft_trace_a():
    with tempfile.TemporaryDirectory() as tmp:
        I = installed_pc(tmp)
        before = pc_files(I)
        I.STAMP = 'V1'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a', '--check'])
        assert rc == 0 and 'CHECK ONLY' in out and pc_files(I) == before, out
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a'])
        assert rc == 0 and 'ADD-JOB g2fa8 DONE' in out, out
        new = json.loads((I.STATE / 'plan.json').read_text())
        assert new['jobs'][1] == expected_g2fa8(I, soft=True) and new['jobs'][1]['trace_a']['soft'] == ['peak', 'resume_max_abs'], new['jobs'][1]
        sup = S.Sup(I.STATE / 'plan.json')
        assert sup.plan['jobs'][1]['trace_a']['soft'] == ['peak', 'resume_max_abs']
        # the same command again changes nothing but its own log; the strict command after the soft one is refused (the entry differs), nothing changes
        before2 = pc_files(I)
        I.STAMP = 'V2'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--soft-trace-a'])
        after2 = pc_files(I)
        assert rc == 0 and {k for k in set(before2) | set(after2) if before2.get(k) != after2.get(k)} == {'add-job-g2fa8-V2.txt'}, out
        before3 = pc_files(I)
        I.STAMP = 'V3'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])
        assert rc == 1 and 'differs from the expected entry' in out and pc_files(I) == before3, out
    with tempfile.TemporaryDirectory() as tmp:
        I = load_installer(tmp)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                I.main(['--soft-trace-a'])
        except SystemExit as e:
            assert e.code == 2
        else:
            raise AssertionError('--soft-trace-a without --add-job was accepted')
    print('ok installer --soft-trace-a: the g2fa8 entry carries trace_a.soft; check changes nothing; idempotent; the strict command after the soft one is refused')


def t_installer_without_skip_and_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        I = installed_pc(tmp)
        I.STAMP = 'U1'                                                                       # g2fa4 stopped and not skipped: its stop file would hold the loop, a `clear` would restart it -> refused
        before = pc_files(I)
        rc, out = quiet(I.main, ['--add-job', 'g2fa8'])
        assert rc == 1 and 'g2fa4 is stopped' in out and 'would not be skipped' in out and 'run with --skip-g2fa4' in out and pc_files(I) == before, out
    with tempfile.TemporaryDirectory() as tmp:                                               # g2fa4 NOT stopped (state pending, no stop file): added without a skip is fine; --skip-g2fa4 is refused
        I = installed_pc(tmp)
        (I.STATE / 'state.json').write_text(json.dumps({'jobs': {'g2fa4': {'status': 'pending'}}}))
        (I.STATE / 'STOPPED.txt').unlink()
        before = pc_files(I)
        I.STAMP = 'U1b'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4', '--check'])
        assert rc == 1 and 'g2fa4 is not stopped' in out and 'state.json: pending' in out and pc_files(I) == before, out
        rc, out = quiet(I.main, ['--add-job', 'g2fa8'])
        new = json.loads((I.STATE / 'plan.json').read_text())
        assert rc == 0 and [j['id'] for j in new['jobs']] == ['g2fa4', 'g2fa8'] and 'skip' not in new['jobs'][0] and 'skip_reason' not in new['jobs'][0], (out, new['jobs'][0])
    with tempfile.TemporaryDirectory() as tmp:                                               # state says stopped but no stop file names g2fa4 (the file is another job's): --skip-g2fa4 refused
        I = installed_pc(tmp)
        (I.STATE / 'STOPPED.txt').write_text('2026-10-14 21:30:00 job g2fa9: something else\n')
        before = pc_files(I)
        I.STAMP = 'U1c'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])
        assert rc == 1 and 'stop file naming g2fa4: none' in out and pc_files(I) == before, out
    with tempfile.TemporaryDirectory() as tmp:                                                   # g2fa4 running: it is not skipped
        I = installed_pc(tmp)
        (I.STATE / 'state.json').write_text(json.dumps({'jobs': {'g2fa4': {'status': 'running'}}}))
        before = pc_files(I)
        I.STAMP = 'U2'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])
        assert rc == 1 and 'g2fa4 is running' in out and pc_files(I) == before, out
    with tempfile.TemporaryDirectory() as tmp:                                                   # a g2fa8 entry that differs is refused, not overwritten
        I = installed_pc(tmp)
        I.STAMP = 'U3'
        assert quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])[0] == 0
        plan = json.loads((I.STATE / 'plan.json').read_text())
        plan['jobs'][1]['steps'] = 5
        (I.STATE / 'plan.json').write_text(json.dumps(plan, indent=1))
        before = pc_files(I)
        I.STAMP = 'U4'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])
        assert rc == 1 and 'differs from the expected entry' in out and pc_files(I) == before, out
    with tempfile.TemporaryDirectory() as tmp:                                                   # a pin that does not match (the same checks as the install): nothing is done
        I = installed_pc(tmp)
        (I.SRC / 'custom_io' / 'models' / 'b3g2.py').write_text('changed\n')
        before = pc_files(I)
        I.STAMP = 'U5'
        rc, out = quiet(I.main, ['--add-job', 'g2fa8', '--skip-g2fa4'])
        assert rc == 1 and '[FIX] src-b3g2ck models/b3g2.py' in out and 'NOT DONE' in out and pc_files(I) == before, out
    with tempfile.TemporaryDirectory() as tmp:                                                   # flags that do not go together
        I = load_installer(tmp)
        for argv in (['--skip-g2fa4'], ['--add-job', 'g2fa8', '--register'], ['--add-job', 'nope']):
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    I.main(argv)
            except SystemExit as e:
                assert e.code == 2, (argv, e.code)
            else:
                raise AssertionError(f'{argv} was accepted')
    print('ok installer: --skip-g2fa4 needs a g2fa4 that is stopped (state.json AND a stop file naming it); a stopped g2fa4 is not left unskipped; refused while g2fa4 runs, for a differing g2fa8 entry, for a wrong pin, for flags that do not go together; nothing changed in those cases')


if __name__ == '__main__':
    try:
        for t in (t_arm_rules, t_two_jobs_skip_no_baseline, t_skip_never_run_not_pending, t_stop_files_and_clear, t_preflight_and_probe_skip, t_attention_names, t_trace_a_soft_items, t_installer_add_job, t_installer_soft_trace_a, t_installer_without_skip_and_refusals):
            try:
                t()
            finally:
                T.cleanup()
        print('ADD-JOB TESTS OK')
    finally:
        T.cleanup()
