#!/usr/bin/env python3
"""lf-sz (Director helper, 2026-09-28): is it depth, or just size, that keeps old skills through a new kind?

lf-8 (scripts/claude_lf8_run.py, PASS) ran rsn-358e4's dense-replayall arm with 2 loop layers (1,646,750 weights) and 8
(6,386,174 weights) and the 8-layer loop kept old grids far better. It has 3.9x the weights, so depth and size moved
together. Here the same recipe runs at (nearly) the same total weights, changing ONLY the shape of the loop net:
  loop8    d256, 8 layers, 8 heads (6,386,174)  lf-8's loop8 again, as the same-box comparator
  loop2w   d512, 2 layers, 8 heads (6,438,814)  the 2-layer loop widened to the same weights (+0.8%)
  loop4w   d360, 4 layers, 8 heads (6,334,182)  a 4-layer loop at that size (-0.8%)
Data, phases, steps (2,500 / 2,500 / 1,500), batch 64, replay, loop schedule, dev sets and scoring are 358e4's, unchanged.
Nothing in the 358 scripts is edited; this file only sets SIZES["small"] before 358e4's run(), as claude_lf8_run.py does.

  python -B scripts/claude_lfsz_run.py run --arm loop8|loop2w|loop4w --seed S --out DIR [--threads N]
  python -B scripts/claude_lfsz_run.py selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e4_replayall as E4  # noqa: E402

X = E4.X
SHAPE = {"loop8": (256, 8), "loop2w": (512, 2), "loop4w": (360, 4)}   # (d, layers); heads stay 8
WEIGHTS = {"loop8": 6386174, "loop2w": 6438814, "loop4w": 6334182}
LF8_WEIGHTS = 6386174


def build(arm):
    d, layers = SHAPE[arm]
    X.SIZES["small"].update(d=d, layers=layers, heads=8)
    X.make_net, X.score, X.phase_batch = E4.make_net, E4.score, E4.phase_batch
    return E4.make_net("dense-replayall", "small")


def selftest():
    for arm, (d, layers) in SHAPE.items():
        net = build(arm)
        n = sum(p.numel() for p in net.parameters())
        assert len(net.blocks) == layers and n == WEIGHTS[arm], (arm, len(net.blocks), n)
        assert abs(n / LF8_WEIGHTS - 1) <= 0.02, (arm, n)
    print("lfsz selftest ok: " + ", ".join(f"{a} {WEIGHTS[a]}" for a in SHAPE) + " weights (all within 2% of loop8's)")


def main():
    if sys.argv[1:] == ["selftest"]:
        return selftest()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--arm", choices=list(SHAPE), required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threads", type=int, default=1)
    a = ap.parse_args()
    build(a.arm)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d, layers = SHAPE[a.arm]
    (out / "lfsz.json").write_text(json.dumps({"arm": a.arm, "d": d, "layers": layers, "heads": 8, "seed": a.seed,
                                               "threads": a.threads}), encoding="utf-8")
    X.run(argparse.Namespace(cmd="run", arm="dense-replayall", seed=a.seed, out=a.out, threads=a.threads,
                             small=True, steps=None))


if __name__ == "__main__":
    main()
