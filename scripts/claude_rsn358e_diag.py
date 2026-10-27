#!/usr/bin/env python3
"""rsn-358e moe-grow diagnostic (sleep research thread, 2026-09-26), asked by the Thread manager at 20:25 UTC after the
first phase-B numbers. Report only; no mark depends on it. The stage-1 runs saved no checkpoints, so this re-runs
moe-grow phases A and B with the SAME code, seed and data (CPU, 1 thread; moe and moe-grow training losses already
matched step for step, so the run is reproducible), then checks:

  REPRO   the after-B dev scores equal the stage-1 run's (seed 1: grids5 40, seed 2: grids5 70). If not, stop:
          nothing below can be read.
  FREEZE  (1) requires_grad of every parameter after the grow step; (2) a byte compare (torch.equal) of every weight
          that existed after phase A, before vs after phase B.
  MASKS   grids5/grids6 on the after-B net with the router changed at test time only (the masking code is below):
            M0 old-only: route and scale over the 4 old experts only (as if the grow step never happened);
            M1 no-rescale: route over all 8 as trained, but scale a chosen old expert by its softmax share over the
               4 old experts only (removes the gate rescale, keeps the routing shift);
            M2 old-routing: route over the 4 old experts only, but scale by the full 8-way softmax share (removes the
               routing shift, keeps the rescale).
Checkpoints (after A, after B) go to the --out folder, never to git.

  python -B scripts/claude_rsn358e_diag.py --seed S --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e2_arms as A  # noqa: E402
import claude_rsn358e_moe as X  # noqa: E402

R = X.R
STAGE1 = {1: {"grids5": 40, "grids6": 34, "sums4": 139}, 2: {"grids5": 70, "grids6": 21, "sums4": 124}}
S = {"calls": 0, "after_a": None, "out": None, "seed": None}


def masked_forward(mode):
    def fwd(self, x):
        logits = self.router(x).float()                          # [B, T, 8] after the grow step
        k = logits.shape[-1] // 2                                # 4 old experts, 4 new
        p_all = F.softmax(logits, -1)
        p_old = F.softmax(logits[..., :k], -1)
        if mode in ("M0", "M2"):
            top = p_old.argmax(-1)                               # routing restricted to the old experts
        else:
            top = p_all.argmax(-1)                               # routing as trained
        out = torch.zeros_like(x)
        for i, ex in enumerate(self.experts):
            m = top == i
            if not m.any():
                continue
            if mode == "M0" or (mode == "M1" and i < k):
                g = p_old[m][:, i:i + 1]                         # old-only share
            else:
                g = p_all[m][:, i:i + 1]                         # full 8-way share
            out[m] = ex(x[m]) * g.to(x.dtype)
        return out
    return fwd


def grids_only(net, dev, device):
    return {k: X.R.evaluate(net, dev[k], device)["right"] for k in ("grids5", "grids6")}


def score(net, dev, device):
    S["calls"] += 1
    out_dir = Path(S["out"])
    if S["calls"] == 2:                                          # after phase A, before the grow step
        S["after_a"] = {n: p.detach().clone() for n, p in net.named_parameters()}
        torch.save(net.state_dict(), out_dir / "after_A.pt")
    if S["calls"] < 3:
        return A.score(net, dev, device)                         # grows (and freezes) after call 2, as in stage 1
    res = X.__dict__["_orig_score"](net, dev, device)            # after phase B: the stage-1 score, no growing
    torch.save(net.state_dict(), out_dir / "after_B.pt")
    want = STAGE1[S["seed"]]
    repro = {k: [res[k]["right"], want[k]] for k in want}
    d = {"seed": S["seed"], "torch": torch.__version__, "repro_ok": all(a == b for a, b in repro.values()),
         "repro": repro, "after_B": {k: v["right"] for k, v in res.items()}}
    now = dict(net.named_parameters())
    req = {"old_trainable": [], "new_frozen": []}
    same, moved = 0, []
    for n, p in S["after_a"].items():
        n2 = n.replace("router.", "router.old.")
        q = now[n2] if n2 in now else now[n]
        if q.requires_grad:
            req["old_trainable"].append(n)
        if torch.equal(q.detach(), p):
            same += 1
        else:
            moved.append(n)
    old_names = {n.replace("router.", "router.old.") if n.replace("router.", "router.old.") in now else n for n in S["after_a"]}
    req["new_frozen"] = [n for n, p in now.items() if n not in old_names and not p.requires_grad]
    d["freeze"] = {"old_tensors": len(S["after_a"]), "byte_identical": same, "moved": moved,
                   "old_with_requires_grad": req["old_trainable"], "new_without_requires_grad": req["new_frozen"],
                   "new_tensors": len(now) - len(S["after_a"])}
    moes = [m for m in net.modules() if isinstance(m, X.MoE)]
    d["masks"] = {}
    if d["repro_ok"]:
        for mode in ("M0", "M1", "M2"):
            for m in moes:
                m.forward = types.MethodType(masked_forward(mode), m)
            d["masks"][mode] = grids_only(net, dev, device)
            for m in moes:
                del m.forward                                    # back to the class forward
        d["masks"]["unmasked_check"] = grids_only(net, dev, device)
    (out_dir / "diag.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
    print(json.dumps(d), flush=True)
    sys.exit(0)                                                  # phase C is not needed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    S.update(out=a.out, seed=a.seed)
    X._orig_score = X.score
    X.make_net, X.score = A.make_net, score
    run_args = argparse.Namespace(cmd="run", arm="moe-grow", seed=a.seed, out=a.out, small=True, threads=1, steps=None)
    X.run(run_args)
