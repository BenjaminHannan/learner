#!/usr/bin/env python3
"""Experiment 43B: does filtering the sleep gradient for "what the experiences share"
beat plain replay?  (Ben's Shared-Subspace Sleep proposal, tested against exp 42.)

Everything is automatic arithmetic on gradients; the model proposes nothing.
Same toy, new skill, replay mix and 3,000 updates as experiment 42.  The awake log has
100 raw episodes, 10 of which carry a WRONG (random) answer = noisy exceptions.
20 of the 100 are held out from sleep and only used to pick the checkpoint.

Each update: the 24 new-skill rows are split into m=4 disjoint groups of 6, one gradient
per group.  The arms differ ONLY in how the four group gradients are combined:

  plain     mean of the groups                      (= experiment-42 replay)
  sign      keep a number only if all 4 groups agree on its sign   (AND-mask)
  snr       shrink each number by signal/(signal+noise) across groups
  subspace  per weight tensor: project the mean onto the top shared direction
            (rank-1 SVD of the 4 length-normalised group gradients, via a 4x4 matrix)
  rank4     mean gradient, but each block weight's total change is cut back to rank 4
            after every update (compact update, already merged: W = W0 + rank-4)

Old-skill replay gradient is added unfiltered in every arm.
Imports CardFold, exp 42 and exp 43A read-only.  One CPU thread per process.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
from pathlib import Path

import torch
from torch import nn

import fable_cardfold_sleep as C
import fable_autosleep42 as A
import fable_lengthgate43 as G

ARMS = ("plain", "sign", "snr", "subspace", "rank4")
EPISODES, NOISY, HELD_OUT = 100, 10, 20
GROUPS = 4
RANK = 4
UPDATES = 3000
CHECK_EVERY = 250
EXTRA_LONG = 12


def make_log(seed: int, splits: C.Splits):
    rows = list(A.awake_log(seed, splits, EPISODES))
    rng = C.make_rng("sleep43b/noise", seed)
    noisy_ids = sorted(rng.sample(range(EPISODES), NOISY))
    truth = {}
    for i in noisy_ids:
        ex = rows[i]
        wrong = ex.out
        while wrong == ex.out:
            wrong = C.random_digit_string(rng, len(ex.out))
        truth[i] = ex
        rows[i] = C.Example(ex.op, ex.inp, wrong)
    order = list(range(EPISODES))
    C.make_rng("sleep43b/holdout", seed).shuffle(order)
    held = set(order[:HELD_OUT])
    train = [rows[i] for i in range(EPISODES) if i not in held]
    heldout = [rows[i] for i in range(EPISODES) if i in held]
    noisy_train = [(rows[i], truth[i]) for i in noisy_ids if i not in held]
    return train, heldout, noisy_train


def grads_of(model, rows, rng):
    loss = G.loss_fn(model, G.collate(rows, rng))
    params = [p for p in model.parameters() if p.requires_grad]
    return torch.autograd.grad(loss, params, allow_unused=True), float(loss.detach())


def combine(arm: str, stack: torch.Tensor) -> torch.Tensor:
    """stack: [GROUPS, *shape] group gradients of one parameter tensor."""
    mean = stack.mean(0)
    if arm in ("plain", "rank4"):
        return mean
    if arm == "sign":
        agree = stack.sign().sum(0).abs() == GROUPS
        return mean * agree
    if arm == "snr":
        var = stack.var(0, unbiased=True)
        return mean * (mean * mean / (mean * mean + var / GROUPS + 1e-20))
    if arm == "subspace":
        flat = stack.reshape(GROUPS, -1)
        unit = flat / (flat.norm(dim=1, keepdim=True) + 1e-20)
        _, vecs = torch.linalg.eigh(unit @ unit.T)       # 4x4, no big matrix is ever built
        direction = unit.T @ vecs[:, -1]
        direction = direction / (direction.norm() + 1e-20)
        return ((mean.reshape(-1) @ direction) * direction).reshape(mean.shape)
    raise ValueError(arm)


def scores(model, seed, splits, train, noisy_train):
    def by_length(examples, tag):
        groups = {}
        for ex in examples:
            groups.setdefault(len(ex.inp), []).append(ex)
        hits = total = 0
        for n, rows in sorted(groups.items()):
            hits += G.score(model, rows, C.make_rng(f"sleep43b/pos/{tag}/{n}", seed)) * len(rows)
            total += len(rows)
        return hits / total
    rng = C.make_rng("sleep43b/long12", seed)
    xs = set()
    while len(xs) < 100:
        xs.add(C.random_digit_string(rng, EXTRA_LONG))
    long12 = C.examples_for_program(C.CARDFOLD_OP, C.CARDFOLD, sorted(xs))
    old = [ex for _, rows in splits.regression for ex in rows]
    out = {
        "fresh": by_length(splits.test_fresh, "fresh"),
        "long_9_10": by_length(splits.test_long, "long"),
        "long_12": by_length(long12, "long12"),
        "old_skills": by_length(old, "old"),
        "seen_clean": by_length([e for e in train if all(e is not n for n, _ in noisy_train)], "seen"),
    }
    if noisy_train:
        out["noise_memorised"] = by_length([n for n, _ in noisy_train], "noisy")
        out["noise_true_answer"] = by_length([t for _, t in noisy_train], "noisytrue")
    return out


def run(seed: int, arm: str, base_path: Path, updates: int) -> dict:
    splits = C.build_splits(seed)
    C.assert_split_disjointness(splits)
    payload = torch.load(base_path, map_location="cpu", weights_only=True)
    assert int(payload["seed"]) == seed
    model = G.PosDecoder(loop=payload["arm"] == "randpos-loop")
    model.load_state_dict(payload["state"])
    train, heldout, noisy_train = make_log(seed, splits)
    before = scores(model, seed, splits, train, noisy_train)
    opt = torch.optim.AdamW(model.parameters(), lr=C.SLEEP_LR, weight_decay=C.WEIGHT_DECAY)
    w0 = {n: p.detach().clone() for n, p in model.named_parameters()
          if p.dim() == 2 and "block" in n} if arm == "rank4" else {}
    per_group = (C.BATCH_SIZE // 2) // GROUPS
    best, best_loss, best_step = None, float("inf"), -1
    agree_trace = []
    t0 = time.time()
    for step in range(updates):
        model.train()
        rng = C.make_rng(f"sleep43b/new/{step}", seed)      # same episodes in every arm
        picks = C.sample_pool(train, per_group * GROUPS, rng)
        group_grads = []
        for k in range(GROUPS):
            g, _ = grads_of(model, picks[k * per_group:(k + 1) * per_group],
                            C.make_rng(f"sleep43b/pos/{step}/{k}", seed))
            group_grads.append(g)
        old_g, _ = grads_of(model, C.replay_half(seed, step, splits),
                            C.make_rng(f"sleep43b/pos-old/{step}", seed))
        kept = total = 0.0
        for i, p in enumerate(q for q in model.parameters() if q.requires_grad):
            parts = [g[i] for g in group_grads]
            if any(x is None for x in parts):
                new = torch.zeros_like(p)
            else:
                stack = torch.stack(parts)
                new = combine(arm, stack)
                kept += float(new.norm() ** 2)
                total += float(stack.mean(0).norm() ** 2)
            p.grad = 0.5 * new + 0.5 * (old_g[i] if old_g[i] is not None else torch.zeros_like(p))
        if step % 100 == 0:
            agree_trace.append(round(kept / max(total, 1e-30), 4))
        nn.utils.clip_grad_norm_(model.parameters(), C.GRAD_CLIP)
        opt.step()
        if arm == "rank4":
            with torch.no_grad():
                for n, p in model.named_parameters():
                    if n in w0:
                        u, s, vh = torch.linalg.svd(p - w0[n], full_matrices=False)
                        p.copy_(w0[n] + (u[:, :RANK] * s[:RANK]) @ vh[:RANK])
        if (step + 1) % CHECK_EVERY == 0 or step + 1 == updates:
            model.eval()
            with torch.no_grad():
                held = float(G.loss_fn(model, G.collate(heldout, C.make_rng("sleep43b/pos-held", seed))))
            if held < best_loss:
                best, best_loss, best_step = copy.deepcopy(model.state_dict()), held, step + 1
    seconds = round(time.time() - t0, 1)
    last = scores(model, seed, splits, train, noisy_train)
    model.load_state_dict(best)
    selected = scores(model, seed, splits, train, noisy_train)
    # acceptance gate: fixed arithmetic, applied to the selected checkpoint
    accepted = selected["old_skills"] >= before["old_skills"] - 0.02
    return {"seed": seed, "arm": arm, "base": str(base_path.name), "updates": updates,
            "before": before, "last": last, "selected": selected, "selected_step": best_step,
            "heldout_loss": best_loss, "accepted_by_gate": accepted,
            "gradient_energy_kept": agree_trace, "sleep_seconds": seconds}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--base", type=Path, required=True, help="a seed*.pt file from experiment 43A")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true", help="10 updates, no claim")
    a = p.parse_args()
    torch.set_num_threads(1)
    torch.manual_seed(C.derive_seed("sleep43b/torch", a.seed) & ((1 << 63) - 1))
    r = run(a.seed, a.arm, a.base, 10 if a.smoke else UPDATES)
    r.update(smoke=a.smoke, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f"seed{a.seed}-{a.arm}.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({"seed": a.seed, "arm": a.arm, "selected": r["selected"],
                      "step": r["selected_step"], "seconds": r["sleep_seconds"]}))


if __name__ == "__main__":
    main()
