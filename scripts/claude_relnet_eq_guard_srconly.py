#!/usr/bin/env python3
"""Source guard for the relation net from source.pt alone (no resume.pt, no training).

scripts/claude_relnet_eq_guard.py asserts a resume.pt (step 12000) that was never pushed to main, so it cannot run
from a clean checkout. This variant is the same scoring block on the same saved weights and drops only the
resume.pt lines: fixed depth chosen on source dev SOURCE_SEED+100, the guard SOURCE_SEED+300, guard_fixed_right_by_depth,
the harness's one-step gradient check, the weight count, the sha256 of source.pt. Steps and seconds are recorded as
unknown: resume.pt is not on main, so this file cannot show them. Output: <dir>/source.json in the schema of
claude_sparse_practice.py, which claude_fewex_eq_bench.py adapt --source (and claude_patch_eq_ladder.py) reads.

  python3 -B scripts/claude_relnet_eq_guard_srconly.py --seed S --out artifacts/claude-relnet-eq-20260928/runs/relnet-sS
Refuses to overwrite an existing source.json, and stops before scoring if source.pt is not the file the Director
recorded (sha256 starts b2988e2a for seed 0, 115f2451 for seed 1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import torch

import claude_fewex_bench as B
import claude_fewex_data as D
import claude_relnet_eq_plugin as S

GUARD_SEED = D.SOURCE_SEED + 300
EXPECT = {0: "b2988e2a", 1: "115f2451"}
B.N = S


def main(seed, out, threads):
    sha = hashlib.sha256((out / "source.pt").read_bytes()).hexdigest()
    if not sha.startswith(EXPECT[seed]):
        raise SystemExit(f"SOURCE-PT-MISMATCH seed {seed}: sha256 {sha} does not start with {EXPECT[seed]}")
    if (out / "source.json").exists():
        raise FileExistsError(out / "source.json")
    arm = "loop"
    torch.manual_seed(seed)
    net = B.load_model(out / "source.pt", arm)      # the harness's own loader (state dict, weights_only)
    t0 = time.monotonic()
    source_dev = D.old_panels(D.SOURCE_SEED + 100)
    fixed_counts = {str(depth): sum(B.score(net, v, depth)["fixed_right"] for v in source_dev.values())
                    for depth in B.DEPTHS}
    fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
    guard = D.old_panels(GUARD_SEED)
    old = {k: B.score(net, v, fixed_depth) for k, v in guard.items()}
    guard_fixed = {k: {str(d): B.score(net, v, d)["fixed_right"] for d in B.DEPTHS} for k, v in guard.items()}
    result = {"arm": arm, "design": "relation net (claude_relnet_eq_plugin)", "seed": seed,
              "source_steps": "unknown, resume.pt not on main", "source_batch": 64, "source_guard_seed": GUARD_SEED,
              "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
              "fixed_depth": fixed_depth, "fixed_source_dev": fixed_counts, "guard_fixed_right_by_depth": guard_fixed,
              "plain_lr_sweep": None, "gradient_check": B.gradient_check(net, seed), "old": old,
              "v1_pass": all(v["right"] >= 190 for v in old.values()),
              "train_seconds": None, "train_seconds_note": "unknown, resume.pt not on main",
              "device": "cpu", "threads": threads, "torch": torch.__version__,
              "scored_by": "scripts/claude_relnet_eq_guard_srconly.py from source.pt alone (no resume.pt; the practice script crashed after saving source.pt)",
              "source_pt_sha256": sha}
    B.dump(out / "source.json", result)
    print(json.dumps({"phase": "guard_done", "seed": seed, "old": {k: v["right"] for k, v in old.items()},
                      "v1_pass": result["v1_pass"], "fixed_depth": fixed_depth,
                      "gradient_nonzero_all": result["gradient_check"]["nonzero_all"],
                      "matrix_count": result["gradient_check"]["matrix_count"],
                      "guard_fixed": guard_fixed, "source_pt_sha256": sha,
                      "score_seconds": round(time.monotonic() - t0)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, choices=(0, 1), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.seed, a.out, a.threads)
