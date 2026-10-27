#!/usr/bin/env python3
"""Exp 257 -- pick tau with 235b's SEALED rule (claude_smolear235b_tau.main, unchanged): most
exact-TEACH recall with wrong-save rate <= 1 %; if none qualifies, the lowest wrong-save rate,
ties -> smallest tau. The brake/gate use relation table v2. Same arguments as the 235b script."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235b_tau as T  # noqa: E402

if __name__ == "__main__":
    T.main()
