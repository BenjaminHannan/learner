#!/usr/bin/env python3
"""Exp 138b B4b driver -- exp-152 phone sessions through loop138b + loop138.

Reuses scripts/fable_session152_run.py BY IMPORT (sealed sessions,
run_session mailbox driver, judge); only the target daemon is swapped
(the brief: "with the target swapped"). Compares per-turn verdicts 138b
vs 138. Bar: 0 new WRONG vs loop138; every correct/abstain move listed.
Inbox writes use the atomic-write client rule (tmp + rename). Outputs
into artifacts/fable-agent138b-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138b_sessions.py
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

import fable_loop138_agent as L138  # noqa: E402 (frozen base, read-only)
import fable_loop138b_agent as L138b  # noqa: E402 (agent under test)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138b-20260922"


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
    out138 = run_target("loop138", L138.Loop138Daemon,
                        L138.DEFAULT_CONFIG138)
    out138b = run_target("loop138b", L138b.Loop138bDaemon,
                         L138b.DEFAULT_CONFIG138B)
    moves, new_wrong = [], 0
    counts138: Counter = Counter()
    counts138b: Counter = Counter()
    for sid, turns in out138b.items():
        for t, b in zip(turns, out138.get(sid, [])):
            counts138[b["verdict"]] += 1
            counts138b[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138": b["verdict"], "loop138b": t["verdict"],
                              "reply138": str(b["reply"]).strip()[:120],
                              "reply138b": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
    out = {"seconds": round(time.time() - t0, 1),
           "loop138": dict(counts138), "loop138b": dict(counts138b),
           "new_wrong_vs_loop138": new_wrong, "moves": moves}
    (ART / "sessions152-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"B4b sessions: loop138 {out['loop138']} loop138b "
          f"{out['loop138b']} new_wrong={new_wrong} moves={len(moves)} "
          f"in {out['seconds']}s", flush=True)
    for m in moves:
        print(f"  MOVE {m['session']}#{m['n']} {m['text']!r}: "
              f"{m['loop138']} -> {m['loop138b']}", flush=True)
    return 1 if new_wrong else 0


if __name__ == "__main__":
    sys.exit(main())
