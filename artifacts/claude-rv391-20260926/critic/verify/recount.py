import json
from collections import defaultdict
RUN = "/home/user/learner/artifacts/claude-rv391-20260926/critic/run"
NETS = ["s1", "s2", "s3", "s4", "r0"]
SETS = ["p-grids7", "p-grids6"]

def auc_rank(pos, neg):
    # Mann-Whitney via mid-ranks (independent of the script's bisect method)
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    ranks = {}
    i = 0; n = len(allv)
    rsum = 0.0
    while i < n:
        j = i
        while j < n and allv[j][0] == allv[i][0]:
            j += 1
        mid = (i + 1 + j) / 2.0
        for t in range(i, j):
            if allv[t][1] == 1:
                rsum += mid
        i = j
    P, N = len(pos), len(neg)
    return (rsum - P * (P + 1) / 2) / (P * N)

def auc_brute(pos, neg):
    tot = 0.0
    for x in pos:
        for y in neg:
            tot += 1.0 if x > y else (0.5 if x == y else 0.0)
    return tot / (len(pos) * len(neg))

res = {}
for net in NETS:
    js = json.load(open(f"{RUN}/critic-{net}.json"))
    log = {}
    for line in open(f"{RUN}/log-{net}.txt"):
        name, rest = line.split(" ", 1)
        log[name] = json.loads(rest)
    cut = js["train"]["cut"]
    rows = [json.loads(l) for l in open(f"{RUN}/critic-{net}.rows.jsonl")]
    by = defaultdict(list)
    for r in rows:
        by[r["set"]].append(r)
    other = set(by) - set(SETS)
    if other: print(net, "UNEXPECTED SETS", other)
    for s in SETS:
        rr = by[s]
        dead = [r for r in rr if r["dead"] == 1]
        live = [r for r in rr if r["dead"] == 0]
        assert all(r["dead"] in (0, 1) for r in rr)
        ps, ns = [r["score"] for r in dead], [r["score"] for r in live]
        pk, nk = [r["k"] for r in dead], [r["k"] for r in live]
        a = auc_rank(ps, ns); ak = auc_rank(pk, nk)
        a2 = auc_brute(ps, ns) if len(ps)*len(ns) < 3e6 else None
        ak2 = auc_brute(pk, nk) if len(pk)*len(nk) < 3e6 else None
        df = sum(x > cut for x in ps); lf = sum(x > cut for x in ns)
        # near-cut rows (rounding to 5 dp could flip)
        near = sum(abs(x - cut) < 1e-5 for x in ps + ns)
        items = len(set(r["item"] for r in rr))
        ties_score = len(ps + ns) - len(set(ps + ns))
        rec = dict(states=len(rr), dead=len(dead), live=len(live), items=items, auc=a, auc_k=ak,
                   auc_brute=a2, auck_brute=ak2, dead_flag=df, live_flag=lf, near_cut=near, ties_score=ties_score,
                   kmin=min(r["k"] for r in rr), kmax=max(r["k"] for r in rr))
        res[(net, s)] = rec
        J = js["sets"][s]; L = log[s]
        diffs = []
        for key, mine in [("states", len(rr)), ("dead", len(dead)), ("auc", a), ("auc_count_only", ak),
                          ("dead_flagged", df), ("live_flagged", lf), ("unfinished", items)]:
            for src, D in [("json", J), ("log", L)]:
                v = D.get(key)
                if v is None or abs(v - mine) > (0.001 if "auc" in key else 0):
                    diffs.append(f"{src}.{key}={v} vs mine={mine}")
        # json vs log identical?
        if J != L: diffs.append(f"json!=log: {J} vs {L}")
        print(f"{net} {s}: states={len(rr)} dead={len(dead)} live={len(live)} items={items} "
              f"auc={a:.4f} (brute {a2 if a2 is None else round(a2,4)}) aucK={ak:.4f} (brute {ak2 if ak2 is None else round(ak2,4)}) "
              f"df={df}/{len(dead)} lf={lf}/{len(live)} near_cut={near} score_dups={ties_score} k={rec['kmin']}..{rec['kmax']}")
        print("   json:", J)
        print("   max|auc diff| json:", round(abs(J['auc']-a),5), " count-only:", round(abs(J['auc_count_only']-ak),5))
        print("   DIFFS:", diffs if diffs else "none")

print()
print("=== Marks (p-grids7, trained nets s1-s4) ===")
tr = ["s1", "s2", "s3", "s4"]
c = [res[(n, "p-grids7")]["auc"] for n in tr]
k = [res[(n, "p-grids7")]["auc_k"] for n in tr]
mc = sum(c) / 4; mk = sum(k) / 4
print("critic AUC per net:", [round(x, 4) for x in c], "mean", round(mc, 4))
print("count-only AUC per net:", [round(x, 4) for x in k], "mean", round(mk, 4))
print("mean critic - mean count:", round(mc - mk, 4))
print("GOOD: mean>=0.65:", mc >= 0.65, "; all>0.5:", all(x > 0.5 for x in c), "; mean-countmean>=0.05:", mc - mk >= 0.05)
print("WRONG: mean<=0.55:", mc <= 0.55, "; mean no better than count (mc<=mk):", mc <= mk)
# alt reading: mean of per-net differences = same as difference of means
print("mean of per-net (critic-count):", round(sum(a - b for a, b in zip(c, k)) / 4, 4))
# JSON-based cross-check of marks
jc = [json.load(open(f"{RUN}/critic-{n}.json"))["sets"]["p-grids7"]["auc"] for n in tr]
jk = [json.load(open(f"{RUN}/critic-{n}.json"))["sets"]["p-grids7"]["auc_count_only"] for n in tr]
print("JSON-based: mean critic", round(sum(jc)/4, 4), "mean count", round(sum(jk)/4, 4), "diff", round(sum(jc)/4 - sum(jk)/4, 4))

print()
print("=== p-grids6 check ===")
hold = 0
for n in tr:
    r = res[(n, "p-grids6")]
    ds = r["dead_flag"] / r["dead"]; ls = r["live_flag"] / r["live"]
    ok = ds > ls; hold += ok
    print(f"{n}: dead {r['dead_flag']}/{r['dead']} = {ds:.3f}; live {r['live_flag']}/{r['live']} = {ls:.3f}; dead share larger: {ok}")
print("nets where dead share > live share:", hold, "of 4 -> holds" if hold >= 3 else "-> NOT holding")
r = res[("r0", "p-grids6")]
print(f"r0 (report only): dead {r['dead_flag']}/{r['dead']} = {r['dead_flag']/r['dead']:.3f}; live {r['live_flag']}/{r['live']} = {r['live_flag']/r['live']:.3f}")
print("p-grids7 flag shares:")
for n in NETS:
    r = res[(n, "p-grids7")]
    print(f"  {n}: dead {r['dead_flag']}/{r['dead']} = {r['dead_flag']/r['dead']:.3f}; live {r['live_flag']}/{r['live']} = {r['live_flag']/r['live']:.3f}")

print()
print("=== Addendum row: trained mean AUC - r0 AUC ===")
for s in SETS:
    m = sum(res[(n, s)]["auc"] for n in tr) / 4
    mkk = sum(res[(n, s)]["auc_k"] for n in tr) / 4
    r0 = res[("r0", s)]["auc"]
    print(f"{s}: trained mean critic {m:.4f}, r0 {r0:.4f}, diff {m - r0:+.4f} | (count-only: trained mean {mkk:.4f}, r0 {res[('r0', s)]['auc_k']:.4f})")
    print("   |diff| within 0.10 (P391c.2):", abs(m - r0) <= 0.10)
