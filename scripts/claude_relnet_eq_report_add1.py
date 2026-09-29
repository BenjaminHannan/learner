#!/usr/bin/env python3
"""Apply PASSMARKS-C.md as amended by ADDENDUM-1.md to the raw harness JSON (relation-net race, equal-practice ruler).

  selftest -> add1-selftest.json     fake seeds, no torch, no raw files needed
  dev      -> race-dev-add1.json     dev tables incl. F_few (no gate, no verdict)
  holdout  -> race-holdout-add1.json every mark per seed and the verdict words

Replaces scripts/claude_relnet_eq_race.py's verdict (that file is untouched). Seeds are never pooled.
Reads only adapt.json / holdout.json / sleepdraws/*.json files. Reuses the arithmetic helpers of
scripts/claude_patch_eq_report.py (untouched).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_patch_eq_report as R  # noqa: E402

ROOT = R.ROOT
ART = ROOT / "artifacts" / "claude-relnet-eq-20260928"
BASE = R.BASE
KINDS, SEEDS = R.KINDS, R.SEEDS
FEW = ("1", "4", "16", "64")
BRANCHES = ("64", "16384")
MARGIN_FLOOR = 6            # X1: margin = max(6, 2 x SE)
NEEDS = {"F_eq": 10, "F_few": 5, "over_plain": 5, "over_fresh": 5}
LOSE_BAR = 2                # X4: "REJECTED by losing" needs both seeds at least 2 points below
OLD_BEFORE_SLACK = 6


def f_few(counts):
    return sum(100 * counts[k] / 300 for k in FEW) / len(FEW)


def mean_sd(xs):
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def sleep_gate(r_draws, ctl_draws, recorded_loop):
    """X1: the relation net's three-draw mean must be at least
    max(loop-control three-draw mean, the recorded loop's single draw) minus max(6, 2 x SE_diff),
    SE_diff from the two arms' three draws each."""
    (rm, rs), (cm, cs) = mean_sd(r_draws), mean_sd(ctl_draws)
    se = math.sqrt(rs ** 2 / len(r_draws) + cs ** 2 / len(ctl_draws))
    margin = max(MARGIN_FLOOR, 2 * se)
    comp = max(cm, recorded_loop)
    return {"relnet_mean": rm, "loop_ctl_mean": cm, "recorded_loop_single_draw": recorded_loop, "comparator": comp,
            "relnet_draws": r_draws, "loop_ctl_draws": ctl_draws, "se_diff": se, "margin": margin,
            "pass": rm >= comp - margin}


def judge_seed(rec):
    """rec['arms'] = arm records (R.arm_record + F_few) for relnet, fresh, loop_ctl, loop_base, plain;
    rec['draws'][arm][branch][kind] = [d0, d1, d2]; rec['overlap'] = support/panel overlap of the relnet run."""
    A = rec["arms"]
    p, lc, lb = A["relnet"], A["loop_ctl"], A["loop_base"]
    comp, comp_few = max(lc["F_eq"], lb["F_eq"]), max(lc["F_few"], lb["F_few"])
    loop_before = {k: max(lc["old"]["before"][k], lb["old"]["before"][k]) for k in KINDS}
    g = {
        "1_F_eq_ge_10_over_higher_of_two_loops": p["F_eq"] - comp >= NEEDS["F_eq"],
        "2_F_few_ge_5_over_higher_of_two_loops": p["F_few"] - comp_few >= NEEDS["F_few"],
        "3a_F_eq_ge_5_over_practised_plain": p["F_eq"] - A["plain"]["F_eq"] >= NEEDS["over_plain"],
        "3b_F_eq_ge_5_over_fresh_relnet": p["F_eq"] - A["fresh"]["F_eq"] >= NEEDS["over_fresh"],
        "4a_old_before_ge_190": all(p["old"]["before"][k] >= 190 for k in KINDS),
        "4b_old_before_within_6_of_higher_loop": all(p["old"]["before"][k] >= loop_before[k] - OLD_BEFORE_SLACK
                                                     for k in KINDS),
        "5_size_within_2pct_of_loop": abs(p["weights"] - lb["weights"]) / lb["weights"] <= .02,
        "0_support_pool_disjoint_from_panels": rec["overlap"] == 0,
    }
    sleeps = {}
    for b in BRANCHES:
        for k in KINDS:
            sleeps[f"{b}/{k}"] = sleep_gate(rec["draws"]["relnet"][b][k], rec["draws"]["loop_ctl"][b][k],
                                            lb["old"]["sleep_" + b][k])
    for b in BRANCHES:
        g[f"6_sleep_{b}_three_draw_mean_within_margin"] = all(sleeps[f"{b}/{k}"]["pass"] for k in KINDS)
    old_gates = [x for x in g if x.startswith(("4", "6"))]
    diffs = {"F_eq_relnet_minus_comparator": p["F_eq"] - comp, "F_few_relnet_minus_comparator": p["F_few"] - comp_few,
             "F_eq_relnet_minus_recorded_loop": p["F_eq"] - lb["F_eq"], "F_eq_relnet_minus_loop_ctl": p["F_eq"] - lc["F_eq"],
             "F_few_relnet_minus_recorded_loop": p["F_few"] - lb["F_few"], "F_few_relnet_minus_loop_ctl": p["F_few"] - lc["F_few"],
             "F_eq_relnet_minus_plain": p["F_eq"] - A["plain"]["F_eq"], "F_eq_relnet_minus_fresh": p["F_eq"] - A["fresh"]["F_eq"],
             "F_eq_loop_ctl_minus_recorded_loop": lc["F_eq"] - lb["F_eq"]}
    flags = {"above_comparator": p["F_eq"] > comp, "at_least_2_below_comparator": p["F_eq"] <= comp - LOSE_BAR,
             "old_gates_all_hold": all(g[x] for x in old_gates)}
    return g, diffs, flags, {"sleep_gate_detail": sleeps}


def verdict(seeds):
    """Returns (words, why, words_if_the_ANY_reading_were_used)."""
    S = {s: {"g": v[0], "flags": v[2]} for s, v in seeds.items()}
    passed = all(all(v["g"].values()) for v in S.values())
    lose_both = all(v["flags"]["at_least_2_below_comparator"] for v in S.values())
    gained = [v for v in S.values() if v["flags"]["above_comparator"]]
    every = bool(gained) and all(not v["flags"]["old_gates_all_hold"] for v in gained)  # X2: EVERY gaining seed
    anyb = bool(gained) and any(not v["flags"]["old_gates_all_hold"] for v in gained)   # the reading NOT used
    if passed:
        words = "PASS"
    elif lose_both or every:
        words = "REJECTED"
    else:
        words = "NOT PROMOTED (not shown)"
    legacy = "PASS" if passed else ("REJECTED" if (lose_both or anyb) else "NOT PROMOTED (not shown)")
    return words, {"both_seeds_at_least_2_below_comparator": lose_both,
                   "every_gaining_seed_breaks_an_old_kind_gate": every}, legacy


def sentence(words, seeds):
    d = {s: v[1] for s, v in seeds.items()}
    per = "; ".join(f"seed {s}: F_eq {v['F_eq_relnet_minus_comparator']:+.2f}, F_few {v['F_few_relnet_minus_comparator']:+.2f}"
                    for s, v in d.items())
    return (f"{words} on mazes (one held-out kind): the relation-net loop, at 12.1x the compute per maze update "
            f"(41.3 s against 3.42 s at one thread, TIMING-ESTIMATE.md). Differences over the higher of the recorded loop and "
            f"the loop re-run on the same machine, {per}. Non-wins read 'not shown' unless both seeds are 2 or more points below.")


def judge(recs):
    seeds = {s: judge_seed(r) for s, r in recs.items()}
    words, why, legacy = verdict(seeds)
    return {"seeds": {s: {"gates": v[0], "differences": v[1], "flags": v[2], "report_only": v[3],
                          "failing": [k for k, x in v[0].items() if not x]} for s, v in seeds.items()},
            "verdict": words, "rejected_because": why, "verdict_if_any_reading_were_used_NOT_USED": legacy,
            "sentence": sentence(words, seeds)}


# ------------------------------------------------------------------ real data
def arm_rec(adapt, scores):
    r = R.arm_record(adapt, scores)
    r["F_few"] = f_few(r["right9"])
    return r


def run_dirs(seed):
    return {"relnet": ART / "eq-runs" / f"relnet-pre-s{seed}", "fresh": ART / "eq-runs" / f"relnet-fresh-s{seed}",
            "loop_ctl": ART / "eq-runs" / f"loopctl-s{seed}",
            "plain": BASE / f"plain-s{seed}-pre", "loop_base": BASE / f"loop-s{seed}-pre"}


def draws_for(seed, folder, adapt):
    out = {}
    for b in BRANCHES:
        out[b] = {k: [adapt["sleep"][b]["old"][k]["right"]] for k in KINDS}
        for d in (1, 2):
            rec = json.loads((ART / "eq-runs" / "sleepdraws" / f"{folder}-s{seed}-k{b}-d{d}.json").read_text())
            for k in KINDS:
                out[b][k].append(rec["old"][k])
    return out


def real(kind):
    recs = {}
    for seed in SEEDS:
        arms, adapts = {}, {}
        for arm, path in run_dirs(seed).items():
            adapts[arm] = R.load(path / "adapt.json")
            scores = R.load(path / "holdout.json")["scores"] if kind == "holdout" else adapts[arm]["rungs"]
            arms[arm] = arm_rec(adapts[arm], scores)
        for arm in ("relnet", "fresh", "loop_ctl"):
            if arms[arm]["support_sha256"] != arms["plain"]["support_sha256"]:
                raise ValueError("support pool differs from the baseline's")
        recs[str(seed)] = {"arms": arms, "overlap": adapts["relnet"]["support_panel_overlap"],
                           "draws": {"relnet": draws_for(seed, "relnet", adapts["relnet"]),
                                     "loop_ctl": draws_for(seed, "loopctl", adapts["loop_ctl"])}}
    return recs


# ------------------------------------------------------------------ selftest
def fake_arm(shift, weights=1000, before=(200, 200), sleeps=(150, 110)):
    """Right-counts of 300 per rung; F_eq moves with shift (the few-example rungs move by 2x)."""
    base = {"1": 1, "4": 0, "16": 20, "64": 130, "256": 256, "1024": 262, "4096": 260, "16384": 270}
    right = {k: min(300, max(0, round(v + shift * 3 * (2 if k in FEW else 0.5)))) for k, v in base.items()}
    return {"F_eq": R.f_eq(right), "F_few": f_few(right), "right9": right, "weights": weights,
            "old": {"before": dict(zip(KINDS, before)),
                    "sleep_64": dict(zip(KINDS, sleeps)), "sleep_16384": dict(zip(KINDS, sleeps))}}


def fake_seed(gain, break_gate=False, noise=0, few_only_shift=None):
    """gain: relnet F_eq shift over both loops; break_gate: relnet far below the loops after sleeps;
    noise: one noisy sleep draw (d0 of the relnet) on sums."""
    lc, lb = fake_arm(0), fake_arm(-0.3)
    drop = 40 if break_gate else 0
    dl = {b: {"sums4": [150, 152, 148], "grids5": [110, 112, 108]} for b in BRANCHES}
    dr = {b: {"sums4": [150 - drop + noise, 150 - drop, 150 - drop], "grids5": [110, 111, 109]} for b in BRANCHES}
    relnet = fake_arm(gain, weights=1004)
    if few_only_shift is not None:                      # F_eq up by gain but F_few flat
        relnet["F_few"] = lc["F_few"] + few_only_shift
    return {"arms": {"relnet": relnet, "loop_ctl": lc, "loop_base": lb, "plain": fake_arm(-8), "fresh": fake_arm(-6)},
            "overlap": 0, "draws": {"relnet": dr, "loop_ctl": dl}}


def selftest(out):
    res, ok = {}, True
    j = judge({"0": fake_seed(9, True), "1": fake_seed(9, False)})   # (a) one gains+breaks, one gains+passes
    res["gains_and_breaks_vs_gains_and_passes"] = {
        "failing": {s: v["failing"] for s, v in j["seeds"].items()},
        "verdict_every_reading_USED": j["verdict"], "verdict_any_reading_NOT_USED": j["verdict_if_any_reading_were_used_NOT_USED"]}
    ok &= j["verdict"] == "NOT PROMOTED (not shown)" and j["verdict_if_any_reading_were_used_NOT_USED"] == "REJECTED"
    j2 = judge({"0": fake_seed(9, True), "1": fake_seed(9, True)})   # (b) both gain, both break
    res["both_gain_and_both_break"] = j2["verdict"]
    ok &= j2["verdict"] == "REJECTED"
    j3 = judge({"0": fake_seed(9), "1": fake_seed(9)})               # (c) both gain and pass
    res["both_gain_and_pass"] = {"verdict": j3["verdict"], "failing": {s: v["failing"] for s, v in j3["seeds"].items()}}
    ok &= j3["verdict"] == "PASS"
    j4 = judge({"0": fake_seed(-1), "1": fake_seed(1)})              # (d) small loss one seed / both lose >= 2
    j5 = judge({"0": fake_seed(-4), "1": fake_seed(-4)})
    res["small_loss_one_seed"], res["both_seeds_lose_by_2_or_more"] = j4["verdict"], j5["verdict"]
    ok &= j4["verdict"] == "NOT PROMOTED (not shown)" and j5["verdict"] == "REJECTED"
    j6 = judge({"0": fake_seed(9, noise=-12), "1": fake_seed(9, noise=-12)})   # (e) one noisy draw passes on the mean
    gate = j6["seeds"]["0"]["report_only"]["sleep_gate_detail"]["64/sums4"]
    res["noisy_single_draw"] = {"single_draw_gap": gate["relnet_draws"][0] - gate["loop_ctl_draws"][0],
                                "three_draw_gap": round(gate["relnet_mean"] - gate["loop_ctl_mean"], 2),
                                "margin": round(gate["margin"], 2), "passes": gate["pass"], "verdict": j6["verdict"]}
    ok &= gate["pass"] and j6["verdict"] == "PASS" and res["noisy_single_draw"]["single_draw_gap"] < -6
    j7 = judge({"0": fake_seed(9, few_only_shift=2), "1": fake_seed(9, few_only_shift=2)})   # (f) F_few row required
    res["f_eq_up_but_f_few_flat"] = {"verdict": j7["verdict"], "failing": {s: v["failing"] for s, v in j7["seeds"].items()}}
    ok &= j7["verdict"] == "NOT PROMOTED (not shown)" and all("2_F_few_ge_5_over_higher_of_two_loops" in v["failing"]
                                                              for v in j7["seeds"].values())
    hi = fake_seed(9)
    hi["arms"]["loop_base"] = fake_arm(9.5)                           # (g) comparator is the HIGHER of the two loops
    j8 = judge({"0": hi, "1": fake_seed(9)})
    res["comparator_is_higher_loop"] = {"seed0_F_eq_diff": round(j8["seeds"]["0"]["differences"]["F_eq_relnet_minus_comparator"], 2),
                                        "failing_seed0": j8["seeds"]["0"]["failing"]}
    ok &= "1_F_eq_ge_10_over_higher_of_two_loops" in j8["seeds"]["0"]["failing"]
    res["sentence_example"] = j["sentence"]
    ok &= "12.1x the compute" in j["sentence"] and " on mazes" in j["sentence"]                    # (h) R3/R4 wording
    res["all_expected"] = ok
    res["note"] = "fake numbers; checks the wording and the arithmetic of the marks, not any model"
    out.write_text(json.dumps(res, indent=2, sort_keys=True))
    print(json.dumps(res, indent=1))
    if not ok:
        raise SystemExit("selftest failed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("selftest", "dev", "holdout"))
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest(ART / "add1-selftest.json")
    elif a.cmd == "dev":
        recs = real("dev")
        table = {s: {arm: {"F_eq": r["F_eq"], "F_few": r["F_few"], "right9": r["right9"]} for arm, r in v["arms"].items()}
                 for s, v in recs.items()}
        (ART / "race-dev-add1.json").write_text(json.dumps(table, indent=2, sort_keys=True))
        for s, arms in table.items():
            print(s, {arm: (round(r["F_eq"], 2), round(r["F_few"], 2)) for arm, r in arms.items()})
    else:
        res = judge(real("holdout"))
        (ART / "race-holdout-add1.json").write_text(json.dumps(res, indent=2, sort_keys=True))
        print(json.dumps({"verdict": res["verdict"], "why": res["rejected_because"],
                          "failing": {s: v["failing"] for s, v in res["seeds"].items()}, "sentence": res["sentence"]}, indent=1))
