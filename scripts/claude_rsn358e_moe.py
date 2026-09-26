#!/usr/bin/env python3
"""rsn-358e (sleep research thread, 2026-09-26): does a mixture-of-experts loop reasoner with a learned router keep
an old skill when it practises a new one, better than the same-size dense loop?

Ben 19:20-19:21 UTC (Thread manager relay): "If it's overriding old skills, just put the old skills somewhere where
they don't get overridden." / "what if we just did a mixture of experts where ... it has the learned router and then
the reasoner is just the mixture of experts."

ONE change vs the dense loop: each block's MLP (d -> 4d -> d) becomes N_EXPERTS=4 experts (d -> d -> d each), picked
per cell by a learned router (top-1, gate-scaled so the router learns; Switch-style load-balance loss x 0.01).
Total weights stay equal (4 x 2d^2 = 8d^2, the same as one 4d MLP) plus the router and extra biases (7d + 4 per
block, +0.1%); active MLP
weights per cell are 1/4. Same-size is judged on TOTAL weights, as against the same-size rival models.
Brain angle (a guess): cortex keeps skills in partly separate circuits and a gate (thalamus / basal ganglia) picks
which one runs, so practising one skill mostly changes its own circuit.

Sequential practice, the same for both arms (code-made data only, fresh seeds, never any sealed test file):
  phase A  grids 4x4/5x5 (358g legend)          STEPS_A steps
  phase B  sums 1-4 digits                        STEPS_B steps   (grids never shown again)
  phase C  mazes 5x5/7x7 (report only: carry-over STEPS_C steps, a kind neither net has seen)
Each phase: fresh AdamW, lr LR, 100-step warm-up, cosine to 0. Loop schedule = 358i (1-16 rounds, gradient through
the last 1-6), fp32 on CPU (no autocast, so the cache bug cannot occur); on CUDA autocast runs with the cache off.
Dev sets (200 each, seeds 48000+): grids5, grids6, sums4, sums6, maze7; scored with 358i's evaluate (own stop, 48
rounds) after each phase. The marks are in artifacts/claude-rsn358e-20260926/PASSMARKS.md.

  python -B scripts/claude_rsn358e_moe.py run --arm dense|moe --seed S --out DIR [--small]
  python -B scripts/claude_rsn358e_moe.py selftest
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358m_run as MR  # noqa: E402  (358i design + the maze kind)
import claude_rsn358t_run as T  # noqa: E402  (any loop arm gets the state norm and stop head)
import claude_rsn358i2_run as I2  # noqa: E402  (autocast cache off on CUDA; gradient logging)

R, E, M = MR.R, MR.E, MR.M
N_EXPERTS, AUX_W = 4, 0.01
SIZES = {"full": dict(d=512, layers=2, heads=8), "small": dict(d=256, layers=2, heads=8)}
STEPS = {"full": (6000, 6000, 3000), "small": (2500, 2500, 1500)}
BATCH = {"full": 128, "small": 64}
LR, WARM = 1e-3, 100
DEV_SEED = 48000


class MoE(nn.Module):
    """top-1 routed experts replacing one MLP; total weights equal to the dense d -> 4d -> d MLP"""

    def __init__(self, d, n=N_EXPERTS):
        super().__init__()
        self.router = nn.Linear(d, n)
        self.experts = nn.ModuleList(nn.Sequential(nn.Linear(d, 4 * d // n), nn.GELU(), nn.Linear(4 * d // n, d))
                                     for _ in range(n))
        self.aux = torch.zeros(())
        self.last_share = None

    def forward(self, x):
        p = F.softmax(self.router(x).float(), -1)                  # [B, T, n]
        top = p.argmax(-1)                                         # [B, T]
        out = torch.zeros_like(x)
        for i, ex in enumerate(self.experts):
            m = top == i
            if m.any():
                out[m] = (ex(x[m]) * p[m][:, i:i + 1].to(x.dtype))
        share = F.one_hot(top, p.shape[-1]).float().mean((0, 1))
        self.aux = p.shape[-1] * (share * p.mean((0, 1))).sum()
        self.last_share = share.detach()
        return out


def make_net(arm, size):
    R.ARMS["dense"] = dict(SIZES[size])
    R.ARMS["moe"] = dict(SIZES[size])
    net = R.Net(arm)
    if arm == "moe":
        for b in net.blocks:
            b.mlp = MoE(SIZES[size]["d"])
    return net


def aux_loss(net):
    ms = [m for m in net.modules() if isinstance(m, MoE)]
    return torch.stack([m.aux for m in ms]).mean() if ms else torch.zeros(())


def phase_batch(rng, kind, bsz, pool):
    if kind == "grids":
        s = rng.choice([4, 5])
        return [E.latin_item(rng, *E.augment_latin(rng, *rng.choice(pool[s]))) for _ in range(bsz)]
    if kind == "sums":
        n = rng.choice([1, 2, 3, 4])
        return [E.make_sum(rng, n) for _ in range(bsz)]
    s = rng.choice(M.SIZES_PRACTICE)
    return [M.make_maze(rng, s) for _ in range(bsz)]


def dev_sets():
    rng = random.Random(DEV_SEED)
    d = {f"grids{s}": [E.latin_item(rng, *E.make_latin_base(rng, s)) for _ in range(200)] for s in (5, 6)}
    d.update({f"sums{n}": [E.make_sum(rng, n) for _ in range(200)] for n in (4, 6)})
    d["maze7"] = [M.make_maze(rng, 7) for _ in range(200)]
    return d


def score(net, dev, device):
    out = {}
    for k, items in dev.items():
        r = R.evaluate(net, items, device)
        out[k] = {"right": r["right"], "r16": r["fixed_rounds"]["16"], "any": r["right_at_any_round"]}
    return out


def expert_share(net, items, device):
    """per block: share of cells sent to each expert, on these items at round 8"""
    ms = [m for m in net.modules() if isinstance(m, MoE)]
    if not ms:
        return None
    net.eval()
    with torch.no_grad():
        t, s, _, env = R.tensors(items[:100], device)
        net.loop_rounds(t, s, env, 8)
    return [[round(float(v), 3) for v in m.last_share] for m in ms]


def run(a):
    size = "small" if a.small else "full"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(a.seed)
    if device == "cpu":
        torch.set_num_threads(a.threads)
    rng, rr = random.Random(5800 + a.seed), random.Random(5900 + a.seed)
    pool = {s: [E.make_latin_base(rng, s) for _ in range(3000)] for s in (4, 5)}
    net = make_net(a.arm, size).to(device)
    dev = dev_sets()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "log.jsonl", "w", encoding="utf-8")
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    t0 = time.time()
    res = {"arm": a.arm, "seed": a.seed, "size": size, "weights": sum(p.numel() for p in net.parameters()),
           "torch": torch.__version__, "device": device, "phases": {}}
    res["phases"]["start"] = score(net, dev, device)
    steps = STEPS[size] if a.steps is None else tuple(a.steps)
    for kind, n in zip(("grids", "sums", "mazes"), steps):
        opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=0.1, betas=(0.9, 0.95))
        sch = torch.optim.lr_scheduler.LambdaLR(opt, lambda i, n=n: min(1, (i + 1) / WARM) * 0.5 * (1 + math.cos(math.pi * min(i, n) / n)))
        for step in range(1, n + 1):
            net.train()
            t, s, y, env = R.tensors(phase_batch(rng, kind, BATCH[size], pool), device)
            tot = rr.randint(1, R.TRAIN_ROUNDS)
            k = rr.randint(1, min(tot, R.GRAD_ROUNDS))
            with amp:
                ls, auxs = [], []
                for lg, q in net.loop_train(t, s, env, tot - k, k):
                    c_, ex = R.ce_and_exact(lg, s, y)
                    ls.append(c_ + 0.5 * F.binary_cross_entropy_with_logits(q.float(), ex))
                    auxs.append(aux_loss(net))
                loss = torch.stack(ls).mean() + AUX_W * torch.stack(auxs).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step(); sch.step()
            if step % 250 == 0 or step == n:
                rec = {"phase": kind, "step": step, "loss": round(loss.item(), 4), "min": round((time.time() - t0) / 60, 1)}
                log.write(json.dumps(rec) + "\n"); log.flush()
                print(json.dumps(rec), flush=True)
        res["phases"][f"after_{kind}"] = score(net, dev, device)
        res["phases"][f"after_{kind}"]["expert_share"] = {k: expert_share(net, dev[k], device) for k in ("grids5", "sums4", "maze7")}
        print(kind, json.dumps(res["phases"][f"after_{kind}"]), flush=True)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "result.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def selftest():
    for size in ("small", "full"):
        dn, mn = make_net("dense", size), make_net("moe", size)
        nd, nm = sum(p.numel() for p in dn.parameters()), sum(p.numel() for p in mn.parameters())
        d, L = SIZES[size]["d"], SIZES[size]["layers"]
        assert nm - nd == L * (7 * d + 4), (nm, nd)          # router (4d + 4) + 3d more expert biases per block
    net = make_net("moe", "small")
    rng = random.Random(0)
    items = [E.make_sum(rng, 3) for _ in range(4)]
    t, s, y, env = R.tensors(items, "cpu")
    outs = net.loop_train(t, s, env, 2, 2)
    loss = sum(R.ce_and_exact(lg, s, y)[0] for lg, _ in outs) + aux_loss(net)
    loss.backward()
    assert net.blocks[0].mlp.router.weight.grad is not None and float(net.blocks[0].mlp.router.weight.grad.abs().sum()) > 0
    used = sum(ex[0].weight.grad is not None for b in net.blocks for ex in b.mlp.experts)
    assert used >= 1
    print(f"selftest ok: moe and dense differ only by the routers ({nm - nd} weights at full size, "
          f"{nm} vs {nd}); the router gets a gradient; {used} of {L * N_EXPERTS} experts used on one batch")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["dense", "moe"], required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--small", action="store_true")
        ap.add_argument("--threads", type=int, default=1)
        ap.add_argument("--steps", type=int, nargs=3, default=None)
        run(ap.parse_args())
