#!/usr/bin/env python3
"""fs-358r (Fix-sleep thread, 2026-09-27; Thread manager's ask 19:13 UTC): is phase C's lower replay share the reason
the dense loop loses grids during mazes? One change against rsn-358e4's dense-replayall (imported unchanged):

  baseline  (358e4 as sealed)  phase C: every 10th step is an earlier-kind batch, alternating grids / sums (75 + 75)
  candidate (this file)        phase C: every 5th step is an earlier-kind batch, alternating grids / sums (150 + 150)

Phase A and phase B are unchanged (B: every 10th step is grids, 250 of 2,500). Phase C stays 1,500 steps, so the
candidate practises mazes 1,200 steps instead of 1,350; that is part of the one change (a higher replay share).
Replay batches come from the phase-A grids pool and the code-made sums generator, never a dev set.

  python -B scripts/claude_rsn358e4_replayall.py run --arm dense-replayall --seed S --out DIR   (baseline)
  python -B scripts/claude_fs358r_creplay.py run --seed S --out DIR                            (candidate)
  python -B scripts/claude_fs358r_creplay.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e4_replayall as E4  # noqa: E402

B_EVERY = 10          # unchanged from 358e4
C_EVERY = 5           # the one change (358e4: 10)


def phase_batch(rng, kind, bsz, pool):
    st = E4.ST
    if kind != st["kind"]:
        st["kind"], st["n"] = kind, 0
    st["n"] += 1
    every = C_EVERY if kind == "mazes" else B_EVERY
    if kind in ("sums", "mazes") and st["n"] % every == 0:
        old = "grids" if kind == "sums" else ("grids", "sums")[(st["n"] // every) % 2]
        st["replayed"][kind][old] = st["replayed"][kind].get(old, 0) + 1
        return E4.E3._phase_batch(rng, old, bsz, pool)
    return E4.E3._phase_batch(rng, kind, bsz, pool)


def selftest():
    import random
    rng = random.Random(0)
    pool = {sz: [E4.E3.E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
    E4.ST.update(kind=None, n=0, replayed={"sums": {}, "mazes": {}})
    for _ in range(2500):
        phase_batch(rng, "sums", 2, pool)
    for _ in range(1500):
        phase_batch(rng, "mazes", 2, pool)
    assert E4.ST["replayed"] == {"sums": {"grids": 250}, "mazes": {"grids": 150, "sums": 150}}, E4.ST["replayed"]
    net = E4.make_net("dense-replayall", "small")
    assert E4.E3.ST["arm"] == "dense"
    n = sum(p.numel() for p in net.parameters())
    assert n == 1646750, n
    print(f"fs358r selftest ok: candidate replay B 250 grids, C 150 grids + 150 sums; dense weights {n}")


if __name__ == "__main__":
    E4.X.make_net, E4.X.score, E4.X.phase_batch = E4.make_net, E4.score, phase_batch
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.arm, a.small, a.steps = "dense-replayall", True, None
        E4.X.run(a)
