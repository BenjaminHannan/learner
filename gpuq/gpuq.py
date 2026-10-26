#!/usr/bin/env python3
"""gpuq: a tiny, stdlib-only GPU job queue whose goal is that GPUs never sit idle.

Layout under $GPUQ_HOME (default ~/gpuq):
  pending/ running/ done/ failed/   job scripts (<name>.sh), moved with os.rename
  logs/<name>.log                   job stdout+stderr (appended per attempt)
  out/<name>/                       job cwd ($GPUQ_OUT); out/filler-<f>/run<k>/ for fillers
  filler/*.sh                       preemptible filler jobs, re-run forever
  state.json  daemon.log  ALERT_EMPTY

Job header (comment lines in a bash script): `# gpuq: key=value`
  name priority gpus(1|2) hours owner retries mem_gb
"""
import argparse
import shutil
import contextlib
import fcntl
import json
import logging
import logging.handlers
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

log = logging.getLogger("gpuq")
log.addHandler(logging.NullHandler())

DIRS = ("pending", "running", "done", "failed", "logs", "out", "filler")
EXT_BUSY_MB = 2048          # GPU memory used by non-gpuq processes => slot busy
TIMEOUT_FACTOR = 1.1        # hard kill at hours * 1.1
# Runs the real command, then records its exit code atomically so a restarted
# daemon can still learn the result of a job it did not start itself.
# The wrapper survives SIGTERM (the whole group gets it) and keeps waiting, so the
# job itself gets the full grace period to checkpoint before the SIGKILL.
WRAPPER = ('rcf="$1"; shift; trap : TERM; "$@" & c=$!; '
           'while :; do wait $c; r=$?; kill -0 $c 2>/dev/null || break; done; '
           'echo $r >"$rcf.tmp" && mv "$rcf.tmp" "$rcf"; exit $r')
KEEPALIVE = ("import time\n"
             "try:\n"
             " import torch\n"
             " x=torch.randn(8192,8192,device='cuda')\n"
             " while True:\n"
             "  x=torch.nn.functional.normalize(x@x,dim=1); torch.cuda.synchronize()\n"
             "except Exception:\n"
             " time.sleep(300)\n")


class JobError(Exception):
    pass


# ---------------------------------------------------------------- paths/state
class Home:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("GPUQ_HOME") or (Path.home() / "gpuq")).expanduser().resolve()
        for d in DIRS:
            setattr(self, d, self.root / d)
        self.state_file = self.root / "state.json"
        self.alert = self.root / "ALERT_EMPTY"

    def ensure(self):
        for d in DIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)


def atomic_write(path, text):
    tmp = path.with_name("%s.tmp.%d" % (path.name, os.getpid()))
    tmp.write_text(text)
    os.replace(tmp, path)


def load_state(h):
    try:
        st = json.loads(h.state_file.read_text())
        if not isinstance(st, dict):
            raise ValueError("not a dict")
    except FileNotFoundError:
        st = {}
    except (ValueError, OSError):
        with contextlib.suppress(OSError):
            os.replace(h.state_file, str(h.state_file) + ".corrupt")
        st = {}
    for k in ("jobs", "running", "filler_runs"):
        st.setdefault(k, {})
    return st


def save_state(h, st):
    atomic_write(h.state_file, json.dumps(st, indent=1, sort_keys=True))


@contextlib.contextmanager
def state_lock(h):
    """Serialise state.json read-modify-write between daemon and CLI commands."""
    h.root.mkdir(parents=True, exist_ok=True)
    with open(h.root / "state.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


# ------------------------------------------------------------------- headers
HDR = re.compile(r"^\s*#\s*gpuq:\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")


def parse_header(path):
    raw = {}
    with open(path, errors="replace") as f:
        for i, line in enumerate(f):
            if i >= 100:
                break
            m = HDR.match(line)
            if m:  # drop trailing "   (comment)" text
                raw[m.group(1)] = re.split(r"\s{2,}|\s+\(", m.group(2))[0].strip()
    try:
        job = dict(name=raw.get("name") or Path(path).stem,
                   priority=int(raw.get("priority", 0)), gpus=int(raw.get("gpus", 1)),
                   hours=float(raw.get("hours", 24)), retries=int(raw.get("retries", 0)),
                   owner=raw.get("owner", ""), mem_gb=raw.get("mem_gb", ""),
                   commit=raw.get("commit", ""))
    except ValueError as e:
        raise JobError("bad header value: %s" % e)
    if not NAME_RE.match(job["name"]):
        raise JobError("bad name %r (use letters, digits, . _ -)" % job["name"])
    if job["gpus"] not in (1, 2):
        raise JobError("gpus must be 1 or 2")
    if job["hours"] <= 0 or job["retries"] < 0:
        raise JobError("hours must be > 0 and retries >= 0")
    return job


# ----------------------------------------------------------------- GPU/process
def gpu_stats():
    """{index: {util, mem_used, mem_total}} (MiB); {} if nvidia-smi is unavailable."""
    fake = os.environ.get("GPUQ_FAKE_GPUS")
    if fake:
        stats = {i: dict(util=0, mem_used=0, mem_total=24564) for i in range(int(fake))}
        for part in filter(None, os.environ.get("GPUQ_FAKE_MEM", "").split(",")):
            i, mb = part.split(":")
            if int(i) in stats:
                stats[int(i)]["mem_used"] = int(mb)
        return stats
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used,memory.total",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20).stdout
        stats = {}
        for line in out.strip().splitlines():
            i, u, mu, mt = [x.strip() for x in line.split(",")]
            stats[int(i)] = dict(util=int(u), mem_used=int(mu), mem_total=int(mt))
        return stats
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def detect_gpus(arg):
    if arg:
        return [int(x) for x in arg.split(",")]
    if os.environ.get("GPUQ_FAKE_GPUS"):
        return list(range(int(os.environ["GPUQ_FAKE_GPUS"])))
    try:
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    gpus = [int(m) for m in re.findall(r"^GPU (\d+):", out, re.M)]
    if not gpus:
        sys.exit("gpuq: no GPUs found (nvidia-smi -L); pass --gpus 0,1")
    return gpus


def proc_start(pid):
    """Kernel start time of pid (field 22 of /proc/pid/stat), or None; guards against pid reuse after reboot."""
    try:
        return Path("/proc/%d/stat" % pid).read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError, ValueError):
        return None


def pid_alive(pid, start=None):
    if pid <= 0:
        return False
    if start is not None and Path("/proc").is_dir() and proc_start(pid) != start:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def killpg(pid, sig):
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, sig)


def read_rc(path):
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


# -------------------------------------------------------------------- daemon
class Daemon:
    def __init__(self, h, gpus, grace=60.0, filler_cooldown=30.0):
        self.h, self.gpus, self.grace, self.cooldown_s = h, gpus, grace, filler_cooldown
        self.procs = {}         # key -> Popen for jobs this process started
        self.cooldown = {}      # filler name -> time before which it is not restarted
        self.ext_seen = set()
        self.warned = set()
        self.st = {}

    # ---- helpers
    def save(self):
        save_state(self.h, self.st)

    def tick(self):
        with state_lock(self.h):
            self.st = load_state(self.h)
            self.reap()
            self.schedule(gpu_stats())
            if self.h.alert.exists() and not any(r["name"] == "filler-keepalive" for r in self.st["running"].values()):
                with contextlib.suppress(OSError):
                    self.h.alert.unlink()
            self.save()

    def recover(self):
        """Startup: running/ files without a live owner go back to pending (or failed)."""
        with state_lock(self.h):
            self.st = load_state(self.h)
            run = self.st["running"]
            known = {r["name"] for r in run.values() if not r.get("filler")}
            for p in sorted(self.h.running.glob("*.sh")):
                if p.stem not in known:      # state lost: nothing to adopt
                    log.warning("recover: %s in running/ has no state; treating as lost", p.stem)
                    run["orphan:" + p.stem] = dict(name=p.stem, gpus=[], attempt=self.attempt(p.stem), pid=0,
                                                   start=time.time(), hours=1, rcfile="", filler=False)
            for key, rec in list(run.items()):
                if rec.get("filler") and not pid_alive(rec["pid"], rec.get("pstart")):
                    run.pop(key)
                elif not rec.get("filler") and not (self.h.running / (rec["name"] + ".sh")).exists():
                    run.pop(key)             # file already moved; state is stale
                elif rec["pid"] and pid_alive(rec["pid"], rec.get("pstart")):
                    log.info("recover: adopting live job %s pid %s", rec["name"], rec["pid"])
            self.save()

    def attempt(self, name):
        return self.st["jobs"].get(name, {}).get("attempt", 1)

    # ---- reaping
    def reap(self):
        now = time.time()
        for key, rec in list(self.st["running"].items()):
            try:
                proc = self.procs.get(key)
                alive = (proc.poll() is None) if proc else pid_alive(rec["pid"], rec.get("pstart"))
                if alive:
                    self.enforce(rec, now)
                    continue
                rc = read_rc(rec["rcfile"]) if rec.get("rcfile") else None
                if rc is None and proc is not None:
                    rc = proc.returncode
                self.finish(key, rec, rc)
            except Exception:
                log.exception("reap of %s failed; dropping its record", key)
                self.st["running"].pop(key, None)

    def enforce(self, rec, now):
        if not rec.get("kill"):
            if not rec.get("filler") and (self.h.running / (rec["name"] + ".cancel")).exists():
                self.terminate(rec, "cancel")
            elif now - rec["start"] > rec["hours"] * 3600 * TIMEOUT_FACTOR:
                self.terminate(rec, "timeout")
        elif now - rec["term_at"] > self.grace and not rec.get("killed"):
            rec["killed"] = True
            log.warning("%s ignored SIGTERM for %.0fs; SIGKILL", rec["name"], self.grace)
            killpg(rec["pid"], signal.SIGKILL)

    def terminate(self, rec, why):
        log.info("terminating %s (%s)", rec["name"], why)
        rec["kill"], rec["term_at"] = why, time.time()
        killpg(rec["pid"], signal.SIGTERM)

    def finish(self, key, rec, rc):
        name, kill, now = rec["name"], rec.get("kill"), time.time()
        self.procs.pop(key, None)
        if rec["pid"] and (proc_start(rec["pid"]) is None or rec.get("pstart") in (None, proc_start(rec["pid"]))):
            killpg(rec["pid"], signal.SIGKILL)   # stray children must not keep holding the GPU
        label = {"timeout": "timeout", "cancel": "cancelled", "preempt": "preempted"}.get(kill, rc)
        runtime = now - rec["start"]
        log.info("finished %s rc=%s runtime=%.0fs", name, label, runtime)
        if rec["gpus"] and rec.get("out"):
            meta = dict(name=name, gpu=rec["gpus"], attempt=rec["attempt"], start=rec["start"], end=now, rc=label)
            with contextlib.suppress(OSError):
                atomic_write(Path(rec["out"]) / "_gpuq.json", json.dumps(meta, indent=1))
        self.st["running"].pop(key, None)
        if rec.get("filler"):
            if rc != 0 and not kill:
                self.cooldown[rec["fname"]] = now + self.cooldown_s
            return
        src = self.h.running / (name + ".sh")
        with contextlib.suppress(OSError):
            (self.h.running / (name + ".cancel")).unlink()
        info = dict(attempt=rec["attempt"], start=rec["start"], end=now, rc=label, gpus=rec["gpus"], reason="")
        if kill in ("timeout", "cancel"):
            dest, info["reason"] = self.h.failed, "killed: " + kill
        elif rc == 0:
            dest = self.h.done
        else:
            try:
                retries = parse_header(src)["retries"]
            except Exception:
                retries = 0
            why = "lost (process vanished)" if rc is None else "rc=%s" % rc
            if rec["attempt"] <= retries:
                dest, info = self.h.pending, dict(attempt=rec["attempt"] + 1, last_rc=label)
                log.info("%s failed (%s); requeue attempt %d", name, why, rec["attempt"] + 1)
            else:
                dest, info["reason"] = self.h.failed, why
        with contextlib.suppress(OSError):
            os.rename(src, dest / src.name)
        self.st["jobs"][name] = info

    # ---- scheduling
    def load_pending(self):
        jobs = []
        for p in self.h.pending.glob("*.sh"):
            try:
                j = parse_header(p)
                j.update(name=p.stem, path=p, submitted=p.stat().st_mtime)
                jobs.append(j)
            except Exception as e:     # a bad job must never take the daemon down
                self.reject(p, str(e))
        jobs.sort(key=lambda j: (-j["priority"], j["submitted"], j["name"]))
        return jobs

    def reject(self, p, reason):
        log.error("bad job %s: %s -> failed/", p.name, reason)
        with contextlib.suppress(OSError):
            os.rename(p, self.h.failed / p.name)
        self.st["jobs"][p.stem] = dict(rc="bad-job", reason=reason, end=time.time(), attempt=1)

    def schedule(self, stats):
        run = self.st["running"]
        used = {g: rec for rec in run.values() for g in rec["gpus"]}
        ext = {g for g in self.gpus if g not in used and stats.get(g, {}).get("mem_used", 0) > EXT_BUSY_MB}
        if ext != self.ext_seen:
            log.warning("GPUs busy outside gpuq (mem > %d MiB, no gpuq job): %s", EXT_BUSY_MB, sorted(ext) or "none")
            self.ext_seen = ext
        free = [g for g in self.gpus if g not in used and g not in ext]
        fill = [g for g in self.gpus if g in used and used[g].get("filler")]
        reserved = set()
        for job in self.load_pending():
            avail = [g for g in free + fill if g not in reserved]
            if len(avail) < job["gpus"]:
                break      # head-of-line: keep freed slots for this job (fillers run meanwhile)
            chosen = avail[:job["gpus"]]
            reserved.update(chosen)
            drain = [g for g in chosen if g in fill]
            for g in drain:
                if not used[g].get("kill"):
                    self.terminate(used[g], "preempt")
            if not drain:
                self.start_job(job, chosen)
        for g in free:
            if g not in reserved:
                self.start_filler(g)

    def start_job(self, job, chosen):
        name = job["name"]
        dst = self.h.running / job["path"].name
        try:
            os.rename(job["path"], dst)
        except OSError:
            return
        if self.h.alert.exists():
            self.h.alert.unlink()
        try:
            extra = self.source_env(job)
        except Exception as e:
            self.reject(dst, "source checkout failed: %s" % e)
            return
        try:
            rec = self.launch(name, name, ["bash", str(dst)], chosen, job["hours"], self.attempt(name),
                              self.h.out / name, name, extra=extra)
        except Exception as e:
            log.exception("launch of %s raised", name)
            rec = None
        if rec is None:
            self.reject(dst, "could not launch")

    def source_env(self, job):
        """GPUQ_SRC = detached worktree of the job's `commit` (or the repo itself); GPUQ_FILES = data mirror."""
        repo = os.environ.get("GPUQ_REPO", "")
        env = dict(GPUQ_FILES=os.environ.get("GPUQ_FILES", str(self.h.root / "files")), GPUQ_SRC=repo)
        if not job.get("commit"):
            return env
        if not repo:
            raise JobError("commit= needs GPUQ_REPO set in the daemon's environment")
        git = lambda *a, **kw: subprocess.run(["git", "-C"] + list(a), timeout=120, capture_output=True,
                                             text=True, **kw)
        want = git(repo, "rev-parse", "-q", "--verify", job["commit"] + "^{commit}")
        if want.returncode != 0:
            git(repo, "fetch", "-q", "origin")
            want = git(repo, "rev-parse", "-q", "--verify", job["commit"] + "^{commit}", check=True)
        want = want.stdout.strip()
        wt = self.h.root / "src" / job["name"]
        if wt.exists():
            have = git(str(wt), "rev-parse", "HEAD").stdout.strip()
            dirty = git(str(wt), "status", "--porcelain", "--untracked-files=no").stdout.strip()
            if have != want or dirty:      # half-made, stale or edited checkout: rebuild it
                git(repo, "worktree", "remove", "-f", str(wt))
                shutil.rmtree(wt, ignore_errors=True)
        if not wt.exists():
            git(repo, "worktree", "prune")
            git(repo, "worktree", "add", "-f", "--detach", str(wt), want, check=True)
        env["GPUQ_SRC"] = str(wt)
        return env

    def fillers(self):
        out = []
        for p in sorted(self.h.filler.glob("*.sh")):
            try:
                if not os.access(p, os.X_OK):
                    raise JobError("not executable")
                j = parse_header(p)
                if j["gpus"] != 1:
                    raise JobError("fillers must use gpus=1")
                j.update(name=p.stem, path=p)
                out.append(j)
            except Exception as e:
                if (p, str(e)) not in self.warned:
                    self.warned.add((p, str(e)))
                    log.warning("ignoring filler %s: %s", p.name, e)
        out.sort(key=lambda j: (-j["priority"], j["name"]))
        return out

    def start_filler(self, g):
        now = time.time()
        fl = [f for f in self.fillers() if self.cooldown.get(f["name"], 0) <= now]
        active = {r.get("fname") for r in self.st["running"].values() if r.get("filler")}
        if fl:
            f = next((f for f in fl if f["name"] not in active), fl[0])
            fname, argv, hours = f["name"], ["bash", str(f["path"])], f["hours"]
        else:
            fname, argv, hours = "keepalive", [sys.executable, "-c", KEEPALIVE], 1
            log.warning("WARNING queue empty: no usable filler in %s; GPU %d runs built-in keepalive", self.h.filler, g)
            atomic_write(self.h.alert, "queue empty at %s; GPU %d on keepalive\n" % (time.ctime(), g))
        k = self.st["filler_runs"].get(fname, 0) + 1
        self.st["filler_runs"][fname] = k
        name = "filler-" + fname
        self.launch("%s-run%d" % (name, k), name, argv, [g], hours, 1, self.h.out / name / ("run%d" % k),
                    name, filler=True, fname=fname, run=k)

    def launch(self, key, name, argv, gpus, hours, attempt, outdir, logname, filler=False, fname=None, run=None, extra=None):
        h = self.h
        outdir.mkdir(parents=True, exist_ok=True)
        rcfile = outdir / "_rc"
        with contextlib.suppress(OSError):
            rcfile.unlink()
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=",".join(map(str, gpus)), GPUQ_OUT=str(outdir) + "/",
                   GPUQ_NAME=name, GPUQ_ATTEMPT=str(attempt), GPUQ_HOME=str(h.root))
        env.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")   # match nvidia-smi indices
        env.update(extra or {})
        if filler:
            env["GPUQ_FILLER_RUN"] = str(run)
        try:
            with open(h.logs / (logname + ".log"), "a") as lf:
                lf.write("=== gpuq attempt %d start %s gpus=%s%s ===\n" % (
                    attempt, time.strftime("%Y-%m-%d %H:%M:%S"), env["CUDA_VISIBLE_DEVICES"],
                    " filler_run=%s" % run if filler else ""))
                lf.flush()
                proc = subprocess.Popen(["bash", "-c", WRAPPER, "gpuq", str(rcfile)] + argv, cwd=outdir, env=env,
                                        stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT,
                                        start_new_session=True)
        except OSError as e:
            log.error("launch of %s failed: %s", name, e)
            return None
        rec = dict(name=name, gpus=list(gpus), attempt=attempt, pid=proc.pid, pstart=proc_start(proc.pid),
                   start=time.time(), hours=hours,
                   rcfile=str(rcfile), out=str(outdir), filler=filler, fname=fname)
        self.procs[key] = proc
        self.st["running"][key] = rec
        self.save()     # persist immediately so a crash cannot lose track of the pid
        log.info("started %s on GPU %s pid %d (attempt %d)", name, rec["gpus"], proc.pid, attempt)
        return rec

    def stop_all(self):
        for rec in self.st.get("running", {}).values():
            killpg(rec["pid"], signal.SIGKILL)
        for p in self.procs.values():
            with contextlib.suppress(Exception):
                p.wait(timeout=5)


# ------------------------------------------------------------------ commands
def cmd_daemon(a):
    h = Home()
    h.ensure()
    lock = open(h.root / "daemon.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("gpuq: another daemon already holds %s" % (h.root / "daemon.lock"))
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for hd in (logging.handlers.RotatingFileHandler(h.root / "daemon.log", maxBytes=5_000_000, backupCount=3),
               logging.StreamHandler()):
        hd.setFormatter(fmt)
        log.addHandler(hd)
    d = Daemon(h, detect_gpus(a.gpus), a.grace, a.filler_cooldown)
    stop = threading.Event()
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop.set())
    log.info("daemon start: gpus=%s home=%s tick=%ss", d.gpus, h.root, a.tick)
    d.recover()
    t0 = time.time()
    while not stop.is_set():
        try:
            d.tick()
        except Exception:
            log.exception("tick failed (continuing)")
        if a.once or (a.max_seconds and time.time() - t0 >= a.max_seconds):
            break
        stop.wait(a.tick)
    if a.kill_on_exit:
        d.stop_all()
    log.info("daemon exit (jobs left running keep running and are adopted on restart)")


def cmd_submit(a):
    h = Home()
    h.ensure()
    try:
        job = parse_header(a.jobfile)
    except (JobError, OSError) as e:
        sys.exit("gpuq: invalid job: %s" % e)
    with state_lock(h):
        for d in ("pending", "running", "done", "failed"):
            if (getattr(h, d) / (job["name"] + ".sh")).exists():
                sys.exit("gpuq: job %r already exists in %s/ (use requeue/cancel)" % (job["name"], d))
        text = Path(a.jobfile).read_text()
        if a.priority is not None:
            lines = [l for l in text.splitlines(True) if not re.match(r"\s*#\s*gpuq:\s*priority\s*=", l)]
            at = 1 if lines and lines[0].startswith("#!") else 0
            lines.insert(at, "# gpuq: priority=%d\n" % a.priority)
            text = "".join(lines)
        dst = h.pending / (job["name"] + ".sh")
        tmp = h.pending / ("." + job["name"] + ".part")
        tmp.write_text(text)
        os.rename(tmp, dst)
    print("submitted %s (gpus=%d hours=%g)" % (job["name"], job["gpus"], job["hours"]))


def cmd_cancel(a):
    h = Home()
    with state_lock(h):
        st = load_state(h)
        p = h.pending / (a.name + ".sh")
        if p.exists():
            os.rename(p, h.failed / p.name)
            st["jobs"][a.name] = dict(rc="cancelled", reason="cancelled while pending", end=time.time(), attempt=1)
            save_state(h, st)
            return print("cancelled pending job", a.name)
        if any(r["name"] == a.name and not r.get("filler") for r in st["running"].values()):
            (h.running / (a.name + ".cancel")).touch()
            return print("cancel requested; the daemon kills it on its next tick")
    sys.exit("gpuq: no pending or running job %r" % a.name)


def cmd_requeue(a):
    h = Home()
    with state_lock(h):
        for d in (h.failed, h.done):
            p = d / (a.name + ".sh")
            if p.exists():
                os.rename(p, h.pending / p.name)
                os.utime(h.pending / p.name)
                st = load_state(h)
                st["jobs"][a.name] = dict(attempt=1)
                save_state(h, st)
                return print("requeued", a.name)
    sys.exit("gpuq: %r not found in done/ or failed/" % a.name)


# ------------------------------------------------------------ status / render
def fdur(s):
    h, r = divmod(int(s or 0), 3600)
    m, s = divmod(r, 60)
    return "%dh%02dm" % (h, m) if h else "%dm%02ds" % (m, s)


def fts(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else "-"


def snapshot(h):
    st, now = load_state(h), time.time()
    running = [dict(name=r["name"], gpus=r["gpus"], start=r["start"], elapsed=now - r["start"],
                    attempt=r["attempt"], pid=r["pid"], hours=r["hours"], filler=bool(r.get("filler")),
                    alive=pid_alive(r["pid"], r.get("pstart"))) for r in sorted(st["running"].values(), key=lambda r: r["start"])]
    pending = []
    for p in h.pending.glob("*.sh"):
        try:
            j = parse_header(p)
        except Exception:
            j = dict(priority=0, gpus=1, hours=0, owner="?")
        try:
            mt = p.stat().st_mtime
        except OSError:
            continue    # moved while we looked
        pending.append(dict(name=p.stem, priority=j["priority"], gpus=j["gpus"], hours=j["hours"],
                            owner=j["owner"], submitted=mt))
    pending.sort(key=lambda j: (-j["priority"], j["submitted"], j["name"]))

    def finished(d):
        rows = []
        for p in d.glob("*.sh"):
            r = st["jobs"].get(p.stem, {})
            try:
                end = r.get("end") or p.stat().st_mtime
            except OSError:
                continue
            rows.append(dict(name=p.stem, rc=r.get("rc", "?"), gpus=r.get("gpus", []), start=r.get("start"),
                             end=end, runtime=(end - r["start"]) if r.get("start") else None,
                             attempt=r.get("attempt", 1), reason=r.get("reason", "")))
        return sorted(rows, key=lambda r: -r["end"])
    gpus = []
    for i, s in sorted(gpu_stats().items()):
        jobs = [r["name"] for r in running if i in r["gpus"]]
        gpus.append(dict(index=i, util=s["util"], mem_used=s["mem_used"], mem_total=s["mem_total"], jobs=jobs))
    return dict(time=now, gpus=gpus, running=running, pending=pending, done=finished(h.done),
                failed=finished(h.failed), alert_empty=h.alert.exists())


def table(headers, rows):
    rows = [[str(c) for c in r] for r in rows]
    w = [max(len(x) for x in col) for col in zip(headers, *rows)]
    return "\n".join("  ".join(c.ljust(n) for c, n in zip(r, w)).rstrip() for r in [headers] + rows)


def run_rows(s):
    return [[r["name"] + (" (filler)" if r["filler"] else ""), ",".join(map(str, r["gpus"])), fts(r["start"]),
             fdur(r["elapsed"]), "%g" % r["hours"], r["attempt"], r["pid"] if r["alive"] else "%s DEAD" % r["pid"]]
            for r in s["running"]]


RUN_H = ["name", "gpu", "started", "elapsed", "hours", "attempt", "pid"]


def cmd_status(a):
    s = snapshot(Home())
    if a.json:
        return print(json.dumps(s, indent=1))
    print("GPUs")
    print(table(["gpu", "util%", "mem MiB", "job"], [[g["index"], g["util"], "%d/%d" % (g["mem_used"], g["mem_total"]),
                                                      ",".join(g["jobs"]) or "-"] for g in s["gpus"]]))
    print("\nRunning (%d)" % len(s["running"]))
    print(table(RUN_H, run_rows(s)))
    print("\nPending (%d)" % len(s["pending"]))
    print(table(["name", "prio", "gpus", "hours", "owner"],
                [[j["name"], j["priority"], j["gpus"], "%g" % j["hours"], j["owner"]] for j in s["pending"]]))
    for key in ("done", "failed"):
        print("\n%s (%d, newest 10)" % (key.capitalize(), len(s[key])))
        print(table(["name", "rc", "ended", "runtime"],
                    [[j["name"], j["rc"], fts(j["end"]), fdur(j["runtime"])] for j in s[key][:10]]))
    if s["alert_empty"]:
        print("\n!! ALERT_EMPTY present: queue ran dry, GPUs are on keepalive")


def md_table(headers, rows):
    if not rows:
        return "_none_\n"
    esc = lambda c: str(c).replace("|", "\\|")
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] +
                     ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]) + "\n"


def render_md(h, path):
    s = snapshot(h)
    fin = lambda rows: [[j["name"], j["rc"], fts(j["end"]), fdur(j["runtime"]) if j["runtime"] is not None else "-",
                         j["reason"]] for j in rows]
    out = ["# GPU queue", "", "_Updated %s_" % fts(s["time"]), ""]
    if s["alert_empty"]:
        out += ["**ALERT: queue is empty, GPUs are running keepalive filler.**", ""]
    out += ["## GPUs", md_table(["gpu", "util %", "memory MiB", "job"], [
        [g["index"], g["util"], "%d/%d" % (g["mem_used"], g["mem_total"]), ", ".join(g["jobs"]) or "-"]
        for g in s["gpus"]])]
    out += ["## Running", md_table(RUN_H, run_rows(s))]
    out += ["## Pending (in run order)", md_table(["#", "name", "priority", "gpus", "hours", "owner"], [
        [i + 1, j["name"], j["priority"], j["gpus"], "%g" % j["hours"], j["owner"]] for i, j in enumerate(s["pending"])])]
    out += ["## Recently done (last 30)", md_table(["name", "rc", "ended", "runtime", ""], fin(s["done"][:30]))]
    out += ["## Failed", md_table(["name", "rc", "ended", "runtime", "reason"], fin(s["failed"]))]
    atomic_write(Path(path), "\n".join(out))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gpuq", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("daemon", help="run the scheduler")
    p.add_argument("--gpus", help="comma list of GPU indices (default: from nvidia-smi -L)")
    p.add_argument("--tick", type=float, default=15, help="seconds between scheduling loops")
    p.add_argument("--once", action="store_true", help="run one loop and exit")
    p.add_argument("--max-seconds", type=float, default=0, help="exit after this long (tests)")
    p.add_argument("--grace", type=float, default=60, help="SIGTERM->SIGKILL wait in seconds")
    p.add_argument("--filler-cooldown", type=float, default=30, help="pause before re-running a failing filler")
    p.add_argument("--kill-on-exit", action="store_true", help="kill running jobs on exit (tests)")
    p.set_defaults(fn=cmd_daemon)
    p = sub.add_parser("submit", help="queue a job script")
    p.add_argument("jobfile")
    p.add_argument("--priority", type=int)
    p.set_defaults(fn=cmd_submit)
    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("render-md", help="write QUEUE.md-style status")
    p.add_argument("path")
    p.set_defaults(fn=lambda a: render_md(Home(), a.path))
    for name, fn in (("cancel", cmd_cancel), ("requeue", cmd_requeue)):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
