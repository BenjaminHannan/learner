#!/usr/bin/env python3
"""claude-numbers-diag (Helper T, 2026-09-28), part 1: what the numbers practice pool looks like and what a net
would score WITHOUT search. Read-only: no training, no torch, no GPU. Uses only the generator
(scripts/claude_rsn358a_envs.py) and codex's exact enumerator (scripts/codex_numbers_20260927_labels.py:solutions_for).

  python -B scripts/claude_numbers_diag_answers.py [--out artifacts/claude-numbers-diag-20260928/answers.json]

Reports:
  pool      sizes of the practice pools and how often each item is drawn in 60,000 steps (Source.batch logic)
  answers   how many valid postfix answers each practice item has, and how the stored one was chosen
  floors    what held-out numbers4 score four search-free strategies get (expected or exact), on the 300 held-out hands
  wider     size of the practice pool if 4-number hands were drawn with targets 5-40 (the proposed fix), held-out hands excluded
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import codex_numbers_20260927_labels as L  # noqa: E402

STEPS, BATCH = 60000, 256
SHAPES = [s_ for s_ in itertools.product("no", repeat=7) if s_[0] == "n" and s_[1] == "n" and s_[-1] == "o" and s_.count("n") == 4
          and all(sum(1 if c == "n" else -1 for c in s_[:i + 1]) >= 1 for i in range(7))]
NB = STEPS / 3                                   # numbers batches: env chosen uniformly from 3 kinds (claude_rsn358a_run.py:Source.batch)


def stored_tokens(nums, target, stored):
    return tuple(E.VAL + v if k == "n" else E.OPS[v] for k, v in E.to_postfix(stored))


def skeleton(seq):
    return tuple(t if t in E.OP_OF else 0 for t in seq)


def n_perms(nums):
    c = collections.Counter(nums)
    return math.factorial(len(nums)) // math.prod(math.factorial(v) for v in c.values())


def reachable_values(nums):
    """set of values reachable using every number once (values only; fast)"""
    n = len(nums)
    dp = {1 << i: {Fraction(x)} for i, x in enumerate(nums)}
    for mask in range(1, 1 << n):
        if mask in dp:
            continue
        out = set()
        left = (mask - 1) & mask
        while left:
            right = mask ^ left
            if left < right:
                for a in dp[left]:
                    for b in dp[right]:
                        out.update((a + b, a - b, b - a, a * b))
                        if b:
                            out.add(a / b)
                        if a:
                            out.add(b / a)
            left = (left - 1) & mask
        dp[mask] = out
    return dp[(1 << n) - 1]


def remap(tokens, src_sorted, dst_sorted):
    """replace the numbers of a stored answer for hand src by those of hand dst, by rank (i-th smallest -> i-th smallest)"""
    used = collections.defaultdict(int)
    out = []
    for t in tokens:
        if t in E.OP_OF:
            out.append(t)
            continue
        v = t - E.VAL
        k = used[v]
        used[v] += 1
        idx = [i for i, x in enumerate(src_sorted) if x == v][k]
        out.append(E.VAL + dst_sorted[idx])
    return tuple(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-numbers-diag-20260928/answers.json")
    a = ap.parse_args()
    four, three = E.number_hands()
    train4, held4 = E.split_four(four)
    res = {"claims": {"SHOWN": "every number here is computed from the generator and the exact enumerator in this script"}}

    # ---- pool ----
    pool = {"four_solvable_hands_total": len(four), "four_practice": len(train4), "four_heldout": len(held4),
            "four_hands_possible_multisets_1_13": math.comb(16, 4), "three_pairs": len(three),
            "batches_numbers_total": NB, "batches_numbers4": NB / 2, "batches_numbers3": NB / 2,
            "draws_per_item_numbers4": NB / 2 * BATCH / len(train4), "draws_per_item_numbers3": NB / 2 * BATCH / len(three)}
    sums4_space = 2 * 9000 * 10000 - 9000 * 9000        # ordered (a,b): a 4-digit and b <=4-digit, or swapped (make_sum), overlap removed
    pool["sums4_distinct_pairs_lower_bound"] = sums4_space
    pool["sums4_draws"] = STEPS / 3 / 4 * BATCH
    pool["grids5_bases"] = 20000
    pool["grids5_draws"] = STEPS / 3 / 2 * BATCH
    pool["grids5_augmentations_per_base"] = math.factorial(5) ** 2 * 2
    res["pool"] = pool

    # ---- answers per practice item ----
    cnt4, cnt3, rows4 = [], [], []
    stored_rank = []
    sk_stored = collections.Counter()
    for nums, t, s in three:
        cnt3.append(len(L.solutions_for(nums, t)))
    valid4 = {}
    for nums, t, s in train4 + held4:
        seqs = L.solutions_for(nums, t)
        valid4[tuple(nums)] = seqs
    for nums, t, s in train4:
        seqs = valid4[tuple(nums)]
        cnt4.append(len(seqs))
        st = stored_tokens(nums, t, s)
        assert st in set(seqs)
        sk_stored[skeleton(st)] += 1
        stored_rank.append(sorted(seqs).index(st))
    allc = sorted(cnt3 + cnt4)
    res["answers"] = {
        "practice_pairs": len(allc), "with_more_than_one_valid": sum(c > 1 for c in allc),
        "min": allc[0], "median": allc[len(allc) // 2], "max": allc[-1],
        "four_hands_median": sorted(cnt4)[len(cnt4) // 2], "four_hands_min": min(cnt4), "four_hands_max": max(cnt4),
        "four_hands_with_exactly_one": sum(c == 1 for c in cnt4),
        "heldout_median_valid": sorted(len(valid4[tuple(h)]) for h, _, _ in held4)[150],
        "heldout_with_exactly_one": sum(len(valid4[tuple(h)]) == 1 for h, _, _ in held4),
        "stored_skeletons_distinct": len(sk_stored), "stored_skeleton_top": [[list(k), v] for k, v in sk_stored.most_common(8)],
        "stored_position_in_sorted_valid_list_median": sorted(stored_rank)[len(stored_rank) // 2],
        "note": "skeleton = postfix with numbers blanked (0) and ops kept as token ids 21 +, 22 -, 23 *, 24 /",
    }

    # ---- floors on the 300 held-out hands ----
    skfreq = {k: v / len(train4) for k, v in sk_stored.items()}
    top_sk = sk_stored.most_common(1)[0][0]
    exp_random = exp_top = exp_prior = 0.0
    cover_any = cover_top5 = 0
    top5 = [k for k, _ in sk_stored.most_common(5)]
    sk_sets_by_hand = {}
    for nums, t, s in held4:
        seqs = valid4[tuple(nums)]
        P = n_perms(nums)
        exp_random += len(seqs) / (P * 5 * 64)
        by_sk = collections.Counter(skeleton(x) for x in seqs)
        exp_top += by_sk.get(top_sk, 0) / P
        exp_prior += sum(f * by_sk.get(k, 0) / P for k, f in skfreq.items())
        cover_any += any(k in by_sk for k in skfreq)
        cover_top5 += any(k in by_sk for k in top5)
    # nearest-hand lookup: sorted-vector L1 nearest practice hand, remap its stored answer by rank
    prac = [(sorted(n), stored_tokens(n, t, s)) for n, t, s in train4]
    hits_nn, hits_nn_loo = 0, 0
    for nums, t, s in held4:
        h = sorted(nums)
        best = min(prac, key=lambda p: sum(abs(x - y) for x, y in zip(p[0], h)))
        tok = remap(best[1], best[0], h)
        hits_nn += E.check_numbers(E.Item("numbers", 4, [], [], [], {"nums": nums, "target": t}), list(tok))
    for i, (nums, t, s) in enumerate(train4):
        h = sorted(nums)
        best = min((p for j, p in enumerate(prac) if j != i), key=lambda p: sum(abs(x - y) for x, y in zip(p[0], h)))
        tok = remap(best[1], best[0], h)
        hits_nn_loo += E.check_numbers(E.Item("numbers", 4, [], [], [], {"nums": nums, "target": t}), list(tok))
    res["floors_on_300_heldout"] = {
        "A_random_wellformed_answer_right_numbers_expected_hits": round(exp_random, 2),
        "B_top_stored_skeleton_random_number_order_expected_hits": round(exp_top, 2),
        "C_stored_skeleton_prior_random_number_order_expected_hits": round(exp_prior, 2),
        "D_nearest_practice_hand_answer_remapped_hits": hits_nn,
        "D_same_on_practice_leave_one_out_hits_of_1062": hits_nn_loo,
        "E_heldout_hands_with_a_valid_answer_in_ANY_practice_skeleton_oracle_order": cover_any,
        "E_same_using_only_the_5_commonest_skeletons": cover_top5,
        "observed_358u_nets_numbers4_of_300": "0-3 (artifacts/claude-rsn358u-20260927/RESULTS.md:12)",
        "meaning": "A-C are what a net would score if it knew the answer format (and, for B and C, the stored style) but could not do arithmetic; E is the ceiling for a net that only ever copies a stored skeleton and picks the number order perfectly",
    }

    # ---- wider pool (the proposed fix) ----
    held = {tuple(h) for h, _, _ in held4}
    pairs = 0
    per_target = collections.Counter()
    hands_used = 0
    for h in itertools.combinations_with_replacement(range(1, 14), 4):
        if h in held:
            continue
        vals = reachable_values(list(h))
        ts = [t for t in range(5, 41) if Fraction(t) in vals]
        if ts:
            hands_used += 1
        pairs += len(ts)
        for t in ts:
            per_target[t] += 1
    res["wider"] = {"four_hands_used": hands_used, "hand_target_pairs_targets_5_40": pairs,
                    "draws_per_pair_numbers4_if_half_of_numbers_batches": round(NB / 2 * BATCH / pairs, 1),
                    "draws_per_item_today": round(pool["draws_per_item_numbers4"], 1),
                    "pairs_at_target_24": per_target[24]}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
