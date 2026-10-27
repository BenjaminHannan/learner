#!/usr/bin/env python3
"""Experiment 146 D3 -- doubt probe runner (sealed case file, fresh daemon
per dialogue, in-process mailbox like the bench harness).

Reads artifacts/fable-doubt146-20260922/doubt146-cases.json (sealed,
sha256 in SEAL.sha256.txt). Each dialogue runs through Loop146Daemon
(agent loop146) or Loop146bDaemon (agent loop146b) via process_file;
restart_after rebuilds the daemon object on the SAME dir (state.json +
notebook + doubts146.json reload = restart persistence). Every step reply
is graded on expect_contains / expect_absent; every dialogue reported,
never averaged.

Registered run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146_probe.py --run
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

import fable_loop146_agent as L146  # noqa: E402 (this experiment)
import fable_loop146b_agent as L146B  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART146 = ROOT / "artifacts" / "fable-doubt146-20260922"
CASES = ART146 / "doubt146-cases.json"


def _drive(daemon, ddir: Path, text: str, n: int) -> str:
    name = f"s{n:03d}.txt"
    (ddir / "inbox" / name).write_text(str(text) + "\n", encoding="utf-8")
    daemon.process_file(ddir / "inbox" / name)
    return (ddir / "outbox" / name).read_text(encoding="utf-8").strip()


def run_dialogue(dlg: dict, workroot: Path) -> dict:
    agent = dlg["agent"]
    if agent == "loop146":
        daemon_cls, cfg = L146.Loop146Daemon, copy.deepcopy(
            L146.DEFAULT_CONFIG146)
    elif agent == "loop146b":
        daemon_cls, cfg = L146B.Loop146bDaemon, copy.deepcopy(
            L146B.DEFAULT_CONFIG146B)
    else:
        raise ValueError(f"unknown agent {agent!r}")
    ddir = workroot / dlg["id"]
    if ddir.exists():
        shutil.rmtree(ddir)
    ddir.mkdir(parents=True)
    daemon = daemon_cls(str(ddir), cfg=dict(cfg))
    steps_out = []
    ok = True
    n = 0
    for i, step in enumerate(dlg["steps"]):
        n += 1
        reply = _drive(daemon, ddir, step["turn"], n)
        fails = []
        for want in step.get("expect_contains", []):
            if want not in reply:
                fails.append(f"missing {want!r}")
        for ban in step.get("expect_absent", []):
            if ban in reply:
                fails.append(f"stale/banned {ban!r} present")
        steps_out.append({"turn": step["turn"], "reply": reply,
                          "pass": not fails, "fails": fails})
        if fails:
            ok = False
        if dlg.get("restart_after") == i:
            daemon = daemon_cls(str(ddir), cfg=dict(cfg))
    doubts_left = 0
    try:
        doubts_left = len(daemon.loop.doubt_store146.doubts)
    except Exception:
        doubts_left = -1
    return {"id": dlg["id"], "agent": agent, "pass": ok,
            "doubts_left": doubts_left, "steps": steps_out}


def cmd_run() -> int:
    data = json.loads(CASES.read_text(encoding="utf-8"))
    workroot = ART146 / "scratch-probe146"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    rows = [run_dialogue(d, workroot) for d in data["dialogues"]]
    seconds = round(time.time() - t0, 1)
    stale = sum(1 for r in rows for s in r["steps"]
                for f in s["fails"] if f.startswith("stale"))
    passed = sum(r["pass"] for r in rows)
    out = {"seconds": seconds, "n": len(rows), "passed": passed,
           "stale_fails": stale, "dialogues": rows}
    (ART146 / "probe146-report.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"probe146: {passed}/{len(rows)} dialogues pass, "
          f"stale_fails={stale} seconds={seconds}")
    for r in rows:
        if not r["pass"]:
            print(f"  FAIL {r['id']}")
            for s in r["steps"]:
                if not s["pass"]:
                    print(f"    turn={s['turn']!r} reply={s['reply']!r} "
                          f"fails={s['fails']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if passed == len(rows) else 1


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 146 D3 probe")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    if args.run:
        return cmd_run()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
