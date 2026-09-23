#!/usr/bin/env python3
"""Exp F1 M5 wall: 3 alternated suite runs per arm under a quiet rule.

New file only. Each timed unit is the M2 suite block (suitediff218
sessions152+bench, suitediff218 rt136, rt143nogate) for one arm, run
in-process via the sealed modules (read-only imports). Order alternates
arms: F1, 292t, F1, 292t, F1, 292t. Before EVERY run, 1-min load must be
below 40 (poll every 120 s, total wait budget 6 h); if a run can never
start quiet, the wall is VOID (not FAIL). Free disk under 3 GB stops.

Bar (M5): median(F1) <= 1.05 * median(292t).

Usage:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_f1_wall.py <run>
Writes <run>/wall.json and prints medians + verdict.
"""

from __future__ import annotations

import copy
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load1() -> float:
    out = subprocess.run(["uptime"], capture_output=True, text=True).stdout
    import re
    m = re.search(r"load averages?:\s*([0-9.]+)", out)
    return float(m.group(1)) if m else 999.0


def free_gb() -> int:
    out = subprocess.run(["df", "-g", "/"], capture_output=True,
                         text=True).stdout
    return int(out.strip().split("\n")[-1].split()[3])


def wait_quiet(log, deadline, what) -> bool:
    while True:
        l = load1()
        log.write(f"{time.strftime('%H:%M:%S')} load1={l} before {what}\n")
        log.flush()
        if l < 40:
            return True
        if time.time() > deadline:
            return False
        time.sleep(120)
    return False


ARMS = {
    "292t": ("scripts/claude_loop292t_agent.py",
             "artifacts/claude-join292t-20260923/loop292t-config.json"),
    "f1": ("scripts/claude_loopf1_agent.py",
           "artifacts/claude-f1-20260923/loopf1-config.json"),
}


def run_block(arm, outdir, workdir) -> float:
    import fable_suitediff218 as S218
    agent, config = ARMS[arm]
    t0 = time.perf_counter()
    rc = S218.main(["--agent", agent, "--config", config,
                    "--base-dir",
                    "artifacts/claude-join292t-20260923/run/sd",
                    "--out", str(outdir / "sd"), "--only",
                    "sessions152,bench"])
    assert rc in (0, None), f"sd rc={rc}"
    rc = S218.main(["--agent", agent, "--config", config,
                    "--base-dir",
                    "artifacts/claude-join292t-20260923/run/sd136",
                    "--out", str(outdir / "sd136"), "--only", "rt136"])
    assert rc in (0, None), f"sd136 rc={rc}"
    import claude_138l_rt143nogate as RT
    RT.run(agent, config, outdir / "rt143.json")
    return time.perf_counter() - t0


def main() -> int:
    run = Path(sys.argv[1])
    walldir = run / "wall"
    walldir.mkdir(parents=True, exist_ok=True)
    log = open(run / "wall.log", "a", encoding="utf-8")
    deadline = time.time() + 6 * 3600
    runs = []
    order = ["f1", "292t"] * 3
    for i, arm in enumerate(order):
        if free_gb() < 3:
            print("free disk < 3 GB: STOP")
            return 5
        if not wait_quiet(log, deadline, f"wall-{i}-{arm}"):
            res = {"runs": runs, "verdict": "VOID",
                   "note": "never quiet (load1>=40 for 6h)"}
            json.dump(res, open(run / "wall.json", "w"), indent=1)
            print("WALL VOID: never quiet")
            return 0
        outdir = walldir / f"{i:02d}-{arm}"
        workdir = Path(tempfile.mkdtemp(prefix=f"f1wall-{i}-{arm}-"))
        try:
            sec = run_block(arm, outdir, workdir)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        runs.append({"arm": arm, "order": i, "seconds": round(sec, 2)})
        log.write(f"wall run {i} {arm}: {sec:.1f}s\n")
        log.flush()
        print(f"wall run {i} {arm}: {sec:.1f}s", flush=True)
    a = sorted(r["seconds"] for r in runs if r["arm"] == "292t")
    b = sorted(r["seconds"] for r in runs if r["arm"] == "f1")
    ma, mb = statistics.median(a), statistics.median(b)
    ratio = mb / ma if ma else float("inf")
    verdict = "PASS" if ratio <= 1.05 else "FAIL"
    res = {"runs": runs, "median292t": ma, "medianf1": mb,
           "ratio": round(ratio, 4), "bar": "<=1.05", "verdict": verdict}
    json.dump(res, open(run / "wall.json", "w"), indent=1)
    print(f"median292t={ma:.1f}s medianf1={mb:.1f}s ratio={ratio:.4f} "
          f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
