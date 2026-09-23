#!/usr/bin/env python3
"""Experiment 159 -- G3 phone-session re-run through loop159 (Muse).

Replays the 6 sealed exp-152 sessions (scripts/fable_session152_sessions.py
SESSIONS, read-only; artifacts/fable-session152-20260922/sessions152.json is
never rewritten) through Loop159Daemon, one fresh daemon dir per session
(6 daemons), in-process `process_file` exactly like
scripts/fable_session152_run.py run_session/judge (imported, not copied).
Only the target is swapped: loop159 for T-T.

Every reply is diffed against the sealed T-T turns
(artifacts/fable-session152-20260922/turns152-T-T-<sid>.json, read-only).
Predicted moves: exactly 4 replies in S4-pets-identity (turns 7, 20, 26,
27 -- the session's only BROKEN_CHAIN turns); everything else byte-identical,
0 new WRONG, 0 new writes except predicted (asks never write).

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix159_session.py
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

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-hop159-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"

import fable_loop159_agent as L159  # noqa: E402 (this experiment)
import fable_session152_run as S152R  # noqa: E402 (harness, read-only)
import fable_session152_sessions as S152  # noqa: E402 (sessions, read-only)


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    cfg0 = copy.deepcopy(L159.DEFAULT_CONFIG159)
    summary: dict = {}
    all_diffs: dict = {}
    new_wrong = 0
    new_writes = 0
    for s in S152.SESSIONS:
        root = ART / "work" / "LOOP159" / s["id"]
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg0)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L159.Loop159Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152R.run_session(daemon, root, s)
        for t in turns:
            t.update(S152R.judge(t))
        (ART / f"turns159-LOOP159-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        sealed = json.loads(
            (ART152 / f"turns152-T-T-{s['id']}.json").read_text(
                encoding="utf-8"))
        base = {t["n"]: t for t in sealed}
        diffs = [t["n"] for t in turns
                 if base.get(t["n"], {}).get("reply") != t["reply"]]
        status_diffs = [t["n"] for t in turns
                        if base.get(t["n"], {}).get("statuses")
                        != t["statuses"]]
        write_diffs = [t["n"] for t in turns
                       if base.get(t["n"], {}).get("fact_writes")
                       != t["fact_writes"]]
        for t in turns:
            if (t["verdict"] == "WRONG"
                    and base.get(t["n"], {}).get("verdict") != "WRONG"):
                new_wrong += 1
        new_writes += len(write_diffs)
        all_diffs[s["id"]] = {"reply_diffs": diffs,
                              "status_diffs": status_diffs,
                              "write_diffs": write_diffs}
        counts: dict[str, int] = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        summary[s["id"]] = counts
        print(f"LOOP159 {s['id']}: {counts} reply_diffs={diffs} "
              f"status_diffs={status_diffs} write_diffs={write_diffs}",
              flush=True)
    total = round(time.time() - t0, 1)
    (ART / "run159-summary.json").write_text(
        json.dumps({"summary": summary, "diffs_vs_TT": all_diffs,
                    "new_wrong_vs_TT": new_wrong,
                    "write_diffs_vs_TT": new_writes,
                    "seconds": total}, indent=1), encoding="utf-8")
    print(f"TOTAL {total} s new_wrong={new_wrong} write_diffs={new_writes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
