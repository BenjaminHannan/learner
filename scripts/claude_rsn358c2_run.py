#!/usr/bin/env python3
"""rsn-358c2 (DRAFT, not sealed; run only if 358c1's answer-cell stop is not enough): rsn-358a v2
(scripts/claude_rsn358a2_run.py, wraps scripts/claude_rsn358a_run.py) with ONE change, from an outside review (Ben,
2026-09-26 01:54 UTC, section 9, and 02:11 UTC): the stop head's training label is "is this answer right by the real
checker" (E.check: any valid expression counts for number puzzles), not "equals the one stored answer". Sums and grids
have exactly one answer, so only number puzzles change. The stop RULE stays v2 (358c1 tests the answer-cell rule
separately); the answer-cell rule is reported as right_answer_cell_rule only.
The answer loss (cross-entropy to the stored answer), nets, data, steps and tests are unchanged, and the plain arm is
untouched (its 358a checkpoints can be reused: same code path, same seeds, same data stream).

  python -B scripts/claude_rsn358c_run.py train|eval|smoke ...   (same arguments as claude_rsn358a_run.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402
import claude_rsn358a2_run as V  # noqa: E402  (installs the v2 evaluate into R)

_tensors, _ce_and_exact = R.tensors, R.ce_and_exact
_last = {"items": None}


def tensors(items, device):
    _last["items"] = items
    return _tensors(items, device)


def ce_and_exact(logits, s, y):
    """same cross-entropy; 'exact' (the stop head's label) is the real checker's verdict on the decoded answer."""
    ce, exact = _ce_and_exact(logits, s, y)
    items = _last["items"]
    if items is None or len(items) != s.shape[0] or items[0].env != "numbers":
        return ce, exact                                  # sums, grids: one answer, equality == checker
    preds = logits.argmax(-1).tolist()
    ok = [float(E.check(it, R.grid_of(p, it))) for it, p in zip(items, preds)]
    return ce, torch.tensor(ok, device=exact.device, dtype=exact.dtype)


def answer_cells(p, it):
    flat = [c for row in it.slot for c in row]
    return tuple(t for t, m in zip(p, flat) if m)


def stop_round(p, q, n, it=None):
    """first round r >= 2 with q[r] > 0.5 and the ANSWER cells equal in rounds r, r-1, r-2; else the last round."""
    a = [answer_cells(x, it) for x in p] if it is not None else p
    return next((r for r in range(2, n) if q[r] > 0.5 and a[r] == a[r - 1] == a[r - 2]), n - 1)


@torch.no_grad()
def evaluate(net, items, device, bs=100):
    if net.arm == "plain":
        return R._evaluate_v1(net, items, device, bs)
    net.eval()
    n = R.TEST_ROUNDS
    fixed = {r: 0 for r in R.FIXED_REPORT}
    right, right_ac, rounds, oracle = 0, 0, [], 0
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = _tensors(chunk, device)
        preds, qs = net.loop_rounds(t, s, env, n)
        preds, qs = preds.tolist(), qs.tolist()
        for it, p, q in zip(chunk, preds, qs):
            stop = V.stop_round(p, q, n)
            rounds.append(stop + 1)
            right += E.check(it, R.grid_of(p[stop], it))
            right_ac += E.check(it, R.grid_of(p[stop_round(p, q, n, it)], it))
            for r in R.FIXED_REPORT:
                fixed[r] += E.check(it, R.grid_of(p[r - 1], it))
            oracle += any(E.check(it, R.grid_of(p[r], it)) for r in range(n))
    return {"n": len(items), "right": right, "right_answer_cell_rule": right_ac,
            "mean_rounds": round(sum(rounds) / len(rounds), 2),
            "rounds_hist": {str(k): rounds.count(k) for k in sorted(set(rounds))},
            "fixed_rounds": {str(k): v for k, v in fixed.items()}, "right_at_any_round": oracle}


R.tensors, R.ce_and_exact, R.evaluate = tensors, ce_and_exact, evaluate

if __name__ == "__main__":
    R.main()
