#!/usr/bin/env python3
"""Experiment 147 -- A1 registered run: sealed 143 cases, loop147-132.

Re-runs the sealed red-team by importing scripts/fable_redteam143_run.py
read-only and redirecting its ART output path to this artifact dir (case
file, judge, verdict rules unchanged); only the daemon class under test
is swapped to the loop147-on-132 variant.

Run (Mac CPU, offline; registered only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_align147_a1.py
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_redteam143_run as R143  # noqa: E402 (sealed runner, read-only)
import fable_loop147_agent132 as M147  # noqa: E402 (variant under test)

ROOT = SCRIPTS.parent
ART147 = ROOT / "artifacts" / "fable-align147-20260922"


def main() -> int:
    t0 = time.time()
    # Redirect outputs (results JSON + scratch dirs) to our artifact dir.
    # CASES_PATH keeps pointing at the sealed 143 case file (read-only).
    assert "fable-redteam143-20260922" in str(R143.CASES_PATH), R143.CASES_PATH
    R143.ART = ART147 / "a1"
    R143.Loop132Daemon = M147.Loop147on132Daemon
    R143.DEFAULT_CONFIG132 = copy.deepcopy(M147.DEFAULT_CONFIG147_132)
    rc = R143.main()
    seconds = round(time.time() - t0, 1)
    print(f"A1 registered run done in {seconds} s -> {ART147 / 'a1'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
