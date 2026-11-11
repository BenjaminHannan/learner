"""Round-3 analysis: allptr vs pool on the fresh English set (PASS-MARKS-R3.md). Prints JSON."""
import glob, json, statistics as st
R = {}
for f in glob.glob("results/box*/out/*.json"):
    if f.endswith("-rows.json"): continue
    d = json.load(open(f)); R[(d["arm"], d.get("seed", 0))] = d
def mean(arm, path):
    v = [R[k] for k in R if k[0] == arm]
    def get(d):
        for p in path: d = d[p]
        return d[0] if isinstance(d, list) else d
    return round(100 * st.mean(get(d) for d in v), 1) if v else None
keys = ["all", "all_contains", "fresh_source", "fresh_paraphrase", "new_word_answers", "short_answer", "yes_no"]
out = {"runs": sorted(f"{a}{s}" for a, s in R)}
for arm in ("pool", "allptr"):
    out[arm] = {k: mean(arm, ["eval", k]) for k in keys}
    out[arm]["train_fit"] = mean(arm, ["train_fit"])
    fams = sorted(k for k in next(R[k] for k in R if k[0] == arm)["eval"] if k.startswith("fam:"))
    out[arm]["families"] = {f[4:]: mean(arm, ["eval", f]) for f in fams}
    w = [R[k]["eval"]["wrong_is_train_answer"] for k in R if k[0] == arm]
    out[arm]["wrong_is_train_answer"] = [sum(x[0] for x in w), sum(x[1] for x in w)]
out["allptr"]["lesion_zero_pool"] = {k: mean("allptr", ["lesion_zero_pool", k]) for k in ("all", "all_contains")}
if ("lm_alone", 0) in R:
    out["lm_alone"] = {k: round(100 * R[("lm_alone", 0)]["eval"][k][0], 1) for k in keys}
    out["lm_alone"]["train_fit"] = round(100 * R[("lm_alone", 0)]["train_fit"][0], 1)
seeds = sorted(s for a, s in R if a == "pool" and ("allptr", s) in R)
def paired(key):
    d = [100 * (R[("allptr", s)]["eval"][key][0] - R[("pool", s)]["eval"][key][0]) for s in seeds]
    m = st.mean(d); h = 2.571 * st.stdev(d) / len(d) ** .5 if len(d) > 1 else float("nan")
    return {"n": len(d), "mean": round(m, 1), "ci": [round(m - h, 1), round(m + h, 1)], "per_seed": [round(x, 1) for x in d]}
out["allptr_vs_pool_all"] = j = paired("all")
out["allptr_vs_pool_new_word"] = paired("new_word_answers")
out["verdict"] = ("PASS" if j["mean"] >= 25 and j["ci"][0] > 0 else "FALSIFIED" if j["mean"] < 8 else "IN BETWEEN") if j["n"] == 6 else "INCOMPLETE"
print(json.dumps(out, indent=1))
