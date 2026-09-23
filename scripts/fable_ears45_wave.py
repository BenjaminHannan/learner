#!/usr/bin/env python3
"""Rung 1 of design 43 -- run one wave (one arm, its three registered seeds in parallel)
and then score it.  One wave per arm keeps every wave under 30 minutes of wall-clock and
never puts more than 3 training processes on the CPU at once.

    python fable_ears45_wave.py --arm tape --updates 8000 \
        --art artifacts/fable-ears45-20260921
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEEDS = (4301, 4302, 4303)
RUNNER = ["uv", "run", "--offline", "--no-project", "--python", "3.12",
          "--with", "torch", "--with", "numpy", "python", "-B"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["tape", "bigru", "names"])
    ap.add_argument("--updates", type=int, default=8000)
    ap.add_argument("--art", required=True)
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args()
    art = Path(a.art)
    runs = art / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    t0 = time.time()
    if not a.score_only:
        procs = []
        for s in SEEDS:
            out = runs / f"{a.arm}-{s}"
            out.mkdir(parents=True, exist_ok=True)
            log = open(out / "train.log", "w")
            procs.append(subprocess.Popen(
                RUNNER + [str(HERE / "fable_ears45_train.py"), "--arm", a.arm,
                          "--seed", str(s), "--out", str(out),
                          "--updates", str(a.updates)],
                cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT))
        codes = [p.wait() for p in procs]
        if any(codes):
            print("TRAIN FAILED", codes)
            sys.exit(1)
    train_s = time.time() - t0
    rc = subprocess.run(
        RUNNER + [str(HERE / "fable_ears45_score.py"), "--arm", a.arm,
                  "--runs", str(runs), "--panels", str(art / "panels"),
                  "--out", str(art / f"score-{a.arm}.json")],
        cwd=HERE, env=env)
    wall = time.time() - t0
    (art / f"wave-{a.arm}.json").write_text(json.dumps(
        {"arm": a.arm, "updates": a.updates, "seeds": list(SEEDS),
         "train_wall_sec": train_s, "wave_wall_sec": wall}, indent=1))
    print(f"wave {a.arm}: train {train_s/60:.1f} min, total {wall/60:.1f} min")
    sys.exit(rc.returncode)


if __name__ == "__main__":
    main()
