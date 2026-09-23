#!/usr/bin/env python3
"""Experiment 43K: 43J with ONE change — the base skills are practised on lengths 4–12 instead of 4–8.

43J showed the learned odd/even counters work, but SWAP's clue scores were only pinned down for
lengths 4–8 and misread one place at lengths 9 and 12.  The sealed reading rule said the next step
is a data change.  Here every base training input has a length drawn evenly from 4..12 (same
number of examples, same updates, same model as 43J's registered arm).  Lengths 9–12 are therefore
no longer a test; the length test moves out to 16, 20, 24, 32 and 64.
Sleep (CARDFOLD from 20 episodes of length 4–8) is unchanged.  Imports 43G/43I/43J read-only.
"""

from __future__ import annotations

import fable_learnedparity43j as J                     # installs the 43J model as T.Transport
import fable_transport43g as T

C, G = T.C, T.G
WIDE_LENGTHS = tuple(range(4, 13))
G.EVAL_LENGTHS = (4, 5, 6, 7, 8, 9, 10, 12, 16, 20, 24, 32, 64)
T.LONG_LENGTHS = (12, 16)                               # CARDFOLD long test unchanged from 43H–43J


def wide_base_step(seed: int, step: int, splits) -> tuple:
    rng = C.make_rng(f"base43k/data/{step}", seed)
    forbidden = splits.reserved_short_inputs()
    rows = []
    for op, program in C.OLD_PROGRAMS:
        for _ in range(C.BATCH_SIZE // len(C.OLD_PROGRAMS)):
            while True:
                x = C.random_digit_string(rng, rng.choice(WIDE_LENGTHS))
                if x not in forbidden:
                    break
            rows.append(C.Example(op, x, C.apply_program(program, x)))
    rng.shuffle(rows)
    return tuple(rows)


C.base_step_examples = wide_base_step

if __name__ == "__main__":
    T.main()
