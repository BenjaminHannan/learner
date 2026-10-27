#!/usr/bin/env python3
"""Experiment 153 -- G3 exp-152 phone sessions re-run with loop153 (Muse).

Imports scripts/fable_session152_run.py (run_session/judge, read-only) and
swaps the target to loop153 (scripts/fable_loop153_agent.py:Loop153Daemon +
artifacts/fable-reverse153-20260922/loop153-config.json). Compares every
turn's reply, verdict and fact_writes to the sealed T-T run
(artifacts/fable-session152-20260922/turns152-T-T-*.json, read-only): ZERO
reply moves, 0 new WRONG and 0 new writes predicted (no session turn matches
any reverse frame -- see PASSMARKS.md). Any move fails G3 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix153_session.py
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

import fable_loop153_agent as L153  # noqa: E402 (this experiment)
import fable_session152_run as S152R  # noqa: E402 (harness, read-only)
import fable_session152_sessions as S152  # noqa: E402 (sessions, read-only)

ROOT = SCRIPTS.parent
ART153 = ROOT / "artifacts" / "fable-reverse153-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"


def main() -> int:
    cfg = copy.deepcopy(L153.DEFAULT_CONFIG153)
    ART153.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    moves: list[dict] = []
    new_wrong = 0
    new_writes = 0
    per_session: dict = {}
    for s in S152.SESSIONS:
        root = ART153 / "work-sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        dc = copy.deepcopy(cfg)
        dc["state_dir"] = str(root)
        dc["sleep_threshold"] = 100000
        daemon = L153.Loop153Daemon(root, cfg=dc, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART153 / f"turns153-loop153-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads(
            (ART152 / f"turns152-T-T-{s['id']}.json").read_text(
                encoding="utf-8"))
        base = {t["n"]: t for t in sealed}
        counts: dict[str, int] = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
            b = base.get(t["n"], {})
            if t["reply"] != b.get("reply"):
                moves.append({"session": s["id"], "n": t["n"],
                              "base": b.get("reply"),
                              "loop153": t["reply"]})
            if t["verdict"] == "WRONG" and b.get("verdict") != "WRONG":
                new_wrong += 1
            if t["fact_writes"] > b.get("fact_writes", 0):
                new_writes += t["fact_writes"] - b.get("fact_writes", 0)
        per_session[s["id"]] = counts
        print(f"{s['id']}: {counts}", flush=True)
    total = round(time.time() - t0, 1)
    payload = {"seconds": total, "per_session": per_session,
               "reply_moves": moves, "new_wrong": new_wrong,
               "new_writes": new_writes}
    (ART153 / "sessions153-summary.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"moves={len(moves)} new_wrong={new_wrong} "
          f"new_writes={new_writes} total={total}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
