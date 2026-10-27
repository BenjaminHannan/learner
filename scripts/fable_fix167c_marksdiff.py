#!/usr/bin/env python3
"""Experiment 167c -- G2 marks123 per-case diff vs base loop167b runs (Muse).

Compares artifacts/fable-label167c-20260922/marks167c (produced by the
registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop167c_agent.py --config
artifacts/fable-label167c-20260922/loop167c-config.json --out <marks167c>`
run) per-case against the BASE agent's marks167b
(artifacts/fable-verb167b-20260922/marks167b, read-only).

Predicted moves (in writing, before the run): on every suite, per-case
payloads are identical EXCEPT
  (a) reply strings that are Saved fact confirmations with an underscore
      relation key move by exactly the shared render
      (fable_fix167c_label.saved_render_move) -- pre-seal scan of the
      frozen marks167b reports finds these ONLY in rt110 rows R4 (1 log
      reply), F6 (4 log replies), N5 (2 log replies); every other suite's
      frozen replies contain no underscore relation key;
  (b) agent/config path + reason strings naming the new files
      (loop167b -> loop167c, marks167b -> marks167c);
  (c) volatile numerics: any key named exactly "seconds" is ignored
      (timings), and "statuses" (mailbox log metadata -- proven
      harness-racy under load on loop167b: two identical loop167b runs can
      differ in statuses with replies, verdicts and fact_writes equal).
Sleep verdict (SKIP/pass) identical; summary numbers identical on every
suite. Soak/rt110 flakes under heavy load are the known mailbox race:
re-run that suite once in the open and report both. Any other move fails
G2 honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167c_agent.py --config artifacts/fable-label167c-20260922/loop167c-config.json --out artifacts/fable-label167c-20260922/marks167c --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix167c_label as F167C  # noqa: E402 (shared move rule)

ROOT = SCRIPTS.parent
REF = ROOT / "artifacts" / "fable-verb167b-20260922" / "marks167b"
NEW = ROOT / "artifacts" / "fable-label167c-20260922" / "marks167c"
ART167C = ROOT / "artifacts" / "fable-label167c-20260922"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "q1-report.json", "bench-report.json", "rt81-report.json",
           "sleep-report.json", "soak-report.json", "rt110-report.json",
           "q4-report.json", "fable_marks123_summary.json"]

RENAME_TOKENS = ("loop167b", "marks167b", "verb167b")


def _derename(s: str) -> str:
    return (s.replace("loop167c", "loop167b")
             .replace("marks167c", "marks167b")
             .replace("label167c", "verb167b"))


def _norm(obj):
    """Drop volatile keys, recursively: 'seconds' (timings) and 'statuses'
    (mailbox log metadata -- proven harness-racy under load on loop167b:
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


def _strings_equal_or_render(ref, new, moves: list, where: str) -> bool:
    """Compare two JSON subtrees: equal after derename, except reply-like
    strings may differ by exactly the Saved render. Records every render
    move into `moves`."""
    if isinstance(ref, dict) and isinstance(new, dict):
        if set(ref) != set(new):
            return False
        return all(_strings_equal_or_render(ref[k], new[k], moves,
                                            f"{where}/{k}")
                   for k in ref)
    if isinstance(ref, list) and isinstance(new, list):
        if len(ref) != len(new):
            return False
        return all(_strings_equal_or_render(a, b, moves, f"{where}[{i}]")
                   for i, (a, b) in enumerate(zip(ref, new)))
    if isinstance(ref, str) and isinstance(new, str):
        if ref == new or _derename(new) == ref:
            return True
        if F167C.saved_render_move(ref, new) and ref != new:
            moves.append(where)
            return True
        if F167C.saved_render_move(_derename(new), ref):
            return True
        return False
    return ref == new


def check_report(ref, new) -> tuple[bool, str, list]:
    moves: list = []
    ok = _strings_equal_or_render(_norm(ref), _norm(new), moves, "$")
    return ok, ("identical" if not moves else
                f"{len(moves)} render-moves"), moves


def check_rt110(ref, new) -> tuple[bool, str]:
    moves: list = []
    ok = _strings_equal_or_render(_norm(ref), _norm(new), moves, "$")
    if not ok:
        return False, "non-render difference present"
    render_only = sorted({m.split("/log[")[0] for m in moves})
    return True, (f"{len(moves)} Saved-render reply moves in rows "
                  f"{render_only}" if moves else "identical")


def check_sleep(ref, new) -> tuple[bool, str]:
    if _norm({k: v for k, v in new.items() if k != "reason"}) != _norm(
            {k: v for k, v in ref.items() if k != "reason"}):
        return False, "non-reason fields differ"
    if "loop167c" not in str(new.get("reason", "")):
        return False, "reason does not name the new agent file"
    return True, "SKIP identical; reason names loop167c as predicted"


def check_summary(ref, new) -> tuple[bool, str]:
    """Suite table: identical numbers on every suite; agent/config paths
    name the new files; sleep number names loop167c; seconds ignored."""
    rt, nt = {r["suite"]: r for r in ref.get("table", [])}, \
        {r["suite"]: r for r in new.get("table", [])}
    if set(rt) != set(nt):
        return False, "suite set differs"
    notes = []
    for s, nr in nt.items():
        rr = rt[s]
        if s == "sleep":
            if not (nr["status"] == rr["status"] == "SKIP"
                    and "loop167c" in nr["number"]):
                return False, "sleep summary not as predicted"
            notes.append("sleep names loop167c")
            continue
        for k in ("bar", "status"):
            if nr.get(k) != rr.get(k):
                return False, f"{s}.{k} differs"
        nn, rn = str(nr.get("number")), str(rr.get("number"))
        if nn != rn and _derename(nn) != rn:
            moves: list = []
            if not _strings_equal_or_render(rr.get("number"),
                                            nr.get("number"), moves, s):
                return False, f"{s}.number differs beyond rename/render"
    return True, "; ".join(notes) + "; all suite numbers identical to loop167b"


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
        ok, msg, moves = check_report(ref, new)
        diffs[name] = {"status": "identical" if ok and not moves
                       else ("predicted" if ok else "MOVED"),
                       "detail": msg, "moves": moves[:20]}
        print(f"{name}: {diffs[name]['status']} -- {msg}")
        ok_all = ok_all and ok
    (ART167C / "marks167c-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    print(f"G2 {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
