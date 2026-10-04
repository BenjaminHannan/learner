"""Round-7 analysis (PASS-MARKS-R7.md): question-first reuse (qfirst) and thin talker (ptr) against allptr."""
import glob, json, statistics as st
R = {}
for f in glob.glob("results7/box*/out/*.json"):
    if f.endswith("-rows.json"): continue
    d = json.load(open(f)); R[(d["arm"], d.get("seed", 0))] = d
def ci(d):
    mu = st.mean(d); h = 2.571 * st.stdev(d) / len(d) ** .5
    return {"n": len(d), "mean": round(mu, 1), "ci": [round(mu - h, 1), round(mu + h, 1)], "per_seed": [round(x, 1) for x in d]}
ARMS = ("allptr", "qfirst", "ptr")
seeds = sorted(s for (a, s) in R if a == "allptr" and all((b, s) in R for b in ARMS))
def v(d, panel, k="all"): return 100 * d[panel][k][0]
def pooled(d):  # exact over FRESH + NEW-KINDS-R5 + NEW-KINDS2-R6 (576 questions)
    ok = sum(d[p]["all"][0] * d[p]["all"][1] for p in ("eval", "extra", "extra2")); n = sum(d[p]["all"][1] for p in ("eval", "extra", "extra2"))
    return 100 * ok / n
def fams(d, panel): return {k[4:]: round(100 * x[0], 1) for k, x in d[panel].items() if k.startswith("fam:")}
out = {"seeds": seeds, "bar_lm_fewshot": {"fresh": 75.0, "new_kinds_R5": 67.7, "new_kinds2_R6": 77.6}}
for a in ARMS:
    D = {s: R[(a, s)] for s in seeds}
    m = lambda f: round(st.mean(f(D[s]) for s in seeds), 1)
    out[a] = {"pooled": m(pooled), "fresh": m(lambda d: v(d, "eval")), "new_kinds_R5": m(lambda d: v(d, "extra")),
              "new_kinds2_R6": m(lambda d: v(d, "extra2")), "fresh_contains": m(lambda d: v(d, "eval", "all_contains")),
              "lesion_zero_pool_fresh": m(lambda d: v(d, "lesion_zero_pool")), "train_fit": m(lambda d: 100 * d["train_fit"][0])}
    if a == "qfirst":
        out[a]["lesion_zero_core_fresh"] = m(lambda d: v(d, "lesion_zero_core"))
    T = [D[s]["timing"] for s in seeds if "timing" in D[s]]
    if T:
        med = lambda xs: round(st.median(xs), 3)
        out[a]["timing"] = {"first_ratio_median": med([t["first_ratio"] for t in T]), "total_ratio_median": med([t["total_ratio"] for t in T]),
                            "per_box_first_ratio": [t["first_ratio"] for t in T], "bare_first_ms": [t["bare"]["first_ms"] for t in T],
                            "arm_first_ms": [t["arm"]["first_ms"] for t in T], "bare_total_ms": [t["bare"]["total_ms"] for t in T],
                            "arm_total_ms": [t["arm"]["total_ms"] for t in T]}
    for p, k in (("extra", "new_kinds_R5_families"), ("extra2", "new_kinds2_R6_families")):
        ks = fams(D[seeds[0]], p); out[a][k] = {f: round(st.mean(fams(D[s], p)[f] for s in seeds), 1) for f in ks}
jA = ci([pooled(R[("qfirst", s)]) - pooled(R[("allptr", s)]) for s in seeds])
out["judgedA_qfirst_minus_allptr_pooled"] = jA | {"verdict": "PASS" if jA["ci"][0] > -5 else "FALSIFIED" if jA["mean"] < -5 else "IN BETWEEN"}
r = out["qfirst"]["timing"]["first_ratio_median"]
out["judgedS_qfirst_first_token_ratio"] = {"ratio": r, "allptr_ratio": out["allptr"]["timing"]["first_ratio_median"],
                                           "verdict": "PASS" if r <= 1.5 else "FALSIFIED" if r >= 2.5 else "IN BETWEEN"}
jB = ci([pooled(R[("ptr", s)]) - pooled(R[("allptr", s)]) for s in seeds])
out["judgedB_ptr_minus_allptr_pooled"] = jB | {"verdict": "PASS" if jB["ci"][0] > -5 else "FALSIFIED" if jB["mean"] < -10 else "IN BETWEEN"}
for a in ("qfirst", "ptr"):
    for p, nm in (("eval", "fresh"), ("extra", "new_kinds_R5"), ("extra2", "new_kinds2_R6")):
        out[f"read_{a}_minus_allptr_{nm}"] = ci([v(R[(a, s)], p) - v(R[("allptr", s)], p) for s in seeds])
print(json.dumps(out, indent=1))
