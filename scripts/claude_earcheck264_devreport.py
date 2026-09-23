#!/usr/bin/env python3
"""Exp 264 -- QA-on-dev analysis (dev only, report only, no tuning).

Runs 261's sealed pipeline (brake -> canon) on each dev set with its GPU ear
preds, applies the QA checker (recorded answers) + 261b guard to the kept TEACH
frames, and reports: holds, false holds (held frame matched gold) and wrong
saves let through, by tag.

python claude_earcheck264_devreport.py --set DEV PREDS SRC [--set ...] --qa Q.json [--out O.json]
Each --set is one dev file plus its GPU ear preds plus the QA id prefix.
QA ids: "<src>:<rowid>#t<k>#q<value|owner|relation>".
Held entries carry category only, never turn text.
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
import claude_earcheck264_arms as B  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", nargs=3, action="append", required=True,
                    metavar=("DEV", "PREDS", "SRC"))
    ap.add_argument("--qa", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    qamap = {}
    for path in a.qa:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            qamap[cid] = (str(v.get("text", "")), float(v.get("ms", 0.0)))

    n_saved = n_held_qa = n_held_guard = n_false = n_wrong = 0
    by_tag = {}
    held = []
    lat = []
    for dev_path, preds_path, src in a.set:
        rows = [json.loads(x) for x in Path(dev_path).read_text().splitlines() if x.strip()]
        preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))["preds"]
        for row in rows:
            p = preds[row["id"]]
            arms = A.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
            kept = arms["kept_canon"]
            n_teach = sum(1 for f in kept if f.get("act") == "TEACH")
            qa_texts = {}
            for k in range(n_teach):
                try:
                    av, avms = qamap[f"{src}:{row['id']}#t{k}#qvalue"]
                    ao, aoms = qamap[f"{src}:{row['id']}#t{k}#qowner"]
                    ar, arms_ = qamap[f"{src}:{row['id']}#t{k}#qrelation"]
                except KeyError:
                    continue
                qa_texts[k] = (av, ao, ar, avms + aoms + arms_)
                lat.extend([avms, aoms, arms_])
            keptA, heldG, savedQA, unsureQA, _, _ = B.qa_arm(kept, qa_texts)
            gold = T.gold_frames(row["frames"])
            tag = row.get("tag")
            t = by_tag.setdefault(tag, dict(kept=0, qa_held=0, guard_held=0,
                                            false=0, wrong=0, reasons=Counter()))
            t["kept"] += n_teach
            n_saved += n_teach
            for h in unsureQA:
                th1, _, _ = S.match([h], gold, "TEACH")
                right = th1 == 1
                t["qa_held"] += 1
                t["reasons"]["qa:" + "+".join(h.get("qa_failed", []))] += 1
                n_held_qa += 1
                if right:
                    t["false"] += 1
                    n_false += 1
                held.append(dict(row=row["id"], tag=tag, stage="QA",
                                 category="qa:" + "+".join(h.get("qa_failed", [])),
                                 right=bool(right)))
            for h in heldG:
                base = {kk: vv for kk, vv in h.items() if kk not in ("why", "guard")}
                th1, _, _ = S.match([base], gold, "TEACH")
                right = th1 == 1
                t["guard_held"] += 1
                t["reasons"][h.get("guard")] += 1
                n_held_guard += 1
                if right:
                    t["false"] += 1
                    n_false += 1
                held.append(dict(row=row["id"], tag=tag, stage="GUARD",
                                 category=h.get("guard"), right=bool(right)))
            th, tx, tn = S.match(keptA, gold, "TEACH")
            t["wrong"] += len(tx)
            n_wrong += len(tx)
            if tx:
                held.append(dict(row=row["id"], tag=tag, stage="LET_THROUGH",
                                 category="qa-passed-wrong", right=False,
                                 n_wrong=len(tx)))
    import statistics
    for t in by_tag.values():
        t["reasons"] = dict(t["reasons"])
    res = dict(kept_teach=n_saved, qa_held=n_held_qa, guard_held=n_held_guard,
               false_holds=n_false, wrong_let_through=n_wrong, by_tag=by_tag,
               held=held,
               qa_ms=dict(n=len(lat), median=round(statistics.median(lat), 1) if lat else None,
                          p90=round(sorted(lat)[int(0.9 * len(lat))], 1) if lat else None,
                          max=round(max(lat), 1) if lat else None))
    print(json.dumps(dict(kept=n_saved, qa_held=n_held_qa, guard_held=n_held_guard,
                          false=n_false, wrong=n_wrong), indent=1))
    for tag in sorted(by_tag, key=str):
        print(tag, by_tag[tag])
    if res["qa_ms"]["n"]:
        print("qa_ms", res["qa_ms"])
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
        print("wrote", a.out)


if __name__ == "__main__":
    main()
