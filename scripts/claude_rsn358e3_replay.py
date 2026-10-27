#!/usr/bin/env python3
"""rsn-358e3 (sleep research thread, 2026-09-26): after rsn-358e stage 1 (FAIL; artifacts/claude-rsn358e-20260926/
RESULTS.md, DIAG-moe-grow.md). The frozen old experts still held all of grids, but the grown router, trained on sums
only, sent grids cells to the new experts. The one change tested here: a small replay of grids in phase B.

  replay   in phase B, every 10th step (steps 10, 20, ..., 2,500: 250 batches, fixed now) is a grids batch drawn from
           the same phase-A grids TRAINING pool (never a dev set) instead of a sums batch. Phases A and C unchanged.

Arms (all import claude_rsn358e_moe.py and claude_rsn358e2_arms.py unchanged; same seeds, data, steps, dev sets):
  moe-grow-eq            same-size moe-grow: 12 experts exist from the start, each d -> 4d/12 -> d (85 wide at d=256),
                         so total weights stay the dense MLP's (plus routers). The router is 3 groups of 4 rows. Phase A
                         routes over experts 0-3 only; before B everything trained is frozen and experts 4-7 plus router
                         group 2 (initialised to zero, as in moe-grow) join; before C the same with 8-11 and group 3.
                         Softmax and routing run over the active experts only, exactly as moe-grow's grown router does.
  moe-grow-eq-replay     moe-grow-eq + replay
  moe-grow-replay        moe-grow + replay (1.64x size in B, as moe-grow)
  dense-replay           dense + replay

  python -B scripts/claude_rsn358e3_replay.py run --arm ARM --seed S --out DIR
  python -B scripts/claude_rsn358e3_replay.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e2_arms as A  # noqa: E402  (moe-grow and its grow step)
import claude_rsn358e_moe as X  # noqa: E402  (phases, data, dev sets, scoring, run)

R, E = X.R, X.E
N_GROUPS, PER_GROUP = 3, X.N_EXPERTS
REPLAY_EVERY = 10
_phase_batch, _score, _make = X.phase_batch, X.score, X.make_net
ST = {"arm": None, "calls": 0, "sums_steps": 0, "replayed": 0, "net": None}


class GroupMoE(X.MoE):
    """12 experts of hidden 4d/12; router = 3 groups of 4 rows; only the first `active` groups are routable"""

    def __init__(self, d):
        nn.Module.__init__(self)
        h = 4 * d // (N_GROUPS * PER_GROUP)
        self.groups = nn.ModuleList(nn.Linear(d, PER_GROUP) for _ in range(N_GROUPS))
        with torch.no_grad():
            for g in self.groups[1:]:
                g.weight.zero_()
                g.bias.zero_()
        self.experts = nn.ModuleList(nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Linear(h, d))
                                     for _ in range(N_GROUPS * PER_GROUP))
        self.active = 1
        self.aux = torch.zeros(())
        self.last_share = None

    def router(self, x):
        return torch.cat([g(x) for g in self.groups[:self.active]], -1)


def eq_grow(net):
    """freeze everything trained so far; open the next router group and its 4 experts"""
    for p in net.parameters():
        p.requires_grad_(False)
    for b in net.blocks:
        m = b.mlp
        k = m.active
        for p in m.groups[k].parameters():
            p.requires_grad_(True)
        for ex in m.experts[k * PER_GROUP:(k + 1) * PER_GROUP]:
            for p in ex.parameters():
                p.requires_grad_(True)
        m.active = k + 1


def make_net(arm, size):
    ST.update(arm=arm, calls=0, sums_steps=0, replayed=0)
    if arm.startswith("moe-grow-eq"):
        net = _make("moe", size)
        for b in net.blocks:
            b.mlp = GroupMoE(X.SIZES[size]["d"])
        net.arm = arm
    elif arm == "moe-grow-replay":
        net = A.make_net("moe-grow", size)
    else:
        net = _make("dense", size)
    for b in net.blocks:                                         # untrained experts of later phases start frozen
        if isinstance(b.mlp, GroupMoE):
            for ex in b.mlp.experts[PER_GROUP:]:
                for p in ex.parameters():
                    p.requires_grad_(False)
            for g in b.mlp.groups[1:]:
                for p in g.parameters():
                    p.requires_grad_(False)
    ST["net"] = net
    return net


def phase_batch(rng, kind, bsz, pool):
    if kind == "sums" and ST["arm"].endswith("replay"):
        ST["sums_steps"] += 1
        if ST["sums_steps"] % REPLAY_EVERY == 0:
            ST["replayed"] += 1
            return _phase_batch(rng, "grids", bsz, pool)          # the phase-A training pool, never a dev set
    return _phase_batch(rng, kind, bsz, pool)


def score(net, dev, device):
    """X.run scores at start and after each phase; grow arms grow (and freeze) after phases A and B"""
    if ST["arm"] == "moe-grow-replay":
        out = A.score(net, dev, device)                          # A.score grows after its calls 2 and 3
    else:
        out = _score(net, dev, device)
    ST["calls"] += 1
    if ST["arm"].startswith("moe-grow-eq") and ST["calls"] in (2, 3):
        eq_grow(net)
    if ST["calls"] == 3:
        out["replayed_batches"] = ST["replayed"]
    return out


def selftest():
    import random
    for arm in ("moe-grow-eq", "dense-replay"):
        make_net(arm, "small")
    net = make_net("moe-grow-eq", "small")
    dense = _make("dense", "small")
    n = lambda m: sum(p.numel() for p in m.parameters())
    tr = lambda m: sum(p.numel() for p in m.parameters() if p.requires_grad)
    mlp_eq = n(net.blocks[0].mlp) - sum(n(g) for g in net.blocks[0].mlp.groups)
    mlp_dense = n(dense.blocks[0].mlp)
    rng = random.Random(0)
    t, s, y, env = R.tensors([E.make_sum(rng, 3) for _ in range(8)], "cpu")
    # phase A: only group 1 routes; the net must train and route over 4 experts only
    for lg, q in net.loop_train(t, s, env, 1, 2):
        pass
    assert net.blocks[0].mlp.last_share.numel() == PER_GROUP
    before = {k: v.detach().clone() for k, v in net.named_parameters()}
    eq_grow(net)
    trainable = {k for k, p in net.named_parameters() if p.requires_grad}
    opt = torch.optim.AdamW(net.parameters(), lr=1e-2, weight_decay=0.1)
    for lg, q in net.loop_train(t, s, env, 1, 2):
        pass
    loss = R.ce_and_exact(lg, s, y)[0] + X.aux_loss(net)
    opt.zero_grad(); loss.backward(); opt.step()
    now = dict(net.named_parameters())
    for k, v in before.items():
        if k not in trainable:
            assert torch.equal(now[k], v), k                    # every frozen weight unchanged (weight decay too)
    moved = sum(float((now[k].detach() - before[k]).abs().sum()) for k in trainable)
    assert moved > 0 and net.blocks[0].mlp.last_share.numel() == 2 * PER_GROUP
    assert all(".groups.1." in k or any(f".experts.{i}." in k for i in range(4, 8)) for k in trainable)
    # replay: every 10th sums batch is grids, 250 of 2,500
    ST.update(arm="dense-replay", sums_steps=0, replayed=0)
    pool = {sz: [E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
    kinds = [phase_batch(rng, "sums", 2, pool)[0] for _ in range(2500)]
    assert ST["replayed"] == 250
    print(f"selftest ok: moe-grow-eq MLP weights {mlp_eq} vs dense MLP {mlp_dense} per block; "
          f"total {n(net)} vs dense {n(dense)}; phase A routes 4 experts, phase B 8; frozen weights unchanged after "
          f"a step; {tr(net)} trainable in B; replay 250 of 2,500 sums steps")


if __name__ == "__main__":
    X.make_net, X.score, X.phase_batch = make_net, score, phase_batch
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["moe-grow-eq", "moe-grow-eq-replay", "moe-grow-replay", "dense-replay"],
                        required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        X.run(a)
