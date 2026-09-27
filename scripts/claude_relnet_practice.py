#!/usr/bin/env python3
"""relnet practice gate (2026-09-27): train the relation net (or its same-size loop) on sums and grids with the
xfer-1 source recipe, then score the race's source guard.

Recipe = scripts/claude_xfer1_bench.py run_practice + scripts/claude_xfer1_net.py Practice, unchanged:
6,000 batches of 64, each batch all sums (1-4 digits) or all Latin grids (4x4/5x5, legend format), stream
Random(7000000 + seed); AdamW lr 1e-3 (--lr for the disclosed sweep), wd 0.1, betas (0.9, 0.95), 200-step warm-up then
cosine, clip 1.0; loss = cell CE + 0.5 x stop-head BCE, 1-16 rounds with gradient through the last 1-6; fp32 on CPU.
Arms: relnet = scripts/claude_relnet_net.py (1,644,198 weights); loop = xfer-1 loop design at 2 x 256, 8 heads, no kind
label (1,645,726 weights).

Scoring (learned stop, 48-round cap, xfer-1's stop rule: first round >= 3 with stop prob > 0.5 and the answer
unchanged for 3 rounds):
  dev  = xfer-1's practice panel (seed 6270703): 200 four-digit sums + 200 5x5 grids. Used for any lr choice.
  gate = a fresh panel (seed 6279901), same make-up. Never used for any choice. The race guard is >= 95% (190 of 200)
         on each kind, and within 3 points of the loop on each.
Also fixed-depth accuracy at 1-48 rounds (stop-failure check), mean stop round and cap hits.

  python -B scripts/claude_relnet_practice.py --arm relnet|loop --seed S [--lr 1e-3] [--threads 2] [--compile] --out DIR
--compile wraps the round step in torch.compile: same maths (checked on both arms: outputs and gradients within
1e-6, 48-round answers identical), about 25% faster on CPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402
import claude_xfer1_bench as B  # noqa: E402  (practice_batch, latin_legend, check, PRACTICE_*)
import claude_xfer1_net as N  # noqa: E402  (loop design, train_loss, tensors)
import claude_xfer1_adapt as A  # noqa: E402  (stop_round)
import claude_relnet_net as RN  # noqa: E402

GATE_PANEL = 6279901
FIXED = [1, 2, 4, 8, 12, 16, 24, 32, 48]
CACHE = Path(os.environ.get("RELNET_CACHE", str(Path.home() / "relnet-cache")))


def build(arm):
    if arm == "relnet":
        return RN.RelNet()
    N.ARMS["loop"] = dict(d=256, layers=2, heads=8)
    return N.Net("loop")


def panel(seed):
    rng = random.Random(seed)
    return {"sums4": [E.make_sum(rng, 4) for _ in range(200)], "grids5": [B.latin_legend(rng, 5) for _ in range(200)]}


@torch.no_grad()
def evaluate(net, items, max_rounds=48, fixed=True):
    net.eval()
    right, fixed_right, stops = 0, {k: 0 for k in FIXED}, []
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        t, s, _ = N.tensors(chunk)
        H, W = t.shape[1], t.shape[2]
        preds, qs = net.loop_rounds(t, s, max_rounds)
        preds, qs = preds.tolist(), qs.tolist()
        for it, p, q in zip(chunk, preds, qs):
            r = A.stop_round(p, q, max_rounds)
            stops.append(r + 1)

            def ok(row):
                return bool(B.check(it, [row[j * W:(j + 1) * W] for j in range(H)]))
            right += ok(p[r])
            if fixed:
                for k in FIXED:
                    fixed_right[k] += ok(p[k - 1])
    out = dict(right=right, n=len(items), mean_rounds=round(sum(stops) / len(stops), 2),
               cap_hits=sum(x == max_rounds for x in stops))
    if fixed:
        out["fixed_depth_right"] = fixed_right
    return out


def main(a):
    torch.set_num_threads(a.threads)
    torch.manual_seed(a.seed)
    net = build(a.arm)
    if a.compile:   # fuses the element-wise ops; checked equal to eager (outputs and gradients within 1e-6) for both arms
        net.step = torch.compile(net.step, dynamic=True)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=N.WD, betas=(0.9, 0.95))
    steps = a.steps
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda i: min(1, (i + 1) / N.WARMUP) * 0.5 * (1 + math.cos(math.pi * min(i, steps) / steps)))
    round_rng = random.Random(9000 + a.seed)
    rng = random.Random(7000000 + a.seed)
    dev, gate = panel(B.PRACTICE_PANEL), panel(GATE_PANEL)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{a.arm}-s{a.seed}-lr{a.lr:g}"
    rep = dict(arm=a.arm, seed=a.seed, lr=a.lr, steps=steps, batch=B.PRACTICE_BATCH, threads=a.threads,
               compile=a.compile, weights=RN.count(net), torch=torch.__version__, curve=[], loss_every250=[])
    t0, losses = time.time(), []
    for i in range(steps):
        net.train()
        loss = N.train_loss(net, B.practice_batch(rng), round_rng)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        losses.append(loss.item())
        if not math.isfinite(losses[-1]):
            rep["error"] = f"non-finite loss at step {i + 1}"
            break
        if (i + 1) % 250 == 0:
            rep["loss_every250"].append(round(sum(losses[-250:]) / 250, 4))
            print(f"{tag} step {i + 1} loss {rep['loss_every250'][-1]} {(time.time() - t0) / 60:.1f} min", flush=True)
        if (i + 1) % a.eval_every == 0 and i + 1 < steps:
            c = {k: evaluate(net, v, fixed=False)["right"] for k, v in dev.items()}
            rep["curve"].append(dict(step=i + 1, minutes=round((time.time() - t0) / 60, 1), dev=c))
            print(f"{tag} step {i + 1} dev {c}", flush=True)
    rep["train_minutes"] = round((time.time() - t0) / 60, 1)
    t1 = time.time()
    rep["dev"] = {k: evaluate(net, v) for k, v in dev.items()}
    rep["gate"] = {k: evaluate(net, v) for k, v in gate.items()}
    rep["eval_minutes"] = round((time.time() - t1) / 60, 1)
    CACHE.mkdir(parents=True, exist_ok=True)
    ck = CACHE / f"{tag}.pt"
    torch.save({"arm": a.arm, "state": net.state_dict()}, ck)
    rep["ckpt"] = str(ck)
    rep["ckpt_sha256"] = hashlib.sha256(ck.read_bytes()).hexdigest()
    (out / f"practice-{tag}.json").write_text(json.dumps(rep, indent=1))
    print(tag, "dev", {k: v["right"] for k, v in rep["dev"].items()}, "gate",
          {k: v["right"] for k, v in rep["gate"].items()}, f"{rep['train_minutes']} min", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["relnet", "loop"], required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--steps", type=int, default=B.PRACTICE_STEPS)
    ap.add_argument("--eval-every", type=int, default=1500)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--out", default="artifacts/claude-relnet-20260927/practice")
    main(ap.parse_args())
