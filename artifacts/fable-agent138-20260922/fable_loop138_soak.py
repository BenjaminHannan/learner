#!/usr/bin/env python3
"""Exp 138 A5 driver -- exactly-once G2 kill-9 burst on the loop138 daemon.

Reuses scripts/fable_soak108_run.py BY IMPORT with RUN pointed at
scripts/fable_loop138_agent.py (same mailbox CLI: --dir + --idle-seconds);
no sealed file is modified. G2 pattern: 6,000 turns, seed 931, 10 aimed
mid-turn kill-9s, 0 graceful stops. Bar: 0 duplicate / 0 lost / 0 wrong
replies (driver audits notebook + receipts + doubled sentences).

Outputs into artifacts/fable-agent138-20260922/soak138-g2/. Run (Mac CPU,
offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B artifacts/fable-agent138-20260922/fable_loop138_soak.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_soak108_run as S108  # noqa: E402 (soak driver, read-only)

# THE daemon swap: the soak driver spawns this instead of daemon108.
S108.RUN = SCRIPTS / "fable_loop138_agent.py"

ART138 = SCRIPTS.parent / "artifacts" / "fable-agent138-20260922"


def main() -> int:
    return S108.main(["--turns", "6000", "--seed", "931", "--kills", "10",
                      "--graceful", "0", "--aim-midturn",
                      "--artifact-dir", str(ART138 / "soak138-g2")])


if __name__ == "__main__":
    sys.exit(main())
