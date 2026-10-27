#!/usr/bin/env python3
"""Experiment 154 -- G3 phone sessions through loop154 by import (Muse).

Reuses scripts/fable_session152_run.py run_session/judge/fact_count by
import with only the daemon class/config swapped to loop154 (the same swap
the brief orders: import the 152 runner, retarget the agent). Outputs go
into artifacts/fable-yesno154-20260922/ only. Replies are diffed against
the sealed T-T run (artifacts/fable-session152-20260922/
turns152-T-T-*.json, read-only): ZERO moves predicted (no session turn is
an "Is ...?" question, so the yes/no stage never fires). Any move fails G3
honestly: 0 new WRONG, 0 new writes except predicted (none).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix154_session152.py
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

import fable_loop154_agent as L154  # noqa: E402 (this experiment)
import fable_session152_run as S152  # noqa: E402 (runner/judge, read-only)

ROOT = SCRIPTS.parent
ART154 = ROOT / "artifacts" / "fable-yesno154-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"


def main() -> int:
    t0 = time.time()
    ART154.mkdir(parents=True, exist_ok=True)
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    base_cfg = json.loads((ART154 / "loop154-config.json").read_text(
        encoding="utf-8"))
    reply_moves: dict = {}
    verdict_moves: dict = {}
    new_wrong: dict = {}
    new_writes: dict = {}
    for s in sessions:
        root = ART154 / "work-sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L154.Loop154Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152.run_session(daemon, root, s)
        for t in turns:
            t.update(S152.judge(t))
        (ART154 / f"turns154-T154-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads(
            (ART152 / f"turns152-T-T-{s['id']}.json").read_text(
                encoding="utf-8"))
        moves, vmoves, wrong, writes = [], [], [], []
        for got, ref in zip(turns, sealed):
            if got["reply"] != ref["reply"]:
                moves.append(got["n"])
            if got["verdict"] != ref["verdict"]:
                vmoves.append(got["n"])
            if got["verdict"] == "WRONG" and ref["verdict"] != "WRONG":
                wrong.append(got["n"])
            if got["fact_writes"] != ref["fact_writes"]:
                writes.append(got["n"])
        reply_moves[s["id"]] = moves
        verdict_moves[s["id"]] = vmoves
        new_wrong[s["id"]] = wrong
        new_writes[s["id"]] = writes
        counts = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        print(f"T154 {s['id']}: {counts} reply_moves={moves} "
              f"verdict_moves={vmoves} new_wrong={wrong} "
              f"new_writes={writes}", flush=True)
    out = {"seconds": round(time.time() - t0, 1),
           "reply_moves": reply_moves, "verdict_moves": verdict_moves,
           "new_wrong": new_wrong, "new_writes": new_writes}
    (ART154 / "run154-sessions-summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"TOTAL seconds={out['seconds']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
