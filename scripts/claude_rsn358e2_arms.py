#!/usr/bin/env python3
"""rsn-358e addendum 1 arms (sleep research thread, 2026-09-26), added after the Thread manager's review (19:31 UTC)
and before any 358e number was read. scripts/claude_rsn358e_moe.py stays byte-identical; this file imports it and
adds three arms to the same run (same seeds, data, steps, dev sets, marks):

  moe-grow      Ben's own form ("put the old skills somewhere where they don't get overridden"): phase A as moe;
                before each new phase, 4 NEW experts are added to every block and EVERYTHING already trained is
                frozen (old experts, attention, embeddings, head, stop head, norms, and the router's old rows);
                only the new experts and the router's new rows learn. Total weights grow each phase (reported
                against the same-size rule). Graded on the same marks as moe (a second graded test).
  moe-aux0      moe with no load-balance loss (report only): does the balance loss stop kinds separating?
  dense-narrow  dense with MLP width d instead of 4d (report only): the same ACTIVE weights per cell as moe.

  python -B scripts/claude_rsn358e2_arms.py run --arm moe-grow|moe-aux0|dense-narrow --seed S --out DIR --small
  python -B scripts/claude_rsn358e2_arms.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e_moe as X  # noqa: E402

R, E = X.R, X.E
_make_net, _score = X.make_net, X.score
STATE = {"arm": None, "calls": 0, "net": None}


class GrownRouter(nn.Module):
    """the old router (frozen) plus k new rows (trainable), as two separate weights so weight decay can't touch the old"""

    def __init__(self, old, k):
        super().__init__()
        self.old = old
        self.new = nn.Linear(old.in_features, k).to(next(old.parameters()).device)
        with torch.no_grad():
            self.new.weight.zero_()
            self.new.bias.zero_()
        self.out_features = old.out_features + k
        self.in_features = old.in_features

    def forward(self, x):
        return torch.cat([self.old(x), self.new(x)], -1)


def grow(net, k=X.N_EXPERTS):
    """freeze every trained weight, then add k experts per block and k new router rows (the only trainable part)"""
    for p in net.parameters():
        p.requires_grad_(False)
    for b in net.blocks:
        m = b.mlp
        d = m.router.in_features
        m.router = GrownRouter(m.router, k)
        for _ in range(k):
            m.experts.append(nn.Sequential(nn.Linear(d, 4 * d // X.N_EXPERTS), nn.GELU(),
                                           nn.Linear(4 * d // X.N_EXPERTS, d)).to(m.router.new.weight.device))


def make_net(arm, size):
    STATE.update(arm=arm, calls=0)
    if arm == "dense-narrow":
        net = _make_net("dense", size)
        d = X.SIZES[size]["d"]
        for b in net.blocks:
            b.mlp = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, d))
    else:
        net = _make_net("moe", size)
    net.arm = arm
    STATE["net"] = net
    return net


def score(net, dev, device):
    """X.run scores at start and after each phase; moe-grow grows (and freezes) right after phases A and B"""
    out = _score(net, dev, device)
    STATE["calls"] += 1
    if STATE["arm"] == "moe-grow" and STATE["calls"] in (2, 3):
        grow(net)
    return out


def selftest():
    import random
    net = make_net("moe-grow", "small")
    old = {n: p.detach().clone() for n, p in net.named_parameters()}
    grow(net)
    fresh = {n: p.detach().clone() for n, p in net.named_parameters() if ".experts.4." in n}
    rng = random.Random(0)
    t, s, y, env = R.tensors([E.make_sum(rng, 3) for _ in range(8)], "cpu")
    opt = torch.optim.AdamW(net.parameters(), lr=1e-2, weight_decay=0.1)
    for lg, q in net.loop_train(t, s, env, 1, 2):
        pass
    loss = R.ce_and_exact(lg, s, y)[0] + X.aux_loss(net)
    opt.zero_grad(); loss.backward(); opt.step()
    now = dict(net.named_parameters())
    for n, p in old.items():
        n2 = n.replace("router.", "router.old.")
        assert torch.equal(now[n2] if n2 in now else now[n], p), n       # every old weight frozen, router too
    moved = sum(float((now[n].detach() - p).abs().sum()) for n, p in fresh.items())
    assert moved > 0 and len(net.blocks[0].mlp.experts) == 8
    dn = make_net("dense-narrow", "small")
    mo = X.make_net("moe", "small")
    na, nm = sum(p.numel() for p in dn.parameters()), sum(p.numel() for p in mo.parameters())
    print(f"selftest ok: moe-grow freezes every old weight (router old rows too) and trains 4 new experts per block; "
          f"dense-narrow {na} weights vs moe {nm}")


if __name__ == "__main__":
    X.make_net, X.score = make_net, score
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["moe-grow", "moe-aux0", "dense-narrow"], required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--small", action="store_true")
        ap.add_argument("--threads", type=int, default=1)
        ap.add_argument("--steps", type=int, nargs=3, default=None)
        a = ap.parse_args()
        if a.arm == "moe-aux0":
            X.AUX_W = 0.0
        X.run(a)
