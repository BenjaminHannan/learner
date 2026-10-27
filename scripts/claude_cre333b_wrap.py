#!/usr/bin/env python3
"""Run a month-end runner with 333b or 333c swapped in (and the fixed twin b). New file only.

  python -B scripts/claude_cre333b_wrap.py b scripts/claude_cre333_run.py --panel ... --arm P ...
  python -B scripts/claude_cre333b_wrap.py c scripts/claude_cre333_run.py --panel ... --arm P ...

b: claude_cre333_agent.Gen333 -> Gen333b (thinking off).
c: b plus claude_cre333_agent.is_creative -> is_creative333c (cue AND request AND not recall).
Both: claude_e2e336_twin.Twin336/build -> twin b. Prints one line naming the swap, then runs the runner.
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if os.name == "nt":
    sys.path.insert(0, str(HERE / "winshim"))

import claude_cre333_agent as C          # noqa: E402
import claude_cre333b_agent as CB        # noqa: E402
import claude_e2e336_twin as OLD         # noqa: E402
import claude_e2e336_twinb as NEW        # noqa: E402


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("b", "c"):
        raise SystemExit("usage: claude_cre333b_wrap.py b|c <runner.py> [runner args]")
    variant, target = sys.argv[1], sys.argv[2]
    C.Gen333 = CB.Gen333b
    if variant == "c":
        C.is_creative = CB.is_creative333c
    OLD.Twin336, OLD.build = NEW.Twin336b, NEW.build
    sys.argv = [target] + sys.argv[3:]
    print(f"cre333{variant}: Gen333b (thinking off)"
          + (", is_creative333c" if variant == "c" else "") + "; twin b", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
