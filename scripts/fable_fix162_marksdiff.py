#!/usr/bin/env python3
"""Experiment 162 -- G2 marks123 per-case diff vs sealed loop150 run (Muse).

Compares artifacts/fable-thename162-20260922/marks162 (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop162_agent.py --config
artifacts/fable-thename162-20260922/loop162-config.json --out <marks162>
--workers 4` run) per-case against the sealed loop150 run
(artifacts/fable-fix150-20260922/marks150, read-only). ZERO per-case moves
predicted: the 162 teach frame fires only on The-initial possessives with
table relations (absent from the sealed suite inputs per the pre-seal scan),
the ask frame claims a turn only when a taught The-entity resolves (no
The-entities are teachable on the base suites), and the 135 guard's own
RESULTS show suite-verdict parity (9/10, the one miss a mailbox timing
hiccup, not content). Soak/rt110 flakes under heavy load are a known
mailbox race: re-run that suite once in the open and report both. Any other
move fails G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop162_agent.py \\
    --config artifacts/fable-thename162-20260922/loop162-config.json \\
    --out artifacts/fable-thename162-20260922/marks162 --workers 4
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix162_marksdiff.py
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
REF = ROOT / "artifacts" / "fable-fix150-20260922" / "marks150"
NEW = ART162 / "marks162"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "rt110-report.json", "q1-report.json", "bench-report.json",
           "rt81-report.json", "sleep-report.json", "soak-report.json",
           "q4-report.json", "fable_marks123_summary.json"]


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
    for name in REPORTS:
        ref_p, new_p = REF / name, NEW / name
        if not ref_p.exists() or not new_p.exists():
            diffs[name] = {"status": "missing-side",
                           "ref": ref_p.exists(), "new": new_p.exists()}
            continue
        ref = json.loads(ref_p.read_text(encoding="utf-8"))
        new = json.loads(new_p.read_text(encoding="utf-8"))
        rc, nc = _cases(ref), _cases(new)
        if rc is None or nc is None:
            same = (ref == new)
            diffs[name] = {"status": "whole-equal" if same else "WHOLE-DIFF",
                           "ref_keys": sorted(ref) if isinstance(ref, dict)
                           else None}
            print(f"{name}: {'identical' if same else 'WHOLE-DIFF'}")
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
                       "n": len(nc), "moves": moves}
        print(f"{name}: n={len(nc)} moves={len(moves)}")
        for m in moves[:10]:
            print(f"   {m}")
    (ART162 / "marks162-diff.json").write_text(json.dumps(diffs, indent=1),
                                               encoding="utf-8")
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") == "WHOLE-DIFF")
    print(f"TOTAL case-moves={total_moves} whole-diffs={whole}")
    return 0 if (total_moves == 0 and whole == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
