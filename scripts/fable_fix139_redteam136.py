#!/usr/bin/env python3
"""Experiment 139 -- V2 red-team-136 re-run through loop139 (Muse).

Same semantics as scripts/fable_redteam136_run.py (fresh daemon dir per
case, mailbox process_file, triples via notebook_triples, verdicts vs the
SEALED artifacts/fable-redteam136-20260922/cases136.json) with only the
daemon factory swapped to loop139. Never overwrites the 136 artifacts:
all outputs go to artifacts/fable-fix139-20260922/.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix139_redteam136.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix129_common as C129  # noqa: E402 (mailbox driver, read-only)
import fable_loop90_agent as L90  # noqa: E402 (notebook_triples, read-only)
import fable_loop139_agent as L139  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139 = ROOT / "artifacts" / "fable-fix139-20260922"


def new_daemon139(root: Path):
    cfg = copy.deepcopy(L139.DEFAULT_CONFIG139)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L139.Loop139Daemon(root, cfg=cfg, idle_seconds=3600.0)


def run_case139(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = new_daemon139(root)
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
    cases = json.loads((ART136 / "cases136.json").read_text(encoding="utf-8"))
    workroot = ART139 / "redteam136-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out = [run_case139(row, workroot) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    (ART139 / "redteam136-loop139.json").write_text(
        json.dumps({"wall_seconds": wall, "counts": counts, "cases": out},
                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"n={len(out)} counts={counts} wall={wall}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
