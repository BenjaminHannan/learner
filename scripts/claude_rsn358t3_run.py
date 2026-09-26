#!/usr/bin/env python3
"""rsn-358t v3 (sleep research thread, 2026-09-26): rsn-358t's sealed arms (loop-trm, loop8, loop8-trm) run with the
autocast weight cache OFF, the same bug repair as rsn-358i2 (scripts/claude_rsn358i2_run.py docstring).

358t v2 ran on a torch 2.8 rental and crashed without a verdict (rc=2, SSH lost); its partial logs fit the cache bug
(loop-trm dev grids5 0/200 at step 10,000). On torch 2.8 loop-trm's layers never get a gradient, because every
segment starts with 4 no-grad rounds inside the same autocast block. This file changes nothing in 358t's code: it
imports 358t (arms, schedules, EMA, train) and then 358i2 (cache off + gradient logging), in that order, so the
logging wraps 358t's own train and Net.__init__.

  python -B scripts/claude_rsn358t3_run.py train --arm loop-trm|loop8|loop8-trm --seed S --out DIR
  python -B scripts/claude_rsn358t3_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_rsn358t3_run.py selftest | check-mask | audit | smoke
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358t_run as T  # noqa: E402  (first: 358t's arms, schedules and train)
import claude_rsn358i2_run as I2  # noqa: E402  (second: autocast cache off, gradient logging around 358t's train)

R, E = T.R, T.E


def selftest():
    T.selftest()
    assert torch.autocast is I2.NoCacheAutocast and R.train is I2.train and I2._train is T.train
    torch.manual_seed(0)
    rng = random.Random(0)
    items = [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(4)]
    t, s, y, env = R.tensors(items, "cpu")
    for arm in ("loop-trm", "loop8-trm"):
        net = R.Net(arm)
        h = torch.zeros(4, t.shape[1] * t.shape[2], R.ARMS[arm]["d"])
        with torch.autocast("cpu", dtype=torch.bfloat16):
            h, (lg, q) = T.segment(net, h, t, s, env)
            loss = R.ce_and_exact(lg, s, y)[0] + q.float().mean()
        loss.backward()
        mats = I2._block_mats(net)
        none = sum(p.grad is None or not bool(p.grad.abs().sum()) for _, p in mats)
        assert none == 0, (arm, none, len(mats))
    print(f"selftest ok: 358t selftest passes; torch {torch.__version__}, cache off; a TRM segment "
          f"(4 no-grad + 4 graded rounds) gives every block Linear weight a gradient")


if __name__ == "__main__":
    cmd = sys.argv[1:]
    if cmd == ["check-mask"]:
        T.I.check_mask()
    elif cmd == ["audit"]:
        T.I.G.audit()
    elif cmd == ["selftest"]:
        selftest()
    else:
        R.main()
