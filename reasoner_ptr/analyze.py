"""Score the two-doors runs against PASS-MARKS.md. Reads results/box*/out/arm*-seed*.json."""
import json, glob, statistics as st, math
R = {}
for f in glob.glob("results/box*/out/arm*-seed*.json"):
    if f.endswith("-rows.json"): continue
    d = json.load(open(f)); R[(d["arm"], d["seed"])] = d
T = 2.571
def get(arm, key, lesion=False):
    src = lambda d: d["lesion_uniform_pointer"] if lesion else d["eval"]
    return {s: 100 * src(R[(arm, s)])[key][0] for s in range(6) if (arm, s) in R}
def paired(a, b, key, la=False, lb=False):
    x, y = get(a, key, la), get(b, key, lb); seeds = sorted(set(x) & set(y))
    d = [x[s] - y[s] for s in seeds]
    if len(d) < 2: return {"n": len(d)}
    m, sd = st.mean(d), st.stdev(d); h = T * sd / math.sqrt(len(d)) if len(d) == 6 else float("nan")
    return {"n": len(d), "mean": round(m, 1), "sd": round(sd, 1), "ci": [round(m - h, 1), round(m + h, 1)], "per_seed": [round(v, 1) for v in d]}
out = {"runs": sorted(f"{a}{s}" for a, s in R)}
for arm in ("A", "B", "C", "W", "BW"):
    if any(k[0] == arm for k in R):
        out[arm] = {k: round(st.mean(get(arm, k).values()), 1) for k in ("unseen", "seen", "two_hop", "seen_two_hop", "one_hop", "all")}
        out[arm]["train_fit"] = round(100 * st.mean(R[(arm, s)]["train_fit_192"] for s in range(6) if (arm, s) in R), 1)
        out[arm]["per_seed_unseen"] = [round(v, 1) for v in get(arm, "unseen").values()]
        if arm in ("B", "BW"):
            out[arm]["lesion_unseen"] = round(st.mean(get(arm, "unseen", True).values()), 1)
            out[arm]["ptr_hit"] = round(100 * st.mean(R[(arm, s)]["eval"]["ptr_hit"] for s in range(6) if (arm, s) in R), 1)
        w = [R[(arm, s)]["eval"]["wrong_unseen_is_train_word"] for s in range(6) if (arm, s) in R]
        out[arm]["wrong_unseen_is_train_word"] = [sum(a for a, _ in w), sum(b for _, b in w)]
v = {}
if all(("A", s) in R and ("B", s) in R for s in range(6)):
    g = paired("B", "A", "unseen"); seen = paired("B", "A", "seen"); les = paired("B", "B", "unseen", lb=True)
    v["B_vs_A_unseen"] = g; v["B_vs_A_seen"] = seen; v["B_minus_lesion_unseen"] = les
    ok = g["mean"] >= 25 and g["ci"][0] > 0 and seen["mean"] >= -5 and les["mean"] >= 0.5 * g["mean"]
    v["B_verdict"] = "PASS" if ok else ("FALSIFIED" if g["mean"] < 8 else "IN BETWEEN")
if all(("A", s) in R and ("W", s) in R for s in range(6)):
    g = paired("W", "A", "seen_two_hop"); v["W_vs_A_seen_two_hop"] = g
    v["W_verdict"] = "PASS" if g["mean"] >= 10 and g["ci"][0] > 0 else ("FALSIFIED" if g["mean"] < 3 else "IN BETWEEN")
if all(("B", s) in R and ("BW", s) in R for s in range(6)):
    g = paired("BW", "B", "two_hop"); v["BW_vs_B_two_hop"] = g
    v["BW_verdict"] = "PASS" if g["mean"] >= 10 and g["ci"][0] > 0 else ("FALSIFIED" if g["mean"] < 3 else "IN BETWEEN")
if all(("A", s) in R and ("C", s) in R for s in range(6)):
    v["C_vs_A_unseen"] = paired("C", "A", "unseen")
out["verdicts"] = v
print(json.dumps(out, indent=1))
