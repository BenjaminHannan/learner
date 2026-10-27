#!/usr/bin/env python3
"""Experiment 163 -- G3 exp-152 phone sessions through loop163 (Muse).

Imports scripts/fable_session152_run.py (runner/judge, read-only) and swaps
the target to this experiment's agent: each of the 6 sealed sessions runs
through a fresh Loop163Daemon (loop163-config + sleep_threshold 100000,
idle_seconds 3600.0, exactly like the 152 harness). Every reply is diffed
against the sealed T-T run (artifacts/fable-session152-20260922/
turns152-T-T-<session>.json, read-only). Predicted reply moves (display-form
owner/value names; judge stays case-insensitive, verdicts unchanged):
  S2-casual-friends turns [18, 23]
    (lowercase ask owners -> display form; literal answers unchanged);
  S5-robustness turns [4, 10, 12, 13, 14, 25]
    (lowercase ask owners -> display form; turn 12 also stores person value
    Quinn capitalised, echoed in 13/14/25).
Zero moves predicted in S1/S3/S4/S6. 0 new WRONG, 0 write moves predicted
(see PASSMARKS.md). Any unpredicted move fails G3 honestly.

Reads: artifacts/fable-session152-20260922/sessions152.json (sealed,
read-only). Writes: only artifacts/fable-lowercase163-20260922/.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix163_session.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop163_agent as L163  # noqa: E402 (this experiment)
import fable_session152_run as S152R  # noqa: E402 (runner/judge, read-only)

ROOT = SCRIPTS.parent
ART163 = ROOT / "artifacts" / "fable-lowercase163-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"


def main() -> int:
    ART163.mkdir(parents=True, exist_ok=True)
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    cfg_base = copy.deepcopy(L163.DEFAULT_CONFIG163)
    summary: dict = {}
    reply_moves: dict = {}
    wrong_moves: dict = {}
    write_moves: dict = {}
    t0 = time.time()
    for s in sessions:
        root = ART163 / "work-sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg_base)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L163.Loop163Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART163 / f"turns163-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads((ART152 / f"turns152-T-T-{s['id']}.json"
                             ).read_text(encoding="utf-8"))
        ref = {t["n"]: t for t in sealed}
        moves, wrongs, writes = [], [], []
        for t in turns:
            r = ref.get(t["n"], {})
            if r.get("reply") != t["reply"]:
                moves.append(t["n"])
            if t["verdict"] == "WRONG" and r.get("verdict") != "WRONG":
                wrongs.append(t["n"])
            if t["fact_writes"] != r.get("fact_writes"):
                writes.append({"n": t["n"], "base": r.get("fact_writes"),
                               "new": t["fact_writes"]})
        counts: dict[str, int] = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        summary[s["id"]] = counts
        reply_moves[s["id"]] = moves
        wrong_moves[s["id"]] = wrongs
        write_moves[s["id"]] = writes
        print(f"{s['id']}: {counts} reply_moves={moves} "
              f"new_wrong={wrongs} write_moves={writes}", flush=True)
    total = round(time.time() - t0, 1)
    (ART163 / "sessions163-summary.json").write_text(json.dumps(
        {"summary": summary, "seconds": total, "reply_moves": reply_moves,
         "new_wrong": wrong_moves, "write_moves": write_moves}, indent=1),
        encoding="utf-8")
    print(f"TOTAL {total} s")
    shutil.rmtree(ART163 / "work-sessions", ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
