#!/usr/bin/env python3
"""Experiment 113e E1: red-team-124's 62 sealed cases, loop113c vs loop113e.

Reuse of scripts/fable_bench113d_redteam124.py by import with class swap
(as the exp-113e brief allows): the only changes are the after-arm daemon
class (Loop113dDaemon -> Loop113eDaemon via module-attribute swap), the
after-arm config, and the artifact directory. Verdicts still come ONLY from
the runner's check_case with the loop113b expectations. The 113d report
filename is renamed to the 113e prefix after the run (own artifact dir).

Run (Mac CPU, offline; only AFTER PASSMARKS.md is sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_bench113e_redteam124.py --run
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_bench113d_redteam124 as D113D  # noqa: E402 (runner, read-only)
import fable_loop113e_agent as L113E  # noqa: E402 (this experiment's agent)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113e-20260922"

# The class swap: after-arm now builds the loop113e daemon. Note the 113d
# make_daemon looks up Loop113dDaemon on the (swapped) agent module, so the
# factory itself is overridden here with the 113d body verbatim except the
# after-arm class/config (before-arm path untouched).
import fable_loop113c_agent as L113C  # noqa: E402 (before arm, read-only)


def make_daemon(arm: str, workdir: Path):
    if arm == "loop113c":
        cfg = copy.deepcopy(L113C.DEFAULT_CONFIG113C)
        cfg["state_dir"] = str(workdir)
        cfg["sleep_threshold"] = 10 ** 9
        return L113C.Loop113cDaemon(str(workdir), cfg=cfg, idle_seconds=30.0)
    cfg = copy.deepcopy(L113E.DEFAULT_CONFIG113E)
    cfg["state_dir"] = str(workdir)
    cfg["sleep_threshold"] = 10 ** 9
    return L113E.Loop113eDaemon(str(workdir), cfg=cfg, idle_seconds=30.0)


D113D.L113D = L113E
D113D.CFG113D = copy.deepcopy(L113E.DEFAULT_CONFIG113E)
D113D.make_daemon = make_daemon
D113D.ART = ART


def cmd_run(_args) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    ret = D113D.cmd_run(_args)
    src = ART / "fable_bench113d_redteam124_report.json"
    dst = ART / "fable_bench113e_redteam124_report.json"
    if src.exists():
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        print(f"renamed {src.name} -> {dst.name} (after-arm is loop113e)")
    return ret


def main() -> int:
    ap = argparse.ArgumentParser(description="Exp 113e E1 redteam124")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
