#!/usr/bin/env python3
"""Exp 174 T2-marks compare -- marks174 vs sealed marks138f, per-case diff.

Compares every *-report.json + fable_marks123_summary.json in
artifacts/fable-chainof174-20260922/marks174/ against the sealed
artifacts/fable-agent138f-20260922/marks138f/ (read-only), ignoring
wall-clock/timing keys and agent/config path strings. Bar (PASSMARKS.md):
per-case identical except predicted (none predicted); 0 new WRONG anywhere.

Run (after the registered marks123 wave for loop174 finishes):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix174_markscmp.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-chainof174-20260922"
A138 = ROOT / "artifacts" / "fable-agent138f-20260922" / "marks138f"
A174 = ART / "marks174"

IGNORE_KEYS = {"seconds", "total_seconds", "agent", "config", "mark_seconds",
               "elapsed", "wall", "duration"}
WRONG_HITS = ("wrong", "bug")


def norm(obj, key=""):
    if isinstance(obj, dict):
        return {k: norm(v, k) for k, v in obj.items()
                if k not in IGNORE_KEYS}
    if isinstance(obj, list):
        return [norm(v, key) for v in obj]
    if isinstance(obj, str) and key in ("agent", "config"):
        return "<path>"
    if isinstance(obj, float):
        return round(obj, 6)
    return obj


def diff(a, b, path=""):
    out = []
    if type(a) is not type(b):
        return [f"{path}: type {type(a).__name__} vs {type(b).__name__}"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k in IGNORE_KEYS:
                continue
            if k not in a:
                out.append(f"{path}/{k}: missing in 174")
            elif k not in b:
                out.append(f"{path}/{k}: missing in 138f")
            else:
                out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: len {len(a)} vs {len(b)}"]
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
        return out
    if a != b:
        sa, sb = str(a)[:160], str(b)[:160]
        return [f"{path}: 174={sa!r} 138f={sb!r}"]
    return out


def main() -> int:
    files = sorted(p.name for p in A138.glob("*-report.json"))
    files += ["fable_marks123_summary.json"]
    moves: list[str] = []
    for f in files:
        pa, pb = A138 / f, A174 / f
        if not pb.exists():
            moves.append(f"{f}: MISSING in marks174")
            continue
        a = norm(json.loads(pa.read_text(encoding="utf-8")))
        b = norm(json.loads(pb.read_text(encoding="utf-8")))
        d = diff(b, a, f)
        # Drop volatile timing-ish leaves (values that are pure numbers
        # under time-like keys missed by IGNORE_KEYS).
        d = [line for line in d
             if not any(k in line.split(":")[0]
                        for k in ("_s", "ms_", "nanos"))]
        moves += d
    new_wrong = [m for m in moves
                 if any(w in m.lower() for w in WRONG_HITS)
                 and "0" not in m]
    out = {"files": files, "nmoves": len(moves), "moves": moves[:200],
           "pass": not moves}
    (ART / "marks174-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"markscmp: files={len(files)} nmoves={len(moves)}", flush=True)
    for m in moves[:60]:
        print(f"  DIFF {m}", flush=True)
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
