#!/usr/bin/env python3
"""Apply PASSMARKS.md as amended by ADDENDUM-2.md to the raw harness JSON (patch race, equal-practice ruler).

  selftest -> add2-selftest.json   two fake seeds, no torch, no raw files needed
  dev      -> race-dev-add2.json   dev tables incl. F_few and the writes-off arm (no gate, no verdict)
  holdout  -> race-holdout-add2.json  every mark per seed and the verdict words

Replaces scripts/claude_patch_eq_report.py's verdict (that file is untouched). Seeds are never pooled.
Reads only adapt.json / holdout.json / sleepdraws/*.json files.
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

ART, KINDS, SEEDS = R.ART, R.KINDS, R.SEEDS
FEW = ("1", "4", "16", "64")
BRANCHES = ("64", "16384")
MARGIN_FLOOR = 6            # X1: margin = max(6, 2 x SE)
NEEDS = {"F_eq_over_comparator": 10, "F_few_over_comparator": 5, "over_plain": 5, "over_fresh": 5}
LOSE_BAR = 2                # X4: "REJECTED by losing" needs both seeds at least 2 points below
WRITES_BAR = 5              # P2 wording rule, report only
COMPUTE_NOTE = ("at 1.5x the compute (each write runs every puzzle to its own stop: measured 4.7 s per maze batch "
                "against 3.1 s for the loop, DESIGN.md; write rounds are in adapt.json)")


def f_few(counts):
    return sum(100 * counts[k] / 300 for k in FEW) / len(FEW)


def mean_sd(xs):
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def sleep_gate(p_draws, l_draws):
    """X1: patch three-draw mean must be at least the loop's three-draw mean minus max(6, 2 x SE_diff)."""
    (pm, ps), (lm, ls) = mean_sd(p_draws), mean_sd(l_draws)
    se = math.sqrt(ps ** 2 / len(p_draws) + ls ** 2 / len(l_draws))
    margin = max(MARGIN_FLOOR, 2 * se)
    return {"patch_mean": pm, "loop_ep_mean": lm, "patch_draws": p_draws, "loop_ep_draws": l_draws,
            "se_diff": se, "margin": margin, "pass": pm >= lm - margin}


def judge_seed(rec):
    """rec: arm records (R.arm_record + F_few) and rec['draws'][arm][branch][kind] = [d0, d1, d2]."""
    A = rec["arms"]
    p, l, lb = A["patch"], A["loop_ep"], A["loop_base"]
    comp = max(l["F_eq"], lb["F_eq"])
    comp_few = max(l["F_few"], lb["F_few"])
    g = {
        "1_F_eq_ge_10_over_higher_of_loop_ep_and_baseline_loop": p["F_eq"] - comp >= NEEDS["F_eq_over_comparator"],
        "2_F_few_ge_5_over_higher_of_loop_ep_and_baseline_loop": p["F_few"] - comp_few >= NEEDS["F_few_over_comparator"],
        "3a_F_eq_ge_5_over_plain": p["F_eq"] - A["plain"]["F_eq"] >= NEEDS["over_plain"],
        "3b_F_eq_ge_5_over_fresh": p["F_eq"] - A["fresh"]["F_eq"] >= NEEDS["over_fresh"],
        "4a_old_before_ge_190": all(p["old"]["before"][k] >= 190 for k in KINDS),
        "4b_old_before_within_6_of_loop_ep": all(p["old"]["before"][k] >= l["old"]["before"][k] - 6 for k in KINDS),
        "5_size_within_2pct_of_loop_ep": abs(p["weights"] - l["weights"]) / l["weights"] <= .02,
    }
    sleeps = {}
    for b in BRANCHES:
        for k in KINDS:
            sleeps[f"{b}/{k}"] = sleep_gate(rec["draws"]["patch"][b][k], rec["draws"]["loop_ep"][b][k])
    for b in BRANCHES:
        g[f"6_sleep_{b}_three_draw_mean_within_margin"] = all(sleeps[f"{b}/{k}"]["pass"] for k in KINDS)
    old_gates = [x for x in g if x.startswith(("4", "6"))]
    diffs = {"F_eq_patch_minus_comparator": p["F_eq"] - comp, "F_few_patch_minus_comparator": p["F_few"] - comp_few,
             "F_eq_patch_minus_loop_ep": p["F_eq"] - l["F_eq"], "F_eq_patch_minus_baseline_loop": p["F_eq"] - lb["F_eq"],
             "F_few_patch_minus_loop_ep": p["F_few"] - l["F_few"],
             "F_eq_patch_minus_plain": p["F_eq"] - A["plain"]["F_eq"], "F_eq_patch_minus_fresh": p["F_eq"] - A["fresh"]["F_eq"],
             "F_eq_loop_ep_minus_baseline_loop": l["F_eq"] - lb["F_eq"]}
    flags = {"above_comparator": p["F_eq"] > comp, "at_least_2_below_comparator": p["F_eq"] <= comp - LOSE_BAR,
             "old_gates_all_hold": all(g[x] for x in old_gates)}
    report_only = {"sleep_gate_detail": sleeps}
    if "writesoff" in A:
        w = A["writesoff"]
        report_only["patch_minus_writes_off"] = {"F_eq": p["F_eq"] - w["F_eq"], "F_few": p["F_few"] - w["F_few"]}
    kept = rec["draws"].get("patch_kept")
    if kept:
        report_only["patch_old_after_sleep_patch_kept"] = kept
    return g, diffs, flags, report_only


def verdict(seeds):
    """seeds: {seed: judge_seed(...) output}. Returns (words, why, legacy_any_reading_words)."""
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
    per = "; ".join(f"seed {s}: F_eq {v['F_eq_patch_minus_comparator']:+.2f}, F_few {v['F_few_patch_minus_comparator']:+.2f}"
                    for s, v in d.items())
    return (f"{words}: the clip-on patch, {COMPUTE_NOTE}. Differences over the higher of the loop with episodes and "
            f"the baseline loop, {per}. Non-wins read 'not shown' unless both seeds are 2 or more points below.")


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


def draws_for(seed, arm_key, adapt):
    """[draw 0 (the ladder's own sleep), draw 1, draw 2] per branch and kind, and patch-kept scores."""
    name = {"patch": "patch", "loop_ep": "loop_ep"}[arm_key]
    out, kept = {}, {}
    for b in BRANCHES:
        out[b] = {k: [adapt["sleep"][b]["old"][k]["right"]] for k in KINDS}
        for d in (1, 2):
            f = ART / "eq-runs" / "sleepdraws" / f"{name}-s{seed}-k{b}-d{d}.json"
            rec = json.loads(f.read_text())
            for k in KINDS:
                out[b][k].append(rec["old"][k])
            if rec.get("old_patch_kept_report_only"):
                kept.setdefault(b, []).append(rec["old_patch_kept_report_only"])
    return out, kept


def real(kind):
    recs = {}
    for seed in SEEDS:
        r = R.runs(seed)
        r["writesoff"] = ART / "eq-runs" / f"writesoff-s{seed}"
        arms, adapts = {}, {}
        for arm, path in r.items():
            if arm == "writesoff" and not (path / ("holdout.json" if kind == "holdout" else "adapt.json")).exists():
                continue
            adapts[arm] = R.load(path / "adapt.json")
            scores = R.load(path / "holdout.json")["scores"] if kind == "holdout" else adapts[arm]["rungs"]
            arms[arm] = arm_rec(adapts[arm], scores)
        for arm in ("patch", "fresh", "loop_ep"):
            if arms[arm]["support_sha256"] != arms["plain"]["support_sha256"]:
                raise ValueError("support pool differs from the baseline's")
        pd, pk = draws_for(seed, "patch", adapts["patch"])
        ld, _ = draws_for(seed, "loop_ep", adapts["loop_ep"])
        recs[str(seed)] = {"arms": arms, "draws": {"patch": pd, "loop_ep": ld, "patch_kept": pk}}
    return recs


# ------------------------------------------------------------------ selftest
def fake_arm(f_eq_shift, weights=1000, before=(200, 200)):
    """Right-counts of 300 per rung built so F_eq moves with f_eq_shift (few-example rungs move by 2x)."""
    base = {"1": 1, "4": 0, "16": 20, "64": 130, "256": 256, "1024": 262, "4096": 260, "16384": 270}
    right = {k: min(300, max(0, round(v + (f_eq_shift * 3 * (2 if k in FEW else 0.5)) / 1))) for k, v in base.items()}
    return {"F_eq": R.f_eq(right), "F_few": f_few(right), "right9": right, "weights": weights,
            "old": {"before": dict(zip(KINDS, before))}}


def fake_seed(gain, break_gate, sleep_noise=(0, 0, 0)):
    """gain: patch F_eq shift over both loops; break_gate: patch is far below the loop after sleeps."""
    loop = fake_arm(0)
    draws_l = {b: {"sums4": [150, 150 + sleep_noise[1], 150 + sleep_noise[2]], "grids5": [110, 112, 108]} for b in BRANCHES}
    drop = 40 if break_gate else 0
    draws_p = {b: {"sums4": [150 - drop + sleep_noise[0], 150 - drop, 150 - drop], "grids5": [110, 111, 109]} for b in BRANCHES}
    return {"arms": {"patch": fake_arm(gain, weights=1004), "loop_ep": loop, "loop_base": fake_arm(-0.3),
                     "plain": fake_arm(-8), "fresh": fake_arm(-6), "writesoff": fake_arm(gain - 4)},
            "draws": {"patch": draws_p, "loop_ep": draws_l}}


def selftest(out):
    res, ok = {}, True
    # Scenario 1: seed 0 gains and breaks a gate, seed 1 gains and passes. "every" and "any" must differ.
    j = judge({"0": fake_seed(9, True), "1": fake_seed(9, False)})
    res["gains_and_breaks_vs_gains_and_passes"] = {
        "F_eq_diffs": {s: round(v["differences"]["F_eq_patch_minus_comparator"], 2) for s, v in j["seeds"].items()},
        "failing": {s: v["failing"] for s, v in j["seeds"].items()},
        "verdict_every_reading_USED": j["verdict"],
        "verdict_any_reading_NOT_USED": j["verdict_if_any_reading_were_used_NOT_USED"]}
    ok &= j["verdict"] == "NOT PROMOTED (not shown)" and j["verdict_if_any_reading_were_used_NOT_USED"] == "REJECTED"
    # Scenario 2: both seeds gain and both break -> REJECTED under every.
    j2 = judge({"0": fake_seed(9, True), "1": fake_seed(9, True)})
    res["both_gain_and_both_break"] = j2["verdict"]
    ok &= j2["verdict"] == "REJECTED" and j2["rejected_because"]["every_gaining_seed_breaks_an_old_kind_gate"]
    # Scenario 3: both gain and pass every mark -> PASS.
    j3 = judge({"0": fake_seed(9, False), "1": fake_seed(9, False)})
    res["both_gain_and_pass"] = {"verdict": j3["verdict"], "failing": {s: v["failing"] for s, v in j3["seeds"].items()}}
    ok &= j3["verdict"] == "PASS"
    # Scenario 4: X4. One seed a hair below, one above: not shown. Both 2+ below: REJECTED.
    j4 = judge({"0": fake_seed(-1, False), "1": fake_seed(1, False)})
    j5 = judge({"0": fake_seed(-4, False), "1": fake_seed(-4, False)})
    res["small_loss_one_seed"] = j4["verdict"]
    res["both_seeds_lose_by_2_or_more"] = j5["verdict"]
    ok &= j4["verdict"] == "NOT PROMOTED (not shown)" and j5["verdict"] == "REJECTED"
    # Scenario 5: X1. A patch equal to the loop but with one noisy sleep draw (-12 on sums) passes on the mean.
    j6 = judge({"0": fake_seed(9, False, (-12, 0, 0)), "1": fake_seed(9, False, (-12, 0, 0))})
    gate = j6["seeds"]["0"]["report_only"]["sleep_gate_detail"]["64/sums4"]
    res["noisy_single_draw"] = {"single_draw_gap": gate["patch_draws"][0] - gate["loop_ep_draws"][0],
                                "three_draw_gap": round(gate["patch_mean"] - gate["loop_ep_mean"], 2),
                                "margin": round(gate["margin"], 2), "passes": gate["pass"], "verdict": j6["verdict"]}
    ok &= gate["pass"] and j6["verdict"] == "PASS" and res["noisy_single_draw"]["single_draw_gap"] < -6
    # Scenario 6: P1/X3. Patch beats the baseline loop by 10 F_eq but not by 5 F_few -> mark 2 fails; sentence has 1.5x.
    res["sentence_example"] = j["sentence"]
    ok &= "1.5x the compute" in j["sentence"]
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
        selftest(ART / "add2-selftest.json")
    elif a.cmd == "dev":
        recs = real("dev")
        table = {s: {arm: {"F_eq": r["F_eq"], "F_few": r["F_few"], "right9": r["right9"]} for arm, r in v["arms"].items()}
                 for s, v in recs.items()}
        (ART / "race-dev-add2.json").write_text(json.dumps(table, indent=2, sort_keys=True))
        for s, arms in table.items():
            print(s, {arm: (round(r["F_eq"], 2), round(r["F_few"], 2)) for arm, r in arms.items()})
    else:
        res = judge(real("holdout"))
        (ART / "race-holdout-add2.json").write_text(json.dumps(res, indent=2, sort_keys=True))
        print(json.dumps({"verdict": res["verdict"], "why": res["rejected_because"],
                          "failing": {s: v["failing"] for s, v in res["seeds"].items()}, "sentence": res["sentence"]}, indent=1))
