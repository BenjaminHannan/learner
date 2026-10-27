#!/usr/bin/env python3
"""Dev gate and pass-mark arithmetic for the held-out-kinds test (Director helper H1, 2026-09-28).

Pure python. Marks are the ones in artifacts/claude-dir-h1-heldout-20260928/PASSMARKS.md; every threshold
below is a constant copied from that file and is not to be changed after any score exists.

  python3 -B scripts/claude_dir_h1_marks.py selftest
  python3 -B scripts/claude_dir_h1_marks.py gate  --kind graph|rank     writes DEV-GATE-<kind>.json (dev files only)
  python3 -B scripts/claude_dir_h1_marks.py score --kind graph|rank     writes SCORE-<kind>.json (needs gate PASS)

Run layout: <ART>/runs/<kind>/<arm>-s<seed>-<pre|fresh>/{adapt.json,holdout.json}; <ART>/SOURCE-CHECK.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts" / "claude-dir-h1-heldout-20260928"
RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
ARMS = ("loop-pre", "loop-fresh", "plain-pre", "plain-fresh")
GRADED = {"graph": "14", "rank": "9"}

# ---- sealed thresholds (PASSMARKS.md) ----
X_POINTS = 5.0          # F_eq margin, points
WIN_RUNGS = 5           # rungs of 8 the practised loop must beat each comparator on
FLOOR_POINTS = 20.0     # practised loop must reach this F_eq by itself
LOW_MARGIN = 5.0        # carry-over margin on F_low, points
LOW_RUNGS = 5           # F_low = mean of the five lowest rungs (k = 1, 4, 16, 64, 256)
V3_LO, V3_HI = 0.10, 0.90


def pct(c, n):
    return 100.0 * c / n


def f_eq(counts, n=300):
    return sum(pct(c, n) for c in counts) / len(counts)


def f_low(counts, n=300):
    return sum(pct(c, n) for c in counts[:LOW_RUNGS]) / LOW_RUNGS


def e_first(counts, n, frac):
    for k, c in zip(RUNGS, counts):
        if c >= frac * n:
            return k
    return None


def collapsed(counts, n=300):
    """Report-only: rungs at least 30 points below every neighbouring rung (a training collapse)."""
    out = []
    for i, c in enumerate(counts):
        nb = [counts[j] for j in (i - 1, i + 1) if 0 <= j < len(counts)]
        if all(pct(x, n) - pct(c, n) >= 30 for x in nb):
            out.append(RUNGS[i])
    return out


def wins(a, b):
    return sum(x > y for x, y in zip(a, b))


def v3_rungs(counts, n=300):
    return [k for k, c in zip(RUNGS, counts) if V3_LO * n < c < V3_HI * n]


def v3(dev, n=300):
    """dev: {(seed, arm): [8 counts]}.  True when some arm-seed has >= 3 rungs strictly between 10% and 90%."""
    per = {f"s{s}-{a}": v3_rungs(c, n) for (s, a), c in dev.items()}
    return any(len(v) >= 3 for v in per.values()), per


def seed_marks(cnt, seed, n=300):
    lp, lf, pp, pf = (cnt[(seed, a)] for a in ARMS)
    F = {a: f_eq(cnt[(seed, a)], n) for a in ARMS}
    m = {
        "F_eq": {a: round(F[a], 2) for a in ARMS},
        "M1_loop_minus_plain_practised": round(F["loop-pre"] - F["plain-pre"], 2),
        "M2_loop_minus_fresh_loop": round(F["loop-pre"] - F["loop-fresh"], 2),
        "M2b_loop_minus_fresh_plain": round(F["loop-pre"] - F["plain-fresh"], 2),
        "M3_wins_vs_plain_practised": wins(lp, pp),
        "M3_wins_vs_fresh_loop": wins(lp, lf),
        "M4_practised_loop_F_eq": round(F["loop-pre"], 2),
        "F_low": {a: round(f_low(cnt[(seed, a)], n), 2) for a in ARMS},
        "C1_low_loop_minus_fresh_loop": round(f_low(lp, n) - f_low(lf, n), 2),
        "report_E50": {a: e_first(cnt[(seed, a)], n, .5) for a in ARMS},
        "report_E30": {a: e_first(cnt[(seed, a)], n, .3) for a in ARMS},
        "report_collapsed_rungs": {a: collapsed(cnt[(seed, a)], n) for a in ARMS},
    }
    m["pass"] = {
        "M1": F["loop-pre"] - F["plain-pre"] >= X_POINTS,
        "M2": F["loop-pre"] - F["loop-fresh"] >= X_POINTS,
        "M2b": F["loop-pre"] - F["plain-fresh"] >= X_POINTS,
        "M3": wins(lp, pp) >= WIN_RUNGS and wins(lp, lf) >= WIN_RUNGS,
        "M4": F["loop-pre"] >= FLOOR_POINTS,
        "C1": f_low(lp, n) - f_low(lf, n) >= LOW_MARGIN,
    }
    m["main_pass"] = all(m["pass"][k] for k in ("M1", "M2", "M2b", "M3", "M4"))
    m["no_advantage"] = F["loop-pre"] <= F["plain-pre"] or F["loop-pre"] <= F["loop-fresh"]
    m["no_carry"] = f_low(lp, n) <= f_low(lf, n)
    return m


def kind_verdict(hold, n=300):
    per = {f"seed{s}": seed_marks(hold, s, n) for s in (0, 1)}
    if all(per[k]["main_pass"] for k in per):
        main = "PASS"
    elif all(per[k]["no_advantage"] for k in per):
        main = "REFUTED"
    else:
        main = "NOT-SHOWN"
    if all(per[k]["pass"]["C1"] for k in per):
        carry = "SHOWN"
    elif all(per[k]["no_carry"] for k in per):
        carry = "REFUTED"
    else:
        carry = "NOT-SHOWN"
    return {"seeds": per, "advantage_verdict": main, "carry_over_verdict": carry}


def overall(verdicts):
    """verdicts: {'graph': kind_verdict, 'rank': kind_verdict}"""
    a = [v["advantage_verdict"] for v in verdicts.values()]
    c = [v["carry_over_verdict"] for v in verdicts.values()]
    if a.count("PASS") == len(a):
        adv = "SUPPORTED-3-KINDS"
    elif "PASS" in a and "REFUTED" not in a:
        adv = "PARTIAL-2-KINDS"
    elif "REFUTED" in a:
        adv = "MAZE-ONLY-SO-FAR (refuted on at least one new kind)"
    else:
        adv = "NOT-SHOWN"
    car = ("SHOWN-BOTH" if c.count("SHOWN") == len(c) else "SHOWN-ONE" if "SHOWN" in c else
           "REFUTED" if "REFUTED" in c and "SHOWN" not in c else "NOT-SHOWN")
    return {"advantage": adv, "carry_over": car}


# ------------------------------ file I/O ------------------------------
def run_dir(kind, arm, seed):
    a, init = arm.split("-")
    return ART / "runs" / kind / f"{a}-s{seed}-{init}"


def load_counts(kind, which):
    key = GRADED[kind]
    out, n = {}, None
    for seed in (0, 1):
        for arm in ARMS:
            d = json.loads((run_dir(kind, arm, seed) / f"{which}.json").read_text())
            table = d["rungs"] if which == "adapt" else d["scores"]
            out[(seed, arm)] = [table[str(k)][key]["right"] for k in RUNGS]
            n = table["1"][key]["n"]
    return out, n


def gate(kind):
    path = ART / f"DEV-GATE-{kind}.json"
    if path.exists():
        raise FileExistsError("dev gate already written")
    src = json.loads((ART / "SOURCE-CHECK.json").read_text())
    dev, n = load_counts(kind, "adapt")
    ok3, per = v3(dev, n)
    v2k = True
    for seed in (0, 1):
        for arm in ARMS:
            d = json.loads((run_dir(kind, arm, seed) / "adapt.json").read_text())
            v2k &= bool(d["gradient_check_adapt"]["nonzero_all_except_halt"])
    res = {"kind": kind, "V0_kind_selftest": "see SELFTEST-" + kind + ".log", "V1": bool(src["V1"]),
           "V2": bool(src["V2"]), "V2k": bool(v2k), "V3": ok3, "V3_middle_rungs": per,
           "dev_counts": {f"s{s}-{a}": c for (s, a), c in dev.items()}, "n": n}
    res["verdict"] = "PASS" if res["V1"] and res["V2"] and res["V2k"] and ok3 else "INCONCLUSIVE"
    path.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("kind", "V1", "V2", "V2k", "V3", "verdict")}))


def score(kind):
    g = json.loads((ART / f"DEV-GATE-{kind}.json").read_text())
    if g["verdict"] != "PASS":
        raise ValueError("dev gate did not pass; holdout must stay sealed")
    hold, n = load_counts(kind, "holdout")
    res = kind_verdict(hold, n)
    res["kind"] = kind
    res["holdout_counts"] = {f"s{s}-{a}": c for (s, a), c in hold.items()}
    (ART / f"SCORE-{kind}.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"kind": kind, "advantage": res["advantage_verdict"], "carry": res["carry_over_verdict"]}))


# ------------------------------ self-test ------------------------------
MAZE_HOLDOUT = {   # RESULTS-EQ.md, one-time holdout, 9x9, counts of 300 at k = 1 .. 16384
    (0, "loop-pre"): [1, 0, 28, 137, 256, 271, 257, 274], (0, "loop-fresh"): [0, 13, 34, 49, 144, 67, 85, 104],
    (0, "plain-pre"): [2, 8, 1, 29, 124, 217, 227, 203], (0, "plain-fresh"): [0, 3, 2, 24, 138, 123, 107, 142],
    (1, "loop-pre"): [1, 0, 3, 190, 262, 236, 284, 255], (1, "loop-fresh"): [0, 1, 36, 166, 167, 0, 128, 18],
    (1, "plain-pre"): [0, 0, 0, 12, 134, 213, 223, 224], (1, "plain-fresh"): [0, 1, 11, 25, 120, 142, 149, 152],
}
MAZE_DEV = {       # RESULTS-EQ.md dev table
    (0, "loop-pre"): [2, 0, 21, 126, 263, 275, 256, 286], (0, "loop-fresh"): [0, 15, 33, 51, 130, 66, 69, 109],
    (0, "plain-pre"): [1, 4, 1, 29, 127, 216, 229, 210], (0, "plain-fresh"): [0, 0, 8, 21, 125, 127, 108, 129],
    (1, "loop-pre"): [0, 0, 4, 173, 277, 233, 292, 261], (1, "loop-fresh"): [0, 1, 39, 164, 161, 0, 116, 24],
    (1, "plain-pre"): [0, 0, 1, 14, 118, 207, 228, 215], (1, "plain-fresh"): [0, 0, 6, 26, 119, 143, 144, 131],
}
MAZE_PUBLISHED_FEQ = {(0, "loop-pre"): 51.00, (0, "loop-fresh"): 20.67, (0, "plain-pre"): 33.79,
                      (0, "plain-fresh"): 22.46, (1, "loop-pre"): 51.29, (1, "loop-fresh"): 21.50,
                      (1, "plain-pre"): 33.58, (1, "plain-fresh"): 25.00}
MAZE_PUBLISHED_DEV_FEQ = {(0, "loop-pre"): 51.21, (0, "loop-fresh"): 19.71, (0, "plain-pre"): 34.04,
                          (0, "plain-fresh"): 21.58, (1, "loop-pre"): 51.67, (1, "loop-fresh"): 21.04,
                          (1, "plain-pre"): 32.62, (1, "plain-fresh"): 23.71}


def selftest():
    # 1. F_eq arithmetic reproduces every published maze number (holdout and dev), to two decimals.
    for key, want in MAZE_PUBLISHED_FEQ.items():
        assert round(f_eq(MAZE_HOLDOUT[key]), 2) == want, (key, f_eq(MAZE_HOLDOUT[key]), want)
    for key, want in MAZE_PUBLISHED_DEV_FEQ.items():
        assert round(f_eq(MAZE_DEV[key]), 2) == want, (key, f_eq(MAZE_DEV[key]), want)
    # 2. E50 as published: practised loop 256 / 64, practised plain 1024 / 1024, fresh loop none / 64, fresh plain none / 16384.
    assert [e_first(MAZE_HOLDOUT[(s, a)], 300, .5) for s in (0, 1) for a in ARMS] == \
        [256, None, 1024, None, 64, 64, 1024, 16384]
    # 3. V3 on the published maze dev table passes (fresh loop seed 0 has six middle rungs).
    ok, per = v3(MAZE_DEV)
    assert ok and len(per["s0-loop-fresh"]) == 6, per
    # 4. Calibration only: what the sealed marks say about the maze results already published.
    mz = kind_verdict(MAZE_HOLDOUT)
    print(json.dumps({"maze_under_these_marks": {
        "advantage": mz["advantage_verdict"], "carry": mz["carry_over_verdict"],
        "seed0": {k: mz["seeds"]["seed0"][k] for k in ("M1_loop_minus_plain_practised", "M2_loop_minus_fresh_loop",
                                                        "M3_wins_vs_plain_practised", "M3_wins_vs_fresh_loop",
                                                        "C1_low_loop_minus_fresh_loop")},
        "seed1": {k: mz["seeds"]["seed1"][k] for k in ("M1_loop_minus_plain_practised", "M2_loop_minus_fresh_loop",
                                                        "M3_wins_vs_plain_practised", "M3_wins_vs_fresh_loop",
                                                        "C1_low_loop_minus_fresh_loop")}}}, sort_keys=True))
    assert mz["advantage_verdict"] == "PASS" and mz["carry_over_verdict"] == "SHOWN"
    # 5. Synthetic cases: no advantage, mixed, floor, and overall roll-up.
    flat = {(s, a): [30, 60, 90, 120, 150, 150, 150, 150] for s in (0, 1) for a in ARMS}
    assert kind_verdict(flat)["advantage_verdict"] == "REFUTED"          # everyone equal
    mixed = dict(MAZE_HOLDOUT)
    mixed[(1, "loop-pre")] = MAZE_HOLDOUT[(1, "plain-pre")]              # seed 1 loses its edge
    assert kind_verdict(mixed)["advantage_verdict"] == "NOT-SHOWN"       # seed 0 ok, seed 1 no advantage
    low = {k: [c // 10 for c in v] for k, v in MAZE_HOLDOUT.items()}     # every arm at a floor
    assert kind_verdict(low)["advantage_verdict"] != "PASS"              # M4 floor blocks a tiny-number "win"
    assert overall({"graph": mz, "rank": mz})["advantage"] == "SUPPORTED-3-KINDS"
    assert overall({"graph": mz, "rank": kind_verdict(flat)})["advantage"].startswith("MAZE-ONLY")
    assert overall({"graph": mz, "rank": kind_verdict(mixed)})["advantage"] == "PARTIAL-2-KINDS"
    # 6. A collapsed fresh-loop rung cannot fake a win: shrink the fresh loop to nothing on one rung only.
    tweak = dict(MAZE_HOLDOUT)
    tweak[(1, "loop-fresh")] = [0, 1, 36, 166, 167, 300, 128, 18]
    assert wins(tweak[(1, "loop-pre")], tweak[(1, "loop-fresh")]) == 5
    assert collapsed(MAZE_HOLDOUT[(1, "loop-fresh")]) == [1024, 16384]
    assert collapsed([100, 100, 0, 100, 100, 100, 100, 100]) == [16]
    # 7. V3 negatives: all-zero and all-saturated ladders fail.
    assert not v3({(0, "loop-pre"): [0] * 8, (0, "loop-fresh"): [300] * 8})[0]
    print("selftest ok")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "gate", "score"))
    p.add_argument("--kind", choices=("graph", "rank"))
    a = p.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "gate":
        gate(a.kind)
    else:
        score(a.kind)


if __name__ == "__main__":
    main()
