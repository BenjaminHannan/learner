#!/usr/bin/env python3
"""reframe-5: restate the puzzle, solve the easier piece, carry it back (creative research thread, 2026-09-25).

Why: Ben liked "reframing" (17:00 UTC) and the top three parts from the discoveries study (17:47 UTC;
reviews/creative-research-2026-09-25/F-discoveries.md). There, representation change broke impasses in human insight
problems (Knoblich et al., matchstick arithmetic). Working backwards ("24 = 4 x 6, so make 6 from the rest") is the
puzzle version.

One change, at test time only (no training): how the same budget of model samples is spent.
  plain   : 30 rule-keeping blurts on the puzzle itself (blurt-3's guesser, T 1.5).
  reframe : code restates the puzzle "use nums to make T" as easier sub-puzzles that each drop one number x:
            make T-x (then x + e), T+x (then e - x), x-T (then x - e), T/x (then x * e), T*x (then e / x), x/T (then
            x / e), keeping whole-number targets 1..200. The model spends the same 30 blurts on those sub-puzzles
            (round robin, in a seeded random order). A sub-puzzle hit e is carried back into a full expression and
            checked on the ORIGINAL puzzle with the same exact checker.
The model does all the guessing; code only writes the restatements and joins the pieces (labelled as such).
Measure: fresh test puzzles solved (at least one checked full answer) with 30 model samples each.

  python -B scripts/claude_reframe5.py --model M --out DIR [--test-seed 784 --n-test 80]
  python -B scripts/claude_reframe5.py --selftest
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402

TEMP = 1.5
TMAX = 200


def reframes(p):
    """Sub-puzzles that drop one number x, with a function that carries a sub-answer back."""
    out, seen = [], set()
    nums, T = p["nums"], Fraction(p["target"])
    for i, x in enumerate(nums):
        rest = nums[:i] + nums[i + 1:]
        if not rest:
            continue
        X = Fraction(x)
        cands = [(T - X, lambda e, x=x: f"{x} + ({e})"), (T + X, lambda e, x=x: f"({e}) - {x}"),
                 (X - T, lambda e, x=x: f"{x} - ({e})"), (T / X, lambda e, x=x: f"{x} * ({e})"),
                 (T * X, lambda e, x=x: f"({e}) / {x}")]
        if T != 0:
            cands.append((X / T, lambda e, x=x: f"{x} / ({e})"))
        for t2, back in cands:
            if t2.denominator != 1 or not 1 <= t2 <= TMAX:
                continue
            key = (tuple(rest), int(t2), back("E"))
            if key in seen:
                continue
            seen.add(key)
            out.append(({"id": p["id"] + f"-r{len(out)}", "nums": rest, "target": int(t2)}, back))
    return out


def solve_plain(s, p, budget):
    bl = s.generate(p, budget, TEMP)
    return sum(B1.check(t, p["nums"], p["target"]) for t in bl)


def solve_reframe(s, p, budget, rng):
    subs = reframes(p)
    if not subs:
        return 0, 0, 0
    rng.shuffle(subs)
    alloc = [budget // len(subs)] * len(subs)
    for i in range(budget - sum(alloc)):
        alloc[i % len(subs)] += 1
    full = sub_hits = used = 0
    for (q, back), k in zip(subs, alloc):
        if k == 0:
            continue
        used += k
        for e in s.generate(q, k, TEMP):
            if B1.check(e, q["nums"], q["target"]):
                sub_hits += 1
                full += B1.check(back(e), p["nums"], p["target"])
    return full, sub_hits, used


def run(a):
    t0 = time.time()
    s = B2.Solver(a.model)
    test = B2.puzzles(a.test_seed, a.n_test)
    dev = {(tuple(p["nums"]), p["target"]) for p in
           (json.loads(x) for x in Path(a.dev_puzzles).read_text().splitlines() if x)} if a.dev_puzzles else set()
    test = [p for p in test if (tuple(p["nums"]), p["target"]) not in dev]
    rng = random.Random(a.test_seed)
    res = {"n_test": len(test), "budget": a.n, "temp": TEMP}
    for k in ("plain_solved", "plain_hits", "reframe_solved", "reframe_full_hits", "reframe_sub_hits",
              "reframe_samples", "solved_3num_plain", "solved_3num_reframe", "solved_4num_plain",
              "solved_4num_reframe", "n_3num", "n_4num"):
        res[k] = 0
    for p in test:
        h = solve_plain(s, p, a.n)
        f, sh, used = solve_reframe(s, p, a.n, rng)
        tag = "3num" if len(p["nums"]) == 3 else "4num"
        res[f"n_{tag}"] += 1
        res["plain_hits"] += h
        res["plain_solved"] += h > 0
        res[f"solved_{tag}_plain"] += h > 0
        res["reframe_full_hits"] += f
        res["reframe_sub_hits"] += sh
        res["reframe_samples"] += used
        res["reframe_solved"] += f > 0
        res[f"solved_{tag}_reframe"] += f > 0
    res["minutes"] = round((time.time() - t0) / 60, 1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reframe5_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    p = {"id": "t", "nums": [3, 4, 6], "target": 24}
    subs = reframes(p)
    got = {(tuple(q["nums"]), q["target"]) for q, _ in subs}
    assert ((4, 6), 8) in got and ((3, 6), 6) in got and ((3, 4), 4) in got      # T/x for each x
    for q, back in subs:                                                            # every carry-back is exact
        sol = B1.solve(q["nums"], q["target"])
        if sol:
            assert B1.check(back(sol), p["nums"], p["target"]), (q, sol, back(sol))
    q, back = next((q, b) for q, b in subs if (tuple(q["nums"]), q["target"]) == ((4, 6), 8))
    assert not B1.check(back("4+6"), p["nums"], p["target"])                       # a wrong piece stays wrong
    assert all(len(q["nums"]) == 2 for q, _ in subs)
    print(f"selftest ok ({len(subs)} reframes for {p['nums']} -> 24)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--test-seed", type=int, default=784)
    ap.add_argument("--n-test", type=int, default=80)
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
