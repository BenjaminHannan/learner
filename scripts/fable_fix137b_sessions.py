#!/usr/bin/env python3
"""Experiment 137b G3-sessions driver -- exp-152 phone sessions, loop137b.

Reuses scripts/fable_session152_run.py BY IMPORT (sealed sessions,
run_session mailbox driver, judge) with the target daemon swapped to
loop137b. Compares per-turn verdicts AND replies against loop138b's own
frozen rows (artifacts/fable-agent138b-20260922/sessions152-loop138b.json).
Inbox writes use the atomic-write client rule (tmp + rename). Bar: 0 new
WRONG vs loop138b; every move listed. Outputs into
artifacts/fable-discourse137b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix137b_sessions.py
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

import fable_loop137b_agent as L137B  # noqa: E402 (agent under test)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-discourse137b-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


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
    out137b = run_target("loop137b", L137B.Loop137bDaemon,
                         L137B.DEFAULT_CONFIG137B)
    base = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    moves, reply_moves, new_wrong = [], [], 0
    counts138b: Counter = Counter()
    counts137b: Counter = Counter()
    for sid, turns in out137b.items():
        for t, b in zip(turns, base.get(sid, [])):
            counts138b[b["verdict"]] += 1
            counts137b[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138b": b["verdict"],
                              "loop137b": t["verdict"],
                              "reply138b": str(b["reply"]).strip()[:120],
                              "reply137b": str(t["reply"]).strip()[:120]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            elif str(t["reply"]).strip() != str(b["reply"]).strip():
                reply_moves.append({"session": sid, "n": t["n"],
                                    "text": str(t["text"])[:100]})
    out = {"seconds": round(time.time() - t0, 1),
           "loop138b": dict(counts138b), "loop137b": dict(counts137b),
           "new_wrong_vs_loop138b": new_wrong, "moves": moves,
           "reply_moves": reply_moves}
    (ART / "sessions152-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"G3-sessions: loop138b {out['loop138b']} loop137b "
          f"{out['loop137b']} new_wrong={new_wrong} moves={len(moves)} "
          f"reply_moves={len(reply_moves)} in {out['seconds']}s", flush=True)
    for m in moves + reply_moves:
        print(f"  MOVE {m}", flush=True)
    return 1 if new_wrong or moves or reply_moves else 0


if __name__ == "__main__":
    sys.exit(main())
