#!/usr/bin/env python3
"""The sealed MoE driver (claude_moe_deep_run.py) with two report-only helpers fixed for CUDA (ADDENDUM-2.md).

The sealed file is not edited. Same command line as the driver. Two fixes, neither touches training, scoring,
data, the ladder or the marks:
  1. cpu_state() clones: on the CPU, `v.detach().cpu()` is the live parameter, so the smoke's CPU start state moved
     with training (ADDENDUM-1). It is only used for snapshots and saved files.
  2. expert_gradient_check() builds its per-expert tally on the CPU: under torch.set_default_device('cuda'),
     torch.zeros(...) landed on the GPU and `|=` with a CPU tensor raised "Expected all tensors to be on the same
     device" after 12,000 practice steps on vast 53347127 (both seeds, 12:56-12:58 UTC 09-29). It is a
     report-only count (PASSMARKS V2 gates only the harness gradient check).
"""
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_moe_deep_run as R  # noqa: E402

R.cpu_state = lambda net: {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}


def expert_gradient_check(net, seed):
    if not hasattr(net, "moes") or not net.moes():
        return None
    net.train()
    rng = random.Random(9242700 + seed)
    alive = [torch.zeros(m.n, dtype=torch.bool, device="cpu") for m in net.moes()]
    for batch in ([R.D.E.make_sum(rng, 4) for _ in range(32)], [R.D.latin_legend(rng, 5) for _ in range(32)]):
        net.zero_grad(set_to_none=True)
        R.B.N.train_loss(net, batch, rng).backward()
        for a, m in zip(alive, net.moes()):
            g = m.w1.grad
            if g is not None:
                a |= (g.abs().sum((1, 2)) > 0).cpu()
    net.zero_grad(set_to_none=True)
    per = [int(a.sum()) for a in alive]
    return {"alive_per_layer": per, "experts_per_layer": net.moes()[0].n,
            "alive_total": sum(per), "experts_total": sum(m.n for m in net.moes())}


R.expert_gradient_check = expert_gradient_check

if __name__ == "__main__":
    # the driver's own command line (claude_moe_deep_run.py, last block), calling the patched module
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("selftest", "smoke", "source", "dev", "holdout", "phase"))
    ap.add_argument("--cfg", default=R.MAIN, choices=sorted(R.M.CFGS) + ["loopctl"])
    ap.add_argument("--seed", type=int, choices=(0, 1), default=0)
    ap.add_argument("--init", choices=("pre", "fresh"), default="pre")
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--phase", type=int, choices=(1, 2, 3))
    ap.add_argument("--no-stages", action="store_true")
    ap.add_argument("--loop-source-root", type=Path)
    a = ap.parse_args()
    if a.cmd == "selftest":
        R.cmd_selftest(a)
    elif a.cmd == "smoke":
        R.cmd_smoke(a)
    elif a.cmd == "source":
        R.cmd_source(a.cfg, a.seed, a.device, a.threads)
    elif a.cmd == "dev":
        R.cmd_dev(a.cfg, a.seed, a.init, a.device, a.threads, a.loop_source_root, stages=not a.no_stages)
    elif a.cmd == "holdout":
        R.cmd_holdout(a.cfg, a.seed, a.init, a.device, a.threads)
    else:
        R.cmd_phase(a)
