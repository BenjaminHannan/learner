#!/usr/bin/env python3
"""Experiment 156c -- loop156c = loop138h + wider no-write small-talk.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix156c_smalltalk.py (Smalltalk156cMixin: fixed class
replies for trailing-word greetings, the how-are-you family,
weather/idle chat, first-person feelings statements, and extra goodbyes
-- only when the loop138h chain returns exactly the generic fallthrough
and the whole normalised message matches a closed anchored phrase).
This file stacks it onto loop138h as the outermost ears layer
(loop138h imported read-only).

Behaviour on every non-small-talk input is loop138h's by construction
(the mixin returns super().hear() untouched unless both guards pass),
and inputs loop138h already answers (156b classes inside 138f, me/name/
verb stages, the 168 feelings path) never reach the new matcher.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop156c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-smalltalk156c-20260922/loop156c-config.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_fix156c_smalltalk as S156c  # noqa: E402 (this experiment)
import fable_loop138h_agent as L138H  # noqa: E402 (wrapped base, read-only)


class Loop156cEars(S156c.Smalltalk156cMixin, L138H.Loop138hEars):
    """Loop138hEars + 156c wider small-talk classes on the fallthrough."""

    name = "loop156c-smalltalk-wide"


class Loop156cAgentLoop(S156c.Smalltalk156cMixin, L138H.Loop138hAgentLoop):
    """Loop138hAgentLoop (mixin is ears-active; clarify acts never write)."""


DEFAULT_CONFIG156c: dict = copy.deepcopy(L138H.DEFAULT_CONFIG138H)
DEFAULT_CONFIG156c["ears"]["stand_in"] = (
    "Loop156cEars (loop138h stack + exp-156c wider no-write small-talk "
    "classes: fixed class replies on the generic fallthrough when the "
    "whole normalised message matches a closed anchored phrase -- "
    "trailing-word greetings, how-are-you family, weather/idle chat, "
    "first-person feelings, extra goodbyes)")
DEFAULT_CONFIG156c["daemon"]["module"] = "Loop156cDaemon (this file)"


def build_agent156c(cfg: dict | None = None) -> Loop156cAgentLoop:
    """Build the loop138h agent shape with the 156c mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG156c, **(cfg or {}))
    loop = L138H.build_agent138h(cfg)
    loop.ears.__class__ = Loop156cEars
    loop.ears.name = Loop156cEars.name
    loop.__class__ = Loop156cAgentLoop
    return loop


class Loop156cDaemon(L138H.Loop138hDaemon):
    """Loop138hDaemon shape with the loop156c agent inside (mailbox same)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s=None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.idle_seconds = float(idle_seconds)
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent156c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        import fable_daemon108_run as D108  # noqa: E402 (read-only)
        import fable_daemon141_settle as D141  # noqa: E402 (read-only)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(
            grace_s=(float(grace_s) if grace_s is not None
                     else D141.SETTLE_GRACE_S))


def run_daemon156c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop156cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 156c small-talk loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop138h)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG156c to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG156c)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG156c)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon156c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent156c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
