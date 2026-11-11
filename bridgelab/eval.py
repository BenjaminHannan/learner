"""Ablations (real / off / shuffle / mean) on two fixed test sets, plus linear probes on the frozen messages."""
from __future__ import annotations

import torch
import torch.nn.functional as F

from . import task
from .models import MODES, Pair


@torch.no_grad()
def accuracy(model: Pair, d: dict, mode: str = "real", bs: int = 500) -> dict[str, float]:
    """Accuracy of head A (direction B->A) and head B (direction A->B). Shuffles are within each batch of bs."""
    model.eval()
    gen = torch.Generator().manual_seed(7)
    n, hits = len(d["yA"]), torch.zeros(2)
    for i in range(0, n, bs):
        sl = slice(i, i + bs)
        la, lb = model(d["xa"][sl], d["xb"][sl], mode, gen)
        hits += torch.tensor([(la.argmax(1) == d["yA"][sl]).sum(), (lb.argmax(1) == d["yB"][sl]).sum()], dtype=torch.float)
    return {"A": float(hits[0] / n), "B": float(hits[1] / n)}


@torch.no_grad()
def messages(model: Pair, d: dict, bs: int = 500) -> dict[str, torch.Tensor]:
    model.eval()
    out = {"ab": [], "ba": []}
    for i in range(0, len(d["yA"]), bs):
        _, _, raw = model(d["xa"][i:i + bs], d["xb"][i:i + bs], "real", None, True)
        for k in out:
            out[k].append(raw[k].flatten(1))
    return {k: torch.cat(v) for k, v in out.items()}


def linear_probe(xtr, ytr, xte, yte, n_cls: int, steps: int = 300) -> float:
    """Multinomial logistic regression (full-batch Adam) on standardised features; returns held-out accuracy."""
    mu, sd = xtr.mean(0), xtr.std(0) + 1e-6
    xtr, xte = (xtr - mu) / sd, (xte - mu) / sd
    lin = torch.nn.Linear(xtr.shape[1], n_cls)
    opt = torch.optim.Adam(lin.parameters(), lr=0.05)
    for _ in range(steps):
        opt.zero_grad()
        F.cross_entropy(lin(xtr), ytr).backward()
        opt.step()
    with torch.no_grad():
        return float((lin(xte).argmax(1) == yte).float().mean())


def probes(model: Pair, test: dict, seed: int) -> dict[str, float]:
    """A->B message predicts v; B->A message predicts u. Fit on 20000 fresh items, scored on the test set."""
    if model.ab is None:
        return {}
    tr = task.make_batch(20000, torch.Generator().manual_seed(999 + seed))
    mtr, mte = messages(model, tr), messages(model, test)
    return {"ab_v": linear_probe(mtr["ab"], tr["v"], mte["ab"], test["v"], task.NV),
            "ba_u": linear_probe(mtr["ba"], tr["u"], mte["ba"], test["u"], task.NV)}


def full_eval(model: Pair, seed: int) -> dict:
    test, held = task.make_test(False), task.make_test(True)
    modes = ("real",) if model.ab is None else MODES
    return {"acc": {m: accuracy(model, test, m) for m in modes},
            "acc_heldout": {m: accuracy(model, held, m) for m in modes},
            "probe": probes(model, test, seed)}
