#!/usr/bin/env python3
"""rsn-356 held-out twin-pair test (evaluation only). Makes 600 base puzzles with 296's generator at a
fixed seed (100 each of value1, value2, yesno, compare, count, correction), each with a "change" twin
(an edit type practice never uses), answers both with the checkpoint, and counts pairs where BOTH
answers are right after the fact-check.

  python claude_rsn356_pairs.py --ckpt W/R/final.pt --out W/R/pairs-final.json
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn294_core as C  # noqa: E402
import claude_rsn296_gen  # noqa: E402,F401
import claude_rsn356_twins as T  # noqa: E402
import claude_rsn294_run as Rn  # noqa: E402

KINDS = ["value1", "value2", "yesno", "compare", "count", "correction"]


def make_pairs(seed=4242, per=100):
    rng = random.Random(seed)
    pairs = []
    for k in KINDS:
        got = 0
        while got < per:
            ep = C.gen_episode(rng, k)
            tw = T.make_twin(ep, rng, "change")
            if tw is None:
                continue
            ep["cat"] = tw["cat"] = k
            pairs.append((ep, tw))
            got += 1
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    dev = torch.device(a.device)
    model, arm = Rn.load(a.ckpt, dev)
    pairs = make_pairs()
    items = [x for p in pairs for x in p]
    with torch.no_grad():
        ans = Rn.answer(model, arm, items, dev)
    by = defaultdict(Counter)
    for i, (ep, tw) in enumerate(pairs):
        ok = [C._key(ans[2 * i + j][1]) == C._key(x["gold"]["answer"]) for j, x in enumerate((ep, tw))]
        c = by[ep["cat"]]
        c["n"] += 1
        c["base_right"] += ok[0]
        c["twin_right"] += ok[1]
        c["both_right"] += ok[0] and ok[1]
        c["twin_wrong_not_idk"] += C._key(ans[2 * i + 1][1]) not in ("unknown", C._key(tw["gold"]["answer"]))
    tot = Counter()
    for c in by.values():
        tot.update(c)
    out = {"total": dict(tot), "by_category": {k: dict(v) for k, v in by.items()}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out["total"]))


if __name__ == "__main__":
    main()
