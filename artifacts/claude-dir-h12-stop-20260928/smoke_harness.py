#!/usr/bin/env python3
"""Harness-level smoke for the H12 plug-in (needs torch; CPU, 1 thread). Not a test of the result.

Runs the equal-practice harness's own adapt_job (scripts/claude_fewex_eq_bench.py, unedited) with the
plug-in on a FAKE random-init source net, shrunk to one rung (k=1), 2 batches (8 updates) and a 64-maze
pool, by overriding the harness's module constants in this process only. It shows that the plug-in is
picked up, the update-count check passes, and adapt.json is written with the fields the marks read.
Usage: python -B artifacts/claude-dir-h12-stop-20260928/smoke_harness.py <scratch dir>
"""
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import claude_dir_h12_stop as H  # noqa: E402
import claude_fewex_eq_bench as EQ  # noqa: E402

EQ.B.N = H
torch.set_num_threads(1)
scratch = Path(sys.argv[1])
src = scratch / "fake-source"
src.mkdir(parents=True, exist_ok=True)
torch.manual_seed(0)
torch.save(H.Net("loop").state_dict(), src / "source.pt")
json.dump({"arm": "loop", "seed": 0, "fixed_depth": 16, "plain_lr_sweep": None,
           "old": {"sums4": {"right": 200}, "grids5": {"right": 200}}, "gradient_check": {"nonzero_all": True}},
          open(src / "source.json", "w"))
EQ.RUNGS, EQ.N_BATCHES, EQ.N_UPDATES = (1,), 2, 8


def small_pool(seed, banned):
    rng, seen = random.Random(EQ.POOL_SEED + seed), set()
    return [EQ.D.unique_maze(rng, 9, banned, seen) for _ in range(64)], seen, "smoke"


EQ.make_pool = small_pool
t0 = time.time()
EQ.adapt_job("loop", 0, "pre", src, scratch / "smoke-out")
r = json.load(open(scratch / "smoke-out" / "adapt.json"))
print(json.dumps({"smoke": "ok", "seconds": round(time.time() - t0), "updates_checked": r["optimizer_updates_per_rung"],
                  "weights": r["weights"], "cold_9x9": r["rungs"]["0"]["9"], "after_8_updates_9x9": r["rungs"]["1"]["9"]}))
