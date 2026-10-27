#!/usr/bin/env python3
"""Exp 138d M4-sessions driver -- exp-152 phone sessions through loop138d.

Reuses scripts/fable_session152_run.py BY IMPORT (sealed sessions,
run_session mailbox driver, judge); runs ONLY the 138d arm and compares
per-turn verdicts against the SEALED loop138b rows (read-only). Bar: 0 new
WRONG vs loop138b, 0 new writes; every move listed. Inbox writes use the
atomic-write client rule (tmp + rename). Outputs into
artifacts/fable-agent138d-20260922/.

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop138d_sessions.py
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

import fable_loop138d_agent as L138d  # noqa: E402 (agent under test)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-agent138d-20260922"
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
    out138d = run_target("loop138d", L138d.Loop138dDaemon,
                         L138d.DEFAULT_CONFIG138D)
    out138b = json.loads(
        (ART138B / "sessions152-loop138b.json").read_text(encoding="utf-8"))
    moves, new_wrong, new_writes = [], 0, []
    counts138b: Counter = Counter()
    counts138d: Counter = Counter()
    for sid, turns in out138d.items():
        for t, b in zip(turns, out138b.get(sid, [])):
            counts138b[b["verdict"]] += 1
            counts138d[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138b": b["verdict"],
                              "loop138d": t["verdict"],
                              "reply138b": str(b["reply"]).strip()[:120],
                              "reply138d": str(t["reply"]).strip()[:120],
                              "why": t["why"][:160]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
            bw = (b.get("fact_writes") or b.get("writes") or [])
            tw = (t.get("fact_writes") or t.get("writes") or [])
            if tw and tw != bw:
                new_writes.append({"session": sid, "n": t["n"],
                                   "loop138b_writes": bw,
                                   "loop138d_writes": tw})
    out = {"seconds": round(time.time() - t0, 1),
           "loop138b": dict(counts138b), "loop138d": dict(counts138d),
           "new_wrong_vs_loop138b": new_wrong, "moves": moves,
           "new_writes": new_writes}
    (ART / "sessions152-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    print(f"M4 sessions: loop138b {out['loop138b']} loop138d "
          f"{out['loop138d']} new_wrong={new_wrong} "
          f"new_writes={len(new_writes)} moves={len(moves)} "
          f"in {out['seconds']}s", flush=True)
    for m in moves:
        print(f"  MOVE {m['session']}#{m['n']} {m['text']!r}: "
              f"{m['loop138b']} -> {m['loop138d']}", flush=True)
    return 1 if (new_wrong or new_writes) else 0


if __name__ == "__main__":
    sys.exit(main())
