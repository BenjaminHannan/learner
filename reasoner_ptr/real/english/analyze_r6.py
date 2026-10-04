"""Round-6 analysis (PASS-MARKS-R6.md): twelve vs six practised kinds on unseen kinds."""
import glob, json, statistics as st
R = {}
for f in glob.glob("results6/box*/out/*.json"):
    if f.endswith("-rows.json"): continue
    d = json.load(open(f)); R[(d["arm"] + d.get("tag", ""), d.get("seed", 0))] = d
def ci(d):
    mu = st.mean(d); h = 2.571 * st.stdev(d) / len(d) ** .5
    return {"n": len(d), "mean": round(mu, 1), "ci": [round(mu - h, 1), round(mu + h, 1)], "per_seed": [round(x, 1) for x in d]}
lm = R[("lm_fewshot", 0)]
bar1, bar2 = 100 * lm["extra"]["all"][0], 100 * lm["extra2"]["all"][0]
seeds = sorted(s for (a, s) in R if a == "allptr-six" and ("allptr-twelve", s) in R)
six = {s: R[("allptr-six", s)] for s in seeds}; tw = {s: R[("allptr-twelve", s)] for s in seeds}
def v(d, panel, k="all"): return 100 * d[panel][k][0]
def fams(d, panel): return {k[4:]: round(100 * x[0], 1) for k, x in d[panel].items() if k.startswith("fam:")}
def mfams(D, panel):
    ks = fams(next(iter(D.values())), panel); return {k: round(st.mean(fams(D[s], panel)[k] for s in seeds), 1) for k in ks}
out = {"seeds": seeds, "bar_new_kinds_R5": round(bar1, 1), "bar_new_kinds2_R6": round(bar2, 1),
       "lm_fewshot": {"new_kinds": round(bar1, 1), "new_kinds2": round(bar2, 1), "fresh": round(v(lm, "eval"), 1),
                      "new_kinds_families": fams(lm, "extra"), "new_kinds2_families": fams(lm, "extra2"),
                      "new_kinds_contains": round(v(lm, "extra", "all_contains"), 1), "new_kinds2_contains": round(v(lm, "extra2", "all_contains"), 1)}}
for name, D in (("six", six), ("twelve", tw)):
    out[name] = {p: round(st.mean(v(D[s], p) for s in seeds), 1) for p in ("extra", "extra2", "eval")}
    out[name] |= {p + "_contains": round(st.mean(v(D[s], p, "all_contains") for s in seeds), 1) for p in ("extra", "extra2")}
    out[name]["new_kinds_families"] = mfams(D, "extra"); out[name]["new_kinds2_families"] = mfams(D, "extra2")
    out[name]["lesion_zero_pool_fresh"] = round(st.mean(100 * D[s]["lesion_zero_pool"]["all"][0] for s in seeds), 1)
jA = ci([v(tw[s], "extra") - v(six[s], "extra") for s in seeds])
jB = ci([v(tw[s], "extra") - bar1 for s in seeds])
out["judgedA_twelve_minus_six_R5"] = jA | {"verdict": "PASS" if jA["mean"] >= 5 and jA["ci"][0] > 0 else "FALSIFIED" if jA["mean"] < 1 else "IN BETWEEN"}
out["judgedB_twelve_R5_goal"] = jB | {"twelve_mean": out["twelve"]["extra"], "verdict": "REACHED" if out["twelve"]["extra"] >= 80 and jB["ci"][0] > 0 else "NOT REACHED"}
out["read_twelve_minus_six_R6set"] = ci([v(tw[s], "extra2") - v(six[s], "extra2") for s in seeds])
out["read_twelve_minus_bar_R6set"] = ci([v(tw[s], "extra2") - bar2 for s in seeds])
out["read_six_minus_bar_R6set"] = ci([v(six[s], "extra2") - bar2 for s in seeds])
out["read_twelve_minus_six_fresh"] = ci([v(tw[s], "eval") - v(six[s], "eval") for s in seeds])
print(json.dumps(out, indent=1))
