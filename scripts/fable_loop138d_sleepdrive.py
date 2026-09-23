#!/usr/bin/env python3
"""Exp 138d M5 driver -- Z1-Z5 + E-family sleep checks with sleep145.

Same shape as artifacts/fable-agent138-20260922/fable_loop138_sleepdrive.py
(scripts/fable_sleep104_drive.py + scripts/fable_sleep116_drive.py BY
IMPORT plus a daemon-class swap; no sealed file modified): D104.PY points
at scripts/fable_loop138d_agent.py, whose L3 is the sleep145 retrofit
(grow-slot + taught-beats-sleep) in place of sleep131.

  z104 : full exp-104 wave (seeds 1-3 + Z4 + Z5 noise4/noise8).
  e116 : full exp-116 redteam wave (E1-E4 taughtwin + the other 33).

Bar: installs happen, 0 wrong installs, taught wins (E2/E3/E4 answer with
source taught). Outputs into artifacts/fable-agent138d-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_sleepdrive.py --only z104
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_sleep104_drive as D104  # noqa: E402 (mailbox helpers, read-only)
import fable_sleep116_drive as D116  # noqa: E402 (redteam logic, read-only)

# THE daemon class swap: every spawn in D104/D116 boots Loop138bDaemon.
D104.PY = [sys.executable, "-B", str(SCRIPTS / "fable_loop138d_agent.py")]

ART138B = SCRIPTS.parent / "artifacts" / "fable-agent138d-20260922"


def run_e116() -> int:
    return D116.main(["--root", str(ART138B / "runs-116"),
                      "--report", str(ART138B / "wave-report-116.json")])


def run_z104() -> int:
    return D104.main(["--root", str(ART138B / "runs-104"),
                      "--report", str(ART138B / "wave-report-104.json")])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 138d M5 sleep wave")
    ap.add_argument("--only", default="e116,z104")
    args = ap.parse_args(argv)
    want = set(c.strip() for c in args.only.split(",") if c.strip())
    rc = 0
    if "e116" in want:
        rc |= run_e116()
    if "z104" in want:
        rc |= run_z104()
    return rc


if __name__ == "__main__":
    sys.exit(main())
