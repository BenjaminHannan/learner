#!/usr/bin/env python3
"""Exp 170 S3 driver -- exactly-once kill-9 burst on the loop170 daemon.

Same shape as scripts/fable_loop138d_soak.py (scripts/fable_soak108_run.py
BY IMPORT with RUN pointed at the agent script; no sealed file modified):
3,000 turns, seed 931, 10 aimed mid-turn kill-9s, 0 graceful stops. Bars:
0 duplicate / 0 lost / 0 wrong replies (exactly-once) AND K4 p99 <= 300 ms.
Outputs into artifacts/fable-speed170-20260922/soak170/.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_soak108_run as S108  # noqa: E402 (soak driver, read-only)

# THE daemon swap: the soak driver spawns this instead of daemon108.
S108.RUN = SCRIPTS / "fable_loop170_agent.py"

ART170 = SCRIPTS.parent / "artifacts" / "fable-speed170-20260922"


def main() -> int:
    return S108.main(["--turns", "3000", "--seed", "931", "--kills", "10",
                      "--graceful", "0", "--aim-midturn",
                      "--artifact-dir", str(ART170 / "soak170")])


if __name__ == "__main__":
    sys.exit(main())
