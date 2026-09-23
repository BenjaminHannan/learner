#!/usr/bin/env python3
"""Experiment 166 -- G2 marks123 per-case diff vs base runs (Muse).

Compares artifacts/fable-me166-20260922/marks166 (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop166_agent.py --config
artifacts/fable-me166-20260922/loop166-config.json --out <marks166>`
run) per-case against:
  (a) the BASE agent's marks162b
       (artifacts/fable-plural162b-20260922/marks162b, read-only) for every
       suite it completed, and
  (b) the sealed loop150 marks150
       (artifacts/fable-fix150-20260922/marks150, read-only) for the suites
       162b compared against marks150 (p3/rt110/q4) -- same fallback 162b's
       brief allows.

ZERO per-case moves predicted: the 166 me teach/ask frames fire only on
first-person "my" possessives (0 such inputs in any suite per the pre-seal
scan), and the reply rewrite only fires on me-claimed turns. Soak/rt110
flakes under heavy load are a known mailbox race: re-run that suite once in
the open and report both. Any other move fails G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166_agent.py \\
    --config artifacts/fable-me166-20260922/loop166-config.json \\
    --out artifacts/fable-me166-20260922/marks166 --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"
ART166 = ROOT / "artifacts" / "fable-me166-20260922"
REF162B = ART162B / "marks162b"
REF150 = ART150 / "marks150"
NEW = ART166 / "marks166"

# Suites 162b completed -> compare vs marks162b; suites 162b compared vs
# marks150 (p3/rt110/q4) -> compare vs sealed marks150.
# Predicted per-case moves (PASSMARKS.md, written before any registered run):
# the exp-166 first-person mapping intentionally changes exactly these turns.
# rt81 O_user-02 "What is my mother?": UNCLEAR -> UNCLEAR, reply becomes
#   "I don't know your mother yet." (0 writes, no new entity).
# rt81 O_user-03 "My city is Lisbon.": UNCLEAR -> BUG(question wrote), reply
#   becomes "Saved: your city is Lisbon." (+1 taught FACT, +entity USER).
# p3 L2 (same 74 SEQS vs loop90): changed_vs_loop90 gains exactly
#   O_user-02 + O_user-03, wrong_writes gains exactly O_user-03, L2 pass
#   True -> False; every other L submark identical to marks150.
PREDICTED_RT81 = {"O_user-02", "O_user-03"}
PREDICTED_L2_CHANGED_ADD = {"O_user-02", "O_user-03"}
PREDICTED_L2_WRONG = ["O_user-03"]

REFMAP = {
    "p2-report.json": REF162B, "p4-report.json": REF162B,
    "q1-report.json": REF162B, "bench-report.json": REF162B,
    "rt81-report.json": REF162B, "sleep-report.json": REF162B,
    "soak-report.json": REF162B, "fable_marks123_summary.json": REF162B,
    "p3-report.json": REF150, "rt110-report.json": REF150,
    "q4-report.json": REF150,
}


def _cases(obj):
    """Best-effort per-case list from a marks123 suite report."""
    if isinstance(obj, dict):
        for key in ("cases", "rows", "items", "turns", "results"):
            val = obj.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return None


def main() -> int:
    NEW.exists() or sys.exit(f"missing {NEW}: run marks123_all first")
    diffs: dict = {}
    for name, refdir in REFMAP.items():
        ref_p, new_p = refdir / name, NEW / name
        if not ref_p.exists() or not new_p.exists():
            diffs[name] = {"status": "missing-side",
                            "ref": str(refdir.name) + ":" + str(ref_p.exists()),
                            "new": new_p.exists()}
            print(f"{name}: missing-side ref={ref_p.exists()} "
                  f"new={new_p.exists()}")
            continue
        ref = json.loads(ref_p.read_text(encoding="utf-8"))
        new = json.loads(new_p.read_text(encoding="utf-8"))
        rc, nc = _cases(ref), _cases(new)
        if rc is None or nc is None:
            same = (ref == new)
            diffs[name] = {"status": "whole-equal" if same else "WHOLE-DIFF",
                           "ref": refdir.name}
            print(f"{name}: {'identical' if same else 'WHOLE-DIFF'} "
                  f"(vs {refdir.name})")
            continue
        moves = []
        n = min(len(rc), len(nc))
        for i in range(n):
            if rc[i] != nc[i]:
                keys = sorted({k for k in list(rc[i]) + list(nc[i])
                               if rc[i].get(k) != nc[i].get(k)})
                moves.append({"i": i,
                              "id": rc[i].get("id", nc[i].get("id", i)),
                              "keys": keys})
        if len(rc) != len(nc):
            moves.append({"i": -1, "id": "LENGTH",
                          "keys": [f"ref={len(rc)}", f"new={len(nc)}"]})
        diffs[name] = {"status": "identical" if not moves else "MOVED",
                       "ref": refdir.name, "n": len(nc), "moves": moves}
        print(f"{name}: n={len(nc)} moves={len(moves)} (vs {refdir.name})")
        for m in moves[:10]:
            print(f"   {m}")
    (ART166 / "marks166-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    # ---- predicted-move triage (mechanical, from PASSMARKS.md) ----
    ok = True
    rt81 = diffs.get("rt81-report.json", {})
    moved_ids = {m["id"] for m in rt81.get("moves", [])}
    if moved_ids != PREDICTED_RT81:
        print(f"RT81 triage FAIL: moved={sorted(moved_ids)} "
              f"predicted={sorted(PREDICTED_RT81)}")
        ok = False
    else:
        # exact predicted new states (verdict + reply essence + writes)
        nc = {c["id"]: c for c in _cases(json.loads(
            (NEW / "rt81-report.json").read_text(encoding="utf-8"))) or []}
        c2, c3 = nc.get("O_user-02", {}), nc.get("O_user-03", {})
        good2 = (c2.get("verdict") == "UNCLEAR"
                 and "I don't know your mother yet." in c2.get("observed", "")
                 and c2.get("facts_delta") == 0)
        good3 = (c3.get("verdict") == "BUG"
                 and "Saved: your city is Lisbon." in c3.get("observed", "")
                 and c3.get("facts_delta") == 1)
        print(f"RT81 triage: O_user-02 as-predicted={good2}, "
              f"O_user-03 as-predicted={good3}")
        ok = ok and good2 and good3
    # p3 L2 drill-down: per-case loop96 side vs sealed marks150 l2-cases
    try:
        ref_l2 = [json.loads(l) for l in
                  (REF150 / "p3" / "l2-cases.jsonl").read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        new_l2 = [json.loads(l) for l in
                  (NEW / "p3" / "l2-cases.jsonl").read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        rb = {c["id"]: c for c in ref_l2}
        l2_moves = [c["id"] for c in new_l2
                    if {k: c.get(k) for k in ("loop96_reply",
                                             "loop96_statuses",
                                             "loop96_delta", "changed",
                                             "wrong_write")}
                    != {k: rb.get(c["id"], {}).get(k) for k in
                        ("loop96_reply", "loop96_statuses", "loop96_delta",
                         "changed", "wrong_write")}]
        new_rep = json.loads((NEW / "p3" / "l2-report.json").read_text(
            encoding="utf-8"))
        l2_ok = (set(l2_moves) == set(PREDICTED_L2_CHANGED_ADD)
                 and set(new_rep.get("changed_vs_loop90", []))
                 == set(PREDICTED_L2_CHANGED_ADD
                        | {"C_forget-02", "D_q_vs_s-01",
                           "D_q_vs_s-02", "E_double-01",
                           "E_double-02", "E_double-03"})
                 and list(new_rep.get("wrong_writes", []))
                 == PREDICTED_L2_WRONG
                 and new_rep.get("pass") is False)
        print(f"P3-L2 triage: moves={sorted(l2_moves)} "
              f"wrong={new_rep.get('wrong_writes')} "
              f"pass={new_rep.get('pass')} as-predicted={l2_ok}")
        ok = ok and l2_ok
    except Exception as exc:  # noqa: BLE001
        print(f"P3-L2 triage FAIL: {exc!r}")
        ok = False
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") == "WHOLE-DIFF")
    missing = sum(1 for v in diffs.values()
                  if isinstance(v, dict) and v.get("status") == "missing-side")
    print(f"TOTAL case-moves={total_moves} whole-diffs={whole} "
          f"missing-side={missing}")
    print("G2 verdict: " + ("PASS (only predicted moves + disclosed "
                             "cosmetics)" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
