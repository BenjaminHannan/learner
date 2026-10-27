#!/usr/bin/env python3
"""H3 race table and verdict with ADDENDUM-1 applied (artifacts/claude-dir-h3-design-20260928/ADDENDUM-1.md).

Copy of scripts/claude_dir_h3_report.py (helper H3). Pure standard library (no torch). It still uses the summary arithmetic of
scripts/claude_sparse_race.py (imported, not edited). The only differences from the original are the ones ADDENDUM-1 lists:

  (a) REJECTED-by-breaking needs EVERY gaining seed to break an old-kind gate (the original code said `any`, the marks said "every").
  (b) the two old-kind sleep gates (marks 4) are judged on the mean of 3 sleep draws per branch for both H3 and the loop, with margin
      max(6, 2 x SE), when `--sleep-draws DIR` holds sleep-draws-s{seed}.json; without it they are "skipped" = report-only.
  (c) a second required verdict row: F_few (mean of the k = 1, 4, 16, 64 rungs) at least 5 points above the loop, in both seeds.
  (d) the "dead gate" flag comes from scripts/claude_dir_h3_gate_report_v2.py (`--gate-reports`, files gate-k{64,16384}-s{seed}.json).
  (e) an optional constant-g = 0.9 control (`--control`, runs h3c-pre-s{seed}) and the dead-gate flags only decide which mechanism
      sentence may be used; they never change the verdict word.

  python3 scripts/claude_dir_h3_report_add1.py selftest
  python3 scripts/claude_dir_h3_report_add1.py --split dev     --h3 <eq-runs dir> --loop '<...>/loop-s{seed}-pre' --plain '<...>/plain-s{seed}-pre' --out dev-table.json
  python3 scripts/claude_dir_h3_report_add1.py --split holdout --h3 ... [--sleep-draws DIR] [--control <eq-runs dir>] [--gate-reports <eq-runs dir>]   (only after every dev run is committed)

sleep-draws-s{seed}.json (counts of 200, exactly 3 draws each; draw 0 is the harness's own recorded sleep):
  {"seed": 0, "h3": {"64": {"sums4": [a, b, c], "grids5": [a, b, c]}, "16384": {...}}, "loop": {"64": {...}, "16384": {...}}}
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_sparse_race as R  # noqa: E402

KINDS = R.KINDS
MARGIN_MIN, SE_MULT = 6.0, 2.0          # ADDENDUM-1 (b): margin = max(6, 2 x SE), counts of 200
FEW_MARGIN = 5.0                        # ADDENDUM-1 (c): F_few at least +5 over the loop
CONTROL_MARGIN = 5.0                    # ADDENDUM-1 (e): H3 F_eq at least +5 over the constant-g control


def draw_gate(h3_draws, loop_draws):
    """One branch. Each argument {kind: [3 counts]}. Passes when, for every kind, mean(H3) >= mean(loop) - max(6, 2 x SE),
    SE = sqrt(var_H3/3 + var_loop/3) with the sample variance (n - 1) of the 3 draws of each side."""
    detail, ok = {}, True
    for k in KINDS:
        a, b = h3_draws[k], loop_draws[k]
        if len(a) != 3 or len(b) != 3 or not all(isinstance(x, int) and 0 <= x <= 200 for x in a + b):
            raise ValueError(f"need exactly 3 integer draws in 0..200 for {k} on each side: {a}, {b}")
        ma, mb = sum(a) / 3, sum(b) / 3
        va = sum((x - ma) ** 2 for x in a) / 2
        vb = sum((x - mb) ** 2 for x in b) / 2
        se = math.sqrt(va / 3 + vb / 3)
        margin = max(MARGIN_MIN, SE_MULT * se)
        detail[k] = {"h3_mean": round(ma, 2), "loop_mean": round(mb, 2), "se": round(se, 2), "margin": round(margin, 2),
                     "pass": ma >= mb - margin}
        ok &= detail[k]["pass"]
    return ok, detail


def seed_gates(h3, fr, lp, pl, draws=None):
    """summaries in, marks out. Sleep gates are True/False when judged on draws, None when skipped (report-only)."""
    g = {"F_eq_loop_plus10": h3["F_eq"] >= lp["F_eq"] + 10,
         "F_eq_plain_plus5": h3["F_eq"] >= pl["F_eq"] + 5,
         "F_eq_fresh_plus5": h3["F_eq"] >= fr["F_eq"] + 5,
         "F_few_loop_plus5": h3["F_few"] >= lp["F_few"] + FEW_MARGIN,
         "old_before_95": all(h3["old_before"][k] >= 190 for k in KINDS),
         "old_before_within3_of_loop": all(h3["old_before"][k] >= lp["old_before"][k] - 6 for k in KINDS),
         "budget_within2pct": abs(h3["weights"] - lp["weights"]) <= .02 * lp["weights"]}
    detail = {}
    for br in ("64", "16384"):
        key = f"sleep{br}_old_mean3_margin"
        if draws is None:
            g[key] = None
        else:
            g[key], detail[br] = draw_gate(draws["h3"][br], draws["loop"][br])
    return g, detail


SLEEP_KEYS = ("sleep64_old_mean3_margin", "sleep16384_old_mean3_margin")
OLD_KEYS = ("old_before_95", "old_before_within3_of_loop")


def seed_row(h3, fr, lp, pl, draws=None):
    g, detail = seed_gates(h3, fr, lp, pl, draws)
    judged = {k: v for k, v in g.items() if v is not None}
    row = {"h3": h3, "h3_fresh": fr, "loop": lp, "plain": pl, "F_eq_minus_loop": h3["F_eq"] - lp["F_eq"],
           "F_few_minus_loop": h3["F_few"] - lp["F_few"], "gates": g, "sleep_draw_detail": detail,
           "sleep_gates_judged": all(g[k] is not None for k in SLEEP_KEYS), "all_judged_gates": all(judged.values())}
    row["gain"] = row["F_eq_minus_loop"] > 0
    # a gain made by breaking an old-kind gate: a gate that was judged and failed (a skipped gate cannot fail)
    row["maze_gain_breaking_old_gate"] = row["gain"] and not all(g[k] for k in OLD_KEYS + SLEEP_KEYS if g[k] is not None)
    return row


def verdict(seeds):
    """seeds: {'0': row, '1': row}. Returns (word, failing gates per seed)."""
    s = seeds
    gaining = [x for x in s if s[x]["gain"]]
    rejected = all(s[x]["F_eq_minus_loop"] <= 0 for x in s) or (
        bool(gaining) and all(s[x]["maze_gain_breaking_old_gate"] for x in gaining))      # ADDENDUM-1 (a): EVERY gaining seed
    all_ok = all(s[x]["all_judged_gates"] for x in s)
    sleeps = all(s[x]["sleep_gates_judged"] for x in s)
    if all_ok and sleeps:
        word = "PASS"
    elif all_ok:
        word = "PASS (sleep gates not judged)"
    elif rejected:
        word = "REJECTED"
    else:
        word = "NOT PROMOTED"
    failing = {x: [k for k, v in s[x]["gates"].items() if v is False] for x in s}
    return word, failing


def gate_flags(gate_dir, seed):
    """dead_gate flags of gate_report_v2 at the k = 64 and k = 16,384 checkpoints of h3-pre (None = file missing)."""
    out = {}
    for k in ("64", "16384"):
        f = Path(gate_dir) / f"gate-k{k}-s{seed}.json"
        out[k] = bool(json.loads(f.read_text())["dead_gate"]) if f.exists() else None
    return out


def mechanism_sentence(seeds, word):
    """ADDENDUM-1 (d), (e): which mechanism words a PASS may use. The dead-gate flags and the constant-g control decide."""
    if not word.startswith("PASS"):
        return "no mechanism claim (not a PASS)"
    flags = [v for x in seeds for v in seeds[x].get("gate_dead", {None: None}).values()]
    if any(f is None for f in flags):
        return "PASS without a complete dead-gate check: no settle-gate mechanism claim"
    if any(flags):
        return "PASS, but the gate is dead (std of g below 0.02 on all sets) at a checkpoint: read as the loop with a constant damping, no settle-gate mechanism claim"
    ctl = [seeds[x].get("h3_minus_control") for x in seeds]
    if any(c is None for c in ctl):
        return "PASS without the constant-g control: mechanism not separated from damping (control not run)"
    if all(c >= CONTROL_MARGIN for c in ctl):
        return "the per-cell settle gate beats plain damping (constant g = 0.9) by at least 5 F_eq points in both seeds"
    return "mechanism not separated from damping: H3 is less than 5 F_eq points above the constant-g = 0.9 control in at least one seed"


def build(split, h3_dir, loop_fmt, plain_fmt, sleep_dir=None, control_dir=None, gate_dir=None):
    res = {"split": split, "seeds": {}}
    for seed in (0, 1):
        h3 = R.summary(*R.load(Path(h3_dir) / f"h3-pre-s{seed}"), split)
        fr = R.summary(*R.load(Path(h3_dir) / f"h3-fresh-s{seed}"), split)
        lp = R.summary(*R.load(loop_fmt.format(seed=seed)), split)
        pl = R.summary(*R.load(plain_fmt.format(seed=seed)), split)
        draws = None
        if sleep_dir:
            draws = json.loads((Path(sleep_dir) / f"sleep-draws-s{seed}.json").read_text())
        row = seed_row(h3, fr, lp, pl, draws)
        if gate_dir:
            row["gate_dead"] = gate_flags(gate_dir, seed)
        if control_dir:
            ct = R.summary(*R.load(Path(control_dir) / f"h3c-pre-s{seed}"), split)
            row["control"] = ct
            row["h3_minus_control"] = h3["F_eq"] - ct["F_eq"]
        res["seeds"][str(seed)] = row
    return res


def main(split, h3_dir, loop_fmt, plain_fmt, out, sleep_dir=None, control_dir=None, gate_dir=None):
    res = build(split, h3_dir, loop_fmt, plain_fmt, sleep_dir, control_dir, gate_dir)
    if split == "holdout":
        res["verdict"], res["failing_gates"] = verdict(res["seeds"])
        res["mechanism_sentence"] = mechanism_sentence(res["seeds"], res["verdict"])
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for seed, row in res["seeds"].items():
        print(f"seed {seed}: F_eq h3 {row['h3']['F_eq']:.2f}, fresh {row['h3_fresh']['F_eq']:.2f}, "
              f"loop {row['loop']['F_eq']:.2f}, plain {row['plain']['F_eq']:.2f}; h3-loop {row['F_eq_minus_loop']:+.2f}; "
              f"F_few h3 {row['h3']['F_few']:.2f} loop {row['loop']['F_few']:.2f} ({row['F_few_minus_loop']:+.2f})"
              + (f"; h3-control {row['h3_minus_control']:+.2f}" if "h3_minus_control" in row else ""))
    if split == "holdout":
        print("verdict:", res["verdict"], res["failing_gates"])
        print("mechanism:", res["mechanism_sentence"])


# ------------------------------ self-test ------------------------------
def _sm(f_eq, f_few, sums=190, grids=190, sleep_ok=True, weights=1_645_984):
    return {"F_eq": f_eq, "F_few": f_few, "old_before": {"sums4": sums, "grids5": grids}, "weights": weights}


def _draws(h3, loop):
    """h3, loop: {branch: {kind: [3 counts]}}"""
    return {"h3": h3, "loop": loop}


def selftest():
    loop = _sm(51.0, 14.0, 200, 200, weights=1_645_726)
    plain, fresh = _sm(33.8, 3.0), _sm(21.0, 2.0)
    same = {"64": {"sums4": [150, 152, 148], "grids5": [100, 99, 101]}, "16384": {"sums4": [80, 82, 78], "grids5": [90, 91, 89]}}
    broken = {"64": {"sums4": [100, 102, 98], "grids5": [100, 99, 101]}, "16384": {"sums4": [80, 82, 78], "grids5": [90, 91, 89]}}
    # 1. the two-seed case of REVIEW X2: seed 0 gains +12 and breaks a sleep gate, seed 1 gains +12 and passes everything.
    win = _sm(63.0, 22.0, 199, 199)
    r0 = seed_row(win, fresh, loop, plain, _draws(broken, same))       # sums after the 64 sleep: 100 against 150, far outside the margin
    r1 = seed_row(win, fresh, loop, plain, _draws(same, same))
    assert r0["gates"]["sleep64_old_mean3_margin"] is False and r0["maze_gain_breaking_old_gate"]
    assert r1["all_judged_gates"] and not r1["maze_gain_breaking_old_gate"]
    seeds = {"0": r0, "1": r1}
    orig_rejected = all(seeds[x]["F_eq_minus_loop"] <= 0 for x in seeds) or any(seeds[x]["maze_gain_breaking_old_gate"] for x in seeds)
    word, failing = verdict(seeds)
    assert orig_rejected is True, "the ORIGINAL 'any' reading calls this pair REJECTED"
    assert word == "NOT PROMOTED", word                                 # the addendum: every gaining seed must break, seed 1 does not
    assert failing["0"] == ["sleep64_old_mean3_margin"] and failing["1"] == []
    # 2. both seeds gain and both break -> REJECTED; neither gains -> REJECTED; a clean double win -> PASS
    assert verdict({"0": r0, "1": seed_row(win, fresh, loop, plain, _draws(broken, same))})[0] == "REJECTED"
    flat = _sm(50.0, 13.0, 200, 200)
    assert verdict({x: seed_row(flat, fresh, loop, plain, _draws(same, same)) for x in "01"})[0] == "REJECTED"
    assert verdict({x: seed_row(win, fresh, loop, plain, _draws(same, same)) for x in "01"})[0] == "PASS"
    # 3. F_few is a required row: F_eq +12 in both seeds but F_few only +3 over the loop -> not a PASS
    low_few = _sm(63.0, 17.0, 199, 199)
    rr = {x: seed_row(low_few, fresh, loop, plain, _draws(same, same)) for x in "01"}
    assert rr["0"]["gates"]["F_few_loop_plus5"] is False and verdict(rr)[0] == "NOT PROMOTED"
    # 4. sleeps skipped: report-only. A clean win then reads "PASS (sleep gates not judged)"; a skipped gate cannot make a gain "breaking"
    skipped = {x: seed_row(win, fresh, loop, plain, None) for x in "01"}
    assert all(skipped[x]["gates"][k] is None for x in "01" for k in SLEEP_KEYS)
    assert verdict(skipped)[0] == "PASS (sleep gates not judged)"
    assert not any(skipped[x]["maze_gain_breaking_old_gate"] for x in "01")
    # 5. the margin: max(6, 2 x SE); a 4-count shortfall inside the floor passes, a 9-count one with tight draws fails,
    #    and wide draws (SE large) widen the margin so the same 9-count shortfall passes
    tight_h = {"sums4": [141, 141, 141], "grids5": [100, 100, 100]}
    tight_l = {"sums4": [150, 150, 150], "grids5": [100, 100, 100]}
    assert draw_gate(tight_h, tight_l)[0] is False                      # 141 vs 150, margin 6
    near_h = {"sums4": [146, 146, 146], "grids5": [100, 100, 100]}
    assert draw_gate(near_h, tight_l)[0] is True                        # 146 vs 150, margin 6
    wide_h = {"sums4": [120, 141, 162], "grids5": [100, 100, 100]}
    wide_l = {"sums4": [130, 150, 170], "grids5": [100, 100, 100]}
    ok, det = draw_gate(wide_h, wide_l)
    assert ok and det["sums4"]["margin"] > 6 and abs(det["sums4"]["h3_mean"] - 141) < 1e-9, det
    # 6. input checks
    for bad in ({"sums4": [1, 2], "grids5": [1, 2, 3]}, {"sums4": [1, 2, 3.0], "grids5": [1, 2, 3]}, {"sums4": [1, 2, 201], "grids5": [1, 2, 3]}):
        try:
            draw_gate(bad, tight_l)
            raise AssertionError("bad draws accepted")
        except ValueError:
            pass
    # 7. the mechanism sentence: dead-gate flags first, then the constant-g control
    for x in "01":
        rr[x]["h3_minus_control"] = 6.0
        rr[x]["gate_dead"] = {"64": False, "16384": False}
    assert "beats plain damping" in mechanism_sentence(rr, "PASS")
    rr["1"]["h3_minus_control"] = 4.9
    assert "not separated from damping" in mechanism_sentence(rr, "PASS")
    assert mechanism_sentence(rr, "NOT PROMOTED") == "no mechanism claim (not a PASS)"
    rr["1"]["h3_minus_control"] = 6.0
    rr["0"]["gate_dead"]["16384"] = True
    assert "gate is dead" in mechanism_sentence(rr, "PASS")
    rr["0"]["gate_dead"]["16384"] = None
    assert "complete dead-gate check" in mechanism_sentence(rr, "PASS")
    assert "complete dead-gate check" in mechanism_sentence({"0": {}, "1": {}}, "PASS")
    ctl_missing = {x: {"gate_dead": {"64": False, "16384": False}} for x in "01"}
    assert "control not run" in mechanism_sentence(ctl_missing, "PASS")
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
        sys.exit(0)
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), required=True)
    p.add_argument("--h3", required=True, help="folder holding h3-{pre,fresh}-s{seed}")
    p.add_argument("--loop", required=True, help="baseline loop/pre run folder, with {seed}")
    p.add_argument("--plain", required=True, help="baseline plain/pre run folder, with {seed}")
    p.add_argument("--out", required=True)
    p.add_argument("--sleep-draws", default=None, help="folder holding sleep-draws-s{seed}.json (3 draws per branch); without it marks 4 are report-only")
    p.add_argument("--control", default=None, help="folder holding h3c-pre-s{seed} (the constant-g = 0.9 control)")
    p.add_argument("--gate-reports", default=None, help="folder holding gate-k64-s{seed}.json and gate-k16384-s{seed}.json (gate_report_v2)")
    a = p.parse_args()
    main(a.split, a.h3, a.loop, a.plain, a.out, a.sleep_draws, a.control, a.gate_reports)
