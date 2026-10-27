#!/usr/bin/env python3
"""Experiment 163 -- G2 marks123 per-case diff vs sealed loop150 run (Muse).

Compares artifacts/fable-lowercase163-20260922/marks163 (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop163_agent.py --config
artifacts/fable-lowercase163-20260922/loop163-config.json --out <marks163>
--workers 4` run) per-case against the sealed loop150 run
(artifacts/fable-fix150-20260922/marks150, read-only). ZERO per-case moves
predicted (pre-seal pure-function scan over every suite input string: no
teach subject, no person-relation teach value, and no question owner span
is all-lowercase; see PASSMARKS.md). The sleep-report reason names the new
agent file (verdict identical) -- predicted. Any other move fails G2
honestly. Soak/rt110 mailbox flakes under load: one open re-run, both
reported (see RESULTS.md).

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop163_agent.py \\
    --config artifacts/fable-lowercase163-20260922/loop163-config.json \\
    --out artifacts/fable-lowercase163-20260922/marks163 --workers 4
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix163_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART163 = ROOT / "artifacts" / "fable-lowercase163-20260922"
REF = ROOT / "artifacts" / "fable-fix150-20260922" / "marks150"
NEW = ART163 / "marks163"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "rt110-report.json", "q1-report.json", "bench-report.json",
           "rt81-report.json", "sleep-report.json", "soak-report.json",
           "q4-report.json", "fable_marks123_summary.json"]


VOLATILE_KEYS = frozenset({"seconds"})


def _scrub(obj):
    """Drop volatile timing keys recursively (content never dropped)."""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()
                if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


def _summary_norm(rep: dict) -> dict:
    """Map the new agent/config paths back to the sealed ones (predicted)."""
    rep = dict(rep)
    if rep.get("agent") == "scripts/fable_loop163_agent.py":
        rep["agent"] = "scripts/fable_loop150_agent.py"
    if rep.get("config") == \
            "artifacts/fable-lowercase163-20260922/loop163-config.json":
        rep["config"] = "artifacts/fable-fix150-20260922/loop150-config.json"
    return rep


def _cases(obj):
    """Best-effort per-case list from a marks123 suite report."""
    if isinstance(obj, dict):
        for key in ("cases", "rows", "items", "turns", "results"):
            val = obj.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return None


def _sleep_ok(ref: dict, new: dict) -> bool:
    """Sleep verdict identical; only the agent filename in reason may differ."""
    if ref.get("pass") != new.get("pass"):
        return False
    if ref.get("skipped") != new.get("skipped"):
        return False
    r0 = str(ref.get("reason", "")).replace("fable_loop150_agent.py", "X")
    r1 = str(new.get("reason", "")).replace("fable_loop163_agent.py", "X")
    return r0 == r1


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
        if name == "sleep-report.json":
            ok = _sleep_ok(ref, new)
            diffs[name] = {"status": "identical-sleep-agent-rename"
                           if ok else "SLEEP-DIFF",
                           "ref_reason": ref.get("reason"),
                           "new_reason": new.get("reason")}
            print(f"{name}: {'sleep-ok (agent rename only)' if ok else 'SLEEP-DIFF'}")
            continue
        if name == "fable_marks123_summary.json":
            new = _summary_norm(new)
        rc, nc = _cases(_scrub(ref)), _cases(_scrub(new))
        if rc is None or nc is None:
            same = (_scrub(ref) == _scrub(new))
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
    (ART163 / "marks163-diff.json").write_text(json.dumps(diffs, indent=1),
                                               encoding="utf-8")
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") in (
                    "WHOLE-DIFF", "MOVED", "SLEEP-DIFF", "missing-side"))
    print(f"TOTAL case-moves={total_moves} whole-diffs={whole}")
    return 0 if (total_moves == 0 and whole == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
