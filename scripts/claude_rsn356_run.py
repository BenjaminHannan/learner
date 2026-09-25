#!/usr/bin/env python3
"""rsn-356 runner: exactly rsn-296's runner (varied generator, plain arm 6x640, steps, batches, lr,
reward, fact-check, seeds, eval), with ONE change in TRAINING only: practice puzzles come with
one-fact twins (scripts/claude_rsn356_twins.py, mode "delete").

  --twins paired    after each puzzle that has a clean twin, the next puzzle is ITS twin (same notebook
                    with one needed row deleted, so the right answer changes). The pair lands side by
                    side in the same batch, so a lazy trick that gives the same answer to both loses.
  --twins unpaired  the control: after each such puzzle, the next puzzle is the twin of a DIFFERENT,
                    freshly made puzzle (which is thrown away). Same mix of puzzle types and answers
                    (the same extra "I don't know" and one-fewer puzzles), but never shown as a pair.

The comparison is paired vs unpaired (same job, same machine), so a gain can only come from pairing,
not from the extra kinds of puzzles. dev and eval are unchanged (no twins).

  python claude_rsn356_run.py train --twins paired --arm plain --seed 1 --out DIR
  python claude_rsn356_run.py dev|eval ...   (same arguments as claude_rsn294_run.py)
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen  # noqa: E402,F401  (replaces claude_rsn294_core.gen_episode, as in 296)
import claude_rsn356_twins as T  # noqa: E402

MODE = None
if "--twins" in sys.argv:
    i = sys.argv.index("--twins")
    MODE = sys.argv[i + 1]
    del sys.argv[i:i + 2]
    if MODE not in ("paired", "unpaired"):
        raise SystemExit("--twins must be paired or unpaired")
if len(sys.argv) > 1 and sys.argv[1] == "train" and MODE is None:
    raise SystemExit("rsn-356 train needs --twins paired|unpaired")

_base = C.gen_episode
_stash = []


def gen356(rng, kind=None, hops=None, n_rows=None, **kw):
    if _stash:
        return _stash.pop()
    ep = _base(rng, kind, hops, n_rows, **kw)
    src = ep if MODE == "paired" else _base(rng, kind, hops, n_rows, **kw)
    tw = T.make_twin(src, rng, "delete")
    if tw is not None:
        _stash.append(tw)
    return ep


if MODE is not None and len(sys.argv) > 1 and sys.argv[1] == "train":
    C.gen_episode = gen356

if __name__ == "__main__":
    runpy.run_path(str(HERE / "claude_rsn294_run.py"), run_name="__main__")
