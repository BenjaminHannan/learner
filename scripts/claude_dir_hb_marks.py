#!/usr/bin/env python3
"""Dev gate and holdout score for the fact-combining test (Director helper HB, 2026-09-28). Pure python, reads the eval JSON only.

Marks are in artifacts/claude-dir-hb-dates-20260928/PASSMARKS.md; every number below is copied from there and is not changed after any score.
Layout read:  RUNS/{loop,plain}-s{0,1}/{dev,hold}.json   (written by claude_dir_hb_run.py eval)

  python3 -B scripts/claude_dir_hb_marks.py gate  --runs DIR   -> DEV-GATE.json  (uses dev.json only)
  python3 -B scripts/claude_dir_hb_marks.py score --runs DIR   -> SCORE.json     (uses hold.json only; refuses unless DEV-GATE.json says PASS)
  python3 -B scripts/claude_dir_hb_marks.py selftest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SEEDS = (0, 1)
V1_LOOP_S0, V1_PLAIN_S0 = 270, 200
M1_MIN, M2_GAP, M3_MIN, M3_GAP, M4_MIN = 150, 30, 120, 15, 270
REF_A_MAX = 60


def load(runs, tag):
    out = {}
    for arm in ("loop", "plain"):
        for s in SEEDS:
            p = Path(runs) / f"{arm}-s{s}" / f"{tag}.json"
            d = json.loads(p.read_text())
            out[(arm, s)] = {k: v["right"] for k, v in d["splits"].items()}
    return out


def gate_from(r):
    v1 = {s: {"loop_s0": r[("loop", s)]["s0"], "plain_s0": r[("plain", s)]["s0"],
              "ok": r[("loop", s)]["s0"] >= V1_LOOP_S0 and r[("plain", s)]["s0"] >= V1_PLAIN_S0} for s in SEEDS}
    verdict = "PASS" if all(v["ok"] for v in v1.values()) else "INCONCLUSIVE"
    return {"V1_recall_control": v1, "verdict": verdict,
            "note": "INCONCLUSIVE means training did not reach the recall control; the holdout stays unopened."}


def score_from(r):
    per = {}
    for s in SEEDS:
        L, P = r[("loop", s)], r[("plain", s)]
        per[s] = {
            "counts": {"loop": L, "plain": P},
            "M1": {"ok": L["s1"] >= M1_MIN and L["s2"] >= M1_MIN, "loop_s1": L["s1"], "loop_s2": L["s2"], "need": M1_MIN},
            "M2": {"ok": L["s1"] - P["s1"] >= M2_GAP and L["s2"] - P["s2"] >= M2_GAP,
                   "gap_s1": L["s1"] - P["s1"], "gap_s2": L["s2"] - P["s2"], "need": M2_GAP},
            "M3": {"ok": L["s3"] >= M3_MIN and L["s3"] - P["s3"] >= M3_GAP, "loop_s3": L["s3"], "gap_s3": L["s3"] - P["s3"],
                   "need": [M3_MIN, M3_GAP]},
            "M4": {"ok": L["s0"] >= M4_MIN, "loop_s0": L["s0"], "need": M4_MIN},
            "cannot_combine": L["s1"] < REF_A_MAX or L["s2"] < REF_A_MAX,
            "no_better_than_plain": L["s1"] <= P["s1"] or L["s2"] <= P["s2"],
        }
    passed = all(per[s][m]["ok"] for s in SEEDS for m in ("M1", "M2", "M3", "M4"))
    ref_a = all(per[s]["cannot_combine"] for s in SEEDS)
    ref_b = all(per[s]["no_better_than_plain"] for s in SEEDS)
    verdict = "PASS" if passed else ("REFUTED-cannot-combine" if ref_a else ("REFUTED-no-better-than-plain" if ref_b else "NOT-SHOWN"))
    return {"per_seed": {str(s): per[s] for s in SEEDS}, "verdict": verdict}


def main():
    cmd = sys.argv[1]
    if cmd == "selftest":
        return selftest()
    runs = Path(sys.argv[sys.argv.index("--runs") + 1])
    if cmd == "gate":
        g = gate_from(load(runs, "dev"))
        (runs / "DEV-GATE.json").write_text(json.dumps(g, indent=1))
        print(json.dumps(g, indent=1))
    elif cmd == "score":
        g = json.loads((runs / "DEV-GATE.json").read_text())
        if g["verdict"] != "PASS":
            sys.exit("REFUSED: DEV-GATE.json is not PASS; the holdout stays unopened.")
        s = score_from(load(runs, "hold"))
        (runs / "SCORE.json").write_text(json.dumps(s, indent=1))
        print(json.dumps(s, indent=1))


def _fake(loop, plain):
    return {(a, s): dict(zip(("s0", "s1", "s2", "s3"), (loop if a == "loop" else plain)[s])) for a in ("loop", "plain") for s in SEEDS}


def selftest():
    good = _fake({0: (290, 200, 180, 150), 1: (285, 190, 170, 140)}, {0: (240, 100, 90, 60), 1: (230, 110, 80, 70)})
    assert score_from(good)["verdict"] == "PASS"
    assert gate_from(good)["verdict"] == "PASS"
    assert gate_from(_fake({0: (260, 0, 0, 0), 1: (290, 0, 0, 0)}, {0: (240, 0, 0, 0), 1: (240, 0, 0, 0)}))["verdict"] == "INCONCLUSIVE"
    assert gate_from(_fake({0: (290, 0, 0, 0), 1: (290, 0, 0, 0)}, {0: (199, 0, 0, 0), 1: (240, 0, 0, 0)}))["verdict"] == "INCONCLUSIVE"
    edge = _fake({0: (270, 150, 150, 120), 1: (270, 150, 150, 120)}, {0: (0, 120, 120, 105), 1: (0, 120, 120, 105)})
    assert score_from(edge)["verdict"] == "PASS"          # every bar is inclusive
    for bad in (_fake({0: (270, 149, 150, 120), 1: (270, 150, 150, 120)}, {0: (0, 100, 100, 100), 1: (0, 100, 100, 100)}),
                _fake({0: (269, 150, 150, 120), 1: (270, 150, 150, 120)}, {0: (0, 100, 100, 100), 1: (0, 100, 100, 100)}),
                _fake({0: (270, 150, 150, 119), 1: (270, 150, 150, 120)}, {0: (0, 100, 100, 100), 1: (0, 100, 100, 100)}),
                _fake({0: (270, 150, 150, 120), 1: (270, 150, 150, 120)}, {0: (0, 121, 100, 100), 1: (0, 100, 100, 100)})):
        assert score_from(bad)["verdict"] == "NOT-SHOWN", score_from(bad)["verdict"]
    assert score_from(_fake({0: (290, 40, 100, 50), 1: (290, 100, 30, 50)}, {0: (0, 10, 10, 10), 1: (0, 10, 10, 10)}))["verdict"] == "REFUTED-cannot-combine"
    assert score_from(_fake({0: (290, 100, 100, 50), 1: (290, 100, 100, 50)}, {0: (0, 100, 50, 10), 1: (0, 50, 100, 10)}))["verdict"] == "REFUTED-no-better-than-plain"
    print("selftest ok")


if __name__ == "__main__":
    main()
