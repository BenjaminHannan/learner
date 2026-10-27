#!/usr/bin/env python3
"""Exp 170 S1: 138d M6 ask test, loop170 vs loop138d (same builder, same asks).

Both arms boot on VERBATIM copies of the sealed 138d M6 doorway-built 15k
notebook (artifacts/fable-agent138d-20260922/work-speed2/nb138d -- the same
FACT records the rebuild would produce; reuse documented as a deviation that
only saves wall-clock). Each arm runs in its OWN process (so the 170 leaf
rebinding can never touch the 138d arm). 25 asks = sealed s1 cases
(facts[(k*37)%len], as M6). Bar: loop170 p50 < 50 ms, p99 < 200 ms, every
reply byte-identical to loop138d's reply on the same ask.
"""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(q * len(s))))]


def run_arm(agent: str, cases: Path, src: Path, work: Path, out: Path,
            env) -> dict:
    if work.exists():
        shutil.rmtree(work)
    cmd = [sys.executable, "-B", str(SCRIPTS / "fable_fix170_replay.py"),
           "--agent", agent, "--cases", str(cases), "--src", str(src),
           "--work", str(work), "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env,
                       cwd=str(ROOT))
    if r.returncode != 0:
        raise RuntimeError(f"arm {agent} failed:\n{r.stdout}\n{r.stderr}")
    return json.loads(out.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    import argparse
    import os
    ap = argparse.ArgumentParser(description="Exp 170 S1")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--src", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--base-ms-p50", type=float, default=5383.0)
    args = ap.parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    res = {}
    for agent in ("loop138d", "loop170"):
        res[agent] = run_arm(
            agent, Path(args.cases), Path(args.src),
            outdir / f"work-{agent}", outdir / f"s1-{agent}.json", env)
    b, m = res["loop138d"], res["loop170"]
    assert b["replies"] is not None and len(b["replies"]) == 25
    assert m["replies"] is not None and len(m["replies"]) == 25
    diffs = [i for i in range(25) if b["replies"][i] != m["replies"][i]]
    summary = {
        "n": 25,
        "loop138d_p50": round(pct(b["ask_ms"], 0.5), 2),
        "loop138d_p99": round(pct(b["ask_ms"], 0.99), 2),
        "loop170_p50": round(pct(m["ask_ms"], 0.5), 2),
        "loop170_p99": round(pct(m["ask_ms"], 0.99), 2),
        "loop138d_s": b["seconds"],
        "loop170_s": m["seconds"],
        "n_diffs": len(diffs),
        "diff_idx": diffs,
        "pass": (len(diffs) == 0 and pct(m["ask_ms"], 0.5) < 50.0
                 and pct(m["ask_ms"], 0.99) < 200.0),
    }
    (outdir / "s1-summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1), flush=True)
    for i in diffs:
        print(f"DIFF ask {i}: base={b['replies'][i]!r} "
              f"loop170={m['replies'][i]!r}", flush=True)
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
