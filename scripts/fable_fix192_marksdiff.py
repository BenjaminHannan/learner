#!/usr/bin/env python3
"""Experiment 192 -- marks123 per-case diff vs base loop167e runs.

Compares artifacts/fable-correctreply192-20260922/marks192 (produced by
the registered `scripts/fable_marks123_all.py --agent
scripts/fable_loop192_agent.py --config
artifacts/fable-correctreply192-20260922/loop192-config.json --out
<marks192>` run) per-case against the BASE agent's marks167e
(artifacts/fable-label167e-20260922/marks167e, read-only).

Predicted moves (in writing, before the run -- see PASSMARKS.md): on
every suite, per-case payloads are identical EXCEPT
  (a) reply strings where loop167e confirms a replacement with Saved
      move to the sealed Updated template naming both values
      (fable_fix192_correctreply.correctreply_move) -- pre-seal scan
      of the frozen marks167e reports lists every Saved-shaped reply;
      only turns that wrote a superseding FACT can move;
  (b) agent/config path + reason strings naming the new files
      (loop167e -> loop192, marks167e -> marks192);
  (c) volatile numerics: any key named exactly "seconds" is ignored
      (timings), and "statuses" (mailbox log metadata -- proven
      harness-racy under load on loop167b: two identical loop167b runs
      can differ in statuses with replies, verdicts and fact_writes
      equal);
  (d) q4 unchanged (the 192 change touches no relation-key label).
Sleep verdict (SKIP/pass) identical; summary numbers identical on every
suite. Soak/rt110 flakes under heavy load are the known mailbox race:
re-run that suite once in the open and report both. Any other move
fails the diff honestly.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop192_agent.py --config artifacts/fable-correctreply192-20260922/loop192-config.json --out artifacts/fable-correctreply192-20260922/marks192 --workers 2
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_marksdiff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix192_correctreply as F192  # noqa: E402 (shared move rule)

ROOT = SCRIPTS.parent
REF = ROOT / "artifacts" / "fable-label167e-20260922" / "marks167e"
NEW = ROOT / "artifacts" / "fable-correctreply192-20260922" / "marks192"
ART192 = ROOT / "artifacts" / "fable-correctreply192-20260922"

REPORTS = ["p2-report.json", "p3-report.json", "p4-report.json",
           "q1-report.json", "bench-report.json", "rt81-report.json",
           "sleep-report.json", "soak-report.json", "rt110-report.json",
           "q4-report.json", "fable_marks123_summary.json"]


def _derename(s: str) -> str:
    return (s.replace("loop192", "loop167e")
              .replace("marks192", "marks167e")
              .replace("label192", "label167e")
              .replace("correctreply192", "label167e"))


def _norm(obj):
    """Drop volatile keys, recursively: 'seconds' (timings) and
    'statuses' (mailbox log metadata -- proven harness-racy under load:
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
    strings may differ by exactly the correct-reply move. Records every
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
        if F192.correctreply_move(ref, new) and ref != new:
            moves.append(where)
            return True
        if F192.correctreply_move(_derename(new), ref):
            return True
        return False
    return ref == new


def check_report(ref, new) -> tuple[bool, str, list]:
    moves: list = []
    ok = _strings_equal_or_render(_norm(ref), _norm(new), moves, "$")
    return ok, ("identical" if not moves else
                f"{len(moves)} correctreply-moves"), moves


def check_q4(ref, new) -> tuple[bool, str]:
    if new.get("leaks") != ref.get("leaks"):
        return False, f"q4 leaks differ: {new.get('leaks')} vs {ref.get('leaks')}"
    if new.get("n_replies") != ref.get("n_replies"):
        return False, "q4 reply count differs"
    if new.get("pass") != ref.get("pass"):
        return False, "q4 pass flips (not predicted)"
    return True, "q4 identical as predicted"


def check_sleep(ref, new) -> tuple[bool, str]:
    if _norm({k: v for k, v in new.items() if k != "reason"}) != _norm(
            {k: v for k, v in ref.items() if k != "reason"}):
        return False, "non-reason fields differ"
    if "loop192" not in str(new.get("reason", "")):
        return False, "reason does not name the new agent file"
    return True, "SKIP identical; reason names loop192 as predicted"


def check_summary(ref, new) -> tuple[bool, str]:
    """Suite table: identical numbers on every suite; agent/config paths
    name the new files; sleep number names loop192; seconds ignored."""
    rt, nt = {r["suite"]: r for r in ref.get("table", [])}, \
        {r["suite"]: r for r in new.get("table", [])}
    if set(rt) != set(nt):
        return False, "suite set differs"
    notes = []
    for s, nr in nt.items():
        rr = rt[s]
        if s == "sleep":
            if not (nr["status"] == rr["status"] == "SKIP"
                    and "loop192" in nr["number"]):
                return False, "sleep summary not as predicted"
            notes.append("sleep names loop192")
            continue
        for k in ("bar", "status"):
            if nr.get(k) != rr.get(k):
                return False, f"{s}.{k} differs"
        nn, rn = str(nr.get("number")), str(rr.get("number"))
        if nn != rn and _derename(nn) != rn:
            moves: list = []
            if not _strings_equal_or_render(rr.get("number"),
                                            nr.get("number"), moves, s):
                return False, f"{s}.number differs beyond rename/move"
    return True, "; ".join(notes) + "; all other suite numbers identical"


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
        if name == "q4-report.json":
            ok, note = check_q4(ref, new)
            moves = []
        elif name == "sleep-report.json":
            ok, note = check_sleep(ref, new)
            moves = []
        elif name == "fable_marks123_summary.json":
            ok, note = check_summary(ref, new)
            moves = []
        else:
            ok, note, moves = check_report(ref, new)
        diffs[name] = {"status": "PASS" if ok else "FAIL", "note": note,
                       "moves": moves[:40]}
        print(f"{name}: {'PASS' if ok else 'FAIL'} {note}", flush=True)
        ok_all = ok_all and ok
    (ART192 / "marks192-diff.json").write_text(
        json.dumps(diffs, indent=1), encoding="utf-8")
    print(f"MARKSDIFF {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
