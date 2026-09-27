#!/usr/bin/env python3
"""Source-only qualification after the 6k plain source guard failed.

No maze is generated or scored here. The source guard uses a new 200/200
panel, separate from the dev panels used to choose the source budget.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch

import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_net as N

GUARD_SEED = D.SOURCE_SEED + 300


def main(arm, seed, steps, out, checkpoint=None, prior_train_seconds=0):
    t0 = time.monotonic()
    if checkpoint is None:
        torch.manual_seed(seed)
        rng = random.Random(7000000 + seed)
        practice = N.Practice(arm, seed, steps)
        for step in range(1, steps + 1):
            practice.step(D.source_batch(rng, 64))
            if step % 1000 == 0:
                print(json.dumps({"phase": "source_qualification", "arm": arm, "seed": seed,
                                  "step": step, "seconds": round(time.monotonic() - t0)}), flush=True)
        net = practice.net
    else:
        net = B.load_model(checkpoint, arm)
    if arm == "loop":
        source_dev = D.old_panels(D.SOURCE_SEED + 100)
        fixed_counts = {str(depth): sum(B.score(net, v, depth)["fixed_right"] for v in source_dev.values())
                        for depth in B.DEPTHS}
        fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
        sweep = None
    else:
        fixed_counts, fixed_depth = {}, 1
        sweep = B.source_plain_lr_sweep(net, seed)
    old = {k: B.score(net, v, fixed_depth) for k, v in D.old_panels(GUARD_SEED).items()}
    result = {"arm": arm, "seed": seed, "source_steps": steps, "source_batch": 64,
              "source_guard_seed": GUARD_SEED, "weights": net.weight_count(),
              "persistent_coefficients": net.weight_count(), "fixed_depth": fixed_depth,
              "fixed_source_dev": fixed_counts, "plain_lr_sweep": sweep,
              "gradient_check": B.gradient_check(net, seed), "old": old,
              "train_seconds": prior_train_seconds + time.monotonic() - t0,
              "reused_source_pilot": str(checkpoint) if checkpoint else None}
    out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), out / "source.pt")
    B.dump(out / "source.json", result)
    print(json.dumps({"phase": "source_qualification_done", "arm": arm, "seed": seed,
                      "old": {k: v["right"] for k, v in old.items()},
                      "seconds": round(result["train_seconds"])}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--arm", choices=("loop", "plain"), required=True)
    p.add_argument("--seed", type=int, choices=(0, 1), required=True)
    p.add_argument("--steps", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--from-checkpoint", type=Path)
    p.add_argument("--prior-train-seconds", type=float, default=0)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.arm, a.seed, a.steps, a.out, a.from_checkpoint, a.prior_train_seconds)
