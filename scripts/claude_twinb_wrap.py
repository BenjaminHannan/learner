#!/usr/bin/env python3
"""Run any month-end runner with the fixed plain twin (scripts/claude_e2e336_twinb.py) in place of
the old one. New file only; the runner itself is not changed.

  python -B scripts/claude_twinb_wrap.py scripts/claude_chat338_run.py --panel ... --arm T ...
  python -B scripts/claude_twinb_wrap.py scripts/claude_cre333_run.py ... --arm T ...
  python -B scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --arm twin ...

It swaps claude_e2e336_twin.Twin336 and claude_e2e336_twin.build for the twin b versions before the
runner starts, prints one line saying so, then runs the runner as __main__ with the remaining args.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if os.name == "nt":                     # Windows (BensPC): stand-in for the Unix-only resource module
    sys.path.insert(0, str(HERE / "winshim"))

import claude_e2e336_twin as OLD      # noqa: E402
import claude_e2e336_twinb as NEW     # noqa: E402

OLD.Twin336 = NEW.Twin336b
OLD.build = NEW.build


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_twinb_wrap.py <runner.py> [runner args]")
    target = sys.argv[1]
    sys.argv = [target] + sys.argv[2:]
    print("twinb: the plain twin is Twin336b (enable_thinking=False)", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
