#!/usr/bin/env python3
"""Exp 140 T1 -- NEW tail probe: emoji/symbol tails, quotes, abbreviations.

44 teach sentences (possessive + bench73 + bench92 frames + symbol-in-name
values from the benchmark answer lists + no-tail controls). One FRESH daemon
per case through the mailbox, exactly like the redteam136 harness. Bar: every
value stored exactly as expected, 0 wrong writes. Plus function-level checks
that subject spans get the same cleaner.

Writes only under artifacts/fable-fix140-20260922/ (never elsewhere).
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix140_t1.py --out artifacts/fable-fix140-20260922
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix140_tail as T140  # noqa: E402 (this experiment)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop140_agent as L140  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix140-20260922"

# Function-level: subject spans get the same cleaner (unit checks, no daemon).
SUBJECT_CHECKS = [
    ("Tom", "Tom"),
    ("the U.S.", "the U.S."),
    ("Washington, D.C.", "Washington, D.C."),
    ("Kip Dune", "Kip Dune"),
    ("St. Louis", "St. Louis"),
]


def run_case(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = L140.Loop140Daemon(
            root, cfg={"sleep_threshold": 100000}, idle_seconds=3600.0)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "text": row["text"], "expect": row["expect"],
                "stored": [], "reply": f"BOOT-FAILED {exc!r}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    (root / "inbox" / "msg_00.txt").write_text(row["text"], encoding="utf-8")
    try:
        daemon.process_file(root / "inbox" / "msg_00.txt")
        stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
        reply = (root / "outbox" / "msg_00.txt").read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "text": row["text"], "expect": row["expect"],
                "stored": [], "reply": f"HARNESS-CAUGHT {exc!r}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    want = [list(row["expect"])]
    if stored == want:
        verdict = "OK"
    elif not stored:
        verdict = "MISSED"
    else:
        verdict = "WRONG-WRITE"
    return {"id": row["id"], "frame": row.get("frame"), "text": row["text"],
            "expect": row["expect"], "stored": stored, "reply": reply.strip()[:120],
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 140 T1 tail probe")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((out / "t1-cases.json").read_text(encoding="utf-8"))["cases"]
    workroot = out / "work-t1"
    workroot.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = [run_case(row, workroot) for row in cases]
    subj = [{"input": s, "want": w, "got": T140.clean_span(s),
             "ok": T140.clean_span(s) == w} for s, w in SUBJECT_CHECKS]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    rep = {"bar": "44/44 OK values exact, 0 wrong writes; subject checks 5/5",
           "n": len(rows), "counts": counts,
           "subject_checks": subj,
           "subject_ok": sum(s["ok"] for s in subj),
           "pass": counts.get("OK", 0) == len(rows) and all(s["ok"] for s in subj),
           "seconds": round(time.time() - t0, 1), "cases": rows}
    (out / "t1-report.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"T1 n={len(rows)} counts={counts} subject={rep['subject_ok']}/5 "
          f"-> {'PASS' if rep['pass'] else 'FAIL'} ({rep['seconds']} s)")
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  {r['id']}: {r['verdict']} text={r['text']!r} "
                  f"stored={r['stored']!r} want={r['expect']!r}")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
