#!/usr/bin/env python3
"""rsn-358g (sleep research thread, 2026-09-26): rsn-358a v2 (scripts/claude_rsn358a2_run.py, wraps
scripts/claude_rsn358a_run.py) with ONE change, a data fix to the Latin grids.

The bug (outside review, Ben 11:51 UTC; confirmed in code): each grid picks random symbol names
(claude_rsn358a_envs.latin_item), and sometimes every copy of one symbol is blanked, so the model cannot know which
name to write while the checker demands it (fresh 300 per size: 67 at 4x4, 45 at 5x5, 21 at 6x6, 12 at 7x7). Two
puzzles can look identical to the model and need different answers.
The fix: under the puzzle, one blank separator row, then a LEGEND row listing the puzzle's s symbol names (in a random
order, given, never written). The answer cells, the checker (it reads only the top s rows) and the puzzles themselves
are unchanged. Sums and number puzzles are untouched. Because the old sealed grid tests have the bug, fresh test files
are made with the fixed items from the same seeds (artifacts/claude-rsn358g-20260926/tests/; sums and numbers tests
come out identical to 358a's).

  python -B scripts/claude_rsn358g_run.py make-tests --out artifacts/claude-rsn358g-20260926/tests
  python -B scripts/claude_rsn358g_run.py train|eval|smoke ...   (same arguments as claude_rsn358a_run.py)
  python -B scripts/claude_rsn358g_run.py audit     (every grid's symbols visible, checker unchanged)
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402
import claude_rsn358a2_run as V  # noqa: E402,F401  (installs the v2 stop rule into R)

_latin_item_v1 = E.latin_item


def latin_item(rng, sol, puz):
    it = _latin_item_v1(rng, sol, puz)
    s = it.size
    legend = [E.SYM + n for n in it.meta["names"]]
    rng.shuffle(legend)
    tokens = it.tokens + [[E.BLANK] * s, legend]
    slot = it.slot + [[0] * s, [0] * s]
    target = it.target + [[0] * s, [0] * s]
    return E.Item("grids", s, tokens, slot, target, it.meta)


E.latin_item = latin_item


def audit(n=300):
    for s in (4, 5, 6, 7):
        rng = random.Random(99)
        hidden, ok = 0, 0
        for _ in range(n):
            it = E.latin_item(rng, *E.make_latin_base(rng, s))
            visible = {t for row in it.tokens for t in row if t >= E.SYM}
            need = {t for row in it.target for t in row if t}
            hidden += not need <= visible
            ok += E.check(it, it.target)
        assert hidden == 0 and ok == n, (s, hidden, ok)
        print(f"{s}x{s}: {n}/{n} puzzles show every needed symbol; checker accepts the stored answer on {ok}/{n}")


if __name__ == "__main__":
    if sys.argv[1:] == ["audit"]:
        audit()
    else:
        R.main()
