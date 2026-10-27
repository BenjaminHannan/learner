#!/usr/bin/env python3
"""rsn-358e4 report-only replay-budget arms (sleep research thread, 2026-09-27; Thread manager 00:27 UTC): the same
as scripts/claude_rsn358e4_replayall.py (unchanged, imported) with half the replay share: every 20th step instead of
every 10th (phase B 125 grids of 2,500; phase C 75 of 1,500, alternating grids and sums).

  python -B scripts/claude_rsn358e4b_halfreplay.py run --arm dense-replayall|eq-replayall --seed S --out DIR
  python -B scripts/claude_rsn358e4b_halfreplay.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e4_replayall as E4  # noqa: E402

E4.REPLAY_EVERY = 20

if __name__ == "__main__":
    E4.X.make_net, E4.X.score, E4.X.phase_batch = E4.make_net, E4.score, E4.phase_batch
    if sys.argv[1:] == ["selftest"]:
        import random
        rng = random.Random(0)
        pool = {sz: [E4.E3.E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
        E4.ST.update(kind=None, n=0, replayed={"sums": {}, "mazes": {}})
        for _ in range(2500):
            E4.phase_batch(rng, "sums", 2, pool)
        for _ in range(1500):
            E4.phase_batch(rng, "mazes", 2, pool)
        r = E4.ST["replayed"]
        assert r["sums"] == {"grids": 125} and sum(r["mazes"].values()) == 75, r
        print(f"selftest ok: half replay {r}")
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=list(E4.ARM), required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        E4.X.run(a)
