#!/usr/bin/env python3
"""rsn-358u DRAFT (sleep research thread, 2026-09-27): rsn-358i3's recipe with ONE change: the net is not told the puzzle
kind. Every 358 net adds a learned kind embedding (Item.env: sums / grids / numbers) at every cell
(claude_rsn358a_run.py:96, set per batch at :172), so no 358 result shows a net working out the kind itself (Sol's input
audit, the Thread manager 12:09 UTC; Ben 11:34 UTC: "It should for each request be able to automatically decide what").
Here tensors() returns the same env index (0) for every item in training, dev and tests, so the kind embedding is one
learned constant and the kind must be read from the puzzle's own tokens. Everything else is rsn-358i2's sealed code
unchanged (imported): autocast cache off, gradient logging, data, 60,000 steps, batch 256, lr and schedule, v2 stop
rule, 48 test rounds, 358i's sealed tests.

  python -B scripts/claude_rsn358u_run.py train --arm loop|plain --seed S --out DIR
  python -B scripts/claude_rsn358u_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_rsn358u_run.py selftest | check-mask
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358i2_run as I2  # noqa: E402

R, E = I2.R, I2.E
FIXED_ENV = 0
_tensors = R.tensors
SEEN = set()


def tensors(items, device):
    """R.tensors, except that env is FIXED_ENV for every item, whatever its kind (the one change)"""
    t, s, y, env = _tensors(items, device)
    SEEN.add(E.ENVS.index(items[0].env))
    return t, s, y, torch.full_like(env, FIXED_ENV)


R.tensors = tensors


def selftest():
    import random
    rng = random.Random(0)
    grid = [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(4)]
    sums = [E.make_sum(rng, 4) for _ in range(4)]
    envs = {int(v) for batch in (grid, sums) for v in R.tensors(batch, "cpu")[3].tolist()}
    assert envs == {FIXED_ENV} and SEEN == {E.ENVS.index("grids"), E.ENVS.index("sums")}, (envs, SEEN)
    I2.selftest()                                                  # 358i2's gradient check, through the patched tensors
    print(f"selftest ok: every item gets env {FIXED_ENV} (kinds seen {sorted(SEEN)}); 358i2 checks pass")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    elif sys.argv[1:] == ["check-mask"]:
        I2.I.check_mask()
    else:
        R.main()
