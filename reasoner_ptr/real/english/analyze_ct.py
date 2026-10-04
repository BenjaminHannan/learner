#!/usr/bin/env python3
"""Score the copy-talker test against PASS-MARKS-CT.md. Usage: analyze_ct.py RESULTS_CT_DIR > ANALYSIS-CT.json
Control = round 6 six arm (results6/box*/out/allptr-gen-six-seed*.json)."""
import glob, json, math, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
T5 = 2.571
BAR = {"extra": 67.7, "extra2": 77.6}


def load(pattern):
    out = {}
    for f in glob.glob(pattern, recursive=True):
        if "rows" in f: continue
        d = json.load(open(f)); out[d["seed"]] = d
    return out


def pooled(d):  # NEW-KINDS-R5 + NEW-KINDS2-R6, 192 + 192 questions
    (a, n1), (b, n2) = d["extra"]["all"], d["extra2"]["all"]
    return 100 * (a * n1 + b * n2) / (n1 + n2)


def stats(xs):
    m = statistics.mean(xs); s = statistics.stdev(xs) if len(xs) > 1 else float("nan")
    h = T5 * s / math.sqrt(len(xs))
    return {"n": len(xs), "mean": round(m, 2), "ci": [round(m - h, 2), round(m + h, 2)], "per_seed": [round(x, 2) for x in xs]}


def main(ct):
    six = load(str(HERE / "results6/**/allptr-gen-six-seed*.json"))
    six = {k: v for k, v in six.items() if True}
    cp = load(f"{ct}/**/copytalk-gen-ct-seed*.json")
    nc = load(f"{ct}/**/copytalk_nocore-gen-ct-seed*.json")
    ap = load(f"{ct}/**/allptr-gen-ct-seed*.json")
    seeds = sorted(set(six) & set(cp) & set(nc))
    r = {"seeds": seeds}
    for name, d in (("allptr_r6", six), ("copytalk", cp), ("copytalk_nocore", nc)):
        r[name] = {"unseen": stats([pooled(d[s]) for s in seeds]),
                   "extra": stats([100 * d[s]["extra"]["all"][0] for s in seeds]),
                   "extra2": stats([100 * d[s]["extra2"]["all"][0] for s in seeds]),
                   "heldout": stats([100 * d[s]["gen_heldout"]["all"][0] for s in seeds]),
                   "fresh": stats([100 * d[s]["eval"]["all"][0] for s in seeds]),
                   "train_fit": [d[s]["train_fit"][0] for s in seeds]}
        if name != "allptr_r6":
            r[name]["atype_unseen"] = {at: round(statistics.mean(
                100 * (d[s]["extra"][f"atype:{at}"][0] * d[s]["extra"][f"atype:{at}"][1] + d[s]["extra2"][f"atype:{at}"][0] * d[s]["extra2"][f"atype:{at}"][1])
                / max(1, d[s]["extra"][f"atype:{at}"][1] + d[s]["extra2"][f"atype:{at}"][1]) for s in seeds), 1)
                for at in ("yes_no", "span1", "spanN", "nonspan")}
            r[name]["talk_ms_per_q"] = [d[s].get("talk_ms_per_q") for s in seeds]
            r[name]["infer_ms_per_q"] = [d[s].get("infer_ms_per_q") for s in seeds]
            r[name]["params"] = d[seeds[0]]["params"]
    gap = [pooled(cp[s]) - pooled(six[s]) for s in seeds]
    gaph = [100 * (cp[s]["gen_heldout"]["all"][0] - six[s]["gen_heldout"]["all"][0]) for s in seeds]
    within = sum(abs(g) <= 8 or g > 0 for g in gap)
    a0 = ap.get(0)
    speed = None
    if a0 and 0 in cp and cp[0].get("talk_ms_per_q"):
        speed = a0["talk_ms_per_q"] / max(cp[0]["talk_ms_per_q"], 1e-9)
    below_bar = any(r["copytalk"][k]["mean"] < BAR[k] for k in BAR)
    A = {"gap_unseen": stats(gap), "gap_heldout": stats(gaph), "seeds_within_8": within, "talk_speedup_seed0": speed,
         "below_bare_bar": below_bar}
    ok = A["gap_unseen"]["mean"] >= -5 and A["gap_heldout"]["mean"] >= -5 and within >= 5 and speed is not None and speed >= 5
    fail = A["gap_unseen"]["mean"] < -10 or below_bar
    A["verdict"] = "FAILS" if fail else "PASS" if ok else "IN BETWEEN"
    r["A_copytalk_minus_allptr"] = A
    core = [pooled(cp[s]) - pooled(nc[s]) for s in seeds]
    B = stats(core)
    B["verdict"] = "REAL" if B["mean"] >= 10 and B["ci"][0] > 0 else "NOT SHOWN" if B["mean"] < 3 else "IN BETWEEN"
    r["B_copytalk_minus_nocore"] = B
    if a0:
        r["allptr_seed0_rerun"] = {"unseen": round(pooled(a0), 2), "r6_seed0_unseen": round(pooled(six[0]), 2),
                                   "shuffle_core_unseen": round(100 * a0["lesion_shuffle_core_unseen"]["all"][0], 2),
                                   "talk_ms_per_q": a0.get("talk_ms_per_q"), "infer_ms_per_q": a0.get("infer_ms_per_q")}
    print(json.dumps(r, indent=1))


main(sys.argv[1])
