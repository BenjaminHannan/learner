#!/usr/bin/env python3
"""rsn-358a v2: the same run as scripts/claude_rsn358a_run.py (sealed, never run) with ONE fix to the loop's stop rule.

Why (sleep research thread, 2026-09-25 22:30 UTC, before any 358a run): an unregistered small CPU preview on sums
(artifacts/claude-rsn358a-20260925/preview/, fresh dev seeds, never the sealed tests) showed the v1 rule "stop at the
first round whose stop head says p > 0.5" stops after one round almost every time, even at the practised size
(4-digit sums: 185/200 with that rule vs 200/200 by round 4). The stop head is calibrated for "probably right",
which is too lax to end thinking on. v2 rule: stop at the first round (from round 3 on) where the stop head says
p > 0.5 AND the answer is the same as in the two rounds before (thinking has settled); if that never happens,
answer at round 48. The v1 rule's count is still reported as "right_v1_rule".
Training, data, nets, tests and pass marks are unchanged (PASSMARKS-v2.md repeats them).

  python -B scripts/claude_rsn358a2_run.py train|eval|make-tests|smoke ...   (same arguments as claude_rsn358a_run.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402


def stop_round(p, q, n):
    """first round r (0-based, r >= 2) with q[r] > 0.5 and p[r] == p[r-1] == p[r-2]; else the last round."""
    return next((r for r in range(2, n) if q[r] > 0.5 and p[r] == p[r - 1] == p[r - 2]), n - 1)


@torch.no_grad()
def evaluate(net, items, device, bs=100):
    if net.arm == "plain":
        return R._evaluate_v1(net, items, device, bs)
    net.eval()
    n = R.TEST_ROUNDS
    fixed = {r: 0 for r in R.FIXED_REPORT}
    right, right_v1, rounds, oracle = 0, 0, [], 0
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = R.tensors(chunk, device)
        preds, qs = net.loop_rounds(t, s, env, n)
        preds, qs = preds.tolist(), qs.tolist()
        for it, p, q in zip(chunk, preds, qs):
            stop = stop_round(p, q, n)
            rounds.append(stop + 1)
            right += E.check(it, R.grid_of(p[stop], it))
            v1 = next((r for r in range(n) if q[r] > 0.5), max(range(n), key=lambda r: q[r]))
            right_v1 += E.check(it, R.grid_of(p[v1], it))
            for r in R.FIXED_REPORT:
                fixed[r] += E.check(it, R.grid_of(p[r - 1], it))
            oracle += any(E.check(it, R.grid_of(p[r], it)) for r in range(n))
    return {"n": len(items), "right": right, "right_v1_rule": right_v1,
            "mean_rounds": round(sum(rounds) / len(rounds), 2),
            "rounds_hist": {str(k): rounds.count(k) for k in sorted(set(rounds))},
            "fixed_rounds": {str(k): v for k, v in fixed.items()}, "right_at_any_round": oracle}


R._evaluate_v1 = R.evaluate
R.evaluate = evaluate          # train's dev checks and eval both look this name up in R at call time

if __name__ == "__main__":
    R.main()
