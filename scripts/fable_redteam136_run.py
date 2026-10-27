#!/usr/bin/env python3
"""Exp 136 -- teach-frame red-team sealed runner (Muse). Read-only vs repo.

Drives loop129b exactly as briefed: fable_fix129_common.new_daemon129b +
process_file through the mailbox, one FRESH daemon dir per case. Reads stored
facts via fable_loop90_agent.notebook_triples. Compares against the SEALED
expectations in cases136.json (never the live CASES list).

Verdicts: OK / WRONG-WRITE (any stored triple outside the expectation) /
MISSED (expected write, got none) / HARNESS-ERROR.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (drivers, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-redteam136-20260922"


def run_case(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = C129.new_daemon129b(root)
    except Exception as exc:  # noqa: BLE001
        return {"id": row["id"], "group": row["group"], "text": row["text"],
                "expect": row["expect"], "stored": [],
                "reply": f"BOOT-FAILED {type(exc).__name__}: {exc}",
                "verdict": "HARNESS-ERROR", "seconds": round(time.time() - t0, 3)}
    (root / "inbox" / "msg_00.txt").write_text(row["text"], encoding="utf-8")
    log: list = []
    try:
        C129.process_pending(daemon, root, log)
        stored = [list(t) for t in L90.notebook_triples(daemon.loop.nb)]
        reply = log[-1]["reply"] if log else "NO-LOG"
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
            "expect": exp, "stored": stored, "reply": reply,
            "verdict": verdict, "seconds": round(time.time() - t0, 3)}


def main() -> int:
    cases = json.loads((ART / "cases136.json").read_text(encoding="utf-8"))
    workroot = ART / "work"
    workroot.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out = [run_case(row, workroot) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    (ART / "results136.json").write_text(
        json.dumps({"wall_seconds": wall, "counts": counts, "cases": out},
                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"n={len(out)} counts={counts} wall={wall}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
