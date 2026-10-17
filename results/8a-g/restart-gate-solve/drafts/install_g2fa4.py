#!/usr/bin/env python3
"""install_g2fa4.py: puts the G2f-a4 pack on BensPC. Run it with the PC's own python from the folder the Mac copied (C:\\Users\\benja\\custom-io\\in-g2fa4):

    C:\\Users\\benja\\AppData\\Local\\Programs\\Python\\Python310\\python.exe install_g2fa4.py [--check] [--skip-tests] [--register]
    C:\\Users\\benja\\AppData\\Local\\Programs\\Python\\Python310\\python.exe install_g2fa4.py --add-job g2fa8 [--skip-g2fa4] [--soft-trace-a [--soft-trace-a-mean]] [--trace-a-early] [--check]

It starts no training job and changes nothing that already exists (a folder or file it replaces is renamed .aside-<stamp>). Steps:
 1. refuses if a custom_io job is running (it would compete for the CPU and the GPU) and checks the pinned hashes of src-b3g2 (the code G2f ran: custom_io at 74d6e92c75);
 2. src-b3g2ck = a copy of src-b3g2 with ONE changed file, custom_io/train.py (the checkpoint / resume overlay of the AT run) and the new tests; src-b3g2 stays untouched;
 3. the two queue files; WORK\\g2fa4\\ with the supervisor and plan.json (its pins are the hashes of what was just checked);
 4. CPU tests of the overlay on the b3g2 model (tiny; the test also runs the Windows file handling: os.replace over a file, fsync): flags off == the unmodified train.py,
    a kill in the middle of a checkpoint interval + --resume == the uninterrupted run. Bit for bit when this CPU is reproducible; the PC's is not (the unmodified train.py
    differs from itself), so the test first measures that noise and allows 20x it (see overlay-tests/test_ckpt_b3g2.py);
 5. with --register: scheduled tasks via PowerShell (Register-ScheduledTask): G2FA4-SUPERVISOR (SYSTEM, highest rights; at startup and every 5 min, no time limit, a second instance is ignored),
    G2FA4-SUPERVISOR-LOGON (this user, DISABLED: the fallback if the selftest shows that SYSTEM cannot use the GPU; enable it only then, and disable the first),
    G2FA4-SELFTEST (SYSTEM, run on demand). They do nothing until the supervisor is armed (`arm`).
--check only does step 1 and reports. Exit 0 = installed (or checked) fine.

--add-job g2fa8 (after the install above; no tests, no scheduled tasks, starts nothing): ADDS the accum-8 job as a second job of plan.json and leaves g2fa4 alone. It runs the same checks as step 1
plus the installed src-b3g2ck (the mark and pins of the g2fa4 install), then (a) copies queue/8aB3G2A8-pc.txt next to the A4 queue files (sha256 logged; the A4 files are not touched), (b) puts the
pack's g2fa4_supervisor.py (the version that honors `skip` and a job without a baseline) into WORK\\g2fa4\\ BEFORE plan.json changes (the old one is kept as .aside-<stamp>), (c) rewrites plan.json:
the old one is kept as plan.json.aside-<stamp>, the job list becomes [g2fa4 unchanged, g2fa8], and only with --skip-g2fa4 the g2fa4 entry gets skip=true and a skip_reason (refused unless g2fa4 is stopped: state.json says
'stopped' AND a stop file names g2fa4; and a stopped g2fa4 is never left unskipped, its stop file would hold the loop). With --soft-trace-a the g2fa8 entry's trace A records, and does not gate, the
whole-card memory peak and the largest single resume difference (the reading of the result is gated after the run instead); with --soft-trace-a-mean as well (only together with --soft-trace-a) it also records, and does not gate, the mean absolute resume difference (the first redone update, NaN/Inf and the loss falling stay hard in every variant). With --trace-a-early (opt-in, valid with --add-job g2fa8, alone or with the soft flags; PREREG-trace-a2.md Amendment 1) the g2fa8 entry's trace A gets two more HARD items: resume_early_abs = 0.005 (largest difference over the 2nd and 3rd redone updates) and resume_exact_fields = ['lr', 'rounds', 'plan_'] (those logged fields must be equal at the first redone update). The variants (strict, soft, soft + mean, each with or without --trace-a-early) are never mixed: the entry differs, so the second run is refused. --check shows what the real ARMED.txt arms. Idempotent: a second run changes nothing; a g2fa8 entry that differs from the expected one is refused, never overwritten. ARMED.txt, STOPPED.txt, state.json and everything of
g2fa4 are not touched: the old go line does not arm g2fa8 (README). The log of the run goes to WORK\\g2fa4\\add-job-g2fa8-<stamp>.txt. A plain install run later keeps the longer plan."""
import argparse, copy, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

IN = Path(__file__).resolve().parent
CIO = Path(os.environ.get('G2FA4_CIO', r'C:\Users\benja\custom-io'))         # the env overrides are for the test on a Linux box only
WORK = CIO / 'work'
SRC0, SRC = CIO / 'src-b3g2', CIO / 'src-b3g2ck'
STATE = WORK / 'g2fa4'
PY = os.environ.get('G2FA4_PY', r'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe')
BUSY = os.environ.get('G2FA4_BUSY', r'C:\Users\benja\GPU-BUSY.txt')
EGPATH = os.environ.get('G2FA4_EGPATH', r'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages')
COMMIT = '74d6e92c75'
STAMP = time.strftime('%Y%m%d-%H%M%S')

# SHA-256 of the files of custom_io at COMMIT that the job and the overlay depend on (the same hashes install_rr.ps1 pinned on 10-12 for the files it lists).
PINS0 = {
    'models/b3g2.py': 'a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce',
    'models/writer.py': 'f3a40ad58749bbc24a964942dc650c79864d6a74442628aac7d752730e73309e',
    'g8a/caps.py': '32862ae2d4e6e401fcad5bb6c5e54b0b8845019202dea73e2cb4c7efe5eea03e',
    'g8a/caps_b3g2.json': 'ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4',
    'g8a/job.py': 'a590e3f176159f531571b1e5ae95bd48d2160238cb999add5eb6be7734fe6a1a',
    'g8a/configs.py': '31287a25a6ad9cbf48973520f1174c788a3db5ce61f607265aa5ec8fa99bd5da',
    'local_runner.py': '0562a4bb065a02f6c048d919d68bb6d445f36e357518dc8826d9d545323db4ef',
    'train.py': 'e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d',        # the UNMODIFIED train.py
}
OVERLAY_TRAIN = 'e75e45fa43c6a6422c0a0e4222e05d8afc27580ec6551100680ed8f9ecdc5015'
CAPS_B3G2_WORK = 'ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4'          # WORK\b3-inputs\caps_b3g2.json


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# jobs that --add-job can add to an installed plan (queue file in the pack's queue/ folder; everything else of the entry is copied from the g2fa4 entry of the plan)
ADD_JOBS = {
    'g2fa8': dict(title='G2f-a8 (B3G2 3M seed 400, accum 8)', queue='8aB3G2A8-pc', job='8aB3G2A8-3M-s400', accum=8),
}
SKIP_G2FA4_REASON = 'trace A FAIL recorded, gate 3 FAIL on the 4090; replaced by g2fa8'
A4_QUEUES = ('8aB3G2A4-pc.txt', '8aB3G2A4b32-pc.txt')

ok_all = True
LINES = []                                   # every line printed by row() / say(): the log of an --add-job run


def say(msg=''):
    print(msg, flush=True)
    LINES.append(msg)


def row(good, what, detail=''):
    global ok_all
    ok_all = ok_all and good
    say(f'[{"ok" if good else "FIX"}] {what} {detail}')
    return good


def aside(p):
    p = Path(p)
    if p.exists():
        q = p.with_name(p.name + '.aside-' + STAMP)
        os.replace(p, q)
        print(f'      moved aside: {q}')


def procs():
    if os.name != 'nt':
        sys.path.insert(0, str(IN))
        import g2fa4_supervisor as S
        return [(str(p), c) for p, c in S.list_procs()]
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }")
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout.strip():                           # this installer is itself a python process, so an empty list means the listing failed
        return [('?', f'custom_io: the process listing FAILED (rc {r.returncode}): {r.stderr.strip()[:120]}')]
    return [ln.partition('|')[::2] for ln in r.stdout.splitlines() if '|' in ln]


def shaq(p):
    return sha(p) if Path(p).is_file() else None


def replace_retry(src, dst):
    """os.replace with a few retries (Windows: the destination may be open for a moment, e.g. plan.json read by the supervisor)."""
    for i in range(10):
        try:
            return os.replace(src, dst)
        except PermissionError:
            if i == 9:
                raise
            time.sleep(0.5)


STOP_RE = re.compile(r'^\S+ \S+ job ([^\s:]+):')           # first line of a supervisor stop file: "<date> <time> job <id>: <why>"


def stop_file_of(job_id):
    """the stop file in STATE written by this job (STOPPED.txt or STOPPED-<id>.txt; the first line names the job), or None."""
    for p in sorted(STATE.glob('STOPPED*.txt')):
        try:
            m = STOP_RE.match(p.read_text(encoding='utf-8', errors='replace').splitlines()[0])
        except (OSError, IndexError):
            continue
        if m and m.group(1) == job_id:
            return p
    return None


def armed_text():
    """what the real ARMED.txt says it arms: absent / 'jobs: ...' / an old file without a jobs line (arms the plan's first job only)."""
    p = STATE / 'ARMED.txt'
    try:
        lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return 'absent'
    ids = [ln[len('jobs:'):].split() for ln in lines if ln.startswith('jobs:')]
    return f'present, jobs line {ids[-1]}' if ids else 'present, no jobs line (an old file: it arms the first job of the plan only)'


SOFT_TRACE_A = ['peak', 'resume_max_abs']          # --soft-trace-a: these two trace A items are recorded, not gated (TRACE-A-READING-2026-10-14.md: gate the reading of the result, not the running)
SOFT_TRACE_A_MEAN = SOFT_TRACE_A + ['resume_mean_abs']          # --soft-trace-a --soft-trace-a-mean: the mean absolute resume difference too (opt-in; never a default)
TRACE_A_EARLY = dict(resume_early_abs=0.005, resume_exact_fields=['lr', 'rounds', 'plan_'])          # --trace-a-early (opt-in, hard items; PREREG-trace-a2.md Amendment 1): early window 2nd-3rd redone update, exact data/RNG/schedule fields at the first


def new_job_entry(spec_id, g4, soft=False, soft_mean=False, early=False):
    """the plan entry of an added job: the registered recipe of `spec_id` on the same src; trace A rules and the compare dict are the g2fa4 ones (the whole-card peak limit stays 12288), NO baseline."""
    spec = ADD_JOBS[spec_id]
    return dict(id=spec_id, title=spec['title'], src=g4['src'], queue=spec['queue'], job=spec['job'], arm='B3G2', steps=24000, accum=spec['accum'], kill_resume_at=150,
                trace_a=dict(copy.deepcopy(g4['trace_a']), peak_limit_mib=12288, **(dict(soft=list(SOFT_TRACE_A_MEAN if soft_mean else SOFT_TRACE_A)) if soft else {}), **(copy.deepcopy(TRACE_A_EARLY) if early else {})), compare=copy.deepcopy(g4['compare']))


def added_plan(old, spec_id, skip_g4, g4_state_status, g4_stop=None, soft=False, soft_mean=False, early=False):
    """-> (new plan, [what changes], [problems]). `old` is not modified. Idempotent: a plan that already has the job (and the skip, if asked) comes back equal."""
    new, changes, problems = copy.deepcopy(old), [], []
    jobs = new.get('jobs', [])
    g4 = next((j for j in jobs if j.get('id') == 'g2fa4'), None)
    if g4 is None:
        return new, changes, ['plan.json has no job g2fa4 (nothing to build the new entry from)']
    want = new_job_entry(spec_id, g4, soft, soft_mean, early)
    have = next((j for j in jobs if j.get('id') == spec_id), None)
    if have is None:
        jobs.append(want)
        changes.append(f'append job {spec_id}')
    elif have != want:
        problems.append(f'plan.json already has a job {spec_id} that differs from the expected entry: not touched (compare the two by hand)')
    stopped = g4_state_status == 'stopped' and g4_stop is not None                 # g2fa4 stopped by the supervisor: state.json says so AND a stop file names g2fa4
    if skip_g4 and not g4.get('skip'):
        if g4_state_status == 'running':
            problems.append('state.json says g2fa4 is running: not skipped (stop it first)')
        elif not stopped:
            problems.append(f'g2fa4 is not stopped (state.json: {g4_state_status or "not recorded"}; stop file naming g2fa4: {g4_stop.name if g4_stop else "none"}): --skip-g2fa4 is only for a g2fa4 that the supervisor stopped, not skipped')
        else:
            g4['skip'], g4['skip_reason'] = True, SKIP_G2FA4_REASON
            changes.append('g2fa4: skip = true')
    elif not skip_g4 and not g4.get('skip') and (g4_state_status == 'stopped' or g4_stop is not None):
        problems.append(f'g2fa4 is stopped (state.json: {g4_state_status or "not recorded"}; stop file: {g4_stop.name if g4_stop else "none"}) and would not be skipped: that stop file would hold the loop, and a later `clear` would restart G2f-a4; run with --skip-g2fa4')
    return new, changes, problems


def add_job(a):
    """--add-job: see the docstring. -> exit code."""
    spec_id = a.add_job
    spec = ADD_JOBS[spec_id]
    qfile = spec['queue'] + '.txt'
    LINES.clear()
    say(f'install_g2fa4 --add-job {spec_id}{" --skip-g2fa4" if a.skip_g2fa4 else ""}{" --soft-trace-a" if a.soft_trace_a else ""}{" --soft-trace-a-mean" if a.soft_trace_a_mean else ""}{" --trace-a-early" if a.trace_a_early else ""}{" --check" if a.check else ""} {STAMP} from {IN}')
    # 1. the checks of the install (pins of src-b3g2, caps, the pack's files, python, disk) + the installed copy and the plan
    step1_checks(('overlay/train.py', 'queue/' + qfile, 'g2fa4_supervisor.py') + tuple('queue/' + q for q in A4_QUEUES))
    mark = SRC / 'G2FA4-SETUP-OK.txt'
    mt = mark.read_text(errors='replace').strip() if mark.exists() else ''
    row(OVERLAY_TRAIN in mt and 'tests passed' in mt, 'src-b3g2ck\\G2FA4-SETUP-OK.txt (overlay train.py, tests passed)', mt[:120] or 'MISSING')
    for rel, want in PINS0.items():
        if rel != 'train.py':
            row(shaq(SRC / 'custom_io' / rel) == want, f'src-b3g2ck {rel}')
    row(shaq(SRC / 'custom_io' / 'train.py') == OVERLAY_TRAIN, 'src-b3g2ck train.py = overlay')
    loops = [(p, c[:90]) for p, c in procs() if 'g2fa4_supervisor' in c and c.strip().endswith(' run')]
    row(not loops, 'no supervisor loop (run) is alive', str(loops))
    row(not (STATE / 'ALL-DONE.txt').exists(), 'no ALL-DONE.txt (the loop would not start with it)')
    pp = STATE / 'plan.json'
    try:
        old = json.loads(pp.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = None
    row(old is not None, 'plan.json of the install', str(pp))
    if old is not None:
        try:
            stj = json.loads((STATE / 'state.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            stj = {}
        g4s = stj.get('jobs', {}).get('g2fa4', {}).get('status')
        g4stop = stop_file_of('g2fa4')
        say(f'      state.json: g2fa4 is {g4s or "not recorded"}; stop file naming g2fa4: {g4stop.name if g4stop else "none"}; ARMED.txt: {armed_text()}')
        new, changes, problems = added_plan(old, spec_id, a.skip_g2fa4, g4s, g4stop, a.soft_trace_a, a.soft_trace_a_mean, a.trace_a_early)
        row(not problems, 'plan.json can take the new job', '; '.join(problems))
        say('      plan.json: ' + ('; '.join(changes) if changes else 'already as wanted, nothing to change') + f'; jobs after: {[j.get("id") for j in new.get("jobs", [])]}')
    if a.check or not ok_all:
        say('CHECK ONLY (nothing changed)' if a.check else 'NOT DONE: fix the [FIX] lines first (nothing changed)')
        return 0 if ok_all else 1
    # 2. the queue file next to the A4 ones (a different file is renamed .aside-<stamp>; the A4 files are only read)
    ql = SRC / 'custom_io' / 'queue_local'
    ql.mkdir(exist_ok=True)
    want_sha, dst = sha(IN / 'queue' / qfile), ql / qfile
    if dst.exists() and sha(dst) == want_sha:
        say(f'queue file {qfile} is already in place; kept; sha256 {want_sha}')
    else:
        if dst.exists():
            aside(dst)
        shutil.copy2(IN / 'queue' / qfile, dst)
        say(f'queue file {qfile} copied to {ql}; sha256 {want_sha}')
    for q in A4_QUEUES:
        say(f'queue file {q} (not touched): ' + (f'sha256 {sha(ql / q)}, ' + ('same as the pack' if sha(ql / q) == sha(IN / 'queue' / q) else 'DIFFERENT from the pack') if (ql / q).exists() else 'MISSING'))
    # 3. the supervisor that honors `skip` and a job without a baseline goes in BEFORE plan.json changes; the old one stays as .aside-<stamp>; the swap is one os.replace
    STATE.mkdir(parents=True, exist_ok=True)
    sup, newsup = STATE / 'g2fa4_supervisor.py', IN / 'g2fa4_supervisor.py'
    if sup.exists() and sha(sup) == sha(newsup):
        say('g2fa4_supervisor.py in place is the pack\'s; kept')
    else:
        if sup.exists():
            shutil.copy2(sup, sup.with_name(sup.name + '.aside-' + STAMP))
        tmp = sup.with_name(sup.name + '.new')
        shutil.copy2(newsup, tmp)
        replace_retry(tmp, sup)
        say(f'g2fa4_supervisor.py replaced by the pack\'s (sha256 {sha(newsup)}); the old one is kept as {sup.name}.aside-{STAMP}')
    # 4. plan.json: the old one is kept as plan.json.aside-<stamp>, the new one is written to a temp file and swapped in with one os.replace
    if new != old:
        shutil.copy2(pp, pp.with_name(pp.name + '.aside-' + STAMP))
        tmp = pp.with_name(pp.name + '.new')
        tmp.write_text(json.dumps(new, indent=1), encoding='utf-8')
        replace_retry(tmp, pp)
        say(f'wrote {pp} (jobs {[j["id"] for j in new["jobs"]]}); the old plan is kept as {pp.name}.aside-{STAMP}')
    else:
        say(f'{pp} already has the job{" and the skip" if a.skip_g2fa4 else ""}; not rewritten')
    ar = STATE / 'ARMED.txt'
    first = (ar.read_text(errors='replace').strip().splitlines() or [''])[0][:100] if ar.exists() else None
    say('ARMED.txt: ' + ('absent' if first is None else f'{armed_text()}, not touched ({first})') + f'. It does NOT arm {spec_id}: an old go line counts for the job it was given for only; '
        f"{spec_id} starts only after `arm` on Ben's own words.")
    (STATE / f'add-job-{spec_id}-{STAMP}.txt').write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    say(f'G2FA4 ADD-JOB {spec_id} DONE (log: add-job-{spec_id}-{STAMP}.txt in {STATE})')
    return 0


def step1_checks(pack_files):
    """step 1 (shared by the install and --add-job): nothing running, pins of src-b3g2, the caps file, the pack's files, python, disk. -> path of WORK\\b3-inputs\\caps_b3g2.json"""
    busy = [(p, c[:100]) for p, c in procs() if 'custom_io' in c and 'install_g2fa4' not in c]
    row(not busy, 'no custom_io job is running', str(busy))
    sf = SRC0 / 'G2-SETUP-OK.txt'
    say('      src-b3g2\\G2-SETUP-OK.txt: ' + (sf.read_text(errors='replace').replace('\n', ' | ')[:300] if sf.exists() else 'MISSING') + ' (information; the hashes below decide)')
    for rel, want in PINS0.items():
        p = SRC0 / 'custom_io' / rel
        h = sha(p) if p.exists() else None
        row(h == want, f'src-b3g2 {rel}', (h or 'MISSING')[:12])
    cb = WORK / 'b3-inputs' / 'caps_b3g2.json'
    row(cb.exists() and sha(cb) == CAPS_B3G2_WORK, 'WORK\\b3-inputs\\caps_b3g2.json', (sha(cb)[:12] if cb.exists() else 'MISSING'))
    for rel in pack_files:
        row((IN / rel).exists(), f'pack file {rel}')
    row((IN / 'overlay' / 'train.py').exists() and sha(IN / 'overlay' / 'train.py') == OVERLAY_TRAIN, 'overlay train.py hash', OVERLAY_TRAIN[:12])
    row(Path(PY).exists(), 'python', PY)
    du = shutil.disk_usage(str(WORK))
    row(du.free > float(os.environ.get('G2FA4_MINFREE_GB', 30)) * 2 ** 30, 'disk', f'{du.free / 2 ** 30:.0f} GB free')
    return cb


def main(argv=None):
    global ok_all
    ok_all = True
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--skip-tests', action='store_true')
    ap.add_argument('--register', action='store_true')
    ap.add_argument('--add-job', choices=sorted(ADD_JOBS), help='add this job to the plan of an installed pack (no tests, no tasks, starts nothing)')
    ap.add_argument('--soft-trace-a', action='store_true', help='with --add-job g2fa8: trace A records (does not gate) the whole-card memory peak and the largest single resume difference')
    ap.add_argument('--soft-trace-a-mean', action='store_true', help='only with --soft-trace-a: the mean absolute resume difference is recorded, not gated, as well (opt-in)')
    ap.add_argument('--trace-a-early', action='store_true', help='with --add-job g2fa8 (opt-in): trace A gets two more hard items, the early window (2nd-3rd redone update <= 0.005) and equal lr / rounds / plan_* fields at the first redone update')
    ap.add_argument('--skip-g2fa4', action='store_true', help='with --add-job g2fa8: mark the g2fa4 job skip=true in plan.json')
    a = ap.parse_args(argv)
    if (a.skip_g2fa4 or a.soft_trace_a or a.trace_a_early) and a.add_job != 'g2fa8':
        ap.error('--skip-g2fa4 / --soft-trace-a / --trace-a-early only go with --add-job g2fa8')
    if a.soft_trace_a_mean and not a.soft_trace_a:
        ap.error('--soft-trace-a-mean only goes together with --soft-trace-a (it adds an item to the soft list)')
    if a.add_job and (a.register or a.skip_tests):
        ap.error('--register / --skip-tests do not go with --add-job')
    if a.add_job:
        return add_job(a)
    print(f'install_g2fa4 {STAMP} from {IN}')
    # 1. nothing running, pins of src-b3g2
    cb = step1_checks(('overlay/train.py', 'overlay/tests/test_ckpt.py', 'overlay-tests/test_ckpt_b3g2.py', 'queue/8aB3G2A4-pc.txt', 'queue/8aB3G2A4b32-pc.txt', 'g2fa4_supervisor.py'))
    if a.check or not ok_all:
        print('CHECK ONLY' if a.check else 'NOT INSTALLED: fix the [FIX] lines first')
        return 0 if ok_all else 1

    # 2. src-b3g2ck
    done = SRC / 'G2FA4-SETUP-OK.txt'
    if done.exists() and OVERLAY_TRAIN in done.read_text(errors='replace') and sha(SRC / 'custom_io' / 'train.py') == OVERLAY_TRAIN:
        print('src-b3g2ck is already installed with this overlay; kept')
    else:
        aside(SRC)
        shutil.copytree(SRC0, SRC, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(IN / 'overlay' / 'train.py', SRC / 'custom_io' / 'train.py')
        for f in (IN / 'overlay' / 'tests' / 'test_ckpt.py', IN / 'overlay-tests' / 'test_ckpt_b3g2.py'):
            shutil.copy2(f, SRC / 'custom_io' / 'tests' / f.name)
        print(f'copied {SRC0} -> {SRC}; train.py replaced by the overlay; two tests added')
    for f in (IN / 'overlay' / 'tests' / 'test_ckpt.py', IN / 'overlay-tests' / 'test_ckpt_b3g2.py'):          # the tests are always the pack's (a kept src-b3g2ck may hold older ones)
        dst = SRC / 'custom_io' / 'tests' / f.name
        if not dst.exists() or sha(dst) != sha(f):
            if dst.exists():
                aside(dst)
            shutil.copy2(f, dst)
            print(f'test file {f.name} refreshed in {SRC}')
    for rel, want in PINS0.items():
        if rel != 'train.py':
            row(sha(SRC / 'custom_io' / rel) == want, f'src-b3g2ck {rel}')
    row(sha(SRC / 'custom_io' / 'train.py') == OVERLAY_TRAIN, 'src-b3g2ck train.py = overlay')
    # 3. queue files + WORK\g2fa4
    ql = SRC / 'custom_io' / 'queue_local'
    ql.mkdir(exist_ok=True)
    for q in ('8aB3G2A4-pc.txt', '8aB3G2A4b32-pc.txt'):
        dst = ql / q
        if dst.exists() and sha(dst) != sha(IN / 'queue' / q):
            aside(dst)
        shutil.copy2(IN / 'queue' / q, dst)
    STATE.mkdir(parents=True, exist_ok=True)
    sup = STATE / 'g2fa4_supervisor.py'
    if sup.exists() and sha(sup) != sha(IN / 'g2fa4_supervisor.py'):
        aside(sup)
    shutil.copy2(IN / 'g2fa4_supervisor.py', sup)
    pins = {str(SRC / 'custom_io' / rel.replace('/', os.sep)): h for rel, h in PINS0.items() if rel != 'train.py'}
    pins[str(SRC / 'custom_io' / 'train.py')] = OVERLAY_TRAIN
    pins[str(cb)] = CAPS_B3G2_WORK
    plan = dict(
        version=1, work=str(WORK), busy=BUSY, python=PY, state_dir=str(STATE), poll_s=15, max_no_progress=3, gpu=dict(need_free_mib=9500), pins=pins,
        jobs=[dict(id='g2fa4', title='G2f-a4 (B3G2 3M seed 400, accum 4)', src=str(SRC), queue='8aB3G2A4-pc', job='8aB3G2A4-3M-s400', arm='B3G2', steps=24000, accum=4, kill_resume_at=150,
                   trace_a=dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10),
                   compare=dict(upto=300, last_n=50, diff_mean_pass=0.03, diff_mean_fail=0.06, last_n_pass=0.05, last_n_fail=0.10, report_from=101),
                   baseline=dict(queue='8aB3G2A4b32-pc', job='8aB3G2A4b32-3M-s400', upto=300, need_free_mib=4000))])
    pp = STATE / 'plan.json'
    cur = json.loads(pp.read_text()) if pp.exists() else None
    if cur and ([j.get('id') for j in cur.get('jobs', [])] != ['g2fa4'] or any(j.get('skip') for j in cur.get('jobs', []))):
        print(f'{pp} holds more than the plain g2fa4 job ({[j.get("id") for j in cur["jobs"]]}, skip: {[j.get("id") for j in cur["jobs"] if j.get("skip")]}): kept as it is (--add-job changes it)')
    else:
        if pp.exists() and cur != plan:
            aside(pp)
        pp.write_text(json.dumps(plan, indent=1))
        print(f'wrote {pp}')
    # 4. CPU tests of the overlay on b3g2 (also the Windows file handling)
    tests = 'skipped'
    if not a.skip_tests:
        env = dict(os.environ, PYTHONPATH=EGPATH, BASE_TREE=str(SRC0), OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1')
        t0 = time.time()
        r = subprocess.run([PY, '-m', 'custom_io.tests.test_ckpt_b3g2'], cwd=str(SRC), env=env, capture_output=True, text=True, timeout=3600)
        (STATE / f'install-test-{STAMP}.txt').write_text(r.stdout + '\n--- stderr ---\n' + r.stderr[-6000:], encoding='utf-8')
        good = row(r.returncode == 0 and 'ALL OK' in r.stdout, f'CPU test of the checkpoint overlay on b3g2 ({time.time() - t0:.0f} s)', r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])
        tests = 'passed' if good else 'FAILED'
        if not good:
            print(r.stdout[-1500:], r.stderr[-1500:])
    if tests == 'FAILED':
        done.unlink(missing_ok=True)                     # no mark: the supervisor's preflight stays red
    else:
        done.write_text(f'{STAMP} installed: src-b3g2 ({COMMIT}) + overlay train.py {OVERLAY_TRAIN}; tests {tests}\n', encoding='ascii')
    # 5. scheduled tasks (PowerShell, so the settings schtasks cannot set are set: no 72 h limit, repeat every 5 min, ignore a second instance)
    if a.register and ok_all:
        def ps_task(name, trig, user, disabled=False, ondemand=False, tail='run'):
            arg = f'"{sup}" --plan "{pp}" {tail}'
            script = (
                f"$a = New-ScheduledTaskAction -Execute '{PY}' -Argument '{arg}'; "
                f"$s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "
                f"$p = {user}; {trig} "
                f"Register-ScheduledTask -TaskName '{name}' -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null; "
                + (f"Disable-ScheduledTask -TaskName '{name}' | Out-Null; " if disabled else '') + f"(Get-ScheduledTask -TaskName '{name}').State")
            r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True)
            row(r.returncode == 0, f'scheduled task {name}', (r.stdout + r.stderr).strip().replace('\n', ' ')[:200])
        sysp = "New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest"
        every5 = "$t = @((New-ScheduledTaskTrigger -AtStartup), (New-ScheduledTaskTrigger -Once -At '00:00' -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)));"
        ps_task('G2FA4-SUPERVISOR', every5, sysp)
        ps_task('G2FA4-SUPERVISOR-LOGON', "$t = New-ScheduledTaskTrigger -AtLogOn;", "New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest", disabled=True)
        ps_task('G2FA4-SELFTEST', "$t = New-ScheduledTaskTrigger -Once -At '00:00';", sysp, tail='selftest')
    print('G2FA4 INSTALL DONE' if ok_all else 'G2FA4 INSTALL FINISHED WITH [FIX] LINES')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
