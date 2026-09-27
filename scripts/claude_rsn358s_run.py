#!/usr/bin/env python3
"""rsn-358s (sleep research thread, 2026-09-27): size scaling. Ben 14:49 UTC 09-26: "A bigger reasoner still beats
other bigger models of its size." The 1x pair is rsn-358i3 (loop 2 x d512, 6,438,302 weights; plain 8 x d256,
6,385,149; PASS, recount 23dbe806b). This file runs the 3x pair with ONE change, width: loop 2 x d896 (19,524,254)
and plain 8 x d448 (19,430,589). Everything else is 358i2's code unchanged (imported): autocast cache off, gradient
logging, data, 60,000 steps, batch 256, lr and schedule, v2 stop rule, 48 test rounds, 358i's sealed tests.

  python -B scripts/claude_rsn358s_run.py train --arm loop|plain --seed S --out DIR
  python -B scripts/claude_rsn358s_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_rsn358s_run.py selftest | check-mask
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358i2_run as I2  # noqa: E402

R = I2.R
ARMS_3X = {"loop": dict(d=896, layers=2, heads=8), "plain": dict(d=448, layers=8, heads=8)}
R.ARMS.update({k: dict(v) for k, v in ARMS_3X.items()})


def selftest():
    n = {a: sum(p.numel() for p in R.Net(a).parameters()) for a in ARMS_3X}
    assert n == {"loop": 19524254, "plain": 19430589}, n
    I2.selftest()
    print(f"selftest ok: 3x arms loop {n['loop']:,} and plain {n['plain']:,} weights (ratio {n['loop'] / n['plain']:.3f})")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    elif sys.argv[1:] == ["check-mask"]:
        I2.I.check_mask()
    else:
        R.main()
