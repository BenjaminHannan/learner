#!/usr/bin/env python3
"""Exp 138d M5-soak driver -- exactly-once kill-9 burst on the loop138d daemon.

Same G2 pattern as artifacts/fable-agent138b-20260922/fable_loop138b_soak.py
(scripts/fable_soak108_run.py BY IMPORT with RUN pointed at the agent
script; no sealed file modified): 3,000 turns (shorter than 138b's 6,000;
stated here), seed 931, 10 aimed mid-turn kill-9s, 0 graceful stops. Bar:
0 duplicate / 0 lost / 0 wrong replies. The daemon serves only settled
files and skips tmp/dot files (141 rule), which is what this burst
exercises. Outputs into artifacts/fable-agent138d-20260922/soak138d-g2/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_soak.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_soak108_run as S108  # noqa: E402 (soak driver, read-only)

# THE daemon swap: the soak driver spawns this instead of daemon108.
S108.RUN = SCRIPTS / "fable_loop138d_agent.py"

ART138D = SCRIPTS.parent / "artifacts" / "fable-agent138d-20260922"


def main() -> int:
    return S108.main(["--turns", "3000", "--seed", "931", "--kills", "10",
                      "--graceful", "0", "--aim-midturn",
                      "--artifact-dir", str(ART138D / "soak138d-g2")])


if __name__ == "__main__":
    sys.exit(main())
