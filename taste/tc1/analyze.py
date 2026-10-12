"""Reads result JSONs and pretest JSONs in a directory; writes RESULT.md and RESULT.json.
python3 -m tc1.analyze DIR"""
import glob, json, os, sys
import numpy as np

ARMS = ["C", "R", "R07", "B", "H", "O", "N"]
T1, T07 = "t1.0", "t0.7"


def mean(x):
    return float(np.mean(x))


def load(d):
    runs, pre = {}, {}
    for p in sorted(glob.glob(os.path.join(d, "*-s*.json"))):
        b = os.path.basename(p)
        r = json.load(open(p))
        if b.startswith("pretest-"):
            pre[r["seed"]] = r
        elif r.get("arm") in ARMS:
            runs[(r["arm"], r["seed"])] = r
    return runs, pre


def final(r, key=T1, field="mean_hidden"):
    return r["evals"][-1][key][field]


def analyze(d):
    runs, pre = load(d)
    seeds = sorted({s for (_, s) in runs})
    out = {"seeds": seeds, "arms_present": sorted({a for (a, _) in runs}), "marks": {}, "tables": {}}
    complete = all((a, s) in runs for a in ARMS for s in seeds) and seeds and all(s in pre for s in seeds)
    out["complete"] = bool(complete)
    # tables: final mean hidden score per arm/seed at both temperatures
    for key in (T1, T07):
        out["tables"][f"final_mean_hidden_{key}"] = {
            a: {s: final(runs[(a, s)], key) for s in seeds if (a, s) in runs} for a in ARMS}
    if not complete:
        out["verdict"] = "INCOMPLETE (missing arms/seeds/pretests)"
        return out, runs, pre
    F = lambda a, s, key=T1: final(runs[(a, s)], key)
    headroom = mean([pre[s]["headroom_O_minus_R"] for s in seeds])
    M = max(0.05, 0.25 * headroom)
    CR = [F("C", s) - F("R", s) for s in seeds]
    m1 = {"mean_C_minus_R": mean(CR), "per_seed": CR, "M": M, "headroom": headroom,
          "pass": mean(CR) >= M and all(x > 0 for x in CR)}
    # best of {B, H, R07@1.0/0.7, N@1.0/0.7}; per-seed best (stricter than best of seed-means)
    comp = {"B": lambda s: F("B", s), "H": lambda s: F("H", s),
            "R07@1.0": lambda s: F("R07", s), "R07@0.7": lambda s: F("R07", s, T07),
            "N@1.0": lambda s: F("N", s), "N@0.7": lambda s: F("N", s, T07)}
    diffs, best_names = [], []
    for s in seeds:
        name = max(comp, key=lambda n: comp[n](s))
        best_names.append(name)
        diffs.append(F("C", s) - comp[name](s))
    best_of_means = max(comp, key=lambda n: mean([comp[n](s) for s in seeds]))
    m2 = {"mean_C_minus_best": mean(diffs), "per_seed": diffs, "best_competitor_per_seed": best_names,
          "alt_C_minus_best_of_seed_means": mean([F("C", s) for s in seeds]) - mean([comp[best_of_means](s) for s in seeds]),
          "pass": mean(diffs) >= 0.03 and all(x > 0 for x in diffs)}
    cc = [runs[("C", s)]["evals"][-1][T1]["copy_rate"] for s in seeds]
    m3 = {"C_copy_rate_mean": mean(cc), "per_seed": cc, "pass": mean(cc) <= 0.05}
    t10 = [runs[("C", s)]["evals"][-1][T1]["top10_share_of_samples"] for s in seeds]
    dC = [runs[("C", s)]["evals"][-1][T1]["distinct_share"] for s in seeds]
    dR = [runs[("R", s)]["evals"][-1][T1]["distinct_share"] for s in seeds]
    m4 = {"C_top10_share_mean": mean(t10), "per_seed_top10": t10, "C_distinct_mean": mean(dC),
          "R_distinct_mean": mean(dR),
          "C_top10_share_of_pictures_mean": mean([runs[("C", s)]["evals"][-1][T1]["top10_share"] for s in seeds]),
          "pass": mean(t10) <= 0.20 and mean(dC) >= mean(dR) - 0.05}
    v0 = [runs[("C", s)]["evals"][0][T1]["valid_program_rate"] for s in seeds]
    v6 = [runs[("C", s)]["evals"][-1][T1]["valid_program_rate"] for s in seeds]
    l0 = [runs[("C", s)]["evals"][0]["heldout_loss"] for s in seeds]
    l6 = [runs[("C", s)]["evals"][-1]["heldout_loss"] for s in seeds]
    m5 = {"valid_day0_mean": mean(v0), "valid_final_mean": mean(v6), "loss_day0_mean": mean(l0),
          "loss_final_mean": mean(l6), "loss_rise": mean(l6) / mean(l0) - 1,
          "pass": mean(v6) >= mean(v0) - 0.02 and mean(l6) <= 1.10 * mean(l0)}
    out["marks"] = {"TC1-1": m1, "TC1-2": m2, "TC1-3": m3, "TC1-4": m4, "TC1-5": m5}
    OR = [F("O", s) - F("R", s) for s in seeds]
    C_H = mean([F("C", s) - F("H", s) for s in seeds])
    C_B = mean([F("C", s) - F("B", s) for s in seeds])
    ver = {
        "PASS": all(m["pass"] for m in out["marks"].values()),
        "SHORTCUT": m1["pass"] and (C_H < 0.03 or C_B < 0.03),
        "NO GAIN": mean(CR) <= 0.02 and all(x <= 0.04 for x in CR),
        "TOY TOO HARD": mean(OR) < M,
    }
    out["O_minus_R_after_night6"] = {"mean": mean(OR), "per_seed": OR}
    out["C_minus_H_mean"], out["C_minus_B_mean"] = C_H, C_B
    out["verdicts_that_apply"] = [k for k, v in ver.items() if v]
    # precedence when several apply (spec silent): PASS, SHORTCUT, TOY TOO HARD, NO GAIN
    verdict = next((k for k in ("PASS", "SHORTCUT", "TOY TOO HARD", "NO GAIN") if ver[k]), "UNDERPOWERED")
    out["verdict"] = verdict
    return out, runs, pre


def md(out, runs, pre):
    L = ["# TC-1 result", ""]
    L.append(f"Seeds: {out['seeds']}; arms present: {out['arms_present']}; complete: {out['complete']}")
    L.append(f"\n**Verdict: {out['verdict']}**")
    if out.get("verdicts_that_apply") is not None:
        L.append(f"(verdicts whose conditions hold: {out['verdicts_that_apply']})")
    L.append("\n## Marks\n")
    for name, m in out["marks"].items():
        L.append(f"- **{name}**: {'PASS' if m['pass'] else 'FAIL'}  " +
                 json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != 'pass'}))
    for key in (T1, T07):
        L.append(f"\n## Final mean hidden score (after last night, temperature {key[1:]})\n")
        L.append("| arm | " + " | ".join(f"seed {s}" for s in out["seeds"]) + " | mean |")
        L.append("|---|" + "---|" * (len(out["seeds"]) + 1))
        for a in ARMS:
            vals = [out["tables"][f"final_mean_hidden_{key}"][a].get(s) for s in out["seeds"]]
            ok = [v for v in vals if v is not None]
            L.append(f"| {a} | " + " | ".join("-" if v is None else f"{v:.3f}" for v in vals) +
                     f" | {mean(ok):.3f} |" if ok else f"| {a} | missing |")
    L.append("\n## Per-night curves (mean hidden score, T=1.0), per seed\n")
    for s in out["seeds"]:
        L.append(f"seed {s}\n\n| arm | " + " | ".join(f"n{i}" for i in range(len(next(iter(runs.values()))['evals']))) + " |")
        L.append("|---|" + "---|" * len(next(iter(runs.values()))['evals']))
        for a in ARMS:
            if (a, s) in runs:
                L.append(f"| {a} | " + " | ".join(f"{e[T1]['mean_hidden']:.3f}" for e in runs[(a, s)]["evals"]) + " |")
        L.append("")
    L.append("## Arm C critic exam per day (AUC)\n")
    for s in out["seeds"]:
        if ("C", s) in runs:
            L.append(f"seed {s}: pretest exam {json.dumps({k: round(v, 3) for k, v in pre.get(s, {}).get('critic_exam', {}).items() if isinstance(v, float)})}")
            for d in runs[("C", s)]["days"]:
                e = d["critic_exam"]
                L.append(f"- day {d['day']}: held-back {e['heldback_vs_fresh']:.3f}, novel {e['novel_vs_fresh']:.3f}, "
                         f"broken {e['heldback_vs_broken']:.3f}")
            L.append("")
    L.append("## Pretest (pick-only, day-0 maker)\n")
    for s, p in sorted(pre.items()):
        L.append(f"seed {s}: picks(8) " + json.dumps({k: round(v['mean'], 3) for k, v in p["picks_8"].items()}) +
                 " C by tries " + json.dumps({k: round(v['mean'], 3) for k, v in p["C_by_tries"].items()}) +
                 f" headroom {p['headroom_O_minus_R']:.3f}")
    L.append("\n## Final-night secondary metrics, T=1.0\n")
    L.append("| arm | seed | full-house | copy | valid | distinct | top10 | heldout loss | traits |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for (a, s), r in sorted(runs.items()):
        e = r["evals"][-1]; t = e[T1]
        L.append(f"| {a} | {s} | {t['full_house_rate']:.3f} | {t['copy_rate']:.3f} | {t['valid_program_rate']:.3f} | "
                 f"{t['distinct_share']:.3f} | {t['top10_share_of_samples']:.3f} | {e['heldout_loss']:.3f} | "
                 + " ".join(f"{k[:3]}={v:.2f}" for k, v in t['trait_rates'].items()) + " |")
    return "\n".join(L) + "\n"


def main(argv=None):
    d = (argv or sys.argv[1:])[0]
    out, runs, pre = analyze(d)
    json.dump(out, open(os.path.join(d, "RESULT.json"), "w"), indent=1, default=float)
    open(os.path.join(d, "RESULT.md"), "w").write(md(out, runs, pre))
    print(out["verdict"])


if __name__ == "__main__":
    main()
