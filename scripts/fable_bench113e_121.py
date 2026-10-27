#!/usr/bin/env python3
"""Experiment 113e E3-121: new bench121 split, loop113c vs loop113e.

Reuse of scripts/fable_bench113d_121.py by import with class swap (as the
exp-113e brief allows): the only changes are the after-arm daemon class
(Loop113dDaemon -> Loop113eDaemon), the after-arm config, and the artifact
directory. Protocol, scorer v2, and the before arm are untouched. Output
files are renamed to the 113e prefix after the run (own artifact dir); the
summary's after-arm key is relabelled loop113e.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench113e_121.py --run
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench113d_121 as B121D  # noqa: E402 (runner, read-only)
import fable_loop113e_agent as L113E  # noqa: E402 (this experiment's agent)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113e-20260922"

# The class swap: after-arm now builds the loop113e daemon.
B121D.Loop113dDaemon = L113E.Loop113eDaemon
B121D.DEFAULT_CONFIG113D = copy.deepcopy(L113E.DEFAULT_CONFIG113E)
B121D.ART = ART


def cmd_run(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    ret = B121D.cmd_run(_args)
    renames = [
        ("fable_bench113d_loop113c_bench121_4hop_rows.jsonl",
         "fable_bench113e_loop113c_bench121_4hop_rows.jsonl"),
        ("fable_bench113d_loop113d_bench121_4hop_rows.jsonl",
         "fable_bench113e_loop113e_bench121_4hop_rows.jsonl"),
        ("fable_bench113d_121_summary.json",
         "fable_bench113e_121_summary.json"),
    ]
    for old, new in renames:
        src, dst = ART / old, ART / new
        if src.exists():
            if dst.exists():
                dst.unlink()
            src.rename(dst)
    summary = ART / "fable_bench113e_121_summary.json"
    if summary.exists():
        text = summary.read_text(encoding="utf-8")
        summary.write_text(text.replace('"loop113d"', '"loop113e"'),
                           encoding="utf-8")
    print("renamed outputs to fable_bench113e_* (after-arm is loop113e)")
    return ret


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 113e bench121 before/after")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
