#!/usr/bin/env python3
"""bm-396 (dev, report only; benchmarks thread, 2026-09-26): how much of the plain 1B's LoCoMo loss is answer length,
and how much is content? Runs on replies that already exist; nothing is generated, trained or tuned. The gold answer
is used only to measure the replies, never to change them. Counts and averages only; nothing is quoted.
All numbers are "after using LoCoMo for development".

Per arm, over categories 1-4, it reports:
- f1: the sealed scorer's F1 (a check).
- all_gold_tokens: replies whose scored words contain every gold word (after the scorer's normalising and stemming).
- zero_overlap: replies sharing no scored word with the gold.
- best_span_f1: mean F1 if each reply were cut to its single best contiguous run of words (an optimistic, gold-guided
  bound on what faithful shortening could reach; a real shortener cannot see the gold).
- keep_matches_f1: the looser bound 2m/(m+g), keeping only the matching words (m of them, g gold words).
- later_line_better: replies whose full text (all lines) scores higher than the scored first line.
Multi-hop (category 1) uses whole-answer token F1 for both bounds, so those two columns are approximate there.

It also prints a clustered bootstrap (resampling the 10 conversations, not the 1,540 questions) for chosen pairs,
because questions from one chat are not independent.

  python -B scripts/claude_bm396_audit.py --data DATA --runs DIR[,DIR2] --arms T,Q2,E20 --pairs E:Rb2,Q2:T
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390_score as SC  # noqa: E402

SEED = 396
BOOT = 10000


def _rows(dirs: list[Path], arm: str) -> list[dict]:
    for d in dirs:
        files = sorted(glob.glob(str(d / f"locomo_{arm}.jsonl"))) or sorted(glob.glob(str(d / f"locomo_{arm}.part*.jsonl")))
        if files:
            return [json.loads(x) for f in files for x in open(f, encoding="utf-8") if x.strip()]
    raise SystemExit(f"bm396: no locomo_{arm} rows")


def _toks(s: str) -> list[str]:
    return [SC.ps.stem(w) for w in SC.normalize_answer(s).split()]


def _f1(p: list[str], g: list[str]) -> float:
    same = sum((Counter(p) & Counter(g)).values())
    if not same:
        return 0.0
    pr, rc = same / len(p), same / len(g)
    return 2 * pr * rc / (pr + rc)


def _gold(qa: dict) -> str:
    g = str(qa["answer"])
    return g.split(";")[0].strip() if qa["category"] == 3 else g


def audit(gold: dict, rows: list[dict]) -> tuple[dict, dict]:
    n = allg = zero = later = 0
    f1s, span, keep = [], [], []
    per = {}
    for r in rows:
        if r["category"] not in (1, 2, 3, 4):
            continue
        qa = gold[r["qid"]]
        n += 1
        pred = SC.official_clean(r["reply"], r["category"], None)
        score = SC.official_score(pred, qa["answer"], qa["category"])
        per[r["qid"]] = score
        f1s.append(score)
        pt, gt = _toks(pred), _toks(_gold(qa))
        m = sum((Counter(pt) & Counter(gt)).values())
        allg += int(bool(gt) and m == len(gt))
        zero += int(m == 0)
        keep.append(2 * m / (m + len(gt)) if m else 0.0)
        best = max((_f1(pt[i:j], gt) for i in range(len(pt)) for j in range(i + 1, len(pt) + 1)), default=0.0)
        span.append(max(best, score))
        full = " ".join(x.strip() for x in r["reply"].split("\n") if x.strip())
        full_clean = SC.official_clean(full, r["category"], None)
        later += int(SC.official_score(full_clean, qa["answer"], qa["category"]) > score + 1e-9)
    mean = lambda v: round(100 * sum(v) / max(1, len(v)), 2)  # noqa: E731
    return ({"questions": n, "f1": mean(f1s), "all_gold_tokens": allg, "zero_overlap": zero,
             "best_span_f1": mean(span), "keep_matches_f1": mean(keep), "later_line_better": later}, per)


def cluster_boot(a: dict, b: dict) -> dict:
    ids = sorted(q for q in a if q in b)
    convs = sorted({q.split("#")[0] for q in ids})
    by = {c: np.array([a[q] - b[q] for q in ids if q.split("#")[0] == c]) for c in convs}
    sums = np.array([by[c].sum() for c in convs])
    cnts = np.array([len(by[c]) for c in convs])
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(convs), size=(BOOT, len(convs)))
    means = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    per_conv = [round(100 * float(by[c].mean()), 2) for c in convs]
    return {"n": len(ids), "diff": round(100 * float(np.mean([a[q] - b[q] for q in ids])), 2),
            "ci95_by_conversation": [round(100 * float(np.percentile(means, 2.5)), 2),
                                     round(100 * float(np.percentile(means, 97.5)), 2)],
            "per_conversation": per_conv}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--runs", required=True, help="comma-separated folders, searched in order")
    ap.add_argument("--arms", required=True)
    ap.add_argument("--pairs", default="")
    a = ap.parse_args()
    lc = json.loads((Path(a.data) / "locomo10.json").read_text(encoding="utf-8"))
    gold = {f"{c['sample_id']}#{i}": qa for c in lc for i, qa in enumerate(c["qa"])}
    dirs = [Path(x) for x in a.runs.split(",")]
    arms = [x for x in a.arms.split(",") if x]
    for p in a.pairs.split(","):
        if p:
            arms += [x for x in p.split(":") if x not in arms]
    per = {}
    for arm in arms:
        stats, per[arm] = audit(gold, _rows(dirs, arm))
        print(json.dumps({arm: stats}), flush=True)
    for p in a.pairs.split(","):
        if p:
            x, y = p.split(":")
            print(json.dumps({f"{x}-{y}": cluster_boot(per[x], per[y])}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
