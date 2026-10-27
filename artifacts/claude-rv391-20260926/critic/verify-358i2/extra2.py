import json, random, bisect
from pathlib import Path
D = Path("/home/user/learner/artifacts/claude-rv391-20260926/critic/run-358i2")
NETS = ["s1","s2","s3","s4"]
rows = {n: [json.loads(l) for l in (D/f"critic-{n}.rows.jsonl").read_text().splitlines()] for n in NETS}
js = {n: json.loads((D/f"critic-{n}.json").read_text()) for n in NETS}
def auc(pos, neg):
    if not pos or not neg: return None
    ns = sorted(neg); t = 0.0
    for x in pos:
        lo, hi = bisect.bisect_left(ns, x), bisect.bisect_right(ns, x); t += lo + 0.5*(hi-lo)
    return t/(len(pos)*len(ns))
# unrounded values
A = {n: auc(*[[r["score"] for r in rows[n] if r["set"]=="p-grids7" and r["dead"]==d] for d in (1,0)]) for n in NETS}
K = {n: auc(*[[r["k"] for r in rows[n] if r["set"]=="p-grids7" and r["dead"]==d] for d in (1,0)]) for n in NETS}
mA = sum(A.values())/4; mK = sum(K.values())/4
print("mean critic %.6f mean count %.6f margin %.6f" % (mA, mK, mA-mK))
# variant: resample ALL unfinished ids 0..U-1 (puzzles without states contribute none)
random.seed(0)
by = {}
for n in NETS:
    U = js[n]["sets"]["p-grids7"]["unfinished"]; g = {i: [] for i in range(U)}
    for r in rows[n]:
        if r["set"]=="p-grids7": g[r["item"]].append(r)
    by[n] = [g[i] for i in range(U)]
ms = []
for _ in range(1000):
    ca, ck = [], []
    for n in NETS:
        pz = by[n]; R = [r for _ in pz for r in pz[random.randrange(len(pz))]]
        ca.append(auc([r["score"] for r in R if r["dead"]], [r["score"] for r in R if not r["dead"]]))
        ck.append(auc([r["k"] for r in R if r["dead"]], [r["k"] for r in R if not r["dead"]]))
    ms.append(sum(ca)/4 - sum(ck)/4)
ms.sort()
print("variant (all unfinished ids): 2.5%% %.4f 97.5%% %.4f share>0 %.3f share>0.05 %.3f" % (ms[25], ms[974], sum(x>0 for x in ms)/1000, sum(x>0.05 for x in ms)/1000))
# seed sensitivity of the main bootstrap (states-bearing puzzles), seeds 1..5
for seed in range(1, 6):
    random.seed(seed)
    g2 = {}
    for n in NETS:
        g = {}
        for r in rows[n]:
            if r["set"]=="p-grids7": g.setdefault(r["item"], []).append(r)
        g2[n] = [g[i] for i in sorted(g)]
    mm = []
    for _ in range(1000):
        ca, ck = [], []
        for n in NETS:
            pz = g2[n]; R = [r for _ in pz for r in pz[random.randrange(len(pz))]]
            ca.append(auc([r["score"] for r in R if r["dead"]], [r["score"] for r in R if not r["dead"]]))
            ck.append(auc([r["k"] for r in R if r["dead"]], [r["k"] for r in R if not r["dead"]]))
        mm.append(sum(ca)/4 - sum(ck)/4)
    mm.sort()
    print("seed %d: 2.5%% %.4f 97.5%% %.4f share>0 %.3f share>0.05 %.3f" % (seed, mm[25], mm[974], sum(x>0 for x in mm)/1000, sum(x>0.05 for x in mm)/1000))
# within-k critic AUC (report-only in addendum 2): dead/live pairs with equal k, pooled over k strata
print("within-k critic AUC, p-grids7 (pairs with the same k):")
for n in NETS:
    R = [r for r in rows[n] if r["set"]=="p-grids7"]; num = den = 0.0
    for k in sorted(set(r["k"] for r in R)):
        pos = [r["score"] for r in R if r["k"]==k and r["dead"]]; neg = [r["score"] for r in R if r["k"]==k and not r["dead"]]
        if pos and neg: a = auc(pos, neg); num += a*len(pos)*len(neg); den += len(pos)*len(neg)
    print(" ", n, round(num/den, 4), "pairs", int(den))
# p-grids6 per-puzzle breakdown
print("p-grids6 per puzzle (item: states dead):")
for n in NETS:
    R = [r for r in rows[n] if r["set"]=="p-grids6"]; g = {}
    for r in R: g.setdefault(r["item"], [0,0]); g[r["item"]][0]+=1; g[r["item"]][1]+=r["dead"]
    print(" ", n, {i: tuple(v) for i, v in sorted(g.items())})
# k ranges
for n in NETS:
    for s in ["p-grids7","p-grids6"]:
        ks = [r["k"] for r in rows[n] if r["set"]==s]; print(n, s, "k range", min(ks), max(ks))
