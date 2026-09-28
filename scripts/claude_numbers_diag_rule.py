#!/usr/bin/env python3
"""claude-numbers-diag (Helper T), part 4: the general repeat rule, audited by code over every practice stream.

RULE: for every practice stream (kind, size) the average number of draws per distinct item must be at most M = 1,000
(N = 1 distinct item per M draws). "Distinct item" = the key (sorted multiset of all input cell tokens, target tokens):
no kind label is read, and the display shuffle of the number puzzles does not count as a new item.
Draws per stream follow claude_rsn358a_run.py:Source.batch (kind uniform over 3, size uniform within the kind) x 60,000 steps x 256.

  python -B scripts/claude_numbers_diag_rule.py [--out artifacts/claude-numbers-diag-20260928/rule.json]

Distinct-item counts: sums sizes 1-3 are ENUMERATED over the generator's support (make_sum); sums4 is a lower bound
(ordered pairs / 2); numbers by enumeration of the hand pools; grids are a deliberately conservative lower bound: the
20,000 stored bases only (ignoring the 28,800 row/column/flip variants and the symbol relabelling per base).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_numbers_diag_answers as A  # noqa: E402

STEPS, BATCH, M = 60000, 256, 1000


def sums_distinct(n):
    lo = 10 ** (n - 1) if n > 1 else 0
    keys = set()
    for a in range(lo, 10 ** n):
        for j in range(1, n + 1):
            for b in range(10 ** j):
                keys.add((tuple(sorted(str(a).zfill(n + 1) + str(b).zfill(n + 1))), a + b))
    return len(keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-numbers-diag-20260928/rule.json")
    a = ap.parse_args()
    four, three = E.number_hands()
    train4, held4 = E.split_four(four)
    held = {tuple(h) for h, _, _ in held4}
    wide = 0
    for h in A.itertools.combinations_with_replacement(range(1, 14), 4):
        if h not in held:
            wide += sum(A.Fraction(t) in A.reachable_values(list(h)) for t in range(5, 41))
    streams = []

    def add(kind, size, distinct, how, extra=None):
        draws = STEPS / 3 / len(E.TRAIN_SIZES[kind]) * BATCH
        d = draws / distinct
        streams.append({"stream": f"{kind}{size}", "draws": int(draws), "distinct_items": distinct, "draws_per_item": round(d, 2),
                        "counted_how": how, "meets_rule_M_1000": d <= M, **(extra or {})})
    for n in (1, 2, 3):
        add("sums", n, sums_distinct(n), "enumerated over make_sum's support")
    add("sums", 4, (2 * 9000 * 10000 - 9000 * 9000) // 2, "lower bound: ordered pairs / 2")
    for s in (4, 5):
        add("grids", s, 20000, "conservative: stored bases only, variants ignored")
    add("numbers", 3, len(three), "enumerated: (hand, target) pairs, hands 1-9, targets 5-40")
    add("numbers", 4, len(train4), "enumerated: hands at target 24 (today)")
    add("numbers", 4, wide, "enumerated: hands 1-13 minus the 300 held-out, targets 5-40 (proposed)", {"variant": "proposed"})
    res = {"rule": "at most 1,000 draws per distinct item, on average, for every practice stream (N=1 per M=1000)",
           "streams": streams, "fail_today": [s["stream"] for s in streams if not s["meets_rule_M_1000"] and s.get("variant") != "proposed"]}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    for s in streams:
        print(s["stream"], s.get("variant", ""), s["draws"], s["distinct_items"], s["draws_per_item"], s["meets_rule_M_1000"])
    print("fail today:", res["fail_today"])


if __name__ == "__main__":
    main()
