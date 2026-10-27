#!/usr/bin/env python3
"""Experiment 173b -- G2 marks123 per-case diff vs loop173's marks.

Compares artifacts/fable-username173b-20260922/marks173b (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop173b_agent.py --config
artifacts/fable-username173b-20260922/loop173b-config.json --out <marks173b>
--workers 2` run) per-case against loop173's marks173
(artifacts/fable-username173-20260922/marks173, read-only) for every suite.

ZERO per-case moves predicted (PASSMARKS.md, written before any registered
run): pre-seal scan finds no 173b name-statement/question fire in any suite
input. Predicted cosmetics only: suite-summary files and the sleep SKIP
reason naming the new agent file; volatile timings may differ. rt110
log-only flakes under load: re-run once in the open, report both.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py \\
    --agent scripts/fable_loop173b_agent.py \\
    --config artifacts/fable-username173b-20260922/loop173b-config.json \\
    --out artifacts/fable-username173b-20260922/marks173b --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix173b_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
REF173 = ROOT / "artifacts" / "fable-username173-20260922" / "marks173"
NEW = ROOT / "artifacts" / "fable-username173b-20260922" / "marks173b"
ART173B = ROOT / "artifacts" / "fable-username173b-20260922"

REPORTS = ["p2-report.json", "p4-report.json", "q1-report.json",
           "bench-report.json", "rt81-report.json", "sleep-report.json",
           "soak-report.json", "fable_marks123_summary.json",
           "p3-report.json", "rt110-report.json", "q4-report.json"]


def _cases(obj):
    if isinstance(obj, dict):
        for key in ("cases", "rows", "items", "turns", "results"):
            val = obj.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return None


def _scrub(obj):
    repl = {"scripts/fable_loop173b_agent.py": "AGENT",
            "scripts/fable_loop173_agent.py": "AGENT",
            "artifacts/fable-username173b-20260922": "ART",
            "artifacts/fable-username173-20260922": "ART",
            "loop173b-config.json": "CFG", "loop173-config.json": "CFG",
            "loop173b": "LOOP", "loop173": "LOOP"}
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.lower() in ("seconds", "wall_seconds", "elapsed",
                             "duration", "timings", "elapsed_seconds",
                             "wall_time", "runtime_seconds",
                             "total_seconds"):
                continue
            out[k] = _scrub(v)
        return out
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        for old, new in repl.items():
            obj = obj.replace(old, new)
        return obj
    return obj


def main() -> int:
    NEW.exists() or sys.exit(f"missing {NEW}: run marks123_all first")
    diffs: dict = {}
    for name in REPORTS:
        ref_p, new_p = REF173 / name, NEW / name
        if not ref_p.exists() or not new_p.exists():
            diffs[name] = {"status": "missing-side",
                            "ref": ref_p.exists(), "new": new_p.exists()}
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
                rk, nk = (set(ref) if isinstance(ref, dict) else None,
                          set(new) if isinstance(new, dict) else None)
                if rk is not None and nk is not None:
                    for k in sorted(rk | nk):
                        if ref.get(k) != new.get(k):
                            print(f"   key={k} ref={str(ref.get(k))[:120]} "
                                  f"new={str(new.get(k))[:120]}")
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
    (ART173B / "marks173b-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    case_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                     if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") == "WHOLE-DIFF")
    missing = sum(1 for v in diffs.values()
                  if isinstance(v, dict)
                  and v.get("status") == "missing-side")
    try:
        ref_l2 = [json.loads(l) for l in
                  (REF173 / "p3" / "l2-cases.jsonl").read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        new_l2 = [json.loads(l) for l in
                  (NEW / "p3" / "l2-cases.jsonl").read_text(
                      encoding="utf-8").splitlines() if l.strip()]
        rb = {c.get("id", i): _scrub(c) for i, c in enumerate(ref_l2)}
        l2_moves = [c.get("id", i) for i, c in enumerate(new_l2)
                    if _scrub(c) != rb.get(c.get("id", i))]
        print(f"P3-L2: n={len(new_l2)} moves={l2_moves[:10]}")
        diffs["p3-l2-cases.jsonl"] = {"status": "identical"
                                      if not l2_moves else "MOVED",
                                      "n": len(new_l2),
                                      "moves": l2_moves[:10]}
        ok_l2 = not l2_moves
    except Exception as exc:  # noqa: BLE001
        print(f"P3-L2 triage FAIL: {exc!r}")
        diffs["p3-l2-cases.jsonl"] = {"status": "missing-side"}
        ok_l2 = False
    ok = (case_moves == 0 and whole == 0 and missing == 0 and ok_l2)
    print(f"TOTAL case-moves={case_moves} whole-diffs={whole} "
          f"missing-side={missing}")
    print("G2 verdict: " + ("PASS (only predicted cosmetics)" if ok
                            else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
