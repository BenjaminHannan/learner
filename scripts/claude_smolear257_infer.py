#!/usr/bin/env python3
"""Exp 257 -- run the 235b inference driver (greedy + k=4 beams + gate) UNCHANGED, with the
brake pointed at relation table v2 (claude_smolear257_table.install()). Same arguments as
claude_smolear235b_infer.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235b_infer as I  # noqa: E402

if __name__ == "__main__":
    I.main()
