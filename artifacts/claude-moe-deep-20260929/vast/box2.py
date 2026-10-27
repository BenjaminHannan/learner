#!/usr/bin/env python3
"""v2 (ADDENDUM-2): wrapper claude_moe_deep_run2.py, GPU dry run first, 400-char bundle lines.
Runs the sealed MoE test on one vast rental, driven only over HTTPS (no ssh, no git credentials).

Started by the rental's onstart with env PIN=<commit>. It downloads the sealed code at PIN from the public repo,
checks SEAL.sha256.txt, runs the selftest, the CPU-vs-GPU smoke and phase 1 (seed 0 and seed 1 as two processes on
the one GPU). Results leave through this process's stdout (the instance log, read with the vast API): progress lines
and, after each part, a base64 tar.gz of the small result files between BUNDLE markers. Never a .pt.

It then polls artifacts/claude-moe-deep-20260929/vast/CONTROL.txt on main (raw.githubusercontent.com) every 2 min.
Each line is one order, run once: `holdout` (only after the phase-1 dev records are committed to main, which is how
PASSMARKS.md orders it: the line is only written after that commit), `phase2`, `phase3` (dev only, run as extra
processes), `bundle`, `exit`. A 14-hour cap ends the box (kills PID 1: the container exits, GPU billing stops).
"""
import base64
import hashlib
import io
import os
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
from pathlib import Path

PIN = os.environ["PIN"]
RAW = "https://raw.githubusercontent.com/BenjaminHannan/learner"
W = Path("/root/w")
ART = "artifacts/claude-moe-deep-20260929"
FILES = [f"scripts/{n}.py" for n in (
    "claude_blurt1", "claude_cre333_agent", "claude_cre333b_agent", "claude_fewex_bench", "claude_fewex_data",
    "claude_fewex_eq_bench", "claude_fewex_net", "claude_moe_deep_net", "claude_moe_deep_run", "claude_moe_deep_report",
    "claude_patch_eq_ladder", "claude_rsn358a_envs", "claude_rsn358m_maze", "claude_moe_deep_run2")] + [
    f"{ART}/vast/dryrun.py"] + [
    f"{ART}/{n}" for n in ("PASSMARKS.md", "DESIGN.md", "selftest.json", "SEAL.sha256.txt")] + [
    "artifacts/claude-fewex-20260927/EQ-DEV-GATE.json"]
T0 = time.time()
CAP_S = 14 * 3600
LOCK = threading.Lock()


def say(*a):
    with LOCK:
        print(time.strftime("%H:%M:%SZ", time.gmtime()), *a, flush=True)


def get(url, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            say("fetch retry", i, url, e)
            time.sleep(5 * (i + 1))
    raise SystemExit(f"FETCH-FAIL {url}")


def bundle(tag):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for p in sorted((W / ART).rglob("*")):
            if p.is_file() and p.suffix in (".json", ".txt", ".log") and "resume" not in p.name \
                    and p.name not in ("selftest.json", "SEAL.sha256.txt", "EQ-DEV-GATE.json"):
                tf.add(p, arcname=str(p.relative_to(W)))
    b = base64.b64encode(buf.getvalue()).decode()
    with LOCK:
        print(f"==BUNDLE-BEGIN {tag} {len(b)} {hashlib.sha256(b.encode()).hexdigest()}==", flush=True)
        for i in range(0, len(b), 400):
            print("B64 " + b[i:i + 400], flush=True)
        print(f"==BUNDLE-END {tag}==", flush=True)


def run(label, args, logname):
    """One driver process; its lines go to its own log and are echoed with a label."""
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    log = open(W / ART / "logs" / logname, "a")
    p = subprocess.Popen([sys.executable, "-B", "scripts/claude_moe_deep_run2.py", *args], cwd=W, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        log.write(line)
        log.flush()
        if "Warning" not in line and "warn(" not in line:
            say(f"[{label}]", line.rstrip()[:600])
    rc = p.wait()
    say(f"[{label}] exit {rc}")
    return rc


def worker(label, steps, logname):
    for args in steps:
        rc = run(label, args, logname)
        if rc != 0:
            say(f"[{label}] STOPPED at {args} rc={rc}")
            break
    bundle(label)


def cap_watch():
    while True:
        time.sleep(60)
        if time.time() - T0 > CAP_S:
            say("TIME-CAP reached: ending the container")
            bundle("timecap")
            os.system("kill -TERM 1")


def main():
    threading.Thread(target=cap_watch, daemon=True).start()
    say("box start, pin", PIN)
    for f in FILES:
        dst = W / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(get(f"{RAW}/{PIN}/{f}"))
    (W / ART / "logs").mkdir(parents=True, exist_ok=True)
    bad = 0
    for line in (W / ART / "SEAL.sha256.txt").read_text().splitlines():
        h, name = line.split()
        ok = hashlib.sha256((W / name).read_bytes()).hexdigest() == h
        bad += not ok
        say("seal", name, "OK" if ok else "MISMATCH")
    if bad:
        raise SystemExit("SEAL-MISMATCH")
    try:
        import numpy  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "numpy"], check=False)
    import torch
    say("torch", torch.__version__, torch.version.cuda, torch.cuda.is_available(),
        torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "cpus", os.cpu_count())
    try:
        subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv"])
    except OSError as e:
        say("no nvidia-smi:", e)
    if run("selftest", ["selftest", "--threads", "4"], "selftest_vast.txt") != 0:
        bundle("selftest-fail")
        raise SystemExit("SELFTEST-FAIL")
    # ADDENDUM-2: the whole pipeline once on the GPU with toy budgets (outside the results folder) before real work
    rc = subprocess.run([sys.executable, "-B", f"{ART}/vast/dryrun.py", "/root/dry", "cuda"], cwd=W,
                        capture_output=True, text=True)
    for line in (rc.stdout + rc.stderr).splitlines():
        if any(x in line for x in ("PLUMBING", "Traceback", "Error", "holdout keys", "File ")):
            say("[dryrun]", line[:400])
    if "PLUMBING OK" not in rc.stdout:
        say("DRYRUN-FAIL: nothing real is run")
        raise SystemExit("DRYRUN-FAIL")
    run("smoke", ["smoke", "--device", "cuda", "--threads", "4"], "smoke_log.txt")   # SMOKE-FAIL is a result
    bundle("smoke")
    ws = []
    for s in (0, 1):
        steps = [["source", "--cfg", "L8-E64", "--seed", str(s), "--device", "cuda", "--threads", "2"],
                 ["dev", "--cfg", "L8-E64", "--seed", str(s), "--init", "pre", "--device", "cuda", "--threads", "2"]]
        t = threading.Thread(target=worker, args=(f"p1s{s}", steps, f"log_phase1_s{s}.txt"))
        t.start()
        ws.append(t)
    done = set()
    extra = []
    while True:
        try:
            ctl = get(f"{RAW}/main/{ART}/vast/CONTROL.txt?t={int(time.time())}", tries=2).decode().split()
        except SystemExit:
            ctl = []
        for order in ctl:
            if order in done:
                continue
            done.add(order)
            say("CONTROL", order)
            if order == "holdout":
                for t in ws:
                    t.join()
                steps = [["holdout", "--cfg", "L8-E64", "--seed", str(s), "--init", "pre", "--device", "cuda"]
                         for s in (0, 1)]
                t = threading.Thread(target=worker, args=("holdout", steps, "log_holdout.txt"))
                t.start()
                extra.append(t)
            elif order in ("phase2", "phase3"):
                t = threading.Thread(target=worker, args=(order, [["phase", "--phase", order[-1], "--device", "cuda",
                                                                    "--threads", "2"]], f"log_{order}.txt"))
                t.start()
                extra.append(t)
            elif order == "bundle":
                bundle("asked")
            elif order == "exit":
                bundle("exit")
                say("EXIT ordered: ending the container")
                os.system("kill -TERM 1")
        if all(not t.is_alive() for t in ws) and not any(t.is_alive() for t in extra) and "phase1-done" not in done:
            done.add("phase1-done")
            say("PHASE1-WORKERS-DONE")
            bundle("phase1")
        time.sleep(120)


if __name__ == "__main__":
    main()
