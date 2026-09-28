#!/usr/bin/env python3
"""Breadth source practice: the ruler's 12,000-step practice, spread over TEN kinds (Director helper A, 2026-09-28).

NEEDS TORCH. NOT RUN when written (the authoring box has no torch); only `py_compile` and the pure-python
kinds selftest (claude_dir_a_kinds.py) were run there.

The ONLY change from artifacts/claude-fewex-20260927 (claude_fewex_source_qualify.py / claude_fewex_bench.source_job):
which puzzles the 12,000 batches of 64 are drawn from. Same nets (claude_fewex_net.Practice: same optimiser,
warm-up + cosine schedule, learning rate, gradient clipping, model seed = arm seed, loop training-round rng),
same total steps and batch size, same fp32 CPU. Old recipe: half sums, half Latin squares. Breadth recipe: exactly
1,200 batches of each of ten kinds (sums, Latin squares and eight new ones), shuffled, one kind and one level per
batch. Every choice made here (loop fixed depth, plain learning rate) is made on the ten practice kinds' dev
panels only; no held-out kind (maze, graph, rank) is generated or scored by this script.

Output per (arm, seed): <out>/source.pt and <out>/source.json, in the layout the ruler's loaders read, plus a
per-kind mastery guard on fresh panels (`practice` in source.json).

  python -B scripts/claude_dir_a_practice.py source --arm loop --seed 0 --out <root>/qual-loop-s0
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_a_kinds as A
import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_net as N0

_old_exact = B.exact


def _exact(item, pred):
    """The ruler's scorer calls B.exact; route the eight new kinds to their own checkers."""
    return A.check(item, pred) if item.env in A.NEW_KINDS else _old_exact(item, pred)


B.exact = _exact

RNG_SEED = 7100000          # the old recipe used 7000000 + seed; a new number because the stream itself is new
SWEEP_RNG_SEED = 9552800
GUARD_PASS = 180            # a practice kind counts as mastered at 90%: at least 180 of 200 on the fresh guard panel
MASTERED_NEED = 8           # ... and a source counts as qualified when at least 8 of the ten kinds are mastered


def kind_panel_scores(net, kind, seed, fixed_depth):
    """Guard/dev score of one kind: levels scored separately (a batch must share a shape), then summed."""
    parts = {str(lv): B.score(net, items, fixed_depth) for lv, items in A.panel(kind, seed).items()}
    return {"right": sum(p["right"] for p in parts.values()), "n": sum(p["n"] for p in parts.values()),
            "fixed_right": sum(p["fixed_right"] for p in parts.values()),
            "mean_rounds": sum(p["mean_rounds"] * p["n"] for p in parts.values()) / sum(p["n"] for p in parts.values()),
            "cap_hits": sum(p["cap_hits"] for p in parts.values()), "levels": parts}


def all_kind_scores(net, seed, fixed_depth):
    return {k: kind_panel_scores(net, k, seed, fixed_depth) for k in A.KINDS}


def mix_batch(rng, kind):
    return A.practice_batch(rng, kind, A.BATCH)


def plain_lr_sweep(net, seed):
    """Pick the plain net's adaptation learning rate from practice-kind puzzles only (protocol of the ruler:
    64 steps of the source objective at each candidate, score on dev at depth 1, sum, ties to the lower rate)."""
    sched = A.schedule(seed)
    candidates = {}
    for lr in B.PLAIN_LRS:
        clone = copy.deepcopy(net)
        opt = torch.optim.AdamW(clone.parameters(), lr=lr, weight_decay=.1, betas=(.9, .95))
        rng = random.Random(SWEEP_RNG_SEED + seed)
        for i in range(64):
            clone.train()
            loss = N0.train_loss(clone, A.practice_batch(rng, sched[i % len(sched)], 32), rng)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(clone.parameters(), 1.)
            opt.step()
        candidates[str(lr)] = sum(v["right"] for v in all_kind_scores(clone, A.DEV_SEED, 1).values())
    chosen = max(B.PLAIN_LRS, key=lambda lr: (candidates[str(lr)], -lr))
    return {"chosen": chosen, "source_dev_counts": candidates}


def source_job(arm, seed, steps, out):
    t0 = time.monotonic()
    torch.manual_seed(seed)
    rng = random.Random(RNG_SEED + seed)
    sched = A.schedule(seed)
    assert steps == A.STEPS == len(sched)
    p = N0.Practice(arm, seed, steps)
    for step in range(1, steps + 1):
        p.step(mix_batch(rng, sched[step - 1]))
        if step % 500 == 0:
            print(json.dumps({"phase": "source", "arm": arm, "seed": seed, "step": step,
                              "seconds": round(time.monotonic() - t0)}), flush=True)
    net = p.net
    if arm == "loop":                                   # fixed depth: chosen on the ten kinds' DEV panels
        fixed_counts = {}
        for depth in B.DEPTHS:
            fixed_counts[str(depth)] = sum(v["fixed_right"] for v in all_kind_scores(net, A.DEV_SEED, depth).values())
        fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
        sweep = None
    else:
        fixed_counts, fixed_depth = {}, 1
        sweep = plain_lr_sweep(net, seed)
    guard = all_kind_scores(net, A.GUARD_SEED, fixed_depth)
    mastered = sorted(k for k, v in guard.items() if v["right"] >= GUARD_PASS)
    old = B.source_scores(net, fixed_depth)              # the current 2-kind panels (sums4, grids5), for comparison
    res = {"arm": arm, "seed": seed, "source_steps": steps, "source_batch": A.BATCH, "recipe": "breadth10",
           "steps_per_kind": A.STEPS_PER_KIND, "weights": net.weight_count(),
           "persistent_coefficients": net.weight_count(), "fixed_depth": fixed_depth,
           "fixed_source_dev": fixed_counts, "plain_lr_sweep": sweep,
           "gradient_check": B.gradient_check(net, seed), "old": old,
           "practice": {k: {"right": v["right"], "n": v["n"], "fixed_right": v["fixed_right"],
                            "mean_rounds": v["mean_rounds"], "cap_hits": v["cap_hits"]} for k, v in guard.items()},
           "mastered_kinds": mastered, "mastered_count": len(mastered),
           "V1a_qualified": len(mastered) >= MASTERED_NEED,
           "train_seconds": time.monotonic() - t0}
    out.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), out / "source.pt")
    B.dump(out / "source.json", res)
    print(json.dumps({"phase": "source_done", "arm": arm, "seed": seed, "mastered": len(mastered),
                      "practice_right_of_200": {k: v["right"] for k, v in guard.items()},
                      "old_right_of_200": {k: v["right"] for k, v in old.items()},
                      "seconds": round(res["train_seconds"])}), flush=True)


def selftest():
    """Torch part: one loop and one plain net take three real steps of every kind, and the scorer runs."""
    rng = random.Random(0)
    for arm in ("loop", "plain"):
        p = N0.Practice(arm, 0, A.STEPS)
        for kind in A.KINDS:
            loss = p.step(mix_batch(rng, kind))
            assert loss == loss, (arm, kind)
        sc = kind_panel_scores(p.net, "assoc", A.DEV_SEED, 16)
        assert sc["n"] == 200
        print(json.dumps({"selftest": "ok", "arm": arm, "weights": p.net.weight_count()}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("selftest", "source"))
    ap.add_argument("--arm", choices=("loop", "plain"))
    ap.add_argument("--seed", type=int, choices=(0, 1))
    ap.add_argument("--out", type=Path)
    ap.add_argument("--threads", type=int, default=1)
    a = ap.parse_args()
    B.N = N0
    torch.set_num_threads(a.threads)
    if a.cmd == "selftest":
        selftest()
    else:
        if None in (a.arm, a.seed, a.out):
            ap.error("--arm --seed --out required")
        if (a.out / "source.json").exists():
            raise FileExistsError("source already written")
        source_job(a.arm, a.seed, A.STEPS, a.out)


if __name__ == "__main__":
    main()
