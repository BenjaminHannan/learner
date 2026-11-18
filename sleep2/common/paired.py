"""Paired comparison of Sleep-B arms on the same questions (addendum 6): exact two-sided McNemar on per-question rows.

  python backbone/sleep/brain/paired.py A.json B.json [C.json ...]   # every pair, primary = weights-mode forward C2+C4
"""
import itertools
import json
import sys
from math import comb


def rows(d, mode, kind, classes=None):
    rs = d["scores"][mode]["rows"][kind]
    return [r for r in rs if classes is None or r.get("cls") in classes]


def mcnemar(b, c):  # exact two-sided binomial test on the discordant pairs
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def compare(da, db, mode="weights", kind="forward", classes=("C2", "C4")):
    ra, rb = rows(da, mode, kind, classes), rows(db, mode, kind, classes)
    assert len(ra) == len(rb) and all(x["q"] == y["q"] for x, y in zip(ra, rb)), "arms were not scored on the same questions"
    a_only = sum(x["ok"] and not y["ok"] for x, y in zip(ra, rb))
    b_only = sum(y["ok"] and not x["ok"] for x, y in zip(ra, rb))
    n = len(ra)
    acc_a, acc_b = 100 * sum(x["ok"] for x in ra) / n, 100 * sum(y["ok"] for y in rb) / n
    return {"n": n, "a": round(acc_a, 1), "b": round(acc_b, 1), "b_minus_a": round(acc_b - acc_a, 1), "a_only": a_only, "b_only": b_only,
            "disagree": round(100 * (a_only + b_only) / n, 1), "p": round(mcnemar(a_only, b_only), 4)}


def summary(d):
    w, dg = d["scores"]["weights"], d["scores"].get("diary") or {}
    return {"recall_C24": round(100 * w["forward"]["C24"], 1), "two_hop": round(100 * w["twohop"]["acc"], 1), "changed_new": round(100 * w["changed"]["new"], 1),
            "routine": round(100 * w["routine"]["acc"], 1), "diary_pooled": round(100 * dg.get("pooled", 0), 1),
            "arc": round(100 * (d.get("arc_easy") or {}).get("acc", 0), 1), "reverts": "".join("1" if n.get("reverted") else "0" for n in d.get("nights", []))}


if __name__ == "__main__":
    arms = {p.rsplit("result_", 1)[-1].removesuffix(".json"): json.load(open(p)) for p in sys.argv[1:]}
    for name, d in arms.items():
        print(name, summary(d))
    for (na, da), (nb, db) in itertools.combinations(arms.items(), 2):
        print(f"{nb} vs {na}", compare(da, db))


# ---------------------------------------------------------------- generic helpers added for sleep2 (any per-item 0/1 vectors)
import random as _random


def mcnemar_items(a, b):
    """a, b: equal-length 0/1 sequences (same items, same order). Returns dict with b_minus_a (points), discordant counts and exact two-sided p."""
    assert len(a) == len(b) and len(a) > 0, "arms were not scored on the same items"
    a_only = sum(1 for x, y in zip(a, b) if x and not y)
    b_only = sum(1 for x, y in zip(a, b) if y and not x)
    n = len(a)
    return {"n": n, "a": round(100 * sum(a) / n, 1), "b": round(100 * sum(b) / n, 1), "b_minus_a": round(100 * (sum(b) - sum(a)) / n, 1),
            "a_only": a_only, "b_only": b_only, "p": round(mcnemar(a_only, b_only), 4)}


def pooled_and_per_seed(by_seed_a, by_seed_b):
    """by_seed_*: {seed: [0/1,...]} over the same items per seed. Pooled = concatenation (2 seeds x 80 = 160 paired items).
    sign_ok_all_seeds is True when b-a > 0 in every seed."""
    seeds = sorted(by_seed_a)
    pooled = mcnemar_items([x for s in seeds for x in by_seed_a[s]], [x for s in seeds for x in by_seed_b[s]])
    per = {s: mcnemar_items(by_seed_a[s], by_seed_b[s]) for s in seeds}
    pooled["per_seed"] = per
    pooled["sign_ok_all_seeds"] = all(per[s]["b_minus_a"] > 0 for s in seeds)
    return pooled


def cluster_bootstrap_ci(a, b, clusters, n_boot=2000, seed=0, alpha=0.05):
    """Secondary: slot-clustered bootstrap CI of mean(b)-mean(a) in points. clusters: cluster label per item (e.g. slot id)."""
    rng = _random.Random(seed)
    groups = {}
    for x, y, c in zip(a, b, clusters):
        groups.setdefault(c, []).append(y - x)
    keys = list(groups)
    diffs = []
    for _ in range(n_boot):
        tot = cnt = 0
        for _ in keys:
            g = groups[keys[rng.randrange(len(keys))]]
            tot += sum(g)
            cnt += len(g)
        diffs.append(100 * tot / cnt)
    diffs.sort()
    return {"lo": round(diffs[int(alpha / 2 * n_boot)], 1), "hi": round(diffs[int((1 - alpha / 2) * n_boot) - 1], 1), "n_clusters": len(keys)}
