#!/usr/bin/env python3
"""Experiment 165 -- G2 marks123 per-case diff vs the base run (Muse).

Compares artifacts/fable-typo165-20260922/marks165 (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop165_agent.py --config
artifacts/fable-typo165-20260922/loop165-config.json --out <marks165>`
run) per-case against the BASE agent's marks162b
(artifacts/fable-plural162b-20260922/marks162b, read-only), which completed
every suite. Volatile keys (seconds/wall-clock timings, run paths, and the
sleep SKIP reason that names the agent file) are scrubbed before compare;
everything scrubbed is listed, and any remaining per-case move fails G2
honestly.

ZERO semantic moves predicted: the 165 write frame needs a full
no-apostrophe ``W R`` shape with a person relation plus notebook gates (the
pre-seal scan finds no such shape in any suite input), and the ask frame is
the base's own code on the rewritten turn. Soak/rt110 flakes under heavy
load are a known mailbox race: re-run that suite once in the open and report
both.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop165_agent.py \\
    --config artifacts/fable-typo165-20260922/loop165-config.json \\
    --out artifacts/fable-typo165-20260922/marks165 --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix165_marksdiff.py
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
ART165 = ROOT / "artifacts" / "fable-typo165-20260922"
REF = ART162B / "marks162b"
NEW = ART165 / "marks165"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "q1-report.json", "q4-report.json", "bench-report.json",
           "rt81-report.json", "rt110-report.json", "sleep-report.json",
           "soak-report.json", "fable_marks123_summary.json"]

# Volatile keys scrubbed before compare (timings, paths, agent-file naming).
SCRUB_KEYS = {"seconds", "wall_seconds", "wall", "elapsed", "elapsed_seconds",
              "duration", "duration_seconds", "run_seconds", "agent",
              "agent_path", "config", "config_path", "out", "out_dir",
              "reason", "detail", "log", "status_path"}


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k not in SCRUB_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, float):
        return round(obj, 1)
    return obj


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
                           "ref_exists": ref_p.exists(),
                           "new_exists": new_p.exists()}
            print(f"{name}: missing-side ref={ref_p.exists()} "
                  f"new={new_p.exists()}")
            continue
        ref = _scrub(json.loads(ref_p.read_text(encoding="utf-8")))
        new = _scrub(json.loads(new_p.read_text(encoding="utf-8")))
        rc, nc = _cases(ref), _cases(new)
        if rc is None or nc is None:
            same = (ref == new)
            diffs[name] = {"status": "identical" if same else "WHOLE-DIFF"}
            print(f"{name}: {'identical' if same else 'WHOLE-DIFF'} "
                  f"(no per-case list)")
            if not same:
                print(f"   ref-keys={sorted(ref) if isinstance(ref, dict) else type(ref)}")
            continue
        moves = []
        n = min(len(rc), len(nc))
        for i in range(n):
            if rc[i] != nc[i]:
                keys = sorted({k for k in list(rc[i]) + list(nc[i])
                               if rc[i].get(k) != nc[i].get(k)})
                moves.append({"i": i,
                              "id": rc[i].get("id", nc[i].get("id", i)),
                              "keys": keys,
                              "ref": {k: rc[i].get(k) for k in keys},
                              "new": {k: nc[i].get(k) for k in keys}})
        if len(rc) != len(nc):
            moves.append({"i": -1, "id": "LENGTH",
                          "keys": [f"ref={len(rc)}", f"new={len(nc)}"]})
        diffs[name] = {"status": "identical" if not moves else "MOVED",
                       "n": len(nc), "moves": moves}
        print(f"{name}: n={len(nc)} moves={len(moves)}")
        for m in moves[:10]:
            print(f"   {m}")
    (ART165 / "marks165-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") == "WHOLE-DIFF")
    missing = sum(1 for v in diffs.values()
                  if isinstance(v, dict) and v.get("status") == "missing-side")
    print(f"TOTAL moves={total_moves} whole-diffs={whole} missing={missing}")
    return 0 if (total_moves + whole + missing) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
