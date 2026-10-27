#!/usr/bin/env python3
"""Exp 257 -- dev report (no bars): per dev tag, TEACH hit/gold/wrong/unsure (the sealed
claude_smolear235b_tau.evaluate) plus ASK hit/gold and stray ASKs, for arms A_raw / A_brake / A
at a given tau, for one or more prediction files (v3 vs v4). Table v2 installed.

python claude_smolear257_devreport.py --dev DEV.jsonl --tau T --preds v3=P3.json v4=P4.json --out OUT.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_smolear235b_beam as B  # noqa: E402
import claude_smolear235b_tau as T  # noqa: E402


def ask_eval(rows, preds, tau):
    agg = {}
    for row in rows:
        p = preds[row["id"]]
        gold = T.gold_frames(row["frames"])
        g = B.gate(row["turn"], p["raw"], p["greedy_lp"], [tuple(x) for x in p["beams"]], tau)
        arms = {"A_raw": [f for f in E.parse_frames(p["raw"]) if f["act"] in ("TEACH", "ASK")],
                "A_brake": g["kept_brake"], "A": g["saved"]}
        for arm, fr in arms.items():
            ah, ax, an = S.match(fr, gold, "ASK")
            for key in ("all", row["tag"]):
                a = agg.setdefault(arm, {}).setdefault(key, dict(ask_hit=0, ask_gold=0, ask_extra=0))
                a["ask_hit"] += ah
                a["ask_gold"] += an
                a["ask_extra"] += len(ax)
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--tau", type=float, required=True)
    ap.add_argument("--preds", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in Path(a.dev).read_text().splitlines() if x.strip()]
    res = {}
    for spec in a.preds:
        name, path = spec.split("=", 1)
        preds = json.loads(Path(path).read_text(encoding="utf-8"))["preds"]
        te, ak = T.evaluate(rows, preds, a.tau), ask_eval(rows, preds, a.tau)
        res[name] = {arm: {tag: {**te[arm][tag], **ak[arm][tag]} for tag in te[arm]} for arm in te}
    Path(a.out).write_text(json.dumps(dict(tau=a.tau, report=res), indent=1))
    tags = sorted(next(iter(res.values()))["A"])
    for arm in ("A_brake", "A"):
        print(f"== {arm} (tau {a.tau})  cells: TEACH hit/gold wrong [unsure] | ASK hit/gold +extra")
        for tag in tags:
            cells = []
            for name in res:
                v = res[name][arm][tag]
                u = f" [{v['unsure']}]" if arm == "A" else ""
                cells.append(f"{name}: {v['hit']}/{v['gold']} w{v['wrong']}{u} | {v['ask_hit']}/{v['ask_gold']} +{v['ask_extra']}")
            print(f"  {tag:10s} " + "   ".join(cells))


if __name__ == "__main__":
    main()
