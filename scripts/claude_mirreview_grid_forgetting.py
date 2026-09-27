#!/usr/bin/env python3
"""Read-only check for the MIR-replay review (reviews/claude-mir-replay-review-2026-09-27.md).

Uses only saved per-puzzle predictions from the two replay-scheduling experiments (seeds 41-46 and 61-66).
For grid5 test puzzles solved after phase A: which were lost by the end of phase C, how well the number of
blank cells (or the stop round at A) predicts that, and whether the same puzzles are lost in both arms of a seed.
No training, no model loading. Run: python3 scripts/claude_mirreview_grid_forgetting.py
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "artifacts/codex-autoroute-20260927"
EXPS = [("late", ROOT / "panels", ROOT / "run", range(41, 47), ("baseline", "late_replay")),
        ("targeted", ROOT / "hard_replay/panels", ROOT / "hard_replay/run", range(61, 67), ("baseline", "hard_grid_replay"))]

def stop_round(p, q):
    return next((r for r in range(2, 48) if q[r] > .5 and p[r] == p[r - 1] == p[r - 2]), 47)

def correct(row, pred):
    tgt = [t for rr in row["target"] for t in rr]; slot = [s for rr in row["slot"] for s in rr]
    p = pred["predictions"][stop_round(pred["predictions"], pred["stop_probabilities"])]
    return all(p[i] == tgt[i] for i in range(len(tgt)) if slot[i])

def auroc(scores_pos, scores_neg):
    n = 0; s = 0.
    for a in scores_pos:
        for b in scores_neg:
            n += 1; s += 1. if a > b else .5 if a == b else 0.
    return s / n if n else float("nan")

allrows = []
for name, pdir, rdir, seeds, arms in EXPS:
    for seed in seeds:
        panel = json.loads((pdir / f"seed{seed}.json").read_text())
        grids = {r["id"]: r for r in panel["final"] if r["env"] == "grids"}
        res = {}
        for arm in arms:
            d = rdir / f"{arm}-s{seed}"
            ph = {}
            for P in "ABC":
                preds = {}
                for line in open(d / f"{P}.jsonl"):
                    j = json.loads(line)
                    if j["id"] in grids:
                        preds[j["id"]] = j
                ph[P] = preds
            ok = {P: {i: correct(grids[i], ph[P][i]) for i in grids} for P in "ABC"}
            stopA = {i: stop_round(ph["A"][i]["predictions"], ph["A"][i]["stop_probabilities"]) + 1 for i in grids}
            saved = json.loads((d / "result.json").read_text())["phases"]
            for P in "ABC":
                assert sum(ok[P].values()) == saved[P]["score"]["grids5"]["right"], (name, arm, seed, P)
            res[arm] = (ok, stopA)
        for i, r in grids.items():
            blanks = sum(sum(x) for x in r["slot"])
            rec = dict(exp=name, seed=seed, id=i, blanks=blanks)
            for arm, (ok, stopA) in res.items():
                rec[arm] = dict(A=ok["A"][i], B=ok["B"][i], C=ok["C"][i], stopA=stopA[i])
            allrows.append(rec)

print("recomputed own-stop grids5 scores match result.json for every arm/seed/phase")
for name, _, _, seeds, arms in EXPS:
    rows = [r for r in allrows if r["exp"] == name]
    print(f"\n== {name} experiment ({len(rows)} grid test puzzles over {len(seeds)} seeds)")
    for arm in arms:
        kept = [r for r in rows if r[arm]["A"]]
        lost = [r for r in kept if not r[arm]["C"]]
        # difficulty predictors available BEFORE new learning: blanks, rounds-to-stop at A
        auc_b = auroc([r["blanks"] for r in lost], [r["blanks"] for r in kept if r[arm]["C"]])
        auc_s = auroc([r[arm]["stopA"] for r in lost], [r[arm]["stopA"] for r in kept if r[arm]["C"]])
        qs = sorted(r["blanks"] for r in kept); cut = [qs[len(qs) * k // 4] for k in (1, 2, 3)]
        bins = [[r for r in kept if (r["blanks"] < cut[0]) if k == 0] or
                [r for r in kept if k > 0 and (cut[k - 1] <= r["blanks"] < (cut[k] if k < 3 else 99))] for k in range(4)]
        rates = [f"{sum(not r[arm]['C'] for r in b)}/{len(b)}" for b in bins]
        print(f"  {arm:17s} correct@A {len(kept)}, lost by C {len(lost)} ({len(lost)/len(kept):.1%}); "
              f"AUROC(blanks) {auc_b:.2f}, AUROC(stop round at A) {auc_s:.2f}; loss by blanks quartile (cuts {cut}): {rates}")
    # same-puzzle consistency across the two arms within a seed
    a1, a2 = arms
    obs = exp = 0.
    for seed in seeds:
        rs = [r for r in rows if r["seed"] == seed and r[a1]["A"] and r[a2]["A"]]
        l1 = {r["id"] for r in rs if not r[a1]["C"]}; l2 = {r["id"] for r in rs if not r[a2]["C"]}
        obs += len(l1 & l2); exp += len(l1) * len(l2) / max(1, len(rs))
    print(f"  puzzles lost by C in BOTH arms (same seed, same test puzzles): observed {obs:.0f} vs {exp:.1f} expected if independent "
          f"(ratio {obs/exp:.2f})")

print("\n-- overlap expected if independent WITHIN blank-count strata (same seed): does puzzle identity matter beyond blanks?")
for name, _, _, seeds, arms in EXPS:
    rows = [r for r in allrows if r["exp"] == name]
    a1, a2 = arms
    obs = exp = 0.
    for seed in seeds:
        for b in sorted({r["blanks"] for r in rows}):
            rs = [r for r in rows if r["seed"] == seed and r["blanks"] == b and r[a1]["A"] and r[a2]["A"]]
            l1 = {r["id"] for r in rs if not r[a1]["C"]}; l2 = {r["id"] for r in rs if not r[a2]["C"]}
            obs += len(l1 & l2); exp += len(l1) * len(l2) / max(1, len(rs))
    print(f"  {name}: observed {obs:.0f} vs {exp:.1f} expected given blank count (ratio {obs/exp:.2f})")
