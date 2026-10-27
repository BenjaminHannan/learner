#!/usr/bin/env python3
"""Entry point for slp-366 (added after run 1 was VOID).

The sealed scorecard defines marks366() below its `if __name__ == "__main__"` block, so running the file directly
crashes at the scoring line after all nights have run (NameError), before any result is written or printed.
This wrapper imports the sealed module (so every function is defined) and calls its main(). Nothing else changes.
  python3 -B scripts/claude_slp366_main.py --out artifacts/claude-slp366-20260925/results.json --workers 4
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_slp366_scorecard as S  # noqa: E402

if __name__ == "__main__":
    sys.exit(S.main())
