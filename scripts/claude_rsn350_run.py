#!/usr/bin/env python3
"""rsn-350 runner: exactly rsn-296's runner (same generator, steps, batches, learning rate, reward,
fact-check, seeds, eval), with ONE change: the plain arm is about 3x bigger.

  size "90m" = PlainThinker(d=1024, layers=7, heads=16): 91,588,629 numbers
  (296's plain arm: d=640, layers=6, heads=10: 30,938,261 numbers, ratio 2.96)

  python claude_rsn350_run.py train --arm plain --size 90m --seed 1 --out DIR
  python claude_rsn350_run.py dev|eval ...   (same arguments as claude_rsn294_run.py)

Asked for by Ben (2026-09-24 19:19 UTC, sleep research thread: "can you do that btw then, the 3
times bigger model?"). Design: design/v3/30-modes/350-bigger-reasoner.md.
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen  # noqa: E402,F401  (replaces claude_rsn294_core.gen_episode, as in 296)

_base_build = C.build


def build350(arm: str, size: str = "30m"):
    if size == "90m":
        if arm != "plain":
            raise SystemExit("rsn-350: size 90m is registered for the plain arm only")
        return C.PlainThinker(1024, 7, 16)
    return _base_build(arm, size)


C.build = build350

if __name__ == "__main__":
    runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
