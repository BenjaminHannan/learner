#!/usr/bin/env python3
"""Experiment 156b -- G3 session replay through loop156b by import (Muse).

Imports scripts/fable_session152_run.py (run_session/judge, read-only)
with the target swapped to loop156b (scripts/fable_loop156b_agent.py +
artifacts/fable-smalltalk156b-20260922/loop156b-config.json). Runs the 6
sealed exp-152 sessions (read from
artifacts/fable-session152-20260922/sessions152.json, read-only) through
fresh daemons, one file per turn, exactly like the 152 harness. Outputs
go into artifacts/fable-smalltalk156b-20260922/ only.

Per-turn replies are diffed against the sealed loop150-equivalent T-T
run (artifacts/fable-session152-20260922/turns152-T-T-*.json, read-only;
T-T is loop139b, whose non-small-talk behaviour loop150/loop156b inherit
unchanged outside their guards -- and the guards provably do not fire
on session non-small-talk turns, see PASSMARKS.md pre-seal scans).
Predicted: exactly the 23 sealed small-talk turns change (to their 156b
class replies -- laugh rows now get the laugh reply, not "Got it!"),
every other turn byte-identical, 0 new WRONG, 0 new writes. Any
unpredicted move fails G3 honestly.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_fix156b_session.py
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
ART156b = ROOT / "artifacts" / "fable-smalltalk156b-20260922"
ART152 = ROOT / "artifacts" / "fable-session152-20260922"


def load_mod(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    t0 = time.time()
    ART156b.mkdir(parents=True, exist_ok=True)
    R152 = load_mod(str(SCRIPTS / "fable_session152_run.py"), "s156b_152run")
    import fable_loop156b_agent as L156b  # noqa: E402 (this experiment)

    sessions = json.loads((ART152 / "sessions152.json").read_text(
        encoding="utf-8"))
    cfg = json.loads((ART156b / "loop156b-config.json").read_text(
        encoding="utf-8"))

    summary: dict = {}
    diffs: dict = {}
    for s in sessions:
        root = ART156b / "work" / "loop156b" / s["id"]
        if root.exists():
            import shutil
            shutil.rmtree(root)
        root.mkdir(parents=True)
        cfg_run = copy.deepcopy(cfg)
        cfg_run["state_dir"] = str(root)
        cfg_run["sleep_threshold"] = 100000
        daemon = L156b.Loop156bDaemon(root, cfg=cfg_run, idle_seconds=3600.0)
        turns = R152.run_session(daemon, root, s)
        for t in turns:
            t.update(R152.judge(t))
        (ART156b / f"turns156b-loop156b-{s['id']}.json").write_text(
            json.dumps(turns, indent=1, ensure_ascii=False), encoding="utf-8")
        counts: dict[str, int] = {}
        for t in turns:
            counts[t["verdict"]] = counts.get(t["verdict"], 0) + 1
        summary[s["id"]] = counts
        print(f"loop156b {s['id']}: {counts}", flush=True)

        sealed = json.loads((ART152 / f"turns152-T-T-{s['id']}.json")
                            .read_text(encoding="utf-8"))
        base = {t["n"]: t for t in sealed}
        moved = [t["n"] for t in turns
                 if base.get(t["n"], {}).get("reply") != t["reply"]]
        write_moves = [t["n"] for t in turns
                       if base.get(t["n"], {}).get("fact_writes")
                       != t["fact_writes"]]
        new_wrong = [t["n"] for t in turns
                     if t["verdict"] == "WRONG"
                     and base.get(t["n"], {}).get("verdict") != "WRONG"]
        diffs[s["id"]] = {"reply_moves": moved, "write_moves": write_moves,
                          "new_wrong": new_wrong}
        print(f"  vs T-T: reply_moves={moved} write_moves={write_moves} "
              f"new_wrong={new_wrong}", flush=True)
    total = round(time.time() - t0, 1)
    (ART156b / "run156b-summary.json").write_text(
        json.dumps({"summary": summary, "diff_vs_TT": diffs,
                    "seconds": total}, indent=1), encoding="utf-8")
    print(f"TOTAL {total} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
