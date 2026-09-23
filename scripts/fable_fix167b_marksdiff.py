#!/usr/bin/env python3
"""Experiment 167b -- G2 marks123 per-case diff vs base loop167 runs (Muse).

Compares artifacts/fable-verb167b-20260922/marks167b (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop167b_agent.py --config
artifacts/fable-verb167b-20260922/loop167b-config.json --out <marks167b>`
run) per-case against the BASE agent's marks167
(artifacts/fable-verb167-20260922/marks167, read-only; 167 completed
every suite, so no fallback folder is needed).

Predicted moves (in writing, before the run): NONE on any suite.
The 167b screen only narrows 167's claims, and 167's G2 showed moves vs
loop162b ONLY on rt110 rows P1+P3 ("Mira lives in Oslo[. ...]" with a
clean "Oslo" object) -- every other suite input is unclaimed by 167, so
167b cannot move it either; P1/P3's clean object passes the screen with
the byte-identical twin, so they stay exactly as 167 left them
("Saved: Mira's city is Oslo." / "Mira's city is Oslo.").
  sleep-report.json reason text names the new agent file (loop167b)
  instead of loop167; verdict (SKIP/pass) identical.
Volatile numerics: any key named exactly "seconds" is ignored (timings),
and "statuses" (mailbox log metadata -- proven harness-racy under load:
two identical loop167 rt110 runs differ in statuses on different rows
with replies, verdicts and fact_writes equal). Verdicts, replies,
fact_writes stay strict. Soak/rt110 flakes under heavy load are the
known mailbox race: re-run that suite once in the open and report both.
Any other move fails G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167b_agent.py \\
    --config artifacts/fable-verb167b-20260922/loop167b-config.json \\
    --out artifacts/fable-verb167b-20260922/marks167b --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167b_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
REF = ROOT / "artifacts" / "fable-verb167-20260922" / "marks167"
NEW = ROOT / "artifacts" / "fable-verb167b-20260922" / "marks167b"
ART167B = ROOT / "artifacts" / "fable-verb167b-20260922"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "q1-report.json", "bench-report.json", "rt81-report.json",
           "sleep-report.json", "soak-report.json", "rt110-report.json",
           "q4-report.json", "fable_marks123_summary.json"]


def _norm(obj):
    """Drop volatile keys, recursively: 'seconds' (timings) and 'statuses'
    (mailbox log metadata -- proven harness-racy under load on loop167:
    replies, verdicts and fact_writes stay strict)."""
    if isinstance(obj, dict):
        return {k: _norm(v) for k, v in obj.items()
                if k not in ("seconds", "statuses")}
    if isinstance(obj, list):
        return [_norm(v) for v in obj]
    return obj


def _cases(obj):
    if isinstance(obj, dict):
        for key in ("cases", "rows", "items", "turns", "results"):
            val = obj.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return None


def check_rt110(ref, new) -> tuple[bool, str]:
    rc = {r["id"]: r for r in ref.get("rows", [])}
    nc = {r["id"]: r for r in new.get("rows", [])}
    if set(rc) != set(nc):
        return False, "row id set differs"
    bad = []
    for rid, nr in nc.items():
        rr = rc[rid]
        if _norm(nr) == _norm(rr):
            continue
        bad.append({"id": rid, "unexpected": True})
    if bad:
        return False, json.dumps(bad)[:800]
    log = nc["P1"].get("log", [])
    ok0 = len(log) > 0 and "Saved: Mira's city is Oslo." in str(
        log[0].get("reply", ""))
    ok2 = len(log) > 2 and "Mira's city is Oslo." in str(
        log[2].get("reply", ""))
    if not (ok0 and ok2):
        return False, "P1 replies drifted from the sealed 167 text"
    return True, (f"all {len(nc)} rows identical to loop167 "
                  f"(P1 still saves/answers Oslo as sealed)")


def check_sleep(ref, new) -> tuple[bool, str]:
    if _norm({k: v for k, v in new.items() if k != "reason"}) != _norm(
            {k: v for k, v in ref.items() if k != "reason"}):
        return False, "non-reason fields differ"
    if "loop167b" not in str(new.get("reason", "")):
        return False, "reason does not name the new agent file"
    return True, "SKIP identical; reason names loop167b as predicted"


def check_summary(ref, new) -> tuple[bool, str]:
    """Suite table: identical numbers on every suite (prediction: no moves
    vs loop167 at all); agent/config paths name the new files; sleep
    number names loop167b; seconds/total_seconds ignored."""
    rt, nt = {r["suite"]: r for r in ref.get("table", [])}, \
        {r["suite"]: r for r in new.get("table", [])}
    if set(rt) != set(nt):
        return False, "suite set differs"
    notes = []
    for s, nr in nt.items():
        rr = rt[s]
        if s == "sleep":
            if not (nr["status"] == rr["status"] == "SKIP"
                    and "loop167b" in nr["number"]):
                return False, "sleep summary not as predicted"
            notes.append("sleep names loop167b")
            continue
        for k in ("bar", "number", "status"):
            if k in ("bar", "status") and nr.get(k) != rr.get(k):
                return False, f"{s}.{k} differs: {rr.get(k)!r:.100} vs {nr.get(k)!r:.100}"
            if k == "number":
                nn, rn = str(nr.get(k)), str(rr.get(k))
                if nn != rn and not (
                        "loop167" in rn and nn.replace("loop167b", "loop167") == rn):
                    return False, f"{s}.number differs: {rn!r:.100} vs {nn!r:.100}"
    return True, "; ".join(notes) + "; all suite numbers identical to loop167"


def main() -> int:
    NEW.exists() or sys.exit(f"missing {NEW}: run marks123_all first")
    diffs: dict = {}
    ok_all = True
    for name in REPORTS:
        ref_p, new_p = REF / name, NEW / name
        if not ref_p.exists() or not new_p.exists():
            diffs[name] = {"status": "missing-side"}
            print(f"{name}: missing-side")
            ok_all = False
            continue
        ref = json.loads(ref_p.read_text(encoding="utf-8"))
        new = json.loads(new_p.read_text(encoding="utf-8"))
        if name == "rt110-report.json":
            ok, msg = check_rt110(ref, new)
            diffs[name] = {"status": "predicted" if ok else "MOVED",
                           "detail": msg}
            print(f"{name}: {diffs[name]['status']} -- {msg}")
            ok_all = ok_all and ok
            continue
        if name == "sleep-report.json":
            ok, msg = check_sleep(ref, new)
            diffs[name] = {"status": "predicted" if ok else "MOVED",
                           "detail": msg}
            print(f"{name}: {diffs[name]['status']} -- {msg}")
            ok_all = ok_all and ok
            continue
        if name == "fable_marks123_summary.json":
            ok, msg = check_summary(ref, new)
            diffs[name] = {"status": "predicted" if ok else "MOVED",
                           "detail": msg}
            print(f"{name}: {diffs[name]['status']} -- {msg}")
            ok_all = ok_all and ok
            continue
        rc, nc = _cases(ref), _cases(new)
        if rc is None or nc is None:
            same = (_norm(ref) == _norm(new))
            diffs[name] = {"status": "identical" if same else "WHOLE-DIFF"}
            print(f"{name}: {diffs[name]['status']}")
            ok_all = ok_all and same
            continue
        moves = []
        n = min(len(rc), len(nc))
        for i in range(n):
            if _norm(rc[i]) != _norm(nc[i]):
                keys = sorted({k for k in list(rc[i]) + list(nc[i])
                               if _norm(rc[i].get(k)) != _norm(nc[i].get(k))})
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
        ok_all = ok_all and not moves
    (ART167B / "marks167b-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    print(f"G2 {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
