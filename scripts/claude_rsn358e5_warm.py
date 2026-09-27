#!/usr/bin/env python3
"""rsn-358e5 DRAFT (sleep research thread, 2026-09-27): warm routing for the freeze-and-grow arm of rsn-358e4.

In rsn-358e4 seed 4 the new router group (zero-initialised rows, top-1 routing, old rows frozen) won none of the sums
cells, so the new experts never trained on sums (artifacts/claude-rsn358e4-20260927/DIAG-new-group-share.md). The one
change tested here is the textbook fix, suggested by the Thread manager at 02:46 UTC:

  warm routing   for the first 10% of phases B and C (steps 1-250 of 2,500 and 1-150 of 1,500), on every NEW-kind
                 batch (not the replay batches), the top-1 choice is made among the newest group's 4 experts only.
                 The gate value is still the full softmax share over all active experts, as before, so the new router
                 rows get a gradient through the chosen expert's gate. Replay batches, all later steps and every
                 evaluation route exactly as rsn-358e4 (unrestricted top-1 over the active experts).
                 This uses the kind of each training batch, like a curriculum. It is never used at test time.

Everything else is rsn-358e4's eq-replayall, imported unchanged: same seeds 3-8, data, steps, replay, dev sets and
scoring. Phase A is untouched, so its after-A scores must equal rsn-358e4's eq-replayall runs exactly (REPRO check).
The controls are rsn-358e4's own runs (eq-replayall and dense-replayall, same seeds); they are not rerun.

  python -B scripts/claude_rsn358e5_warm.py run --arm eq-replayall-warm --seed S --out DIR
  python -B scripts/claude_rsn358e5_warm.py selftest
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358e4_replayall as E4  # noqa: E402  (eq-replayall arm, replay-all schedule, scoring)

E3, X = E4.E3, E4.X
WARM_FRAC = 0.1
_, STEPS_B, STEPS_C = X.STEPS["small"]
WARM = {"sums": int(STEPS_B * WARM_FRAC), "mazes": int(STEPS_C * WARM_FRAC)}      # 250 and 150
ST = {"force": False, "forced": {"sums": 0, "mazes": 0}}
_forward = X.MoE.forward


def forward(self, x):
    """X.MoE.forward, except that while ST["force"] is set a GroupMoE picks its top-1 expert in its newest group"""
    if not (ST["force"] and isinstance(self, E3.GroupMoE)):
        return _forward(self, x)
    logits = self.router(x).float()
    p = F.softmax(logits, -1)                                    # gate: full share over all active experts
    lo = (self.active - 1) * E3.PER_GROUP
    top = logits[..., lo:lo + E3.PER_GROUP].argmax(-1) + lo      # choice: newest group only
    out = torch.zeros_like(x)
    for i, ex in enumerate(self.experts):
        m = top == i
        if m.any():
            out[m] = (ex(x[m]) * p[m][:, i:i + 1].to(x.dtype))
    share = F.one_hot(top, p.shape[-1]).float().mean((0, 1))
    self.aux = p.shape[-1] * (share * p.mean((0, 1))).sum()
    self.last_share = share.detach()
    return out


def phase_batch(rng, kind, bsz, pool):
    batch = E4.phase_batch(rng, kind, bsz, pool)
    n = E4.ST["n"]
    ST["force"] = kind in WARM and n <= WARM[kind] and n % E4.REPLAY_EVERY != 0
    if ST["force"]:
        ST["forced"][kind] += 1
    return batch


def make_net(arm, size):
    assert arm == "eq-replayall-warm"
    ST.update(force=False, forced={"sums": 0, "mazes": 0})
    return E4.make_net("eq-replayall", size)


def score(net, dev, device):
    ST["force"] = False                                          # evaluation always routes freely
    out = E4.score(net, dev, device)
    if E3.ST["calls"] in (3, 4):
        out["forced_batches"] = dict(ST["forced"])
    return out


def selftest():
    import random
    rng = random.Random(0)
    pool = {sz: [E3.E.make_latin_base(rng, sz) for _ in range(5)] for sz in (4, 5)}
    net = make_net("eq-replayall-warm", "small")
    E4.ST.update(kind=None, n=0, replayed={"sums": {}, "mazes": {}})
    for _ in range(2500):
        phase_batch(rng, "sums", 2, pool)
    for _ in range(1500):
        phase_batch(rng, "mazes", 2, pool)
    assert ST["forced"] == {"sums": 225, "mazes": 135}, ST["forced"]
    assert E4.ST["replayed"] == {"sums": {"grids": 250}, "mazes": {"grids": 75, "sums": 75}}
    assert not ST["force"]
    # forced routing picks only the newest group; unforced routing is rsn-358e4's exactly
    E3.eq_grow(net)                                              # as after phase A: 8 experts routable
    t, s, y, env = E3.R.tensors([E3.E.make_sum(rng, 3) for _ in range(8)], "cpu")
    net.eval()
    with torch.no_grad():
        X.MoE.forward = forward
        ST["force"] = True
        net.loop_rounds(t, s, env, 2)
        sh = net.blocks[0].mlp.last_share
        assert float(sh[:4].sum()) == 0 and abs(float(sh[4:8].sum()) - 1) < 1e-6, sh
        ST["force"] = False
        a = [lg.clone() for lg, q in net.loop_train(t, s, env, 0, 2)]
        X.MoE.forward = _forward
        b = [lg.clone() for lg, q in net.loop_train(t, s, env, 0, 2)]
    assert all(torch.equal(u, v) for u, v in zip(a, b))
    print(f"selftest ok: warm routing on {ST['forced']} new-kind batches (replay unchanged: {E4.ST['replayed']}); "
          f"forced choice stays in the newest group; unforced output identical to rsn-358e4")


if __name__ == "__main__":
    X.make_net, X.score, X.phase_batch, X.MoE.forward = make_net, score, phase_batch, forward
    if sys.argv[1:] == ["selftest"]:
        selftest()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--arm", choices=["eq-replayall-warm"], required=True)
        ap.add_argument("--seed", type=int, required=True)
        ap.add_argument("--out", required=True)
        ap.add_argument("--threads", type=int, default=1)
        a = ap.parse_args()
        a.small, a.steps = True, None
        X.run(a)
