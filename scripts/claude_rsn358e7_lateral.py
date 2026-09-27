#!/usr/bin/env python3
"""rsn-358e7 (sleep research thread, 2026-09-27): Ben 18:42 UTC, "What if we did something where the neural net just gets
bigger? We freeze the neurons, and add a new neuron each sleep?" The Thread manager asked for the next one-change test off
rsn-358e3's moe-grow-replay arm (artifacts/claude-rsn358e3-20260926/RESULTS.md): there, freeze + grow + replay kept grids
(191 / 188) but the new experts learned sums badly (136 / 67).

The one change (graded arm moe-grow-lat-replay vs 358e3's moe-grow-replay): lateral connections, as in Progressive Neural
Networks (Rusu et al. 2016). Each new expert also reads the frozen old experts: on every cell it is sent, the sum of all
older experts' outputs goes through a new d -> hidden matrix U (zero at the start, so the net starts exactly as
moe-grow-replay) and is added inside the new expert, before its GELU:  new(x) = W2 GELU(W1 x + U s),  s = sum_old old(x).
Old weights stay frozen, replay stays the same (every 10th phase-B step is a grids batch from the phase-A pool), and
seeds, data, steps, dev sets and scoring are rsn-358e3's.

Report-only control for the size rule (goals page, "Counting size"): dense-big-replay, the dense loop with its MLP widened
so its total weights match the grown lateral net's total in phase B, every weight trainable, the same replay.

  python -B scripts/claude_rsn358e7_lateral.py run --arm moe-grow-lat-replay|dense-big-replay --seed S --out DIR
  python -B scripts/claude_rsn358e7_lateral.py selftest
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e3_replay as E3  # noqa: E402  (replay batches; imports the two below unchanged)
import claude_rsn358e2_arms as A  # noqa: E402  (moe-grow's grown router)
import claude_rsn358e_moe as X  # noqa: E402  (phases, data, dev sets, scoring, run)

R, E = X.R, X.E
_score, _make = X.score, X.make_net
ST = {"arm": None, "calls": 0, "sizes": {}}


class LatExpert(nn.Module):
    """a new expert d -> h -> d that also reads the sum of the frozen older experts' outputs through U (zero at start)"""

    def __init__(self, d, h, olds):
        super().__init__()
        self.fc1, self.fc2 = nn.Linear(d, h), nn.Linear(h, d)
        self.U = nn.Linear(d, h, bias=False)
        with torch.no_grad():
            self.U.weight.zero_()
        object.__setattr__(self, "olds", list(olds))            # frozen, already counted in the block; not re-registered

    def forward(self, x):
        with torch.no_grad():
            s = sum(o(x) for o in self.olds)
        return self.fc2(F.gelu(self.fc1(x) + self.U(s)))


def lat_grow(net, k=X.N_EXPERTS):
    """moe-grow's grow step (freeze every trained weight, add k router rows at zero), with lateral new experts"""
    for p in net.parameters():
        p.requires_grad_(False)
    for b in net.blocks:
        m = b.mlp
        d = m.router.in_features
        m.router = A.GrownRouter(m.router, k)
        olds = list(m.experts)
        dev = m.router.new.weight.device
        for _ in range(k):
            m.experts.append(LatExpert(d, 4 * d // X.N_EXPERTS, olds).to(dev))


def dense_big_hidden(size):
    """MLP hidden width for dense-big: its total weights match the lateral net's total after the first grow"""
    lat = A.make_net("moe-grow", size)
    lat_grow(lat)
    target = sum(p.numel() for p in lat.parameters())
    base = _make("dense", size)
    d, L = X.SIZES[size]["d"], X.SIZES[size]["layers"]
    rest = sum(p.numel() for p in base.parameters()) - sum(p.numel() for b in base.blocks for p in b.mlp.parameters())
    h = round((target - rest - L * d) / (L * (2 * d + 1)))     # per block: d*h + h + h*d + d
    return h, target


def make_net(arm, size):
    ST.update(arm=arm, calls=0, sizes={})
    E3.ST.update(arm=arm, calls=0, sums_steps=0, replayed=0)   # E3.phase_batch replays for any arm ending in "replay"
    if arm == "moe-grow-lat-replay":
        net = A.make_net("moe-grow", size)
    else:
        h, target = dense_big_hidden(size)
        net = _make("dense", size)
        d = X.SIZES[size]["d"]
        for b in net.blocks:
            b.mlp = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Linear(h, d))
        ST["sizes"]["dense_big_hidden"] = h
        ST["sizes"]["lateral_net_total_in_B"] = target
    net.arm = arm
    return net


def counts(net):
    return {"total": sum(p.numel() for p in net.parameters()),
            "trainable": sum(p.numel() for p in net.parameters() if p.requires_grad)}


def score(net, dev, device):
    """X.run scores at start and after each phase; the lateral arm grows (and freezes) right after phases A and B"""
    out = _score(net, dev, device)
    ST["calls"] += 1
    if ST["arm"] == "moe-grow-lat-replay" and ST["calls"] in (2, 3):
        lat_grow(net)
    out["weights_next_phase"] = counts(net)
    out["sizes"] = dict(ST["sizes"])
    if ST["calls"] == 3:
        out["replayed_batches"] = E3.ST["replayed"]
    return out


def selftest():
    import random
    torch.manual_seed(0)
    net = A.make_net("moe-grow", "small")
    ref = copy.deepcopy(net)
    torch.manual_seed(1); A.grow(ref)
    torch.manual_seed(1); lat_grow(net)
    rng = random.Random(0)
    t, s, y, env = R.tensors([E.make_sum(rng, 3) for _ in range(8)], "cpu")
    with torch.no_grad():
        a, _ = ref.loop_rounds(t, s, env, 4)
        b, _ = net.loop_rounds(t, s, env, 4)
    assert torch.equal(a, b), "with U at zero the lateral net must equal moe-grow"
    old = {n: p.detach().clone() for n, p in net.named_parameters() if not p.requires_grad}
    opt = torch.optim.AdamW(net.parameters(), lr=1e-2, weight_decay=0.1)
    for lg, q in net.loop_train(t, s, env, 1, 2):
        pass
    loss = R.ce_and_exact(lg, s, y)[0] + X.aux_loss(net)
    opt.zero_grad(); loss.backward(); opt.step()
    now = dict(net.named_parameters())
    assert all(torch.equal(now[n], p) for n, p in old.items()), "a frozen weight moved"
    moved_U = sum(float(now[n].abs().sum()) for n in now if n.endswith(".U.weight"))
    assert moved_U > 0 and len(net.blocks[0].mlp.experts) == 8
    c = counts(net)
    h, target = dense_big_hidden("small")
    big = make_net("dense-big-replay", "small")
    nb = sum(p.numel() for p in big.parameters())
    assert abs(nb - target) / target < 0.01, (nb, target)
    ST.update(arm="moe-grow-lat-replay")
    E3.ST.update(arm="moe-grow-lat-replay", sums_steps=0, replayed=0)
    pool = {sz: [E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
    for _ in range(2500):
        E3.phase_batch(rng, "sums", 2, pool)
    assert E3.ST["replayed"] == 250
    print(f"selftest ok: lateral net equals moe-grow while U = 0; frozen weights unchanged after a step; U learns; "
          f"lateral net in B: {c['total']} total, {c['trainable']} trainable; dense-big hidden {h}: {nb} total "
          f"(target {target}); replay 250 of 2,500 sums steps")


if __name__ == "__main__":
    X.make_net, X.score, X.phase_batch = make_net, score, E3.phase_batch
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["moe-grow-lat-replay", "dense-big-replay"], required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        X.run(a)
