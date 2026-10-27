#!/usr/bin/env python3
"""Exp 144 F1 -- multi-"of"-name probe: 26 must-write + 20 genuine two-fact.

Each case runs in ONE FRESH daemon through the mailbox (same harness shape
as scripts/fable_fix140_t1.py, read-only, never edited).

  must-write: reply must start with "Saved:" and the notebook must hold
    exactly the expected triple -- else MISSED (nothing stored) or
    WRONG-WRITE (something else stored).
  two-fact:   the notebook must gain ZERO facts (refusing is fine, any
    clarify text is fine) and the reply must not be a save -- else
    WRONG-WRITE.

Bar (sealed in PASSMARKS.md): must-write >= 25/26 exact triples with
0 wrong writes; two-fact 20/20 with 0 writes of any wrong triple.

Writes only under artifacts/fable-fix144-20260922/ (never elsewhere).
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix144_f1.py --out artifacts/fable-fix144-20260922
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop144_agent as L144  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-fix144-20260922"


def run_case(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        cfg = copy.deepcopy(L144.DEFAULT_CONFIG144)
        cfg["sleep_threshold"] = 100000
        daemon = L144.Loop144Daemon(root, cfg=cfg, idle_seconds=3600.0)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "kind": row["kind"], "text": row["text"],
                "stored": [], "reply": f"BOOT-FAILED {exc!r}",
                "verdict": "HARNESS-ERROR",
                "seconds": round(time.time() - t0, 3)}
    (root / "inbox" / "msg_00.txt").write_text(row["text"], encoding="utf-8")
    try:
        daemon.process_file(root / "inbox" / "msg_00.txt")
        stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
        reply = (root / "outbox" / "msg_00.txt").read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "kind": row["kind"], "text": row["text"],
                "stored": [], "reply": f"HARNESS-CAUGHT {exc!r}",
                "verdict": "HARNESS-ERROR",
                "seconds": round(time.time() - t0, 3)}
    rep = {"id": row["id"], "kind": row["kind"], "frame": row.get("frame"),
           "text": row["text"], "stored": stored,
           "reply": reply.strip()[:160],
           "seconds": round(time.time() - t0, 3)}
    if row["kind"] == "must-write":
        want = [list(row["expect"])]
        rep["expect"] = row["expect"]
        if stored == want and reply.strip().startswith("Saved:"):
            rep["verdict"] = "OK"
        elif not stored:
            rep["verdict"] = "MISSED"
        else:
            rep["verdict"] = "WRONG-WRITE"
    else:
        if not stored and not reply.strip().startswith("Saved:"):
            rep["verdict"] = "OK"
        else:
            rep["verdict"] = "WRONG-WRITE"
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 144 F1 of-name probe")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((out / "f1-cases.json").read_text(
        encoding="utf-8"))["cases"]
    workroot = out / "work-f1"
    workroot.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = [run_case(row, workroot) for row in cases]
    must = [r for r in rows if r["kind"] == "must-write"]
    two = [r for r in rows if r["kind"] == "two-fact"]
    must_ok = sum(r["verdict"] == "OK" for r in must)
    two_ok = sum(r["verdict"] == "OK" for r in two)
    wrong = sum(r["verdict"] == "WRONG-WRITE" for r in rows)
    harness = sum(r["verdict"] == "HARNESS-ERROR" for r in rows)
    ok = (must_ok >= 25 and wrong == 0 and harness == 0
          and two_ok == len(two) and len(must) == 26 and len(two) == 20)
    rep = {"bar": ("must-write >= 25/26 exact, 0 wrong writes; "
                   "two-fact 20/20 no-write"),
           "n_must": len(must), "must_ok": must_ok,
           "n_two": len(two), "two_ok": two_ok,
           "wrong_writes": wrong, "harness_errors": harness,
           "pass": bool(ok), "seconds": round(time.time() - t0, 1),
           "cases": rows}
    (out / "f1-report.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"F1 must={must_ok}/{len(must)} two={two_ok}/{len(two)} "
          f"wrong={wrong} harness={harness} -> "
          f"{'PASS' if ok else 'FAIL'} ({rep['seconds']} s)")
    for r in rows:
        if r["verdict"] != "OK":
            print(f"  {r['id']}: {r['verdict']} text={r['text']!r} "
                  f"stored={r['stored']!r} reply={r['reply']!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
