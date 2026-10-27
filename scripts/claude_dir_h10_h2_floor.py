#!/usr/bin/env python3
"""H10 addendum for H2 (2026-09-28): the code-only, no-search floor on the 300 P_other dev pairs. Pure python, no torch.

H2's PASSMARKS.md judges P_other (300 dev (hand, target != 24) pairs, right at the net's own stop, any valid answer counts)
but gives no floor for it. The diagnosis floors A, B, C (claude_numbers_diag_answers.py) are for target 24; easy targets (for
example the sum of the four numbers) have a much higher no-search floor. This script applies the same three strategies, plus
one stricter oracle, to the sealed dev pairs of claude_dir_h2_pool.split_dev. It reads no net and no test panel.

  python3 -B scripts/claude_dir_h10_h2_floor.py           prints the floors and writes artifacts/claude-dir-h10-addenda-20260928/h2-pother-floor.json

Strategies (expected number of right answers out of 300, exact arithmetic over all number orders):
  A  a random well-formed postfix answer that uses the right four numbers (random order, random shape, random ops)
  B  the single commonest stored skeleton of the NEW practice pool, numbers in a random order
  C  a skeleton drawn from the stored-skeleton frequencies of the NEW practice pool, numbers in a random order
  Bold / Cold  the same B and C with the OLD practice pool's (target-24 only) skeleton counts, for continuity with the diagnosis
  F  the best single fixed skeleton of all shapes, chosen AFTER seeing the dev pairs (an oracle; a strict ceiling for any strategy
     that copies one fixed skeleton and never checks arithmetic)
  G  report only, a loose ceiling: for every dev pair the best skeleton for THAT pair is known, only the number order is guessed
     (needs the target arithmetic to pick the skeleton, so it is not a no-search strategy; it shows how much a net that knows
     "which shape" but cannot order the numbers could reach)
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h2_pool as P  # noqa: E402
import claude_numbers_diag_answers as D  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402
import codex_numbers_20260927_labels as L  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "claude-dir-h10-addenda-20260928" / "h2-pother-floor.json"


def floors():
    practice, dev = P.practice_and_dev()
    four, _ = E.number_hands()
    train4, _held = E.split_four(four)
    # skeleton counts of stored answers: new practice pool, and the old target-24 pool
    sk_new, sk_old = collections.Counter(), collections.Counter()
    for h, t, s in practice:
        sk_new[D.skeleton(D.stored_tokens(h, t, s))] += 1
    for h, t, s in train4:
        sk_old[D.skeleton(D.stored_tokens(h, t, s))] += 1
    top_new, top_old = sk_new.most_common(1)[0][0], sk_old.most_common(1)[0][0]
    fr_new = {k: v / len(practice) for k, v in sk_new.items()}
    fr_old = {k: v / len(train4) for k, v in sk_old.items()}
    A = B = C = Bold = Cold = 0.0
    per_sk = collections.Counter()          # expected hits of each fixed skeleton over the dev pairs (for F)
    G = 0.0
    n_valid_pairs = 0
    for h, t, _s in dev:
        seqs = L.solutions_for(list(h), t)
        n_valid_pairs += bool(seqs)
        Pn = D.n_perms(h)
        by_sk = collections.Counter(D.skeleton(x) for x in seqs)
        A += len(seqs) / (Pn * 5 * 64)
        B += by_sk.get(top_new, 0) / Pn
        C += sum(f * by_sk.get(k, 0) / Pn for k, f in fr_new.items())
        Bold += by_sk.get(top_old, 0) / Pn
        Cold += sum(f * by_sk.get(k, 0) / Pn for k, f in fr_old.items())
        for k, v in by_sk.items():
            per_sk[k] += v / Pn
        G += max(by_sk.values()) / Pn if by_sk else 0.0
    best_sk, F = max(per_sk.items(), key=lambda kv: kv[1])
    # dev pairs that a sum-of-the-four-numbers answer solves (a no-search rule any order works for): count exactly
    easy_sum = sum(1 for h, t, _ in dev if sum(h) == t)
    res = {
        "n_dev_pairs": len(dev), "dev_pairs_with_a_valid_answer": n_valid_pairs,
        "A_random_wellformed_answer_right_numbers": round(A, 2),
        "B_top_stored_skeleton_new_pool_random_order": round(B, 2),
        "C_stored_skeleton_prior_new_pool_random_order": round(C, 2),
        "Bold_top_stored_skeleton_old_pool_random_order": round(Bold, 2),
        "Cold_stored_skeleton_prior_old_pool_random_order": round(Cold, 2),
        "F_best_single_fixed_skeleton_oracle_chosen_after_seeing_dev": round(F, 2),
        "F_skeleton_tokens": list(best_sk),
        "G_report_only_best_skeleton_per_pair_random_order": round(G, 2),
        "unrounded": {"A": A, "B": B, "C": C, "F": F, "G": G},
        "top_new_skeleton_tokens": list(top_new), "top_old_skeleton_tokens": list(top_old),
        "dev_pairs_where_target_equals_sum_of_the_four_numbers": easy_sum,
        "dev_target_histogram": dict(sorted(collections.Counter(t for _, t, _ in dev).items())),
        "note": "skeleton = postfix with numbers blanked (0), ops as token ids 21 +, 22 -, 23 *, 24 /; expected counts of 300",
    }
    return res


def main():
    res = floors()
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
