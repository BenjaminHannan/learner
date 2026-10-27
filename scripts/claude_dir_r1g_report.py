#!/usr/bin/env python3
"""Race table and verdict for the general reach-channel design (artifacts/claude-dir-r1g-20260928/PASSMARKS.md). Pure standard library.

Marks and rules are those of the H3 test as amended by ADDENDUM-1 of artifacts/claude-dir-h3-design-20260928 (H10), with the H3-specific
parts (gate tensors, constant-g control, dead gate) replaced by this design's credit check. The summary arithmetic is the sparse race's
(scripts/claude_sparse_race.py, imported, not edited) and the three-draw sleep gate is the H3 add1 function (imported, not edited).

  python3 scripts/claude_dir_r1g_report.py selftest
  python3 scripts/claude_dir_r1g_report.py --split dev     --runs <eq-runs dir> --loop '<...>/loop-s{seed}-pre' --plain '<...>/plain-s{seed}-pre' --out dev-table.json
  python3 scripts/claude_dir_r1g_report.py --split holdout --runs ... [--sleep-draws DIR] [--credit DIR] [--use DIR]   (only after every dev run is committed)

runs dir holds r1g-pre-s{seed} and r1g-fresh-s{seed}. sleep-draws-s{seed}.json:
  {"seed": 0, "r1g": {"64": {"sums4": [a, b, c], "grids5": [a, b, c]}, "16384": {...}}, "loop": {"64": {...}, "16384": {...}}}   (counts of 200)
credit-s{seed}.json (claude_dir_r1g_credit.py): {"seed": s, "dev_9x9_on": n, "dev_9x9_off": m, ...}       use-s{seed}.json: {"seed": s, "mix_mean_abs": {"practice": x, "k16384": y}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h3_report_add1 as H  # noqa: E402  (draw_gate only)
import claude_sparse_race as R  # noqa: E402

KINDS = R.KINDS
FEW_MARGIN = 5.0
CREDIT_MIN_DROP = 30            # of 300: zeroing the reach features on the dev 9x9 panel at k = 1,024 must cost at least this many
UNUSED_BELOW = 1e-3             # mean |mix.weight| below this at practice AND at k = 16,384 = the channel was never used
SLEEP_KEYS = ("sleep64_old_mean3_margin", "sleep16384_old_mean3_margin")
OLD_KEYS = ("old_before_95", "old_before_within3_of_loop")


def seed_gates(r1, fr, lp, pl, draws=None):
    g = {"F_eq_loop_plus10": r1["F_eq"] >= lp["F_eq"] + 10,
         "F_eq_plain_plus5": r1["F_eq"] >= pl["F_eq"] + 5,
         "F_eq_fresh_plus5": r1["F_eq"] >= fr["F_eq"] + 5,
         "F_few_loop_plus5": r1["F_few"] >= lp["F_few"] + FEW_MARGIN,
         "old_before_95": all(r1["old_before"][k] >= 190 for k in KINDS),
         "old_before_within3_of_loop": all(r1["old_before"][k] >= lp["old_before"][k] - 6 for k in KINDS),
         "budget_within2pct": abs(r1["weights"] - lp["weights"]) <= .02 * lp["weights"]}
    detail = {}
    for br in ("64", "16384"):
        key = f"sleep{br}_old_mean3_margin"
        if draws is None:
            g[key] = None
        else:
            g[key], detail[br] = H.draw_gate(draws["r1g"][br], draws["loop"][br])
    return g, detail


def seed_row(r1, fr, lp, pl, draws=None):
    g, detail = seed_gates(r1, fr, lp, pl, draws)
    judged = {k: v for k, v in g.items() if v is not None}
    row = {"r1g": r1, "r1g_fresh": fr, "loop": lp, "plain": pl, "F_eq_minus_loop": r1["F_eq"] - lp["F_eq"],
           "F_few_minus_loop": r1["F_few"] - lp["F_few"], "gates": g, "sleep_draw_detail": detail,
           "sleep_gates_judged": all(g[k] is not None for k in SLEEP_KEYS), "all_judged_gates": all(judged.values())}
    row["gain"] = row["F_eq_minus_loop"] > 0
    row["maze_gain_breaking_old_gate"] = row["gain"] and not all(g[k] for k in OLD_KEYS + SLEEP_KEYS if g[k] is not None)
    return row


def verdict(seeds):
    s = seeds
    gaining = [x for x in s if s[x]["gain"]]
    rejected = all(s[x]["F_eq_minus_loop"] <= 0 for x in s) or (bool(gaining) and all(s[x]["maze_gain_breaking_old_gate"] for x in gaining))
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
    return word, {x: [k for k, v in s[x]["gates"].items() if v is False] for x in s}


def mechanism_sentence(seeds, word):
    """Which words a PASS may use. Report-only: never changes the verdict word."""
    if not word.startswith("PASS"):
        return "no mechanism claim (not a PASS)"
    drops = [seeds[x].get("credit_drop") for x in seeds]
    unused = [seeds[x].get("channel_unused") for x in seeds]
    if any(d is None for d in drops) or any(u is None for u in unused):
        return "PASS without a complete credit check: the design passed; no claim that the reach channel is the cause"
    if all(u for u in unused):
        return "PASS, but the reach channel was unused (mean |mix.weight| below 0.001 at practice and at k = 16,384, both seeds): the design passed; the reach channel is not the cause"
    if all(d >= CREDIT_MIN_DROP for d in drops):
        return "the reach channel passed: switching its features off at inference costs at least 30 of 300 dev 9x9 mazes at k = 1,024 in both seeds"
    return "the design passed; the reach channel is a bystander in at least one seed (switching it off costs fewer than 30 of 300 dev mazes at k = 1,024)"


def build(split, runs, loop_fmt, plain_fmt, sleep_dir=None, credit_dir=None, use_dir=None):
    res = {"split": split, "seeds": {}}
    for seed in (0, 1):
        r1 = R.summary(*R.load(Path(runs) / f"r1g-pre-s{seed}"), split)
        fr = R.summary(*R.load(Path(runs) / f"r1g-fresh-s{seed}"), split)
        lp = R.summary(*R.load(loop_fmt.format(seed=seed)), split)
        pl = R.summary(*R.load(plain_fmt.format(seed=seed)), split)
        draws = json.loads((Path(sleep_dir) / f"sleep-draws-s{seed}.json").read_text()) if sleep_dir else None
        row = seed_row(r1, fr, lp, pl, draws)
        if credit_dir:
            c = json.loads((Path(credit_dir) / f"credit-s{seed}.json").read_text())
            row["credit_drop"] = c["dev_9x9_on"] - c["dev_9x9_off"]
        if use_dir:
            u = json.loads((Path(use_dir) / f"use-s{seed}.json").read_text())["mix_mean_abs"]
            row["channel_unused"] = u["practice"] < UNUSED_BELOW and u["k16384"] < UNUSED_BELOW
        res["seeds"][str(seed)] = row
    return res


def main(split, runs, loop_fmt, plain_fmt, out, sleep_dir=None, credit_dir=None, use_dir=None):
    res = build(split, runs, loop_fmt, plain_fmt, sleep_dir, credit_dir, use_dir)
    if split == "holdout":
        res["verdict"], res["failing_gates"] = verdict(res["seeds"])
        res["mechanism_sentence"] = mechanism_sentence(res["seeds"], res["verdict"])
    Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    for seed, row in res["seeds"].items():
        print(f"seed {seed}: F_eq r1g {row['r1g']['F_eq']:.2f}, fresh {row['r1g_fresh']['F_eq']:.2f}, loop {row['loop']['F_eq']:.2f}, "
              f"plain {row['plain']['F_eq']:.2f}; r1g-loop {row['F_eq_minus_loop']:+.2f}; F_few r1g {row['r1g']['F_few']:.2f} "
              f"loop {row['loop']['F_few']:.2f} ({row['F_few_minus_loop']:+.2f})"
              + (f"; credit drop {row['credit_drop']} of 300" if "credit_drop" in row else ""))
    if split == "holdout":
        print("verdict:", res["verdict"], res["failing_gates"])
        print("mechanism:", res["mechanism_sentence"])


def _sm(f_eq, f_few, sums=190, grids=190, weights=1_654_198):
    return {"F_eq": f_eq, "F_few": f_few, "old_before": {"sums4": sums, "grids5": grids}, "weights": weights}


def selftest():
    loop = _sm(51.0, 14.0, 200, 200, weights=1_645_726)
    plain, fresh = _sm(33.8, 3.0), _sm(21.0, 2.0)
    same = {"64": {"sums4": [150, 152, 148], "grids5": [100, 99, 101]}, "16384": {"sums4": [80, 82, 78], "grids5": [90, 91, 89]}}
    broken = {"64": {"sums4": [100, 102, 98], "grids5": [100, 99, 101]}, "16384": same["16384"]}
    win = _sm(63.0, 22.0, 199, 199)
    r0 = seed_row(win, fresh, loop, plain, {"r1g": broken, "loop": same})
    r1 = seed_row(win, fresh, loop, plain, {"r1g": same, "loop": same})
    assert r0["gates"]["sleep64_old_mean3_margin"] is False and r0["maze_gain_breaking_old_gate"] and r1["all_judged_gates"]
    assert verdict({"0": r0, "1": r1})[0] == "NOT PROMOTED"                       # only one gaining seed breaks a gate
    assert verdict({"0": r0, "1": seed_row(win, fresh, loop, plain, {"r1g": broken, "loop": same})})[0] == "REJECTED"
    flat = _sm(50.0, 13.0, 200, 200)
    assert verdict({x: seed_row(flat, fresh, loop, plain, {"r1g": same, "loop": same}) for x in "01"})[0] == "REJECTED"
    assert verdict({x: seed_row(win, fresh, loop, plain, {"r1g": same, "loop": same}) for x in "01"})[0] == "PASS"
    low_few = seed_row(_sm(63.0, 17.0, 199, 199), fresh, loop, plain, {"r1g": same, "loop": same})   # F_few +3 only
    assert low_few["gates"]["F_few_loop_plus5"] is False and verdict({"0": low_few, "1": low_few})[0] == "NOT PROMOTED"
    skipped = {x: seed_row(win, fresh, loop, plain, None) for x in "01"}
    assert verdict(skipped)[0] == "PASS (sleep gates not judged)" and not any(skipped[x]["maze_gain_breaking_old_gate"] for x in "01")
    # size: 1,654,198 is +0.515%; a 3% net would fail mark 5
    assert seed_row(_sm(63, 22, 199, 199, weights=1_700_000), fresh, loop, plain, None)["gates"]["budget_within2pct"] is False
    # mechanism sentence
    ok = {x: {"credit_drop": 60, "channel_unused": False} for x in "01"}
    assert mechanism_sentence(ok, "PASS").startswith("the reach channel passed")
    ok["1"]["credit_drop"] = 29
    assert "bystander" in mechanism_sentence(ok, "PASS")
    ok["1"]["credit_drop"] = 60
    ok["0"]["channel_unused"] = ok["1"]["channel_unused"] = True
    assert "unused" in mechanism_sentence(ok, "PASS")
    assert "complete credit check" in mechanism_sentence({"0": {}, "1": {}}, "PASS")
    assert mechanism_sentence(ok, "NOT PROMOTED") == "no mechanism claim (not a PASS)"
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
        sys.exit(0)
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), required=True)
    p.add_argument("--runs", required=True, help="folder holding r1g-{pre,fresh}-s{seed}")
    p.add_argument("--loop", required=True)
    p.add_argument("--plain", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--sleep-draws", default=None)
    p.add_argument("--credit", default=None)
    p.add_argument("--use", default=None)
    a = p.parse_args()
    main(a.split, a.runs, a.loop, a.plain, a.out, a.sleep_draws, a.credit, a.use)
