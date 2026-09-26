#!/usr/bin/env python3
"""rt-02h-T: how many examples of a new way of asking does rt-02h's head need? (Plain-English puzzles, 2026-09-26)

Marks: artifacts/claude-rt02hT-20260926/PASSMARKS-rt02hT.md (sealed before this runs). Practice data only: rt-02h's
own 1B drafts (artifacts/claude-rt02h-20260926/train/drafts_1b.jsonl) and their saved hidden-state features
(claude_rt02h_probe.py feats). No blind panel is read.

For each of the 6 asking styles h: the head (layer 18, L2 0.001, as registered for rt-02h) is trained on the other 5
styles' positive drafts, k drafts of style h (k = 0, 1, 3, 5; 3 draws each), and the training negatives. The cut is
picked the rt-02h way (5-fold CV by prompt; held-out negatives fire on <= 1%). It is scored on style h's test drafts,
which come from prompts none of the k examples came from. Recognised = head score >= cut.

  OMP_NUM_THREADS=1 python -B scripts/claude_rt02hT.py --drafts artifacts/claude-rt02h-20260926/train/drafts_1b.jsonl \
      --feats FEATS.pt --out artifacts/claude-rt02hT-20260926/run
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SEED = 4870
KS = (0, 1, 3, 5)
DRAWS = 3
LAYER, L2 = 18, 1e-3


def cv_cut(PR, X, y, g, l2):
    """rt-02h's cut rule: 5-fold CV by group; the cut lets held-out negatives fire on <= 1%"""
    import torch
    groups = sorted(set(g), key=str)
    fold = {q: i % 5 for i, q in enumerate(groups)}
    s = torch.zeros(len(y))
    for f in range(5):
        a = [j for j in range(len(y)) if fold[g[j]] != f]
        b = [j for j in range(len(y)) if fold[g[j]] == f]
        s[b] = PR._fit(X[a], y[a], l2)(X[b])
    neg = s[y == 0].sort(descending=True).values
    return float(neg[max(0, int(0.01 * len(neg)))]) + 1e-6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", required=True)
    ap.add_argument("--feats", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import torch
    import claude_rt02h_probe as PR
    rows = [r for r in map(json.loads, Path(a.drafts).read_text().splitlines()) if r["keep"]]
    d = torch.load(a.feats)
    meta = [m for m in d["meta"] if m[0] == "draft"]
    assert len(meta) == len(rows) and all(m[2] == int(r["kind"] == "pos") and m[1] == r["pi"] for m, r in zip(meta, rows))
    li = PR.LAYERS.index(LAYER)
    X = d["X"][[i for i, m in enumerate(d["meta"]) if m[0] == "draft"]][:, li]
    y = torch.tensor([int(r["kind"] == "pos") for r in rows])
    grp = [(r["kind"], r["pi"]) for r in rows]
    neg_groups = sorted({q for q, r in zip(grp, rows) if r["kind"] != "pos"}, key=str)
    neg_test = {q for i, q in enumerate(neg_groups) if i % 5 == 0}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "cells.jsonl"
    if path.exists():
        raise SystemExit(f"rt02hT: {path} exists (launched once)")
    cells = []
    for h in range(6):
        prompts = sorted({r["pi"] for r in rows if r["kind"] == "pos" and r["style"] == h})
        random.Random(SEED + h).shuffle(prompts)
        test_p = set(prompts[: (len(prompts) + 1) // 2])
        test = [i for i, r in enumerate(rows) if r["kind"] == "pos" and r["style"] == h and r["pi"] in test_p]
        pool = [i for i, r in enumerate(rows) if r["kind"] == "pos" and r["style"] == h and r["pi"] not in test_p]
        base = [i for i, r in enumerate(rows) if (r["kind"] == "pos" and r["style"] != h)
                or (r["kind"] != "pos" and grp[i] not in neg_test)]
        ntest = [i for i, r in enumerate(rows) if r["kind"] != "pos" and grp[i] in neg_test]
        for k in KS:
            for draw in range(DRAWS if k else 1):
                if k > len(pool):
                    cells.append({"style": h, "k": k, "draw": draw, "measurable": False})
                    continue
                extra = random.Random(SEED * 100 + h * 10 + k * 3 + draw).sample(pool, k)
                tr = base + extra
                Xt, yt, gt = X[tr], y[tr], [grp[i] for i in tr]
                cut = cv_cut(PR, Xt, yt, gt, L2)
                hd = PR._fit(Xt, yt, L2)
                st, sn = hd(X[test]), hd(X[ntest])
                cells.append({"style": h, "k": k, "draw": draw, "measurable": True, "n_test": len(test),
                              "recognised": int((st >= cut).sum()), "n_neg_test": len(ntest),
                              "neg_fired": int((sn >= cut).sum()), "cut": round(cut, 4), "n_pool": len(pool)})
                print(json.dumps(cells[-1]), flush=True)
    path.write_text("".join(json.dumps(c) + "\n" for c in cells))
    summary = {}
    for h in range(6):
        per_k = {}
        for k in KS:
            cs = [c for c in cells if c["style"] == h and c["k"] == k and c["measurable"]]
            if cs:
                per_k[k] = statistics.median(c["recognised"] / c["n_test"] for c in cs)
        kstar = next((k for k in KS if per_k.get(k, 0) >= 0.9), None)
        summary[h] = {"rate_by_k": per_k, "k_star": kstar, "n_test": next(c["n_test"] for c in cells if c["style"] == h
                                                                        and c["measurable"])}
    ks = sorted((s["k_star"] if s["k_star"] is not None else 99) for s in summary.values())
    med = (ks[2] + ks[3]) / 2
    below = sum(int(s["rate_by_k"][max(s["rate_by_k"])] < 0.9) for s in summary.values())   # at its largest measurable k
    res = {"per_style": summary, "median_k_star": med, "styles_below_90_at_largest_k": below,
           "neg_fired_total": sum(c.get("neg_fired", 0) for c in cells),
           "neg_tested_total": sum(c.get("n_neg_test", 0) for c in cells),
           "marks": {"T1_learned_request": med <= 3, "T2_memorised": below >= 3}}
    res["verdict"] = ("learned a request" if res["marks"]["T1_learned_request"] else
                      "memorised wordings" if res["marks"]["T2_memorised"] else "in between")
    (out / "summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
