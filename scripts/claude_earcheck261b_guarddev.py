#!/usr/bin/env python3
"""Exp 261b -- guard-on-dev analysis (dev only, report only, no tuning).

Runs 261's sealed pipeline (brake -> canon -> checker split at theta 0.25,
prompt B pYES) on 261's dev (257 dev split + dev_checker.jsonl with their GPU
ear preds), then applies the 261b span guard to the checker-saved TEACH
frames. Reports: how many kept frames the guard holds back, by tag, and how
many of those were right (false holds: held frame matches a gold frame).

python claude_earcheck261b_guarddev.py --set DEV PREDS SRC [--set DEV PREDS SRC ...] --pyes Y [--out O.json]
Each --set is one dev file plus its GPU ear preds plus the pYES id prefix
("d257" for 257 dev, "dc" for 261 checker dev, custom for 261b dev).
Writes JSON {summary, by_tag, held:[...]} to --out (or stdout if omitted).
Held entries carry category (guard reason) only, never turn text.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_score as S  # noqa: E402
import claude_smolear235b_tau as T  # noqa: E402
import claude_earcheck261_arms as A  # noqa: E402
import claude_earcheck261b_guard as G  # noqa: E402
import claude_earcheck261b_arms as B  # noqa: E402

THETA = 0.25


def load_set(dev_path, preds_path):
    rows = [json.loads(x) for x in Path(dev_path).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))["preds"]
    return rows, preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", nargs=3, action="append", required=True,
                    metavar=("DEV", "PREDS", "SRC"))
    ap.add_argument("--pyes", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    pmap = {}
    for path in a.pyes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            pmap[cid] = float(v["p"])

    n_saved = n_held = n_false = 0
    by_tag = {}
    held = []
    for dev_path, preds_path, src in a.set:
        rows, preds = load_set(dev_path, preds_path)
        for row in rows:
            p = preds[row["id"]]
            arms = A.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
            kept = arms["kept_canon"]
            plist, k = [], 0
            for f in kept:
                if f.get("act") != "TEACH":
                    continue
                plist.append(pmap[f"{src}:{row['id']}#t{k}"])
                k += 1
            saved, _ = A.checker_split(kept, plist, THETA)
            teach_saved = [f for f in saved if f.get("act") == "TEACH"]
            kept2, held2, _ = B.apply_guard(saved)
            gold = T.gold_frames(row["frames"])
            tag = row.get("tag")
            t = by_tag.setdefault(tag, dict(saved=0, held=0, false=0,
                                            reasons=Counter()))
            t["saved"] += len(teach_saved)
            n_saved += len(teach_saved)
            for f in held2:
                th1, _, _ = S.match([f], gold, "TEACH")
                right = th1 == 1
                t["held"] += 1
                t["reasons"][f.get("guard")] += 1
                n_held += 1
                if right:
                    t["false"] += 1
                    n_false += 1
                held.append(dict(row=row["id"], tag=tag, category=f.get("guard"),
                                 right=bool(right)))
    for t in by_tag.values():
        t["reasons"] = dict(t["reasons"])
    res = dict(theta=THETA, checker_saved_teach=n_saved, guard_held=n_held,
               false_holds=n_false, by_tag=by_tag, held=held)
    print(json.dumps(dict(theta=THETA, saved=n_saved, held=n_held,
                           false_holds=n_false), indent=1))
    for tag in sorted(by_tag, key=str):
        print(tag, by_tag[tag])
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
        print("wrote", a.out)


if __name__ == "__main__":
    main()
