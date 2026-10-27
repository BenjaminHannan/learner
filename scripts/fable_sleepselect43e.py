#!/usr/bin/env python3
"""Experiment 43E: how should sleep pick its checkpoint?  (and rank-4 vs plain, clean data)

43B's fixed rule "keep the checkpoint with the lowest held-out LOSS" picked the very
first check (update 250) in all 15 runs, so every arm was judged almost before it had
learned anything.  This experiment goes back to Experiment 42's exact setting
(registered base, 100 clean raw episodes, 3,000 updates, half new / half old replay)
and changes one thing: 20 of the 100 episodes are held out, and at every 250 updates
we record held-out loss, held-out exact match, and the real test score.  Afterwards the
two automatic rules are compared on the same run:

  loss rule    lowest held-out loss
  match rule   highest held-out exact match, ties -> the LATER check, never before update 1,000

Arms: plain (Experiment-42 replay) and rank4 (each block matrix's total change is cut
back to rank 4 after every update).  Imports CardFold and exp 42 read-only.
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

ARMS = ("plain", "rank4")
EPISODES, HELD_OUT, RANK = 100, 20, 4
UPDATES, CHECK_EVERY, MIN_UPDATES = 3000, 250, 1000


def run(seed: int, arm: str, base_dir: Path, updates: int) -> dict:
    splits = C.build_splits(seed)
    C.assert_split_disjointness(splits)
    base = C.load_base(seed, base_dir)
    _, base_old = C.score_regression(base, splits)
    log = list(A.awake_log(seed, splits, EPISODES))
    order = list(range(EPISODES))
    C.make_rng("sleep43e/holdout", seed).shuffle(order)
    held = [log[i] for i in sorted(order[:HELD_OUT])]
    train = [log[i] for i in sorted(order[HELD_OUT:])]
    model = copy.deepcopy(base)
    opt = torch.optim.AdamW(model.parameters(), lr=C.SLEEP_LR, weight_decay=C.WEIGHT_DECAY)
    w0 = {n: p.detach().clone() for n, p in model.named_parameters()
          if p.dim() == 2 and n.startswith("blocks.")} if arm == "rank4" else {}
    half = C.BATCH_SIZE // 2
    checks = []
    t0 = time.time()
    for step in range(updates):
        rng = C.make_rng(f"sleep43e/new/{step}", seed)             # same rows in both arms
        rows = C.sample_pool(train, half, rng) + C.replay_half(seed, step, splits)
        C.train_step(model, opt, C.collate(rows, C.make_rng(f"sleep43e/positions/{step}", seed)))
        if w0:
            with torch.no_grad():
                for n, p in model.named_parameters():
                    if n in w0:
                        u, s, vh = torch.linalg.svd(p - w0[n], full_matrices=False)
                        p.copy_(w0[n] + (u[:, :RANK] * s[:RANK]) @ vh[:RANK])
        if (step + 1) % CHECK_EVERY == 0:
            model.eval()
            with torch.no_grad():
                loss = float(C.masked_loss(model, C.collate(held, C.make_rng("sleep43e/pos-held", seed))))
            _, old = C.score_regression(model, splits)
            checks.append({"update": step + 1, "heldout_loss": loss,
                           "heldout_match": C.score(model, held),
                           "fresh": C.score(model, splits.test_fresh),
                           "long": C.score(model, splits.test_long), "old_skills": old})
    by_loss = min(checks, key=lambda c: c["heldout_loss"])
    eligible = [c for c in checks if c["update"] >= MIN_UPDATES] or checks
    by_match = max(eligible, key=lambda c: (c["heldout_match"], c["update"]))
    best = max(checks, key=lambda c: c["fresh"])
    return {"seed": seed, "arm": arm, "updates": updates, "base_old_skills": base_old,
            "checks": checks, "picked_by_loss": by_loss, "picked_by_match": by_match,
            "best_possible": best, "sleep_seconds": round(time.time() - t0, 1)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--base-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="250 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(C.derive_seed("sleep43e/torch", a.seed) & ((1 << 63) - 1))
    r = run(a.seed, a.arm, a.base_dir, 250 if a.smoke else UPDATES)
    r.update(smoke=a.smoke, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{a.arm}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({"seed": a.seed, "arm": a.arm,
                      "loss_rule": [r["picked_by_loss"]["update"], r["picked_by_loss"]["fresh"]],
                      "match_rule": [r["picked_by_match"]["update"], r["picked_by_match"]["fresh"]],
                      "best": [r["best_possible"]["update"], r["best_possible"]["fresh"]],
                      "seconds": r["sleep_seconds"]}))


if __name__ == "__main__":
    main()
