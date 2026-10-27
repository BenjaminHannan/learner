"""slp-358n3 official scoring (helper S). Reads the four seed JSONs and scores them with the sealed PASSMARKS.md.
Pure counting; no torch, no training. Output: artifacts/claude-slp358n3-20260927/claude_slp358n3_report_score.json

Rules implemented, quoted from artifacts/claude-slp358n3-20260927/PASSMARKS.md (line numbers are checked at run time):

 L62  | M1 learns from the day | S − R on day_grids and on day_sums (400 each) | mean ≥ +20 and ≥ +20 on 3 of 4 seeds, each kind.
      Ceiling rule: a kind where S and R are both ≥ 360 on a seed counts as uninformative on that seed. Floor rule: a kind
      where S and R are both ≤ 40 on a seed is also uninformative on that seed. The kind passes if its informative seeds
      pass. If it is uninformative on 3 or more seeds, it is reported as such and M1 rests on the other kind (and if both
      are, M1 fails). |
 L63  | M2 not a placebo | S − Z on each day kind | ≥ +20 on 3 of 4 seeds, each kind (same ceiling and floor rules) |
 L64  | M3 no harm | S on harm_sums4 and harm_grids5 (300 each) | ≥ N − 6, every seed, each test |
 L65  | M3b retention | "lost" = harm items the arm's pre-night net got right and its morning gets wrong, after each of the 3
      nights | S lost ≤ 15 of 300, every seed, every night, each test |
 L66  | RESUME | ... arm S, seed 13, nights 1-2. Run 1 goes straight through. Run 2 stops at step 150 of night 2 ... Run 3, a
      fresh process, resumes from that file. | the weights and the optimizer state after night 2 are identical (torch.equal on
      every tensor), and the hashes of the 150 batches drawn after the resume equal the straight run's batches 150-299 |
 L68  **PASS (H-B) = M1, M2, M3, M3b and RESUME.** Otherwise FAIL (stays FAIL).
 L70-71 **Proved wrong** ... S − R ≤ +5 on both day kinds, on 3 of 4 seeds, with neither kind at the ceiling or floor on those seeds.

Choices where the text leaves room (all logged in the output under "readings"):
 * Marks are read after night 3 ("Marks (after night 3; per seed s13-s16)"); mornings 1 and 2 are report only, except M3b,
   which the text says covers every night.
 * "mean >= +20": the mean of S-R over the INFORMATIVE seeds of that kind; "3 of 4 seeds": at least min(3, n_informative)
   of the informative seeds; a kind with < 1 informative seed cannot pass. The output also states whether this choice mattered
   (it does not if all 4 seeds are informative).
 * Ceiling/floor use the 400-item day counts (morning 3), 'right' field, for the two arms compared.
 * N in M3 is the untouched net's score on the same test (morning[3]['N'], which the script also checks equals 'base').
"""
import json, hashlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "artifacts/claude-slp358n3-20260927")
OUT = os.path.join(A, "claude_slp358n3_report_score.json")
SEEDS = [13, 14, 15, 16]

# --- guard: the quoted lines must be where I say they are, and PASSMARKS.md must be the sealed file
pm = open(os.path.join(A, "PASSMARKS.md"), encoding="utf-8").read().split("\n")
def line(n): return pm[n - 1]
assert line(62).startswith("| M1 learns from the day") and "mean ≥ +20 and ≥ +20 on 3 of 4 seeds" in line(62)
assert "both ≥ 360" in line(62) and "both ≤ 40" in line(62)
assert line(63).startswith("| M2 not a placebo") and "≥ +20 on 3 of 4 seeds" in line(63)
assert line(64).startswith("| M3 no harm") and "≥ N − 6, every seed, each test" in line(64)
assert line(65).startswith("| M3b retention") and "S lost ≤ 15 of 300, every seed, every night, each test" in line(65)
assert line(66).startswith("| RESUME")
assert line(68).startswith("**PASS (H-B) = M1, M2, M3, M3b and RESUME.**")
assert "S − R ≤ +5 on both day kinds, on 3 of 4 seeds" in line(71)
GAIN, CEIL, FLOOR, MIN_OK = 20, 360, 40, 3          # L62/L63
HARM_SLACK, LOST_MAX = 6, 15                        # L64/L65
WRONG_GAIN = 5                                      # L71
pm_sha = hashlib.sha256(open(os.path.join(A, "PASSMARKS.md"), "rb").read()).hexdigest()
sealed = {p.strip(): h for h, p in (l.split(None, 1) for l in open(os.path.join(A, "SEAL-code.sha256.txt")).read().splitlines() if l.strip())}
assert sealed["artifacts/claude-slp358n3-20260927/PASSMARKS.md"] == pm_sha, "PASSMARKS.md is not the sealed file"

D = {s: json.load(open(os.path.join(A, f"runs/s{s}/slp358n3-seed{s}.json"))) for s in SEEDS}
sizes = json.load(open(os.path.join(A, "run-vast/sizes.json")))
res = {"passmarks_sha256": pm_sha, "readings": {}, "checks": {}}

# --- sanity checks on the records (not marks)
chk = res["checks"]
chk["cfg_matches_passmarks"] = all(D[s]["cfg"][k] == v for s in SEEDS for k, v in
    dict(night_steps=300, long_steps=6000, night_lr=3e-5, batch=256, days=3, n_day=300, n_test=400, n_harm=300, n_report=200, stop_step=150).items())
chk["day_sizes"] = {str(s): D[s]["sizes"] for s in SEEDS}
chk["day_sizes_match_sizes_json"] = all(D[s]["sizes"] == sizes["sizes"] for s in SEEDS)
means = sizes["means"]
chk["size_rule_recomputed"] = {k: min([int(z) for z, v in m.items() if v <= 240] or [max(int(z) for z in m)]) for k, m in means.items()}
chk["excluded_day_items"] = {str(s): D[s]["excluded_day_items"] for s in SEEDS}
chk["N_equals_base_every_morning"] = all(D[s]["morning"][str(m)]["N"][t] == D[s]["morning"]["base"][t]
                                         for s in SEEDS for m in (1, 2, 3) for t in D[s]["morning"]["base"])
chk["day1_all_arms_identical_before_first_night"] = all(
    len({json.dumps(D[s]["day"]["1"][a], sort_keys=True) for a in D[s]["day"]["1"]}) == 1 for s in SEEDS)
chk["n_per_test"] = {t: sorted({D[s]["morning"]["3"]["S"][t]["n"] for s in SEEDS}) for t in D[13]["morning"]["3"]["S"]}
chk["arms_present"] = {str(s): sorted(D[s]["morning"]["3"]) for s in SEEDS}
chk["torch"] = sorted({D[s]["torch"] for s in SEEDS}); chk["gpu"] = sorted({D[s]["gpu"] for s in SEEDS})
chk["minutes"] = {str(s): D[s]["minutes"] for s in SEEDS}

def r(s, m, arm, t): return D[s]["morning"][str(m)][arm][t]["right"]

# --- M1 / M2
def gain_mark(name, other, kinds=("day_sums", "day_grids"), m=3):
    out = {"pass_all_kinds_needed": True, "kinds": {}}
    resting = []
    for k in kinds:
        rows = {}
        for s in SEEDS:
            a, b = r(s, m, "S", k), r(s, m, other, k)
            ceil = a >= CEIL and b >= CEIL
            floor = a <= FLOOR and b <= FLOOR
            rows[s] = {"S": a, other: b, "diff": a - b, "ceiling": ceil, "floor": floor, "informative": not (ceil or floor),
                       "diff_ge_20": a - b >= GAIN}
        inf = [s for s in SEEDS if rows[s]["informative"]]
        n_unin = len(SEEDS) - len(inf)
        mean = sum(rows[s]["diff"] for s in inf) / len(inf) if inf else None
        n_ok = sum(rows[s]["diff_ge_20"] for s in inf)
        need = min(MIN_OK, len(inf))
        uninformative_kind = n_unin >= 3
        passes = (not uninformative_kind) and mean is not None and mean >= GAIN and n_ok >= need
        mean_all = sum(rows[s]["diff"] for s in SEEDS) / 4
        out["kinds"][k] = {"per_seed": rows, "informative_seeds": inf, "n_uninformative": n_unin,
                           "mean_diff_informative": mean, "mean_diff_all4": mean_all, "seeds_with_diff_ge_20": n_ok,
                           "needed": need, "kind_uninformative_3plus": uninformative_kind, "kind_passes": passes,
                           "reading_mattered": n_unin > 0}
    passing = [k for k in kinds if out["kinds"][k]["kind_passes"]]
    unin = [k for k in kinds if out["kinds"][k]["kind_uninformative_3plus"]]
    if len(unin) == len(kinds): out["pass"] = False
    else: out["pass"] = all(out["kinds"][k]["kind_passes"] for k in kinds if k not in unin)
    out["uninformative_kinds"] = unin
    return out
res["M1"] = gain_mark("M1", "R")
res["M2"] = gain_mark("M2", "Z")

# --- M3 (after night 3) and M3b
m3 = {"rows": {}, "pass": True}
for s in SEEDS:
    for t in ("harm_sums4", "harm_grids5"):
        S_, N_ = r(s, 3, "S", t), r(s, 3, "N", t)
        ok = S_ >= N_ - HARM_SLACK
        m3["rows"][f"s{s}/{t}"] = {"S": S_, "N": N_, "S_minus_N": S_ - N_, "pass": ok}
        m3["pass"] &= ok
res["M3"] = m3
m3b = {"rows": {}, "pass": True}
for s in SEEDS:
    for n in (1, 2, 3):
        for t in ("harm_sums4", "harm_grids5"):
            v = D[s]["lost"][str(n)]["S"][t]
            m3b["rows"][f"s{s}/night{n}/{t}"] = {"lost_of_300": v, "pass": v <= LOST_MAX}
            m3b["pass"] &= v <= LOST_MAX
m3b["max_lost"] = max(x["lost_of_300"] for x in m3b["rows"].values())
res["M3b"] = m3b

# --- RESUME
rj = json.load(open(os.path.join(A, "run-vast/resume.json")))
need = dict(weights_identical=True, optimizer_identical=True, batches_after_resume_identical=True, RESUME_identical=True)
res["RESUME"] = {"record": rj, "fields_true": {k: rj.get(k) is True for k in need},
                 "settings_ok": rj["night_steps"] == 300 and rj["batch"] == 256 and rj["stop_step"] == 150 and rj["return_codes"] == [0, 3, 0],
                 "pass": all(rj.get(k) is True for k in need) and rj["night_steps"] == 300 and rj["batch"] == 256
                         and rj["stop_step"] == 150 and rj["return_codes"] == [0, 3, 0],
                 "note": "CPU, float32, deterministic algorithms, 4 threads: read from the sealed code (nights_only, lines 323-324 and the 'cpu' argument), not from the record"}

marks = {k: res[k]["pass"] for k in ("M1", "M2", "M3", "M3b", "RESUME")}
res["marks"] = marks
res["VERDICT"] = "PASS" if all(marks.values()) else "FAIL"

# --- Proved wrong test (L70-71)
pw = {}
cnt = 0
for s in SEEDS:
    ok = True
    for k in ("day_sums", "day_grids"):
        e = res["M1"]["kinds"][k]["per_seed"][s]
        ok &= (e["diff"] <= WRONG_GAIN) and e["informative"]
    pw[s] = ok; cnt += ok
res["proved_wrong"] = {"per_seed_both_kinds_le_5_and_informative": pw, "seeds": cnt, "proved_wrong": cnt >= 3}

# --- Report only
tests = list(D[13]["morning"]["3"]["S"])
rep = {}
rep["mornings_1_2_3"] = {str(s): {str(m): {a: {t: r(s, m, a, t) for t in tests} for a in D[s]["morning"]["3"]} for m in (1, 2, 3)} for s in SEEDS}
rep["base"] = {str(s): {t: D[s]["morning"]["base"][t]["right"] for t in tests} for s in SEEDS}
rep["day_tries"] = {str(s): {d: {a: {k: D[s]["day"][d][a][k]["right"] for k in D[s]["day"][d][a]} for a in D[s]["day"][d]} for d in "123"} for s in SEEDS}
rep["harm_R_vs_N_Z_vs_N_after_night3"] = {str(s): {t: {"R-N": r(s, 3, "R", t) - r(s, 3, "N", t), "Z-N": r(s, 3, "Z", t) - r(s, 3, "N", t)}
                                                   for t in ("harm_sums4", "harm_grids5")} for s in SEEDS}
rep["lost_all_arms"] = {str(s): D[s]["lost"] for s in SEEDS}
rep["L_vs_S_vs_N"] = {str(s): {str(m): {t: {"L": r(s, m, "L", t), "S": r(s, m, "S", t), "N": r(s, m, "N", t),
                                            "L-S": r(s, m, "L", t) - r(s, m, "S", t), "L-N": r(s, m, "L", t) - r(s, m, "N", t)} for t in tests}
                               for m in (1, 2, 3)} for s in (13, 14)}
rep["L_lost"] = {str(s): {n: D[s]["lost"][n]["L"] for n in "123"} for s in (13, 14)}
rep["L_day_tries_vs_S"] = {str(s): {d: {k: {"L": D[s]["day"][d]["L"][k]["right"], "S": D[s]["day"][d]["S"][k]["right"], "N": D[s]["day"][d]["N"][k]["right"]} for k in ("sums", "grids")} for d in "123"} for s in (13, 14)}
rep["mean_stop_round_morning3"] = {str(s): {a: {t: D[s]["morning"]["3"][a][t]["mean_rounds"] for t in tests} for a in D[s]["morning"]["3"]} for s in SEEDS}
rep["fixed8_fixed48_morning3"] = {str(s): {a: {t: [D[s]["morning"]["3"][a][t]["fixed8"], D[s]["morning"]["3"][a][t]["fixed48"]] for t in tests} for a in D[s]["morning"]["3"]} for s in SEEDS}
rep["night_minutes"] = {str(s): D[s]["night_minutes"] for s in SEEDS}
res["report_only"] = rep
res["readings"] = {
    "marks_read_after": "night 3 (morning 3); M3b over nights 1, 2 and 3",
    "M1_M2_mean": "mean of S-R (S-Z) over the informative seeds of the kind; 3-of-4 becomes min(3, informative seeds)",
    "reading_mattered": {m: [k for k in res[m]["kinds"] if res[m]["kinds"][k]["reading_mattered"]] for m in ("M1", "M2")},
}
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)

# --- short text
def P(*a): print(*a)
P("passmarks sha", pm_sha[:16], "sealed ok")
for m in ("M1", "M2"):
    for k, e in res[m]["kinds"].items():
        P(m, k, "diffs", {s: e["per_seed"][s]["diff"] for s in SEEDS}, "informative", e["informative_seeds"],
          "mean", e["mean_diff_informative"], "kind passes", e["kind_passes"])
    P(m, "PASS" if res[m]["pass"] else "FAIL")
P("M3", {k: v["S_minus_N"] for k, v in m3["rows"].items()}, "PASS" if m3["pass"] else "FAIL")
P("M3b max lost", m3b["max_lost"], "PASS" if m3b["pass"] else "FAIL")
P("RESUME", "PASS" if res["RESUME"]["pass"] else "FAIL")
P("proved wrong seeds", cnt, res["proved_wrong"]["proved_wrong"])
P("checks", json.dumps(chk))
P("VERDICT", res["VERDICT"])
