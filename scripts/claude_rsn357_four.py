#!/usr/bin/env python3
"""rsn-357 four-step test (evaluation only). 300 code-made four-step value questions (296's generator,
seed 5151, re-solved by 296's independent solver), never practised. Scores checked and raw right; for
the loop also at 6, 12, 20 and 40 rounds.

  python claude_rsn357_four.py --ckpt W/R/final.pt --out W/R/four-final.json
"""
import argparse
import json
import random
import sys
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.argv, _argv = [sys.argv[0]], sys.argv       # keep 357's runner from reading our flags
import claude_rsn357_run  # noqa: E402,F401  (MAX_HOPS 4, shared input, loop fix)
sys.argv = _argv
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen as G  # noqa: E402
import claude_rsn294_run as Rn  # noqa: E402


def items(seed=5151, n=300):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        e = C.gen_episode(rng, "value", hops=4)
        if len(e["frame"]["relations"]) != 4 or G.solve(e) is None:
            continue
        e["cat"] = "four_step"
        out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    dev = torch.device(a.device)
    model, arm = Rn.load(a.ckpt, dev)
    its = items()
    res = {}
    with torch.no_grad():
        for st in ([6, 12, 20, 40] if arm == "loop" else [None]):
            res[f"steps_{st}"] = Rn.score(its, Rn.answer(model, arm, its, dev, st or Rn.EVAL_STEPS), "cat")["total"]
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
