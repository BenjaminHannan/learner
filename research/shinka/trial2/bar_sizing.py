#!/usr/bin/env python3
"""Bar sizing from existing noise runs only (seeds 100-104). Rule fixed in G0-PASSMARK.md. $0.

Usage: python bar_sizing.py [--out ../results/trial2/bar_sizing.json]
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOISE = HERE.parent / "results" / "noise"
BAR, N_FRESH = 0.05, 6
WRITERS = ("baseline_singlepool", "mean_pool", "two_pool", "multihead_pool")  # oracle excluded: not a legal writer
OLD_SEEDS = (100, 101, 102, 103, 104)


def load(writer: str) -> dict[int, float]:
    out = {}
    for seed in OLD_SEEDS:
        text = (NOISE / f"{writer}_{seed}.txt").read_text()
        out[seed] = json.loads(re.search(r"(\{.*\})", text).group(1))["acc_novel"]
    return out


def chi2_ci_sd(s: float, n: int) -> tuple[float, float]:
    # 95% interval on an sd from n paired values, chi-square quantiles for 4 dof (n=5)
    if n != 5:
        raise ValueError("table is for n=5")
    lo_q, hi_q = 0.4844, 11.143   # chi2(4) 0.025 / 0.975 quantiles
    return s * math.sqrt(4 / hi_q), s * math.sqrt(4 / lo_q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "results" / "trial2" / "bar_sizing.json"))
    a = ap.parse_args()
    acc = {w: load(w) for w in WRITERS}
    pairs = {}
    for x, y in itertools.combinations(WRITERS, 2):
        d = [acc[x][s] - acc[y][s] for s in OLD_SEEDS]
        pairs[f"{x} - {y}"] = {"mean_diff": statistics.mean(d), "sd_diff": statistics.stdev(d)}
    mh = {k: v for k, v in pairs.items() if "multihead_pool" in k}
    worst_key = max(mh, key=lambda k: mh[k]["sd_diff"])
    s = mh[worst_key]["sd_diff"]
    se = s / math.sqrt(N_FRESH)
    lo, hi = chi2_ci_sd(s, len(OLD_SEEDS))
    needed = 2 * se
    raised = max(BAR, math.ceil(needed / 0.005 - 1e-9) * 0.005)
    out = {
        "per_seed_acc_novel": acc, "pairs": pairs,
        "multihead_pairs_worst": {"pair": worst_key, "sd_diff": s, "se_over_6_seeds": se, "two_se": needed,
                                  "sd_95ci": [lo, hi], "two_se_at_ci_upper": 2 * hi / math.sqrt(N_FRESH)},
        "median_sd_all_pairs": statistics.median(p["sd_diff"] for p in pairs.values()),
        "bar_in_plan": BAR, "two_se_exceeds_bar": needed > BAR, "required_bar": raised,
        "multihead_sd_alone": statistics.stdev(acc["multihead_pool"].values()),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_seed_acc_novel", "pairs")}, indent=2))
    for k, v in pairs.items():
        print(f"{k:50s} mean {v['mean_diff']:+.3f}  sd {v['sd_diff']:.3f}")


if __name__ == "__main__":
    main()
