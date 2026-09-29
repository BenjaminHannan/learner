#!/usr/bin/env python3
"""Pond marks: reads the baseline, plain and pond-arm dev records and applies artifacts/claude-dir-pond-20260928/PASSMARKS.md.

    python -B scripts/claude_dir_pond_marks.py selftest
    python -B scripts/claude_dir_pond_marks.py judge [--out FILE] [--arms a,b,c,z]

No torch: it only reads `adapt.json` files (dev 9x9 counts). PASSMARKS.md wins if this script and the page disagree.
Helpers that are the same as H12's (loading, F scores, validity V4/V5, noise) are imported from claude_dir_h12_marks.py unedited.
The holdout is never read here.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h12_marks as H  # noqa: E402

ROOT = H.ROOT
BASE_PAT = H.BASE_PAT
PLAIN_PAT = "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre/adapt.json"
ARM_PAT = "artifacts/claude-dir-pond-20260928/eq-runs/pond-{arm}-pre-s{{seed}}/adapt.json"
ARMS = ("a", "b", "c", "z")
LAMBDA = {"a": 0.001, "b": 0.004, "c": 0.016, "z": 0.0}
JUDGED, RUNGS, FEW, N = H.JUDGED, H.RUNGS, H.FEW, H.N
CAP_BAR, NEED_S1, NEED_S2, STOP_TOL = 150, 4, 4, 6          # PASSMARKS: S1, S2
BAR = {"F_eq": 7.0, "F_few": 8.5}                             # PASSMARKS: A1, A2 (same as H12: 2 x noise SD 3.33, 4.17)
PLAIN_MARGIN = 10.0                                           # PASSMARKS: P
EPS = 1e-9


def stop_marks(run):
    rungs, n1, n2 = {}, 0, 0
    for k in JUDGED:
        p = H.p9(run, k)
        s1 = p["cap_hits"] < CAP_BAR
        s2 = p["right"] >= p["fixed_right"] - STOP_TOL
        n1 += s1
        n2 += s2
        rungs[str(k)] = {"right": p["right"], "fixed_right": p["fixed_right"], "cap_hits": p["cap_hits"],
                         "mean_rounds": round(p["mean_rounds"], 3), "S1": s1, "S2": s2}
    return {"rungs": rungs, "s1_rungs_passing": n1, "S1": n1 >= NEED_S1, "s1_all5": n1 == len(JUDGED),
            "s2_rungs_passing": n2, "S2": n2 >= NEED_S2}


def accuracy_rows(base, arm, plain):
    """A1, A2, P per seed and overall; body reading report-only."""
    out = {}
    for name, key in (("A1", "F_eq"), ("A2", "F_few")):
        deltas = []
        for s in (0, 1):
            fb, fa = H.f_all(base[s])[key], H.f_all(arm[s])[key]
            deltas.append(fa["learned"] - max(fb["learned"], fb["fixed"]))
        out[name] = {"score": key, "bar": BAR[key], "delta_by_seed": [round(d, 3) for d in deltas],
                     "pass": all(d >= -BAR[key] - EPS for d in deltas)}
    margins = [H.f_all(arm[s])["F_eq"]["learned"] - H.f_all(plain[s])["F_eq"]["learned"] for s in (0, 1)]
    out["P"] = {"margin_over_plain_by_seed": [round(m, 3) for m in margins], "need": PLAIN_MARGIN,
                "pass": all(m >= PLAIN_MARGIN - EPS for m in margins)}
    body = {}
    for key in ("F_eq", "F_few"):
        d = [H.f_all(arm[s])[key]["fixed"] - H.f_all(base[s])[key]["fixed"] for s in (0, 1)]
        body[key] = {"delta_fixed16_by_seed": [round(x, 3) for x in d],
                     "BODY MOVED": any(abs(x) > BAR[key] + EPS for x in d)}
    out["body_reading"] = body
    return out


def arm_word(marks, rows):
    s1 = [marks[s]["S1"] for s in (0, 1)]
    s2 = [marks[s]["S2"] for s in (0, 1)]
    if all(s1):
        return "PONDER WORKS" if (all(s2) and rows["A1"]["pass"] and rows["A2"]["pass"] and rows["P"]["pass"]) else "FIRES BUT HURTS"
    if not any(s1):
        return "WRONG"
    return "NOT SHOWN"


def overall(words):
    """words: {arm: word} for arms a, b, c. Control z is read separately."""
    w = [words[a] for a in ("a", "b", "c") if a in words]
    if any(x == "PONDER WORKS" for x in w):
        ok = [a for a in ("a", "b", "c") if words.get(a) == "PONDER WORKS"]
        text = f"SHOWN (recommended lambda: the smallest passing arm, {ok[0]})"
        if len(ok) == 1 and len(w) == 3:
            text += "; ISOLATED (only one arm passes)"
        return text
    if len(w) == 3 and all(x == "WRONG" for x in w):
        return "PROVEN WRONG IN THIS FORM"
    return "NOT SHOWN"


def judge(arms, out=None):
    base = {s: H.load(BASE_PAT, s) for s in (0, 1)}
    plain = {s: H.load(PLAIN_PAT, s) for s in (0, 1)}
    result = {"baseline_reference": {str(s): dict(stop_marks(base[s]), F=H.f_all(base[s])) for s in (0, 1)},
              "plain_F_eq": {str(s): H.f_all(plain[s])["F_eq"]["learned"] for s in (0, 1)},
              "noise": H.noise(base), "arms": {}}
    words = {}
    for a in arms:
        pat = ARM_PAT.format(arm=a)
        try:
            run = {s: H.load(pat, s) for s in (0, 1)}
        except FileNotFoundError as e:
            result["arms"][a] = {"lambda": LAMBDA[a], "word": "NOT RUN", "missing": str(e)}
            continue
        ok, bad = H.validity(base, run)
        if not ok:
            result["arms"][a] = {"lambda": LAMBDA[a], "word": "INVALID", "failures": bad}
            continue
        marks = {s: stop_marks(run[s]) for s in (0, 1)}
        rows = accuracy_rows(base, run, plain)
        word = arm_word(marks, rows)
        words[a] = word
        result["arms"][a] = {"lambda": LAMBDA[a], "word": word, "seeds": {str(s): dict(marks[s], F=H.f_all(run[s])) for s in (0, 1)},
                             "rows": rows, "report_only": {str(s): H.report_only(run[s]) for s in (0, 1)}}
    result["overall"] = overall(words)
    z = result["arms"].get("z")
    if z and "seeds" in z and z["word"] in ("PONDER WORKS", "FIRES BUT HURTS") and all(z["seeds"][s]["S1"] for s in ("0", "1")):
        result["control_z"] = "PENALTY NOT NEEDED (the label-free halting objective alone fires the stop)"
    text = json.dumps(result, indent=2, sort_keys=True)
    if out:
        Path(out).write_text(text + "\n")
    print(text)
    return result


# ---- selftest ---------------------------------------------------------------------------

def _good(run, cap=20, dr=-2):
    run = copy.deepcopy(run)
    for k in JUDGED:
        p = H.p9(run, k)
        right = max(p["right"], 200)
        p.update(right=right, fixed_right=right - dr, cap_hits=cap, mean_rounds=8.0)
    for k in RUNGS:
        p = H.p9(run, k)
        p["right"] = max(p["right"], 60)
    return run


def selftest():
    base = {s: H.load(BASE_PAT, s) for s in (0, 1)}
    plain = {s: H.load(PLAIN_PAT, s) for s in (0, 1)}
    # 1. baseline references written in PASSMARKS.md
    m = {s: stop_marks(base[s]) for s in (0, 1)}
    assert [m[s]["rungs"][str(k)]["cap_hits"] for s in (0, 1) for k in JUDGED] == [300, 300, 300, 300, 143, 265, 300, 61, 196, 194]
    assert (m[0]["s1_rungs_passing"], m[1]["s1_rungs_passing"]) == (1, 1) and not m[0]["S1"] and not m[1]["S1"]
    assert [p for p in (H.p9(base[0], k)["right"] for k in JUDGED)] == [126, 263, 275, 256, 286]
    assert [p for p in (H.p9(base[1], k)["fixed_right"] for k in JUDGED)] == [171, 268, 220, 288, 259]
    pf = {s: H.f_all(plain[s])["F_eq"]["learned"] for s in (0, 1)}
    assert (round(pf[0], 2), round(pf[1], 2)) == (34.04, 32.62), pf         # 32.625 rounds to 32.62 in python; PASSMARKS says 32.63
    fb = {s: H.f_all(base[s])["F_eq"]["learned"] - pf[s] for s in (0, 1)}
    assert (round(fb[0], 1), round(fb[1], 1)) == (17.2, 19.0), fb           # PASSMARKS: baseline clears P by 17.2 and 19.0
    nz = H.noise(base)
    assert (nz["F_eq"]["sd_two_run_diff_points"], nz["F_few"]["sd_two_run_diff_points"]) == (3.33, 4.17)
    assert (nz["F_eq"]["bar_rounded_up_to_half"], nz["F_few"]["bar_rounded_up_to_half"]) == (BAR["F_eq"], BAR["F_few"])
    # 2. boundaries
    def one(cap):
        run = copy.deepcopy(base[0])
        for k in JUDGED:
            H.p9(run, k)["cap_hits"] = cap
        return stop_marks(run)
    assert one(149)["S1"] and one(149)["s1_all5"] and not one(150)["S1"]
    r = copy.deepcopy(base[0])
    for k in JUDGED[:3]:
        H.p9(r, k)["cap_hits"] = 149
    assert stop_marks(r)["s1_rungs_passing"] == 4                                                  # 3 set + k=16384 already 143 in seed 0
    assert stop_marks(r)["S1"]
    r = copy.deepcopy(base[1])
    for k in JUDGED[:2]:
        H.p9(r, k)["cap_hits"] = 149
    assert stop_marks(r)["s1_rungs_passing"] == 3 and not stop_marks(r)["S1"]                      # 149, 149, 61: three of five
    s2 = copy.deepcopy(base[0])
    for k in JUDGED[:4]:
        p = H.p9(s2, k)
        p["right"] = p["fixed_right"] - 6
    assert stop_marks(s2)["s2_rungs_passing"] == 5
    H.p9(s2, 64)["right"] = H.p9(s2, 64)["fixed_right"] - 7
    H.p9(s2, 256)["right"] = H.p9(s2, 256)["fixed_right"] - 7
    assert stop_marks(s2)["s2_rungs_passing"] == 3 and not stop_marks(s2)["S2"]
    # 3. words
    good = {s: _good(base[s]) for s in (0, 1)}
    mk = {s: stop_marks(good[s]) for s in (0, 1)}
    rows = accuracy_rows(base, good, plain)
    assert mk[0]["S1"] and mk[1]["S1"] and mk[0]["S2"] and rows["A1"]["pass"] and rows["A2"]["pass"] and rows["P"]["pass"], (mk, rows)
    assert arm_word(mk, rows) == "PONDER WORKS"
    assert arm_word({0: {"S1": False, "S2": True}, 1: {"S1": False, "S2": True}}, rows) == "WRONG"
    assert arm_word({0: {"S1": True, "S2": True}, 1: {"S1": False, "S2": True}}, rows) == "NOT SHOWN"
    bad_s2 = {0: {"S1": True, "S2": False}, 1: {"S1": True, "S2": True}}
    assert arm_word(bad_s2, rows) == "FIRES BUT HURTS"
    # A1 / A2 / P each break the word on their own
    hurt = copy.deepcopy(base)
    for k in RUNGS:                                    # seed 1: 30 counts (10 points) below the baseline's learned read on every rung
        hurt[1]["rungs"][str(k)]["9"]["right"] -= 30
    rh = accuracy_rows(base, hurt, plain)
    assert not rh["A1"]["pass"] and arm_word(mk, rh) == "FIRES BUT HURTS"
    for drop, expect in ((168, True), (169, False)):          # F_eq = sum of right / 24: 168 counts is exactly 7.0 points
        near = copy.deepcopy(base)
        near[0]["rungs"]["16384"]["9"]["right"] -= drop
        assert accuracy_rows(base, near, plain)["A1"]["pass"] is expect, drop
    # P: an arm no better than the plain net fails P whatever else it does
    weak = copy.deepcopy(good)
    for s in (0, 1):
        for k in RUNGS:
            p = H.p9(weak[s], k)
            p["right"] = H.p9(plain[s], k)["right"]
    assert not accuracy_rows(base, weak, plain)["P"]["pass"]
    # overall
    assert overall({"a": "WRONG", "b": "WRONG", "c": "WRONG"}) == "PROVEN WRONG IN THIS FORM"
    assert overall({"a": "WRONG", "b": "PONDER WORKS", "c": "WRONG"}).startswith("SHOWN (recommended lambda: the smallest passing arm, b)")
    assert "ISOLATED" in overall({"a": "WRONG", "b": "PONDER WORKS", "c": "WRONG"})
    assert overall({"a": "PONDER WORKS", "b": "PONDER WORKS", "c": "NOT SHOWN"}).count("ISOLATED") == 0
    assert overall({"a": "WRONG", "b": "NOT SHOWN", "c": "WRONG"}) == "NOT SHOWN"
    assert overall({"a": "FIRES BUT HURTS", "b": "WRONG", "c": "WRONG"}) == "NOT SHOWN"
    # validity comes from H12's (its own selftest covers each failure); check it flags a real mismatch here
    ok, bad = H.validity(base, base)
    assert ok
    broken = copy.deepcopy(base)
    broken[0]["weights"] += 1
    assert not H.validity(base, broken)[0]
    print(json.dumps({"selftest": "ok", "baseline_s1_rungs": [m[0]["s1_rungs_passing"], m[1]["s1_rungs_passing"]],
                      "baseline_over_plain": [round(fb[0], 2), round(fb[1], 2)], "noise_sd": [nz["F_eq"]["sd_two_run_diff_points"], nz["F_few"]["sd_two_run_diff_points"]]}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "judge"))
    p.add_argument("--arms", default=",".join(ARMS))
    p.add_argument("--out")
    a = p.parse_args()
    selftest() if a.cmd == "selftest" else judge(a.arms.split(","), a.out)


if __name__ == "__main__":
    main()
