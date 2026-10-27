#!/usr/bin/env python3
"""Exp 235b -- choose tau on the OWN dev set only (before the seal; the 235b panel is not opened).

Rule (from the brief): the tau with the most exact-TEACH recall subject to
wrong-save rate <= 1 %. Ties -> the smallest tau.
  recall          = saved TEACH frames matching a gold TEACH frame / all gold TEACH frames (all dev rows)
  wrong-save rate = saved TEACH frames matching no gold frame of that row / number of
                    non-question dev rows (rows whose gold has no ASK frame)
Grid: 0.0 .. 15.0 step 0.1.

python claude_smolear235b_tau.py --dev DEV.jsonl --preds PREDS.json --out TAU.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_smolear235b_beam as B  # noqa: E402

GRID = [round(i * 0.1, 1) for i in range(0, 151)]
MAX_RATE = 0.01


def gold_frames(lines):
    out = []
    for f in E.parse_frames("\n".join(lines)):
        if f["act"] == "TEACH":
            rs = f["relation"].split("/")
            out.append(dict(act="TEACH", subject=f["subject"], relation=[rs[0]], value=f["value"],
                            aliases=[rs[1:]]))
        elif f["act"] == "ASK":
            out.append(dict(act="ASK", subject=f["subject"], relation=f["relation"],
                            aliases=[[] for _ in f["relation"]]))
    return out


def evaluate(rows, preds, tau):
    agg = {}
    for row in rows:
        p = preds[row["id"]]
        gold = gold_frames(row["frames"])
        g = B.gate(row["turn"], p["raw"], p["greedy_lp"], [tuple(x) for x in p["beams"]], tau)
        arms = {"A_raw": [f for f in E.parse_frames(p["raw"]) if f["act"] in ("TEACH", "ASK")],
                "A_brake": g["kept_brake"], "A": g["saved"]}
        nonq = not any(f["act"] == "ASK" for f in gold)
        for arm, fr in arms.items():
            th, tx, tn = S.match(fr, gold, "TEACH")
            for key in ("all", row["tag"]):
                a = agg.setdefault(arm, {}).setdefault(key, dict(rows=0, nonq=0, gold=0, hit=0, wrong=0,
                                                                  unsure=0, guard=0))
                a["rows"] += 1
                a["nonq"] += nonq
                a["gold"] += tn
                a["hit"] += th
                a["wrong"] += len(tx)
                if arm == "A":
                    a["unsure"] += len(g["unsure"])
                    a["guard"] += len(g["guard"])
    for arm in agg.values():
        for a in arm.values():
            a["recall"] = a["hit"] / a["gold"] if a["gold"] else None
            a["wrong_rate"] = a["wrong"] / a["nonq"] if a["nonq"] else None
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in Path(a.dev).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(a.preds).read_text(encoding="utf-8"))["preds"]
    sweep = []
    for tau in GRID:
        ev = evaluate(rows, preds, tau)
        A = ev["A"]["all"]
        sweep.append(dict(tau=tau, recall=A["recall"], wrong=A["wrong"], wrong_rate=A["wrong_rate"],
                          unsure=A["unsure"], guard=A["guard"], hit=A["hit"], gold=A["gold"]))
    ok = [s for s in sweep if s["wrong_rate"] <= MAX_RATE]
    fallback = not ok
    if ok:
        best = max(s["recall"] for s in ok)
        choice = min(s["tau"] for s in ok if s["recall"] == best)
    else:
        # FALLBACK (fixed before the seal, after seeing that no tau reaches the 1 % rate on dev):
        # the tau with the LOWEST wrong-save rate; ties -> the smallest tau (most recall).
        low = min(s["wrong_rate"] for s in sweep)
        choice = min(s["tau"] for s in sweep if s["wrong_rate"] == low)
    detail = evaluate(rows, preds, choice)
    res = dict(rule=f"max recall s.t. wrong_rate <= {MAX_RATE}; ties -> smallest tau; if none qualifies: "
                    "lowest wrong_rate, ties -> smallest tau", fallback_used=fallback, tau=choice,
               at_choice=detail, sweep=sweep)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print("tau =", choice)
    for s in sweep[::5]:
        print(s)
    for arm, d in detail.items():
        for tag, v in d.items():
            print(arm, tag, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items()})


if __name__ == "__main__":
    main()
