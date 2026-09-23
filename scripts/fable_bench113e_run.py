#!/usr/bin/env python3
"""Experiment 113e E2-bench: loop113c (before) vs loop113e (after), scorer v2.

Reuse of scripts/fable_bench113d_run.py by import with class swap (as the
exp-113e brief allows): the only changes are the after-arm daemon class
(Loop113dDaemon -> Loop113eDaemon), the after-arm config, and the artifact
directory. Splits, scorer v2, teach-verbatim protocol, and the before arm
are untouched. Output files are renamed to the 113e prefix after the run
(own artifact dir); the summary's after-arm key is relabelled loop113e.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench113e_run.py --run
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench113d_run as B113D  # noqa: E402 (runner, read-only)
import fable_loop113e_agent as L113E  # noqa: E402 (this experiment's agent)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113e-20260922"

# The class swap: after-arm now builds the loop113e daemon.
B113D.Loop113dDaemon = L113E.Loop113eDaemon
B113D.DEFAULT_CONFIG113D = copy.deepcopy(L113E.DEFAULT_CONFIG113E)
B113D.ART = ART


def _relabel(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace('"loop113d"', '"loop113e"')
    path.write_text(text, encoding="utf-8")


def cmd_run(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    ret = B113D.cmd_run(_args)
    renames = [
        ("loop113d-config.json", "loop113e-config.json"),
        ("fable_bench113d_summary.json", "fable_bench113e_summary.json"),
    ]
    for tag in ("fable_edit_200", "s2fresh_4hop"):
        renames.append((f"fable_bench113d_loop113c_{tag}_rows.jsonl",
                        f"fable_bench113e_loop113c_{tag}_rows.jsonl"))
        renames.append((f"fable_bench113d_loop113d_{tag}_rows.jsonl",
                        f"fable_bench113e_loop113e_{tag}_rows.jsonl"))
    for old, new in renames:
        src, dst = ART / old, ART / new
        if src.exists():
            if dst.exists():
                dst.unlink()
            src.rename(dst)
    # Relabel the after-arm key inside the 113e summary (own file).
    _relabel(ART / "fable_bench113e_summary.json")
    print("renamed outputs to fable_bench113e_* (after-arm is loop113e)")
    return ret


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 113e before/after bench")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
