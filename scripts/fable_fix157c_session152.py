#!/usr/bin/env python3
"""Experiment 157c -- G3 sessions re-run through loop157c by import (Muse).

Imports scripts/fable_session152_run.py (runner/judge, read-only) and
swaps the target to the loop157c daemon + loop157c-config. Compares every
reply to the sealed loop157b session runs
(artifacts/fable-filler157b-20260922/turns157b-loop157b-*.json, read-only).
Predicted moves are listed in PASSMARKS.md (pre-seal scan: none); every
other reply byte-identical, 0 new WRONG, 0 new writes.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157c_session152.py
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

import fable_loop157c_agent as L157C  # noqa: E402 (this experiment)
import fable_session152_run as S152R  # noqa: E402 (runner/judge, read-only)
import fable_session152_sessions as S152  # noqa: E402 (sessions, read-only)

ROOT = SCRIPTS.parent
ART157C = ROOT / "artifacts" / "fable-title157c-20260922"
ART157B = ROOT / "artifacts" / "fable-filler157b-20260922"


def main() -> int:
    t0 = time.time()
    ART157C.mkdir(parents=True, exist_ok=True)
    cfg_base = copy.deepcopy(L157C.DEFAULT_CONFIG157C)
    summary: dict = {}
    diffs: dict = {}
    counts: dict = {}
    for s in S152.SESSIONS:
        sid = s["id"]
        root = ART157C / "work-sessions" / sid
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg_base)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L157C.Loop157cDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART157C / f"turns157c-loop157c-{sid}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads(
            (ART157B / f"turns157b-loop157b-{sid}.json").read_text(encoding="utf-8"))
        base_reply = {t["n"]: t["reply"] for t in sealed}
        base_verdict = {t["n"]: t["verdict"] for t in sealed}
        moved = [t["n"] for t in turns
                 if base_reply.get(t["n"]) != t["reply"]]
        new_wrong = [t["n"] for t in turns
                     if t["verdict"] == "WRONG"
                     and base_verdict.get(t["n"]) != "WRONG"]
        new_writes = [t["n"] for t in turns
                      if t["fact_writes"] > 0
                      and sealed[t["n"]]["fact_writes"] == 0]
        cell: dict[str, int] = {}
        for t in turns:
            cell[t["verdict"]] = cell.get(t["verdict"], 0) + 1
        summary[sid] = cell
        diffs[sid] = {"reply_moves": moved, "new_wrong": new_wrong,
                      "new_writes": new_writes}
        counts[sid] = {t["n"]: {"reply": t["reply"],
                                "verdict": t["verdict"],
                                "writes": t["fact_writes"]} for t in turns}
        print(f"{sid}: {cell} moves={moved} new_wrong={new_wrong} "
              f"new_writes={new_writes}", flush=True)
    total = round(time.time() - t0, 1)
    (ART157C / "sessions157c-summary.json").write_text(
        json.dumps({"summary": summary, "diff_vs_loop157b": diffs,
                    "seconds": total}, indent=1), encoding="utf-8")
    print(f"TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
