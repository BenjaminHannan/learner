#!/usr/bin/env python3
"""dir-h6 ADDENDUM-1 (helper H10, Claude, 2026-09-28, written between 21:05 and 21:10 UTC (`date -u`)): reads the mid-night curve. Report only: it decides nothing.

Pure python (no torch). Inputs: the run folder(s) that hold dirh6-seed{S}.json (the sealed script's output) and
dirh6-curve-seed{S}.json (scripts/claude_dir_h6_sleeplen_add1.py's output). For every seed x night x arm in {L, B} it puts one label on the
night's curve, by a fixed decision list (the reasons are in ADDENDUM-1.md; every number is a count of right answers):

  f0      the arm's own morning net on the sealed day_grids test (400), i.e. the previous morning (night 1: the base net)
  own0    the same net on that day's own grid puzzles (about 300), before the night   (dirh6-seed json, log["day"][d][arm]["grids"])
  F[s]    the net after s night steps on the day_grids test (400, never trained on)    (curve json, "fresh")
  O[s]    the net after s night steps on the night's own grid puzzles                  (curve json, "own")
  steps   300, 1,000, 2,000 and 6,000 (the last is the end of the night); "early" = every step but the last
  T = 40  the size of a real change: M1's +40 in PASSMARKS.md and twice the +-20 wobble (DESIGN.md)

  0 NO-ROOM           own0 is at least 90% of the own puzzles: the net already solves them, the curve cannot show learning
  1 NOT-LEARNING      O[end] - own0 < T and max(F) - f0 < T          (both low)
  2 MEMORISED         O[end] is at least 90% of the own puzzles and max(F) - f0 < T   (own near its ceiling, fresh flat)
  3 PEAK-THEN-DECAY   max(F early) - F[end] >= T and max(F early) - f0 >= T   (the net moved too far)
  4 GAIN-KEPT         F[end] - f0 >= T
  5 UNCLEAR           none of the above

The first line that applies wins. Also printed: the integrity check that the curve's last point equals the night's morning score
(the same net on the same 400 puzzles, so it must), and the mean fresh change per arm, night and step.

  python3 scripts/claude_dir_h6_curve_read.py read --runs artifacts/claude-dir-h6-sleeplen-20260928/runs [--out FILE]
  python3 scripts/claude_dir_h6_curve_read.py selftest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

T = 40
OWN_HIGH_NUM, OWN_HIGH_DEN = 9, 10          # "at least 90%" as integer arithmetic: 10 * count >= 9 * n
EXPECT_STEPS = (300, 1000, 2000, 6000)
ARMS = ("L", "B")
LABELS = ("NO-ROOM", "NOT-LEARNING", "MEMORISED", "PEAK-THEN-DECAY", "GAIN-KEPT", "UNCLEAR")


def at_least_90(count, n):
    return OWN_HIGH_DEN * count >= OWN_HIGH_NUM * n


def classify(f0, own0, n_own, fresh, own):
    """fresh, own: {step: right}. Returns the label and the numbers it read."""
    steps = sorted(fresh)
    end = steps[-1]
    early = steps[:-1]
    fmax = max(fresh.values())
    fearly = max((fresh[s] for s in early), default=None)
    nums = {"f0": f0, "own0": own0, "n_own": n_own, "F_end": fresh[end], "O_end": own[end], "F_max": fmax, "F_early_max": fearly,
            "F_gain_max": fmax - f0, "O_gain": own[end] - own0, "end_step": end}
    if at_least_90(own0, n_own):
        label = "NO-ROOM"
    elif own[end] - own0 < T and fmax - f0 < T:
        label = "NOT-LEARNING"
    elif at_least_90(own[end], n_own) and fmax - f0 < T:
        label = "MEMORISED"
    elif fearly is not None and fearly - fresh[end] >= T and fearly - f0 >= T:
        label = "PEAK-THEN-DECAY"
    elif fresh[end] - f0 >= T:
        label = "GAIN-KEPT"
    else:
        label = "UNCLEAR"
    return label, nums


def find(runs):
    """seed -> (main json path, curve json path); files are matched by the seed in their names, anywhere under the folder(s)"""
    found = {}
    for root in runs:
        for p in sorted(Path(root).rglob("dirh6-*seed*.json")):
            m = re.fullmatch(r"dirh6-(curve-)?seed(\d+)\.json", p.name)
            if m:
                found.setdefault(int(m.group(2)), {})["curve" if m.group(1) else "main"] = p
    return found


def read_seed(seed, main, curve):
    rows, integrity, s_check = [], [], []
    for d in sorted(curve["curve"], key=int):
        for arm in ARMS:
            c = curve["curve"][d].get(arm)
            row = {"seed": seed, "night": int(d), "arm": arm}
            if c is None or [int(s) for s in sorted(c["steps"], key=int)] != list(EXPECT_STEPS):
                row.update(label="INCOMPLETE", why="curve steps " + (str(sorted(c["steps"], key=int)) if c else "missing") +
                           (" errors " + json.dumps(c["errors"]) if c and c.get("errors") else ""))
                rows.append(row)
                continue
            prev = main["morning"]["base"] if d == "1" else main["morning"][str(int(d) - 1)][arm]
            f0 = prev["day_grids"]["right"]
            day = main["day"][d][arm]["grids"]
            fresh = {int(s): v["fresh"]["right"] for s, v in c["steps"].items()}
            own = {int(s): v["own"]["right"] for s, v in c["steps"].items()}
            label, nums = classify(f0, day["right"], day["n"], fresh, own)
            end = c["steps"][str(EXPECT_STEPS[-1])]["fresh"]
            m = main["morning"][d][arm]["day_grids"]
            ok = end["right"] == m["right"] and end["n"] == m["n"] and c["own_n"] == day["n"]
            integrity.append(ok)
            if d == "1" and arm == "L" and "S" in main["morning"]["1"]:      # night 1: L's first 300 steps are S's whole night
                s_end = main["morning"]["1"]["S"]["day_grids"]["right"]
                s_check.append({"seed": seed, "L_at_300": fresh[300], "S_morning": s_end, "equal": fresh[300] == s_end})
            row.update(label=label, numbers=nums, fresh=fresh, own=own, curve_end_equals_morning=ok)
            rows.append(row)
    return rows, integrity, s_check


def summarize(rows, integrity, s_check):
    out = {"counts": {}, "mean_fresh_change": {}}
    for arm in ARMS:
        mine = [r for r in rows if r["arm"] == arm and r["label"] != "INCOMPLETE"]
        out["counts"][arm] = {"readable_arm_nights": len(mine), "incomplete": sum(r["arm"] == arm and r["label"] == "INCOMPLETE" for r in rows),
                              **{lab: sum(r["label"] == lab for r in mine) for lab in LABELS}}
        for night in sorted({r["night"] for r in mine}):
            sel = [r for r in mine if r["night"] == night]
            out["mean_fresh_change"].setdefault(arm, {})[str(night)] = {
                str(s): round(sum(r["fresh"][s] - r["numbers"]["f0"] for r in sel) / len(sel), 1) for s in EXPECT_STEPS}
    out["integrity"] = {"curve_end_equals_morning": sum(integrity), "of": len(integrity)}
    out["night1_L300_equals_S_morning"] = {"equal": sum(x["equal"] for x in s_check), "of": len(s_check), "detail": s_check}
    return out


def read(runs, out=None):
    found = find(runs)
    rows, integrity, s_check, missing = [], [], [], []
    for seed in sorted(found):
        f = found[seed]
        if "main" not in f or "curve" not in f:
            missing.append({"seed": seed, "have": sorted(f)})
            continue
        r, i, sc = read_seed(seed, json.loads(f["main"].read_text()), json.loads(f["curve"].read_text()))
        rows += r
        integrity += i
        s_check += sc
    res = {"threshold": T, "seeds_read": sorted({r["seed"] for r in rows}), "seeds_missing_a_file": missing, "rows": rows,
           "summary": summarize(rows, integrity, s_check)}
    for r in rows:
        if r["label"] == "INCOMPLETE":
            print(f"seed {r['seed']} night {r['night']} {r['arm']}: INCOMPLETE ({r['why']})")
            continue
        n = r["numbers"]
        print(f"seed {r['seed']} night {r['night']} {r['arm']}: {r['label']}  fresh f0 {n['f0']} -> " +
              " ".join(f"{s}:{r['fresh'][s]}" for s in EXPECT_STEPS) + f"  own {n['own0']} -> " +
              " ".join(f"{s}:{r['own'][s]}" for s in EXPECT_STEPS) + f" (of {n['n_own']})")
    for arm in ARMS:
        c = res["summary"]["counts"][arm]
        print(f"{arm}: readable {c['readable_arm_nights']}, " + ", ".join(f"{lab} {c[lab]}" for lab in LABELS) +
              (f", incomplete {c['incomplete']}" if c["incomplete"] else ""))
    print("integrity: curve end equals the morning score on", res["summary"]["integrity"]["curve_end_equals_morning"], "of", res["summary"]["integrity"]["of"], "arm-nights")
    sc = res["summary"]["night1_L300_equals_S_morning"]
    print("night 1: L at step 300 equals S's morning day_grids on", sc["equal"], "of", sc["of"], "seeds (the two nights are the same 300 steps)")
    if missing:
        print("seeds with a missing file:", json.dumps(missing))
    if out:
        p = Path(out)
        if p.exists():
            sys.exit(f"refusing to overwrite {p}")
        p.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# ------------------------------------------------------------------ selftest
def selftest_classify():
    F = lambda *v: dict(zip(EXPECT_STEPS, v))
    cases = [                                                   # label, f0, own0, n_own, fresh at the 4 steps, own at the 4 steps
        ("NO-ROOM", 200, 270, 300, F(250, 260, 270, 280), F(285, 290, 295, 298)),
        ("NOT-LEARNING", 200, 100, 300, F(200, 205, 210, 215), F(105, 110, 118, 139)),
        ("MEMORISED", 200, 100, 300, F(205, 210, 215, 239), F(200, 260, 280, 295)),
        ("PEAK-THEN-DECAY", 200, 100, 300, F(290, 300, 280, 230), F(150, 200, 230, 250)),
        ("GAIN-KEPT", 200, 100, 300, F(250, 270, 285, 290), F(150, 250, 280, 290)),
        ("UNCLEAR", 200, 100, 300, F(230, 235, 225, 232), F(150, 180, 190, 200)),
    ]
    for want, f0, own0, n_own, fr, ow in cases:
        got, _ = classify(f0, own0, n_own, fr, ow)
        assert got == want, (want, got)
    flat = F(100, 100, 100, 100)
    edges = [                                                   # every edge is 39 against 40, or 269 against 270 of 300
        ("NOT-LEARNING", 200, 100, F(200, 200, 200, 239), F(100, 100, 100, 139)),       # fresh +39, own +39
        ("GAIN-KEPT", 200, 100, F(200, 200, 200, 240), F(100, 100, 100, 139)),          # fresh +40
        ("UNCLEAR", 200, 100, F(200, 200, 200, 239), F(100, 100, 100, 140)),            # own +40 alone: not "both low"
        ("UNCLEAR", 200, 100, F(200, 200, 200, 239), F(100, 100, 100, 269)),            # 269 of 300 is not 90%
        ("MEMORISED", 200, 100, F(200, 200, 200, 239), F(100, 100, 100, 270)),          # 270 of 300 is
        ("NOT-LEARNING", 200, 269, F(200, 200, 200, 200), F(269, 269, 269, 269)),       # own0 269: there is room
        ("NO-ROOM", 200, 270, F(200, 200, 200, 200), F(270, 270, 270, 270)),            # own0 270: none
        ("GAIN-KEPT", 200, 100, F(240, 300, 260, 261), flat),                           # decay 39: not a peak-then-decay, gain 61 kept
        ("PEAK-THEN-DECAY", 200, 100, F(240, 300, 260, 260), flat),                     # decay 40, peak gain 100
        ("NOT-LEARNING", 200, 100, F(200, 239, 200, 200), flat),                        # peak gain 39: too small to call a peak
        ("PEAK-THEN-DECAY", 200, 100, F(200, 240, 200, 200), flat),                     # peak gain 40 and decay 40
    ]
    for want, f0, own0, fr, ow in edges:
        got, _ = classify(f0, own0, 300, fr, ow)
        assert got == want, (want, got, fr, ow)
    return {"cases": len(cases), "edges": len(edges)}


def selftest_files():
    tmp = Path(tempfile.mkdtemp())

    def main_json(f0_base, own0, own_n, ends, s_morning=290):    # nights 1 and 2, arms L and B (S's night-1 morning = L at step 300)
        morning = {"base": {"day_grids": {"right": f0_base, "n": 400}}}
        day = {}
        for i, d in enumerate(("1", "2")):
            morning[d] = {a: {"day_grids": {"right": ends[i][a], "n": 400}} for a in ARMS}
            day[d] = {a: {"grids": {"right": own0, "n": own_n}} for a in ARMS}
        morning["1"]["S"] = {"day_grids": {"right": s_morning, "n": 400}}
        return {"morning": morning, "day": day}

    def curve_json(table, own_n):
        return {"curve": {d: {a: {"own_n": own_n, "steps": {str(s): {"fresh": {"right": table[d][a]["fresh"][j], "n": 400},
                                                                    "own": {"right": table[d][a]["own"][j], "n": own_n}}
                                                         for j, s in enumerate(EXPECT_STEPS)}} for a in ARMS} for d in table}}
    table = {"1": {"L": {"fresh": [290, 300, 280, 230], "own": [150, 200, 230, 250]}, "B": {"fresh": [250, 270, 285, 290], "own": [150, 250, 280, 290]}},
             "2": {"L": {"fresh": [200, 205, 210, 215], "own": [105, 110, 118, 139]}, "B": {"fresh": [230, 235, 225, 232], "own": [150, 180, 190, 200]}}}
    ends = [{"L": 230, "B": 290}, {"L": 215, "B": 232}]         # the morning scores that equal the curve's last points
    (tmp / "s13").mkdir()
    (tmp / "s13/dirh6-seed13.json").write_text(json.dumps(main_json(200, 100, 300, ends)))
    (tmp / "s13/dirh6-curve-seed13.json").write_text(json.dumps(curve_json(table, 300)))
    res = read([tmp], out=tmp / "reading.json")
    got = {(r["night"], r["arm"]): r["label"] for r in res["rows"]}
    assert got == {(1, "L"): "PEAK-THEN-DECAY", (1, "B"): "GAIN-KEPT", (2, "L"): "NOT-LEARNING", (2, "B"): "UNCLEAR"}, got
    assert res["summary"]["integrity"] == {"curve_end_equals_morning": 4, "of": 4}, res["summary"]["integrity"]
    assert res["summary"]["counts"]["L"]["readable_arm_nights"] == 2 and res["summary"]["counts"]["L"]["PEAK-THEN-DECAY"] == 1
    assert res["summary"]["mean_fresh_change"]["L"]["1"]["300"] == 90.0, res["summary"]["mean_fresh_change"]
    assert res["summary"]["night1_L300_equals_S_morning"]["equal"] == 1 and res["summary"]["night1_L300_equals_S_morning"]["of"] == 1
    assert (tmp / "reading.json").exists()
    try:
        read([tmp], out=tmp / "reading.json")
        raise AssertionError("overwrite allowed")
    except SystemExit as e:
        assert "refusing" in str(e)
    # a curve end that does not equal the morning score is flagged, not hidden
    bad = [{"L": 231, "B": 290}, {"L": 215, "B": 232}]
    (tmp / "s13/dirh6-seed13.json").write_text(json.dumps(main_json(200, 100, 300, bad)))
    assert read([tmp])["summary"]["integrity"]["curve_end_equals_morning"] == 3
    (tmp / "s13/dirh6-seed13.json").write_text(json.dumps(main_json(200, 100, 300, ends, s_morning=289)))
    assert read([tmp])["summary"]["night1_L300_equals_S_morning"]["equal"] == 0            # a mismatch is shown, not hidden
    (tmp / "s13/dirh6-seed13.json").write_text(json.dumps(main_json(200, 100, 300, bad)))
    # a missing step makes the row INCOMPLETE and it is not counted
    cj = curve_json(table, 300)
    del cj["curve"]["2"]["B"]["steps"]["1000"]
    (tmp / "s13/dirh6-curve-seed13.json").write_text(json.dumps(cj))
    c = read([tmp])["summary"]["counts"]["B"]
    assert c["incomplete"] == 1 and c["readable_arm_nights"] == 1, c
    # a seed with only one of the two files is listed, not silently dropped
    (tmp / "s14").mkdir()
    (tmp / "s14/dirh6-seed14.json").write_text("{}")
    assert read([tmp])["seeds_missing_a_file"] == [{"seed": 14, "have": ["main"]}]
    return {"file_checks": 6}


def selftest():
    print(json.dumps({"classify": selftest_classify()}))
    print(json.dumps({"files": selftest_files()}))
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("read")
    p.add_argument("--runs", nargs="+", required=True)
    p.add_argument("--out")
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
    else:
        read(a.runs, a.out)
