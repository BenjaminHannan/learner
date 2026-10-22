#!/usr/bin/env python3
"""Pre-declared bar tightening (CARD2 section 3): baseline and multi-head on seeds 105-109 added to 100-104.

Rule as written in CARD2 before these runs: s = largest paired sd of acc_novel over pairs that include multi-head,
each pair on the seeds it has (multihead - baseline: 10 seeds; the others: 100-104). bar = max(0.05, 2 s / sqrt(6)
rounded up to the next 0.005). $0, CPU only. Usage: python bar_sizing_10.py
"""
import itertools, json, math, re, statistics
from pathlib import Path

NOISE = Path(__file__).resolve().parent.parent / "results" / "noise"
OUT = Path(__file__).resolve().parent.parent / "results" / "trial2" / "bar_sizing_10.json"
WRITERS = ("baseline_singlepool", "mean_pool", "two_pool", "multihead_pool")


def load(w):
    out = {}
    for seed in range(100, 110):
        f = NOISE / f"{w}_{seed}.txt"
        if f.exists():
            out[seed] = json.loads(re.search(r"(\{.*\})", f.read_text()).group(1))["acc_novel"]
    return out


acc = {w: load(w) for w in WRITERS}
pairs = {}
for x, y in itertools.combinations(WRITERS, 2):
    seeds = sorted(set(acc[x]) & set(acc[y]))
    d = [acc[x][s] - acc[y][s] for s in seeds]
    pairs[f"{x} - {y}"] = {"n": len(d), "mean_diff": statistics.mean(d), "sd_diff": statistics.stdev(d)}
mh = {k: v for k, v in pairs.items() if "multihead_pool" in k}
worst = max(mh, key=lambda k: mh[k]["sd_diff"])
s = mh[worst]["sd_diff"]
need = 2 * s / math.sqrt(6)
bar = max(0.05, math.ceil(need / 0.005 - 1e-9) * 0.005)
res = {"pairs": pairs, "worst_pair": worst, "sd": s, "two_se": need, "sealed_bar": bar,
       "multihead_novel_sd_alone_10": statistics.stdev(acc["multihead_pool"].values()),
       "n_multihead_seeds": len(acc["multihead_pool"])}
OUT.write_text(json.dumps(res, indent=2))
print(json.dumps({k: v for k, v in res.items() if k != "pairs"}, indent=2))
for k, v in pairs.items():
    print(f"{k:50s} n={v['n']} mean {v['mean_diff']:+.3f} sd {v['sd_diff']:.3f}")
