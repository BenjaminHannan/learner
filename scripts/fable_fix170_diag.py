#!/usr/bin/env python3
"""Exp 170 STEP1 diagnosis (unregistered, before seal): cProfile 25 asks on 15k notebook.

Builds loop138d exactly as 138d M6 did (same builder + config, copied
notebook dir), profiles 25 taught-entity asks, prints top-15 by cumulative
time with file:line.
"""
from __future__ import annotations
import copy, cProfile, io, pstats, shutil, sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_loop138d_agent as L138d

ROOT = SCRIPTS.parent
SRC = ROOT / "artifacts" / "fable-agent138d-20260922" / "work-speed2" / "nb138d"
WORK = ROOT / "artifacts" / "fable-speed170-20260922" / "scratch-diag" / "nb138d-copy"

def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC, WORK)
    cfg = copy.deepcopy(L138d.DEFAULT_CONFIG138D)
    cfg["state_dir"] = str(WORK)
    cfg["sleep_threshold"] = 100000
    lp = L138d.build_agent138d(cfg)
    n = sum(1 for f in lp.nb.facts.values() if f.get("source") == "taught")
    print(f"taught facts: {n}", flush=True)
    facts = [f for f in lp.nb.facts.values() if f.get("source") == "taught"]
    asks = [f"What is {lp.nb.entities[f['subject']]}'s {f['relation']}?"
            for k in range(25) for f in [facts[(k * 37) % len(facts)]]]
    # warmup-free: profile exactly the 25 asks
    pr = cProfile.Profile()
    pr.enable()
    for tx in asks:
        lp.turn(tx)
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(15)
    print(s.getvalue())
    # also full caller info for top offenders
    s2 = io.StringIO()
    pstats.Stats(pr, stream=s2).sort_stats("tottime").print_stats(10)
    print("=== tottime top10 ===")
    print(s2.getvalue())
    return 0

if __name__ == "__main__":
    sys.exit(main())
