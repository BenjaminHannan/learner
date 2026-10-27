#!/usr/bin/env python3
"""dir-h2 numbers (helper H2, 2026-09-28): rsn-358u's sealed recipe with ONE change: the pool the 4-number practice draws from.

Old pool: the 1,062 practice hands at target 24 (each drawn about 2,410 times in 60,000 steps).
New pool: every 4-number hand of 1-13 that is not held out, with every reachable target 5-40, minus 300 dev pairs
(claude_dir_h2_pool.py). Everything else is claude_rsn358u_run.py unchanged (imported): fixed env 0, 60,000 steps, batch 256,
lr, schedule, loop and plain nets, tests, own stop, poison check. Plan and marks: artifacts/claude-dir-h2-numbers-20260928/.

  python -B scripts/claude_dir_h2_run.py train --arm loop|plain --seed S --out DIR        (defaults only)
  python -B scripts/claude_dir_h2_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_dir_h2_run.py poison --ckpt DIR/final.pt --out F
  python -B scripts/claude_dir_h2_run.py extra --ckpt DIR/final.pt --out F     (P_other on 300 dev pairs, P_train24)
  python -B scripts/claude_dir_h2_run.py selftest | check-mask
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358u_run as U  # noqa: E402  (sealed; applies its fixed-env, gradient-check and autocast patches)
import claude_dir_h2_pool as P  # noqa: E402

R, E = U.R, U.E
_POOL = {}


def pools():
    if not _POOL:
        practice, dev = P.practice_and_dev()
        _POOL["practice"], _POOL["dev"] = practice, dev
    return _POOL["practice"], _POOL["dev"]


class WideSource(R.Source):
    """the sealed practice stream, except that the 4-number hands come from the wide pool"""

    def __init__(self, seed, latin_pool=20000):
        super().__init__(seed, latin_pool=latin_pool)
        held = {tuple(h) for h, _, _ in E.split_four(E.number_hands()[0])[1]}
        practice, dev = pools()
        self.four = practice
        print(P.summary_line(practice, dev, E.split_four(E.number_hands()[0])[1]), flush=True)
        assert not ({tuple(h) for h, _, _ in practice} & held), "held-out hand in the pool"


R.Source = WideSource


@torch.no_grad()
def extra(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, device)
    practice, dev = pools()
    train4, _ = E.split_four(E.number_hands()[0])
    rng = random.Random(35834)
    res = {"arm": net.arm, "ckpt": str(a.ckpt), "n_practice_pairs": len(practice), "n_dev": len(dev)}
    for name, hands in (("P_other", dev), ("P_train24", P.train24_sample(train4))):
        items = [E.number_item(rng, h, t, s) for h, t, s in hands]
        r = R.evaluate(net, items, device)
        res[name] = {"n": len(items), "right": r["right"]}
        print(name, json.dumps(res[name]), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


def selftest():
    P.selftest()
    practice, dev = pools()
    assert R.Source is WideSource
    assert all(t != 24 for _, t, _ in dev) and len(practice) == 36782
    print("run selftest ok (needs torch: imports the sealed runner and checks the swap)")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
    elif sys.argv[1:] == ["check-mask"]:
        U.I2.I.check_mask()
    elif sys.argv[1:2] == ["poison"]:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
        U.poison(ap.parse_args())
    elif sys.argv[1:2] == ["extra"]:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
        extra(ap.parse_args())
    else:
        R.main()
