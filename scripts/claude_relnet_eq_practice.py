#!/usr/bin/env python3
"""Qualified source practice for Test C on the equal-practice ruler (the relation net as the loop) (ADDENDUM-3 recipe).

This is claude_fewex_source_qualify.main with the plug-in's Practice and Net:
12,000 batches of 64 sums or grids, 1e-3 warm-up/cosine, source RNG 7000000+seed,
fixed depth chosen on source dev SOURCE_SEED+100, V1 judged on the untouched
guard SOURCE_SEED+300, and the harness's one-step gradient check. No maze is
generated or scored here. Adds only a resumable checkpoint every 1,000 steps
(it restores the optimizer, schedule and both RNG streams) and the sha256 of
the saved weights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import torch

import claude_fewex_bench as B
import claude_fewex_data as D
import claude_relnet_eq_plugin as S

GUARD_SEED = D.SOURCE_SEED + 300
B.N = S   # the harness's score() and gradient_check() use the plug-in


def main(seed, steps, out):
    out.mkdir(parents=True, exist_ok=True)
    arm = "loop"
    ck = out / "resume.pt"
    torch.manual_seed(seed)
    rng = random.Random(7000000 + seed)
    practice = S.Practice(arm, seed, steps)
    start, prior = 0, 0.0
    if ck.exists():
        st = torch.load(ck, map_location="cpu", weights_only=False)
        practice.net.load_state_dict(st["net"])
        practice.opt.load_state_dict(st["opt"])
        practice.sched.load_state_dict(st["sched"])
        practice.round_rng.setstate(st["round_rng"])
        rng.setstate(st["source_rng"])
        start, prior = st["step"], st["seconds"]
    t0 = time.monotonic()
    losses = []
    for step in range(start + 1, steps + 1):
        losses.append(practice.step(D.source_batch(rng, 64)))
        if step % 1000 == 0:
            secs = prior + time.monotonic() - t0
            torch.save({"net": practice.net.state_dict(), "opt": practice.opt.state_dict(),
                        "sched": practice.sched.state_dict(), "round_rng": practice.round_rng.getstate(),
                        "source_rng": rng.getstate(), "step": step, "seconds": secs}, ck)
            print(json.dumps({"phase": "relnet_eq_practice", "seed": seed, "step": step,
                              "loss_mean_last": sum(losses) / len(losses), "seconds": round(secs)}), flush=True)
            losses = []
    net = practice.net
    train_seconds = prior + time.monotonic() - t0
    source_dev = D.old_panels(D.SOURCE_SEED + 100)
    fixed_counts = {str(depth): sum(B.score(net, v, depth)["fixed_right"] for v in source_dev.values())
                    for depth in B.DEPTHS}
    fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
    old = {k: B.score(net, v, fixed_depth) for k, v in D.old_panels(GUARD_SEED).items()}
    # report-only: fixed-depth accuracy on the untouched guard at every harness depth (does forcing 48 rounds decay sums?)
    guard_fixed = {k: {str(d): B.score(net, v, d)["fixed_right"] for d in B.DEPTHS}
                   for k, v in D.old_panels(GUARD_SEED).items()}
    torch.save(net.state_dict(), out / "source.pt")
    result = {"arm": arm, "design": "relation net (claude_relnet_eq_plugin)", "seed": seed,
              "source_steps": steps, "source_batch": 64, "source_guard_seed": GUARD_SEED,
              "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
              "fixed_depth": fixed_depth, "fixed_source_dev": fixed_counts, "guard_fixed_right_by_depth": guard_fixed, "plain_lr_sweep": None,
              "gradient_check": B.gradient_check(net, seed), "old": old,
              "v1_pass": all(v["right"] >= 190 for v in old.values()),
              "train_seconds": train_seconds, "device": str(S.DEVICE),
              "threads": torch.get_num_threads(),
              "source_pt_sha256": hashlib.sha256((out / "source.pt").read_bytes()).hexdigest()}
    B.dump(out / "source.json", result)
    print(json.dumps({"phase": "relnet_eq_practice_done", "seed": seed,
                      "old": {k: v["right"] for k, v in old.items()}, "v1_pass": result["v1_pass"],
                      "seconds": round(train_seconds)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, choices=(0, 1), required=True)
    p.add_argument("--steps", type=int, default=12000)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.seed, a.steps, a.out)
