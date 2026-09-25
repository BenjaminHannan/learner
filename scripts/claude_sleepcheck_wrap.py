#!/usr/bin/env python3
"""Sleep check for rented runs (month-end line, 2026-09-25). New file only; no agent or runner code changes.

Why: sleep's learning step needs artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt, which is not in git.
When it is missing, the sleeper skips learning ("no base checkpoint") and still reports accepted: true, so the
registered 336 run most likely had no sleep learning (VERIFY-336.md addendum; slp-360 RESULTS.md).

What: before the next script starts, wraps Sleep145Sleeper.sleep (the sleeper of the 292t loop that 330c is built
on) so that every sleep appends one JSON line to $SLEEPCHECK_LOG: the state dir, accepted, recipe.attempted and
recipe.reason. With SLEEPCHECK_STOP=1 the run stops at the first sleep whose checkpoint file is missing or whose recipe says
"no base checkpoint".
The sleep itself and its outcome are unchanged.

  SLEEPCHECK_LOG=run/sleep_P.jsonl SLEEPCHECK_STOP=1 python -B scripts/claude_sleepcheck_wrap.py \
      scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --arm ... [runner args]
"""
from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fable_sleep145_agent as S145   # noqa: E402

LOG = os.environ.get("SLEEPCHECK_LOG", "")
STOP = os.environ.get("SLEEPCHECK_STOP", "") == "1"
_inner = S145.Sleep145Sleeper.sleep


def _sleep_checked(self, *a, **kw):
    out = _inner(self, *a, **kw)
    outcome = out if isinstance(out, dict) else dict(getattr(self, "last_outcome", {}) or {})
    recipe = outcome.get("recipe", {}) if isinstance(outcome.get("recipe", {}), dict) else {}
    row = {"state_dir": str(getattr(self, "state_dir", "")), "accepted": outcome.get("accepted"),
           "attempted": recipe.get("attempted"), "reason": recipe.get("reason"),
           "checkpoint_exists": Path(str(getattr(self, "checkpoint", ""))).exists()}
    if LOG:
        Path(LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    if STOP and ("no base checkpoint" in str(recipe.get("reason", "")) or not row["checkpoint_exists"]):
        raise SystemExit("SLEEP-NOT-LEARNING: sleep's base checkpoint is missing; nothing was scored")
    return out


S145.Sleep145Sleeper.sleep = _sleep_checked


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: claude_sleepcheck_wrap.py <script.py> [args]")
    target = sys.argv[1]
    sys.argv = [target] + sys.argv[2:]
    print(f"sleepcheck: logging every sleep to {LOG or '(no log)'}; stop on missing checkpoint = {STOP}", flush=True)
    runpy.run_path(target, run_name="__main__")


if __name__ == "__main__":
    main()
