#!/usr/bin/env python3
"""Experiment 158 -- G3/Q2 session re-run through loop158 by import (Muse).

Imports scripts/fable_session152_run.py (run_session, judge, CLARIFY_BITS)
read-only and swaps ONLY the target to loop158
(scripts/fable_loop158_agent.py:Loop158Daemon +
artifacts/fable-qform158-20260922/loop158-config.json). Sessions come from
the sealed artifacts/fable-session152-20260922/sessions152.json dump
(read-only). Outputs go into artifacts/fable-qform158-20260922/ only.

Per-turn replies are diffed against the sealed T-T run
(artifacts/fable-session152-20260922/turns152-T-T-*.json, read-only).
Predicted moves (see PASSMARKS.md): exactly S5-robustness n5/n6/n9, each
UNHELPFUL -> OK with the canonical answer and 0 writes; every other turn
byte-identical; 0 new WRONG; 0 new writes.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix158_session.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT = SCRIPTS.parent
ART158 = ROOT / "artifacts" / "fable-qform158-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"


def load_mod(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    t0 = time.time()
    ART158.mkdir(parents=True, exist_ok=True)
    S152 = load_mod(str(SCRIPTS / "fable_session152_run.py"), "s152_runner")
    L158 = load_mod(str(SCRIPTS / "fable_loop158_agent.py"), "s158_loop")
    cfg158 = json.loads((ART158 / "loop158-config.json").read_text(
        encoding="utf-8"))
    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    summary: dict = {}
    all_turns: dict = {}
    for s in sessions:
        root = ART158 / "work" / "loop158" / s["id"]
        if root.exists():
            import shutil
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg = copy.deepcopy(cfg158)
        cfg["state_dir"] = str(root)
        cfg["sleep_threshold"] = 100000
        daemon = L158.Loop158Daemon(root, cfg=cfg, idle_seconds=3600.0)
        turns = S152.run_session(daemon, root, s)
        for t in turns:
            t.update(S152.judge(t))
        (ART158 / f"turns158-loop158-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        all_turns[s["id"]] = turns
        counts: dict[str, int] = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        summary[s["id"]] = counts
        print(f"loop158 {s['id']}: {counts}", flush=True)
    # Diff vs sealed T-T replies.
    moves, new_wrong, new_writes = [], [], []
    for s in sessions:
        sid = s["id"]
        sealed = json.loads(
            (ART152 / f"turns152-T-T-{sid}.json").read_text(encoding="utf-8"))
        base = {t["n"]: t for t in sealed}
        for t in all_turns[sid]:
            b = base[t["n"]]
            if b["reply"] != t["reply"]:
                moves.append({"session": sid, "n": t["n"],
                              "text": t["text"],
                              "base_verdict": b["verdict"],
                              "new_verdict": t["verdict"],
                              "base_reply": b["reply"][:120],
                              "new_reply": t["reply"][:120]})
            if t["verdict"] == "WRONG" and b["verdict"] != "WRONG":
                new_wrong.append({"session": sid, "n": t["n"]})
            if t["fact_writes"] > b["fact_writes"]:
                new_writes.append({"session": sid, "n": t["n"],
                                   "base": b["fact_writes"],
                                   "new": t["fact_writes"]})
    total = round(time.time() - t0, 1)
    (ART158 / "run158-session-summary.json").write_text(
        json.dumps({"summary": summary, "seconds": total,
                    "reply_moves_vs_TT": moves,
                    "new_wrong": new_wrong,
                    "new_writes": new_writes}, indent=1), encoding="utf-8")
    print(f"MOVES vs T-T: {len(moves)}")
    for m in moves:
        print(f"  {m['session']} n={m['n']} {m['text']!r}: "
              f"{m['base_verdict']} -> {m['new_verdict']}", flush=True)
    print(f"new_wrong={new_wrong} new_writes={new_writes} TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
