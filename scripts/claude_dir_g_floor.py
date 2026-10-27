#!/usr/bin/env python3
"""dir-g (test G, builder thread, 2026-09-28): F4, the no-arithmetic best-of-4 floor on the 300 held-out numbers4 hands. Pure python, no torch.

PASSMARKS.md (artifacts/claude-dir-g-search-20260928/) defines F4 as "the expected S_any of 4 independent no-arithmetic guesses
(the diagnosis's floor strategies A, B, C, four draws each, exact over number orders)". Here, for each held-out hand (target 24)
a single draw of a strategy is right with probability p (exact over all number orders, any valid answer counts, as the test does);
four independent draws are right at least once with probability 1 - (1 - p)^4. F4_X = sum over the 300 hands of that.
Strategies (scripts/claude_numbers_diag_answers.py, same definitions as the diagnosis and as claude_dir_h10_h2_floor.py):
  A  random well-formed postfix answer with the right four numbers (random order, shape and ops)
  B  the single commonest stored skeleton of the practice pool, numbers in a random order
  C  a skeleton drawn from the practice pool's stored-skeleton frequencies, numbers in a random order
The practice pool is the recipe G trains on: "h2" (36,782 wide pairs; default) or "old" (the 1,062 target-24 hands).
F4 (the number G-BASELINE.md enters) = the largest of F4_A, F4_B, F4_C for the recipe. The PASSMARKS bar "S_pick > F4" and, when
F4 > 30, "F4 + 10" use it. It reads no net and no test file: only the sealed held-out HANDS' arithmetic (the same 300 hands the
diagnosis's floors used); never any held-out answer of a net.

  python3 -B scripts/claude_dir_g_floor.py [--out artifacts/claude-dir-g-build-20260928/f4.json]     (about 2-4 minutes)
  python3 -B scripts/claude_dir_g_floor.py selftest
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h2_pool as P  # noqa: E402
import claude_numbers_diag_answers as D  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402
import codex_numbers_20260927_labels as L  # noqa: E402

DRAWS = 4


def best_of(p, k=DRAWS):
    return 1.0 - (1.0 - p) ** k


def skeleton_counts(pairs):
    c = collections.Counter()
    for h, t, s in pairs:
        c[D.skeleton(D.stored_tokens(h, t, s))] += 1
    return c


def floors(pool):
    four, _ = E.number_hands()
    train4, held4 = E.split_four(four)
    assert len(held4) == 300
    if pool == "h2":
        practice, _dev = P.practice_and_dev()
    else:
        practice = train4
    sk = skeleton_counts(practice)
    top = sk.most_common(1)[0][0]
    freq = {k: v / len(practice) for k, v in sk.items()}
    single = {"A": 0.0, "B": 0.0, "C": 0.0}
    best4 = {"A": 0.0, "B": 0.0, "C": 0.0}
    n_valid = 0
    for h, t, _s in held4:
        seqs = L.solutions_for(list(h), t)
        n_valid += bool(seqs)
        Pn = D.n_perms(h)
        by_sk = collections.Counter(D.skeleton(x) for x in seqs)
        p = {"A": len(seqs) / (Pn * 5 * 64),
             "B": by_sk.get(top, 0) / Pn,
             "C": sum(f * by_sk.get(k, 0) / Pn for k, f in freq.items())}
        for k in p:
            assert 0.0 <= p[k] <= 1.0, (k, p[k], h)
            single[k] += p[k]
            best4[k] += best_of(p[k])
    F4 = max(best4.values())
    return {"pool": pool, "n_heldout_hands": len(held4), "heldout_hands_with_a_valid_answer": n_valid,
            "practice_pairs": len(practice), "top_skeleton_tokens": list(top),
            "single_draw_expected_of_300": {k: round(v, 3) for k, v in single.items()},
            "F4_expected_S_any_of_4_independent_draws_of_300": {k: round(v, 3) for k, v in best4.items()},
            "F4": round(F4, 3), "F4_strategy": max(best4, key=best4.get),
            "upper_bound_4x_single_best": round(4 * max(single.values()), 3),
            "unrounded": {"single": single, "best4": best4, "F4": F4}}


def selftest():
    assert abs(best_of(0.0)) < 1e-12 and abs(best_of(1.0) - 1.0) < 1e-12 and abs(best_of(0.5) - (1 - 0.5 ** 4)) < 1e-12
    assert best_of(0.1) < 4 * 0.1                       # the union bound is never tight for independent draws
    # tiny hand by hand: one draw right in 1 of 2 orders, four draws right with 15/16
    assert abs(best_of(1 / 2) - 15 / 16) < 1e-12
    r = floors("old")
    s = r["single_draw_expected_of_300"]
    assert abs(s["B"] - 7.5) < 0.05, s["B"]              # the diagnosis's floor B on the held-out hands (7.50)
    assert r["F4"] <= r["upper_bound_4x_single_best"] + 1e-9
    print("selftest ok: single-draw B on the held-out hands =", s["B"], "(diagnosis 7.50); F4 (old pool) =", r["F4"])


def main():
    if sys.argv[1:] == ["selftest"]:
        selftest()
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-dir-g-build-20260928/f4.json")
    a = ap.parse_args()
    res = {"claims": {"SHOWN": "computed here from the generator, the exact enumerator and the sealed held-out hands; no net read"},
           "h2": floors("h2"), "old": floors("old")}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "claims"}, indent=1))


if __name__ == "__main__":
    main()
