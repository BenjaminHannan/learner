#!/usr/bin/env python3
"""Experiment 157b -- G3 session re-run through loop157b by import (Muse).

Imports scripts/fable_session152_run.py (runner/judge, read-only) and
swaps the target to the loop157b daemon + loop157b-config. Compares every
reply to the sealed loop157 session runs
(artifacts/fable-filler157-20260922/turns157-loop157-*.json, read-only).
Predicted moves are listed in PASSMARKS.md (pre-seal scan: none); every
other reply byte-identical, 0 new WRONG, 0 new writes. The sealed T-T
diffs are inherited unchanged from loop157 (recorded in its
sessions157-summary.json).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix157b_session152.py
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

import fable_loop157b_agent as L157B  # noqa: E402 (this experiment)
import fable_session152_run as S152R  # noqa: E402 (runner/judge, read-only)
import fable_session152_sessions as S152  # noqa: E402 (sessions, read-only)

ROOT = SCRIPTS.parent
ART157B = ROOT / "artifacts" / "fable-filler157b-20260922"
ART157 = ROOT / "artifacts" / "fable-filler157-20260922"


def main() -> int:
    t0 = time.time()
    ART157B.mkdir(parents=True, exist_ok=True)
    cfg_base = copy.deepcopy(L157B.DEFAULT_CONFIG157B)
    summary: dict = {}
    diffs: dict = {}
    counts: dict = {}
    for s in S152.SESSIONS:
        sid = s["id"]
        root = ART157B / "work-sessions" / sid
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg_base)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L157B.Loop157bDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART157B / f"turns157b-loop157b-{sid}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads(
            (ART157 / f"turns157-loop157-{sid}.json").read_text(encoding="utf-8"))
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
    (ART157B / "sessions157b-summary.json").write_text(
        json.dumps({"summary": summary, "diff_vs_loop157": diffs,
                    "seconds": total}, indent=1), encoding="utf-8")
    print(f"TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
