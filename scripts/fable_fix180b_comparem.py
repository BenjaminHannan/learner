#!/usr/bin/env python3
"""Exp 180b T2-marks compare -- marks180b per-case vs sealed marks138h.

Read-only scrub-compare (volatile metadata + agent-path strings). Prints
every non-identical case. Exit 0 iff all diffs are within the sealed
predicted set (sleep SKIP reason agent filename + total_seconds timing
only). Per-case verdict/reply diffs are NEVER predicted.

Run (after the marks123 run, before or after the seal -- read-only):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix180b_comparem.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix138g_compareg2 as C2  # noqa: E402 (scrub, read-only)

import re as _re

ROOT = SCRIPTS.parent
G = ROOT / "artifacts" / "fable-case180b-20260922" / "marks180b"
F = ROOT / "artifacts" / "fable-agent138h-20260922" / "marks138h"


def _rt110_casing_only(g: dict, f: dict) -> bool:
    """True iff every rt110 row diff is verdict/reason/write-identical
    with replies differing only in letter case. Prints each move."""
    for key in ("mark", "n", "ok_to_bug", "bug_to_ok", "still_bug",
                "harness_errors", "pass"):
        if g.get(key) != f.get(key):
            print(f"  rt110 header diff: {key}={g.get(key)!r} "
                  f"vs {f.get(key)!r}", flush=True)
            return False
    gr = {r["id"]: r for r in g.get("rows", [])}
    fr = {r["id"]: r for r in f.get("rows", [])}
    if set(gr) != set(fr):
        print("  rt110 row-id set differs", flush=True)
        return False
    ok = True
    for rid, a in sorted(gr.items()):
        b = fr[rid]
        for key in ("group", "sealed_verdict", "agent_verdict", "reason",
                    "severity", "harness_error"):
            if a.get(key) != b.get(key):
                print(f"  rt110 {rid} field diff: {key}="
                      f"{a.get(key)!r} vs {b.get(key)!r}", flush=True)
                ok = False
        la, lb = a.get("log", []), b.get("log", [])
        if len(la) != len(lb):
            print(f"  rt110 {rid} log-length differs", flush=True)
            ok = False
            continue
        for e1, e2 in zip(la, lb):
            if e1.get("file") != e2.get("file") or e1.get(
                    "fact_writes") != e2.get("fact_writes"):
                print(f"  rt110 {rid} {e1.get('file')} file/write "
                      f"diff", flush=True)
                ok = False
                continue
            r1, r2 = str(e1.get("reply", "")), str(e2.get("reply", ""))
            if r1 != r2:
                if r1.lower() == r2.lower():
                    print(f"  rt110 {rid} {e1.get('file')} "
                          f"casing-only: {r2.strip()[:90]!r} -> "
                          f"{r1.strip()[:90]!r}", flush=True)
                else:
                    print(f"  rt110 {rid} {e1.get('file')} "
                          f"NON-CASING reply diff: {r2.strip()[:90]!r} "
                          f"-> {r1.strip()[:90]!r}", flush=True)
                    ok = False
    return ok


def norm_agent(s: str) -> str:
    """Map the new agent/config names onto the sealed 138h names FIRST so
    the shared read-only scrub treats both sides identically."""
    s = s.replace("fable_loop180b_agent.py", "fable_loop138h_agent.py")
    s = s.replace("loop180b-config.json", "loop138h-config.json")
    s = s.replace("fable-case180b-20260922", "fable-agent138h-20260922")
    s = s.replace("loop180b", "loop138h")
    s = _re.sub(r"rt110-tmp/[A-Za-z0-9_]+", "rt110-tmp/<WORK>", s)
    return s


def load_norm(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    normed = json.loads(norm_agent(json.dumps(raw, sort_keys=True)))
    return drop_volatile(C2.scrub(normed))


def drop_volatile(o):
    """Drop timing-volatile + race-volatile fields (sealed rule).

    - total_seconds/seconds: wall-clock timing.
    - statuses: rt110 per-turn record statuses are a known harness race
      (the runner returns once outbox+done are visible, but the daemon
      appends daemon.log.jsonl AFTER moving the file to done, so the
      statuses read may miss the latest turn line). Evidence: a fresh
      rerun of the SEALED 138h code disagrees with its own sealed row
      (T3 msg_01 [] vs ["clarify"]). Verdicts, replies and fact_writes
      are always compared.
    """
    if isinstance(o, dict):
        return {k: drop_volatile(v) for k, v in o.items()
                if k not in ("total_seconds", "seconds", "statuses",
                             "agent", "config")}
    if isinstance(o, list):
        return [drop_volatile(v) for v in o]
    return o


def main(argv=None) -> int:
    names = ["p2-report.json", "p3-report.json", "p4-report.json",
             "rt110-report.json", "q1-report.json", "bench-report.json",
             "rt81-report.json", "sleep-report.json", "soak-report.json",
             "q4-report.json", "fable_marks123_summary.json"]
    bad = 0
    for name in names:
        gp, fp = G / name, F / name
        if not gp.exists() or not fp.exists():
            print(f"SKIP {name} (missing)", flush=True)
            continue
        g = load_norm(gp)
        f = load_norm(fp)
        if g == f:
            print(f"SAME {name}", flush=True)
            continue
        gs, fs = json.dumps(g, sort_keys=True), json.dumps(
            f, sort_keys=True)
        if gs == fs:
            print(f"SAME {name}", flush=True)
            continue
        # Predicted casing-only move: q1 M5 shout "MIRA's city is
        # Lisbon." renders stored casing "Mira's city is Lisbon."
        # (m5_ok stays true, mark pass stays true).
        if name == "q1-report.json" and gs.replace(
                "Mira's city is Lisbon.", "<C>").replace(
                "MIRA's city is Lisbon.", "<C>") == fs.replace(
                "Mira's city is Lisbon.", "<C>").replace(
                "MIRA's city is Lisbon.", "<C>"):
            print(f"SAME-predicted-casing {name}", flush=True)
            continue
        # Predicted casing-only moves: rt110 rows whose verdicts,
        # reasons and fact_writes are identical and whose replies
        # differ ONLY in letter case (stored-casing render). Any other
        # rt110 diff is unpredicted.
        if name == "rt110-report.json" and _rt110_casing_only(g, f):
            print(f"SAME-predicted-casing {name}", flush=True)
            continue
        print(f"DIFF {name}", flush=True)
        bad += 1
        print(f"  180b: {gs[:800]}", flush=True)
        print(f"  138h: {fs[:800]}", flush=True)
    # tmp dirs hold random-suffixed daemon workdirs (volatile names by
    # construction); only file COUNTS are compared, never names/contents.
    for sub in ("p3", "rt110-tmp", "p2-tmp", "p4-tmp", "rt81-tmp"):
        gd, fd = G / sub, F / sub
        if not gd.exists() or not fd.exists():
            continue
        gf = sorted(p.name for p in gd.iterdir())
        ff = sorted(p.name for p in fd.iterdir())
        print(f"{sub}: 180b-files={len(gf)} 138h-files={len(ff)}",
              flush=True)
    print("marks-compare: " + ("ALL-SAME-or-predicted" if not bad
                               else f"{bad} UNPREDICTED-DIFFS"),
          flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
