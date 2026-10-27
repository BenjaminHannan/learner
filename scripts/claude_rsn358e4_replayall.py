#!/usr/bin/env python3
"""rsn-358e4 (sleep research thread, 2026-09-27): the trade rsn-358e3 showed only in report rows, put on a graded
mark at equal size. Replay protected only what was replayed (dense-replay grids5 184/172 after B, then 0/0 after
mazes with no replay), while frozen experts kept a skill nobody practised (moe-grow-replay 185/160 after mazes) but
learned new kinds badly (sums4 136/67, maze7 9/0).

Here both arms replay EVERY earlier kind in every phase (as the sleep design says: practise everything checkable):
  phase B (sums):  every 10th step is a grids batch                          (250 of 2,500; as rsn-358e3)
  phase C (mazes): every 10th step is an earlier-kind batch, alternating grids / sums (150 of 1,500: 75 + 75)
Batches come from the phase-A grids training pool and the code-made sums generator, never a dev set.

Arms, equal total weights:
  dense-replayall   358e's dense loop (1,646,750 weights), all weights train in every phase
  eq-replayall      358e3's moe-grow-eq (1,654,446 weights): 12 experts of hidden 4d/12; one router group and its 4
                    experts open per phase, everything earlier frozen (352,944 trainable per later phase)

  python -B scripts/claude_rsn358e4_replayall.py run --arm dense-replayall|eq-replayall --seed S --out DIR
  python -B scripts/claude_rsn358e4_replayall.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e3_replay as E3  # noqa: E402  (arms, eq layout, grow/freeze, scoring hooks)

X = E3.X
REPLAY_EVERY = 10
ST = {"kind": None, "n": 0, "replayed": {"sums": {}, "mazes": {}}}


def phase_batch(rng, kind, bsz, pool):
    if kind != ST["kind"]:
        ST["kind"], ST["n"] = kind, 0
    ST["n"] += 1
    if kind in ("sums", "mazes") and ST["n"] % REPLAY_EVERY == 0:
        if kind == "sums":
            old = "grids"
        else:
            old = ("grids", "sums")[(ST["n"] // REPLAY_EVERY) % 2]
        ST["replayed"][kind][old] = ST["replayed"][kind].get(old, 0) + 1
        return E3._phase_batch(rng, old, bsz, pool)
    return E3._phase_batch(rng, kind, bsz, pool)


ARM = {"dense-replayall": "dense-replay", "eq-replayall": "moe-grow-eq-replay"}


def make_net(arm, size):
    net = E3.make_net(ARM[arm], size)
    E3.ST["arm"] = ARM[arm].replace("-replay", "")              # E3's own replay hook off; ours runs instead
    ST.update(kind=None, n=0, replayed={"sums": {}, "mazes": {}})
    return net


def score(net, dev, device):
    out = E3.score(net, dev, device)
    if E3.ST["calls"] in (3, 4):
        out["replayed"] = {k: dict(v) for k, v in ST["replayed"].items()}   # a snapshot (ADDENDUM-1 fix)
    return out


def selftest():
    import random
    rng = random.Random(0)
    pool = {sz: [E3.E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
    ST.update(kind=None, n=0, replayed={"sums": {}, "mazes": {}})
    for _ in range(2500):
        phase_batch(rng, "sums", 2, pool)
    for _ in range(1500):
        phase_batch(rng, "mazes", 2, pool)
    assert ST["replayed"] == {"sums": {"grids": 250}, "mazes": {"grids": 75, "sums": 75}}, ST["replayed"]
    counts = {k: dict(v) for k, v in ST["replayed"].items()}
    for arm in ARM:
        net = make_net(arm, "small")
        assert E3.ST["arm"] in ("dense", "moe-grow-eq")
    print(f"selftest ok: replay {counts}; arms build; E3's own replay hook is off")


if __name__ == "__main__":
    X.make_net, X.score, X.phase_batch = make_net, score, phase_batch
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=list(ARM), required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        X.run(a)
