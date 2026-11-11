"""Shared helpers for the target-puzzle math (CPU only, no model, no repo edits).

Calculator model (mirrors pipeline_code/calculator_tools.py + calculator_runtime_depth_compare.py):
  * 4 loops; each loop: NONE, ADD or SUB.
  * ADD/SUB take two references with different ids (DUPLICATE_REFERENCE otherwise).
  * References = integer literals of the question (the k given numbers AND, by default, the target
    literal, because "to make 25" puts 25 in the question) + earlier OK results.
  * A result is OK only if 0 <= r <= UMAX (UMAX=99 is the assumption the brief asks for; the public
    LFM2.5 tokenizer actually makes 0..999 single tokens, see tok_check.py, so UMAX=999 is a sensitivity).
  * ERROR / NONE add no reference.

Checkers (on the OK calls only):
  STRICT      : OK calls form ONE tree; leaves = every given number exactly once; target literal never a
                leaf; each intermediate used exactly once later; last OK result == target.
                (Any OK call after the tree is finished breaks it.)
  STRICT-STOP : same, but loops after the finishing call are ignored (a checker that truncates).
  LENIENT     : some OK result == target whose tree uses each given number at most once, >= 2 numbers,
                and never the target literal.
"""
import itertools
from collections import defaultdict
from functools import lru_cache

import numpy as np

TARGETS = 100  # targets 0..99


# ----------------------------------------------------------------------------------------------
# Expression trees over k labelled leaves
# ----------------------------------------------------------------------------------------------
def merge_sequences(k):
    """Yield the final expression of every ordered sequence of k-1 merges (= one OK-call trajectory).
    Leaves are ints 0..k-1; internal nodes ('+', x, y) / ('-', x, y). Pieces are identified by
    position so each yielded item is one distinct call trajectory."""
    def rec(pieces):
        if len(pieces) == 1:
            yield pieces[0]
            return
        m = len(pieces)
        for a in range(m):
            for b in range(m):
                if a == b:
                    continue
                rest = [p for i, p in enumerate(pieces) if i not in (a, b)]
                for op in ('+', '-'):
                    yield from rec(rest + [(op, pieces[a], pieces[b])])
    yield from rec(list(range(k)))


def canon(e):
    """Canonical key up to commutativity of ADD (children of '+' sorted; no associativity)."""
    if isinstance(e, int):
        return ('L', e)
    x, y = canon(e[1]), canon(e[2])
    if e[0] == '+':
        x, y = sorted([x, y])
    return (e[0], x, y)


def signs(e, k):
    if isinstance(e, int):
        s = [0] * k
        s[e] = 1
        return tuple(s)
    a, b = signs(e[1], k), signs(e[2], k)
    return tuple(p + q if e[0] == '+' else p - q for p, q in zip(a, b))


def canonical_trees(k):
    """Return list of (representative_expr, multiplicity=#trajectories, sign_vector)."""
    groups = {}
    for e in merge_sequences(k):
        c = canon(e)
        if c in groups:
            groups[c][1] += 1
        else:
            groups[c] = [e, 1]
    return [(e, m, signs(e, k)) for e, m in groups.values()]


def eval_tree(e, X, umax):
    """Vectorised value of expression e on number sets X [N,k]; also mask 'all internal nodes in 0..umax'."""
    if isinstance(e, int):
        return X[:, e].astype(np.int32), np.ones(X.shape[0], dtype=bool)
    va, ma = eval_tree(e[1], X, umax)
    vb, mb = eval_tree(e[2], X, umax)
    v = va + vb if e[0] == '+' else va - vb
    return v, ma & mb & (v >= 0) & (v <= umax)


def number_sets(k, lo, hi):
    return np.array(list(itertools.combinations(range(lo, hi + 1), k)), dtype=np.int32)


def solution_counts(k, lo, hi, umax=99):
    """For every k-subset of lo..hi and every target 0..99: number of strict solutions counted as
    (traj) distinct OK-call trajectories, (trees) distinct trees up to ADD commutativity,
    (signs) distinct sign patterns (+/- per number, i.e. genuinely different arithmetic)."""
    X = number_sets(k, lo, hi)
    N = X.shape[0]
    traj = np.zeros((N, TARGETS), dtype=np.int16)
    trees = np.zeros((N, TARGETS), dtype=np.int16)
    sgn = np.zeros((N, TARGETS), dtype=np.int16)
    rows = np.arange(N)
    by_sign = defaultdict(list)
    for e, m, s in canonical_trees(k):
        by_sign[s].append((e, m))
    for s, lst in by_sign.items():
        any_valid = np.zeros(N, dtype=bool)
        val = None
        for e, m in lst:
            v, ok = eval_tree(e, X, umax)
            ok &= (v >= 0) & (v < TARGETS)
            traj[rows[ok], v[ok]] += m
            trees[rows[ok], v[ok]] += 1
            any_valid |= ok
            val = v
        sgn[rows[any_valid], val[any_valid]] += 1
    return X, traj, trees, sgn


# ----------------------------------------------------------------------------------------------
# Exact random-policy acceptance (STRICT and STRICT-STOP)
# ----------------------------------------------------------------------------------------------
def exact_random_strict(numbers, target, umax=99, target_literal=True, pointer='distinct', loops=4):
    """Exact probability that the uniform random policy yields a STRICT (and STRICT-STOP) accepted
    trajectory. pointer='distinct': uniform over ordered pairs of distinct references (the brief).
    pointer='independent': left and right pointers uniform and independent (as two argmax heads could
    be); equal picks -> DUPLICATE_REFERENCE error.
    State = (pieces, others): pieces = unconsumed partial trees (values), others = consumed refs and the
    target literal (still pointable, but any OK call touching them breaks STRICT)."""
    k = len(numbers)
    start = (tuple(sorted(numbers)), (target,) if target_literal else ())

    @lru_cache(maxsize=None)
    def analyse(pieces, others):
        allv = pieces + others
        n = len(allv)
        P = len(pieces)
        err = 0
        merges = defaultdict(int)
        for a in range(n):
            va = allv[a]
            for b in range(n):
                if a == b:
                    continue
                vb = allv[b]
                for r in (va + vb, va - vb):
                    if r < 0 or r > umax:
                        err += 1
                    elif a < P and b < P:
                        rest = [p for i, p in enumerate(pieces) if i not in (a, b)]
                        ns = (tuple(sorted(rest + [r])), tuple(sorted(others + (va, vb))))
                        merges[ns] += 1
        if pointer == 'distinct':
            denom = 3 * n * (n - 1)
            q = 1 / 3 + err / denom
        else:
            denom = 3 * n * n
            q = 1 / 3 + (err + 2 * n) / denom
        return q, tuple((ns, c / denom) for ns, c in merges.items())

    @lru_cache(maxsize=None)
    def f(state, L, stop):
        pieces, others = state
        if len(pieces) == 1:
            if pieces[0] != target:
                return 0.0
            if stop:
                return 1.0
            q, _ = analyse(pieces, others)
            return q ** L
        if len(pieces) - 1 > L:
            return 0.0
        q, merges = analyse(pieces, others)
        total = q * f(state, L - 1, stop)
        for ns, w in merges:
            total += w * f(ns, L - 1, stop)
        return total

    return f(start, loops, False), f(start, loops, True)


# ----------------------------------------------------------------------------------------------
# Monte Carlo of the random policy (vectorised); gives STRICT, STRICT-STOP and LENIENT
# ----------------------------------------------------------------------------------------------
def mc_random(numbers, targets, R, rng, umax=99, target_literal=True, pointer='distinct', loops=4):
    """numbers [I,k] int, targets [I]. Returns per-instance hit fractions (strict, stop, lenient), each [I]."""
    numbers = np.asarray(numbers, dtype=np.int32)
    targets = np.asarray(targets, dtype=np.int32)
    I, k = numbers.shape
    S = I * R
    N0 = k + (1 if target_literal else 0)
    Nmax = N0 + loops
    TBIT = 1 << k
    vals = np.zeros((S, Nmax), dtype=np.int32)
    masks = np.zeros((S, Nmax), dtype=np.int32)
    dup = np.zeros((S, Nmax), dtype=bool)
    consumed = np.zeros((S, Nmax), dtype=bool)
    vals[:, :k] = np.repeat(numbers, R, axis=0)
    for i in range(k):
        masks[:, i] = 1 << i
    tgt = np.repeat(targets, R)
    if target_literal:
        vals[:, k] = tgt
        masks[:, k] = TBIT
        consumed[:, k] = True  # never a legal STRICT leaf
    n = np.full(S, N0, dtype=np.int32)
    ar = np.arange(S)
    broken = np.zeros(S, dtype=bool)
    merges = np.zeros(S, dtype=np.int32)
    last_ok = np.full(S, -1, dtype=np.int32)
    stop_acc = np.zeros(S, dtype=bool)
    len_hit = np.zeros(S, dtype=bool)
    for _ in range(loops):
        act = rng.integers(0, 3, size=S)
        i = np.minimum((rng.random(S) * n).astype(np.int32), n - 1)
        if pointer == 'distinct':
            j = np.minimum((rng.random(S) * (n - 1)).astype(np.int32), n - 2)
            j = j + (j >= i)
            same = np.zeros(S, dtype=bool)
        else:
            j = np.minimum((rng.random(S) * n).astype(np.int32), n - 1)
            same = i == j
        va, vb = vals[ar, i], vals[ar, j]
        r = np.where(act == 1, va + vb, va - vb)
        ok = (act > 0) & ~same & (r >= 0) & (r <= umax)
        valid = ~consumed[ar, i] & ~consumed[ar, j]
        broken_before = broken.copy()
        broken |= ok & ~valid
        mi, mj = masks[ar, i], masks[ar, j]
        newmask = mi | mj
        newdup = dup[ar, i] | dup[ar, j] | ((mi & mj) != 0)
        okv = ok & valid
        # consume children of a valid merge
        consumed[ar[okv], i[okv]] = True
        consumed[ar[okv], j[okv]] = True
        # append the new reference
        rows = ar[ok]
        slot = n[ok]
        vals[rows, slot] = r[ok]
        masks[rows, slot] = newmask[ok]
        dup[rows, slot] = newdup[ok]
        consumed[rows, slot] = False
        merges += okv
        last_ok = np.where(ok, r, last_ok)
        stop_acc |= okv & ~broken_before & (merges == k - 1) & (r == tgt)
        len_hit |= ok & (r == tgt) & ((newmask & TBIT) == 0) & ~newdup
        n = n + ok
    strict = ~broken & (merges == k - 1) & (last_ok == tgt)
    f = lambda a: a.reshape(I, R).mean(1)
    return f(strict), f(stop_acc), f(len_hit)


def passk(p, k):
    p = np.asarray(p, dtype=float)
    return float(np.mean(1 - (1 - p) ** k))


def quantiles(a, qs=(0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)):
    a = np.asarray(a, dtype=float)
    return [float(np.quantile(a, q)) for q in qs]
