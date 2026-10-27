#!/usr/bin/env python3
"""rsn-357 runner: practise three-step, test four-step (road map R7; round 1's C1 with the shared input).

Base: rsn-355's shared chain-step input (claude_rsn355_run) with room for 4 chain steps (MAX_HOPS 3 -> 4,
possible only with the shared input). ONE change in practice: three-step questions join practice (value3
replaces 1 in 8 practice puzzles, copy and practice phases). Four-step is never practised; it is the new
"one step past practice" test (scripts/claude_rsn357_four.py). Everything else is 296's recipe.

  --arm plain  296's plain net (6x640)
  --arm loop   the loop net with rsn-353's fix (no per-pass step embedding), random 2-12 rounds in
               training, 12 at evaluation (dev also scores 6, 12, 20)

  python claude_rsn357_run.py train --arm plain|loop --seed 1 --out DIR
  python claude_rsn357_run.py dev|eval ...   (same arguments as claude_rsn294_run.py)
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn294_core as C  # noqa: E402

C.MAX_HOPS = 4                                   # before anything is built or encoded
import claude_rsn296_gen  # noqa: E402,F401  (296's generator)
import claude_rsn355_run  # noqa: E402,F401  (shared chain-step input; reads C.MAX_HOPS at run time)
import claude_rsn353_run  # noqa: E402,F401  (loop: no per-pass step embedding; plain unaffected)

_base = C.gen_episode


def gen357(rng, kind=None, hops=None, n_rows=None, **kw):
    if kind is not None and rng.random() < 1 / 8:
        kind, hops = "value3", None
    return _base(rng, kind, hops, n_rows, **kw)


if len(sys.argv) > 1 and sys.argv[1] == "train":
    C.gen_episode = gen357

if __name__ == "__main__":
    runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
