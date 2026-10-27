#!/usr/bin/env python3
"""Exp 128 C4: seed-93 20,000-turn soak through the fast exactly-once daemon."""
from __future__ import annotations
import sys
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import fable_soak108_run as S108

S108.RUN = SCRIPTS / "fable_perf128_daemon.py"

if __name__ == "__main__":
    sys.exit(S108.main())
