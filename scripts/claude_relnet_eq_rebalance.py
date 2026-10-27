#!/usr/bin/env python3
"""Detached helper: when the first practice run exits, move the second one onto more threads.

Waits for --pid-done to exit, waits for the second run to print its next checkpoint line (so the resume.pt is
freshly and completely saved), stops the second run by its exact PID, and restarts the same command with more
threads. claude_relnet_eq_practice.py resumes from resume.pt (weights, optimizer, schedule, both RNG streams).
"""
import argparse, os, signal, subprocess, sys, time
from pathlib import Path

def alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return Path(f"/proc/{pid}/stat").exists() and Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"

ap = argparse.ArgumentParser()
ap.add_argument("--pid-done", type=int, required=True)
ap.add_argument("--pid-move", type=int, required=True)
ap.add_argument("--log", required=True)
ap.add_argument("--threads", type=int, required=True)
ap.add_argument("--seed", type=int, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
def stamp(m):
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), m, flush=True)
while alive(a.pid_done):
    time.sleep(30)
stamp(f"pid {a.pid_done} finished")
if not alive(a.pid_move):
    stamp(f"pid {a.pid_move} already finished; nothing to move"); sys.exit(0)
n0 = len(Path(a.log).read_text().splitlines())
while alive(a.pid_move) and len(Path(a.log).read_text().splitlines()) == n0:
    time.sleep(10)
if not alive(a.pid_move):
    stamp("second run finished on its own"); sys.exit(0)
os.kill(a.pid_move, signal.SIGTERM)
while alive(a.pid_move):
    time.sleep(1)
stamp(f"stopped pid {a.pid_move} just after a checkpoint; restarting seed {a.seed} on {a.threads} threads")
with open(a.log, "ab") as lg:
    p = subprocess.Popen([sys.executable, "-B", "scripts/claude_relnet_eq_practice.py", "--seed", str(a.seed),
                          "--threads", str(a.threads), "--out", a.out], stdout=lg, stderr=subprocess.STDOUT,
                         start_new_session=True)
stamp(f"restarted seed {a.seed} as pid {p.pid}")
