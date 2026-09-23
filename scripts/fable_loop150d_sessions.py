#!/usr/bin/env python3
"""Exp 150d G3-sessions driver -- exp-152 phone sessions through loop150d.

Follows the scripts/fable_loop138b_sessions.py PATTERN (sealed sessions +
run_session + judge from scripts/fable_session152_run.py by import, atomic
inbox writes); only the 150d arm runs, compared per-turn against loop138b's
OWN frozen rows (read-only). Bar: 0 new WRONG vs loop138b; every move
predicted in writing before the run (predicted: none).

Outputs into artifacts/fable-hedgecase150d-20260922/.
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

import fable_loop150d_agent as L150d  # noqa: E402 (agent under test)
import fable_session152_run as S152R  # noqa: E402 (sessions+judge, read-only)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-hedgecase150d-20260922"
ART138B = ROOT / "artifacts" / "fable-agent138b-20260922"


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    sessions_out: dict = {}
    for s in S152R.S152.SESSIONS:
        root = ART / "work-sessions-loop150d" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(L150d.DEFAULT_CONFIG150D)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L150d.Loop150dDaemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        judged = []
        for t in turns:
            j = S152R.judge(t)
            judged.append({**t, "verdict": j["verdict"], "why": j["why"]})
        sessions_out[s["id"]] = judged
    (ART / "sessions152-loop150d.json").write_text(
        json.dumps(sessions_out, indent=1, ensure_ascii=False),
        encoding="utf-8")
    base = json.loads((ART138B / "sessions152-loop138b.json").read_text(
        encoding="utf-8"))
    moves, new_wrong = [], 0
    counts150d: Counter = Counter()
    for sid, turns in sessions_out.items():
        for t, b in zip(turns, base.get(sid, [])):
            counts150d[t["verdict"]] += 1
            if t["verdict"] != b["verdict"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": str(t["text"])[:100],
                              "loop138b": b["verdict"],
                              "loop150d": t["verdict"]})
                if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                    new_wrong += 1
    out = {"seconds": round(time.time() - t0, 1),
           "loop150d": dict(counts150d),
           "new_wrong_vs_loop138b": new_wrong, "moves": moves}
    (ART / "sessions152-compare.json").write_text(
        json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print(f"G3-sessions: loop150d {out['loop150d']} new_wrong={new_wrong} "
          f"moves={len(moves)} in {out['seconds']}s", flush=True)
    for m in moves:
        print(f"  MOVE {m['session']}#{m['n']} {m['text']!r}: "
              f"{m['loop138b']} -> {m['loop150d']}", flush=True)
    return 1 if (new_wrong or moves) else 0


if __name__ == "__main__":
    sys.exit(main())
