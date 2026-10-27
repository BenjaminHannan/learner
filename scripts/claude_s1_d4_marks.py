#!/usr/bin/env python3
"""S1 marks: reads the baseline and D4-arm dev records and applies artifacts/claude-s1-d4-20260929/PASSMARKS.md.

    python -B scripts/claude_s1_d4_marks.py selftest
    python -B scripts/claude_s1_d4_marks.py judge [--out FILE]

No torch: it only reads `adapt.json` (dev 9x9 counts) and optional `vote.json`. PASSMARKS.md wins if this script and the
page disagree. Loading, p9 and F scores are H12's helpers, imported unedited. The holdout is never read here.
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
LOOP_BASE = "artifacts/claude-fewex-20260927/eq-runs/loop-s{seed}-pre/adapt.json"
PLAIN_BASE = "artifacts/claude-fewex-20260927/eq-runs/plain-s{seed}-pre/adapt.json"
LOOP_ARM = "artifacts/claude-s1-d4-20260929/eq-runs/s1-loop-pre-s{seed}/adapt.json"
PLAIN_ARM = "artifacts/claude-s1-d4-20260929/eq-runs/s1-plain-pre-s{seed}/adapt.json"
RUNGS, FEW = H.RUNGS, H.FEW
# PASSMARKS "Marks" (fixed before any D4 score; the sweep's synthesis section 3 numbers, kept by the Director's ruling)
G_EQ_MEAN, G_EQ_SEED = 8.0, 4.0
G_FEW_MEAN, G_FEW_SEED = 10.5, 5.0
GAP_MIN = 17.2 - 3.3
GAP_SHRINK_WRONG = 4.0
A2_HURT = 8.5            # F_few not hurt: Delta >= -8.5 in both seeds
EPS = 1e-9


def control(run, key):
    """Loop control: the higher of the learned and fixed-16 reads (the baseline's stop may be better or worse)."""
    f = H.f_all(run)[key]
    return max(f["learned"], f["fixed"])


def read(run, key, arm):
    f = H.f_all(run)[key]
    return f["learned"]


def marks(lb, la, pb, pa):
    """lb, la, pb, pa: dicts seed -> adapt.json for loop base, loop D4, plain base, plain D4."""
    rows = {"seeds": {}}
    d_eq, d_few, gaps, shrink = [], [], [], []
    for s in (0, 1):
        loop_eq, loop_few = H.f_all(la[s])["F_eq"]["learned"], H.f_all(la[s])["F_few"]["learned"]
        plain_eq, plain_few = H.f_all(pa[s])["F_eq"]["learned"], H.f_all(pa[s])["F_few"]["learned"]
        c_eq, c_few = control(lb[s], "F_eq"), control(lb[s], "F_few")
        pb_eq, pb_few = H.f_all(pb[s])["F_eq"]["learned"], H.f_all(pb[s])["F_few"]["learned"]
        gap_now, gap_before = loop_eq - plain_eq, c_eq - pb_eq
        d_eq.append(loop_eq - c_eq)
        d_few.append(loop_few - c_few)
        gaps.append(gap_now)
        shrink.append(gap_before - gap_now)
        rows["seeds"][str(s)] = {
            "loop_F_eq": {"control": round(c_eq, 3), "d4": round(loop_eq, 3), "delta": round(loop_eq - c_eq, 3)},
            "loop_F_few": {"control": round(c_few, 3), "d4": round(loop_few, 3), "delta": round(loop_few - c_few, 3)},
            "plain_F_eq": {"control": round(pb_eq, 3), "d4": round(plain_eq, 3), "delta": round(plain_eq - pb_eq, 3)},
            "plain_F_few": {"control": round(pb_few, 3), "d4": round(plain_few, 3), "delta": round(plain_few - pb_few, 3)},
            "gap_loop_minus_plain": {"before": round(gap_before, 3), "d4": round(gap_now, 3),
                                     "shrink": round(gap_before - gap_now, 3)}}
    m_eq, m_few = sum(d_eq) / 2, sum(d_few) / 2
    g_eq = m_eq >= G_EQ_MEAN - EPS and all(d >= G_EQ_SEED - EPS for d in d_eq)
    g_few = m_few >= G_FEW_MEAN - EPS and all(d >= G_FEW_SEED - EPS for d in d_few)
    rows["G"] = {"F_eq_delta_by_seed": [round(x, 3) for x in d_eq], "F_eq_mean": round(m_eq, 3), "F_eq_pass": g_eq,
                 "F_few_delta_by_seed": [round(x, 3) for x in d_few], "F_few_mean": round(m_few, 3), "F_few_pass": g_few,
                 "pass": g_eq or g_few}
    rows["GAP"] = {"gap_by_seed": [round(x, 3) for x in gaps], "need_each": round(GAP_MIN, 3),
                   "pass": all(g >= GAP_MIN - EPS for g in gaps)}
    rows["A2"] = {"F_few_delta_by_seed": [round(x, 3) for x in d_few], "need_each": -A2_HURT,
                  "pass": all(d >= -A2_HURT - EPS for d in d_few)}
    rows["wrong_reasons"] = {
        "loop_gain_under_4_both_seeds": all(d < G_EQ_SEED for d in d_eq),
        "gap_shrinks_over_4_both_seeds": all(x > GAP_SHRINK_WRONG for x in shrink)}
    rows["plain_reading"] = {"plain_passes_G_alone": {
        "F_eq": all(rows["seeds"][str(s)]["plain_F_eq"]["delta"] >= G_EQ_SEED - EPS for s in (0, 1))
        and sum(rows["seeds"][str(s)]["plain_F_eq"]["delta"] for s in (0, 1)) / 2 >= G_EQ_MEAN - EPS}}
    if any(rows["wrong_reasons"].values()):
        word = "WRONG"
    elif rows["G"]["pass"] and rows["GAP"]["pass"] and rows["A2"]["pass"]:
        word = "WORKS WITH A MAZE-SPECIFIC SHORTCUT"
    else:
        word = "NOT SHOWN"
    rows["word"] = word
    return rows


def validity(lb, la, pb, pa):
    """V1..V4 (PASSMARKS 'Validity'). Returns (ok, list of failures)."""
    bad = []
    for name, base, arm in (("loop", lb, la), ("plain", pb, pa)):
        for s in (0, 1):
            b, a = base[s], arm[s]
            for key in ("weights", "fixed_depth", "lr", "support_sha256", "optimizer_updates_per_rung", "rung_batches"):
                if b[key] != a[key]:
                    bad.append(f"V1 {name} s{s}: {key} differs ({b[key]} vs {a[key]})")
            if a["optimizer_updates_per_rung"] != 2048:
                bad.append(f"V2 {name} s{s}: not 2048 updates per rung")
            if abs(b["rungs"]["0"]["9"]["right"] - a["rungs"]["0"]["9"]["right"]) > 1:
                bad.append(f"V3 {name} s{s}: cold k=0 count differs by more than 1")
            for kind in ("sums4", "grids5"):
                if abs(b["old"]["before"][kind]["right"] - a["old"]["before"][kind]["right"]) > 1:
                    bad.append(f"V3 {name} s{s}: old-kind {kind} before differs by more than 1")
            if a["support_panel_overlap"] != 0 or a["support_unique_layouts"] != 16384:
                bad.append(f"V4 {name} s{s}: pool overlap/unique count wrong")
    return not bad, bad


def load_all():
    g = lambda pat: {s: H.load(pat, s) for s in (0, 1)}
    return g(LOOP_BASE), g(LOOP_ARM), g(PLAIN_BASE), g(PLAIN_ARM)


def vote_report():
    out = {}
    for arm in ("loop", "plain"):
        for s in (0, 1):
            p = ROOT / f"artifacts/claude-s1-d4-20260929/eq-runs/s1-{arm}-pre-s{s}/vote.json"
            if p.exists():
                out[f"{arm}-s{s}"] = json.loads(p.read_text())
    return out


def judge(out=None):
    lb, la, pb, pa = load_all()
    ok, bad = validity(lb, la, pb, pa)
    res = {"valid": ok, "invalid_because": bad}
    if ok:
        res.update(marks(lb, la, pb, pa))
    res["report_only_vote"] = vote_report()
    if out:
        Path(out).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps(res, indent=2, sort_keys=True))
    return res


# ---- selftest with made-up records ----------------------------------------------------------

def fake(counts9, fixed=None, cold=0):
    run = {"weights": 1, "fixed_depth": 16, "lr": 1e-3, "support_sha256": "x", "optimizer_updates_per_rung": 2048,
           "rung_batches": 512, "support_panel_overlap": 0, "support_unique_layouts": 16384,
           "old": {"before": {"sums4": {"right": 200}, "grids5": {"right": 200}}}, "rungs": {"0": {"9": {"right": cold}}}}
    fixed = fixed or counts9
    for k, c, f in zip(RUNGS, counts9, fixed):
        run["rungs"][str(k)] = {"9": {"right": c, "fixed_right": f}}
    return run


def selftest():
    def curve(level):
        return [int(level * 3)] * 8      # level in points -> count of 300 on every rung
    base_loop = {s: fake(curve(50)) for s in (0, 1)}
    base_plain = {s: fake(curve(33)) for s in (0, 1)}
    def run(loop_lvl, plain_lvl):
        return marks(base_loop, {s: fake(curve(loop_lvl)) for s in (0, 1)}, base_plain,
                     {s: fake(curve(plain_lvl)) for s in (0, 1)})
    r = run(60, 34)                                   # loop +10, plain +1: gap 26
    assert r["word"] == "WORKS WITH A MAZE-SPECIFIC SHORTCUT", r
    r = run(60, 60)                                   # plain gains as much: gap 0, shrink 17 -> WRONG
    assert r["word"] == "WRONG" and r["wrong_reasons"]["gap_shrinks_over_4_both_seeds"], r
    r = run(51, 34)                                   # loop +1
    assert r["word"] == "WRONG" and r["wrong_reasons"]["loop_gain_under_4_both_seeds"], r
    r = run(56, 34)                                   # +6: over 4 each, mean under 8 -> NOT SHOWN
    assert r["word"] == "NOT SHOWN" and not r["G"]["pass"], r
    # one seed only: seed 0 +12, seed 1 +2 -> mean 7 (< 8) and seed floor fails
    la = {0: fake(curve(62)), 1: fake(curve(52))}
    r = marks(base_loop, la, base_plain, {s: fake(curve(34)) for s in (0, 1)})
    assert r["word"] == "NOT SHOWN", r
    # F_few route: gain only on few rungs (+12 points on k=1..64 rungs, 0 elsewhere -> F_eq +6, F_few +12)
    few = [186] * 4 + [150] * 4
    la = {s: fake(few) for s in (0, 1)}
    r = marks(base_loop, la, base_plain, {s: fake(curve(34)) for s in (0, 1)})
    assert r["G"]["F_few_pass"] and not r["G"]["F_eq_pass"] and r["word"] == "WORKS WITH A MAZE-SPECIFIC SHORTCUT", r
    # A2: few-shot badly hurt blocks PASS even if F_eq gains
    hurt = [90, 90, 90, 90] + [200] * 4                # F_few 30 vs 50 base; F_eq = (120+800)/8/3 ...
    la = {s: fake(hurt) for s in (0, 1)}
    r = marks(base_loop, la, base_plain, {s: fake(curve(34)) for s in (0, 1)})
    assert not r["A2"]["pass"] and r["word"] != "WORKS WITH A MAZE-SPECIFIC SHORTCUT", r
    # validity catches a wrong update count and a support mismatch
    bad_arm = {s: fake(curve(60)) for s in (0, 1)}
    bad_arm[1]["optimizer_updates_per_rung"] = 1024
    ok, why = validity(base_loop, bad_arm, base_plain, {s: fake(curve(34)) for s in (0, 1)})
    assert not ok and any("V2" in w for w in why), why
    bad_arm = {s: fake(curve(60)) for s in (0, 1)}
    bad_arm[0]["support_sha256"] = "y"
    ok, why = validity(base_loop, bad_arm, base_plain, {s: fake(curve(34)) for s in (0, 1)})
    assert not ok and any("V1" in w for w in why), why
    # the real baselines must load and reproduce the reference numbers (dev F_eq of the sealed baseline)
    lb = {s: H.load(LOOP_BASE, s) for s in (0, 1)}
    pb = {s: H.load(PLAIN_BASE, s) for s in (0, 1)}
    for s, want in ((0, 51.21), (1, 51.67)):
        assert abs(control(lb[s], "F_eq") - want) < 0.01, (s, control(lb[s], "F_eq"))
    for s, want in ((0, 34.04), (1, 32.63)):
        assert abs(H.f_all(pb[s])["F_eq"]["learned"] - want) < 0.01, s
    print(json.dumps({"selftest": "ok"}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "judge"))
    p.add_argument("--out")
    a = p.parse_args()
    selftest() if a.cmd == "selftest" else judge(a.out)


if __name__ == "__main__":
    main()
