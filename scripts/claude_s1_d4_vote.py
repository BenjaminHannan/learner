#!/usr/bin/env python3
"""S1 report-only read-out: 8-view plurality vote on saved D4-arm checkpoints, dev 9x9 panel only (holdout untouched).

    python -B scripts/claude_s1_d4_vote.py run --arm loop --seed 0 --dir <eq-runs/s1-loop-pre-s0> --source <qual dir>
    python -B scripts/claude_s1_d4_vote.py selftest

For each rung in (64, 1024, 16384) and each of the 8 views of the 300 dev mazes it takes the net's answer (learned-stop
read, as B.score; plain: its one read), turns it back to the original frame and records: single-view exact counts (x of
300 for each view), the plurality-vote exact count, and how many mazes get the same answer in all 8 views. Ties in the
vote go to the earliest view in order 0..7. Never used for any mark.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_s1_d4_aug as A  # noqa: E402

RUNGS = (64, 1024, 16384)


def plurality(answers):
    """answers: list of 8 grids (original frame). Returns the most common one, earliest view on ties."""
    keys = [json.dumps(a) for a in answers]
    best = max(range(len(keys)), key=lambda i: (Counter(keys)[keys[i]], -i))
    return answers[best]


def tally(views_ok, vote_ok, all_same, n):
    return {"single_view_right": views_ok, "single_view_mean": sum(views_ok) / len(views_ok),
            "vote_right": vote_ok, "same_in_all_8": all_same, "n": n}


def predictions(net, items, fixed_depth, batch=32):
    """Learned-stop read of each item, same rule as claude_fewex_bench.score; returns grids (lists of rows)."""
    import torch
    import claude_fewex_bench as B
    N = B.N
    out = []
    net.eval()
    with torch.no_grad():
        for i in range(0, len(items), batch):
            chunk = items[i:i + batch]
            t, s, _ = N.tensors(chunk)
            h, w = t.shape[1:]
            if net.arm == "plain":
                cells, _ = net.forward(t, s)
                sel = cells[-1].argmax(-1).tolist()
            else:
                if hasattr(net, "infer_rounds"):
                    ps, qs = net.infer_rounds(t, s, B.MAX_ROUNDS)
                    ps, qs = ps.tolist(), qs.tolist()
                else:
                    cells, stops = net.forward(t, s)
                    ps = torch.stack([x.argmax(-1) for x in cells], 1).tolist()
                    qs = torch.stack([x.float().sigmoid() for x in stops], 1).tolist()
                rr = [next((r + 1 for r in range(2, B.MAX_ROUNDS)
                            if q[r] > .5 and p[r] == p[r - 1] == p[r - 2]), B.MAX_ROUNDS) for p, q in zip(ps, qs)]
                sel = [p[r - 1] for p, r in zip(ps, rr)]
            out += [[a[j * w:(j + 1) * w] for j in range(h)] for a in sel]
    return out


def vote_rung(net, items, fixed_depth):
    import claude_fewex_bench as B
    per_view = []
    for t in range(8):
        turned = [A.d4_item(it, t) for it in items]
        preds = predictions(net, turned, fixed_depth)
        per_view.append([A.unturn(p, t) for p in preds])
    views_ok = [sum(int(B.exact(it, per_view[t][i])) for i, it in enumerate(items)) for t in range(8)]
    vote_ok = same = 0
    for i, it in enumerate(items):
        answers = [per_view[t][i] for t in range(8)]
        vote_ok += int(B.exact(it, plurality(answers)))
        same += int(len({json.dumps(a) for a in answers}) == 1)
    return tally(views_ok, vote_ok, same, len(items))


def run(arm, seed, d, source):
    import torch
    import importlib
    import claude_fewex_bench as B
    import claude_fewex_data as D
    B.N = importlib.import_module("claude_s1_d4")
    torch.set_num_threads(1)
    depth = json.loads((Path(source) / "source.json").read_text())["fixed_depth"]
    items = D.panels()[0]["dev"][9]
    res = {"arm": arm, "seed": seed, "note": "dev 9x9 only; report-only; no mark reads this", "rungs": {}}
    for k in RUNGS:
        net = B.load_model(Path(d) / f"k{k}.pt", arm)
        res["rungs"][str(k)] = vote_rung(net, items, depth)
        print(json.dumps({"phase": "vote", "arm": arm, "seed": seed, "k": k, **res["rungs"][str(k)]}), flush=True)
    (Path(d) / "vote.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")


def selftest():
    g = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    a, b = [[0, 0], [0, 1]], [[1, 0], [0, 0]]
    assert plurality([a, b, b, a, a, b, a, b]) == a          # 4-4 tie -> earliest view
    assert plurality([b, a, a, a, a, a, a, a]) == a
    for t in range(8):
        assert A.unturn(A.turn(g, t), t) == g
    assert len({json.dumps(A.turn(g, t)) for t in range(8)}) == 8
    print(json.dumps({"selftest": "ok", "part": "vote logic (no torch)"}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("run", "selftest"))
    p.add_argument("--arm", choices=("loop", "plain"))
    p.add_argument("--seed", type=int)
    p.add_argument("--dir")
    p.add_argument("--source")
    a = p.parse_args()
    selftest() if a.cmd == "selftest" else run(a.arm, a.seed, a.dir, a.source)


if __name__ == "__main__":
    main()
