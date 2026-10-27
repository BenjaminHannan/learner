#!/usr/bin/env python3
"""Code-made wider practice for the patch reasoner.

All items use claude_rsn358a_envs.Item and its 125-token vocabulary. There is
no family identifier in tokens: the operation is observable from the worked
example (sort/reverse), the count key, or the bracket alphabet and blank.
`check` accepts a flat H*W prediction. `fingerprint` hashes only model input,
so an excluded puzzle cannot return with a different answer or metadata.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import claude_rsn358a_envs as E

KINDS = ("sums", "grids", "sorting", "reversing", "counting", "brackets")
VOCAB = E.VOCAB
DEFAULT_SIZE = {"sorting": 6, "reversing": 6, "counting": 6, "brackets": 16}


def _sequence_item(kind, rng, size):
    """A worked transformation makes sort and reverse distinguishable."""
    if size < 3 or size > 16:
        raise ValueError("sequence size must be 3..16")
    op = sorted if kind == "sorting" else lambda x: list(reversed(x))
    while True:
        example = [E.DIG + rng.randrange(10) for _ in range(size)]
        # A common visible input must never ask for incompatible outputs.
        if sorted(example) != list(reversed(example)):
            break
    query = [E.DIG + rng.randrange(10) for _ in range(size)]
    tokens = [example, op(example), query, [E.MASK] * size]
    slot = [[0] * size for _ in range(3)] + [[1] * size]
    target = [[0] * size for _ in range(3)] + [op(query)]
    return E.Item(kind, size, tokens, slot, target, {})


def _count_item(rng, size):
    """First cell is the key; count its occurrences in the following cells."""
    if size < 2 or size > 9:
        raise ValueError("counting size must be 2..9")
    key = E.DIG + rng.randrange(10)
    seq = [E.DIG + rng.randrange(10) for _ in range(size)]
    w = size + 1
    tokens = [[key] + seq, [E.MASK] + [E.BLANK] * size]
    slot = [[0] * w, [1] + [0] * size]
    target = [[0] * w, [E.DIG + seq.count(key)] + [0] * size]
    return E.Item("counting", size, tokens, slot, target, {})


def _bracket_item(rng, size):
    """Complete one missing parenthesis in a balanced sequence.

    Existing + and - operator tokens stand for opening and closing brackets;
    no vocabulary entry is added. The visible balance uniquely fixes the blank.
    """
    if size < 2 or size > 18 or size % 2:
        raise ValueError("bracket size must be even and 2..18")
    seq, depth = [], 0
    for i in range(size):
        remaining = size - i
        if depth == 0:
            opening = True
        elif depth == remaining:
            opening = False
        else:
            opening = rng.random() < 0.5
        seq.append(E.OPS["+"] if opening else E.OPS["-"])
        depth += 1 if opening else -1
    assert depth == 0
    j = rng.randrange(size)
    tokens = [seq[:]]
    tokens[0][j] = E.MASK
    slot = [[int(i == j) for i in range(size)]]
    target = [[seq[i] if i == j else 0 for i in range(size)]]
    return E.Item("brackets", size, tokens, slot, target, {})


def _make(kind, rng, size):
    if kind == "sums":
        if size not in (1, 2, 3, 4):
            raise ValueError("sum size must be 1..4")
        return E.make_sum(rng, size)
    if kind == "grids":
        if size not in (4, 5):
            raise ValueError("grid size must be 4 or 5")
        sol, puz = E.make_latin_base(rng, size)
        sol, puz = E.augment_latin(rng, sol, puz)
        it = E.latin_item(rng, sol, puz)
        # The legend exposes the episode's symbols, including those absent
        # from the givens. It occupies two non-answer rows, as in xfer-1.
        legend = [E.SYM + x for x in it.meta["names"]]
        rng.shuffle(legend)
        it.tokens.extend([[E.BLANK] * size, legend])
        it.slot.extend([[0] * size, [0] * size])
        it.target.extend([[0] * size, [0] * size])
        return it
    if kind in ("sorting", "reversing"):
        return _sequence_item(kind, rng, size)
    if kind == "counting":
        return _count_item(rng, size)
    if kind == "brackets":
        return _bracket_item(rng, size)
    raise ValueError(f"unknown kind: {kind}")


def fingerprint(item):
    """Exact visible puzzle key, independent of family label and answer."""
    raw = json.dumps([item.tokens, item.slot], separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def batch(kind, rng, n, size=None, exclude=None):
    """Return n distinct-input Items of one shape; skip excluded fingerprints.

    `exclude` may be a set of fingerprints or Items. Use panel fingerprints as
    exclusion during training, or pass training fingerprints when making dev.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    if n < 0:
        raise ValueError("n must be nonnegative")
    if size is None:
        size = (rng.choice((1, 2, 3, 4)) if kind == "sums" else
                rng.choice((4, 5)) if kind == "grids" else DEFAULT_SIZE[kind])
    ban = {fingerprint(x) if isinstance(x, E.Item) else x for x in (exclude or ())}
    seen = set(ban)
    out = []
    attempts = 0
    while len(out) < n:
        attempts += 1
        if attempts > max(1000, 100 * n):
            raise ValueError("not enough distinct puzzles outside exclusion set")
        it = _make(kind, rng, size)
        fp = fingerprint(it)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(it)
    return out


def panel(kind, seed, n=300, exclude=None, size=None):
    """Fixed-seed fresh panel; optional exclusion enforces exact split isolation."""
    if size is None:
        size = 4 if kind == "sums" else 5 if kind == "grids" else None
    return batch(kind, random.Random(seed), n, size=size, exclude=exclude)


def check(item, pred):
    """Grade a flat H*W prediction using only values at answer slots."""
    h, w = len(item.tokens), len(item.tokens[0])
    if len(pred) != h * w:
        return False
    rows = [list(pred[r * w:(r + 1) * w]) for r in range(h)]
    if item.env == "sums":
        return E.check_sum(item, rows[2])
    if item.env == "grids":
        return E.check_latin(item, rows)
    if item.env in ("sorting", "reversing", "counting", "brackets"):
        return all(rows[r][c] == item.target[r][c]
                   for r in range(h) for c in range(w) if item.slot[r][c])
    raise ValueError(f"unknown item environment: {item.env}")


def generator_hashes():
    """SHA-256 of this generator and the imported environment dependencies."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(E.__file__), Path(E.B1.__file__))}


if __name__ == "__main__":
    rng = random.Random(0)
    for kind in KINDS:
        items = batch(kind, rng, 20)
        assert len({fingerprint(x) for x in items}) == len(items)
        assert len({(len(x.tokens), len(x.tokens[0])) for x in items}) == 1
        for it in items:
            flat = [v for row in it.target for v in row]
            assert check(it, flat), (kind, it.tokens)
        fresh = panel(kind, 1, 20, exclude={fingerprint(x) for x in items})
        assert not ({fingerprint(x) for x in items} & {fingerprint(x) for x in fresh})
    print("selfcheck ok")
