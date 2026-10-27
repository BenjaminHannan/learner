#!/usr/bin/env python3
"""Experiment 150 -- S4 red-team-136 re-run through loop150 (Muse).

Same semantics as scripts/fable_fix139b_redteam136.py (fresh daemon dir per
case, mailbox process_file, triples via notebook_triples, verdicts vs the
SEALED artifacts/fable-redteam136-20260922/cases136.json) with only the
daemon factory swapped to loop150. Never overwrites the 136 artifacts:
all outputs go to artifacts/fable-fix150-20260922/. Per-case verdicts are
diffed against the sealed loop139b run
(artifacts/fable-fix139b-20260922/redteam136-loop139b.json, read-only):
ZERO moves predicted (none of the 14 loop139b WRONG-WRITE subjects hits the
150 screen; the 5 MISSED cases are unparseable/clarify paths the guard never
touches; see PASSMARKS.md). No case worse than loop139b passes S4.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix150_redteam136.py
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
import fable_loop150_agent as L150  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART136 = ROOT / "artifacts" / "fable-redteam136-20260922"
ART139B = ROOT / "artifacts" / "fable-fix139b-20260922"
ART150 = ROOT / "artifacts" / "fable-fix150-20260922"


def new_daemon150(root: Path):
    cfg = copy.deepcopy(L150.DEFAULT_CONFIG150)
    cfg["state_dir"] = str(root)
    cfg["sleep_threshold"] = 100000
    return L150.Loop150Daemon(root, cfg=cfg, idle_seconds=3600.0)


def run_case150(row: dict, workroot: Path) -> dict:
    root = Path(tempfile.mkdtemp(prefix=row["id"] + "_", dir=str(workroot)))
    (root / "inbox").mkdir(exist_ok=True)
    t0 = time.time()
    try:
        daemon = new_daemon150(root)
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
    workroot = ART150 / "redteam136-tmp"
    workroot.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out = [run_case150(row, workroot) for row in cases]
    wall = round(time.time() - t0, 1)
    counts: dict[str, int] = {}
    for r in out:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    sealed = json.loads((ART139B / "redteam136-loop139b.json").read_text(
        encoding="utf-8"))
    base = {c["id"]: c.get("verdict") for c in sealed["cases"]}
    worse = [r["id"] for r in out
             if base.get(r["id"]) == "OK" and r["verdict"] != "OK"]
    moves = [(r["id"], base.get(r["id"]), r["verdict"]) for r in out
             if base.get(r["id"]) != r["verdict"]]
    (ART150 / "redteam136-loop150.json").write_text(
        json.dumps({"wall_seconds": wall, "counts": counts,
                    "vs_loop139b_moves": moves, "worse_than_loop139b": worse,
                    "cases": out},
                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"n={len(out)} counts={counts} wall={wall}s")
    print(f"vs loop139b moves={moves} worse={worse}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
