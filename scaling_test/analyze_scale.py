#!/usr/bin/env python3
"""Score the scaling test against PASS-MARKS-SCALE.md. Usage: analyze_scale.py RESULTS_DIR [...]  (dirs holding *.json run results)."""
import glob, json, math, statistics as st, sys
T = {4: 2.776, 5: 2.571}
runs, bar = {}, None
for d in sys.argv[1:]:
    for f in glob.glob(d + "/**/*.json", recursive=True):
        if f.endswith("-rows.json") or "rows" in f.split("/")[-1]: continue
        try: r = json.load(open(f))
        except Exception: continue
        if not isinstance(r, dict) or "arm" not in r: continue
        if r["arm"] == "lm_fewshot": bar = r; continue
        if r["arm"] != "allptr": continue
        runs[(r["layers"], r["experts"], r["seed"])] = r
pts = lambda L, E=8: {s: runs[(L, E, s)] for s in range(6) if (L, E, s) in runs}
def acc(r, key="extra"): return 100 * r[key]["all"][0]
def interval(diffs):
    n = len(diffs); m = st.mean(diffs); sd = st.stdev(diffs) if n > 1 else float("nan")
    h = T[n - 1] * sd / math.sqrt(n) if n > 1 else float("nan")
    return round(m, 2), round(m - h, 2), round(m + h, 2)
out = {"n_runs": len(runs)}
S = {L: pts(L) for L in (2, 4, 8)}
seeds = sorted(set.intersection(*[set(S[L]) for L in S])) if all(S.values()) else []
out['t_df'] = max(len(seeds) - 1, 0)
out["seeds_complete"] = seeds
for L in S:
    out[f"S L{L} extra acc by seed"] = {s: round(acc(r), 1) for s, r in S[L].items()}
    out[f"S L{L} mean"] = round(st.mean(acc(r) for r in S[L].values()), 2) if S[L] else None
    out[f"S L{L} core_params"] = next((r["core_params"] for r in S[L].values()), None)
    out[f"S L{L} train_fit mean"] = round(100 * st.mean(r["train_fit"][0] for r in S[L].values()), 1) if S[L] else None
    out[f"S L{L} FRESH-R3 mean (read)"] = round(st.mean(acc(r, "eval") for r in S[L].values()), 2) if S[L] else None
    out[f"S L{L} lesion zero_pool on FRESH-R3 (read)"] = round(st.mean(acc(r, "lesion_zero_pool") for r in S[L].values() if "lesion_zero_pool" in r), 2) if S[L] else None
if len(seeds) >= 2:
    dA = [acc(S[8][s]) - acc(S[2][s]) for s in seeds]; dB = [acc(S[4][s]) - acc(S[2][s]) for s in seeds]
    m, lo, hi = interval(dA); out["A: L8-L2 mean, lo, hi"] = (m, lo, hi); out["A positive seeds"] = sum(d > 0 for d in dA)
    out["A verdict"] = ("PASS" if m >= 5 and lo > 0 and sum(d > 0 for d in dA) >= 5 else "WRONG WAY" if m <= -5 and hi < 0 else
                        "NOT SCALING" if hi < 3 else "IN BETWEEN")
    mb, lob, hib = interval(dB); out["L4-L2 mean, lo, hi"] = (mb, lob, hib)
    mean = {L: st.mean(acc(S[L][s]) for s in seeds) for L in S}
    out["B verdict"] = ("PASS" if out["A verdict"] == "PASS" and mb > 0 and min(mean[2], mean[8]) <= mean[4] <= max(mean[2], mean[8]) + 2 else
                        "FAILS" if out["A verdict"] == "PASS" else "n/a (A not PASS)")
    if bar:
        b = acc(bar); dC = [acc(S[8][s]) - b for s in seeds]; mc, loc, hic = interval(dC)
        out["C: bar (lm_fewshot, NEW-KINDS-S)"] = round(b, 2); out["C: L8-bar mean, lo, hi"] = (mc, loc, hic)
        out["C verdict"] = "PASS" if loc > 0 else "FALSIFIED" if mc < -10 else "IN BETWEEN"
        out["bar FRESH-R3 (read)"] = round(acc(bar, "eval"), 2)
    for L in (2, 4, 8):
        out[f"S L{L} per-family (mean over seeds)"] = {k[4:]: round(100 * st.mean(S[L][s]["extra"][k][0] for s in seeds), 1) for k in S[L][seeds[0]]["extra"] if k.startswith("fam:")}
    out["wrong_is_train_answer (share, mean) per size"] = {L: round(st.mean(S[L][s]["extra"]["wrong_is_train_answer"][0] / max(1, S[L][s]["extra"]["wrong_is_train_answer"][1]) for s in seeds), 3) for L in S}
    out["seconds mean per size"] = {L: round(st.mean(S[L][s]["seconds"] for s in seeds)) for L in S}
E32 = pts(2, 32)
if E32: out["E32 mean (read)"] = round(st.mean(acc(r) for r in E32.values()), 2)
print(json.dumps(out, indent=1))
