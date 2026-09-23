#!/usr/bin/env python3
"""Experiment 155 -- G3 exp-152 phone sessions through loop155 (Muse).

Imports scripts/fable_session152_run.py (runner/judge, read-only) and swaps
the target to this experiment's agent: each of the 6 sealed sessions runs
through a fresh Loop155Daemon (loop155-config + sleep_threshold 100000,
idle_seconds 3600.0, exactly like the 152 harness). Every reply is diffed
against the sealed T-T run (artifacts/fable-session152-20260922/
turns152-T-T-<session>.json, read-only): ZERO reply moves predicted
(pre-seal pure-function scan: no session turn matches an inverted frame
with an allowed relation; the two "who is ...'s ..." shapes are questions
and stay on the base path via the kinds-gate; see PASSMARKS.md). Any move
fails G3 honestly. 0 new WRONG, 0 new writes except predicted (none).

Reads: artifacts/fable-session152-20260922/sessions152.json (sealed,
read-only). Writes: only artifacts/fable-inverted155-20260922/.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix155_sessions.py
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

import fable_loop155_agent as L155  # noqa: E402 (this experiment)
import fable_session152_run as S152R  # noqa: E402 (runner/judge, read-only)

ROOT = SCRIPTS.parent
ART155 = ROOT / "artifacts" / "fable-inverted155-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"


def main() -> int:
    ART155.mkdir(parents=True, exist_ok=True)
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    cfg_base = copy.deepcopy(L155.DEFAULT_CONFIG155)
    summary: dict = {}
    reply_moves: dict = {}
    wrong_moves: dict = {}
    write_moves: dict = {}
    t0 = time.time()
    for s in sessions:
        root = ART155 / "work-sessions" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg_base)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L155.Loop155Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART155 / f"turns155-{s['id']}.json").write_text(
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
    (ART155 / "sessions155-summary.json").write_text(json.dumps(
        {"summary": summary, "seconds": total, "reply_moves": reply_moves,
         "new_wrong": wrong_moves, "write_moves": write_moves}, indent=1),
        encoding="utf-8")
    print(f"TOTAL {total} s")
    shutil.rmtree(ART155 / "work-sessions", ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
