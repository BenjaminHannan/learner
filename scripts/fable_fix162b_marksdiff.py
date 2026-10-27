#!/usr/bin/env python3
"""Experiment 162b -- G2 marks123 per-case diff vs base runs (Muse).

Compares artifacts/fable-plural162b-20260922/marks162b (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop162b_agent.py --config
artifacts/fable-plural162b-20260922/loop162b-config.json --out <marks162b>`
run) per-case against:
  (a) the BASE agent's marks162
      (artifacts/fable-thename162-20260922/marks162, read-only) for every
      suite it completed (p2/p4/q1/bench/rt81/sleep/soak), and
  (b) the sealed loop150 marks150
      (artifacts/fable-fix150-20260922/marks150, read-only) for the suites
      162 could not run (p3/rt110/q4) -- same fallback 162's brief allows.

ZERO per-case moves predicted: the 162b plural teach frame fires only on
The-initial ``s'`` possessives with table relations (0 such inputs in any
suite per the pre-seal scan), the ask frame is 162's unchanged code gated on
resolving to a taught entity (no plural entity is teachable on the base
suites), and the daemon fix is harness-only. Soak/rt110 flakes under heavy
load are a known mailbox race: re-run that suite once in the open and report
both. Any other move fails G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop162b_agent.py \\
    --config artifacts/fable-plural162b-20260922/loop162b-config.json \\
    --out artifacts/fable-plural162b-20260922/marks162b --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix162b_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART162 = ROOT / "artifacts" / "fable-thename162-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"
ART162B = ROOT / "artifacts" / "fable-plural162b-20260922"
REF162 = ART162 / "marks162"
REF150 = ART150 / "marks150"
NEW = ART162B / "marks162b"

# Suites 162 completed -> compare vs marks162; suites 162 could not run
# (p3/rt110/q4 missing there) -> compare vs sealed marks150.
REFMAP = {
    "p2-report.json": REF162, "p4-report.json": REF162,
    "q1-report.json": REF162, "bench-report.json": REF162,
    "rt81-report.json": REF162, "sleep-report.json": REF162,
    "soak-report.json": REF162, "fable_marks123_summary.json": REF162,
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
    (ART162B / "marks162b-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") == "WHOLE-DIFF")
    missing = sum(1 for v in diffs.values()
                  if isinstance(v, dict) and v.get("status") == "missing-side")
    print(f"TOTAL case-moves={total_moves} whole-diffs={whole} "
          f"missing-side={missing}")
    return 0 if (total_moves == 0 and whole == 0 and missing == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
