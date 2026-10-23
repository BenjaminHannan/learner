"""Train one (arm, seed): python -m bridgelab.run --arm pooled --seed 0 --steps 8000"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from . import eval as ev
from . import task
from .models import Pair

RESULTS = Path(__file__).parent / "results"
CURRICULUM, SWAPS = 0.6, 10   # tables start as the identity; the allowed number of random swaps grows 0 -> SWAPS over this fraction of training, then fully random


def train(arm: str, seed: int, steps: int, bs: int = 64, lr: float = 1e-3, log: int = 500, **kw) -> Pair:
    torch.manual_seed(seed)
    model = Pair(arm, **kw)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    gen = torch.Generator().manual_seed(1000 + seed)
    t0 = time.time()
    for step in range(steps):
        for g in opt.param_groups:
            g["lr"] = lr * min(1.0, (step + 1) / 200) * (0.5 * (1 + math.cos(math.pi * step / steps)) * 0.95 + 0.05)
        d = task.make_batch(bs, gen, max_swaps=int(SWAPS * step / (CURRICULUM * steps)) if step < CURRICULUM * steps else None)
        la, lb = model(d["xa"], d["xb"])
        loss = F.cross_entropy(la, d["yA"]) + F.cross_entropy(lb, d["yB"])
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if log and (step % log == 0 or step == steps - 1):
            accs = [float((l.argmax(1) == d[k]).float().mean()) for l, k in ((la, "yA"), (lb, "yB"))]
            print(f"{arm} s{seed} step {step} loss {loss.item():.3f} accA {accs[0]:.2f} accB {accs[1]:.2f} t {time.time() - t0:.0f}s", flush=True)
    return model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps", type=int, default=8000)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", default=str(RESULTS))
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    t0 = time.time()
    model = train(a.arm, a.seed, a.steps)
    res = {"arm": a.arm, "seed": a.seed, "steps": a.steps, "train_s": time.time() - t0, **ev.full_eval(model, a.seed)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.arm}_s{a.seed}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("acc", "probe")}))


if __name__ == "__main__":
    main()
