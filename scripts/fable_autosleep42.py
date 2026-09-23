#!/usr/bin/env python3
"""Experiment 42: AUTOMATIC sleep on the CardFold toy.

Ben's ruling (2026-09-21): the model never proposes a rule and never decides what
to store.  Sleep is a fixed mathematical procedure over raw experience.

So there is no lesson and no program search here.  Every arm replays the RAW awake
log (input -> answer pairs of the new skill) mixed half-and-half with old-skill
replay, exactly like the registered CardFold R arm.  The arms differ only in

  * how much raw experience there was      (20 / 100 / 400 awake episodes)
  * squeeze pressure                        (weight decay 0.01 vs 0.10)
  * which episodes get replayed             (uniform vs highest prediction error)
  * how long sleep lasts                    (3,000 vs 12,000 updates)

Reuses the saved base checkpoints of the registered CardFold run; imports the
CardFold script read-only.  One CPU thread per process.
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

# name: (awake episodes, weight decay, replay rule, sleep updates)
ARMS = {
    "R20": (20, 0.01, "uniform", 3000),
    "R100": (100, 0.01, "uniform", 3000),
    "R400": (400, 0.01, "uniform", 3000),
    "R100-squeeze": (100, 0.10, "uniform", 3000),
    "R100-surprise": (100, 0.01, "surprise", 3000),
    "R100-squeeze-long": (100, 0.10, "uniform", 12000),
    "R20-squeeze-long": (20, 0.10, "uniform", 12000),
}
SURPRISE_REFRESH = 100  # re-measure each episode's prediction error every N updates


def awake_log(seed: int, splits: C.Splits, count: int) -> tuple[C.Example, ...]:
    """First 20 = the registered awake log; the rest are further raw episodes,
    input-disjoint from every test split, the old log and the S-arm practice set."""
    rows = list(splits.awake)
    if count > len(rows):
        used = set(splits.reserved_short_inputs())
        rng = C.make_rng("awake/log-extended", seed)
        extra = C.generate_unique_inputs(rng, count - len(rows), C.TRAIN_LENGTHS, used)
        rows += list(C.examples_for_program(C.CARDFOLD_OP, C.CARDFOLD, extra))
    assert len(rows) == count and len({r.inp for r in rows}) == count
    tests = {e.inp for e in splits.test_fresh} | {e.inp for e in splits.test_long}
    assert not tests & {r.inp for r in rows}
    return tuple(rows)


@torch.no_grad()
def per_episode_loss(model, log, seed: int, step: int) -> list[float]:
    model.eval()
    out = []
    for i in range(0, len(log), 64):
        chunk = log[i:i + 64]
        for j, ex in enumerate(chunk):
            batch = C.collate((ex,), C.make_rng(f"auto/surprise-pos/{step}/{i + j}", seed))
            out.append(float(C.masked_loss(model, batch)))
    model.train()
    return out


def run_arm(base, name: str, seed: int, splits: C.Splits) -> dict:
    count, decay, rule, updates = ARMS[name]
    log = awake_log(seed, splits, count)
    model = copy.deepcopy(base)
    opt = torch.optim.AdamW(model.parameters(), lr=C.SLEEP_LR, weight_decay=decay)
    half = C.BATCH_SIZE // 2
    weights = None
    losses = []
    t0 = time.time()
    for step in range(updates):
        rng = C.make_rng(f"auto/new/{name}/{step}", seed)
        if rule == "surprise":
            if step % SURPRISE_REFRESH == 0:
                weights = [x + 1e-4 for x in per_episode_loss(model, log, seed, step)]
            new = tuple(rng.choices(log, weights=weights, k=half))
        else:
            new = C.sample_pool(log, half, rng)
        rows = new + C.replay_half(seed, step, splits)
        batch = C.collate(rows, C.make_rng(f"auto/positions/{step}", seed))
        losses.append(C.train_step(model, opt, batch))
    regression, reg_mean = C.score_regression(model, splits)
    return {
        "arm": name, "awake_episodes": count, "weight_decay": decay,
        "replay_rule": rule, "sleep_updates": updates,
        "fresh": C.score(model, splits.test_fresh),
        "long": C.score(model, splits.test_long),
        "seen": C.score(model, log),
        "old_skills": reg_mean, "old_skills_by_op": regression,
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
    torch.manual_seed(C.derive_seed("auto/torch", a.seed))
    if a.smoke:
        ARMS[a.arm] = ARMS[a.arm][:3] + (5,)
    splits = C.build_splits(a.seed)
    C.assert_split_disjointness(splits)
    base = C.load_base(a.seed, a.base_dir)
    _, base_old = C.score_regression(base, splits)
    r = run_arm(base, a.arm, a.seed, splits)
    r.update(seed=a.seed, base_old_skills=base_old, smoke=a.smoke,
             script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{a.arm}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({k: r[k] for k in ("seed", "arm", "fresh", "long", "seen", "old_skills", "base_old_skills", "seconds")}))


if __name__ == "__main__":
    main()
