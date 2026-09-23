#!/usr/bin/env python3
"""Exp 138d M5 completion -- retry Z4 + run Z5 (noise4/noise8) standalone.

Same daemon swap as scripts/fable_loop138d_sleepdrive.py (D104.PY pointed
at scripts/fable_loop138d_agent.py; no sealed file modified). The sealed
z104 wave crashed inside Z4 ("daemon died before the kill"), so Z4 was
FAIL-by-crash and Z5 never ran. This runs only the unfinished remainder:
--only z4,z5n4,z5n8 into the same root/report paths.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_sleepz5.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_sleep104_drive as D104  # noqa: E402 (mailbox helpers, read-only)

# THE daemon class swap: every spawn boots Loop138dDaemon.
D104.PY = [sys.executable, "-B", str(SCRIPTS / "fable_loop138d_agent.py")]

ART138D = SCRIPTS.parent / "artifacts" / "fable-agent138d-20260922"


def main() -> int:
    return D104.main(["--root", str(ART138D / "runs-104"),
                      "--report", str(ART138D / "wave-report-104.json"),
                      "--only", "z4,z5n4,z5n8"])


if __name__ == "__main__":
    sys.exit(main())
