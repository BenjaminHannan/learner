#!/usr/bin/env python3
"""Source guard for the relation net, from a saved source.pt (no training).

claude_relnet_eq_practice.py finished its 12,000 steps and saved source.pt, then crashed in the result block
(it read S.DEVICE, which this plug-in does not have, a line copied from the sparse script), so its guard scores were
lost. This script runs exactly that script's scoring block on the saved weights: fixed depth chosen on source dev
SOURCE_SEED+100, the guard SOURCE_SEED+300, guard_fixed_right_by_depth, the harness's one-step gradient check, the
weight count. It adds the sha256 of source.pt and the steps and seconds stored in resume.pt. Output:
<dir>/source.json, in the schema of claude_sparse_practice.py, which claude_fewex_eq_bench.py adapt --source reads.
The plug-in is CPU only, so device is recorded as "cpu".
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
B.N = S


def main(seed, out):
    arm = "loop"
    torch.manual_seed(seed)
    net = B.load_model(out / "source.pt", arm)      # the harness's own loader (state dict, weights_only)
    st = torch.load(out / "resume.pt", map_location="cpu", weights_only=False)
    assert st["step"] == 12000, st["step"]
    t0 = time.monotonic()
    source_dev = D.old_panels(D.SOURCE_SEED + 100)
    fixed_counts = {str(depth): sum(B.score(net, v, depth)["fixed_right"] for v in source_dev.values())
                    for depth in B.DEPTHS}
    fixed_depth = max(B.DEPTHS, key=lambda d: (fixed_counts[str(d)], -d))
    old = {k: B.score(net, v, fixed_depth) for k, v in D.old_panels(GUARD_SEED).items()}
    guard_fixed = {k: {str(d): B.score(net, v, d)["fixed_right"] for d in B.DEPTHS}
                   for k, v in D.old_panels(GUARD_SEED).items()}
    result = {"arm": arm, "design": "relation net (claude_relnet_eq_plugin)", "seed": seed,
              "source_steps": st["step"], "source_batch": 64, "source_guard_seed": GUARD_SEED,
              "weights": net.weight_count(), "persistent_coefficients": net.weight_count(),
              "fixed_depth": fixed_depth, "fixed_source_dev": fixed_counts, "guard_fixed_right_by_depth": guard_fixed,
              "plain_lr_sweep": None, "gradient_check": B.gradient_check(net, seed), "old": old,
              "v1_pass": all(v["right"] >= 190 for v in old.values()),
              "train_seconds": st["seconds"], "train_seconds_note": "from resume.pt at step 12000 (sums the segments across the restarts)",
              "device": "cpu", "threads": torch.get_num_threads(),
              "scored_by": "scripts/claude_relnet_eq_guard.py from source.pt (the practice script crashed after saving it)",
              "source_pt_sha256": hashlib.sha256((out / "source.pt").read_bytes()).hexdigest()}
    B.dump(out / "source.json", result)
    print(json.dumps({"phase": "guard_done", "seed": seed, "old": {k: v["right"] for k, v in old.items()},
                      "v1_pass": result["v1_pass"], "fixed_depth": fixed_depth,
                      "gradient_nonzero_all": result["gradient_check"]["nonzero_all"],
                      "matrix_count": result["gradient_check"]["matrix_count"],
                      "guard_fixed": guard_fixed, "score_seconds": round(time.monotonic() - t0)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, choices=(0, 1), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--threads", type=int, default=1)
    a = p.parse_args()
    torch.set_num_threads(a.threads)
    main(a.seed, a.out)
