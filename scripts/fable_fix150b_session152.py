#!/usr/bin/env python3
"""Experiment 150b -- G3 exp-152 phone sessions through loop150b (Muse).

Imports scripts/fable_session152_run.py (read-only, never edited) for
run_session/judge and swaps the target to loop150b: each of the 6 sealed
sessions (artifacts/fable-session152-20260922/sessions152.json, read-only)
runs through a fresh Loop150bDaemon through the mailbox exactly like the
152 harness. Per-turn replies are diffed against the sealed T-T run
(artifacts/fable-session152-20260922/turns152-T-T-*.json, read-only):
every reply identical except turns predicted in writing before the run
(ZERO predicted: pure-function scan of all session teach subjects fires
nowhere; see PASSMARKS.md), 0 new WRONG, 0 new writes except predicted.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix150b_session152.py
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

import fable_session152_run as S152R  # noqa: E402 (runner fns, read-only)
import fable_loop150b_agent as L150b  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART152 = ROOT / "artifacts" / "fable-session152-20260922"
ART150B = ROOT / "artifacts" / "fable-subject150b-20260922"


def main() -> int:
    cfg_base = copy.deepcopy(L150b.DEFAULT_CONFIG150B)
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    ART150B.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    summary: dict = {}
    reply_diffs: dict = {}
    verdict_moves: dict = {}
    for s in sessions:
        root = ART150B / "work-sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg_base)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L150b.Loop150bDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART150B / f"turns150b-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads(
            (ART152 / f"turns152-T-T-{s['id']}.json").read_text(
                encoding="utf-8"))
        base_reply = {t["n"]: t["reply"] for t in sealed}
        base_verdict = {t["n"]: t["verdict"] for t in sealed}
        base_writes = {t["n"]: t["fact_writes"] for t in sealed}
        diffs = [t["n"] for t in turns
                 if base_reply.get(t["n"]) != t["reply"]]
        moves = [(t["n"], base_verdict.get(t["n"]), t["verdict"])
                 for t in turns
                 if base_verdict.get(t["n"]) != t["verdict"]]
        new_wrong = [t["n"] for t in turns
                     if t["verdict"] == "WRONG"
                     and base_verdict.get(t["n"]) != "WRONG"]
        new_writes = [(t["n"], base_writes.get(t["n"]), t["fact_writes"])
                      for t in turns
                      if t["fact_writes"] != base_writes.get(t["n"])]
        reply_diffs[s["id"]] = diffs
        verdict_moves[s["id"]] = {"moves": moves, "new_wrong": new_wrong,
                                  "new_writes": new_writes}
        counts: dict[str, int] = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        summary[s["id"]] = counts
        print(f"{s['id']}: {counts} reply_diffs={diffs} moves={moves} "
              f"new_wrong={new_wrong} new_writes={new_writes}", flush=True)
    total = round(time.time() - t0, 1)
    (ART150B / "sessions150b-summary.json").write_text(json.dumps(
        {"summary": summary, "seconds": total, "reply_diffs": reply_diffs,
         "verdict_moves": verdict_moves}, indent=1), encoding="utf-8")
    print(f"TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
