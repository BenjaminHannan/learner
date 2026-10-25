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
