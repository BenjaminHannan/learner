#!/usr/bin/env python3
"""Addendum-1 arithmetic for the held-out-kinds test (helper H10, 2026-09-28). Pure python, no torch.

Text: artifacts/claude-dir-h1-heldout-20260928/ADDENDUM-1.md. The sealed marks (PASSMARKS.md, scripts/claude_dir_h1_marks.py) are
imported, not edited. Two additions, both computed from the same raw dev files (runs/<kind>/<arm>-s<seed>-<init>/adapt.json):

  H1-a  V3 usable ladder, tightened: in at least one seed, the practised loop AND the fresh loop are each strictly between 10% and
        90% on the SAME at least three rungs of the dev graded panel (a rung counts only when both arms are in the band on it).
  H1-b  validity row: practised plain accuracy at k = 16,384 on dev, per seed. Below 90% (fewer than 270 of 300) in either seed:
        the plain comparisons (M1, M2b) are labelled "expressivity"; M2 (vs the fresh loop) carries the claim.

  python3 -B scripts/claude_dir_h1_marks_add1.py selftest
  python3 -B scripts/claude_dir_h1_marks_add1.py check  --kind graph|rank    writes ADDENDUM1-CHECK-<kind>.json (dev files only)
  python3 -B scripts/claude_dir_h1_marks_add1.py rollup                      prints the sentence Ben may quote (needs both kinds' check and SCORE files)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h1_marks as M  # noqa: E402  (sealed; imported, never edited)

ART = M.ART
RUNGS = M.RUNGS
NEED_SHARED = 3                 # ADDENDUM-1 (a): shared rungs strictly inside the band, per seed
NEED_SEEDS = 1                  # ADDENDUM-1 (a): in at least this many seeds (the sealed V3 also says "at least one seed")
PLAIN_MIN_PCT = 90.0            # ADDENDUM-1 (b): practised plain at k = 16,384 below this -> "expressivity"
LOOP, FRESH, PLAIN = "loop-pre", "loop-fresh", "plain-pre"


def in_band(c, n):
    """strictly above 10% and strictly below 90% (the sealed V3 band)."""
    return M.V3_LO * n < c < M.V3_HI * n


def shared_rungs(dev, seed, n=300):
    """rungs on which the practised loop and the fresh loop are both inside the band, in this seed."""
    a, b = dev[(seed, LOOP)], dev[(seed, FRESH)]
    return [k for k, x, y in zip(RUNGS, a, b) if in_band(x, n) and in_band(y, n)]


def v3_add1(dev, n=300, need_seeds=NEED_SEEDS):
    per = {f"s{s}": shared_rungs(dev, s, n) for s in (0, 1)}
    good = sum(len(v) >= NEED_SHARED for v in per.values())
    return good >= need_seeds, per


def plain_row(dev, n=300):
    """practised plain right answers at k = 16,384 on dev, per seed, and the label the row gives."""
    rows = {f"s{s}": {"right": dev[(s, PLAIN)][-1], "n": n, "pct": round(100.0 * dev[(s, PLAIN)][-1] / n, 1)}
            for s in (0, 1)}
    expressive = any(100.0 * r["right"] / n < PLAIN_MIN_PCT for r in rows.values())
    return rows, ("expressivity" if expressive else "few-example")


def status(dev, n=300):
    ok_any, per = v3_add1(dev, n, 1)
    ok_both, _ = v3_add1(dev, n, 2)
    plain, label = plain_row(dev, n)
    return {"V3_sealed": M.v3(dev, n)[0], "V3_add1": v3_add1(dev, n)[0], "V3_add1_any_seed": ok_any,
            "V3_add1_both_seeds_report_only": ok_both, "shared_rungs_by_seed": per,
            "practised_plain_k16384_dev": plain, "plain_comparison_label": label}


def sentence(verdicts):
    """verdicts: {kind: {"advantage": PASS|REFUTED|NOT-SHOWN|INCONCLUSIVE, "label": few-example|expressivity}}.
    The sealed roll-up with one qualifier: a kind labelled expressivity may be quoted only against the fresh loop."""
    adv = {k: v["advantage"] for k, v in verdicts.items()}
    refuted = sorted(k for k, a in adv.items() if a == "REFUTED")
    if refuted:
        return "mazes-only so far; refuted on " + ", ".join(refuted)
    full = sorted(k for k, v in verdicts.items() if v["advantage"] == "PASS" and v["label"] == "few-example")
    fresh_only = sorted(k for k, v in verdicts.items() if v["advantage"] == "PASS" and v["label"] == "expressivity")
    if len(full) == len(verdicts):
        return "shown on mazes and on two further held-out kinds, in two seeds each"
    if full or fresh_only:
        parts = []
        if full:
            parts.append("shown on mazes and on " + " and ".join(full) + ", in two seeds each")
        if fresh_only:
            parts.append("on " + " and ".join(fresh_only) + " the practised loop learns from fewer examples than a fresh looped net "
                         "(M2, two seeds); the same-size plain net comparison there is labelled expressivity and is not quoted")
        return "; ".join(parts)
    return "not shown on a further kind (reported as mazes-only so far)"


def check(kind):
    path = ART / f"ADDENDUM1-CHECK-{kind}.json"
    if path.exists():
        raise FileExistsError("addendum-1 check already written for this kind")
    dev, n = M.load_counts(kind, "adapt")
    res = {"kind": kind, "n": n, **status(dev, n)}
    gate_file = ART / f"DEV-GATE-{kind}.json"
    res["sealed_gate_verdict"] = json.loads(gate_file.read_text())["verdict"] if gate_file.exists() else "no DEV-GATE file"
    res["addendum_dev_verdict"] = "PASS" if res["sealed_gate_verdict"] == "PASS" and res["V3_add1"] else "INCONCLUSIVE"
    res["note"] = ("INCONCLUSIVE here means: no kind verdict and no roll-up credit, even if the sealed job already opened the holdout; "
                   "the holdout numbers are still reported as they stand")
    path.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("kind", "V3_sealed", "V3_add1", "shared_rungs_by_seed", "plain_comparison_label",
                                          "addendum_dev_verdict")}))


def rollup():
    verdicts = {}
    for kind in ("graph", "rank"):
        chk = json.loads((ART / f"ADDENDUM1-CHECK-{kind}.json").read_text())
        adv = "INCONCLUSIVE"
        if chk["addendum_dev_verdict"] == "PASS":
            adv = json.loads((ART / f"SCORE-{kind}.json").read_text())["advantage_verdict"]
        verdicts[kind] = {"advantage": adv, "label": chk["plain_comparison_label"]}
    print(json.dumps({"kinds": verdicts, "sentence": sentence(verdicts)}, indent=2))


# ------------------------------ self-test ------------------------------
def _recount_maze_dev():
    """the maze dev ladders from the raw equal-practice files, if present (they are on main)."""
    base = ART.parents[0] / "claude-fewex-20260927" / "eq-runs"
    out = {}
    for seed in (0, 1):
        for arm in (LOOP, FRESH, PLAIN, "plain-fresh"):
            f = base / f"{arm.replace('-', '-s%d-' % seed)}" / "adapt.json"
            if not f.exists():
                return None
            rungs = json.loads(f.read_text())["rungs"]
            out[(seed, arm)] = [rungs[str(k)]["9"]["right"] for k in RUNGS]
    return out


def selftest():
    # 1. the calibration on the published maze dev ladders (numbers copied from RESULTS-EQ.md into the sealed marks script)
    st = status(M.MAZE_DEV)
    assert st["shared_rungs_by_seed"] == {"s0": [64, 256, 4096], "s1": [64]}, st["shared_rungs_by_seed"]
    assert st["V3_sealed"] and st["V3_add1"] and st["V3_add1_any_seed"] and not st["V3_add1_both_seeds_report_only"]
    assert st["practised_plain_k16384_dev"] == {"s0": {"right": 210, "n": 300, "pct": 70.0},
                                                "s1": {"right": 215, "n": 300, "pct": 71.7}}, st["practised_plain_k16384_dev"]
    assert st["plain_comparison_label"] == "expressivity"
    # 2. the same shared-rung sets recomputed from the raw eq-runs files, when the folder is present
    raw = _recount_maze_dev()
    if raw is not None:
        assert raw == M.MAZE_DEV, "raw eq-runs dev ladders differ from the copy in the sealed marks script"
        assert status(raw) == st
        print("raw maze dev ladders (8 of 8 arm-seeds) equal the sealed copy")
    else:
        print("raw eq-runs not found: raw recount skipped")
    # 3. the H1-a case: only the fresh loop sits in the band, the practised loop is at the ceiling; sealed V3 passes, add1 fails
    ceiling = {(s, a): [300] * 8 for s in (0, 1) for a in M.ARMS}
    for s in (0, 1):
        ceiling[(s, FRESH)] = [0, 20, 60, 100, 150, 120, 140, 160]
    assert M.v3(ceiling)[0] and not v3_add1(ceiling)[0]
    # 4. a practised loop that is at 0 on every rung: same
    floor = {k: (v if k[1] != LOOP else [0] * 8) for k, v in ceiling.items()}
    assert M.v3(floor)[0] and not v3_add1(floor)[0]
    # 5. strict band: 30 and 270 of 300 are outside, 31 and 269 inside; three shared rungs are needed, two are not enough
    assert not in_band(30, 300) and in_band(31, 300) and in_band(269, 300) and not in_band(270, 300)
    two = {(s, a): [31, 31, 0, 0, 0, 0, 0, 0] for s in (0, 1) for a in (LOOP, FRESH)}
    three = {(s, a): [31, 31, 31, 0, 0, 0, 0, 0] for s in (0, 1) for a in (LOOP, FRESH)}
    for d in (two, three):
        d.update({(s, a): [0] * 8 for s in (0, 1) for a in (PLAIN, "plain-fresh")})
    assert not v3_add1(two)[0] and v3_add1(three)[0]
    # 6. the plain row: exactly 270 of 300 is not below 90 -> few-example; 269 -> expressivity; either seed decides
    ok = {(s, PLAIN): [0] * 7 + [270] for s in (0, 1)}
    assert plain_row(ok)[1] == "few-example"
    ok[(1, PLAIN)] = [0] * 7 + [269]
    assert plain_row(ok)[1] == "expressivity"
    # 7. the roll-up sentence
    full = {"graph": {"advantage": "PASS", "label": "few-example"}, "rank": {"advantage": "PASS", "label": "few-example"}}
    assert sentence(full) == "shown on mazes and on two further held-out kinds, in two seeds each"
    mixed = {"graph": {"advantage": "PASS", "label": "expressivity"}, "rank": {"advantage": "PASS", "label": "few-example"}}
    s = sentence(mixed)
    assert "shown on mazes and on rank" in s and "graph the practised loop learns from fewer examples than a fresh looped net" in s
    assert sentence({"graph": {"advantage": "REFUTED", "label": "few-example"},
                     "rank": {"advantage": "PASS", "label": "few-example"}}) == "mazes-only so far; refuted on graph"
    assert sentence({"graph": {"advantage": "INCONCLUSIVE", "label": "few-example"},
                     "rank": {"advantage": "NOT-SHOWN", "label": "few-example"}}).startswith("not shown")
    print("selftest ok")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "check", "rollup"))
    p.add_argument("--kind", choices=("graph", "rank"))
    a = p.parse_args()
    {"selftest": selftest, "rollup": rollup}.get(a.cmd, lambda: check(a.kind))()


if __name__ == "__main__":
    main()
