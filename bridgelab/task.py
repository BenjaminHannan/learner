"""Split-information lookup task.

A (reader) sees four (name, value) pairs, a query `? name` (-> its private value v) and a private table sigma (a permutation of 0..7).
B (calculator) sees a private table pi (a permutation of 0..7) and a private key u.
  head B must output pi[v]    (needs v, which only A can read)         -> direction A->B
  head A must output sigma[u] (needs u, which only B has)              -> direction B->A
Alone, each side's answer is uniform over 8 values (the tables are random permutations), so chance = 1/8.
"""
from __future__ import annotations

import torch

NV, K = 8, 4
N_TRAIN_NAMES, N_NAMES = 40, 48
QRY, VAL0 = 48, 49
VOCAB_A = VAL0 + NV                  # names, query marker, 8 value tokens (also used for table entries)
VOCAB_B = NV                         # value tokens only
LEN_A, LEN_B = 2 * K + 2 + NV, NV + 1
CHANCE = 1 / NV


def _perm(n: int, gen: torch.Generator, max_swaps: int | None = None) -> torch.Tensor:
    """Uniform random permutations of 0..NV-1. Curriculum: with max_swaps set, each row is the identity followed by U{0..max_swaps} random transpositions."""
    if max_swaps is None:
        return torch.rand(n, NV, generator=gen).argsort(1)
    p, ar = torch.arange(NV).repeat(n, 1), torch.arange(n)
    m = torch.randint(0, max_swaps + 1, (n,), generator=gen)
    for s in range(max_swaps):
        i, j = torch.randint(0, NV, (n,), generator=gen), torch.randint(0, NV, (n,), generator=gen)
        vi, vj = p[ar, i], p[ar, j]
        on = s < m
        p[ar, i] = torch.where(on, vj, vi)
        p[ar, j] = torch.where(on, vi, p[ar, j])
    return p


def make_batch(n: int, gen: torch.Generator, heldout: bool = False, max_swaps: int | None = None) -> dict[str, torch.Tensor]:
    """n items. heldout=True draws all names from the 8 never-trained name tokens. max_swaps: training curriculum, tables are near-identity."""
    lo, hi = (N_TRAIN_NAMES, N_NAMES) if heldout else (0, N_TRAIN_NAMES)
    names = lo + torch.rand(n, hi - lo, generator=gen).argsort(1)[:, :K]          # K distinct names
    vals = torch.randint(0, NV, (n, K), generator=gen)
    q = torch.randint(0, K, (n,), generator=gen)
    ar = torch.arange(n)
    sigma, pi = _perm(n, gen, max_swaps), _perm(n, gen, max_swaps)
    u = torch.randint(0, NV, (n,), generator=gen)
    body = torch.stack([names, vals + VAL0], 2).reshape(n, 2 * K)
    xa = torch.cat([body, torch.full((n, 1), QRY), names[ar, q][:, None], sigma + VAL0], 1)
    xb = torch.cat([pi, u[:, None]], 1)
    v = vals[ar, q]
    return {"xa": xa, "xb": xb, "yA": sigma[ar, u], "yB": pi[ar, v], "v": v, "u": u}


def make_test(heldout: bool = False, n: int = 5000) -> dict[str, torch.Tensor]:
    """Fixed test set (seeded independently of any training seed)."""
    return make_batch(n, torch.Generator().manual_seed(12345 + int(heldout)), heldout)
