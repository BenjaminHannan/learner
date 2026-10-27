#!/usr/bin/env python3
"""SL source stage: the qualified sums-and-grids source net, built exactly as claude_fewex_source_qualify.py builds it
(loop arm, 12,000 steps, batch 64, seeds 0 and 1), but with the plug-in's label-free stop target (claude_dir_sl_stop.py).

Writes <out>/source.pt and <out>/source.json in the qualified format (so the sealed equal-practice harness accepts it),
plus fields "sl_target" and "sl_target_stats" added AFTER the qualified fields are written (nothing qualified is altered).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

import claude_dir_sl_stop as P
import claude_fewex_bench as B
import claude_fewex_source_qualify as Q

STEPS = 12000


def main(seed, out, steps=STEPS, threads=1):
    torch.set_num_threads(threads)
    B.N = P          # gradient_check, score and tensors resolve through the plug-in (its train_loss is the changed one)
    Q.N = P          # Practice comes from the plug-in
    for k in P.STATS:
        P.STATS[k] = 0
    Q.main("loop", seed, steps, out)
    path = Path(out) / "source.json"
    res = json.loads(path.read_text())
    res["sl_target"] = "stable-now: arg-max on every fill cell equals the round-48 arg-max (claude_dir_sl_stop.py)"
    res["sl_target_stats"] = dict(P.STATS)
    B.dump(path, res)
    print(json.dumps({"phase": "sl_source_done", "seed": seed, "steps": steps, "stats": dict(P.STATS)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, choices=(0, 1), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--steps", type=int, default=STEPS, help="12000 for the real run; smaller only for a smoke test")
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    main(a.seed, a.out, a.steps, a.threads)
