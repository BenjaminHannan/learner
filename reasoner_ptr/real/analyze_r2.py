"""Score the real-pipeline pointer test against PASS-MARKS-R2.md. Reads results/box*/out/{arm}-seed*.json."""
import json, glob, math, statistics as st
R = {}
for f in glob.glob("results/box*/out/*-seed*.json"):
    if "rows" in f: continue
    d = json.load(open(f)); R[(d["arm"], d["seed"])] = d
def g(arm, key, src="eval"):
    return {s: 100 * R[(arm, s)][src][key][0] for s in range(6) if (arm, s) in R and src in R[(arm, s)]}
def paired(a, b, key, sa="eval", sb="eval"):
    x, y = g(a, key, sa), g(b, key, sb); ss = sorted(set(x) & set(y)); d = [x[s] - y[s] for s in ss]
    if len(d) < 2: return {"n": len(d), "per_seed": d}
    m, sd = st.mean(d), st.stdev(d); h = 2.571 * sd / math.sqrt(6) if len(d) == 6 else float("nan")
    return {"n": len(d), "mean": round(m, 1), "ci": [round(m - h, 1), round(m + h, 1)], "per_seed": [round(v, 1) for v in d]}
out = {"runs": sorted(f"{a}{s}" for a, s in R)}
for arm in ("pool", "ptr", "emb"):
    if not any(k[0] == arm for k in R): continue
    o = {k: round(st.mean(g(arm, k).values()), 1) for k in ("unseen", "seen", "two_hop", "one_hop", "new_wording", "train_wording", "all")}
    o["train_fit"] = round(100 * st.mean(R[(arm, s)]["train_fit_192"] for s in range(6) if (arm, s) in R), 1)
    w = [R[(arm, s)]["eval"]["wrong_unseen_is_train_word"] for s in range(6) if (arm, s) in R]
    o["wrong_unseen_is_train_word"] = [sum(a for a, _ in w), sum(b for _, b in w)]
    for les in ("lesion_uniform", "lesion_zero_pool"):
        if any(les in R[k] for k in R if k[0] == arm):
            o[les] = {k: round(st.mean(g(arm, k, les).values()), 1) for k in ("unseen", "seen", "all")}
    if arm == "ptr": o["ptr_hit"] = round(100 * st.mean(R[(arm, s)]["eval"]["ptr_hit"] for s in range(6) if (arm, s) in R), 1)
    out[arm] = o
v = {}
if all(("pool", s) in R and ("ptr", s) in R for s in range(6)):
    gain = paired("ptr", "pool", "unseen"); seen = paired("ptr", "pool", "seen"); les = paired("ptr", "ptr", "unseen", "eval", "lesion_uniform")
    v.update(ptr_vs_pool_unseen=gain, ptr_vs_pool_seen=seen, ptr_minus_uniform_lesion_unseen=les)
    ok = gain["mean"] >= 25 and gain["ci"][0] > 0 and seen["mean"] >= -5 and les["mean"] >= 0.5 * gain["mean"]
    v["verdict"] = "PASS" if ok else ("FALSIFIED" if gain["mean"] < 8 else "IN BETWEEN")
if all(("emb", s) in R and ("ptr", s) in R for s in range(6)):
    v["emb_vs_ptr_unseen"] = paired("emb", "ptr", "unseen"); v["emb_vs_ptr_all"] = paired("emb", "ptr", "all")
out["verdicts"] = v
print(json.dumps(out, indent=1))
