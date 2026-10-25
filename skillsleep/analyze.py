"""PREREG pass marks from out/summary.jsonl (runs locally on downloaded out/ too).
Usage: python3 analyze.py [path/to/summary.jsonl]
Rate = mean over tasks of the per-task mean pass (tasks present in both arms of a comparison). Test = two-sided paired sign-flip permutation
on the per-task differences, 10,000 random flips, seed 0, p = (1 + #{|flipped mean| >= |observed|}) / (1 + 10000)."""
import json, sys
import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else "out/summary.jsonl"
S = {}
for l in open(path):
    if l.strip():
        r = json.loads(l); S[(r["arm"], r["domain"])] = r  # a later line for the same arm+domain replaces an earlier one
tm = lambda r: {t: float(np.mean(v)) for t, v in r["per_task"].items() if v}


def compare(a, b, dom):
    """A minus B (points) and p over tasks present in both; None if an arm is missing."""
    if (a, dom) not in S or (b, dom) not in S:
        return None
    x, y = tm(S[(a, dom)]), tm(S[(b, dom)]); ts = sorted(set(x) & set(y))
    if not ts:
        return None
    d = np.array([x[t] - y[t] for t in ts]); rng = np.random.default_rng(0)
    flips = rng.choice([-1.0, 1.0], size=(10000, len(d))); obs = abs(d.mean())
    p = (1 + int((np.abs((flips * d).mean(1)) >= obs - 1e-12).sum())) / 10001
    return {"delta": 100 * d.mean(), "p": p, "n": len(ts), "a": 100 * np.mean([x[t] for t in ts]), "b": 100 * np.mean([y[t] for t in ts])}


def rate(arm, dom):
    r = S.get((arm, dom))
    return None if r is None else (100 * np.mean(list(tm(r).values())), sum(map(sum, r["per_task"].values())), sum(map(len, r["per_task"].values())))


f = lambda v, s="{:.1f}": "n/a" if v is None else s.format(v)
print("| arm | retail test | airline test | ARC-Easy |\n|---|---|---|---|")
for arm in ("A0", "A1", "A2"):
    cells = []
    for dom in ("retail_test", "airline_test", "arc_easy"):
        r = rate(arm, dom); cells.append("n/a" if r is None else f"{r[0]:.1f}% ({r[1]}/{r[2]})")
    print(f"| {arm} | " + " | ".join(cells) + " |")
for k in [k for k in S if k[0] in ("day", "fix")]:
    print(f"\n{k[0]} {k[1]}: {S[k]['pass']}/{S[k]['sims']} runs pass")

C = {n: compare(a, b, d) for n, (a, b, d) in {"r20": ("A2", "A0", "retail_test"), "r21": ("A2", "A1", "retail_test"), "r10": ("A1", "A0", "retail_test"),
                                              "a20": ("A2", "A0", "airline_test"), "c20": ("A2", "A0", "arc_easy")}.items()}
print("\n| comparison | delta (points) | p | tasks |\n|---|---|---|---|")
for n, lab in [("r20", "retail A2 - A0"), ("r21", "retail A2 - A1"), ("r10", "retail A1 - A0"), ("a20", "airline A2 - A0"), ("c20", "ARC-Easy A2 - A0")]:
    c = C[n]; print(f"| {lab} | " + ("n/a | n/a | n/a" if c is None else f"{c['delta']:+.1f} | {c['p']:.4f} | {c['n']}") + " |")


def verdict(name, ok_, txt):
    print(f"{name}: {'n/a (missing data)' if ok_ is None else ('PASS' if ok_ else 'FAIL')} - {txt}")


c = C["r20"]; verdict("P1 sleep teaches skill", None if c is None else (c["delta"] >= 6 and c["p"] < 0.05), "A2 retail test >= A0 + 6 points and p < 0.05")
c = C["r21"]
if c is None:
    verdict("P2 bad examples add something", None, "A2 >= A1 + 4 points and p < 0.05")
else:
    verdict("P2 bad examples add something", c["delta"] >= 4 and c["p"] < 0.05, "A2 >= A1 + 4 points and p < 0.05")
    if c["delta"] >= 4 and c["p"] >= 0.05:
        print("   (gap >= 4 with p >= 0.05: suggested, not shown)")
c = C["a20"]; verdict("P3 skills carry over (label only)", None if c is None else c["delta"] >= 0, "A2 airline test >= A0")
a, k = C["a20"], C["c20"]
verdict("P4 no harm", None if a is None or k is None else (a["delta"] >= -7.5 - 1e-9 and k["delta"] >= -2 - 1e-9), "A2 airline >= A0 - 7.5 points and ARC-Easy >= A0 - 2 points")
if C["r20"] is not None and C["r21"] is not None:
    print("Wrong if A2 <= A0 on retail test:", "YES (sleep on skills does nothing)" if C["r20"]["delta"] <= 0 else "no")
    print("Wrong if A2 < A1 - 4:", "YES (bad examples hurt)" if C["r21"]["delta"] < -4 else "no")
r = rate("A0", "retail_test")
if r:
    print(f"Day-1 sanity: A0 retail test {r[0]:.1f}% vs Swap-1 64% -> gap {r[0] - 64:+.1f} points" + ("  > 15: stack changed, report with caveat" if abs(r[0] - 64) > 15 else "  (within 15)"))
