#!/usr/bin/env python3
"""Exp 261 -- pick theta on dev with 257's sealed tau rule.

Dev = 257's dev split (dev_tau.jsonl + v4.1 v41_preds.json, kept frames
recomputed locally: identical to the sealed numbers) PLUS the new checker dev
set (dev_checker.jsonl + its GPU ear preds). For each row: parse -> brake ->
canonicalise -> checker split at theta (ASK always saved). Sweep theta
0.00..1.00 step 0.05:

  recall     = checker-saved TEACH matching gold / all gold TEACH (all rows)
  wrong_rate = checker-saved TEACH matching no gold frame / non-question rows

Rule (257's, adapted): the theta with the most recall at wrong_rate <= 1%;
otherwise the lowest wrong_rate; ties -> the smallest theta. Writes the theta
curve JSON and prints per-tag cells at the pick.

Also reports ear+checker latency: per turn, ear greedy ms (preds file, both
models resident on the 5070 Ti) + summed checker ms for that turn's frames.

python claude_earcheck261_theta.py --dev257 D --preds257 P --devcheck D2 --predscheck P2 --pyes Y.json --manifest M.json --out OUT.json
(pyps + manifest may be given twice for the two sources.)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_score as S  # noqa: E402
import claude_smolear235b_tau as T  # noqa: E402
import claude_earcheck261_arms as A  # noqa: E402

GRID = [round(i * 0.05, 2) for i in range(0, 21)]
MAX_RATE = 0.01


def load_set(dev_path, preds_path):
    rows = [json.loads(x) for x in Path(dev_path).read_text().splitlines() if x.strip()]
    preds = json.loads(Path(preds_path).read_text(encoding="utf-8"))["preds"]
    return rows, preds


def evaluate(all_rows, theta):
    """all_rows: list of dict(row, gold, kept_canon, plist, ear_ms, check_ms).
    Returns (agg_all, agg_bytag)."""
    agg = {}
    for r in all_rows:
        saved, _ = A.checker_split(r["kept_canon"], r["plist"], theta)
        gold = r["gold"]
        th, tx, tn = S.match(saved, gold, "TEACH")
        nonq = not any(f["act"] == "ASK" for f in gold)
        for key in ("all", r["tag"]):
            a = agg.setdefault(key, dict(rows=0, nonq=0, gold=0, hit=0, wrong=0,
                                         unsure=0))
            a["rows"] += 1
            a["nonq"] += nonq
            a["gold"] += tn
            a["hit"] += th
            a["wrong"] += len(tx)
            a["unsure"] += sum(1 for f in r["kept_canon"]
                               if f.get("act") == "TEACH") - (th + len(tx))
        lat = r.get("lat_ms")
        if lat is not None:
            agg.setdefault("_lat", []).append(lat)
    for k, a in agg.items():
        if k == "_lat" or not isinstance(a, dict):
            continue
        a["recall"] = a["hit"] / a["gold"] if a["gold"] else None
        a["wrong_rate"] = a["wrong"] / a["nonq"] if a["nonq"] else None
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev257", required=True)
    ap.add_argument("--preds257", required=True)
    ap.add_argument("--devcheck", required=True)
    ap.add_argument("--predscheck", required=True)
    ap.add_argument("--pyes", nargs="+", required=True)
    ap.add_argument("--manifest", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pmap = {}
    for path in a.pyes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            pmap[cid] = (float(v["p"]), float(v.get("ms", 0.0)))

    all_rows = []
    lat_all = []
    for dev_path, preds_path, src in ((a.dev257, a.preds257, "d257"),
                                      (a.devcheck, a.predscheck, "dc")):
        rows, preds = load_set(dev_path, preds_path)
        for row in rows:
            p = preds[row["id"]]
            arms = A.base_arms(p["raw"], row["turn"], p["greedy_lp"], p["beams"])
            kept = arms["kept_canon"]
            plist, cms = [], 0.0
            k = 0
            for f in kept:
                if f.get("act") != "TEACH":
                    continue
                cid = f"{src}:{row['id']}#t{k}"
                k += 1
                pv, ms = pmap[cid]
                plist.append(pv)
                cms += ms
            gold = T.gold_frames(row["frames"])
            ear_ms = float(p.get("ms_greedy", p.get("ms", 0.0)))
            all_rows.append(dict(tag=row.get("tag"), gold=gold, kept_canon=kept,
                                 plist=plist, lat_ms=ear_ms + cms))
            lat_all.append(ear_ms + cms)

    sweep = []
    for theta in GRID:
        ev = evaluate(all_rows, theta)
        Al = ev["all"]
        sweep.append(dict(theta=theta, recall=Al["recall"], wrong=Al["wrong"],
                          wrong_rate=Al["wrong_rate"], unsure=Al["unsure"],
                          hit=Al["hit"], gold=Al["gold"]))
    ok = [s for s in sweep if (s["wrong_rate"] or 1.0) <= MAX_RATE]
    if ok:
        best = max(s["recall"] for s in ok)
        choice = min(s["theta"] for s in ok if s["recall"] == best)
        fallback = False
    else:
        low = min(s["wrong_rate"] for s in sweep)
        choice = min(s["theta"] for s in sweep if s["wrong_rate"] == low)
        fallback = True
    detail = evaluate(all_rows, choice)
    res = dict(rule="max recall s.t. wrong_rate <= 0.01; ties -> smallest theta; "
                    "if none qualifies: lowest wrong_rate, ties -> smallest theta",
               fallback_used=fallback, theta=choice, sweep=sweep,
               at_choice={k: v for k, v in detail.items() if k != "_lat"},
               latency=dict(n=len(lat_all),
                            median_ms=round(statistics.median(lat_all), 1),
                            p90_ms=round(sorted(lat_all)[int(0.9 * len(lat_all))], 1),
                            max_ms=round(max(lat_all), 1)))
    Path(a.out).write_text(json.dumps(res, indent=1))
    print("theta =", choice, "fallback:", fallback)
    for s in sweep:
        print(s)
    for tag, v in sorted(res["at_choice"].items()):
        print(tag, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in v.items()})
    print("latency", res["latency"])


if __name__ == "__main__":
    main()
