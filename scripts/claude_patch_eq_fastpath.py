#!/usr/bin/env python3
"""Report only, dev only: the patch's fast path alone (PASSMARKS.md, report-only list).

For the practised patch of one seed, at k = 1, 4, 16 and 64: start from a clean copy of the
practised net, freeze every ordinary weight, make only the rung's 512 writes (one per batch of
the harness's own batches() over the ruler's own support pool), then score the 9x9 dev panel.
There is no optimizer and no update. The harness itself would refuse such a rung, which is why
this is a separate script. The holdout is never touched here.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

import torch

import claude_fewex_bench as B
import claude_fewex_data as D
import claude_fewex_eq_bench as EQ
import claude_patch_eq_plugin as P

RUNGS = (1, 4, 16, 64)


def main(seed, source, out):
    if out.exists():
        raise FileExistsError("fast-path record already written")
    B.N = P
    src = json.loads((source / "source.json").read_text())
    if (src["arm"], src["seed"], src["practice_arm"]) != ("loop", seed, "patch"):
        raise ValueError("source identity mismatch")
    depth = src["fixed_depth"]
    base = B.load_model(source / "source.pt", "loop")
    for p in base.parameters():
        p.requires_grad_(False)
    panels, banned = D.panels()
    pool, _, digest = EQ.make_pool(seed, banned)
    res = {"seed": seed, "source": str(source), "fixed_depth": depth, "support_sha256": digest,
           "panel": "dev 9x9 (300)", "ordinary_weights": "frozen, no optimizer", "rungs": {}}
    res["rungs"]["0"] = {**B.score(base, panels["dev"][9], depth), "writes": 0}
    for k in RUNGS:
        t0 = time.monotonic()
        net = copy.deepcopy(base)
        frozen = {n: p.clone() for n, p in net.named_parameters()}
        writes = rounds = 0
        for batch in EQ.batches(pool, k, seed):
            rounds += net.write_batch(batch)
            writes += 1
        unchanged = all(torch.equal(frozen[n], p) for n, p in net.named_parameters())
        if writes != EQ.N_BATCHES or not unchanged:
            raise RuntimeError("fast path must be exactly 512 writes with frozen weights")
        res["rungs"][str(k)] = {**B.score(net, panels["dev"][9], depth), "writes": writes,
                                "ordinary_weights_unchanged": unchanged,
                                "mean_write_rounds": rounds / (writes * B.MAZE_BATCH),
                                "patch_fro": {"A": float(net.patch_a.norm()), "B": float(net.patch_b.norm())},
                                "seconds": time.monotonic() - t0}
        B.dump(out.with_suffix(".partial.json"), res)
        print(json.dumps({"seed": seed, "k": k, "right9_dev": res["rungs"][str(k)]["right"]}), flush=True)
    B.dump(out, res)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(0, 1), required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=1)
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    main(a.seed, a.source, a.out)
