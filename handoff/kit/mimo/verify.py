#!/usr/bin/env python3
"""Director mechanical verify: python3 verify.py <task-stem e.g. 203-smalltalk156c> <artifact dir>
1) shasum -c the seal (from the repo root); 2) walk go1..goN tool logs in order, find the seal creation,
list every Edit/Write after it, flagging edits to sealed files and to the ledger (append-only)."""
import re, subprocess, sys, glob, os
R = "/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27"
Q = os.path.dirname(os.path.abspath(__file__)) + "/queue"
stem, art = sys.argv[1], sys.argv[2].rstrip("/")
ansi = re.compile(r"\x1b\[[0-9;]*m")
seals = sorted(glob.glob(f"{R}/{art}/SEAL*.txt"))
sealed = set()
for s in seals:
    out = subprocess.run(["shasum", "-a", "256", "-c", os.path.relpath(s, R)], cwd=R, capture_output=True, text=True)
    bad = [l for l in out.stdout.splitlines() if not l.endswith(": OK")]
    print(f"SEAL {os.path.relpath(s, R)}: {len(out.stdout.splitlines())} lines, {'ALL OK' if not bad and out.returncode == 0 else 'PROBLEM: ' + '; '.join(bad) + out.stderr.strip()}")
    for l in open(s):
        parts = l.split()
        if len(parts) >= 2: sealed.add(parts[-1].lstrip("*"))
logs = sorted(glob.glob(f"{Q}/{stem}.go*.err.txt"), key=lambda p: int(re.search(r"\.go(\d+)\.", p).group(1)))
seal_seen = False
post = []
for lg in logs:
    g = re.search(r"\.go(\d+)\.", lg).group(1)
    for n, line in enumerate(open(lg, errors="replace"), 1):
        line = ansi.sub("", line.rstrip("\n"))
        if not seal_seen and (re.search(r"shasum -a 256 .*>\s*\S*SEAL", line) or re.search(r"(Write|Edit) \S*SEAL", line)):
            seal_seen = True; print(f"seal created: go{g} line {n}: {line[:160]}"); continue
        m = re.search(r"← .{0,6}(Edit|Write) (\S+)", line)
        if m and seal_seen:
            path = m.group(2)
            flag = "SEALED-FILE EDIT" if path in sealed else ("LEDGER " + m.group(1).upper() if "predictions-ledger" in path else "")
            post.append((g, n, m.group(1), path, flag))
if not seal_seen: print("WARNING: no seal creation found in logs")
print(f"post-seal edits/writes ({len(post)}):")
for g, n, k, p, f in post: print(f"  go{g}:{n} {k} {p} {('<-- ' + f) if f else ''}")
