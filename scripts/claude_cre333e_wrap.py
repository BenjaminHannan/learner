#!/usr/bin/env python3
"""Run the 333 runner with 333e swapped in (and twin b). New file only; the runner is not changed.

  CRE333E_ARM=e1|e2 CRE333E_HEAD=<head333e.json> python -B scripts/claude_cre333e_wrap.py scripts/claude_cre333_run.py \
      --panel ... --arm P|T ...

Swaps: claude_cre333_agent.Gen333 -> Gen333b (thinking off; shared by 338's Gen338 and the router);
claude_cre333_agent.install_creative333(agent, gen) -> install_creative333e(agent, Gen338(share=gen),
Router333e(gen, head), with_history = arm == "e2"); claude_e2e336_twin -> twin b. Prints one line naming the swap.
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
import claude_cre333e_agent as CE        # noqa: E402
import claude_e2e336_twin as OLD         # noqa: E402
import claude_e2e336_twinb as NEW        # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_cre333e_wrap.py <runner.py> [runner args]")
    arm, head = os.environ.get("CRE333E_ARM", ""), os.environ.get("CRE333E_HEAD", "")
    if arm not in ("e1", "e2") or not Path(head).is_file():
        raise SystemExit("set CRE333E_ARM=e1|e2 and CRE333E_HEAD=<head333e.json>")
    target = sys.argv[1]
    C.Gen333 = CB.Gen333b
    C.install_creative333 = lambda agent, gen: CE.install_creative333e(
        agent, C38.Gen338(share=gen), CE.Router333e(gen, head), with_history=(arm == "e2"))
    OLD.Twin336, OLD.build = NEW.Twin336b, NEW.build
    sys.argv = [target] + sys.argv[2:]
    print(f"cre333e: arm {arm}, head {head}; Gen333b (thinking off), tool-call router, "
          f"{'writer sees the chat' if arm == 'e2' else '333d writer (no chat)'}; twin b", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
