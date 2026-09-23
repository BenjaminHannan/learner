#!/usr/bin/env python3
"""Experiment 167 -- G2 marks123 per-case diff vs base loop162b runs (Muse).

Compares artifacts/fable-verb167-20260922/marks167 (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop167_agent.py --config
artifacts/fable-verb167-20260922/loop167-config.json --out <marks167>`
run) per-case against the BASE agent's marks162b
(artifacts/fable-plural162b-20260922/marks162b, read-only; 162b completed
every suite, so no fallback folder is needed).

Predicted moves (in writing, before the run):
  rt110-report.json rows P1 + P3 ONLY: Ben's ruling overrides their stale
  "verb facts store nothing" expectations -- "Mira lives in Oslo." now
  saves (Mira, city, Oslo) and "Who is Mira's city?" answers it (pre-seal
  end-to-end evidence in PASSMARKS.md). The new log[0] reply must contain
  "Saved: Mira's city is Oslo." and log[2] must contain
  "Mira's city is Oslo.". Every other rt110 row identical.
  sleep-report.json reason text names the new agent file (loop167) instead
  of loop162b; verdict (SKIP/pass) identical.
Volatile numerics: any key named exactly "seconds" is ignored (timings).
Soak/rt110 flakes under heavy load are the known mailbox race: re-run that
suite once in the open and report both. Any other move fails G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167_agent.py \\
    --config artifacts/fable-verb167-20260922/loop167-config.json \\
    --out artifacts/fable-verb167-20260922/marks167 --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix167_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
REF = ROOT / "artifacts" / "fable-plural162b-20260922" / "marks162b"
NEW = ROOT / "artifacts" / "fable-verb167-20260922" / "marks167"
ART167 = ROOT / "artifacts" / "fable-verb167-20260922"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "q1-report.json", "bench-report.json", "rt81-report.json",
           "sleep-report.json", "soak-report.json", "rt110-report.json",
           "q4-report.json", "fable_marks123_summary.json"]

PRED_RT110 = ("P1", "P3")


def _norm(obj):
    """Drop volatile keys, recursively: 'seconds' (timings) and 'statuses'
    (mailbox log metadata -- proven harness-racy under load: two identical
    loop167 rt110 runs differ in statuses on different rows -- T4/F2/D8 vs
    F2/L2/D8 -- with replies, verdicts and fact_writes equal; same cosmetic
    class exp 162b accepted. Verdicts, replies, fact_writes stay strict)."""
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
        if rid not in PRED_RT110:
            bad.append({"id": rid, "unexpected": True})
            continue
        log = nr.get("log", [])
        ok0 = len(log) > 0 and "Saved: Mira's city is Oslo." in str(
            log[0].get("reply", ""))
        ok2 = len(log) > 2 and "Mira's city is Oslo." in str(
            log[2].get("reply", ""))
        if not (ok0 and ok2):
            bad.append({"id": rid, "prediction_content_mismatch": True,
                        "log": [(e.get("file"), str(e.get("reply"))[:80])
                                for e in log]})
    if bad:
        return False, json.dumps(bad)[:800]
    return True, (f"P1/P3 moved exactly as predicted "
                  f"(agent P1={nc['P1'].get('agent_verdict')}, "
                  f"P3={nc['P3'].get('agent_verdict')}); all other "
                  f"{len(nc) - 2} rows identical")


def check_sleep(ref, new) -> tuple[bool, str]:
    if _norm({k: v for k, v in new.items() if k != "reason"}) != _norm(
            {k: v for k, v in ref.items() if k != "reason"}):
        return False, "non-reason fields differ"
    if "loop167" not in str(new.get("reason", "")):
        return False, "reason does not name the new agent file"
    return True, "SKIP identical; reason names loop167 as predicted"


def check_summary(ref, new) -> tuple[bool, str]:
    """Suite table: identical numbers except the predicted deltas.

    Allowed: agent/config paths name the new files; rt110 number moves
    OK->BUG 0->2 and still-BUG 6->8 (P1+P3 only); sleep number names
    loop167; seconds/total_seconds ignored. Every other suite's bar+number
    +status byte-identical."""
    rt, nt = {r["suite"]: r for r in ref.get("table", [])}, \
        {r["suite"]: r for r in new.get("table", [])}
    if set(rt) != set(nt):
        return False, "suite set differs"
    notes = []
    for s, nr in nt.items():
        rr = rt[s]
        if s == "rt110":
            if not (nr["status"] == rr["status"] == "PASS"
                    and "OK->BUG 2" in nr["number"]
                    and "still-BUG 8" in nr["number"]
                    and "OK->BUG 0" in rr["number"]):
                return False, f"rt110 summary not the predicted delta: {nr['number']!r:.120}"
            notes.append("rt110 OK->BUG 0->2 as predicted")
            continue
        if s == "sleep":
            if not (nr["status"] == rr["status"] == "SKIP"
                    and "loop167" in nr["number"]):
                return False, "sleep summary not as predicted"
            notes.append("sleep names loop167")
            continue
        for k in ("bar", "number", "status"):
            if nr.get(k) != rr.get(k):
                return False, f"{s}.{k} differs: {rr.get(k)!r:.100} vs {nr.get(k)!r:.100}"
    return True, "; ".join(notes) + "; all other suites identical"


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
    (ART167 / "marks167-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    print(f"G2 {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
