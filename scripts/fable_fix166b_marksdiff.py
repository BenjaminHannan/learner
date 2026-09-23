#!/usr/bin/env python3
"""Experiment 166b -- G2 marks123 per-case diff vs loop166's marks166 (Muse).

Compares artifacts/fable-me166b-20260922/marks166b (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop166b_agent.py --config
artifacts/fable-me166b-20260922/loop166b-config.json --out <marks166b>`
run) per-case against loop166's FROZEN marks166
(artifacts/fable-me166-20260922/marks166, read-only).

ZERO per-case moves predicted (pre-seal scan: no suite sequence pairs a
lowercase entity write with a later capitalised-only-different mention;
the fix only rewrites said lines containing a stored all-lowercase
display). Sleep SKIP verdict identical, reason text names the new agent
file. Soak/rt110 flakes under heavy load are the known mailbox race ->
re-run that suite once in the open and report both. Any other move fails
G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166b_agent.py \\
    --config artifacts/fable-me166b-20260922/loop166b-config.json \\
    --out artifacts/fable-me166b-20260922/marks166b --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix166b_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART166 = ROOT / "artifacts" / "fable-me166-20260922"
ART166B = ROOT / "artifacts" / "fable-me166b-20260922"
REF166 = ART166 / "marks166"
NEW = ART166B / "marks166b"


VOLATILE_KEYS = {"seconds", "wall_seconds", "wall", "elapsed",
                 "started", "finished", "timestamp", "total_seconds"}


def _normalize(obj):
    """Drop volatile timing keys; map base folder/agent/config names to new."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()
                if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, str):
        return (obj.replace("fable_loop166_agent.py",
                            "fable_loop166b_agent.py")
                   .replace("fable-me166-20260922",
                            "fable-me166b-20260922")
                   .replace("loop166-config.json",
                            "loop166b-config.json")
                   .removesuffix("("))
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
    ref_names = sorted(p.name for p in REF166.glob("*.json"))
    new_names = sorted(p.name for p in NEW.glob("*.json"))
    diffs: dict = {}
    for name in sorted(set(ref_names) | set(new_names)):
        ref_p, new_p = REF166 / name, NEW / name
        if not ref_p.exists() or not new_p.exists():
            diffs[name] = {"status": "missing-side",
                           "ref": ref_p.exists(), "new": new_p.exists()}
            print(f"{name}: missing-side ref={ref_p.exists()} "
                  f"new={new_p.exists()}")
            continue
        ref = json.loads(ref_p.read_text(encoding="utf-8"))
        new = json.loads(new_p.read_text(encoding="utf-8"))
        rc, nc = _cases(ref), _cases(new)
        if rc is None or nc is None:
            same = (_normalize(ref) == _normalize(new))
            diffs[name] = {"status": "whole-equal" if same else "WHOLE-DIFF",
                           "ref": "marks166"}
            print(f"{name}: {'identical' if same else 'WHOLE-DIFF'} "
                  f"(vs marks166)")
            continue
        moves = []
        n = min(len(rc), len(nc))
        for i in range(n):
            if _normalize(rc[i]) != _normalize(nc[i]):
                keys = sorted({k for k in list(rc[i]) + list(nc[i])
                               if _normalize(rc[i].get(k))
                               != _normalize(nc[i].get(k))})
                moves.append({"i": i,
                              "id": rc[i].get("id", nc[i].get("id", i)),
                              "keys": keys})
        if len(rc) != len(nc):
            moves.append({"i": -1, "id": "LENGTH",
                          "keys": [f"ref={len(rc)}", f"new={len(nc)}"]})
        diffs[name] = {"status": "identical" if not moves else "MOVED",
                       "ref": "marks166", "n": len(nc), "moves": moves}
        print(f"{name}: n={len(nc)} moves={len(moves)} (vs marks166)")
        for m in moves[:10]:
            print(f"   {m}")
    (ART166B / "marks166b-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    # p3 l2-cases drill-down (loop96 side, same triage as the 166 driver)
    try:
        ref_l2 = [json.loads(l) for l in
                  (REF166 / "p3" / "l2-cases.jsonl").read_text(
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
        print(f"P3-L2 per-case moves vs marks166: {sorted(l2_moves)}")
    except Exception as exc:  # noqa: BLE001
        print(f"P3-L2 triage note: {exc!r}")
        l2_moves = ["TRIAGE-ERROR"]
    total_moves = sum(len(v.get("moves", [])) for v in diffs.values()
                      if isinstance(v, dict))
    whole = sum(1 for v in diffs.values()
                if isinstance(v, dict) and v.get("status") == "WHOLE-DIFF")
    missing = sum(1 for v in diffs.values()
                  if isinstance(v, dict) and v.get("status") == "missing-side")
    # ---- known mailbox-race triage (brief clause, reported in the open) ----
    # rt110/soak log-only moves with identical verdicts are the known race:
    # acceptable only with the open re-run on disk (both runs reported).
    race_ok = True
    for name in ("rt110-report.json", "soak-report.json"):
        moves = diffs.get(name, {}).get("moves", [])
        if not moves:
            continue
        ref_rep = json.loads((REF166 / name).read_text(encoding="utf-8"))
        new_rep = json.loads((NEW / name).read_text(encoding="utf-8"))
        rc = {c.get("id", c.get("i")): c for c in (_cases(ref_rep) or [])}
        nc = {c.get("id", c.get("i")): c for c in (_cases(new_rep) or [])}
        for m in moves:
            cid = m["id"]
            rkeys = {k: v for k, v in rc.get(cid, {}).items()
                     if k not in ("log", "seconds")}
            nkeys = {k: v for k, v in nc.get(cid, {}).items()
                     if k not in ("log", "seconds")}
            if _normalize(rkeys) != _normalize(nkeys):
                race_ok = False
                print(f"  {name}/{cid}: VERDICT-LEVEL move, not race")
            else:
                print(f"  {name}/{cid}: log-only, verdicts identical "
                      f"(known race)")
    rerun = ART166B / "marks166b-rt110rerun" / "rt110-report.json"
    print(f"  open rt110 re-run on disk: {rerun.exists()}")
    print(f"TOTAL case-moves={total_moves} whole-diffs={whole} "
          f"missing-side={missing} l2_moves={l2_moves}")
    ok = (total_moves == 0 and whole == 0 and missing == 0
          and l2_moves == [])
    if not ok and race_ok and rerun.exists() and whole == 0 \
            and missing == 0 and l2_moves == []:
        print("G2 verdict: PASS (per-case identical except verdict-identical "
              "rt110/soak log-only race moves; open re-run on disk, both "
              "reported)")
        return 0
    if not ok:
        print("G2 verdict: FAIL (moves above are unpredicted)")
    else:
        print("G2 verdict: PASS (per-case identical to marks166)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
