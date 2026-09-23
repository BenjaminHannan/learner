#!/usr/bin/env python3
"""Experiment 146b probes -- H1 (146 D3 re-run on 146c) and H2 (new
hearsay-exemption probe), fresh daemon per dialogue, in-process mailbox
like the 146 harness.

H1 reads the SEALED 146 case file
(artifacts/fable-doubt146-20260922/doubt146-cases.json, read-only) and
runs every dialogue on loop146c (agent field overridden).

H2 reads the SEALED new file
(artifacts/fable-doubt146b-20260922/doubt146b-cases.json): after a taught
fact, a hearsay/quoted contradiction leaves the standing answer in place
(0 doubts); first-person refused corrections doubt + abstain; mixed
orders. Optional "expect_doubts" asserts the doubts left standing;
optional "restart_after" rebuilds the daemon on the same dir.

--control146 re-runs the H2 hearsay-pure dialogues (marked
"control146": true) on the OLD loop146 to show the test is non-vacuous
(they abstain there). The old loop is not a registered arm.

Registered runs (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146b_probe.py --run-h1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_doubt146b_probe.py --run-h2
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

import fable_loop146_agent as L146  # noqa: E402 (old-loop control, read-only)
import fable_loop146c_agent as L146C  # noqa: E402 (this experiment)
import fable_loop146d_agent as L146D  # noqa: E402 (this experiment)

ROOT = SCRIPTS.parent
ART146 = ROOT / "artifacts" / "fable-doubt146-20260922"
ART146B = ROOT / "artifacts" / "fable-doubt146b-20260922"
CASES146 = ART146 / "doubt146-cases.json"
CASES146B = ART146B / "doubt146b-cases.json"


def _daemon_for(agent: str):
    if agent == "loop146c":
        return L146C.Loop146cDaemon, copy.deepcopy(
            L146C.DEFAULT_CONFIG146C)
    if agent == "loop146d":
        return L146D.Loop146dDaemon, copy.deepcopy(
            L146D.DEFAULT_CONFIG146D)
    if agent == "loop146":
        return L146.Loop146Daemon, copy.deepcopy(
            L146.DEFAULT_CONFIG146)
    raise ValueError(f"unknown agent {agent!r}")


def _drive(daemon, ddir: Path, text: str, n: int) -> str:
    name = f"s{n:03d}.txt"
    (ddir / "inbox" / name).write_text(str(text) + "\n", encoding="utf-8")
    daemon.process_file(ddir / "inbox" / name)
    return (ddir / "outbox" / name).read_text(encoding="utf-8").strip()


def run_dialogue(dlg: dict, workroot: Path,
                 force_agent: str | None = None) -> dict:
    agent = force_agent or dlg["agent"]
    daemon_cls, cfg = _daemon_for(agent)
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
    try:
        doubts_left = len(daemon.loop.doubt_store146.doubts)
    except Exception:
        doubts_left = -1
    if "expect_doubts" in dlg and doubts_left != dlg["expect_doubts"]:
        ok = False
    return {"id": dlg["id"], "agent": agent, "pass": ok,
            "doubts_left": doubts_left,
            "expect_doubts": dlg.get("expect_doubts"),
            "steps": steps_out}


def _run(dialogues: list[dict], outname: str, force_agent: str | None,
         control: bool = False) -> int:
    workroot = ART146B / f"scratch-probe146b-{outname}"
    if workroot.exists():
        shutil.rmtree(workroot)
    workroot.mkdir(parents=True)
    t0 = time.time()
    rows = [run_dialogue(d, workroot, force_agent) for d in dialogues]
    seconds = round(time.time() - t0, 1)
    stale = sum(1 for r in rows for s in r["steps"]
                for f in s["fails"] if f.startswith("stale"))
    passed = sum(r["pass"] for r in rows)
    out = {"seconds": seconds, "n": len(rows), "passed": passed,
           "stale_fails": stale, "dialogues": rows}
    (ART146B / f"probe146b-{outname}-report.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(f"probe146b-{outname}: {passed}/{len(rows)} dialogues pass, "
          f"stale_fails={stale} seconds={seconds}")
    for r in rows:
        if not r["pass"]:
            print(f"  FAIL {r['id']} doubts_left={r['doubts_left']}")
            for s in r["steps"]:
                if not s["pass"]:
                    print(f"    turn={s['turn']!r} reply={s['reply']!r} "
                          f"fails={s['fails']}")
    shutil.rmtree(workroot, ignore_errors=True)
    return 0 if passed == len(rows) else 1


def cmd_h1() -> int:
    data = json.loads(CASES146.read_text(encoding="utf-8"))
    return _run(data["dialogues"], "h1", force_agent="loop146c")


def cmd_h2(control: bool = False) -> int:
    data = json.loads(CASES146B.read_text(encoding="utf-8"))
    if control:
        dialogues = [d for d in data["dialogues"]
                     if d.get("control146")]
        return _run(dialogues, "h2-control146", force_agent="loop146",
                    control=True)
    return _run(data["dialogues"], "h2", force_agent=None)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Exp 146b H1/H2 probes")
    ap.add_argument("--run-h1", action="store_true")
    ap.add_argument("--run-h2", action="store_true")
    ap.add_argument("--control146", action="store_true",
                    help="with --run-h2: old-loop146 control on "
                    "control146-marked dialogues")
    args = ap.parse_args(argv)
    if args.run_h1:
        return cmd_h1()
    if args.run_h2:
        return cmd_h2(control=args.control146)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
