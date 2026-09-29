#!/usr/bin/env python3
"""dir-s3 numbers (2026-09-29): every valid postfix answer of every (hand, target) pair of the dir-h2 wide pool. Pure python.

Training-data code only: the exact checker (claude_rsn358a_envs.check_numbers) builds the candidate lists; nothing here
runs at test time. One subset DP per hand gives the answers for all targets 5-40 at once (same DP as
codex_numbers_20260927_labels.solutions_for, which keeps both operand orders; a test below checks they agree).

  python -B scripts/claude_dir_s3_labels.py selftest     (pure python, a few minutes)
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402


def answers_by_target(nums, lo=5, hi=40):
    """{target: sorted list of 7-token postfix answers (token ids as in E.number_item)} for one 4-number hand"""
    n = len(nums)
    dp = {1 << i: {Fraction(x): {(E.VAL + x,)}} for i, x in enumerate(nums)}
    for mask in range(1, 1 << n):
        if mask.bit_count() < 2:
            continue
        out = {}

        def add(v, seq):
            out.setdefault(v, set()).add(seq)
        left = (mask - 1) & mask
        while left:
            right = mask ^ left
            if right and left < right:
                for a, aseqs in dp[left].items():
                    for b, bseqs in dp[right].items():
                        for x in aseqs:
                            for y in bseqs:
                                add(a + b, x + y + (E.OPS["+"],)); add(a + b, y + x + (E.OPS["+"],))
                                add(a * b, x + y + (E.OPS["*"],)); add(a * b, y + x + (E.OPS["*"],))
                                add(a - b, x + y + (E.OPS["-"],)); add(b - a, y + x + (E.OPS["-"],))
                                if b:
                                    add(a / b, x + y + (E.OPS["/"],))
                                if a:
                                    add(b / a, y + x + (E.OPS["/"],))
            left = (left - 1) & mask
        dp[mask] = out
    full = dp[(1 << n) - 1]
    return {t: sorted(full[Fraction(t)]) for t in range(lo, hi + 1) if Fraction(t) in full}


def build_table(practice):
    """{(hand tuple, target): [answers]} for every pair in `practice` (list of (hand, target, stored solution))"""
    by_hand = {}
    table = {}
    for h, t, _ in practice:
        key = tuple(h)
        if key not in by_hand:
            by_hand[key] = answers_by_target(list(key))
        table[(key, t)] = by_hand[key][t]
    return table


def stored_tokens(stored):
    return tuple(E.VAL + v if k == "n" else E.OPS[v] for k, v in E.to_postfix(stored))


def selftest():
    import random
    import codex_numbers_20260927_labels as L
    import claude_dir_h2_pool as P
    rng = random.Random(3)
    # 1. agrees with the exact enumerator used by the diagnosis, on 6 hands x all targets
    for h in ([1, 2, 3, 4], [5, 5, 5, 1], [13, 13, 12, 11], [6, 7, 8, 9], [1, 1, 1, 1], [3, 3, 8, 8]):
        mine = answers_by_target(h)
        for t in range(5, 41):
            assert mine.get(t, []) == [tuple(x) for x in L.solutions_for(h, t)], (h, t)
    print("[1] answers_by_target equals codex solutions_for on 6 hands x 36 targets")
    # 2. the whole wide pool
    practice, dev = P.practice_and_dev()
    table = build_table(practice + dev)
    sizes = [len(v) for v in table.values()]
    assert min(sizes) >= 1
    print(f"[2] {len(table)} pairs, valid answers per pair: min {min(sizes)}, median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)}")
    # 3. the stored answer is always among the valid answers; a sample all pass the sealed checker
    for h, t, s in practice + dev:
        assert stored_tokens(s) in set(table[(tuple(h), t)]), (h, t)
    for (h, t), seqs in rng.sample(sorted(table.items()), 400):
        item = E.Item("numbers", 4, [], [], [], {"nums": list(h), "target": t})
        for seq in rng.sample(seqs, min(len(seqs), 20)):
            assert E.check_numbers(item, seq)
    print("[3] stored answer in its own candidate list for all pairs; 400 pairs x up to 20 answers pass E.check_numbers")
    # 4. no valid answer is missing: a random invalid postfix of the right shape is never in a list
    for (h, t), seqs in rng.sample(sorted(table.items()), 200):
        item = E.Item("numbers", 4, [], [], [], {"nums": list(h), "target": t})
        seq = tuple(rng.choice(seqs))
        alt = list(seq)
        i = rng.randrange(7)
        alt[i] = rng.choice([x for x in (*E.OPS.values(), *(E.VAL + v for v in h)) if x != alt[i]])
        if tuple(alt) in set(seqs):
            assert E.check_numbers(item, tuple(alt))
        else:
            assert not E.check_numbers(item, tuple(alt)), (h, t, alt)      # no valid answer missing from the list
    print("[4] 200 single-token edits: in the list => valid; not in the list => invalid (no valid answer missing)")
    print("s3 labels selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
