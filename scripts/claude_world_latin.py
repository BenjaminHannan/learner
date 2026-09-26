#!/usr/bin/env python3
"""Shared puzzle world: number squares (Latin squares) in a one-line text form (sleep research thread, 2026-09-26).

Offered to the Creative thread for its blurt -> checker -> night loop, and the same kind the loop reasoner and the
chat-puzzle gate (358b3) use, so hits found by one thread are usable by the other.
  item = make(seed, size, blanks): a random s x s square (row, column and symbol shuffles of the cyclic square) with
  `blanks` cells hidden. The difficulty knobs are size (3-6) and blanks.
  prompt: one line, rows separated by " / ", "_" for blanks; the reply is the finished square in the same form.
  check(item, reply): exact code check. Any square that keeps every clue and has 1..s once in every row and column
  counts, so squares with several answers are fine.
  Reply mode "blanks" (added 2026-09-26 for Creative's DEV finding that the 1B won't copy the square back):
  prompt_blanks(item) asks for only the missing numbers, left to right and top to bottom; check_blanks(item, reply)
  needs EXACTLY as many numbers in the reply as there are blanks, fills them in reading order and calls check().
  (Claude-written prompt frames: test prompts only. Training on them needs GLM wording, Ben 16:39.)
Seeds: the Creative thread owns 900000-999999; the sleep research thread never uses them.

  python -B scripts/claude_world_latin.py selftest
  python -B scripts/claude_world_latin.py sample --size 4 --blanks 6 --seed 900001
"""
from __future__ import annotations

import argparse
import random
import re


def make(seed, size, blanks):
    rng = random.Random(f"latin:{size}:{blanks}:{seed}")
    s = size
    rows, cols, syms = rng.sample(range(s), s), rng.sample(range(s), s), rng.sample(range(1, s + 1), s)
    sol = [[syms[(rows[r] + cols[c]) % s] for c in range(s)] for r in range(s)]
    hide = set(rng.sample(range(s * s), min(blanks, s * s)))
    puz = [[0 if r * s + c in hide else sol[r][c] for c in range(s)] for r in range(s)]
    text = " / ".join(" ".join(str(v) if v else "_" for v in row) for row in puz)
    prompt = (f"Fill each _ so every row and every column of this {s}x{s} square holds 1 to {s} once: {text}. "
              f"Reply with the finished square only, rows separated by \" / \".")
    return {"seed": seed, "size": s, "blanks": len(hide), "puz": puz, "sol": sol, "prompt": prompt}


def parse(reply, s):
    """the first run of s rows of s numbers; rows split by "/" or new lines"""
    rows = []
    for part in re.split(r"[/\n]", reply):
        cells = re.findall(r"\d+", part)
        if len(cells) == s and all(1 <= int(x) <= s for x in cells):
            rows.append([int(x) for x in cells])
            if len(rows) == s:
                return rows
        elif rows:
            rows = []
    return None


def check(item, reply):
    s, puz, g = item["size"], item["puz"], parse(reply, item["size"])
    if g is None:
        return False
    full = set(range(1, s + 1))
    return (all(puz[r][c] in (0, g[r][c]) for r in range(s) for c in range(s))
            and all(set(row) == full for row in g) and all({g[r][c] for r in range(s)} == full for c in range(s)))


def prompt_blanks(item):
    s = item["size"]
    text = " / ".join(" ".join(str(v) if v else "_" for v in row) for row in item["puz"])
    return (f"In this {s}x{s} square every row and every column must hold 1 to {s} once: {text}. "
            f"Reply with only the missing numbers, left to right and top to bottom, separated by spaces.")


def check_blanks(item, reply):
    puz, vals = item["puz"], [int(x) for x in re.findall(r"\d+", reply)]
    if len(vals) != sum(v == 0 for row in puz for v in row):
        return False
    it = iter(vals)
    return check(item, " / ".join(" ".join(str(v if v else next(it)) for v in row) for row in puz))


def selftest():
    seen = set()
    for size in (3, 4, 5, 6):
        for seed in range(900000, 900300):
            it = make(seed, size, size * size // 2)
            ans = " / ".join(" ".join(map(str, row)) for row in it["sol"])
            assert check(it, ans) and check(it, "Sure:\n" + ans.replace(" / ", "\n")), (size, seed)
            bad = [row[:] for row in it["sol"]]
            bad[0][0], bad[0][1] = bad[0][1], bad[0][0]
            assert not check(it, " / ".join(" ".join(map(str, r)) for r in bad))
            seen.add(it["prompt"])
            fill = [it["sol"][r][c] for r in range(size) for c in range(size) if it["puz"][r][c] == 0]
            assert check_blanks(it, "The missing numbers: " + ", ".join(map(str, fill)) + ".")
            assert not check_blanks(it, " ".join(map(str, fill[:-1])))                   # one short
            assert not check_blanks(it, " ".join(map(str, fill + [1])))                  # one extra
            bad = fill[:]
            bad[0] = bad[0] % size + 1                                                   # one cell changed
            assert not check_blanks(it, " ".join(map(str, bad)))
    assert len(seen) >= 1150, len(seen)
    print(f"selftest ok: {len(seen)} distinct prompts in 1,200; the solution checks; a swapped pair fails; "
          f"blanks mode needs exactly the blank count")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("sample"); p.add_argument("--size", type=int, default=4)
    p.add_argument("--blanks", type=int, default=6); p.add_argument("--seed", type=int, default=900000)
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        it = make(a.seed, a.size, a.blanks)
        print(it["prompt"])
