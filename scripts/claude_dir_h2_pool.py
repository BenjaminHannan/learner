#!/usr/bin/env python3
"""dir-h2 numbers (helper H2, 2026-09-28): the wide 4-number practice pool, pure python (no torch).

The one change of the experiment (artifacts/claude-dir-h2-numbers-20260928/PASSMARKS.md): the 4-number practice draws from
every 4-number hand of 1-13 that is not one of the 300 held-out hands, paired with every target 5-40 the hand can reach (the
target range the 3-number puzzles already use), with the stored answer from the same solver (claude_blurt1.solve).
300 of the pairs with target not 24 are a dev check and are left out of practice. Nothing else is touched.

  python -B scripts/claude_dir_h2_pool.py selftest      (about 1-3 minutes, pure python)
  python -B scripts/claude_dir_h2_pool.py summary       (prints the counts)
"""
from __future__ import annotations

import hashlib
import itertools
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_rsn358a_envs as E  # noqa: E402

TARGETS = range(5, 41)          # the 3-number puzzles' target range (claude_rsn358a_envs.number_hands)
GRADED_TARGET = 24
DEV_SEED, N_DEV = 41707, 300
TRAIN24_SEED, N_TRAIN24 = 41708, 300
STEPS, BATCH, N_KINDS, N_SIZES = 60000, 256, 3, 2      # numbers gets 1/3 of batches, size 4 is 1 of 2 sizes


def reachable(nums):
    """every value the numbers can make using each once with + - * / (exact fractions)."""
    def rec(items):
        if len(items) == 1:
            return {items[0]}
        out = set()
        for i, j in itertools.combinations(range(len(items)), 2):
            rest = [items[k] for k in range(len(items)) if k not in (i, j)]
            a, b = items[i], items[j]
            vs = {a + b, a - b, b - a, a * b}
            if b:
                vs.add(a / b)
            if a:
                vs.add(b / a)
            for v in vs:
                out |= rec(rest + [v])
        return out
    return rec([Fraction(n) for n in nums])


def heldout_hands():
    four, _ = E.number_hands()
    train4, held4 = E.split_four(four)
    return train4, held4


def wide_pool():
    """[(hand list, target, stored solution)] for hands 1-13 not held out, targets 5-40, in a fixed order."""
    _, held4 = heldout_hands()
    held = {tuple(h) for h, _, _ in held4}
    pool = []
    for h in itertools.combinations_with_replacement(range(1, 14), 4):
        if h in held:
            continue
        r = reachable(h)
        for t in TARGETS:
            if Fraction(t) in r:
                s = B1.solve(list(h), t)
                assert s, (h, t)
                pool.append((list(h), t, s))
    return pool


def split_dev(pool):
    """(practice, dev): dev = 300 pairs with target != 24, drawn with a fixed seed."""
    rng = random.Random(DEV_SEED)
    cand = [i for i, (_, t, _) in enumerate(pool) if t != GRADED_TARGET]
    dev_idx = set(rng.sample(cand, N_DEV))
    practice = [p for i, p in enumerate(pool) if i not in dev_idx]
    dev = [pool[i] for i in sorted(dev_idx)]
    return practice, dev


def train24_sample(train4):
    return random.Random(TRAIN24_SEED).sample(train4, N_TRAIN24)


def practice_and_dev():
    pool = wide_pool()
    return split_dev(pool)


def numbers4_draws():
    return STEPS // N_KINDS // N_SIZES * BATCH


def summary_line(practice, dev, held4):
    held = {tuple(h) for h, _, _ in held4}
    ph = {tuple(h) for h, _, _ in practice}
    dk = {(tuple(h), t) for h, t, _ in dev}
    pk = {(tuple(h), t) for h, t, _ in practice}
    return (f"h2 pool: {len(practice)} practice pairs over {len(ph)} hands, {len(dev)} dev pairs, "
            f"{len(ph & held)} held-out hands in the pool, {len(pk & dk)} dev pairs in the pool")


def selftest():
    import ast
    import re
    here = Path(__file__).resolve().parent
    root = here.parent
    # 1. sealed code and tests untouched (the SEAL of rsn-358u)
    seal = root / "artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt"
    n_ok = 0
    for line in seal.read_text().splitlines():
        digest, path = line.split(None, 1)
        assert hashlib.sha256((root / path.strip()).read_bytes()).hexdigest() == digest, path
        n_ok += 1
    print(f"[1] sealed 358u code and tests: {n_ok} of {n_ok} sha256 lines match")

    # 2. the pool
    four, _ = E.number_hands()
    train4, held4 = E.split_four(four)
    held = {tuple(h) for h, _, _ in held4}
    pool = wide_pool()
    practice, dev = split_dev(pool)
    assert len(pool) == 37082 and len(practice) == 36782 and len(dev) == 300, (len(pool), len(practice), len(dev))
    assert len(held4) == 300 and len(train4) == 1062
    hands = {tuple(h) for h, _, _ in pool}
    assert len(hands) == 1519
    print(f"[2] pool {len(pool)} pairs over {len(hands)} hands; practice {len(practice)}, dev {len(dev)}; "
          f"old pool {len(train4)} hands at target 24")

    # 3. held-out hands disjoint from every pool/practice/dev pair, by multiset and by (multiset, target)
    assert not (hands & held)
    assert not ({(tuple(h), t) for h, t, _ in pool} & {(h, 24) for h in held})
    pk, dk = {(tuple(h), t) for h, t, _ in practice}, {(tuple(h), t) for h, t, _ in dev}
    assert not (pk & dk) and len(pk) == len(practice) and len(dk) == 300
    assert all(t != 24 for _, t, _ in dev)
    print(f"[3] held-out hands (300) in the pool: {len(hands & held)}; held-out (hand, 24) pairs in the pool: 0; "
          f"dev pairs in practice: {len(pk & dk)}")
    # the 300 held-out hands are exactly the ones the sealed test builds from (claude_rsn358a_run.make_test uses split_four)
    assert held == {tuple(h) for h, _, _ in E.split_four(E.number_hands()[0])[1]}

    # 4. the old target-24 pairs are inside the pool with the same stored answer; every answer is valid
    old = {(tuple(h), s) for h, _, s in train4}
    new24 = {(tuple(h), s) for h, t, s in pool if t == 24}
    assert old == new24, (len(old), len(new24))
    rng = random.Random(0)
    for h, t, s in pool:
        assert B1.check(E.postfix_to_infix(E.to_postfix(s)), h, t)
    for h, t, s in rng.sample(pool, 200):
        it = E.number_item(rng, h, t, s)
        assert E.check(it, it.target) and it.tokens[1][0] == E.VAL + t and max(x for r in it.tokens for x in r) < E.VOCAB
    print(f"[4] all {len(pool)} stored answers pass the exact checker; the {len(new24)} target-24 pairs equal the old practice pool")

    # 5. how often each pair is drawn: exact arithmetic plus a small simulation of the sampler
    draws = numbers4_draws()
    per_pair, per_hand_old = draws / len(practice), draws / len(train4)
    sim = random.Random(1)
    seen = {}
    for _ in range(200000):
        h, t, _s = practice[sim.randrange(len(practice))]
        seen[(tuple(h), t)] = seen.get((tuple(h), t), 0) + 1
    print(f"[5] numbers4 draws {draws}; new {per_pair:.1f} per pair (old {per_hand_old:.0f} per hand, {per_hand_old / per_pair:.0f}x more); "
          f"200,000 simulated draws touched {len(seen)} of {len(practice)} pairs; target-24 share {sum(1 for h, t, _ in practice if t == 24) / len(practice):.3f}")
    assert 69 < per_pair < 70 and per_hand_old > 2400

    # 6. only the pool changes: the run file assigns one thing in the sealed modules and names no panel or test
    txt = (here / "claude_dir_h2_run.py").read_text()
    tree = ast.parse(txt)
    assigned = sorted({ast.unparse(t) for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets
                       if isinstance(t, ast.Attribute)})
    assert assigned == ["R.Source", "self.four"], assigned
    code = "\n".join(ln for ln in txt.splitlines() if not ln.lstrip().startswith("#"))
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    for bad in ("readpanel", "TRAIN_SIZES", "TRAIN_ROUNDS", "GRAD_ROUNDS", "TEST_ROUNDS", "ARMS", "environ", "getpass"):
        assert bad not in code, bad
    print(f"[6] claude_dir_h2_run.py assigns only {assigned} in the sealed modules; no test-panel path, no key access")

    # 7. mixed-stream stub: the numbers-3 pool, sums and grids code paths are the sealed ones
    assert E.TRAIN_SIZES == {"sums": [1, 2, 3, 4], "grids": [4, 5], "numbers": [3, 4]}
    print("selftest ok")


def main():
    if sys.argv[1:] == ["selftest"]:
        selftest()
    elif sys.argv[1:] == ["summary"]:
        practice, dev = practice_and_dev()
        _, held4 = heldout_hands()
        print(summary_line(practice, dev, held4))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
