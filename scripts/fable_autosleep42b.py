#!/usr/bin/env python3
"""Experiment 42b: automatic sleep that may only make a SMALL change.

Same raw-replay sleep as experiment 42 (no lesson, no rule search, nothing chosen by
the model).  The one thing changed: which numbers sleep is allowed to alter.

  embed  only the new skill's own word vector (160 numbers); every old weight frozen.
         The new skill can then only be "a new way of calling what I already know".
  norms  that vector plus the layer-norm gains/biases (a few thousand numbers).

A small allowed change is a purely mathematical preference for simple explanations
(few bits), and it cannot damage old skills by construction in the embed arm.
Imports experiments 42 and CardFold read-only.  One CPU thread per process.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
from pathlib import Path

import torch

import fable_cardfold_sleep as C
import fable_autosleep42 as A

# name: (awake episodes, what may change, sleep updates)
ARMS = {
    "R20-embed": (20, "embed", 3000),
    "R100-embed": (100, "embed", 3000),
    "R20-norms": (20, "norms", 3000),
    "R100-norms": (100, "norms", 3000),
}
SLEEP_LR = 1.0e-2  # few numbers move, so a larger step; fixed before any run


def run_arm(base, name: str, seed: int, splits: C.Splits) -> dict:
    count, scope, updates = ARMS[name]
    log = A.awake_log(seed, splits, count)
    model = copy.deepcopy(base)
    op_row = C.op_token_id(C.CARDFOLD_OP)
    for pname, param in model.named_parameters():
        keep = pname == "token_embedding.weight" or (scope == "norms" and "norm" in pname)
        param.requires_grad_(keep)
    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=SLEEP_LR, weight_decay=0.0)
    frozen_rows = model.token_embedding.weight.detach().clone()
    rows_mask = torch.ones(frozen_rows.shape[0], dtype=torch.bool)
    rows_mask[op_row] = False
    changed = sum(p.numel() for p in trainable) - int(rows_mask.sum()) * frozen_rows.shape[1]
    half = C.BATCH_SIZE // 2
    losses = []
    t0 = time.time()
    for step in range(updates):
        rng = C.make_rng(f"auto/new/{name}/{step}", seed)
        rows = C.sample_pool(log, half, rng) + C.replay_half(seed, step, splits)
        batch = C.collate(rows, C.make_rng(f"auto/positions/{step}", seed))
        losses.append(C.train_step(model, opt, batch))
        with torch.no_grad():  # every word vector except the new skill's stays as it was
            model.token_embedding.weight[rows_mask] = frozen_rows[rows_mask]
    regression, reg_mean = C.score_regression(model, splits)
    return {
        "arm": name, "awake_episodes": count, "may_change": scope, "numbers_changed": changed,
        "sleep_updates": updates,
        "fresh": C.score(model, splits.test_fresh), "long": C.score(model, splits.test_long),
        "seen": C.score(model, log), "old_skills": reg_mean, "old_skills_by_op": regression,
        "tail_loss": sum(losses[-50:]) / 50, "seconds": round(time.time() - t0, 1),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm", choices=sorted(ARMS), required=True)
    p.add_argument("--base-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="5 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(C.derive_seed("auto42b/torch", a.seed))
    if a.smoke:
        ARMS[a.arm] = ARMS[a.arm][:2] + (5,)
    splits = C.build_splits(a.seed)
    C.assert_split_disjointness(splits)
    base = C.load_base(a.seed, a.base_dir)
    _, base_old = C.score_regression(base, splits)
    r = run_arm(base, a.arm, a.seed, splits)
    r.update(seed=a.seed, base_old_skills=base_old, smoke=a.smoke,
             script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{a.arm}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({k: r[k] for k in ("seed", "arm", "numbers_changed", "fresh", "long", "seen",
                                        "old_skills", "base_old_skills", "seconds")}))


if __name__ == "__main__":
    main()
