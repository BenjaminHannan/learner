#!/usr/bin/env python3
"""Exp 270b POST-SEAL panel scorer (new file, disclosed D3).

Scores the registered panel wave with the sealed devscore pipeline
(imported read-only), plus the ONE panel-dictated addition: symmetric
possessive-stem normalisation on subject spans.

Why (writer's spec, make_panel.py docstring): panel gold uses the exact raw
spans from the turn ("jamess", "tesss", "louiss", "selmas", ...), and "the
scorer normalises". A correct pipeline predicts the true name ("James"),
which matches raw-span gold only after possessive-s normalisation. The rule
is fixed and symmetric (applies identically to gold and predicted spans,
both arms, TEACH and ASK subjects; values untouched):
  strip ONE trailing "s" from a subject span iff it ends in "s" and is
  longer than 3 chars (after S.norm_subj lowercasing; "<user>" unaffected).

Symmetric-strip consequences (disclosed): glued raw spans ("jamess") count
the same as clean spans ("James") on BOTH arms, so M1 margin comes only
from frames the ear fails to emit (recall), not spans. The one known
artifact: a mangled span ("Iri" for "Iris", where the sealed normaliser
lacks "iris" in S_NAMES270b) still matches ("iri"=="iri") and counts HIT;
it is reported as a scorer-blind-spot note, not removed.

Marks (brief bars), arm A:
  M1 casual exact TEACH >= 30/40 and >= A261b+15
  M2 casual_q ASK >= 12/15
  M3 lower_trap wrong TEACH saves <= 1
  M4 clean 30/30 frames identical A vs A261b
  M5 0 new wrong TEACH saves vs A261b (normalised frames)
  M6 median added normaliser time <= 20 ms

Usage: python -B scripts/claude_type270b_panelscore.py --rows ROWS.jsonl --preds P --pyesA YA --pyesB YB --normmanifest N --theta 0.25 --out SCORE.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_score as S  # noqa: E402
import claude_type270b_devscore as D  # noqa: E402 (sealed, read-only)

_ORIG_NORM_SUBJ = S.norm_subj


def strip_subj(s):
    """S.norm_subj plus symmetric possessive-s strip (panel-dictated)."""
    n = _ORIG_NORM_SUBJ(s)
    if n not in ("<user>",) and len(n) > 3 and n.endswith("s"):
        return n[:-1]
    return n


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--pyesA", required=True)
    ap.add_argument("--pyesB", required=True)
    ap.add_argument("--normmanifest", required=True)
    ap.add_argument("--theta", type=float, default=0.25)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    S.norm_subj = strip_subj
    try:
        sys.argv = ["devscore", "--dev", a.rows, "--preds", a.preds,
                    "--pyesA", a.pyesA, "--pyesB", a.pyesB,
                    "--normmanifest", a.normmanifest, "--theta",
                    str(a.theta), "--out", a.out]
        rc = D.main()
    finally:
        S.norm_subj = _ORIG_NORM_SUBJ
    rep = json.loads(Path(a.out).read_text(encoding="utf-8"))
    m = rep["marks"]
    m1a, m1b = m["M1_casual_exact"]["A"], m["M1_casual_exact"]["A261b"]
    m1n = m["M1_casual_exact"]["n"]
    m2a, m2n = m["M2_ask_exact"]["A"], m["M2_ask_exact"]["n"]
    m3a = m["M3_trap_wrong_saves"]["A"]
    m4i, m4n = m["M4_clean_identical"]["identical"], m["M4_clean_identical"]["n"]
    m5n = m["M5_new_wrong_saves"]["n"]
    m6 = m["M6_norm_ms_median"]
    v = {"M1": (m1a >= 30 and (m1a - m1b) >= 15),
         "M2": (m2a >= 12),
         "M3": (m3a <= 1),
         "M4": (m4i == 30 and m4n == 30),
         "M5": (m5n == 0),
         "M6": (m6 <= 20)}
    v["ALL"] = all(v.values())
    print(f"PANEL VERDICT: M1 A {m1a}/{m1n} vs A261b {m1b}/{m1n} "
          f"margin {m1a - m1b} -> {'PASS' if v['M1'] else 'FAIL'}")
    print(f"M2 {m2a}/{m2n} -> {'PASS' if v['M2'] else 'FAIL'}; "
          f"M3 {m3a} -> {'PASS' if v['M3'] else 'FAIL'}; "
          f"M4 {m4i}/{m4n} -> {'PASS' if v['M4'] else 'FAIL'}; "
          f"M5 {m5n} {m['M5_new_wrong_saves']['ids']} -> "
          f"{'PASS' if v['M5'] else 'FAIL'}; "
          f"M6 {m6} -> {'PASS' if v['M6'] else 'FAIL'}")
    print("OVERALL:", "PASS" if v["ALL"] else "FAIL")
    rep["panel_verdict"] = v
    Path(a.out).write_text(json.dumps(rep, indent=1, default=str),
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
