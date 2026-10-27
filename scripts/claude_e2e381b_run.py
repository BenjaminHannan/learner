#!/usr/bin/env python3
"""The 336 runner with the 381b harness (stricter "is that right?" answers). New file; the 336 runner is unchanged.

  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e381b_run.py <same args as claude_e2e336_run.py>
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import claude_e2e336_run as R          # noqa: E402
import claude_e2e381b_harness as H      # noqa: E402

if __name__ == "__main__":
    H.install381b()
    print("381b: confirm answers use claude_e2e381b_harness.confirm_answer381b", flush=True)
    sys.exit(R.main())
