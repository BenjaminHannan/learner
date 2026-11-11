"""Measurement after each night (uses the hidden score; never feeds back into training)."""
import numpy as np
from collections import Counter
from .paint import parse, render, CTX, canonical
from . import hidden_score


def sample_metrics(maker, guard, seed, night, ti, temp, n):
    u = np.random.default_rng([seed, 9000 + night, ti]).random((n, CTX - 1))
    toks = maker.sample(n, temp, u)
    grids = np.zeros((n, 12, 12), dtype=np.int8)
    parsed = np.zeros(n, dtype=bool)
    for i, t in enumerate(toks):
        c = parse(t)
        if c is not None:
            parsed[i] = True
            grids[i] = render(c)
    valid = parsed & grids.reshape(n, -1).any(1)
    copy = np.zeros(n, dtype=bool)
    if valid.any():
        copy[valid] = guard.distances(grids[valid]) <= guard.k
    scores = np.zeros(n)
    traits = np.zeros((n, 5), dtype=bool)
    for i in np.flatnonzero(valid):
        s, t = hidden_score.score_grid(grids[i])
        scores[i], traits[i] = s, t
    raw_mean = float(scores.mean())
    scores[copy] = 0.0
    traits[copy] = False
    canon = Counter(canonical(grids[i]) for i in np.flatnonzero(valid))
    nv = int(valid.sum())
    top10 = sum(c for _, c in canon.most_common(10))
    return {
        "mean_hidden": float(scores.mean()), "mean_hidden_copies_not_zeroed": raw_mean,
        "full_house_rate": float((traits.all(1)).mean()),
        "trait_rates": dict(zip(["body", "roof", "door", "symmetric", "clean"], traits.mean(0).tolist())),
        "copy_rate": float(copy.mean()),                       # copies / all raw samples
        "copy_rate_of_valid": float(copy.sum() / max(nv, 1)),
        "valid_program_rate": float(parsed.mean()),            # parses
        "draws_cells_rate": float(valid.mean()),               # parses and draws >= 1 cell
        "distinct_share": float(len(canon) / max(nv, 1)),
        "top10_share": float(top10 / max(nv, 1)),              # share of drawn pictures
        "top10_share_of_samples": float(top10 / n),            # share of all raw samples
        "n_samples": n,
    }


def evaluate(maker, data, guard, cfg, seed, night, heldout):
    out = {"night": night}
    for ti, temp in enumerate((1.0, 0.7)):
        out[f"t{temp}"] = sample_metrics(maker, guard, seed, night, ti, temp, cfg.eval_samples)
    out["heldout_loss"] = maker.nll(heldout)
    return out
