#!/usr/bin/env python3
"""Score the LFM2.5-350M swap against PASS-MARKS-SMALL-LM.md. Usage: analyze_small.py R4_ENGLISH_DIR"""
import glob, json, statistics as st, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; R4 = Path(sys.argv[1])
def load(pat):
    R = {}
    for f in glob.glob(str(pat)):
        if f.endswith("-rows.json"): continue
        d = json.load(open(f)); R[(d["arm"], d.get("seed", 0))] = d
    return R
small, big = load(HERE / "results/box*/out/*.json"), load(R4 / "results4/box*/out/*.json")
s = {k[1]: d for k, d in small.items() if k[0] == "allptr"}; b = {k[1]: d for k, d in big.items() if k[0] == "allptr"}
seeds = sorted(set(s) & set(b))
pc = lambda d, *p: 100 * (lambda x: x[0] if isinstance(x, list) else x)(__import__("functools").reduce(lambda a, k: a[k], p, d))
def ci(x):
    mu = st.mean(x); h = {3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}[len(x)] * st.stdev(x) / len(x) ** .5 if len(x) > 1 else 0
    return {"n": len(x), "mean": round(mu, 1), "ci95": [round(mu - h, 1), round(mu + h, 1)], "per_seed": [round(v, 1) for v in x]}
keys = ["all", "all_contains", "fresh_source", "fresh_paraphrase", "new_word_answers", "yes_no"]
out = {"seeds": seeds,
       "small_350M": {k: round(st.mean(pc(s[q], "eval", k) for q in seeds), 1) for k in keys}
       | {"train_fit_bank": round(st.mean(pc(s[q], "train_fit") for q in seeds), 1),
          "gen_heldout": round(st.mean(pc(s[q], "gen_heldout", "all") for q in seeds), 1),
          "lesion_zero_pool": round(st.mean(pc(s[q], "lesion_zero_pool", "all") for q in seeds), 1),
          "families": {f[4:]: round(st.mean(pc(s[q], "eval", f) for q in seeds), 1) for f in s[seeds[0]]["eval"] if f.startswith("fam:")}},
       "big_1p2B": {k: round(st.mean(pc(b[q], "eval", k) for q in seeds), 1) for k in keys}
       | {"train_fit_bank": round(st.mean(pc(b[q], "train_fit") for q in seeds), 1),
          "gen_heldout": round(st.mean(pc(b[q], "gen_heldout", "all") for q in seeds), 1)}}
for a in ("lm_alone", "lm_fewshot"):
    if (a, 0) in small: out[f"bare_350M_{a}"] = round(pc(small[(a, 0)], "eval", "all"), 1)
drop = ci([pc(b[q], "eval", "all") - pc(s[q], "eval", "all") for q in seeds])
m1 = drop["mean"] <= 5 and max(drop["per_seed"]) <= 10
sm = [pc(s[q], "eval", "all") for q in seeds]
m2 = st.mean(sm) >= 85 and min(sm) > 75
out["M1_drop_vs_1p2B"] = drop | {"verdict": "PASS" if m1 else "FAIL"}
out["M2_vs_bare_1p2B_8shot_75"] = {"mean": round(st.mean(sm), 1), "min": round(min(sm), 1), "verdict": "PASS" if m2 else "FAIL"}
out["complete"] = len(seeds) == 6
print(json.dumps(out, indent=1))
