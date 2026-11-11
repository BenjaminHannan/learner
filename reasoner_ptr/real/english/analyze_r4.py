"""Round-4 analysis (PASS-MARKS-R4.md): allptr-gen vs round-3 allptr (paired by seed) and vs the best bare-LM row."""
import glob, json, statistics as st
def load(pat):
    R = {}
    for f in glob.glob(pat):
        if f.endswith("-rows.json"): continue
        d = json.load(open(f)); R[(d["arm"], d.get("seed", 0))] = d
    return R
R3, R4 = load("results/box*/out/*.json"), load("results4/box*/out/*.json")
g = {s: d for (a, s), d in R4.items() if a == "allptr"}
b = {s: d for (a, s), d in R3.items() if a == "allptr"}
lm0 = R3[("lm_alone", 0)]["eval"]; lmf = R4[("lm_fewshot", 0)]["eval"]
bar = max(lm0["all"][0], lmf["all"][0]) * 100
def m(ds, *path):
    v = []
    for d in ds:
        for p in path: d = d[p]
        v.append(d[0] if isinstance(d, list) else d)
    return round(100 * st.mean(v), 1)
def ci(diffs):
    mu = st.mean(diffs); h = 2.571 * st.stdev(diffs) / len(diffs) ** .5
    return {"n": len(diffs), "mean": round(mu, 1), "ci": [round(mu - h, 1), round(mu + h, 1)], "per_seed": [round(x, 1) for x in diffs]}
seeds = sorted(set(g) & set(b))
keys = ["all", "all_contains", "fresh_source", "fresh_paraphrase", "new_word_answers", "short_answer", "yes_no"]
out = {"seeds": seeds,
       "allptr_gen": {k: m(g.values(), "eval", k) for k in keys} | {"train_fit_bank": m(g.values(), "train_fit"),
                      "gen_heldout": m(g.values(), "gen_heldout", "all"), "lesion_zero_pool": m(g.values(), "lesion_zero_pool", "all"),
                      "families": {f[4:]: m(g.values(), "eval", f) for f in sorted(next(iter(g.values()))["eval"]) if f.startswith("fam:")}},
       "allptr_r3": {k: m(b.values(), "eval", k) for k in keys},
       "lm_alone": {k: round(100 * lm0[k][0], 1) for k in keys},
       "lm_fewshot": {k: round(100 * lmf[k][0], 1) for k in keys} | {"families": {f[4:]: round(100 * lmf[f][0], 1) for f in lmf if f.startswith("fam:")}},
       "bar": round(bar, 1)}
w = [d["eval"]["wrong_is_train_answer"] for d in g.values()]; out["allptr_gen"]["wrong_is_bank_answer"] = [sum(x[0] for x in w), sum(x[1] for x in w)]
j1 = ci([100 * (g[s]["eval"]["all"][0] - b[s]["eval"]["all"][0]) for s in seeds])
j2 = ci([100 * g[s]["eval"]["all"][0] - bar for s in seeds])
out["judged1_gen_minus_r3"] = j1 | {"verdict": "PASS" if j1["mean"] >= 15 and j1["ci"][0] > 0 else "FALSIFIED" if j1["mean"] < 5 else "IN BETWEEN"}
out["judged2_gen_minus_bar"] = j2 | {"verdict": "PASS" if j2["mean"] >= 10 and j2["ci"][0] > 0 else "FALSIFIED" if j2["mean"] <= 0 else "IN BETWEEN"}
out["contains_vs_lm_alone"] = ci([100 * g[s]["eval"]["all_contains"][0] - 100 * lm0["all_contains"][0] for s in seeds])
print(json.dumps(out, indent=1))
