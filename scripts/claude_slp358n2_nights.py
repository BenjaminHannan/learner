#!/usr/bin/env python3
"""slp-358n2: slp-358n (scripts/claude_slp358n_nights.py, sealed, registered FAIL) with ONE fix to the night mix,
plus a cleaner placebo (sleep research thread, 2026-09-26).

The fix (the one change): in slp-358n a night's day-batches picked a puzzle SHAPE at random, and sums come in two
shapes (5 and 6 digits) while 5x5 grids are one, so grids got ~1/3 of the day practice and sums ~2/3 (blind recount,
artifacts/claude-slp358n-20260926/VERIFY.md). Here a day-batch first picks the KIND (sums or grids, half each), then
a shape within it. Rehearsal batches are unchanged (already half sums, half grids).

Placebo fix (the control, not the treatment): shuffling grid answers between puzzles with different blanks and
different symbol names left ~48% of answer cells blank and ~23% with foreign symbols. Now a grid placebo answer is,
for every blank cell, a random symbol from that puzzle's own symbols. The sums placebo (shuffled answers between
same-width sums) was clean and is unchanged. Everything else (nets, steps, lr, tests, scoring) is identical.

  python -B scripts/claude_slp358n2_nights.py run --seed 3 --out DIR
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_slp358n_nights as N  # noqa: E402

_shuffled_v1 = N.shuffled_answers


def night_batches(arm, day, rng, cfg):
    kinds = {}
    for it in day:
        kinds.setdefault(it.env, {}).setdefault((len(it.tokens), len(it.tokens[0])), []).append(it)
    kinds = {k: list(v.values()) for k, v in sorted(kinds.items())}
    names = sorted(kinds)
    out = []
    for _ in range(cfg["night_steps"]):
        if arm == "R" or rng.random() < 0.5:
            out.append(N.practice_batch(rng, cfg["batch"]))
        else:
            g = rng.choice(kinds[rng.choice(names)])
            out.append([rng.choice(g) for _ in range(cfg["batch"])])
    return out


def shuffled_answers(items, rng):
    sums = [it for it in items if it.env == "sums"]
    out_sums = iter(_shuffled_v1(sums, rng))
    out = []
    for it in items:
        if it.env == "sums":
            out.append(next(out_sums))
            continue
        own = [E.SYM + n for n in it.meta["names"]]
        tgt = [[rng.choice(own) if it.slot[r][c] else 0 for c in range(len(it.slot[0]))] for r in range(len(it.slot))]
        out.append(E.Item(it.env, it.size, it.tokens, it.slot, tgt, it.meta))
    return out


N.night_batches = night_batches
N.shuffled_answers = shuffled_answers

if __name__ == "__main__":
    N.main()
