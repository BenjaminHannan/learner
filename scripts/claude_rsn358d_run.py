#!/usr/bin/env python3
"""rsn-358d (sleep research thread, 2026-09-26 03:30 UTC, written after 358a's registered FAIL): rsn-358a v2
(scripts/claude_rsn358a2_run.py, wraps scripts/claude_rsn358a_run.py) with ONE change, the 4-number practice puzzles.

Why: in 358a both arms solved 100% of practice number puzzles and ~0 of the 300 held-out 4-number hands (1-4 of 300)
and 5-number hands (0-2): with only 1,062 fixed 4-number practice puzzles (target always 24) they memorised them
instead of learning to search. Here the 4-number practice is every 4-number hand (numbers 1-13) that is NOT one of
the 300 held-out test hands (those hands are excluded with every target), paired with EVERY whole target 1-99 it
can reach (about 70x more distinct puzzles). 3-number practice, sums, grids, nets, steps, tests, stop rule (v2) and
marks are unchanged. The tests still ask target 24 (held-out 4-number hands, fresh 5-number hands).

  python -B scripts/claude_rsn358d_run.py train|eval|smoke ...   (same arguments as claude_rsn358a_run.py)
  python -B scripts/claude_rsn358d_run.py pool                    (prints pool size and checks exclusions)
"""
from __future__ import annotations

import itertools
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402
import claude_rsn358a2_run as V  # noqa: E402,F401  (installs the v2 stop rule into R)

_init_v1 = R.Source.__init__


def all_values(items):
    """{value: one expression} for every value reachable using all items (same expression format as B1.solve)."""
    if len(items) == 1:
        return {items[0][0]: items[0][1]}
    out = {}
    for i, j in itertools.combinations(range(len(items)), 2):
        rest = [items[k] for k in range(len(items)) if k not in (i, j)]
        for v in B1._combine(items[i], items[j]):
            for val, expr in all_values(rest + [v]).items():
                out.setdefault(val, expr)
    return out


def four_pool():
    four, _ = E.number_hands()
    _, held = E.split_four(four)
    held_hands = {tuple(sorted(h)) for h, _, _ in held}
    pool = []
    for h in itertools.combinations_with_replacement(range(1, 14), 4):
        if h in held_hands:
            continue
        vals = all_values([(Fraction(n), str(n)) for n in h])
        for t in range(1, 100):
            s = vals.get(Fraction(t))
            if s is not None and B1.check(s, list(h), t):
                pool.append((list(h), t, s))
    return pool, held_hands


_POOL = {}


def _init(self, seed, latin_pool=20000):
    _init_v1(self, seed, latin_pool)
    if "four" not in _POOL:
        _POOL["four"] = four_pool()[0]
    self.four = _POOL["four"]


R.Source.__init__ = _init

if __name__ == "__main__":
    if sys.argv[1:] == ["pool"]:
        pool, held = four_pool()
        assert not any(tuple(sorted(h)) in held for h, _, _ in pool)
        print(f"pool {len(pool)} four-number puzzles over {len({tuple(h) for h, _, _ in pool})} hands; "
              f"{len(held)} held-out hands excluded; target-24 puzzles in pool: {sum(t == 24 for _, t, _ in pool)}")
    else:
        R.main()
