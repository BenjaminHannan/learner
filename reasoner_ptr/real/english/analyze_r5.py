"""Round-5 analysis (PASS-MARKS-R5.md): new question kinds and leave-two-families-out."""
import glob, json, statistics as st
DROP = {"explicit_negation_with_positive_alternative", "two_simple_relations_combined"}
R, ROWS = {}, {}
for f in glob.glob("results5/box*/out/*.json"):
    if f.endswith("-rows.json"): continue
    d = json.load(open(f)); key = (d["arm"] + d.get("tag", ""), d.get("seed", 0)); R[key] = d
    base = f[:-5]
    ROWS[key] = {"fresh": json.load(open(base + "-rows.json")), "extra": json.load(open(base + "-extra-rows.json"))}
def acc(rows, sel=lambda r: True, k="ok"):
    s = [r[k] for r in rows if sel(r)]; return 100 * sum(s) / len(s)
def ci(d):
    mu = st.mean(d); h = 2.571 * st.stdev(d) / len(d) ** .5
    return {"n": len(d), "mean": round(mu, 1), "ci": [round(mu - h, 1), round(mu + h, 1)], "per_seed": [round(x, 1) for x in d]}
lm = ROWS[("lm_fewshot", 0)]
dropsel = lambda r: r["family"] in DROP
keepsel = lambda r: r["family"] not in DROP
bar_new = acc(lm["extra"]); bar_drop = acc(lm["fresh"], dropsel)
seeds = sorted(s for (a, s) in R if a == "allptr-full" and ("allptr-lofo", s) in R)
full = {s: ROWS[("allptr-full", s)] for s in seeds}; lofo = {s: ROWS[("allptr-lofo", s)] for s in seeds}
fams = sorted({r["family"] for r in lm["extra"]})
out = {"seeds": seeds, "bar_new_kinds_lm_fewshot": round(bar_new, 1), "bar_dropped_fams_lm_fewshot": round(bar_drop, 1),
       "lm_fewshot": {"new_kinds": round(bar_new, 1), "new_kinds_contains": round(acc(lm["extra"], k="contains"), 1),
                      "new_kinds_families": {f: round(acc(lm["extra"], lambda r: r["family"] == f), 1) for f in fams},
                      "fresh_all": round(acc(lm["fresh"]), 1), "fresh_dropped_fams": round(bar_drop, 1), "fresh_kept_fams": round(acc(lm["fresh"], keepsel), 1)}}
for name, D in (("full", full), ("lofo", lofo)):
    out[name] = {"new_kinds": round(st.mean(acc(D[s]["extra"]) for s in seeds), 1),
                 "new_kinds_contains": round(st.mean(acc(D[s]["extra"], k="contains") for s in seeds), 1),
                 "new_kinds_families": {f: round(st.mean(acc(D[s]["extra"], lambda r, f=f: r["family"] == f) for s in seeds), 1) for f in fams},
                 "fresh_all": round(st.mean(acc(D[s]["fresh"]) for s in seeds), 1),
                 "fresh_dropped_fams": round(st.mean(acc(D[s]["fresh"], dropsel) for s in seeds), 1),
                 "fresh_kept_fams": round(st.mean(acc(D[s]["fresh"], keepsel) for s in seeds), 1),
                 "lesion_zero_pool_fresh": round(100 * st.mean(R[("allptr-" + name, s)]["lesion_zero_pool"]["all"][0] for s in seeds), 1)}
jA = ci([acc(full[s]["extra"]) - bar_new for s in seeds])
jB = ci([acc(lofo[s]["fresh"], dropsel) - bar_drop for s in seeds])
out["judgedA_full_new_kinds_minus_bar"] = jA | {"verdict": "PASS" if jA["ci"][0] > 0 else "FALSIFIED" if jA["mean"] < -10 else "IN BETWEEN"}
out["judgedB_lofo_dropped_minus_bar"] = jB | {"verdict": "PASS" if jB["ci"][0] > 0 else "FALSIFIED" if jB["mean"] < -10 else "IN BETWEEN"}
out["read_lofo_minus_full_dropped"] = ci([acc(lofo[s]["fresh"], dropsel) - acc(full[s]["fresh"], dropsel) for s in seeds])
out["read_lofo_minus_full_kept"] = ci([acc(lofo[s]["fresh"], keepsel) - acc(full[s]["fresh"], keepsel) for s in seeds])
out["read_lofo_minus_full_new_kinds"] = ci([acc(lofo[s]["extra"]) - acc(full[s]["extra"]) for s in seeds])
r4 = {json.load(open(f))["seed"]: json.load(open(f)) for f in glob.glob("results4/box*/out/allptr-gen-seed*.json") if not f.endswith("rows.json")}
out["read_full_vs_round4_fresh"] = ci([acc(full[s]["fresh"]) - 100 * r4[s]["eval"]["all"][0] for s in seeds if s in r4])
print(json.dumps(out, indent=1))
