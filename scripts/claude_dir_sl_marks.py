#!/usr/bin/env python3
"""SL marks (artifacts/claude-dir-sl-20260928/PASSMARKS.md Part C). Pure python.

    judge     read the two baseline and two variant adapt.json (and the two new source.json) and print every number and the words
    selftest  reproduce the baseline numbers quoted in PASSMARKS.md from the raw baseline files, and the four verdict words on synthetic records

If this script and PASSMARKS.md ever disagree, PASSMARKS.md wins.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
FEW = (1, 4, 16, 64)
JUDGED = (64, 256, 1024, 4096, 16384)
N = 300
MIN_RIGHT, CAP_BAR, SLACK = 31, 150, 6
BAR_EQ, BAR_FEW = 7.0, 8.5
BASE = "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre/adapt.json"
VAR = "artifacts/claude-dir-sl-20260928/eq-runs/sl-pre-s{seed}/adapt.json"
SRC = "artifacts/claude-dir-sl-20260928/sources/sl-source-s{seed}/source.json"
H12 = "artifacts/claude-dir-h12-stop-20260928/eq-runs/h12-pre-s{seed}/adapt.json"


def rung(adapt, k):
    r = adapt["rungs"][str(k)]["9"]
    return {"right": r["right"], "fixed_right": r["fixed_right"], "mean_rounds": r["mean_rounds"], "cap_hits": r["cap_hits"]}


def f_score(adapt, ks, key):
    return sum(100 * adapt["rungs"][str(k)]["9"][key] / N for k in ks) / len(ks)


def f1_rung(r):
    return r["right"] >= MIN_RIGHT and r["cap_hits"] <= CAP_BAR


def f2_rung(r):
    return r["right"] >= r["fixed_right"] - SLACK


def seed_marks(adapt):
    rows = {str(k): rung(adapt, k) for k in RUNGS}
    f1 = [k for k in JUDGED if f1_rung(rows[str(k)])]
    f2 = [k for k in JUDGED if f2_rung(rows[str(k)])]
    return {"rungs": rows, "f1_rungs_passing": f1, "f2_rungs_passing": f2,
            "F1": len(f1) >= 4, "F2": len(f2) == len(JUDGED),
            "F": {"F_eq": {"learned": f_score(adapt, RUNGS, "right"), "fixed": f_score(adapt, RUNGS, "fixed_right")},
                  "F_few": {"learned": f_score(adapt, FEW, "right"), "fixed": f_score(adapt, FEW, "fixed_right")}}}


def validity(adapt, base, source):
    """V1 for the new source net, V4 for the harness run. Returns (list of failures)."""
    bad = []
    if source is not None:
        old = source["old"]
        if not (old["sums4"]["right"] >= 190 and old["grids5"]["right"] >= 190 and source["gradient_check"]["nonzero_all"]):
            bad.append("V1: source failed sums4/grids5 >= 190 of 200 or the gradient check")
    for key in ("optimizer_updates_per_rung", "weights", "persistent_coefficients", "fixed_depth", "lr", "support_sha256",
                "rung_batches", "batch_size"):
        if adapt.get(key) != base.get(key):
            bad.append(f"V4: {key} is {adapt.get(key)!r}, the baseline's is {base.get(key)!r}")
    if adapt.get("optimizer_updates_per_rung") != 2048 or adapt.get("weights") != 1645726:
        bad.append("V4: updates per rung must be 2048 and weights 1645726")
    return bad


def word_acc(deltas, bar):
    if all(d >= bar for d in deltas):
        return "HELPS"
    if all(d <= -bar for d in deltas):
        return "HURTS"
    return "NOT SEPARABLE FROM NOISE"


def verdict(per_seed, invalid):
    if len(invalid) == 2:
        return "INVALID"
    if invalid:
        return "NOT SHOWN (one seed INVALID-SOURCE or INVALID-START; a verdict needs both seeds)"
    f1 = [m["F1"] for m in per_seed.values()]
    f2 = [m["F2"] for m in per_seed.values()]
    n1 = [len(m["f1_rungs_passing"]) for m in per_seed.values()]
    if all(f1):
        return "STOP FIRES WITHOUT LABELS" if all(f2) else "FIRES BUT HURTS"
    if not any(f1) and all(n <= 2 for n in n1):
        return "WRONG"
    return "NOT SHOWN"


def judge(base, var, src, h12=None):
    out = {"seeds": {}, "invalid": {}}
    marks = {}
    for s in (0, 1):
        bad = validity(var[s], base[s], src.get(s))
        if src.get(s) is None:
            bad.append("V1: source.json missing")
        out["invalid"][str(s)] = bad
        marks[s] = seed_marks(var[s])
        out["seeds"][str(s)] = {"variant": marks[s], "baseline": seed_marks(base[s])}
    invalid = [s for s in (0, 1) if out["invalid"][str(s)]]
    out["verdict"] = verdict(marks, invalid)
    acc = {}
    for name, ks, bar in (("F_eq", RUNGS, BAR_EQ), ("F_few", FEW, BAR_FEW)):
        deltas, body = [], []
        for s in (0, 1):
            b = out["seeds"][str(s)]["baseline"]["F"][name]
            ctl = max(b["learned"], b["fixed"])                      # the higher of the baseline's two reads
            deltas.append(marks[s]["F"][name]["learned"] - ctl)
            body.append(marks[s]["F"][name]["fixed"] - b["fixed"])
        acc[name] = {"bar": bar, "delta_learned_by_seed": [round(d, 2) for d in deltas], "word": word_acc(deltas, bar),
                     "delta_fixed16_by_seed": [round(d, 2) for d in body], "body_word": word_acc(body, bar)}
    out["accuracy"] = acc
    out["recommend"] = out["verdict"] == "STOP FIRES WITHOUT LABELS" and all(a["word"] != "HURTS" for a in acc.values())
    if h12:
        out["h12_report_only"] = {str(s): {str(k): rung(h12[s], k) for k in JUDGED} for s in h12}
    return out


def noise_from_baseline(base):
    d = [base[0]["rungs"][str(k)]["9"]["right"] - base[1]["rungs"][str(k)]["9"]["right"] for k in RUNGS]
    rms = lambda xs: math.sqrt(sum(x * x for x in xs) / len(xs))
    sd_eq = rms(d) / math.sqrt(len(d)) / 3.0
    sd_few = rms(d[:4]) / math.sqrt(4) / 3.0
    return {"diffs": d, "rms_eq_counts": rms(d), "rms_few_counts": rms(d[:4]), "sd_eq_points": sd_eq, "sd_few_points": sd_few}


def load(pattern, seeds=(0, 1), optional=False):
    out = {}
    for s in seeds:
        p = ROOT / pattern.format(seed=s)
        if p.exists():
            out[s] = json.loads(p.read_text())
        elif not optional:
            raise FileNotFoundError(str(p))
    return out


def judge_cmd(out_path):
    base = load(BASE)
    var = load(VAR)
    src = load(SRC, optional=True)
    h12 = load(H12, optional=True) or None
    res = judge(base, var, src, h12)
    n = noise_from_baseline(base)
    res["noise"] = n
    print("VERDICT", res["verdict"], "| invalid", res["invalid"])
    for s in ("0", "1"):
        m = res["seeds"][s]["variant"]
        print(f"seed {s}: F1 rungs passing {m['f1_rungs_passing']} (need 4 of 5) | F2 rungs passing {m['f2_rungs_passing']} (need all 5)")
        for k, r in m["rungs"].items():
            print(f"   k {k}: right {r['right']} of {N}, fixed16 {r['fixed_right']}, cap hits {r['cap_hits']}, mean rounds {r['mean_rounds']:.1f}")
        print(f"   F_eq learned {m['F']['F_eq']['learned']:.2f} fixed16 {m['F']['F_eq']['fixed']:.2f} | F_few learned {m['F']['F_few']['learned']:.2f} fixed16 {m['F']['F_few']['fixed']:.2f}")
    for name, a in res["accuracy"].items():
        print(name, a)
    print("recommend the stability target for practice:", res["recommend"])
    print("noise (baseline seed-to-seed, for the bars):", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in n.items()})
    if out_path:
        Path(out_path).write_text(json.dumps(res, indent=2, sort_keys=True, default=str) + "\n")
    return res


# ---- selftest -------------------------------------------------------------------------------

def _fake(right, fixed, cap, rounds, base):
    a = json.loads(json.dumps(base))
    for k in RUNGS:
        a["rungs"][str(k)]["9"].update(right=right, fixed_right=fixed, cap_hits=cap, mean_rounds=rounds)
    return a


def selftest():
    base = load(BASE)
    # the baseline numbers quoted in PASSMARKS.md / DESIGN.md
    m0, m1 = seed_marks(base[0]), seed_marks(base[1])
    assert m0["f1_rungs_passing"] == [16384] and m1["f1_rungs_passing"] == [1024], (m0["f1_rungs_passing"], m1["f1_rungs_passing"])
    assert len(m0["f2_rungs_passing"]) == 5 and len(m1["f2_rungs_passing"]) == 5
    assert not m0["F1"] and not m1["F1"] and m0["F2"] and m1["F2"]
    assert [round(m["F"]["F_eq"][x], 2) for m in (m0, m1) for x in ("learned", "fixed")] == [51.21, 49.83, 51.67, 50.42]
    assert [round(m["F"]["F_few"][x], 2) for m in (m0, m1) for x in ("learned", "fixed")] == [12.42, 11.83, 14.75, 14.58]
    n = noise_from_baseline(base)
    assert n["diffs"] == [2, 0, 17, -47, -14, 42, -36, 25], n["diffs"]
    assert round(n["rms_eq_counts"], 1) == 28.2 and round(n["rms_few_counts"], 1) == 25.0
    assert round(n["sd_eq_points"], 2) == 3.33 and round(n["sd_few_points"], 2) == 4.17
    assert BAR_EQ >= 2 * n["sd_eq_points"] and BAR_FEW >= 2 * n["sd_few_points"]      # the bars sit above 2 x measured noise
    assert [base[s]["rungs"][str(k)]["9"]["cap_hits"] for s in (0, 1) for k in JUDGED] == [300, 300, 300, 300, 143, 265, 300, 61, 196, 194]
    good_src = {"old": {"sums4": {"right": 200}, "grids5": {"right": 200}}, "gradient_check": {"nonzero_all": True}}
    src = {0: good_src, 1: good_src}
    # synthetic variants for every verdict word
    fires = {s: _fake(280, 278, 20, 15.0, base[s]) for s in (0, 1)}
    r = judge(base, fires, src)
    assert r["verdict"] == "STOP FIRES WITHOUT LABELS", r["verdict"]
    assert r["accuracy"]["F_eq"]["word"] == "HELPS" and r["accuracy"]["F_few"]["word"] == "HELPS", r["accuracy"]
    assert r["recommend"]
    hurts = {s: _fake(200, 250, 20, 15.0, base[s]) for s in (0, 1)}           # fires, but 50 below fixed-16
    assert judge(base, hurts, src)["verdict"] == "FIRES BUT HURTS"
    low = {s: _fake(100, 100, 20, 15.0, base[s]) for s in (0, 1)}               # F_eq 33.3 vs the 51 control: HURTS; F_few 33.3 vs 12 to 15: HELPS
    ra = judge(base, low, src)["accuracy"]
    assert ra["F_eq"]["word"] == "HURTS" and ra["F_few"]["word"] == "HELPS", ra          # the two rows are judged separately
    assert not judge(base, low, src)["recommend"]
    one_up = {0: fires[0], 1: low[1]}                                           # one seed up, one down: never HELPS or HURTS
    assert judge(base, one_up, src)["accuracy"]["F_eq"]["word"] == "NOT SEPARABLE FROM NOISE"
    wrong = {s: _fake(280, 278, 300, 48.0, base[s]) for s in (0, 1)}
    assert judge(base, wrong, src)["verdict"] == "WRONG"
    mixed = {0: fires[0], 1: wrong[1]}                                          # one seed fires: never WRONG, never a win
    assert judge(base, mixed, src)["verdict"] == "NOT SHOWN"
    three = {s: _fake(280, 278, 20, 15.0, base[s]) for s in (0, 1)}
    for s in (0, 1):                                                            # 3 of 5 rungs fire in both seeds: NOT SHOWN, not WRONG
        for k in (1024, 4096):
            three[s]["rungs"][str(k)]["9"]["cap_hits"] = 300
    assert judge(base, three, src)["verdict"] == "NOT SHOWN"
    # the control is the HIGHER of the baseline's two reads: make seed 0's fixed-16 read 10 points above its learned read
    hi = {s: json.loads(json.dumps(base[s])) for s in (0, 1)}
    for k in RUNGS:
        hi[0]["rungs"][str(k)]["9"]["fixed_right"] = hi[0]["rungs"][str(k)]["9"]["right"] + 30
    rh = judge(hi, {s: _fake(210, 200, 20, 15.0, base[s]) for s in (0, 1)}, src)
    want0 = f_score(_fake(210, 200, 20, 15.0, base[0]), RUNGS, "right") - f_score(hi[0], RUNGS, "fixed_right")
    assert abs(rh["accuracy"]["F_eq"]["delta_learned_by_seed"][0] - round(want0, 2)) < 1e-9, rh["accuracy"]["F_eq"]
    # rung-level edges: right 30 fails F1 (needs >= 31); cap 150 passes, 151 fails; fixed - 6 passes, fixed - 7 fails
    assert not f1_rung({"right": 30, "cap_hits": 0}) and f1_rung({"right": 31, "cap_hits": 150}) and not f1_rung({"right": 31, "cap_hits": 151})
    assert f2_rung({"right": 94, "fixed_right": 100}) and not f2_rung({"right": 93, "fixed_right": 100})
    # invalid source: a failed V1 makes that seed invalid
    bad_src = {0: {"old": {"sums4": {"right": 189}, "grids5": {"right": 200}}, "gradient_check": {"nonzero_all": True}}, 1: good_src}
    rb = judge(base, fires, bad_src)
    assert rb["verdict"].startswith("NOT SHOWN") and rb["invalid"]["0"] and not rb["invalid"]["1"]
    assert judge(base, fires, {0: bad_src[0], 1: bad_src[0]})["verdict"] == "INVALID"
    # invalid start: different support hash or update count
    moved = json.loads(json.dumps(fires[0]))
    moved["support_sha256"] = "x"
    assert any("support_sha256" in b for b in validity(moved, base[0], good_src))
    moved = json.loads(json.dumps(fires[0]))
    moved["optimizer_updates_per_rung"] = 2047
    assert validity(moved, base[0], good_src)
    assert validity(fires[0], base[0], good_src) == []
    print(json.dumps({"selftest": "ok"}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    j = sub.add_parser("judge")
    j.add_argument("--out")
    a = p.parse_args()
    selftest() if a.cmd == "selftest" else judge_cmd(a.out)


if __name__ == "__main__":
    main()
