import json, random, bisect, re
from pathlib import Path
D = Path("/home/user/learner/artifacts/claude-rv391-20260926/critic/run-358i2")
NETS = ["s1", "s2", "s3", "s4"]
SETS = ["p-grids7", "p-grids6"]

def auc(pos, neg):
    """Independent pairwise AUC: P(pos > neg), ties half (brute force, no bisect)."""
    if not pos or not neg:
        return None
    t = 0.0
    for x in pos:
        for y in neg:
            t += 1.0 if x > y else (0.5 if x == y else 0.0)
    return t / (len(pos) * len(neg))

def auc_fast(pos, neg):
    ns = sorted(neg); t = 0.0
    for x in pos:
        lo, hi = bisect.bisect_left(ns, x), bisect.bisect_right(ns, x)
        t += lo + 0.5 * (hi - lo)
    return t / (len(pos) * len(ns))

rows, js, logs = {}, {}, {}
for n in NETS:
    rows[n] = [json.loads(l) for l in (D / f"critic-{n}.rows.jsonl").read_text().splitlines() if l.strip()]
    js[n] = json.loads((D / f"critic-{n}.json").read_text())
    logs[n] = {}
    for l in (D / f"log-{n}.txt").read_text().splitlines():
        m = re.match(r"(\S+) (\{.*\})", l)
        if m: logs[n][m.group(1)] = json.loads(m.group(2))

# sanity on row schema
for n in NETS:
    keys = set(tuple(sorted(r)) for r in rows[n]); print(n, "row keys", keys, "sets", sorted(set(r["set"] for r in rows[n])))
    assert all(r["dead"] in (0, 1) for r in rows[n])

print("\n== Step 1: recount vs JSON and log (flag |diff| > 0.001)")
rec = {}
for n in NETS:
    for s in SETS:
        R = [r for r in rows[n] if r["set"] == s]
        pos = [r["score"] for r in R if r["dead"]]; neg = [r["score"] for r in R if not r["dead"]]
        kp = [r["k"] for r in R if r["dead"]]; kn = [r["k"] for r in R if not r["dead"]]
        a, ak = auc(pos, neg), auc(kp, kn)
        assert abs(a - auc_fast(pos, neg)) < 1e-12 and abs(ak - auc_fast(kp, kn)) < 1e-12
        items = sorted(set(r["item"] for r in R))
        rec[(n, s)] = dict(states=len(R), dead=len(pos), live=len(neg), auc=a, auc_k=ak, items=len(items),
                           max_item=max(items) if items else None)
        J = js[n]["sets"][s]; L = logs[n][s]
        diffs = []
        for key, mine in [("states", len(R)), ("dead", len(pos)), ("auc", a), ("auc_count_only", ak)]:
            for src, v in [("json", J[key]), ("log", L[key])]:
                if abs(v - mine) > 0.001: diffs.append(f"{key} {src}={v} mine={mine}")
        if J != L: diffs.append("json != log")
        print(f"{n} {s}: states {len(R)} dead {len(pos)} live {len(neg)} puzzles-with-states {len(items)} (max id {rec[(n,s)]['max_item']}, unfinished {J['unfinished']}) "
              f"auc {a:.4f} (json {J['auc']}) count-only {ak:.4f} (json {J['auc_count_only']})  {'DIFFS: ' + '; '.join(diffs) if diffs else 'ok'}")

print("\n== Step 2: marks on p-grids7, four trained nets")
A = [rec[(n, "p-grids7")]["auc"] for n in NETS]; K = [rec[(n, "p-grids7")]["auc_k"] for n in NETS]
mA, mK = sum(A) / 4, sum(K) / 4
print("critic AUCs", [round(x, 4) for x in A], "mean", round(mA, 4))
print("count AUCs ", [round(x, 4) for x in K], "mean", round(mK, 4))
print("margin", round(mA - mK, 4))
good = mA >= 0.65 and all(x > 0.5 for x in A) and (mA - mK) >= 0.05
wrong = mA <= 0.55 or mA <= mK
print("GOOD:", mA >= 0.65, all(x > 0.5 for x in A), (mA - mK) >= 0.05, "->", good)
print("WRONG:", mA <= 0.55, mA <= mK, "->", wrong)

print("\n== Step 3a per-net-mean margin", round(mA - mK, 4))
# 3b bootstrap
random.seed(0)
by = {}
for n in NETS:
    R = [r for r in rows[n] if r["set"] == "p-grids7"]
    g = {}
    for r in R: g.setdefault(r["item"], []).append(r)
    by[n] = [g[i] for i in sorted(g)]
margins = []
none_count = 0
for b in range(1000):
    ca, ck = [], []
    for n in NETS:
        puz = by[n]
        pick = [puz[random.randrange(len(puz))] for _ in range(len(puz))]
        R = [r for p in pick for r in p]
        pos = [r["score"] for r in R if r["dead"]]; neg = [r["score"] for r in R if not r["dead"]]
        kp = [r["k"] for r in R if r["dead"]]; kn = [r["k"] for r in R if not r["dead"]]
        ca.append(auc_fast(pos, neg)); ck.append(auc_fast(kp, kn))
    if None in ca or None in ck: none_count += 1; continue
    margins.append(sum(ca) / 4 - sum(ck) / 4)
ms = sorted(margins); m = len(ms)
def pct(p):  # simple percentile by index
    return ms[int(p * (m - 1))]
import statistics
print("resamples used", m, "skipped", none_count)
print("2.5% / 97.5% (index int(p*(n-1)))", round(pct(0.025), 4), round(pct(0.975), 4))
# also linear-interp percentiles
def q(p):
    x = p * (m - 1); lo = int(x); hi = min(lo + 1, m - 1); return ms[lo] + (x - lo) * (ms[hi] - ms[lo])
print("2.5% / 97.5% (linear interp)", round(q(0.025), 4), round(q(0.975), 4))
print("2.5% / 97.5% (sorted[25], sorted[974])", round(ms[25], 4), round(ms[974], 4))
print("median", round(statistics.median(ms), 4), "mean", round(sum(ms)/m, 4))
print("share > 0", sum(x > 0 for x in ms) / m, " share > +0.05", sum(x > 0.05 for x in ms) / m, " share >= 0.05", sum(x >= 0.05 for x in ms) / m)
print("bootstrap puzzles per net", {n: len(by[n]) for n in NETS})

print("\n== Step 3c pooled count-only")
P = [r for n in NETS for r in rows[n] if r["set"] == "p-grids7"]
kp = [r["k"] for r in P if r["dead"]]; kn = [r["k"] for r in P if not r["dead"]]
pk = auc(kp, kn)
print("pooled states", len(P), "dead", len(kp), "pooled count-only AUC", round(pk, 4), "critic mean minus it", round(mA - pk, 4))
# for context: pooled critic AUC (scores are on different nets' scales; report only)
pa = auc([r["score"] for r in P if r["dead"]], [r["score"] for r in P if not r["dead"]])
print("(context only) pooled critic AUC across nets", round(pa, 4))

print("\n== Step 4 p-grids6 check with each JSON's train cut")
holds = 0
for n in NETS:
    cut = js[n]["train"]["cut"]
    R = [r for r in rows[n] if r["set"] == "p-grids6"]
    d = [r for r in R if r["dead"]]; l = [r for r in R if not r["dead"]]
    df = sum(r["score"] > cut for r in d); lf = sum(r["score"] > cut for r in l)
    near = [r["score"] for r in R if abs(r["score"] - cut) < 1e-4]
    sd, sl = df / len(d) if d else None, lf / len(l) if l else None
    ok = sd is not None and sl is not None and sd > sl
    holds += ok
    J = js[n]["sets"]["p-grids6"]
    print(f"{n}: cut {cut:.5f}  dead flagged {df}/{len(d)} ({sd:.3f})  live flagged {lf}/{len(l)} ({sl:.3f})  larger dead share: {ok}  "
          f"json dead_flagged {J['dead_flagged']} live_flagged {J['live_flagged']}  near-cut rows {near}  puzzles {len(set(r['item'] for r in R))}")
print("nets where it holds:", holds, "of 4 ->", "holds" if holds >= 3 else "NOT holding up")
print("\n== p-grids7 flag shares (report only, with JSON cut)")
for n in NETS:
    cut = js[n]["train"]["cut"]
    R = [r for r in rows[n] if r["set"] == "p-grids7"]
    d = [r for r in R if r["dead"]]; l = [r for r in R if not r["dead"]]
    df = sum(r["score"] > cut for r in d); lf = sum(r["score"] > cut for r in l)
    J = js[n]["sets"]["p-grids7"]
    print(f"{n}: dead {df}/{len(d)} live {lf}/{len(l)}  json {J['dead_flagged']}/{J['live_flagged']}")
