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
  python -B scripts/claude_rsn358u_run.py poison --ckpt DIR/final.pt --out F    (validity mark V1, the Thread manager 12:25 UTC)
  python -B scripts/claude_rsn358u_run.py selftest | check-mask

V1 poison check (Sol's input-audit test): on 100 freshly generated practised-size items per kind (sums4 seed 13579,
grids5 seed 13580, numbers4 from the 4-number PRACTICE hands, rng 13581; never the TEST-ONLY panel, which stays evaluated
once), run the net twice, once as is and once with every item's env field changed (sums/grids -> numbers,
numbers -> sums). Every prediction (all 48 rounds and stop values for the loop) must be identical.
The 2 unused rows of the kind embedding (2 x d weights) stay in both nets as dead weights and are counted in the size.
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


def poison_items():
    import random
    rs = random.Random(13579)
    items = [E.make_sum(rs, 4) for _ in range(100)]
    rg = random.Random(13580)
    items += [E.latin_item(rg, *E.make_latin_base(rg, 5)) for _ in range(100)]
    practice, _ = E.split_four(E.number_hands()[0])
    rn = random.Random(13581)
    items += [E.number_item(rn, h, t, s) for h, t, s in practice[:100]]
    return items


@torch.no_grad()
def predictions(net, items, device):
    net.eval()
    t, s, _, env = R.tensors(items, device)
    if net.arm == "plain":
        return [net.plain_forward(t, s, env).argmax(-1)]
    preds, qs = net.loop_rounds(t, s, env, R.TEST_ROUNDS)
    return [preds, qs]


def poison(a):
    import json
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = R.load(a.ckpt, device)
    items = poison_items()
    out, same_all = {}, True
    for kind in ("sums", "grids", "numbers"):
        batch = [it for it in items if it.env == kind]
        swapped = [E.Item("sums" if kind == "numbers" else "numbers", it.size, it.tokens, it.slot, it.target, it.meta)
                   for it in batch]
        p, q = predictions(net, batch, device), predictions(net, swapped, device)
        same = all(torch.equal(x, y) for x, y in zip(p, q))
        same_all &= same
        out[kind] = {"n": len(batch), "identical": same}
    res = {"arm": net.arm, "ckpt": str(a.ckpt), "V1_identical": same_all, "by_kind": out}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


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
    elif sys.argv[1:2] == ["poison"]:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
        poison(ap.parse_args())
    else:
        R.main()
