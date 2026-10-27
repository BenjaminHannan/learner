#!/usr/bin/env python3
"""research-loop harness: keeps an autonomous experiment loop honest.

The harness, not the agent, runs every evaluation, compares results against
measured noise, commits or reverts with git, rations the holdout, picks the
next strategy, and keeps a short summary. All state lives in .research/,
which is excluded from git so reverts never touch it.

Standard library only. Works on Windows, macOS and Linux (Python 3.8+).

Commands (run from anywhere inside the repo):
  init        --goal TEXT                      create .research/, branch, templates
  setup       --metric M --direction max|min --dev-cmd CMD --holdout-cmd CMD --lock PATH...
  reference   --name NAME [--cmd CMD] [--holdout-cmd CMD]
  calibrate                                     baseline + noise floor on dev and holdout
  next                                          which strategy to try next, what is due
  trial       --hypothesis TEXT --predict TEXT [--hyp ID] [--source URL]
  confirm     [--final]                         rationed holdout check of the incumbent
  refreshed   --note TEXT                       acknowledge a research refresh
  relock      --reason TEXT                     re-hash the eval after a deliberate fix
  status                                        print the compact summary
  report                                        write .research/report.md
"""
import argparse
import fnmatch
import hashlib
import json
import math
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

RD = Path(".research")
CFG = RD / "config.json"
STATE = RD / "state.json"
LOG = RD / "log.jsonl"
RUNS = RD / "runs"
PATCHES = RD / "patches"
SUMMARY = RD / "summary.md"
REPORT = RD / "report.md"

ARM_ORDER = ["literature", "tune", "bold", "simplify", "combine"]
ARMS = {
    "literature": "Implement the highest-ranked untried card in .research/hypotheses.md. "
                  "Pass its id with --hyp and its link with --source.",
    "tune": "Make a small, conservative change to the current best: a hyperparameter, "
            "schedule, or minor tweak that recent results point to.",
    "bold": "Redesign one component substantially instead of tweaking it. Most bold trials "
            "fail; the point is a jump that tuning cannot reach.",
    "simplify": "Remove or simplify something (ablate a component, drop an option). Kept if "
                "it is not worse beyond noise and the diff deletes more lines than it adds.",
    "combine": "Merge two near-misses from .research/patches/ (listed in summary.md), or a "
               "near-miss with a hypothesis card.",
}
EXPLORE_ARMS = {"bold", "literature", "combine"}

DEFAULTS = {
    "seeds": 2, "calib_seeds": 5, "holdout_seeds": None, "timeout_min": 20.0,
    "max_trials": 200, "max_hours": None, "deadline": None, "z": 1.0,
    "early_stop_z": 2.0, "min_delta": 0.0, "holdout_every": 3, "holdout_cap": 12,
    "fork_every": 5, "refresh_every": 10, "plateau": 8, "explore": 0.2,
    "max_file_mb": 20.0,
}

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[-+]?(?:nan|inf)"


# ----------------------------------------------------------------- utilities

def die(msg, code=2):
    print("ERROR: " + msg)
    sys.exit(code)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def load(path, default=None):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def log_event(kind, **kw):
    rec = {"t": now_iso(), "kind": kind}
    rec.update(kw)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def git(*args, check=True):
    p = subprocess.run(["git"] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        die("git %s failed: %s" % (" ".join(args), (p.stderr or p.stdout).strip()))
    return p.stdout.strip()


def to_repo_root():
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if p.returncode != 0:
        die("not inside a git repository. Run `git init`, commit the project, then retry.")
    os.chdir(p.stdout.strip())


def head():
    return git("rev-parse", "HEAD")


def short(c):
    return (c or "")[:8]


def dirty_files():
    out = git("status", "--porcelain", "--untracked-files=all")
    return [l[3:] for l in out.splitlines() if l.strip()]


def untracked():
    out = git("ls-files", "--others", "--exclude-standard")
    return set(l for l in out.splitlines() if l.strip())


def exclude_path():
    p = Path(git("rev-parse", "--git-path", "info/exclude"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def add_excludes(paths):
    ex = exclude_path()
    have = ex.read_text(encoding="utf-8").splitlines() if ex.exists() else []
    new = [p for p in paths if p not in have]
    if new:
        with open(ex, "a", encoding="utf-8") as f:
            for p in new:
                f.write(p + "\n")
    return new


def norm(p):
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p or "."


def under(path, pattern):
    path, pat = norm(path), norm(pattern)
    if pat == ".":
        return True
    base = pat.rstrip("/")
    if path == base or path.startswith(base + "/"):
        return True
    return fnmatch.fnmatch(path, pat)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def std(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def fmtd(x):
    return "n/a" if x is None else "%+.4f" % x


# ------------------------------------------------------------------ locking

def hash_file(p, h):
    size = p.stat().st_size
    if size > 64 * 2 ** 20:  # large data files: size + mtime + head/tail
        st = p.stat()
        h.update(("%d:%d" % (size, st.st_mtime_ns)).encode())
        with open(p, "rb") as f:
            h.update(f.read(2 ** 20))
            f.seek(-2 ** 20, 2)
            h.update(f.read(2 ** 20))
    else:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(2 ** 20), b""):
                h.update(chunk)


def hash_paths(paths):
    out = {}
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            out[raw] = "MISSING"
            continue
        h = hashlib.sha256()
        files = [p] if p.is_file() else sorted(
            q for q in p.rglob("*") if q.is_file() and ".git" not in q.parts
            and "__pycache__" not in q.parts and q.suffix != ".pyc")
        for q in files:
            h.update(norm(str(q)).encode())
            hash_file(q, h)
        out[raw] = h.hexdigest()
    return out


def check_lock(cfg, state):
    cur = hash_paths(cfg["lock"])
    bad = [p for p in cfg["lock"] if cur.get(p) != state["lock"].get(p)]
    if bad:
        die("EVAL LOCK VIOLATION: %s changed since the benchmark was locked. Restore it "
            "(e.g. `git checkout -- <path>`). If the change is a deliberate bug fix to the "
            "benchmark, commit it and run `relock --reason \"...\"` (this forces recalibration)."
            % ", ".join(bad))


# ---------------------------------------------------------------- running

def kill_tree(p):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(p.pid, signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
    try:
        p.wait(timeout=15)
    except Exception:
        pass


def run_cmd(cmd, env, log_path, timeout_s):
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    t0 = time.time()
    with open(log_path, "wb") as f:
        p = subprocess.Popen(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, env=env, **kw)
        try:
            rc = p.wait(timeout=timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            kill_tree(p)
            rc, timed_out = -9, True
        except KeyboardInterrupt:
            kill_tree(p)
            raise
    dur = time.time() - t0
    size = log_path.stat().st_size
    if size > 2 * 2 ** 20:  # keep the tail of very long logs
        with open(log_path, "rb") as f:
            f.seek(-2 ** 20, 2)
            tail = f.read()
        with open(log_path, "wb") as f:
            f.write(b"[... log truncated by research-loop ...]\n" + tail)
    return rc, timed_out, dur


def parse_metrics(text, names):
    out = {}
    for n in names:
        rx = re.compile(r"(?<![\w.])%s\"?\s*[:=]\s*(%s)" % (re.escape(n), NUM), re.I)
        ms = rx.findall(text)
        if ms:
            try:
                out[n] = float(ms[-1])
            except ValueError:
                pass
    return out


def crash_signature(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in reversed(lines[-60:]):
        if re.search(r"(error|exception|traceback|killed|out of memory)", l, re.I):
            return l[:160]
    return (lines[-1][:160] if lines else "no output")


def sig_key(s):
    return re.sub(r"\d+", "#", s)[:120]


def metric_names(cfg):
    return [cfg["metric"]] + [g["metric"] for g in cfg["guards"]]


def evaluate(cfg, split, seeds, label, cmd=None, early=None):
    """Run cmd once per seed. Returns dict(values, metrics, crash, sig, dur, logs, stopped)."""
    cmd_t = cmd or (cfg["dev_cmd"] if split == "dev" else cfg["holdout_cmd"])
    names = metric_names(cfg)
    res = {"values": [], "metrics": {n: [] for n in names}, "crash": False, "sig": None,
           "dur": 0.0, "logs": [], "stopped": False}
    before = untracked()
    for i, s in enumerate(seeds):
        env = dict(os.environ)
        env.update({"RL_SEED": str(s), "RL_SPLIT": split, "RL_LABEL": label,
                    "PYTHONUNBUFFERED": "1"})
        c = cmd_t.replace("{seed}", str(s))
        lp = RUNS / ("%s-%s-s%s.log" % (label, split, s))
        print("  running %s seed %s ..." % (split, s), flush=True)
        rc, to, dur = run_cmd(c, env, lp, cfg["timeout_min"] * 60)
        res["dur"] += dur
        res["logs"].append(str(lp))
        text = lp.read_bytes().decode("utf-8", errors="replace")
        m = parse_metrics(text, names)
        v = m.get(cfg["metric"])
        if rc != 0 or v is None or math.isnan(v) or math.isinf(v):
            res["crash"] = True
            why = "timeout after %g min" % cfg["timeout_min"] if to else (
                "exit code %s" % rc if rc != 0 else "metric '%s' not found in output" % cfg["metric"])
            res["sig"] = "%s | %s" % (why, crash_signature(text))
            break
        res["values"].append(v)
        for n in names:
            if n in m:
                res["metrics"][n].append(m[n])
        print("    %s = %.6g  (%.0fs)" % (cfg["metric"], v, dur), flush=True)
        if early and i == 0 and len(seeds) > 1 and early(v):
            res["stopped"] = True
            break
    created = sorted(untracked() - before)
    if created:  # eval outputs must never end up in a commit
        newx = add_excludes(sorted(set(created)))
        if newx:
            print("  note: the eval created untracked files; excluded them from git locally: "
                  + ", ".join(newx[:5]) + (" ..." if len(newx) > 5 else ""))
            print("        (better: write outputs outside the repo or to a gitignored folder)")
    return res


def summarize_metrics(res):
    return {n: mean(v) for n, v in res["metrics"].items() if v}


# ------------------------------------------------------------------ guards

GUARD_RE = re.compile(r"^\s*([A-Za-z_][\w.\-/]*)\s*(>=|<=)\s*(.+?)\s*$")


def parse_guard(g):
    m = GUARD_RE.match(g)
    if not m:
        die("bad --guard %r; use e.g. \"new_task_acc>=0.8\" or \"new_task_acc>=baseline-0.02\"" % g)
    rhs = m.group(3).replace(" ", "")
    if not re.fullmatch(r"baseline(?:[-+*](?:%s))?|(?:%s)" % (NUM, NUM), rhs):
        die("bad guard threshold %r" % rhs)
    return {"metric": m.group(1), "op": m.group(2), "rhs": rhs, "text": g}


def guard_threshold(g, base_metrics):
    rhs = g["rhs"]
    if not rhs.startswith("baseline"):
        return float(rhs)
    b = base_metrics.get(g["metric"])
    if b is None:
        return None
    if rhs == "baseline":
        return b
    op, val = rhs[8], float(rhs[9:])
    return b - val if op == "-" else b + val if op == "+" else b * val


def check_guards(cfg, state, mets):
    fails = []
    base = (state.get("baseline") or {}).get("metrics", {})
    for g in cfg["guards"]:
        thr = guard_threshold(g, base)
        v = mets.get(g["metric"])
        if v is None:
            fails.append("%s missing from output" % g["metric"])
        elif thr is not None and ((g["op"] == ">=" and v < thr) or (g["op"] == "<=" and v > thr)):
            fails.append("%s=%.4g violates %s (threshold %.4g)" % (g["metric"], v, g["text"], thr))
    return fails


# --------------------------------------------------------------- statistics

def pooled_sigma(state):
    num = den = 0.0
    for n, s in state.get("sigma_samples", []):
        if n >= 2:
            num += (n - 1) * s * s
            den += n - 1
    return math.sqrt(num / den) if den else 0.0


def margin(cfg, state, n_cand, n_inc):
    s = pooled_sigma(state)
    return max(cfg["z"] * s * math.sqrt(1.0 / max(n_cand, 1) + 1.0 / max(n_inc, 1)),
               cfg["min_delta"])


def better(cfg, a, b):
    """Improvement of a over b in 'higher is better' units."""
    return (a - b) if cfg["direction"] == "max" else (b - a)


# ---------------------------------------------------------------- bookkeeping

def load_all(need_cfg=True):
    to_repo_root()
    state = load(STATE)
    if state is None:
        die("no .research/ here. Start with `loop.py init --goal \"...\"`.")
    cfg = load(CFG)
    if need_cfg and cfg is None:
        die("benchmark not set up yet. Run `loop.py setup ...` first.")
    return cfg, state


def n_trials(state):
    return len([t for t in state["trials"] if t.get("segment") == state["segment"]])


def seg_trials(state):
    return [t for t in state["trials"] if t.get("segment") == state["segment"]]


def last_keep_n(state):
    ts = seg_trials(state)
    for i in range(len(ts) - 1, -1, -1):
        if ts[i]["outcome"] == "keep":
            return i + 1
    return 0


def leading_arm(state):
    for t in reversed(seg_trials(state)):
        if t["outcome"] == "keep":
            return t["arm"]
    return None


def near_misses(state, k=5):
    nm = [t for t in seg_trials(state) if t["outcome"] == "near-miss" and t.get("patch")]
    nm.sort(key=lambda t: -(t.get("delta") or 0))
    return nm[:k]


def plateau_on(cfg, state):
    return n_trials(state) - last_keep_n(state) >= cfg["plateau"]


def refresh_due(cfg, state):
    n = n_trials(state)
    lr = state.get("last_refresh_n", 0)
    if n - lr >= cfg["refresh_every"]:
        return "every %d trials" % cfg["refresh_every"]
    if plateau_on(cfg, state) and lr < last_keep_n(state) + cfg["plateau"]:
        return "plateau: %d trials without a keep" % (n - last_keep_n(state))
    return None


def confirm_due(cfg, state):
    return state.get("keeps_since_confirm", 0) >= cfg["holdout_every"]


def stop_reason(cfg, state):
    n = n_trials(state)
    if n >= cfg["max_trials"]:
        return "reached max_trials (%d)" % cfg["max_trials"]
    if cfg.get("max_hours") and state.get("runtime_s", 0) / 3600 >= cfg["max_hours"]:
        return "reached max_hours of experiment runtime (%.1f h)" % cfg["max_hours"]
    if cfg.get("deadline") and datetime.now() >= datetime.fromisoformat(cfg["deadline"]):
        return "deadline %s passed" % cfg["deadline"]
    return None


def recent_crash_sigs(state, window=10):
    ts = seg_trials(state)[-window:]
    if not ts:
        return 0.0, []
    crashes = [t for t in ts if t["outcome"] == "crash"]
    rate = len(crashes) / len(ts)
    counts = {}
    for t in crashes:
        k = sig_key(t.get("crash_sig") or "")
        counts.setdefault(k, [0, t.get("crash_sig")])
        counts[k][0] += 1
    top = sorted(counts.values(), key=lambda x: -x[0])[:3]
    return rate, top


def summary_text(cfg, state):
    L = []
    L.append("# Research loop status  (%s)" % now_iso())
    L.append("Goal: " + state["goal"])
    if not cfg:
        L.append("Phase: %s. Next: research, build the benchmark, then `setup`." % state["phase"])
        return "\n".join(L) + "\n"
    s = pooled_sigma(state)
    n_inc = (state.get("incumbent") or {}).get("n", cfg["seeds"])
    L.append("Metric: %s (%s) | dev seeds/trial %d | noise sigma %.4g | min detectable delta %.4g"
             % (cfg["metric"], cfg["direction"], cfg["seeds"], s,
                margin(cfg, state, cfg["seeds"], n_inc)))
    if cfg["guards"]:
        L.append("Guards: " + "; ".join(g["text"] for g in cfg["guards"]))
    L.append("Segment %d | phase %s | branch %s" % (state["segment"], state["phase"], state.get("branch")))
    b = state.get("baseline")
    if b:
        L.append("Baseline: dev %.4f +/- %.4f | holdout %.4f +/- %.4f"
                 % (b["mean"], b["std"], b["holdout_mean"], b["holdout_std"]))
    if state.get("references"):
        L.append("References (dev): " + " | ".join(
            "%s %.4f" % (k, v["mean"]) for k, v in state["references"].items()))
    inc = state.get("incumbent")
    if inc and b:
        L.append("Incumbent: dev %.4f (trial #%s, %s) | %s vs baseline"
                 % (inc["mean"], inc.get("trial") or "base", short(inc["commit"]),
                    fmtd(better(cfg, inc["mean"], b["mean"]))))
    c = state.get("confirmed")
    if c and b:
        L.append("Last holdout-confirmed: #%s %s holdout %.4f (%s vs baseline) | holdout calls %d/%d"
                 % (c.get("trial") or "base", short(c["commit"]), c["holdout_mean"],
                    fmtd(better(cfg, c["holdout_mean"], b["holdout_mean"])),
                    len(state.get("holdout_calls", [])), cfg["holdout_cap"]))
    ts = seg_trials(state)
    cnt = lambda o: len([t for t in ts if t["outcome"] == o])
    L.append("Trials %d | keep %d | near-miss %d | discard %d | crash %d | runtime %.2f h"
             % (len(ts), cnt("keep"), cnt("near-miss"), cnt("discard"), cnt("crash"),
                state.get("runtime_s", 0) / 3600)
             + (" / %.1f h" % cfg["max_hours"] if cfg.get("max_hours") else "")
             + (" | deadline %s" % cfg["deadline"] if cfg.get("deadline") else ""))
    L.append("Arms (kept/tried): " + " | ".join(
        "%s %d/%d" % (a, len([t for t in ts if t["arm"] == a and t["outcome"] == "keep"]),
                      len([t for t in ts if t["arm"] == a])) for a in ARM_ORDER))
    due = []
    if confirm_due(cfg, state):
        due.append("holdout confirm")
    r = refresh_due(cfg, state)
    if r:
        due.append("research refresh (%s)" % r)
    sr = stop_reason(cfg, state)
    if sr:
        due.append("STOP: " + sr)
    L.append("Due: " + (", ".join(due) if due else "nothing"))
    rate, top = recent_crash_sigs(state)
    if rate >= 0.15 and top:
        L.append("Recurring errors (crash rate %.0f%% over last 10 trials):" % (100 * rate))
        for n, sig in top:
            L.append("  - x%d %s" % (n, sig))
    nm = near_misses(state)
    if nm:
        L.append("Near-miss patches (for combine): " + " | ".join(
            "%s (%s)" % (Path(t["patch"]).name, fmtd(t.get("delta"))) for t in nm))
    if ts:
        L.append("")
        L.append("Last trials (newest last):")
        L.append("  #    arm         outcome     delta     hypothesis")
        for t in ts[-8:]:
            L.append("  %-4s %-11s %-11s %-9s %s" % (t["id"], t["arm"], t["outcome"],
                     fmtd(t.get("delta")), (t["hypothesis"] or "")[:70]))
    return "\n".join(L) + "\n"


def write_summary(cfg, state):
    SUMMARY.write_text(summary_text(cfg, state), encoding="utf-8")


# ----------------------------------------------------------------- commands

PROGRAM_TMPL = """# Research program

## Goal
{goal}

## The goal as an experimental question
(e.g. "After training on tasks A then B then C, how much of A's accuracy survives,
without hurting how well C is learned?")

## Benchmark (fill in during Phase 2)
- Primary metric and direction:
- Guard metrics:
- Dev split / holdout split (and why the holdout tests the same capability):
- Per-trial budget:
- Reference points (floor / strong simple baseline / ceiling):

## Constraints
- Hardware (GPU, VRAM, disk):
- Files that may change:
- Must not touch:
- Total budget / deadline:

## Assumptions made without asking the user

## Benchmark changes (every relock, with reason)
"""

NOTES_TMPL = """# Research notes

One entry per source you actually read: link, what it found, why it matters here.
Mark sources you only saw the abstract of as (abstract only).

"""

HYP_TMPL = """# Hypothesis queue

Ordered by rank: the top untried card is what a `literature` trial implements next.
Re-rank at every research refresh. Keep retired cards (with their trial ids): failures are results.

## H1 - <short name>   [status: untried]
- Idea:
- Mechanism (why it should help here):
- Source:
- Expected effect (direction, rough size):
- Cost (implementation effort, runtime):
- Risk / how it could fail:
- Trials:
"""


def cmd_init(a):
    to_repo_root()
    if STATE.exists():
        die(".research/ already exists here. Use `status` to see where things stand.")
    if subprocess.run(["git", "rev-parse", "--verify", "HEAD"], capture_output=True).returncode:
        die("the repository has no commits yet. Commit the project first.")
    for d in (RD, RUNS, PATCHES):
        d.mkdir(parents=True, exist_ok=True)
    add_excludes([".research/"])
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not a.no_branch and not branch.startswith("research/"):
        slug = re.sub(r"[^a-z0-9]+", "-", a.goal.lower()).strip("-")[:40] or "run"
        name = "research/%s-%s" % (slug, datetime.now().strftime("%Y%m%d-%H%M"))
        git("checkout", "-b", name)
        branch = name
    me = Path(__file__).resolve()
    dst = (RD / "loop.py").resolve()
    if me != dst:
        shutil.copy2(me, dst)
    for fn, tmpl in (("program.md", PROGRAM_TMPL), ("notes.md", NOTES_TMPL),
                     ("hypotheses.md", HYP_TMPL)):
        p = RD / fn
        if not p.exists():
            p.write_text(tmpl.replace("{goal}", a.goal), encoding="utf-8")
    state = {"goal": a.goal, "phase": "research", "branch": branch, "base_commit": head(),
             "created": now_iso(), "segment": 1, "lock": {}, "trials": [], "trial_seq": 0,
             "references": {}, "baseline": None, "incumbent": None, "confirmed": None,
             "holdout_calls": [], "keeps_since_confirm": 0, "sigma_samples": [],
             "arms": {k: {"n": 0, "r": 0.0} for k in ARM_ORDER}, "pending": None,
             "last_refresh_n": 0, "runtime_s": 0.0, "refreshes": []}
    save(STATE, state)
    log_event("init", goal=a.goal, branch=branch)
    write_summary(None, state)
    print("Initialized .research/ on branch %s (the user's original branch is untouched)." % branch)
    print("From now on run the harness as:  python .research/loop.py <command>")
    print("Next: fill in .research/program.md, do the literature research (notes.md, "
          "hypotheses.md), build and commit the benchmark, then run `setup`.")


def parse_deadline(s):
    if not s:
        return None
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        hh, mm = map(int, s.split(":"))
        now = datetime.now()
        d = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if d <= now:
            d += timedelta(days=1)
        return d.isoformat(timespec="minutes")
    try:
        return datetime.fromisoformat(s).isoformat(timespec="minutes")
    except ValueError:
        die("bad --deadline %r; use HH:MM or YYYY-MM-DDTHH:MM (local time)" % s)


def cmd_setup(a):
    to_repo_root()
    state = load(STATE)
    if state is None:
        die("run `init` first.")
    if CFG.exists() and not a.force:
        die("benchmark already set up. To change the eval deliberately, commit the change and "
            "use `relock --reason ...`; to redo setup from scratch pass --force.")
    d = dirty_files()
    if d:
        die("uncommitted changes: %s. Commit the benchmark first so it can be locked."
            % ", ".join(d[:8]))
    for p in a.lock:
        if not Path(p).exists():
            die("lock path %s does not exist" % p)
    cfg = dict(DEFAULTS)
    for k in DEFAULTS:
        v = getattr(a, k, None)
        if v is not None:
            cfg[k] = v
    cfg.update({"metric": a.metric, "direction": a.direction, "dev_cmd": a.dev_cmd,
                "holdout_cmd": a.holdout_cmd, "lock": [norm(p) for p in a.lock],
                "editable": [norm(p) for p in (a.editable or [])],
                "guards": [parse_guard(g) for g in (a.guard or [])]})
    cfg["deadline"] = parse_deadline(a.deadline)
    if cfg["holdout_seeds"] is None:
        cfg["holdout_seeds"] = max(cfg["seeds"], 2)
    if "{seed}" not in a.dev_cmd:
        print("note: --dev-cmd has no {seed}; the seed is still passed as env var RL_SEED.")
    state["lock"] = hash_paths(cfg["lock"])
    state["phase"] = "calibrate"
    save(CFG, cfg)
    save(STATE, state)
    log_event("setup", cfg=cfg)
    write_summary(cfg, state)
    print("Benchmark locked: " + ", ".join(cfg["lock"]))
    print("Metric %s (%s), %d seeds per trial, %d calibration seeds, timeout %.0f min."
          % (cfg["metric"], cfg["direction"], cfg["seeds"], cfg["calib_seeds"], cfg["timeout_min"]))
    if cfg["deadline"]:
        print("Deadline: %s" % cfg["deadline"])
    print("Next: `reference --name ...` for floor / strong baseline / ceiling, then `calibrate`.")


def cmd_reference(a):
    cfg, state = load_all()
    check_lock(cfg, state)
    n = a.seeds or cfg["calib_seeds"]
    dev = evaluate(cfg, "dev", list(range(n)), "ref-" + a.name, cmd=a.cmd)
    if dev["crash"]:
        die("reference %s crashed: %s (log: %s)" % (a.name, dev["sig"], dev["logs"][-1]))
    rec = {"mean": mean(dev["values"]), "std": std(dev["values"]), "n": len(dev["values"]),
           "metrics": summarize_metrics(dev), "cmd": a.cmd or cfg["dev_cmd"]}
    if a.holdout_cmd:
        ho = evaluate(cfg, "holdout", list(range(n)), "ref-" + a.name, cmd=a.holdout_cmd)
        if not ho["crash"]:
            rec.update({"holdout_mean": mean(ho["values"]), "holdout_std": std(ho["values"])})
    state["references"][a.name] = rec
    state["runtime_s"] = state.get("runtime_s", 0) + dev["dur"]
    save(STATE, state)
    log_event("reference", name=a.name, rec=rec)
    write_summary(cfg, state)
    print("Reference %s: dev %.4f +/- %.4f%s" % (a.name, rec["mean"], rec["std"],
          (" | holdout %.4f" % rec["holdout_mean"]) if "holdout_mean" in rec else ""))


def cmd_calibrate(a):
    cfg, state = load_all()
    check_lock(cfg, state)
    d = dirty_files()
    if d:
        die("uncommitted changes (%s). Calibration measures the committed code; commit or "
            "stash first." % ", ".join(d[:8]))
    n = cfg["calib_seeds"]
    print("Calibrating: %d seeds on dev, %d on holdout." % (n, n))
    dev = evaluate(cfg, "dev", list(range(n)), "calib")
    if dev["crash"]:
        die("baseline dev run failed: %s (log: %s). Fix the benchmark before looping."
            % (dev["sig"], dev["logs"][-1]))
    ho = evaluate(cfg, "holdout", list(range(n)), "calib")
    if ho["crash"]:
        die("baseline holdout run failed: %s (log: %s)." % (ho["sig"], ho["logs"][-1]))
    c = head()
    dm, ds = mean(dev["values"]), std(dev["values"])
    hm, hs = mean(ho["values"]), std(ho["values"])
    mets = summarize_metrics(dev)
    fails = check_guards(cfg, dict(state, baseline={"metrics": mets}), mets)
    missing = [f for f in fails if "missing" in f]
    if missing:
        die("guard metric not printed by the eval: " + "; ".join(missing))
    state["baseline"] = {"commit": c, "mean": dm, "std": ds, "n": n, "metrics": mets,
                         "holdout_mean": hm, "holdout_std": hs, "holdout_n": n, "t": now_iso()}
    state["incumbent"] = {"commit": c, "mean": dm, "n": n, "metrics": mets, "trial": None}
    state["confirmed"] = {"commit": c, "holdout_mean": hm, "holdout_n": n, "trial": None,
                          "incumbent": dict(state["incumbent"])}
    state["holdout_sigma"] = hs
    state["sigma_samples"] = [[n, ds]]
    state["keeps_since_confirm"] = 0
    state["phase"] = "running"
    state["runtime_s"] = state.get("runtime_s", 0) + dev["dur"] + ho["dur"]
    save(STATE, state)
    log_event("calibrate", baseline=state["baseline"])
    write_summary(cfg, state)
    md = margin(cfg, state, cfg["seeds"], n)
    print("Baseline dev %.4f +/- %.4f | holdout %.4f +/- %.4f" % (dm, ds, hm, hs))
    print("Minimum detectable improvement per trial (z=%.1f, %d seeds): %.4g" % (cfg["z"], cfg["seeds"], md))
    if ds == 0:
        print("WARNING: zero spread across seeds. Either the eval ignores the seed or it is fully "
              "deterministic; single lucky configurations will look like progress. Make the seed "
              "vary data order / init, or set --min-delta.")
    for name, r in state["references"].items():
        print("  vs reference %-12s dev %.4f (%s)" % (name, r["mean"], fmtd(better(cfg, dm, r["mean"]))))
    print("Next: sanity-check the ordering of references and the detectable delta, then start "
          "the loop with `next`.")


def ucb_pick(state, allowed, rng, explore):
    arms = state["arms"]
    if rng.random() < explore:
        return rng.choice(sorted(allowed, key=ARM_ORDER.index)), "exploration draw"
    untried = [a for a in ARM_ORDER if a in allowed and arms[a]["n"] == 0]
    if untried:
        return untried[0], "not tried yet"
    total = sum(arms[a]["n"] for a in ARM_ORDER) + 1
    best, score = None, -1e9
    for a in ARM_ORDER:
        if a not in allowed:
            continue
        n = arms[a]["n"]
        sc = arms[a]["r"] / n + math.sqrt(2 * math.log(total) / n)
        if sc > score:
            best, score = a, sc
    r = arms[best]
    return best, "UCB (%.2f reward over %d tries)" % (r["r"], r["n"])


def cmd_next(a):
    cfg, state = load_all()
    if state["phase"] != "running":
        die("not ready to loop (phase: %s). Finish setup and calibrate first." % state["phase"])
    sr = stop_reason(cfg, state)
    if sr:
        state["pending"] = None
        save(STATE, state)
        print("STOP: %s." % sr)
        print("Wrap up: `confirm --final`, then `report`, then write the findings section of "
              ".research/report.md.")
        return
    n = n_trials(state) + 1
    allowed = set(ARM_ORDER)
    if not near_misses(state):
        allowed.discard("combine")
    notes = []
    if plateau_on(cfg, state):
        allowed &= EXPLORE_ARMS
        notes.append("plateau (%d trials since the last keep): exploring only"
                     % (n - 1 - last_keep_n(state)))
    lead = leading_arm(state)
    if lead and n % cfg["fork_every"] == 0 and len(allowed - {lead}) > 0:
        allowed.discard(lead)
        notes.append("fork step: branching off the current best with a different arm than '%s'" % lead)
    if not allowed:
        allowed = {"literature"}
    rng = random.Random(1000 * state["segment"] + n)
    arm, why = ucb_pick(state, allowed, rng, cfg["explore"])
    state["pending"] = {"n": n, "arm": arm, "why": why, "notes": notes}
    save(STATE, state)
    inc = state["incumbent"]
    print("NEXT: trial %d" % (state["trial_seq"] + 1))
    print("  arm: %s  (%s)" % (arm, why))
    for x in notes:
        print("  note: " + x)
    print("  do: " + ARMS[arm])
    print("  parent: HEAD %s, incumbent dev %s = %.4f" % (short(head()), cfg["metric"], inc["mean"]))
    due = []
    if confirm_due(cfg, state):
        due.append("holdout confirm is due: run `confirm` before this trial")
    r = refresh_due(cfg, state)
    if r:
        due.append("research refresh is due (%s): update hypotheses.md from results and new "
                   "searches, then run `refreshed --note \"...\"` before this trial" % r)
    for x in due:
        print("  DUE: " + x)
    left = []
    left.append("%d/%d trials" % (n - 1, cfg["max_trials"]))
    if cfg.get("max_hours"):
        left.append("%.1f/%.1f h runtime" % (state.get("runtime_s", 0) / 3600, cfg["max_hours"]))
    if cfg.get("deadline"):
        mins = (datetime.fromisoformat(cfg["deadline"]) - datetime.now()).total_seconds() / 60
        left.append("%dh%02dm to deadline" % (mins // 60, mins % 60))
    print("  budget: " + ", ".join(left))
    print("  then: make ONE change, and run `trial --hypothesis \"...\" --predict \"...\"`")


def stage_candidate(cfg):
    git("add", "-A", "--", ".")
    files = [f for f in git("diff", "--cached", "--name-only").splitlines() if f.strip()]
    if not files:
        die("no code changes to test. Edit the code for this trial first.")
    bad = [f for f in files if any(under(f, p) for p in cfg["lock"])]
    if bad:
        git("reset", "-q")
        die("the change touches locked benchmark files: %s. Revert them; the eval is off-limits."
            % ", ".join(bad))
    if cfg["editable"]:
        outside = [f for f in files if not any(under(f, p) for p in cfg["editable"])]
        if outside:
            git("reset", "-q")
            die("the change touches files outside --editable: %s" % ", ".join(outside))
    big = [f for f in files if Path(f).is_file() and Path(f).stat().st_size > cfg["max_file_mb"] * 2 ** 20]
    if big:
        git("reset", "-q")
        die("refusing to commit large files (%s). Keep data and checkpoints out of git "
            "(gitignore them or write them outside the repo)." % ", ".join(big))
    added = removed = 0
    for line in git("diff", "--cached", "--numstat").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
    return files, added, removed


def drop_bytecode(files):
    """Delete cached bytecode for changed .py files so a run can never use a stale .pyc."""
    for f in files:
        if f.endswith(".py"):
            p = Path(f)
            cache = p.parent / "__pycache__"
            if cache.is_dir():
                for c in cache.glob(p.stem + ".*.pyc"):
                    try:
                        c.unlink()
                    except OSError:
                        pass


def discard_candidate(files=()):
    git("reset", "-q", "--hard", "HEAD")
    drop_bytecode(files)


def require_incumbent_head(state):
    inc = state["incumbent"]["commit"]
    if head() != inc:
        die("HEAD (%s) is not the loop's incumbent (%s). Only the harness commits during the "
            "loop. If you committed by hand, `git reset --soft %s` turns those commits back into "
            "uncommitted changes you can test with `trial`." % (short(head()), short(inc), short(inc)))


def cmd_trial(a):
    cfg, state = load_all()
    if state["phase"] != "running":
        die("not in the loop phase (phase: %s)." % state["phase"])
    check_lock(cfg, state)
    sr = stop_reason(cfg, state)
    if sr:
        die("budget exhausted (%s). Wrap up with `confirm --final` and `report`." % sr)
    pend = state.get("pending")
    if not pend or pend["n"] != n_trials(state) + 1:
        die("run `next` first; it picks the strategy for this trial.")
    arm = a.arm or pend["arm"]
    if arm not in ARMS:
        die("unknown arm %s" % arm)
    if arm != pend["arm"] and not a.override:
        die("`next` chose arm '%s'. Follow it, or pass --arm %s --override \"reason\"."
            % (pend["arm"], arm))
    if confirm_due(cfg, state):
        die("holdout confirm is due. Run `confirm` first.")
    r = refresh_due(cfg, state)
    if r:
        die("research refresh is due (%s). Update hypotheses.md, then `refreshed --note ...`." % r)
    if not a.hypothesis.strip() or not a.predict.strip():
        die("--hypothesis and --predict are required: say what you changed and what you expect "
            "(direction and rough size) before seeing the result.")
    require_incumbent_head(state)
    files, added, removed = stage_candidate(cfg)
    drop_bytecode(files)
    tid = state["trial_seq"] + 1
    patch = PATCHES / ("%04d-%s.diff" % (tid, arm))
    patch.write_text(git("diff", "--cached", "--binary") + "\n", encoding="utf-8")
    inc = state["incumbent"]
    simplify_mode = arm == "simplify" and (added - removed) < 0
    S = cfg["seeds"]
    sig = pooled_sigma(state)
    print("Trial %d [%s]: %s" % (tid, arm, a.hypothesis))
    print("  files: %s (+%d -%d)" % (", ".join(files[:6]) + (" ..." if len(files) > 6 else ""),
                                     added, removed))

    def early(v):
        if sig <= 0:
            return False
        return better(cfg, v, inc["mean"]) < -cfg["early_stop_z"] * sig * math.sqrt(1 + 1.0 / inc["n"])

    scr = evaluate(cfg, "dev", list(range(S)), "t%04d" % tid, early=early)
    dur = scr["dur"]
    last_log = scr["logs"][-1] if scr["logs"] else "-"
    rec = {"id": tid, "segment": state["segment"], "arm": arm, "hypothesis": a.hypothesis,
           "predict": a.predict, "hyp": a.hyp, "source": a.source, "override": a.override,
           "parent": head(), "files": files, "lines_added": added, "lines_removed": removed,
           "patch": str(patch), "t": now_iso(), "notes": pend.get("notes", [])}
    outcome, reason, fresh = None, "", None
    delta = None
    if scr["crash"]:
        outcome, reason = "crash", scr["sig"]
        rec["crash_sig"] = scr["sig"]
    else:
        cm = mean(scr["values"])
        delta = better(cfg, cm, inc["mean"])
        rec.update({"dev_values": scr["values"], "dev_mean": cm, "dev_std": std(scr["values"]),
                    "metrics": summarize_metrics(scr), "delta": delta})
        if len(scr["values"]) >= 2:
            state["sigma_samples"].append([len(scr["values"]), std(scr["values"])])
        mg = margin(cfg, state, len(scr["values"]), inc["n"])
        thr = -mg if simplify_mode else mg
        gfails = check_guards(cfg, state, rec["metrics"])
        if scr["stopped"]:
            outcome, reason = "discard", "early stop: first seed %s below incumbent (noise %.3g)" % (
                fmtd(delta), sig)
        elif gfails:
            outcome, reason = "discard", "guard failed: " + "; ".join(gfails)
        elif delta > thr:
            print("  passed screening (%s > %s); confirming on %d fresh seeds ..." % (
                fmtd(delta), fmtd(thr), S))
            fseeds = [100000 + tid * 97 + k for k in range(S)]
            fr = evaluate(cfg, "dev", fseeds, "t%04d-fresh" % tid)
            dur += fr["dur"]
            last_log = fr["logs"][-1] if fr["logs"] else last_log
            if fr["crash"]:
                outcome, reason = "crash", "fresh-seed run: " + fr["sig"]
                rec["crash_sig"] = fr["sig"]
            else:
                fm = mean(fr["values"])
                fresh = {"values": fr["values"], "mean": fm, "metrics": summarize_metrics(fr)}
                rec["fresh"] = fresh
                if len(fr["values"]) >= 2:
                    state["sigma_samples"].append([len(fr["values"]), std(fr["values"])])
                fd = better(cfg, fm, inc["mean"])
                fthr = -margin(cfg, state, len(fr["values"]), inc["n"]) if simplify_mode else 0.0
                fg = check_guards(cfg, state, fresh["metrics"])
                if fd > fthr and not fg:
                    outcome = "keep"
                    reason = "screen %s, fresh seeds %s (threshold %s)" % (fmtd(delta), fmtd(fd), fmtd(fthr))
                    rec["delta"] = fd
                else:
                    outcome = "near-miss"
                    reason = "screen %s but fresh seeds %s%s" % (
                        fmtd(delta), fmtd(fd), ("; guard: " + "; ".join(fg)) if fg else "")
        elif delta > 0:
            outcome, reason = "near-miss", "%s is within noise (needs > %s)" % (fmtd(delta), fmtd(thr))
        else:
            outcome, reason = "discard", "%s vs incumbent" % fmtd(delta)
    rec["outcome"], rec["reason"] = outcome, reason
    rec["duration_s"] = dur
    if outcome == "keep":
        msg = "[research-loop #%d %s] %s\n\nPrediction: %s\nResult: %s\nSource: %s" % (
            tid, arm, a.hypothesis[:72], a.predict, reason, a.source or "-")
        ident = []
        if not git("config", "user.email", check=False):
            ident = ["-c", "user.name=research-loop", "-c", "user.email=research-loop@localhost"]
        git(*(ident + ["commit", "-q", "--no-verify", "-m", msg]))
        git("reset", "-q", "--hard", "HEAD")  # drop anything the eval scribbled on tracked files
        c = head()
        rec["commit"] = c
        state["incumbent"] = {"commit": c, "mean": fresh["mean"], "n": len(fresh["values"]),
                              "metrics": fresh["metrics"], "trial": tid}
        state["keeps_since_confirm"] = state.get("keeps_since_confirm", 0) + 1
    else:
        discard_candidate(files)
    reward = {"keep": 1.0, "near-miss": 0.25}.get(outcome, 0.0)
    state["arms"][arm]["n"] += 1
    state["arms"][arm]["r"] += reward
    state["runtime_s"] = state.get("runtime_s", 0) + dur
    state["trial_seq"] = tid
    state["trials"].append(rec)
    state["pending"] = None
    save(STATE, state)
    log_event("trial", **{k: v for k, v in rec.items() if k not in ("files",)})
    write_summary(cfg, state)
    print("RESULT trial %d: %s. %s" % (tid, outcome.upper(), reason))
    if outcome == "keep":
        print("  committed %s; incumbent is now %.4f" % (short(rec["commit"]), state["incumbent"]["mean"]))
    elif outcome == "crash":
        print("  reverted. Log: %s  (the change is saved at %s)" % (last_log, patch))
    else:
        print("  reverted (patch kept at %s)." % patch)
    print("  prediction was: %s" % a.predict)
    print("Next: update the card in hypotheses.md if this was one, then `next`.")


def cmd_confirm(a):
    cfg, state = load_all()
    if state["phase"] not in ("running", "done"):
        die("nothing to confirm yet (phase %s)." % state["phase"])
    check_lock(cfg, state)
    d = dirty_files()
    if d:
        die("uncommitted changes (%s); confirm checks the committed incumbent. Revert them first."
            % ", ".join(d[:8]))
    require_incumbent_head(state)
    conf = state["confirmed"]
    c = head()
    if c == conf["commit"]:
        state["keeps_since_confirm"] = 0
        if a.final:
            state["phase"] = "done"
        save(STATE, state)
        print("The incumbent (%s) is already holdout-confirmed; nothing to spend." % short(c))
        return
    if not (confirm_due(cfg, state) or a.final):
        die("holdout confirm is not due (%d/%d keeps since the last one). The holdout is rationed "
            "on purpose: every look at it leaks information into the loop."
            % (state.get("keeps_since_confirm", 0), cfg["holdout_every"]))
    calls = state.setdefault("holdout_calls", [])
    if len(calls) >= cfg["holdout_cap"] and not a.final:
        print("WARNING: holdout cap (%d) reached; this check will be reported as over budget."
              % cfg["holdout_cap"])
    n = cfg["holdout_seeds"]
    k = len(calls) + 1
    print("Holdout check %d on %s (%d seeds) ..." % (k, short(c), n))
    ho = evaluate(cfg, "holdout", list(range(n)), "confirm%02d" % k)
    state["runtime_s"] = state.get("runtime_s", 0) + ho["dur"]
    inc_trial = state["incumbent"].get("trial")
    if ho["crash"]:
        verdict, hm = "crash", None
    else:
        hm = mean(ho["values"])
        hs = state.get("holdout_sigma", 0.0)
        mg = max(cfg["z"] * hs * math.sqrt(1.0 / n + 1.0 / conf["holdout_n"]), cfg["min_delta"])
        dh = better(cfg, hm, conf["holdout_mean"])
        verdict = "regressed" if dh < -mg else ("gain" if dh > mg else "flat")
    call = {"t": now_iso(), "commit": c, "trial": inc_trial, "mean": hm, "n": n,
            "verdict": verdict, "final": bool(a.final)}
    if verdict in ("regressed", "crash"):
        tag = "research-loop/unconfirmed-%d" % k
        git("tag", "-f", tag, c)
        git("reset", "-q", "--hard", conf["commit"])
        state["incumbent"] = dict(conf["incumbent"])
        call["reverted_to"] = conf["commit"]
        # the keeps since the last confirmation did not transfer: take their credit back
        for t in seg_trials(state):
            if t["outcome"] == "keep" and t["id"] > (conf.get("trial") or 0):
                t["outcome"] = "reverted"
                t["reason"] = (t.get("reason") or "") + "; reverted by holdout check %d" % k
                state["arms"][t["arm"]]["r"] = max(0.0, state["arms"][t["arm"]]["r"] - 1.0)
        print("HOLDOUT %s: %s. The dev gains since %s did not transfer." % (
            verdict.upper(), ("holdout %.4f vs confirmed %.4f" % (hm, conf["holdout_mean"]))
            if hm is not None else ho["sig"], short(conf["commit"])))
        print("  Reverted to the last confirmed commit %s; the unconfirmed chain is tagged %s."
              % (short(conf["commit"]), tag))
        print("  Treat this as evidence of dev overfitting: prefer changes with a clear mechanism, "
              "and consider whether the dev split is too small or too easy to fit.")
    else:
        state["confirmed"] = {"commit": c, "holdout_mean": hm, "holdout_n": n, "trial": inc_trial,
                              "incumbent": dict(state["incumbent"])}
        b = state["baseline"]
        print("HOLDOUT %s: %.4f (vs last confirmed %.4f, vs baseline %s)." % (
            verdict.upper(), hm, conf["holdout_mean"], fmtd(better(cfg, hm, b["holdout_mean"]))))
    calls.append(call)
    state["keeps_since_confirm"] = 0
    if a.final:
        state["phase"] = "done"
    save(STATE, state)
    log_event("confirm", **call)
    write_summary(cfg, state)


def cmd_refreshed(a):
    cfg, state = load_all()
    if not a.note.strip():
        die("--note is required: what did the refresh change in the queue?")
    state["last_refresh_n"] = n_trials(state)
    state.setdefault("refreshes", []).append({"t": now_iso(), "n": n_trials(state), "note": a.note})
    save(STATE, state)
    log_event("refresh", note=a.note)
    write_summary(cfg, state)
    print("Research refresh recorded at trial %d." % n_trials(state))


def cmd_relock(a):
    cfg, state = load_all()
    if not a.reason.strip():
        die("--reason is required.")
    d = dirty_files()
    if d:
        die("commit the benchmark change first (%s)." % ", ".join(d[:8]))
    old = state["lock"]
    state["lock"] = hash_paths(cfg["lock"])
    state["segment"] += 1
    state["phase"] = "calibrate"
    state["pending"] = None
    state["arms"] = {k: {"n": 0, "r": 0.0} for k in ARM_ORDER}
    state["last_refresh_n"] = 0
    state["keeps_since_confirm"] = 0
    if state.get("references"):
        state.setdefault("old_references", []).append(state["references"])
        state["references"] = {}
    state.setdefault("relocks", []).append({"t": now_iso(), "reason": a.reason, "commit": head(),
                                            "old": old, "new": state["lock"]})
    save(STATE, state)
    log_event("relock", reason=a.reason)
    write_summary(cfg, state)
    print("Benchmark relocked; segment %d starts. Results from earlier segments are not comparable."
          % state["segment"])
    print("Log the reason in program.md, re-run the `reference` points, then `calibrate` again.")


def cmd_status(a):
    to_repo_root()
    state = load(STATE)
    if state is None:
        die("no .research/ here.")
    cfg = load(CFG)
    txt = summary_text(cfg, state)
    SUMMARY.write_text(txt, encoding="utf-8")
    print(txt)
    if state.get("pending"):
        print("Pending: trial %d, arm %s (already chosen by `next`)." % (state["pending"]["n"],
                                                                         state["pending"]["arm"]))


def cmd_report(a):
    cfg, state = load_all()
    b = state.get("baseline")
    if not b:
        die("nothing to report before calibration.")
    L = []
    old = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    m = re.search(r"<!-- findings:start -->.*?<!-- findings:end -->", old, re.S)
    L.append("# Research report\n")
    L.append("Goal: %s  \nBranch: `%s` (the user's original branch was not modified)  \nGenerated: %s\n"
             % (state["goal"], state.get("branch"), now_iso()))
    L.append(m.group(0) if m else "<!-- findings:start -->\n## Findings\n\n(Write the narrative "
             "here: headline result on the holdout with noise, what worked and why, notable "
             "failures, caveats, next hypotheses.)\n<!-- findings:end -->")
    L.append("\n## Benchmark\n")
    L.append("- Metric: `%s` (%s); guards: %s" % (cfg["metric"], cfg["direction"],
             ", ".join("`%s`" % g["text"] for g in cfg["guards"]) or "none"))
    L.append("- Dev: `%s`  \n- Holdout: `%s`" % (cfg["dev_cmd"], cfg["holdout_cmd"]))
    L.append("- Locked: %s; segment %d%s" % (", ".join("`%s`" % p for p in cfg["lock"]),
             state["segment"], (" (%d relocks, see program.md)" % len(state.get("relocks", [])))
             if state.get("relocks") else ""))
    L.append("- Noise: pooled dev sigma %.4g; holdout sigma %.4g; %d seeds per trial"
             % (pooled_sigma(state), state.get("holdout_sigma", 0), cfg["seeds"]))
    L.append("\n## Where things landed\n")
    L.append("| | dev | holdout |\n|---|---|---|")
    L.append("| baseline (start) | %.4f +/- %.4f | %.4f +/- %.4f |" % (b["mean"], b["std"],
             b["holdout_mean"], b["holdout_std"]))
    for k, r in state.get("references", {}).items():
        L.append("| reference: %s | %.4f +/- %.4f | %s |" % (k, r["mean"], r["std"],
                 ("%.4f" % r["holdout_mean"]) if "holdout_mean" in r else "-"))
    inc, conf = state["incumbent"], state["confirmed"]
    L.append("| incumbent (#%s, `%s`) | %.4f | %s |" % (inc.get("trial") or "base",
             short(inc["commit"]), inc["mean"],
             ("%.4f" % conf["holdout_mean"]) if conf["commit"] == inc["commit"] else "not confirmed"))
    L.append("| last holdout-confirmed (#%s, `%s`) | %.4f | %.4f |" % (conf.get("trial") or "base",
             short(conf["commit"]), conf["incumbent"]["mean"], conf["holdout_mean"]))
    ts = seg_trials(state)
    keeps = [t for t in ts if t["outcome"] == "keep"]
    L.append("\n## Kept changes (%d)\n" % len(keeps))
    if keeps:
        L.append("| # | arm | change | dev delta | commit | source |\n|---|---|---|---|---|---|")
        for t in keeps:
            L.append("| %d | %s | %s | %s | `%s` | %s |" % (t["id"], t["arm"],
                     t["hypothesis"].replace("|", "/")[:90], fmtd(t.get("delta")),
                     short(t.get("commit")), t.get("source") or "-"))
    rev = [t for t in ts if t["outcome"] == "reverted"]
    if rev:
        L.append("\nReverted by a holdout check (dev gains that did not transfer): " + "; ".join(
            "#%d %s (dev %s)" % (t["id"], t["hypothesis"][:60], fmtd(t.get("delta"))) for t in rev))
    L.append("\n## Holdout checks (%d of cap %d)\n" % (len(state.get("holdout_calls", [])), cfg["holdout_cap"]))
    for h in state.get("holdout_calls", []):
        L.append("- %s: trial #%s `%s` -> %s (%s)%s" % (h["t"], h.get("trial") or "base",
                 short(h["commit"]), ("%.4f" % h["mean"]) if h["mean"] is not None else "crash",
                 h["verdict"], (", reverted to `%s`" % short(h["reverted_to"])) if h.get("reverted_to") else ""))
    L.append("\n## Arms\n")
    L.append("| arm | tried | kept | near-miss | crash |\n|---|---|---|---|---|")
    for a_ in ARM_ORDER:
        at = [t for t in ts if t["arm"] == a_]
        L.append("| %s | %d | %d | %d | %d |" % (a_, len(at), len([t for t in at if t["outcome"] == "keep"]),
                 len([t for t in at if t["outcome"] == "near-miss"]),
                 len([t for t in at if t["outcome"] == "crash"])))
    L.append("\n## All trials\n")
    L.append("| # | arm | outcome | delta | hypothesis | prediction | reason |\n|---|---|---|---|---|---|---|")
    for t in ts:
        L.append("| %d | %s | %s | %s | %s | %s | %s |" % (t["id"], t["arm"], t["outcome"],
                 fmtd(t.get("delta")), t["hypothesis"].replace("|", "/")[:80],
                 t["predict"].replace("|", "/")[:60], (t.get("reason") or "").replace("|", "/")[:80]))
    L.append("\nRuntime: %.2f h of experiments across %d trials. Refreshes: %d."
             % (state.get("runtime_s", 0) / 3600, len(ts), len(state.get("refreshes", []))))
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("Wrote %s. Fill in the Findings section between the findings markers." % REPORT)


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="research-loop harness")
    sp = ap.add_subparsers(dest="command", required=True)

    p = sp.add_parser("init")
    p.add_argument("--goal", required=True)
    p.add_argument("--no-branch", action="store_true")

    p = sp.add_parser("setup")
    p.add_argument("--metric", required=True)
    p.add_argument("--direction", choices=["max", "min"], required=True)
    p.add_argument("--dev-cmd", required=True)
    p.add_argument("--holdout-cmd", required=True)
    p.add_argument("--lock", nargs="+", required=True)
    p.add_argument("--guard", action="append")
    p.add_argument("--editable", nargs="+")
    p.add_argument("--seeds", type=int)
    p.add_argument("--calib-seeds", dest="calib_seeds", type=int)
    p.add_argument("--holdout-seeds", dest="holdout_seeds", type=int)
    p.add_argument("--timeout-min", dest="timeout_min", type=float)
    p.add_argument("--max-trials", dest="max_trials", type=int)
    p.add_argument("--max-hours", dest="max_hours", type=float)
    p.add_argument("--deadline")
    p.add_argument("--z", type=float)
    p.add_argument("--early-stop-z", dest="early_stop_z", type=float)
    p.add_argument("--min-delta", dest="min_delta", type=float)
    p.add_argument("--holdout-every", dest="holdout_every", type=int)
    p.add_argument("--holdout-cap", dest="holdout_cap", type=int)
    p.add_argument("--fork-every", dest="fork_every", type=int)
    p.add_argument("--refresh-every", dest="refresh_every", type=int)
    p.add_argument("--plateau", type=int)
    p.add_argument("--explore", type=float)
    p.add_argument("--max-file-mb", dest="max_file_mb", type=float)
    p.add_argument("--force", action="store_true")

    p = sp.add_parser("reference")
    p.add_argument("--name", required=True)
    p.add_argument("--cmd")
    p.add_argument("--holdout-cmd", dest="holdout_cmd")
    p.add_argument("--seeds", type=int)

    sp.add_parser("calibrate")
    sp.add_parser("next")

    p = sp.add_parser("trial")
    p.add_argument("--hypothesis", required=True)
    p.add_argument("--predict", required=True)
    p.add_argument("--arm")
    p.add_argument("--override")
    p.add_argument("--hyp")
    p.add_argument("--source")

    p = sp.add_parser("confirm")
    p.add_argument("--final", action="store_true")

    p = sp.add_parser("refreshed")
    p.add_argument("--note", required=True)

    p = sp.add_parser("relock")
    p.add_argument("--reason", required=True)

    sp.add_parser("status")
    sp.add_parser("report")

    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    {"init": cmd_init, "setup": cmd_setup, "reference": cmd_reference, "calibrate": cmd_calibrate,
     "next": cmd_next, "trial": cmd_trial, "confirm": cmd_confirm, "refreshed": cmd_refreshed,
     "relock": cmd_relock, "status": cmd_status, "report": cmd_report}[a.command](a)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
