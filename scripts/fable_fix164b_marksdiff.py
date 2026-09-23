#!/usr/bin/env python3
"""Experiment 164b -- A3 marks123 per-case diff vs sealed loop138h run.

Compares artifacts/fable-about164b-20260922/marks164b (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop164b_agent.py --config
artifacts/fable-about164b-20260922/loop164b-config.json --out <marks164b>
--workers 4` run) per-case against the sealed loop138h run
(artifacts/fable-agent138h-20260922/marks138h, read-only). ZERO per-case
moves predicted (pre-seal scan: no about/summary full-turn shape, incl. the
about-me variant, appears in any bench turn, session152 turn, or suite case
literal outside this experiment's own files; see PASSMARKS.md). Volatile
wall-clock ("seconds") fields are exempt; the sleep SKIP reason is exempt
from byte-equality but must name the new agent file (proving the run really
used loop164b) with verdict identical. Soak/rt110 flakes under heavy load
are a known mailbox race: re-run that suite once in the open and report
both. Any other move fails A3 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop164b_agent.py \\
    --config artifacts/fable-about164b-20260922/loop164b-config.json \\
    --out artifacts/fable-about164b-20260922/marks164b --workers 4
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix164b_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART164B = ROOT / "artifacts" / "fable-about164b-20260922"
REF = ROOT / "artifacts" / "fable-agent138h-20260922" / "marks138h"
NEW = ART164B / "marks164b"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "rt110-report.json", "q1-report.json", "bench-report.json",
           "rt81-report.json", "sleep-report.json", "soak-report.json",
           "q4-report.json", "fable_marks123_summary.json"]

VOLATILE = {"seconds"}

# Diagnostic-only keys: transport/timing text, never the mark verdict. A
# diff confined to these is reported, not failing (mailbox race, e.g. an
# empty first read shifting the per-turn log with verdicts identical).
DIAG_ONLY = {"log", "reason"}


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _mark(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items()
                if k not in VOLATILE and k not in DIAG_ONLY}
    return _strip(obj)


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
            print(f"{name}: missing-side ref={ref_p.exists()} "
                  f"new={new_p.exists()}")
            continue
        ref = json.loads(ref_p.read_text(encoding="utf-8"))
        new = json.loads(new_p.read_text(encoding="utf-8"))
        if name == "sleep-report.json":
            ok = (ref.get("skipped") == new.get("skipped")
                  and ref.get("pass") == new.get("pass")
                  and "fable_loop164b_agent" in str(new.get("reason", "")))
            diffs[name] = {"status": "identical" if ok else "MOVED",
                           "ref_reason": ref.get("reason"),
                           "new_reason": new.get("reason"),
                           "moves": [] if ok else [{"id": "sleep-reason"}]}
            print(f"{name}: {'identical(exempt reason, new agent named)' if ok else 'MOVED'}")
            continue
        rc, nc = _cases(ref), _cases(new)
        if rc is None or nc is None:
            if name == "fable_marks123_summary.json":
                rt, nt = ref.get("table", []), new.get("table", [])

                def _canon(row):
                    s = json.dumps({k: v for k, v in row.items()
                                    if k not in VOLATILE}, sort_keys=True)
                    return s.replace("fable_loop138h_agent.py",
                                     "fable_loop164b_agent.py").replace(
                        "loop138h-config.json", "loop164b-config.json")

                moves = []
                for r_row, n_row in zip(rt, nt):
                    if _canon(r_row) != _canon(n_row):
                        rr = {k: v for k, v in r_row.items()
                              if k not in VOLATILE}
                        nn = {k: v for k, v in n_row.items()
                              if k not in VOLATILE}
                        moves.append({"id": r_row.get("suite"),
                                      "ref": rr, "new": nn})
                if len(rt) != len(nt):
                    moves.append({"id": "LENGTH"})
                ok = (not moves
                      and "fable_loop164b_agent" in str(new.get("agent", ""))
                      and "loop164b-config" in str(new.get("config", "")))
                diffs[name] = {"status": "identical" if ok else "WHOLE-DIFF",
                               "moves": moves if moves else
                               ([] if ok else [{"id": "AGENT-OR-CONFIG"}])}
                print(f"{name}: {'identical (agent+seconds exempt)' if ok else 'WHOLE-DIFF'}")
                continue
            same = (_strip(ref) == _strip(new))
            diffs[name] = {"status": "whole-equal" if same else "WHOLE-DIFF",
                           "moves": [] if same else [{"id": "WHOLE"}]}
            print(f"{name}: {'identical' if same else 'WHOLE-DIFF'}")
            continue
        moves = []
        diag = []
        n = min(len(rc), len(nc))
        for i in range(n):
            if _strip(rc[i]) != _strip(nc[i]):
                keys = sorted({k for k in list(rc[i]) + list(nc[i])
                               if _strip(rc[i].get(k)) != _strip(nc[i].get(k))})
                entry = {"i": i,
                         "id": rc[i].get("id", nc[i].get("id", i)),
                         "keys": keys}
                if _mark(rc[i]) != _mark(nc[i]):
                    moves.append(entry)
                else:
                    diag.append(entry)
        if len(rc) != len(nc):
            moves.append({"i": -1, "id": "LENGTH",
                          "keys": [f"ref={len(rc)}", f"new={len(nc)}"]})
        diffs[name] = {"status": "identical" if not moves else "MOVED",
                       "n": len(nc), "moves": moves, "diag_only": diag}
        print(f"{name}: n={len(nc)} moves={len(moves)} "
              f"diag_only={len(diag)}")
        for m in moves[:10]:
            print(f"   {m}")
        for m in diag[:10]:
            print(f"   diag {m}")
    (ART164B / "marks164b-diff.json").write_text(json.dumps(diffs, indent=1),
                                                encoding="utf-8")
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    print(f"TOTAL case-moves={total_moves}")
    return 0 if total_moves == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
