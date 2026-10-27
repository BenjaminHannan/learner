#!/usr/bin/env python3
"""Experiment 137e G3-sessions driver -- exp-152 phone sessions, loop137e.

Reuses scripts/fable_session152_run.py BY IMPORT (sealed sessions,
run_session mailbox driver, judge) with the target daemon swapped to
loop137e. Compares per-turn verdicts AND replies against loop137c's own
frozen rows (artifacts/fable-hypo137c-20260922/sessions152-loop137c.json).
Inbox writes use the atomic-write client rule (tmp + rename). Bar: 0 new
WRONG vs loop137c; every move listed (predicted: none -- pre-seal
real-agent scan scripts/fable_fix137e_scan.py executed all 180 session
turns live on loop137e + loop137c: 0 frame-kind fires, all
reply+writes equal). Outputs into
artifacts/fable-frame137e-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137e_sessions.py
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop137e_agent as L137E  # noqa: E402 (agent under test)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-frame137e-20260922"
ART137C = ROOT / "artifacts" / "fable-hypo137c-20260922"


def run_target(tag: str, daemon_cls, base_cfg: dict) -> dict:
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / f"work-sessions-{tag}" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(base_cfg)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = daemon_cls(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / f"sessions152-{tag}.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    return sessions_out


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    out137e = run_target("loop137e", L137E.Loop137eDaemon,
                         L137E.DEFAULT_CONFIG137E)
    base = json.loads((ART137C / "sessions152-loop137c.json").read_text(
        encoding="utf-8"))
    moves, reply_moves, new_wrong = [], [], 0
    counts137c: Counter = Counter()
    counts137e: Counter = Counter()
    for sid, turns in out137e.items():
        for t, b in zip(turns, base.get(sid, [])):
            counts137c[b["verdict"]] += 1
            counts137e[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop137c": b["verdict"],
                              "loop137e": t["verdict"],
                              "reply137c": str(b["reply"]).strip()[:120],
                              "reply137e": str(t["reply"]).strip()[:120]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            elif str(t["reply"]).strip() != str(b["reply"]).strip():
                reply_moves.append({"session": sid, "n": t["n"],
                                    "text": str(t["text"])[:100]})
    out = {"seconds": round(time.time() - t0, 1),
           "loop137c": dict(counts137c), "loop137e": dict(counts137e),
           "new_wrong_vs_loop137c": new_wrong, "moves": moves,
           "reply_moves": reply_moves}
    (ART / "sessions152-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"G3-sessions: loop137c {out['loop137c']} loop137e "
          f"{out['loop137e']} new_wrong={new_wrong} moves={len(moves)} "
          f"reply_moves={len(reply_moves)} in {out['seconds']}s", flush=True)
    for m in moves + reply_moves:
        print(f"  MOVE {m}", flush=True)
    return 1 if new_wrong or moves or reply_moves else 0


if __name__ == "__main__":
    sys.exit(main())
