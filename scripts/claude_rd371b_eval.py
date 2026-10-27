#!/usr/bin/env python3
"""rd-371b: bar sweep on dev and panel scoring (counts only).

sweep: python claude_rd371b_eval.py sweep --pred PRED.jsonl --judged JUDGE_OUT.jsonl [--pair ...] --out SWEEP.json
       Registered bar rule: the LOWEST grid value whose accepted notes are at most 4% "unsupported" on dev
       (accepted > 0); if none, the largest grid value.
score: python claude_rd371b_eval.py score --pred PRED.jsonl --key KEY.jsonl --threshold T --out SCORE.json
       KEY rows {"dialog","t","k","kind","label": "ok"|"unsupported"|"excluded"}.
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

GRID = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.999, 0.9995, 0.9999]
TARGET = 0.04


def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def pairs(pred_paths, judged_paths):
    P = {}
    for p in pred_paths:
        for r in load(p):
            P[(r["dialog"], int(r["t"]), int(r["k"]))] = r["p_yes"]
    out = []
    for jp in judged_paths:
        for r in load(jp):
            for k, v in enumerate(r["verdicts"]):
                key = (r["dialog"], int(r["t"]), k)
                if key in P:
                    out.append((P[key], v))
    return out


def sweep(a):
    xs = pairs(a.pred, a.judged)
    table, T = [], None
    for g in GRID:
        acc = [v for p, v in xs if p >= g]
        uns = sum(v == "unsupported" for v in acc)
        ok_all = sum(v == "ok" for _, v in xs)
        row = {"t": g, "accepted": len(acc), "unsupported": uns, "ok_kept": sum(v == "ok" for v in acc),
               "ok_total": ok_all, "rate": round(uns / len(acc), 4) if acc else None}
        table.append(row)
        if T is None and acc and uns / len(acc) <= TARGET:
            T = g
    res = {"T": T if T is not None else GRID[-1], "rule": "lowest grid value with dev unsupported/accepted <= 0.04",
           "notes": len(xs), "verdicts": dict(Counter(v for _, v in xs)), "sweep": table}
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("T", "notes", "verdicts")}))


def score(a):
    P = {(r["dialog"], int(r["t"]), int(r["k"])): r for r in load(a.pred)}
    c, ms = Counter(), []
    for r in load(a.key):
        p = P.get((r["dialog"], int(r["t"]), int(r["k"])))
        if p is None:
            c["missing_pred"] += 1
            continue
        ms.append(p.get("ms", 0))
        lab, kind, acc = r["label"], r.get("kind", "all"), p["p_yes"] >= a.threshold
        c[f"{lab}_total"] += 1
        c[f"{kind}:{lab}_total"] += 1
        if acc:
            c["accepted"] += 1
            c[f"{lab}_kept"] += 1
            c[f"{kind}:{lab}_kept"] += 1
    res = dict(sorted(c.items()))
    acc_scored = c["ok_kept"] + c["unsupported_kept"]
    res["threshold"] = a.threshold
    res["C1_unsupported_share_of_accepted"] = round(c["unsupported_kept"] / acc_scored, 4) if acc_scored else None
    res["C2_ok_kept_share"] = round(c["ok_kept"] / c["ok_total"], 4) if c["ok_total"] else None
    res["ms_median"] = statistics.median(ms) if ms else None
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sweep")
    s.add_argument("--pred", action="append", required=True)
    s.add_argument("--judged", action="append", required=True)
    s.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--pred", required=True)
    s.add_argument("--key", required=True)
    s.add_argument("--threshold", type=float, required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    (sweep if a.cmd == "sweep" else score)(a)


if __name__ == "__main__":
    main()
