#!/usr/bin/env python3
"""lf-8 (asked by the Thread manager for Ben, 2026-09-27 19:36 UTC; run in the "Making things up about you" thread's
container): does the 8-layer loop forget less than the 2-block loop?

rsn-358e4's dense-replayall arm (scripts/claude_rsn358e4_replayall.py on claude_rsn358e_moe.py, "small": d256, 8 heads,
phases A grids / B sums / C mazes, every earlier kind replayed), unchanged except ONE setting:
  loop2  X.SIZES["small"]["layers"] = 2 (358e4's arm as written; 1,646,750 weights)
  loop8  X.SIZES["small"]["layers"] = 8 (same width, heads, data, steps, replay, schedule and scoring; 6,386,174 weights,
         about 3.9x, so this is a depth test, not a same-size one)
Nothing in the sleep research thread's scripts is edited; this file only sets that value before 358e4's run().

  python -B scripts/claude_lf8_run.py run --arm loop2|loop8 --seed S --out DIR [--threads N]
  python -B scripts/claude_lf8_run.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e4_replayall as E4  # noqa: E402

X = E4.X
LAYERS = {"loop2": 2, "loop8": 8}
WEIGHTS = {"loop2": 1646750, "loop8": 6386174}


def build(arm):
    X.SIZES["small"]["layers"] = LAYERS[arm]
    X.make_net, X.score, X.phase_batch = E4.make_net, E4.score, E4.phase_batch
    return E4.make_net("dense-replayall", "small")


def selftest():
    for arm in LAYERS:
        net = build(arm)
        n = sum(p.numel() for p in net.parameters())
        assert len(net.blocks) == LAYERS[arm] and n == WEIGHTS[arm], (arm, len(net.blocks), n)
    print(f"lf8 selftest ok: loop2 {WEIGHTS['loop2']} weights (358e4's dense-replayall), loop8 {WEIGHTS['loop8']}")


def main():
    if sys.argv[1:] == ["selftest"]:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--arm", choices=list(LAYERS), required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threads", type=int, default=1)
    a = ap.parse_args()
    build(a.arm)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "lf8.json").write_text(json.dumps({"arm": a.arm, "layers": LAYERS[a.arm], "seed": a.seed,
                                              "threads": a.threads}), encoding="utf-8")
    X.run(argparse.Namespace(cmd="run", arm="dense-replayall", seed=a.seed, out=a.out, threads=a.threads,
                             small=True, steps=None))


if __name__ == "__main__":
    main()
