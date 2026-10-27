#!/usr/bin/env python3
"""Exp 140 T2 -- red team 136 re-run with the loop140 daemon factory swapped.

Reads the SEALED cases (artifacts/fable-redteam136-20260922/cases136.json,
never written); one FRESH loop140 daemon dir per case through the mailbox;
stored triples via fable_loop90_agent.notebook_triples. Verdicts identical
to scripts/fable_redteam136_run.py: OK / WRONG-WRITE / MISSED / HARNESS-ERROR.

Writes ONLY under the given --out dir (default
artifacts/fable-fix140-20260922/): redteam140.json.
Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix140_redteam136.py --out artifacts/fable-fix140-20260922
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
import fable_loop140_agent as L140  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART = ROOT / "artifacts" / "fable-fix140-20260922"

FOCUS = ("C117", "C118", "C119", "C126", "C140")


def run_case(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = L140.Loop140Daemon(
            root, cfg={"sleep_threshold": 100000}, idle_seconds=3600.0)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"BOOT-FAILED {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    (root / "inbox" / "msg_00.txt").write_text(row["text"], encoding="utf-8")
    try:
        daemon.process_file(root / "inbox" / "msg_00.txt")
        stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
        reply = (root / "outbox" / "msg_00.txt").read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"HARNESS-CAUGHT {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    exp = row["expect"]
    if exp == "nowrite":
        verdict = "OK" if not stored else "WRONG-WRITE"
    else:
        want = [list(exp)]
        if stored == want:
            verdict = "OK"
        elif not stored:
            verdict = "MISSED"
        else:
            verdict = "WRONG-WRITE"
    return {"id": row["id"], "group": row["group"], "text": row["text"],
            "expect": exp, "stored": stored, "reply": reply.strip()[:160],
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 140 T2 redteam136 re-run")
    ap.add_argument("--out", default=str(ART))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    sealed = json.loads((ART136 / "results136.json").read_text(encoding="utf-8"))
    sealed_verdict = {c["id"]: c["verdict"] for c in sealed["cases"]}
    workroot = out / "work-rt140"
    workroot.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = [run_case(row, workroot) for row in cases]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    focus = {r["id"]: {"verdict": r["verdict"], "stored": r["stored"],
                       "expect": r["expect"]} for r in rows if r["id"] in FOCUS}
    ok_stayed_ok = [r["id"] for r in rows
                    if sealed_verdict.get(r["id"]) == "OK" and r["verdict"] == "OK"]
    ok_total = sum(1 for c in cases if sealed_verdict.get(c["id"]) == "OK")
    ok_regressed = [r["id"] for r in rows
                    if sealed_verdict.get(r["id"]) == "OK" and r["verdict"] != "OK"]
    rep = {"bar": "C117 C118 C119 C126 C140 exact; every prior OK stays OK",
           "n": len(rows), "counts": counts, "focus": focus,
           "ok_stayed_ok": len(ok_stayed_ok), "ok_total": ok_total,
           "ok_regressed": ok_regressed,
           "pass": (all(f["verdict"] == "OK"
                        and ([list(f["expect"])] == f["stored"])
                        for f in focus.values())
                    and not ok_regressed),
           "seconds": round(time.time() - t0, 1),
           "sealed_verdicts": sealed_verdict, "cases": rows}
    (out / "redteam140.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"T2 n={len(rows)} counts={counts} focus5="
          f"{ {k: v['verdict'] for k, v in focus.items()} } "
          f"ok_stayed={len(ok_stayed_ok)}/{ok_total} "
          f"-> {'PASS' if rep['pass'] else 'FAIL'} ({rep['seconds']} s)")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
