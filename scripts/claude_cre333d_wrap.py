#!/usr/bin/env python3
"""Run the 333 runner with 333d swapped in (and twin b). New file only; the runner is not changed.

  python -B scripts/claude_cre333d_wrap.py scripts/claude_cre333_run.py --panel ... --arm P|T ...

Swaps: claude_cre333_agent.Gen333 -> Gen333b (thinking off; it is also the model 338's Gen338 shares);
claude_cre333_agent.install_creative333(agent, gen) -> install_creative333d(agent, Gen338(share=gen));
claude_e2e336_twin -> twin b. Prints one line naming the swap, then runs the runner.
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

import claude_chat338_agent as C38       # noqa: E402
import claude_cre333_agent as C          # noqa: E402
import claude_cre333b_agent as CB        # noqa: E402
import claude_cre333d_agent as CD        # noqa: E402
import claude_e2e336_twin as OLD         # noqa: E402
import claude_e2e336_twinb as NEW        # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_cre333d_wrap.py <runner.py> [runner args]")
    target = sys.argv[1]
    C.Gen333 = CB.Gen333b
    C.install_creative333 = lambda agent, gen: CD.install_creative333d(agent, C38.Gen338(share=gen))
    OLD.Twin336, OLD.build = NEW.Twin336b, NEW.build
    sys.argv = [target] + sys.argv[2:]
    print("cre333d: Gen333b (thinking off), install_creative333d (338-style generation, 333c routing); twin b",
          flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
