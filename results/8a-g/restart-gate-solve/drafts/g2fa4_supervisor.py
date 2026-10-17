#!/usr/bin/env python3
"""g2fa4_supervisor.py: runs the jobs of plan.json on BensPC one after another and keeps each alive (python 3, standard library only).

  python g2fa4_supervisor.py preflight   read-only checks (hash pins, GPU, disk, other jobs, checkpoint test); exit 0 = ready, 1 = something to fix
  python g2fa4_supervisor.py run         the loop: start / resume the current job, the planned kill-and-resume test, trace A, the accum-32 baseline,
                                         restart after any death (including a reboot: a scheduled task starts this at boot), finish, next job
  python g2fa4_supervisor.py status      print status.md
  python g2fa4_supervisor.py clear [ID]  after a STOPPED.txt has been read and the cause removed: let the loop go on (a stopped job writes STOPPED.txt, or STOPPED-<id>.txt when
                                         STOPPED.txt is another job's; `clear` moves aside the stop files of the jobs it releases, never those of a skipped job)
  python g2fa4_supervisor.py arm "<Ben's go line, with its time>"   writes ARMED.txt (its second line `jobs: <ids>` names the non-skipped jobs it arms); `run` does nothing until it
                                         exists and names the job to run (an ARMED.txt without that line, written before, arms the plan's first job only); the boot task starts `run` after every restart
  python g2fa4_supervisor.py disarm      renames ARMED.txt: the loop leaves; a running job goes on
  python g2fa4_supervisor.py halt        disarm + stop the plan's runners (their checkpoints stay): only on Ben's word
  python g2fa4_supervisor.py probe-resume --keep DIR --step 200 --upto 250   after the run: resume the kept checkpoint twice on the idle card, compare with the run's own updates
                                         (refuses a checkpoint whose sidecar accum / step is not the job's)
  python g2fa4_supervisor.py selftest    CUDA check in this very context (the boot task runs as SYSTEM): writes selftest.txt

It starts nothing by itself: `run` does nothing until ARMED.txt exists, which the Mac helper writes (`arm`) on Ben's go line; after that the boot task
restarts it after every reboot. Every long job runs with --ckpt-every N --resume, so any death costs at most N updates.

What it never does: delete anything (files it replaces are renamed .aside-<stamp>), touch a process it did not start or that is not a custom_io job
of the plan, edit code, caps, data or marks, or stop a running job except for the two registered reasons (the planned kill at update `kill_resume_at`
and a failed trace A: a non-finite loss or a GPU peak over the limit).

A job of plan.json with "skip": true is never started, resumed, evaluated or counted as pending, and nothing of it is touched (its results, its stop file, its entry of state.json);
one log line says so. A job without a "baseline" entry has no baseline run and no compare, and its end does not wait for either.
"""
import argparse, datetime, glob, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NT = os.name == 'nt'
SELF_NAME = 'g2fa4_supervisor'


# ---------------------------------------------------------------- platform bits (a test replaces these)
def now():
    return datetime.datetime.now()


def stamp():
    return now().strftime('%Y%m%d-%H%M%S')


def ts():
    return now().strftime('%Y-%m-%d %H:%M:%S')


def list_procs():
    """[(pid, command line)] of every python / llama process (all that the supervisor ever looks at)."""
    out = []
    if NT:
        ps = ("$ErrorActionPreference = 'Stop'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
              "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -or $_.Name -like 'llama*' -or $_.Name -like 'ollama*' } | "
              "ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }")
        r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        if r.returncode != 0:
            raise RuntimeError('process listing failed (rc %s): %s' % (r.returncode, r.stderr.strip()[:200]))
        for ln in r.stdout.splitlines():
            pid, _, cmd = ln.partition('|')
            if pid.strip().isdigit():
                out.append((int(pid), cmd.strip()))
    else:
        for d in glob.glob('/proc/[0-9]*'):
            try:
                comm = open(d + '/comm').read().strip()
                cmd = open(d + '/cmdline', 'rb').read().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
            except OSError:
                continue
            if cmd and comm.startswith(('python', 'llama', 'ollama')):          # like the Windows listing: only python / llama processes
                out.append((int(os.path.basename(d)), cmd))
    return out


def kill_tree(pid):
    if NT:
        return subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True, timeout=120).returncode == 0
    else:
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def gpu_mem():
    """(used MiB, total MiB) of GPU 0, or None."""
    exe = shutil.which('nvidia-smi') or next((p for p in (r'C:\Windows\System32\nvidia-smi.exe', r'C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe') if os.path.exists(p)), None)
    if not exe:
        return None
    try:
        r = subprocess.run([exe, '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=60)
        u, t = (int(x) for x in r.stdout.strip().splitlines()[0].split(','))
        return u, t
    except Exception:
        return None


def spawn_detached(cmd, cwd, env, logpath):
    log = open(logpath, 'ab')
    kw = dict(cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    if NT:
        kw['creationflags'] = 0x00000200 | 0x08000000     # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW (no visible console; DETACHED_PROCESS would give each child its own window)
    else:
        kw['start_new_session'] = True
    return subprocess.Popen(cmd, **kw)


def boot_time():
    """seconds since the epoch at which this machine booted (rounded to 10 s), or None."""
    try:
        if NT:
            import ctypes
            up = ctypes.windll.kernel32.GetTickCount64() / 1000.0
        else:
            up = float(open('/proc/uptime').read().split()[0])
        return round((time.time() - up) / 10) * 10
    except Exception:
        return None


def acquire_lock(path):
    """An OS-level lock on `path`, held for the life of the process (so it does not matter which user or context a second supervisor runs in). -> file object or None."""
    f = open(path, 'a+')
    try:
        if NT:
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


# ---------------------------------------------------------------- small helpers
def jload(p, default=None):
    try:
        return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return default


def jdump(p, obj):
    p = Path(p)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=1), encoding='utf-8')
    os.replace(tmp, p)


STOP_RE = re.compile(r'^\S+ \S+ job ([^\s:]+):')           # first line of a stop file: "<date> <time> job <id>: <why>"


def stop_owner(path):
    """the id of the job that wrote a stop file (STOPPED.txt written before there were per-job names is read the same way), or None when the file cannot be read that way."""
    try:
        first = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()[0]
    except (OSError, IndexError):
        return None
    m = STOP_RE.match(first)
    return m.group(1) if m else None


def replace_retry(src, dst):
    """os.replace with a few retries (Windows: the destination may be open for a moment, e.g. ARMED.txt read by the running loop)."""
    for i in range(10):
        try:
            return os.replace(src, dst)
        except PermissionError:
            if i == 9:
                raise
            time.sleep(0.5)


def aside(p):
    """rename a file out of the way (never delete)."""
    p = Path(p)
    if p.exists():
        q = p.with_name(p.name + '.aside-' + stamp())
        os.replace(p, q)
        return q


class Log:
    def __init__(self, path):
        self.path = Path(path)

    def __call__(self, msg):
        line = f'{ts()} {msg}'
        print(line, flush=True)
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except OSError:
            pass


# ---------------------------------------------------------------- the events file train.py writes (with --ckpt-every / --resume)
class Events:
    """Incremental reader of OUT/events.jsonl (every event line of every segment). .train = [dict(seg, step, loss, elapsed, ...)]."""

    def __init__(self, path):
        self.path, self.off = Path(path), 0
        self.reset()

    def reset(self):
        self.off, self.seg, self.train, self.resumed, self.segments = 0, 0, [], [], []
        self.last_step, self.nonfinite, self.last_elapsed = 0, False, 0.0
        self.device, self.ckpt_failed, self.ckpts = None, 0, 0
        self.warnings = []                        # every `resume_warning` event line (train.py: accum differs from the checkpoint's, other code id, CUDA streams not restored)

    def update(self):
        try:
            size = self.path.stat().st_size
        except OSError:
            return self
        if size < self.off:
            self.reset()
        with open(self.path, 'rb') as f:
            f.seek(self.off)
            data = f.read()
        end = data.rfind(b'\n') + 1               # only complete lines
        for ln in data[:end].decode('utf-8', 'replace').splitlines():
            try:
                e = json.loads(ln)
            except ValueError:
                continue
            ev = e.get('event')
            if ev == 'segment':
                self.seg += 1
                self.segments.append(e)
            elif ev == 'resumed':
                self.resumed.append((self.seg, e.get('step')))
            elif ev == 'start':
                self.device = e.get('device')
            elif ev == 'resume_warning':
                self.warnings.append(e)
            elif ev == 'ckpt_failed':
                self.ckpt_failed += 1
            elif ev == 'ckpt':
                self.ckpts += 1
            elif ev == 'train':
                loss = e.get('loss')
                if not isinstance(loss, (int, float)) or not math.isfinite(loss):
                    self.nonfinite = True
                self.train.append(dict(e, seg=self.seg))
                self.last_step = e.get('step', self.last_step)
                self.last_elapsed = e.get('elapsed', self.last_elapsed)
        self.off += end
        return self

    def merged(self):
        """step -> loss, a later segment overrides an earlier one (the path the run actually took)."""
        d = {}
        for e in self.train:
            d[e['step']] = e['loss']
        return d


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


# ---------------------------------------------------------------- the two registered checks (pure functions; thresholds come from plan.json)
def trace_a(ev, rules, max_used_mib):
    """Trace A (big-run, fixed before any PC run): no NaN/Inf; GPU peak under the limit; the loss falls; the resume matches."""
    up, n = rules['upto'], rules['first_n']
    m = ev.merged()
    r = dict(upto=up, rules=rules, why_fail=[], notes=[], max_used_mib=max_used_mib, soft_misses=[])
    soft = set(rules.get('soft', ()))          # items listed here ('peak', 'resume_max_abs', and with --soft-trace-a-mean also 'resume_mean_abs') are RECORDED, not gated: a miss goes to soft_misses and does not stop the run (the reading of the result is gated after the run instead)

    def miss(key, msg):
        (r['soft_misses'] if key in soft else r['why_fail']).append(msg)
    have = all(s in m for s in range(1, up + 1))
    r['complete'] = have
    r['finite'] = not ev.nonfinite
    if not r['finite']:
        r['why_fail'].append('a non-finite loss was logged')
    if max_used_mib is None:
        r['notes'].append('GPU memory could not be read (nvidia-smi): peak not checked')
    elif max_used_mib > rules['peak_limit_mib']:
        miss('peak', f'GPU memory in use peaked at {max_used_mib} MiB, over the {rules["peak_limit_mib"]} MiB limit')
    if have:
        first, last = mean(m[s] for s in range(1, n + 1)), mean(m[s] for s in range(up - rules['last_n'] + 1, up + 1))
        r.update(mean_first=first, mean_last=last, falls=bool(last < first))
        if not last < first:
            r['why_fail'].append(f'loss did not fall (mean of updates 1..{n} {first:.4f}, mean of the last {rules["last_n"]} {last:.4f})')
    else:
        r['why_fail'].append('the trace has gaps before update %d' % up)
    # the resume: the earlier segment's updates after the checkpoint, redone by the resumed segment (the first resume that has any such updates)
    r['resume'] = None
    for seg2, rstep in ev.resumed:
        s1 = {}
        for e in ev.train:
            if e['seg'] < seg2 and e['step'] > rstep:          # the latest earlier line for each step (a segment that died before its first update has none)
                s1[e['step']] = e['loss']
        s2 = {e['step']: e['loss'] for e in ev.train if e['seg'] == seg2}
        common = sorted(set(s1) & set(s2))
        if common:
            d = [abs(s1[s] - s2[s]) for s in common]
            r['resume'] = dict(resumed_step=rstep, n_redone=len(common), first_diff=d[0], mean_abs=mean(d), max_abs=max(d))
            if d[0] > rules['resume_first_diff']:
                r['why_fail'].append(f'first redone update differs by {d[0]:.4f} (limit {rules["resume_first_diff"]})')
            if mean(d) > rules['resume_mean_abs']:
                miss('resume_mean_abs', f'redone updates differ by {mean(d):.4f} on average (limit {rules["resume_mean_abs"]})')       # hard unless rules.soft lists 'resume_mean_abs' (installer: --soft-trace-a-mean; never a default)
            if max(d) > rules['resume_max_abs']:
                miss('resume_max_abs', f'redone updates differ by up to {max(d):.4f} (limit {rules["resume_max_abs"]})')
            break
    if r['resume'] is None:
        r['why_fail'].append('no resume with redone updates to compare (the planned kill-and-resume did not run, or the killed segment had no update after its checkpoint)')
    r['verdict'] = 'PASS' if not r['why_fail'] else 'FAIL'
    return r


def compare(ea, eb, rules):
    """Accum 4 vs accum 32 over the first `upto` updates (big-run: PASS within +/-0.03 on the difference of means and last-50 at most 0.05 above;
    FAIL beyond 0.06 / 0.10 or a NaN; in between UNCLEAR, read as GO). Also reports the earlier 0.02 / 0.01 numbers beside it, not as the gate."""
    up, k = rules['upto'], rules['last_n']
    a, b = ea.merged(), eb.merged()
    r = dict(upto=up, rules=rules)
    if ea.nonfinite or eb.nonfinite:
        r.update(verdict='FAIL', why='a non-finite loss in the %s trace' % ('accum-4' if ea.nonfinite else 'baseline'))
        return r
    miss = [s for s in range(1, up + 1) if s not in a or s not in b]
    if miss:
        r.update(verdict='INCOMPLETE', why='missing updates (first %s)' % miss[:5])
        return r
    d_mean = mean(a[s] for s in range(1, up + 1)) - mean(b[s] for s in range(1, up + 1))
    d_last = mean(a[s] for s in range(up - k + 1, up + 1)) - mean(b[s] for s in range(up - k + 1, up + 1))
    r.update(diff_of_means=d_mean, last_n_diff=d_last)
    f0 = rules['report_from']
    r['report_beside'] = dict(from_update=f0, mean_abs_diff=mean(abs(a[s] - b[s]) for s in range(f0, up + 1)), diff_of_means=mean(a[s] for s in range(f0, up + 1)) - mean(b[s] for s in range(f0, up + 1)),
                              earlier_limits='0.02 and 0.01 (assumed identical loop-length draws; not the gate)')
    p1, p2 = abs(d_mean) <= rules['diff_mean_pass'], d_last <= rules['last_n_pass']
    f1, f2 = abs(d_mean) > rules['diff_mean_fail'], d_last > rules['last_n_fail']
    r['verdict'] = 'FAIL' if (f1 or f2) else 'PASS' if (p1 and p2) else 'UNCLEAR'
    r['read_as'] = 'GO' if r['verdict'] in ('PASS', 'UNCLEAR') else 'NO-GO: fall back to accum 8, then 32 (big-run)'
    return r


def lag1_autocorr(xs):
    """lag-1 autocorrelation of a series (sum of (x_t - m)(x_t+1 - m) over sum of (x_t - m)^2); None if the series has under 3 points or no variance."""
    xs = list(xs)
    if len(xs) < 3:
        return None
    m = sum(xs) / len(xs)
    den = sum((x - m) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((a - m) * (b - m) for a, b in zip(xs, xs[1:])) / den


def resume_probe_verdict(C, R1, R2):
    """The registered resume-noise rule (TRACE-A-READING item 2): C = the run's continuous updates, R1 / R2 = two resumes of the same checkpoint (equal-length lists).
    n = largest |R1 - R2|, d = largest |R_i - C|; PASS if d <= max(0.10, 3n), FAIL otherwise.
    `verdict`, n, d, limit and the mean_abs_* / diff_* keys are exactly the registered rule's. Added beside it (recorded, NOT the gate; the mean form is pre-registered in the re-reading
    of the probe, rejudge_probe.py): first_r1_c / first_r2_c / first_r1_r2 = the differences at the first probe update (exactly 0 when the restore is complete: the forward pass of the first update is deterministic),
    Dbar = mean(mean_abs_r1_c, mean_abs_r2_c), Nbar = mean_abs_r1_r2, ratio = Dbar / Nbar (inf if Nbar == 0 and Dbar > 0; 1.0 if both are 0),
    mean_form_limit = max(0.02, 2 Nbar), mean_form_verdict = PASS if Dbar <= mean_form_limit, lag1_autocorr of the signed series R1 - R2 (None if it has no variance)."""
    assert len(C) == len(R1) == len(R2) and C, 'the three loss lists must have the same non-zero length'
    d12, d1, d2 = ([abs(x - y) for x, y in zip(a, b)] for a, b in ((R1, R2), (R1, C), (R2, C)))
    n, d = max(d12), max(d1 + d2)
    lim = max(0.10, 3 * n)
    out = dict(n=n, d=d, limit=lim, verdict='PASS' if d <= lim else 'FAIL', mean_abs_r1_r2=mean(d12), mean_abs_r1_c=mean(d1), mean_abs_r2_c=mean(d2),
               diff_r1_r2=d12, diff_r1_c=d1, diff_r2_c=d2)
    dbar, nbar = mean([out['mean_abs_r1_c'], out['mean_abs_r2_c']]), out['mean_abs_r1_r2']
    ratio = (float('inf') if dbar > 0 else 1.0) if nbar == 0 else dbar / nbar
    mlim = max(0.02, 2 * nbar)
    out.update(first_r1_c=d1[0], first_r2_c=d2[0], first_r1_r2=d12[0], Dbar=dbar, Nbar=nbar, ratio=ratio, mean_form_limit=mlim,
               mean_form_verdict='PASS' if dbar <= mlim else 'FAIL', lag1_autocorr=lag1_autocorr([x - y for x, y in zip(R1, R2)]))
    return out


# ---------------------------------------------------------------- the supervisor
class Sup:
    def __init__(self, plan_path):
        self.plan_path = Path(plan_path)
        self.plan = jload(self.plan_path)
        if not self.plan:
            sys.exit(f'cannot read {self.plan_path}')
        self.sd = Path(self.plan.get('state_dir') or HERE)
        self.sd.mkdir(parents=True, exist_ok=True)
        self.log = Log(self.sd / 'supervisor.log')
        self.state_path = self.sd / 'state.json'
        self.st = jload(self.state_path, {'jobs': {}})
        self.ev = {}
        self.bev = {}
        self._noted = set()

    # ---- jobs that are skipped (plan.json "skip": true): not started, resumed, evaluated or counted; nothing of theirs is read from state.json or written to it
    def active_jobs(self):
        return [j for j in self.plan['jobs'] if not j.get('skip')]

    def skipped_ids(self):
        return {j['id'] for j in self.plan['jobs'] if j.get('skip')}

    def note_skipped(self):
        """one log line per skipped job per supervisor process. The shared status.md describes the job that runs, so a skipped job's last status.md is first copied to status-<id>.md (once, never over a file)."""
        for j in self.plan['jobs']:
            if j.get('skip') and j['id'] not in self._noted:
                self._noted.add(j['id'])
                self.log(f'job {j["id"]} is skipped (plan.json skip: {j.get("skip_reason") or "no reason given"}): never started, resumed or evaluated; its files and state are not touched')
                snap, cur = self.sd / f'status-{j["id"]}.md', self.sd / 'status.md'
                try:
                    if cur.exists() and not snap.exists() and f'job {j["id"]} (' in cur.read_text(encoding='utf-8', errors='replace'):
                        shutil.copy2(cur, snap)
                        self.log(f'the last status.md of {j["id"]} is kept as {snap.name}')
                except OSError as e:
                    self.log(f'status of the skipped job {j["id"]} could not be copied: {e}')

    # ---- stop files: STOPPED.txt (the old name) or STOPPED-<id>.txt; each names its job in its first line
    def stop_files(self):
        """[(path, id of the job that wrote it or None)]"""
        return [(p, stop_owner(p)) for p in sorted(self.sd.glob('STOPPED*.txt'))]

    def blocking_stops(self):
        """the stop files that hold the loop: all except those of skipped jobs (a file whose owner cannot be read blocks, as STOPPED.txt always did)."""
        sk = self.skipped_ids()
        return [p for p, o in self.stop_files() if o not in sk]

    def stop_path(self, job):
        p = self.sd / 'STOPPED.txt'
        if not p.exists() or stop_owner(p) == job['id']:
            return p
        return self.sd / f'STOPPED-{job["id"]}.txt'              # STOPPED.txt is another job's record: never overwritten

    def attn_path(self, kind, job):
        """ATTENTION-<kind>.txt is g2fa4's name (as before there was a second job); every other job writes ATTENTION-<kind>-<id>.txt, so one job's note never hides another's."""
        return self.sd / (f'ATTENTION-{kind}.txt' if job['id'] == 'g2fa4' else f'ATTENTION-{kind}-{job["id"]}.txt')

    # ---- ARMED.txt: line 1 "<time> armed: <Ben's words>", line 2 "jobs: <ids>" (the non-skipped jobs of the plan at that time)
    def armed_ids(self):
        """None = no ARMED.txt; 'first' = a file without a jobs line (written before there were any); else the list of ids."""
        p = self.sd / 'ARMED.txt'
        for i in range(5):
            try:
                lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
                break
            except FileNotFoundError:
                self._armed_seen = None
                return None
            except OSError:                                          # Windows: the file is open for a moment (the swap of `arm`, a scanner); try again, then let the last decision stand
                if i == 4:
                    return getattr(self, '_armed_seen', None)
                time.sleep(0.2)
        ids = None
        if len(lines) > 1 and (lines[1].startswith('jobs: ') or lines[1] == 'jobs:'):         # line 2 only: a "jobs:" line inside the words of line 1 or later never arms
            ids = lines[1][len('jobs:'):].split()
        self._armed_seen = 'first' if ids is None else ids
        return self._armed_seen

    def armed_text(self):
        ids = self.armed_ids()
        return 'nothing (no ARMED.txt)' if ids is None else f'the first job of the plan, {self.plan["jobs"][0]["id"]}, only (an old file without a jobs line)' if ids == 'first' else f'jobs {ids}'

    def armed_for(self, job):
        ids = self.armed_ids()
        if ids is None:
            return False
        if ids == 'first':
            return job['id'] == self.plan['jobs'][0]['id']       # an old file armed the plan as it was, i.e. its first job; a job added later waits for its own `arm`
        return job['id'] in ids

    # ---- paths of a job
    def res(self, queue):
        return Path(self.plan['work']) / 'results' / queue

    def out_dir(self, job, base=False):
        q, j = (job['baseline']['queue'], job['baseline']['job']) if base else (job['queue'], job['job'])
        return self.res(q) / j

    def arm_dir(self, job, base=False):
        return self.out_dir(job, base) / job['arm']

    def events(self, job, base=False):
        d = self.bev if base else self.ev
        key = job['id']
        if key not in d:
            d[key] = Events(self.arm_dir(job, base) / 'events.jsonl')
        return d[key].update()

    def js(self, job):
        return self.st['jobs'].setdefault(job['id'], dict(status='pending', restarts=[], no_progress=0, kill_done=False, max_used_mib=None,
                                                          base=dict(status='waiting' if job.get('baseline') else 'none')))

    def save(self):
        jdump(self.state_path, self.st)

    # ---- processes (one listing per cycle: the PowerShell query takes a second or two on Windows)
    def procs(self, fresh=False):
        if fresh or not hasattr(self, '_p'):
            p = list_procs()
            if os.getpid() not in [x for x, _ in p]:           # a listing that lacks this very process is broken (Windows is still starting up): never act on it
                raise RuntimeError('the process listing does not contain this process: not acting on it')
            self._p = p
        return self._p

    def find(self, match, queue):
        return [pid for pid, cmd in self.procs() if match in cmd and (queue + '.txt') in cmd and SELF_NAME not in cmd]

    def strays(self, jobname):
        return [pid for pid, cmd in self.procs(True) if jobname in cmd and ('custom_io' in cmd or 'fake_runner' in cmd) and SELF_NAME not in cmd]

    def runner_cmd(self, job, base=False):
        q = job['baseline']['queue'] if base else job['queue']
        qpath = Path(job['src']) / 'custom_io' / 'queue_local' / (q + '.txt')
        rc = (job['baseline'] if base else job).get('runner_cmd')
        if rc:                                       # a test's stand-in for local_runner
            return [c.format(python=self.plan['python'], work=self.plan['work'], queue=q, qpath=qpath, busy=self.plan['busy']) for c in rc]
        return [self.plan['python'], '-m', 'custom_io.local_runner', 'run', '--work', self.plan['work'], '--queue', str(qpath), '--device', 'cuda', '--par', '1',
                '--busy', self.plan['busy']]

    def start(self, job, base=False):
        q = job['baseline']['queue'] if base else job['queue']
        cmd = self.runner_cmd(job, base)
        env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
        p = spawn_detached(cmd, job['src'], env, self.sd / f'runner-{q}.log')
        self.log(f'STARTED runner {q} pid {p.pid}: {" ".join(cmd)}')
        time.sleep(0.5)
        self.procs(True)
        return p.pid

    def kill_job(self, job, base=False, why=''):
        q = job['baseline']['queue'] if base else job['queue']
        jn = job['baseline']['job'] if base else job['job']
        pids = self.find(job.get('runner_match', 'local_runner'), q)
        gone = False
        for attempt in range(3):
            for pid in pids:
                kill_tree(pid)
            time.sleep(2)
            for pid in self.strays(jn):
                kill_tree(pid)
            time.sleep(1)
            self.procs(True)
            pids = self.find(job.get('runner_match', 'local_runner'), q) + self.strays(jn)
            if not pids:
                gone = True
                break
        self.log(f'{"KILLED" if gone else "KILL FAILED (processes still alive: %s)" % pids} {q}: {why}')
        if gone:
            self.js(job)['verified_dead_at' if not base else 'base_dead_at'] = time.time()
            self.after_kill(job, base)
        return gone

    def after_kill(self, job, base=False):
        """clean what a killed run leaves: its GPU-BUSY lines and stale pool locks (renamed, never deleted), a job-level arm_failed RESULT.json (renamed)."""
        q = job['baseline']['queue'] if base else job['queue']
        busy = Path(self.plan['busy'])
        try:
            if busy.exists():
                lines = busy.read_text(encoding='utf-8', errors='replace').splitlines()
                keep = [ln for ln in lines if not re.match(r'^\S+ ' + re.escape(q) + r'/', ln)]
                if len(keep) != len(lines):
                    if keep:
                        busy.write_text('\n'.join(keep) + '\n', encoding='utf-8')
                    else:
                        aside(busy)
                    self.log(f'GPU-BUSY: removed {len(lines) - len(keep)} line(s) of {q}')
        except OSError as e:
            self.log(f'GPU-BUSY cleanup failed: {e}')
        alive = [pid for pid, cmd in self.procs(True) if ('custom_io' in cmd or 'fake_runner' in cmd) and SELF_NAME not in cmd]
        if not alive:
            for lk in glob.glob(str(Path(self.plan['work']) / 'g8a' / 'pools' / '*.lock')):
                self.log(f'stale pool lock moved aside: {aside(lk)}')
        rj = self.out_dir(job, base) / 'RESULT.json'
        r = jload(rj)
        if r and r.get('status') != 'ok':
            self.log(f'job-level RESULT.json ({r.get("status")}) moved aside: {aside(rj)}')

    def ev_age(self, job, base=False):
        """seconds since events.jsonl was last written (a huge number if it does not exist)."""
        try:
            return time.time() - os.path.getmtime(self.arm_dir(job, base) / 'events.jsonl')
        except OSError:
            return 1e9

    # ---- state of a job
    def arm_ok(self, job, base=False):
        r = jload(self.arm_dir(job, base) / 'RESULT.json')
        j = jload(self.out_dir(job, base) / 'RESULT.json')
        return bool(r and r.get('status') == 'ok' and j and j.get('status') == 'ok'), r

    def fatal_text(self, job):
        try:
            tail = (self.arm_dir(job) / 'stdout.txt').read_text(encoding='utf-8', errors='replace')[-6000:]
        except OSError:
            return None
        for pat in ('--resume refused', 'rows touch the global caps', 'REFUSED'):
            if pat in tail:
                return pat
        return None

    def stop(self, job, why):
        js = self.js(job)
        js['status'] = 'stopped'
        js['why'] = why
        sp = self.stop_path(job)
        sp.write_text(f'{ts()} job {job["id"]}: {why}\nread status.md and supervisor.log; after the cause is removed: python {SELF_NAME}.py clear {job["id"]}\n', encoding='utf-8')
        self.log(f'STOPPED job {job["id"]}: {why}' + (f' ({sp.name})' if sp.name != 'STOPPED.txt' else ''))
        self.save()

    def write_status(self, job, runner_pids):
        js = self.js(job)
        ev = self.events(job)
        L = [f'# G2f-a4 supervisor status, {ts()}', '',
             f'job {job["id"]} ({job["title"]}): **{js["status"]}**' + (f' ({js.get("why")})' if js.get('why') else ''),
             f'runner pids: {runner_pids or "none"}; update {ev.last_step} of {job["steps"]}; segments {ev.seg}; resumes at {[s for _, s in ev.resumed]}; restarts after the first start {sum(1 for r in js["restarts"] if not r.get("first"))}']
        tr = [e for e in ev.train if e['seg'] == ev.seg]
        if len(tr) > 20:
            a, b = tr[-20], tr[-1]
            sp = (b['elapsed'] - a['elapsed']) / max(1, b['step'] - a['step'])
            L.append(f'speed (last 20 lines): {sp:.2f} s/update; left about {sp * (job["steps"] - ev.last_step) / 3600:.1f} h at that speed')
        L.append(f'max GPU memory in use seen: {js["max_used_mib"]} MiB; planned kill-and-resume: {js["kill_done"]}')
        if js.get('traceA'):
            L.append(f'trace A: **{js["traceA"]["verdict"]}** {js["traceA"]["why_fail"] or ""} (TRACE-A-{job["id"]}.md)')
        if job.get('baseline'):
            L.append(f'baseline: {js["base"]["status"]}' + (f'; compare: **{js["compare"]["verdict"]}** ({js["compare"].get("read_as")})' if js.get('compare') else ''))
        else:
            L.append('baseline: none in this job')
        try:
            L += ['', 'last log lines:'] + ['    ' + x for x in (self.sd / 'supervisor.log').read_text(encoding='utf-8').splitlines()[-6:]]
        except OSError:
            pass
        (self.sd / 'status.md').write_text('\n'.join(L) + '\n', encoding='utf-8')

    # ---- one pass of the loop
    def cycle(self):
        """-> seconds to sleep, or None when everything is finished / stopped."""
        self.plan = jload(self.plan_path, self.plan)          # re-read: jobs can be appended while it runs
        self.note_skipped()
        if not (self.sd / 'ARMED.txt').exists():
            self.log('not armed (ARMED.txt missing): the loop leaves')
            return None
        if self.blocking_stops():                             # (a stop file of a skipped job does not count)
            return None
        self.procs(True)
        act = self.active_jobs()                              # skipped jobs are never looked at again: no state entry is made for them, none is read
        job = next((j for j in act if self.js(j)['status'] not in ('done',)), None)
        late = [j for j in act if j is not job and self.js(j)['base']['status'] == 'running']     # a finished job's baseline still running
        for j in late:
            self.baseline(j, self.js(j), gpu_mem())
        if late:
            self.save()
        if job is None and late:
            return self.plan.get('poll_s', 15)
        if job is None:
            if not (self.sd / 'ALL-DONE.txt').exists():
                sk = sorted(self.skipped_ids())
                (self.sd / 'ALL-DONE.txt').write_text(f'{ts()} every job of the plan is done' + (f' (skipped: {", ".join(sk)})' if sk else '') + '\n', encoding='utf-8')
                self.log('ALL DONE')
            return None
        if not self.armed_for(job):
            self.log(f'ARMED.txt does not arm job {job["id"]} (it arms {self.armed_text()}): the loop leaves; `arm` on Ben\'s go line arms it')
            return None
        js = self.js(job)
        poll = self.plan.get('poll_s', 15)
        pids = self.find(job.get('runner_match', 'local_runner'), job['queue'])
        ev = self.events(job)
        g = gpu_mem()
        if pids and g:
            js['max_used_mib'] = max(js['max_used_mib'] or 0, g[0])
        if js['status'] == 'pending':
            js['status'] = 'running'
        if pids:
            self.running(job, js, ev, pids)
        else:
            done, res = self.arm_ok(job)
            if done:
                self.finish(job, js, res)
            else:
                self.relaunch(job, js, ev, g)
        self.baseline(job, js, g)
        self.write_status(job, pids)
        self.save()
        return poll

    def running(self, job, js, ev, pids):
        up = job['trace_a']['upto'] if job.get('trace_a') else None
        now_t = time.time()
        # progress clock for the stall watchdog (a hung process, a stale lock, a full disk: the runner is alive but nothing moves)
        if ev.last_step != js.get('wd_step'):
            js['wd_step'], js['wd_t'] = ev.last_step, now_t
        stall = now_t - max(js.get('wd_t', now_t), js.get('launched_t', 0))
        if ev.last_step < job['steps'] and stall > self.plan.get('stall_warn_s', 1200) and not js.get('stall_warned'):
            js['stall_warned'] = True
            self.attn_path('stall', job).write_text(f'{ts()} {job["id"]}: no new update for {stall / 60:.0f} min at update {ev.last_step}; the runner is alive\n', encoding='utf-8')
            self.log(f'STALL: no new update for {stall / 60:.0f} min at update {ev.last_step}')
        if ev.last_step < job['steps'] and stall > self.plan.get('stall_kill_s', 3600):
            js['stall_warned'] = False
            js['wd_t'] = now_t
            js['restarts'].append(dict(at=ts(), step=ev.last_step, planned=False, stall=True))
            self.kill_job(job, why=f'no new update for {stall / 60:.0f} min: restart from the newest checkpoint')
            return
        # the run must be on the GPU: a driver swap can leave torch without CUDA, and train.py would quietly go on at CPU speed
        want_dev = self.plan.get('device', 'cuda')                      # 'cpu' only in the test of the supervisor against the real train.py
        if ev.device and not str(ev.device).startswith(want_dev):
            self.kill_job(job, why=f'train.py started on "{ev.device}", not {want_dev}')
            return self.stop(job, f'train.py started on the device "{ev.device}" instead of {want_dev} (driver / torch CUDA problem after an update?); it was stopped, nothing restarts until this is fixed')
        if ev.ckpt_failed >= 3 and not self.attn_path('ckpt', job).exists():
            self.attn_path('ckpt', job).write_text(f'{ts()} {job["id"]}: {ev.ckpt_failed} checkpoint writes failed (disk full? file locked?); a restart would lose more than 100 updates\n', encoding='utf-8')
            self.log(f'ATTENTION: {ev.ckpt_failed} checkpoint writes failed')
        # the planned kill-and-resume test (R4): once, in the middle of a checkpoint interval
        if job.get('kill_resume_at') and not js['kill_done'] and not ev.resumed and ev.last_step >= job['kill_resume_at']:
            ck = sorted(glob.glob(str(self.arm_dir(job) / 'ckpt' / 'step-*.pt')))
            if not ck:
                if self.kill_job(job, why=f'no checkpoint file at update {ev.last_step}'):
                    self.stop(job, f'no checkpoint was written by update {ev.last_step} (--ckpt-every 100): the checkpoint path does not work on this card; stopped rather than run 15 h unprotected')
                return
            msg = f'killed at update {ev.last_step}, newest checkpoint {os.path.basename(ck[-1])}'
            if self.kill_job(job, why=f'planned kill-and-resume test at update {ev.last_step} (Ben\'s go line; big-run R4)'):
                js['kill_done'] = msg
                js['restarts'].append(dict(at=ts(), step=ev.last_step, planned=True))
            return                                           # not killed: tried again next cycle
        # trace A once the resumed segment has reached update `upto`
        if up and not js.get('traceA') and ev.last_step >= up and (ev.resumed and ev.seg > 1):
            r = trace_a(ev, job['trace_a'], js['max_used_mib'])
            r['gpu_used_mib_at_launch'] = js.get('gpu_at_launch')
            js['traceA'] = dict(verdict=r['verdict'], why_fail=r['why_fail'], soft_misses=r['soft_misses'])
            jdump(self.sd / f'TRACE-A-{job["id"]}.json', r)
            (self.sd / f'TRACE-A-{job["id"]}.md').write_text(self.md_trace_a(job, r), encoding='utf-8')
            self.log(f'TRACE A: {r["verdict"]} {r["why_fail"]}' + (f' (recorded, not gated: {r["soft_misses"]})' if r['soft_misses'] else ''))
            if r['verdict'] == 'FAIL':
                self.kill_job(job, why='trace A failed')
                self.stop(job, 'trace A FAILED: ' + '; '.join(r['why_fail']) + (' (registered fallback: accum 8, then 32; a new run name each)' if job.get('accum') == 4 else ''))      # (the fallback text is the accum-4 job's)
        elif up and not js.get('traceA') and ev.last_step >= up + 100:
            self.kill_job(job, why='trace A could not be evaluated')
            self.stop(job, f'update {ev.last_step} reached with no trace A verdict (no resume happened): stopped so the run is not left ungated')

    def finish(self, job, js, res):
        js['status'] = 'done'
        js['result'] = {k: res.get(k) for k in ('steps', 'steps_per_s', 'train_s', 'peak_mem_mib', 'peak_reserved_mib', 'n_params', 'resumed_from')}
        tail = (f'baseline compare: {json.dumps(js.get("compare"))}\nread it only if the compare verdict is PASS or UNCLEAR (big-run).\n' if job.get('baseline')
                else 'no baseline in this job (no compare was made here).\n')
        (self.sd / f'DONE-{job["id"]}.txt').write_text(f'{ts()} {job["id"]} finished: {json.dumps(js["result"])}\nRESULT.json: {self.arm_dir(job) / "RESULT.json"}\n' + tail, encoding='utf-8')
        self.log(f'DONE {job["id"]}: {js["result"]}')
        if js['base']['status'] == 'waiting':          # trace A never passed (or no room): there is nothing to compare any more
            js['base']['status'] = 'abandoned'

    def relaunch(self, job, js, ev, g):
        if (Path(self.plan['work']) / 'STOP').exists():
            self.log('WORK\\STOP exists: nothing is (re)started')
            return
        ar = jload(self.arm_dir(job) / 'RESULT.json')
        if ar and ar.get('status') not in (None, 'ok'):
            return self.stop(job, f'train.py finished with status "{ar.get("status")}" (RESULT.json): not restarted')
        bad = self.fatal_text(job)
        if bad:
            return self.stop(job, f'train.py says "{bad}": a restart would refuse the same way')
        # nothing may be started on a guess: the GPU reading is mandatory, and the GPU must be free (Ben's other programs, the Qwen server, are never touched)
        need = job.get('need_free_mib', self.plan['gpu']['need_free_mib'])
        if not g:
            self.log('no GPU reading (nvidia-smi failed): nothing is started')
            return
        if g[1] - g[0] < need:
            who = [f'pid {p} {c[:60]}' for p, c in self.procs() if 'llama' in c or 'ollama' in c]
            if not js.get('waiting_gpu') or time.time() - js['waiting_gpu'] > 600:
                js['waiting_gpu'] = time.time()
                self.log(f'WAITING for the GPU: {g[1] - g[0]} MiB free, need {need}; other GPU users seen: {who or "unknown"}')
            return
        js['waiting_gpu'] = None
        # a runner this supervisor cannot see (another context) would still be writing events.jsonl: wait for 3 quiet minutes unless this supervisor killed it
        if self.ev_age(job) < self.plan.get('quiet_s', 180) and js.get('verified_dead_at', 0) < time.time() - self.ev_age(job):
            if not js.get('waiting_quiet'):
                js['waiting_quiet'] = True
                self.log(f'events.jsonl was written {self.ev_age(job):.0f} s ago by a runner that is not listed: waiting until it is quiet for {self.plan.get("quiet_s", 180)} s')
            return
        js['waiting_quiet'] = False
        # a death across a reboot is not a crash; a death with no new update since the last start is
        last, bt = js.get('step_at_launch'), boot_time()
        rebooted = bt is not None and js.get('boot_at_launch') is not None and abs(bt - js['boot_at_launch']) > 120
        if last is not None and not rebooted:
            js['no_progress'] = js['no_progress'] + 1 if ev.last_step <= last else 0
        elif rebooted:
            js['no_progress'] = 0
        if js['no_progress'] >= self.plan.get('max_no_progress', 3):
            return self.stop(job, f'{js["no_progress"]} restarts in a row with no new update (stuck at {ev.last_step})')
        # the baseline shares the card: if the main run died, the baseline goes first (it could be what filled the card), then the main run restarts alone
        if js['base']['status'] == 'running':
            self.kill_job(job, base=True, why='the main run died while the baseline shared the card')
            js['base']['status'] = 'abandoned'
            self.attn_path('baseline', job).write_text(f'{ts()} the main run died at update {ev.last_step} while the accum-32 baseline ran; the baseline was stopped and is NOT redone automatically\n', encoding='utf-8')
        self.after_kill(job)
        if not (self.sd / 'ARMED.txt').exists():                    # halt / disarm while this cycle was running
            return
        js['step_at_launch'], js['boot_at_launch'], js['launched_t'], js['gpu_at_launch'] = ev.last_step, bt, time.time(), g[0]
        if not js['restarts'] or js['restarts'][-1].get('launched'):
            js['restarts'].append(dict(at=ts(), step=ev.last_step, planned=False, first=not js['restarts'], rebooted=bool(rebooted)))
        js['restarts'][-1].update(launched=ts())
        self.start(job)

    # ---- the accum-32 baseline (alongside, once trace A passed and the GPU has room)
    def baseline(self, job, js, g):
        b, base = js['base'], job.get('baseline')
        if not base or js['status'] == 'stopped' or b['status'] in ('done', 'abandoned', 'failed'):
            return
        if b['status'] == 'waiting':
            if js.get('traceA', {}).get('verdict') == 'PASS' and g and g[1] - g[0] >= base['need_free_mib'] and not (Path(self.plan['work']) / 'STOP').exists() \
                    and (self.sd / 'ARMED.txt').exists():
                b['status'] = 'running'
                b['started'] = ts()
                self.start(job, base=True)
            return
        pids = self.find(job.get('runner_match', 'local_runner'), base['queue'])
        ev = self.events(job, base=True)
        up = base['upto']
        if ev.last_step >= up or ev.nonfinite:
            if pids:
                self.kill_job(job, base=True, why=f'baseline reached update {ev.last_step}')
            r = compare(self.events(job), ev, job['compare'])
            js['compare'] = dict(verdict=r['verdict'], read_as=r.get('read_as'), why=r.get('why'))
            jdump(self.sd / f'COMPARE-{job["id"]}.json', r)
            (self.sd / f'COMPARE-{job["id"]}.md').write_text(self.md_compare(job, r), encoding='utf-8')
            b['status'] = 'done'
            self.log(f'COMPARE accum {job["accum"]} vs 32: {r["verdict"]} ({r.get("read_as")}) diff of means {r.get("diff_of_means")} last-n {r.get("last_n_diff")}')
            if r['verdict'] in ('FAIL', 'INCOMPLETE'):
                self.attn_path('compare', job).write_text(f'{ts()} {job["id"]} baseline compare {r["verdict"]}: {json.dumps(r)}\nthe main run keeps going until someone decides (big-run: fall back to accum 8, then 32)\n', encoding='utf-8')
        elif not pids:
            if (Path(self.plan['work']) / 'STOP').exists():
                return
            if not g or g[1] - g[0] < base['need_free_mib']:
                return
            if self.ev_age(job, base=True) < self.plan.get('quiet_s', 180) and self.js(job).get('base_dead_at', 0) < time.time() - self.ev_age(job, base=True):
                return
            b['restarts'] = b.get('restarts', 0) + 1
            if b['restarts'] > 4:
                b['status'] = 'failed'
                self.attn_path('baseline', job).write_text(f'{ts()} the accum-32 baseline died {b["restarts"]} times before update {up}; the main job is not affected\n', encoding='utf-8')
                self.log('baseline FAILED (died too often); the main job goes on')
                return
            self.after_kill(job, base=True)
            self.log('baseline runner is gone before update %d: restarting it (resume)' % up)
            self.start(job, base=True)

    # ---- the resume-noise probe (after the run: two resumes of the kept checkpoint on the idle card)
    def probe_job(self, job, tag):
        """the plan job under probe names: the first '-' of queue and job name gets the tag (8aB3G2A4-pc -> 8aB3G2A4n1-pc); never has a baseline."""
        nm = lambda x: x.replace('-', tag + '-', 1) if '-' in x else x + tag
        rc = job.get('runner_cmd')
        return dict(job, id=job['id'] + tag, queue=nm(job['queue']), job=nm(job['job']), baseline=None,
                    runner_cmd=[c.replace(job['job'], nm(job['job'])) for c in rc] if rc else None)

    def probe_run(self, job, pj, keep, step, upto):
        """one probe: queue copy with only the job name changed, a copy of the kept checkpoint, run until update `upto`, kill. -> (Events of the probe, why-not or None)."""
        qd = Path(job['src']) / 'custom_io' / 'queue_local'
        lines = (qd / (job['queue'] + '.txt')).read_text(encoding='utf-8').splitlines(True)
        new = [ln.replace(job['job'], pj['job']) if ln.startswith('g8a:') else ln for ln in lines]
        if new == lines:
            return None, f'job name {job["job"]} not found on a g8a: line of {job["queue"]}.txt'
        aside(qd / (pj['queue'] + '.txt'))
        (qd / (pj['queue'] + '.txt')).write_text(''.join(new), encoding='utf-8')
        aside(self.out_dir(pj))                                              # an earlier probe's folder moves aside
        ck = self.arm_dir(pj) / 'ckpt'
        ck.mkdir(parents=True)
        for ext in ('pt', 'json'):
            shutil.copy2(keep / f'step-{step}.{ext}', ck / f'step-{step}.{ext}')
        self.start(pj)
        ev, t0, why = Events(self.arm_dir(pj) / 'events.jsonl'), time.time(), None
        while True:
            time.sleep(self.plan.get('poll_s', 15))
            ev.update()
            if ev.last_step >= upto or ev.nonfinite:
                break
            if not self.find(pj.get('runner_match', 'local_runner'), pj['queue']):
                why = f'the probe runner died at update {ev.last_step}'
                break
            if time.time() - t0 > self.plan.get('probe_limit_s', 1800):
                why = f'30 min limit: only update {ev.last_step} of {upto}'
                break
        if not self.kill_job(pj, why=why or f'probe reached update {ev.last_step}'):
            why = (why or '') + ' (KILL FAILED: look at the processes before anything else)'
        return ev.update(), why

    # ---- reports
    @staticmethod
    def md_trace_a(job, r):
        L = [f'# Trace A for {job["id"]}: {r["verdict"]}', '', f'rules (big-run, fixed before the run): {json.dumps(r["rules"])}', '',
             f'- finite: {r["finite"]}; GPU memory in use (whole card, sampled every poll), peak: {r["max_used_mib"]} MiB (limit {r["rules"]["peak_limit_mib"]}); in use before the run started: {r.get("gpu_used_mib_at_launch")} MiB',
             f'- loss: mean of updates 1..{r["rules"]["first_n"]} = {r.get("mean_first")}, mean of the last {r["rules"]["last_n"]} of {r["upto"]} = {r.get("mean_last")}, falls: {r.get("falls")}',
             f'- resume: {json.dumps(r.get("resume"))}', f'- failures: {r["why_fail"] or "none"}', f'- recorded, not gated (rules.soft = {r["rules"].get("soft", [])}; the result is read only if RESULT.json peak_mem_mib <= {r["rules"]["peak_limit_mib"]} and the resume-noise probe passes): {r.get("soft_misses") or "none"}',
             f'- notes: {r["notes"] or "none"}']
        return '\n'.join(L) + '\n'

    @staticmethod
    def md_compare(job, r):
        L = [f'# Accum {job["accum"]} against the accum-32 baseline, first {r["upto"]} updates: {r["verdict"]}', '', f'rules (big-run): {json.dumps(r["rules"])}', '']
        for k in ('diff_of_means', 'last_n_diff', 'report_beside', 'read_as', 'why'):
            if k in r:
                L.append(f'- {k}: {json.dumps(r[k])}')
        return '\n'.join(L) + '\n'

    @staticmethod
    def md_probe(r):
        f = lambda x: f'{x:.4f}'
        L = [f'# Resume-noise probe for {r["job"]}: {r["verdict"]}', '',
             f'In plain words: the training run was restarted twice, on purpose, from the same saved copy (update {r["step"]}) on an idle card, and each restart redid updates {r["step"] + 1} to {r["upto"]}. '
             "We compare the two restarts with each other (that gap, n, is the card's own run-to-run noise) and each with what the real run logged (gap d). "
             'If the restarts differ from the real run by no more than the larger of 0.10 and 3 times the noise, the restart is as good as never stopping (PASS); '
             'if more, the restored state is wrong somewhere and the run is not read (FAIL).', '']
        if r['why_fail']:
            L += ['Problems: ' + '; '.join(r['why_fail']), '']
        if 'n' in r:
            L += [f'- n = largest |R1 - R2| = {r["n"]:.4f}; d = largest |R - C| = {r["d"]:.4f}; limit max(0.10, 3n) = {r["limit"]:.4f}',
                  f'- mean abs difference: R1-R2 {r["mean_abs_r1_r2"]:.4f}, R1-C {r["mean_abs_r1_c"]:.4f}, R2-C {r["mean_abs_r2_c"]:.4f}', '',
                  '| update | C (run) | R1 | R2 | abs R1-R2 | abs R1-C | abs R2-C |', '|---|---|---|---|---|---|---|']
            for i, s in enumerate(r['steps']):
                L.append(f'| {s} | {f(r["C"][i])} | {f(r["R1"][i])} | {f(r["R2"][i])} | {f(r["diff_r1_r2"][i])} | {f(r["diff_r1_c"][i])} | {f(r["diff_r2_c"][i])} |')
        if 'Dbar' in r:
            ac = r.get('lag1_autocorr')
            L += ['', '## recorded beside (pre-registered mean form, not the registered gate)', '',
                  f'The verdict above is the registered rule and is unchanged. These numbers are recorded next to it (re-read with rejudge_probe.py):',
                  f'- first probe update (expected exactly 0 when the restore is complete): |R1-C| = {r["first_r1_c"]:.6f}, |R2-C| = {r["first_r2_c"]:.6f}, |R1-R2| = {r["first_r1_r2"]:.6f}',
                  f'- Dbar = mean(mean|R1-C|, mean|R2-C|) = {r["Dbar"]:.4f}; Nbar = mean|R1-R2| = {r["Nbar"]:.4f}; ratio Dbar/Nbar = {r["ratio"]:.3f}',
                  f'- mean form: Dbar <= max(0.02, 2 Nbar) = {r["mean_form_limit"]:.4f}: {r["mean_form_verdict"]}',
                  f'- lag-1 autocorrelation of the signed series R1 - R2: {"not defined (no variance)" if ac is None else f"{ac:.3f}"}']
        if r.get('resume_warnings'):
            L += ['', 'resume_warning lines of the probe runs: ' + json.dumps(r['resume_warnings'])]
        return '\n'.join(L) + '\n'


# ---------------------------------------------------------------- commands
def run_loop(a):
    sup = Sup(a.plan)
    stops = sup.blocking_stops()                                      # (a stop file of a skipped job does not count)
    nxt = next((j for j in sup.active_jobs() if sup.st['jobs'].get(j['id'], {}).get('status') != 'done'), None)
    if stops or (sup.sd / 'ALL-DONE.txt').exists() or not (sup.sd / 'ARMED.txt').exists() or (nxt is not None and not sup.armed_for(nxt)):
        why = (f'{stops[0].name} exists' if stops else 'ALL-DONE.txt exists' if (sup.sd / 'ALL-DONE.txt').exists() else
               'not armed (ARMED.txt missing; the Mac writes it with `arm` on Ben\'s go line)' if not (sup.sd / 'ARMED.txt').exists() else
               f'ARMED.txt does not arm job {nxt["id"]} (it arms {sup.armed_text()}); the Mac writes it with `arm` on Ben\'s go line')
        print(f'{ts()} nothing to do: {why}')                       # printed, not logged: the boot task starts this every few minutes
        return 0
    lock = acquire_lock(sup.sd / 'supervisor.lock')
    if lock is None:
        print(f'{ts()} another supervisor holds supervisor.lock; this one exits')
        return 0
    sup.log(f'supervisor started, pid {os.getpid()}, plan {sup.plan_path}, jobs {[j["id"] for j in sup.plan["jobs"]]}')
    while True:
        try:
            s = sup.cycle()
        except Exception as e:                          # never die on a transient error (a failed nvidia-smi or process listing, a half-written file)
            import traceback
            sup.log('cycle error: ' + traceback.format_exc().replace('\n', ' | ')[-700:])
            s = 30
        if s is None:
            sup.log('supervisor leaves the loop (see STOPPED.txt / ALL-DONE.txt / ARMED.txt)')
            return 0
        time.sleep(s)


def preflight(a):
    sup = Sup(a.plan)
    pl, ok = sup.plan, True

    def row(good, what, detail=''):
        nonlocal ok
        ok = ok and good
        print(f'[{"ok" if good else "FIX"}] {what} {detail}')

    import hashlib
    for rel, want in pl.get('pins', {}).items():
        p = Path(rel)
        h = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        row(h == want.lower(), 'pin', f'{p} {h[:12] if h else "MISSING"}')
    g = gpu_mem()
    need = pl['gpu']['need_free_mib']
    row(bool(g) and g[1] - g[0] >= need, 'GPU free', f'{(g[1] - g[0]) if g else "?"} MiB of {g[1] if g else "?"} (need {need}); other users: ' +
        str([f'pid {p} {c[:50]}' for p, c in list_procs() if 'llama' in c or 'ollama' in c]))
    du = shutil.disk_usage(pl['work'])
    row(du.free > 30 * 2 ** 30, 'disk', f'{du.free / 2 ** 30:.0f} GB free on the work drive')
    busy = [(p, c[:90]) for p, c in list_procs() if 'custom_io' in c and SELF_NAME not in c]
    row(not busy, 'no other custom_io job running', str(busy))
    row(not (Path(pl['work']) / 'STOP').exists(), 'no WORK\\STOP file')
    blocking = sup.blocking_stops()
    row(not blocking, 'no STOPPED.txt of the supervisor', str([p.name for p in blocking]) if blocking else '')
    for p, o in sup.stop_files():
        if p not in blocking:
            print(f'[info] {p.name} belongs to the skipped job {o}: it does not hold the loop')
    for j in pl['jobs']:
        if j.get('skip'):
            print(f'[skip] job {j["id"]} is skipped in plan.json ({j.get("skip_reason") or "no reason given"}): not checked')
            continue
        qp = Path(j['src']) / 'custom_io' / 'queue_local' / (j['queue'] + '.txt')
        row(qp.exists(), 'queue file', str(qp))
        mk = Path(j['src']) / 'G2FA4-SETUP-OK.txt'
        row(mk.exists() and 'tests passed' in mk.read_text(errors='replace'), 'installer ran and its CPU tests passed (G2FA4-SETUP-OK.txt)', mk.read_text(errors='replace').strip() if mk.exists() else 'MISSING')
        row(not self_out_exists(sup, j), 'no earlier output for the job name', str(sup.out_dir(j)))
    print('READY' if ok else 'NOT READY')
    return 0 if ok else 1


def self_out_exists(sup, j):
    d = sup.out_dir(j)
    return d.exists() and any(d.iterdir())


def clear(a):
    """releases the jobs named (all non-skipped ones without an id): their stop files are moved aside, their 'stopped' state goes back to 'pending'. A skipped job (its stop file, its state) is a record and stays as it is."""
    sup = Sup(a.plan)
    sk = sup.skipped_ids()
    if a.id is not None and a.id not in {j['id'] for j in sup.plan['jobs']}:
        print(f'refused: no job {a.id} in the plan (jobs: {[j["id"] for j in sup.plan["jobs"]]})')
        return 2
    if a.id in sk:
        print(f'refused: job {a.id} is skipped in plan.json: its stop file and its state are kept as they are (take "skip" out of the plan first if it is to run again)')
        return 2
    for p, owner in sup.stop_files():
        if owner not in sk and (a.id is None or owner in (None, a.id)):
            sup.log(f'{p.name} cleared: {aside(p)}')
    for j in sup.active_jobs():
        if a.id in (None, j['id']):
            js = sup.js(j)
            if js['status'] == 'stopped':
                js['status'], js['no_progress'] = 'pending', 0
                js.pop('why', None)
    sup.save()
    return 0


def arm(a):
    """ARMED.txt: line 1 `<time> armed: <Ben's words>`, line 2 `jobs: <ids of the non-skipped jobs of the plan>`. The earlier file (an earlier go line) is kept as .aside-<stamp>; the new one is swapped in with one os.replace (a running loop never sees none)."""
    sup = Sup(a.plan)
    ids = ' '.join(j['id'] for j in sup.active_jobs())
    p = sup.sd / 'ARMED.txt'
    kept = None
    if p.exists():
        kept = p.with_name(p.name + '.aside-' + stamp())
        for n in range(1, 100):
            if not kept.exists():
                break
            kept = p.with_name(f'{p.name}.aside-{stamp()}-{n}')              # two arms in one second: never over an earlier copy
        shutil.copy2(p, kept)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(f'{ts()} armed: {a.text}\njobs: {ids}\n', encoding='utf-8')
    replace_retry(tmp, p)
    sup.log(f'ARMED: {a.text} (jobs: {ids})' + (f'; the earlier ARMED.txt is kept as {kept.name}' if kept else ''))
    return 0


def disarm(a):
    sup = Sup(a.plan)
    sup.log(f'DISARMED: {aside(sup.sd / "ARMED.txt")}')
    return 0


def halt(a):
    sup = Sup(a.plan)
    sup.log(f'HALT: {aside(sup.sd / "ARMED.txt")}')
    for j in sup.plan['jobs']:
        for base in (False, True):
            if base and not j.get('baseline'):
                continue
            q = j['baseline']['queue'] if base else j['queue']
            if sup.find(j.get('runner_match', 'local_runner'), q):
                sup.kill_job(j, base=base, why='halt (Ben\'s word)')
    return 0


def first_per_step(train, lo, hi):
    """step -> loss of the first logged line per step in lo..hi."""
    d = {}
    for e in train:
        if lo <= e['step'] <= hi:
            d.setdefault(e['step'], e['loss'])
    return d


def queue_accum(text, arm):
    """the accum of `arm` on the g8a: line(s) of a queue file (`--accum B3G2=8`, or a bare `--accum 8` for every arm). -> (int or None, problem or None); None + problem if the file names two different values."""
    vals = set()
    for ln in text.splitlines():
        if ln.startswith('g8a:'):
            for m in re.finditer(r'--accum\s+(?:(\w+)=)?(\d+)', ln):
                if m.group(1) in (None, arm):
                    vals.add(int(m.group(2)))
    if len(vals) > 1:
        return None, f'the queue file names several --accum values for {arm}: {sorted(vals)}'
    return (vals.pop() if vals else None), None


def main_run_hashes(sup, job):
    """config hashes of the main run, cheaply: ({full hash from each sidecar in the run's own ckpt\\ (the newest two)}, {12-character prefixes from the `resumed` event lines of its events.jsonl})."""
    full, short = set(), set()
    arm = sup.arm_dir(job)
    for f in sorted((arm / 'ckpt').glob('step-*.json')):
        d = jload(f)
        if isinstance(d, dict) and d.get('config_hash'):
            full.add(d['config_hash'])
    try:
        for ln in open(arm / 'events.jsonl', encoding='utf-8', errors='replace'):
            if '"resumed"' in ln:
                try:
                    e = json.loads(ln)
                except ValueError:
                    continue
                if e.get('event') == 'resumed' and e.get('config_hash'):
                    short.add(str(e['config_hash'])[:12])
    except OSError:
        pass
    return full, short


def keep_guard(job, step, side, queue_text, main_hashes):
    """Does the kept checkpoint (its sidecar `side`) belong to `job` and to `step`? -> (problems, notes). Any problem = refuse (exit 2), nothing is run.
    train.py only WARNS when --accum differs from the checkpoint's (resume_warning), so without this the probe of a job could resume another job's checkpoint (the README's ckpt-keep holds g2fa4's accum-4 step 200; g2fa8 is accum 8)
    and report a false FAIL. The config hash does NOT include --accum (queue header), so it cannot tell g2fa4 from g2fa8: only the accum check can. The hash is compared with the main run's own (sidecars in its ckpt\\,
    or the `resumed` events) when one is there; when the main run has none of either (no checkpoint kept, never resumed) the comparison is skipped and said so in `notes`."""
    problems, notes = [], []
    if not isinstance(side, dict):
        return [f'step-{step}.json is not a JSON object'], notes
    if side.get('step') != step:
        problems.append(f'the sidecar step-{step}.json says step {side.get("step")!r}, not {step} (--step): the file is not that checkpoint')
    qa, qprob = queue_accum(queue_text, job.get('arm', 'B3G2'))
    if qprob:
        problems.append(qprob)
    pa = job.get('accum')
    if qa is not None and pa is not None and qa != pa:
        problems.append(f'job {job["id"]}: its queue file says --accum {qa} but plan.json says accum {pa}: cannot tell which one is the job\'s')
    want = qa if qa is not None else pa
    if want is None:
        problems.append(f'job {job["id"]}: no accum found (neither --accum {job.get("arm", "B3G2")}=<n> in {job["queue"]}.txt nor "accum" in plan.json): cannot check the checkpoint')
    elif side.get('accum') != want:
        problems.append(f'the checkpoint in --keep was saved at accum {side.get("accum")!r}, job {job["id"]} runs at accum {want}: it is another job\'s checkpoint (train.py would only warn and resume it); '
                        f'use the step-{step} of {job["id"]} itself, or --job of the job it belongs to')
    full, short = main_hashes
    h = side.get('config_hash')
    if full:
        if h not in full:
            problems.append(f'the checkpoint\'s config_hash {str(h)[:12]} differs from the main run\'s own checkpoints ({sorted(x[:12] for x in full)}): it is not this run\'s checkpoint')
    elif short:
        if str(h)[:12] not in short:
            problems.append(f'the checkpoint\'s config_hash {str(h)[:12]} differs from the main run\'s (resumed events: {sorted(short)})')
    else:
        notes.append('config_hash not compared: the main run has no checkpoint sidecar and no resumed event to take its hash from')
    return problems, notes


def probe_resume(a):
    """After the run: resume the kept checkpoint twice on the idle card (queues <queue>n1 / n2), compare with the run's own logged updates. Exit 0 PASS, 1 FAIL, 2 refused."""
    sup = Sup(a.plan)
    job = next((j for j in sup.plan['jobs'] if a.job == j['id'] or (a.job is None and not j.get('skip'))), None)          # without --job: the first job that is not skipped
    if job is None:
        print(f'refused: no job {a.job or "that is not skipped"} in the plan')
        return 2
    if job.get('skip'):
        print(f'refused: job {job["id"]} is skipped in plan.json; the probe does not touch a skipped job')
        return 2
    keep, step, upto = Path(a.keep), a.step, a.upto
    steps = list(range(step + 1, upto + 1))
    if not (sup.sd / 'ALL-DONE.txt').exists() and (sup.sd / 'ARMED.txt').exists():
        print('refused: the supervised run is armed and not finished (ALL-DONE.txt missing): halt it first, or wait; the probe never competes with it')
        return 2
    g, need = gpu_mem(), sup.plan['gpu']['need_free_mib']
    if not g or g[1] - g[0] < need:
        print(f'refused: the card is not idle ({"no GPU reading" if not g else f"{g[1] - g[0]} MiB free, need {need}"})')
        return 2
    sup.procs(True)
    qs = [(j, q) for j in sup.plan['jobs'] for q in [j['queue']] + ([j['baseline']['queue']] if j.get('baseline') else [])]
    busy = [(q, pid) for j, q in qs for pid in sup.find(j.get('runner_match', 'local_runner'), q)]
    if busy:
        print(f'refused: a runner of the plan is running: {busy}')
        return 2
    miss = [f'step-{step}.{x}' for x in ('pt', 'json') if not (keep / f'step-{step}.{x}').exists()]
    C = first_per_step(sup.events(job).train, step + 1, upto)
    if miss or any(s not in C for s in steps):
        print(f'refused: missing {miss or "logged updates %d..%d of the main run in %s" % (step + 1, upto, sup.arm_dir(job) / "events.jsonl")}')
        return 2
    side = jload(keep / f'step-{step}.json')
    qf = Path(job['src']) / 'custom_io' / 'queue_local' / (job['queue'] + '.txt')
    try:
        qtext = qf.read_text(encoding='utf-8')
    except OSError as e:
        print(f'refused: the queue file of job {job["id"]} cannot be read ({e})')
        return 2
    bad, notes = keep_guard(job, step, side, qtext, main_run_hashes(sup, job))
    for n in notes:
        sup.log(f'PROBE guard: {n}')
    if bad:
        print(f'refused: the checkpoint in {keep} is not job {job["id"]}\'s step {step}:\n  ' + '\n  '.join(bad))
        return 2
    R, why, warns = {}, [], {}
    for tag in ('n1', 'n2'):
        pj = sup.probe_job(job, tag)
        sup.log(f'PROBE {tag}: {pj["queue"]} / {pj["job"]} from {keep} step-{step}')
        ev, bad = sup.probe_run(job, pj, keep, step, upto)
        if bad:
            why.append(f'{tag}: {bad}')
        if ev is None:
            continue
        warns[tag] = [w.get('warning') for w in ev.warnings]
        if any('accum' in (w or '') for w in warns[tag]):
            why.append(f'{tag}: train.py warned about --accum on resume ({[w for w in warns[tag] if "accum" in (w or "")][0]}): the probe resumed another job\'s checkpoint; not judged')
            continue
        rs = next((s for _, s in ev.resumed), None)
        if rs != step:
            why.append(f'{tag}: resumed at {rs}, not {step}')
            continue
        R[tag] = first_per_step([e for e in ev.train if e['seg'] >= ev.resumed[0][0]], step + 1, upto)
        if any(s not in R[tag] for s in steps):
            why.append(f'{tag}: updates missing (first {[s for s in steps if s not in R[tag]][:5]})')
    r = dict(job=job['id'], step=step, upto=upto, keep=str(keep), why_fail=why, verdict='FAIL', resume_warnings={t: w for t, w in warns.items() if w})
    if not why:
        r.update(resume_probe_verdict([C[s] for s in steps], [R['n1'][s] for s in steps], [R['n2'][s] for s in steps]))
        r.update(steps=steps, C=[C[s] for s in steps], R1=[R['n1'][s] for s in steps], R2=[R['n2'][s] for s in steps])
    jdump(sup.sd / f'PROBE-RESUME-{job["id"]}.json', r)
    (sup.sd / f'PROBE-RESUME-{job["id"]}.md').write_text(Sup.md_probe(r), encoding='utf-8')
    sup.log(f'PROBE RESUME: {r["verdict"]} n={r.get("n")} d={r.get("d")} limit={r.get("limit")} {why or ""}')
    return 0 if r['verdict'] == 'PASS' else 1


def selftest(a):
    """CUDA in the context this process runs in (the boot task runs as SYSTEM): imports torch with the queue's PYTHONPATH and touches the GPU."""
    sup = Sup(a.plan)
    j = (sup.active_jobs() or sup.plan['jobs'])[0]                       # (every job of the plan has the same ENV lines)
    qf = Path(j['src']) / 'custom_io' / 'queue_local' / (j['queue'] + '.txt')
    env = dict(os.environ, PYTHONUTF8='1')
    for raw in open(qf, encoding='utf-8'):
        line = raw.strip()
        if line.startswith('#') and line[1:].split()[:1] == ['ENV']:
            k, _, v = line[1:].strip()[3:].strip().partition('=')
            env[k.strip()] = v.strip()
    code = ('import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-", torch.cuda.mem_get_info() if torch.cuda.is_available() else "-")\n'
            'import custom_io.models.b3g2, custom_io.models.eg as E; print("b3g2 import ok")\n'
            'import os; print("EG2 dir", os.environ.get("CUSTOM_IO_EG2"), os.path.isdir(os.environ.get("CUSTOM_IO_EG2", "")))\n'
            'm = E.FrozenEG().load(torch.device("cuda")) if torch.cuda.is_available() else None; print("FrozenEG on cuda ok" if m is not None else "no cuda")')
    r = subprocess.run([sup.plan['python'], '-c', code], capture_output=True, text=True, env=env, cwd=j['src'], timeout=900)
    who = os.environ.get('USERNAME') or os.environ.get('USER') or '?'
    txt = f'{ts()} user={who} rc={r.returncode}\nstdout: {r.stdout.strip()}\nstderr: {r.stderr.strip()[-600:]}\ngpu_mem: {gpu_mem()}\n'
    (sup.sd / 'selftest.txt').write_text(txt, encoding='utf-8')
    print(txt)
    return 0 if r.returncode == 0 and ' True ' in r.stdout and 'FrozenEG on cuda ok' in r.stdout else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--plan', default=str(HERE / 'plan.json'))
    sp = ap.add_subparsers(dest='cmd', required=True)
    for c in ('preflight', 'run', 'status'):
        sp.add_parser(c)
    cl = sp.add_parser('clear')
    cl.add_argument('id', nargs='?')
    ar = sp.add_parser('arm')
    ar.add_argument('text')
    for c in ('disarm', 'halt', 'selftest'):
        sp.add_parser(c)
    pr = sp.add_parser('probe-resume')
    pr.add_argument('--keep', required=True)
    pr.add_argument('--step', type=int, required=True)
    pr.add_argument('--upto', type=int, required=True)
    pr.add_argument('--job')
    a = ap.parse_args(argv)
    if a.cmd == 'run':
        return run_loop(a)
    if a.cmd == 'preflight':
        return preflight(a)
    if a.cmd == 'probe-resume':
        return probe_resume(a)
    if a.cmd in ('clear', 'arm', 'disarm', 'halt', 'selftest'):
        return globals()[a.cmd](a)
    print((Sup(a.plan).sd / 'status.md').read_text(encoding='utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
