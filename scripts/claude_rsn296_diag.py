#!/usr/bin/env python3
"""rsn-296 diagnosis (report-only, no training): where do counting, comparing and before/after
fail?  Uses GENERATED episodes only (the varied 296 generator), never a panel item.

  python claude_rsn296_diag.py --ckpt W/plain-s1/final.pt --out diag.json [--n 200] [--device cpu]

Buckets (checked answers, i.e. after the fact-check, exactly as the registered eval):
  count      by gold count 1..7 (the practice range) and 8..12 (never practised: extra rows of the
             same person+relation are added to a generated count episode)
  compare    by how many numeric rows the notebook has (2, 3-5, 6-10, 11+) and whether the two
             compared values are neighbours in the notebook's number order
  before/after  by how many dated rows the asked person has
Writes category-level counts only.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn296_gen as G  # noqa: E402  (installs the varied generator)
import claude_rsn294_core as C  # noqa: E402
import claude_rsn294_run as R  # noqa: E402


def _refid(rows):
    for i, r in enumerate(rows):
        r["fid"] = f"f{i + 1}"


def big_count(rng, n):
    """a generated count episode pushed to gold n by adding rows for the same person+relation"""
    for _ in range(200):
        ep = G.gen_episode296(rng, "count")
        fr = ep["frame"]
        a, r = fr["who"][0], fr["relations"][0]
        have = [x for x in ep["notebook"] if C._key(x["subject"]) == C._key(a) and C._key(x["relation"]) == C._key(r)]
        extra = n - len(have)
        if extra < 0 or len(ep["notebook"]) + extra > C.MAX_ROWS:
            continue
        used = {C._key(x["value"]) for x in ep["notebook"]} | {C._key(x["subject"]) for x in ep["notebook"]}
        top = max(int(x["when"]) for x in ep["notebook"])
        rows = list(ep["notebook"])
        for i in range(extra):
            while True:
                v = C.fake_name(rng)
                if C._key(v) not in used:
                    used.add(C._key(v)); break
            rows.append({"fid": "", "subject": a, "relation": r, "value": v, "when": top + i + 1})
        rng.shuffle(rows)
        _refid(rows)
        ep = {"category": "count", "notebook": rows, "frame": fr,
              "gold": {"answer": str(n), "support": []}}
        if G.solve(ep) == str(n):
            return ep
    raise RuntimeError("no big count episode")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ckpt", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--device", default="cpu")
    a = p.parse_args()
    import torch
    dev = torch.device(a.device)
    model, arm = R.load(a.ckpt, dev)
    rng = random.Random(2961)
    items = []
    for _ in range(a.n):
        e = G.gen_episode296(rng, "count"); e["cat"] = f"count_{int(e['gold']['answer']):02d}"; items.append(e)
    for n in range(8, 13):
        for _ in range(max(1, a.n // 5)):
            e = big_count(rng, n); e["cat"] = f"count_{n:02d}_unpractised"; items.append(e)
    for _ in range(a.n):
        e = G.gen_episode296(rng, "compare")
        nums = sorted({float(x["value"]) for x in e["notebook"] if C._isnum(x["value"])})
        who = [C._key(w) for w in e["frame"]["who"]]
        r = C._key(e["frame"]["relations"][0])
        vs = [float(x["value"]) for x in e["notebook"] if C._key(x["subject"]) in who and C._key(x["relation"]) == r]
        k = len(nums)
        size = "02" if k <= 2 else "03-05" if k <= 5 else "06-10" if k <= 10 else "11+"
        adj = len(vs) == 2 and abs(nums.index(vs[0]) - nums.index(vs[1])) == 1
        e["cat"] = f"compare_nums{size}_{'adjacent' if adj else 'apart'}"
        items.append(e)
    for k in ("before", "after"):
        for _ in range(a.n):
            e = G.gen_episode296(rng, k)
            w = C._key(e["frame"]["who"][0])
            d = sum(1 for x in e["notebook"] if C._key(x["subject"]) == w and x.get("year") is not None)
            e["cat"] = f"{k}_dated{d}"
            items.append(e)
    steps = R.EVAL_STEPS
    res = R.score(items, R.answer(model, arm, items, dev, steps), "cat")
    out = {c: {"n": v["n"], "checked_right": v.get("checked_right", 0), "checked_idk": v.get("checked_idk", 0),
               "checked_wrong": v.get("checked_wrong", 0), "raw_right": v.get("raw_right", 0)}
           for c, v in res["by_category"].items()}
    json.dump({"ckpt": a.ckpt, "arm": arm, "by_bucket": out}, open(a.out, "w"), indent=1)
    for c in sorted(out):
        o = out[c]
        print(f"{c:32s} {o['checked_right']:4d}/{o['n']:<4d} idk {o['checked_idk']:4d} wrong {o['checked_wrong']:4d}")


if __name__ == "__main__":
    main()
