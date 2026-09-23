#!/usr/bin/env python3
"""Exp 231b: loop231 re-built on loop221 + 232c's fix.

loop231b = "221+232c" (scripts/claude_loop221x232c_agent.py) +
Chain231Mixin (scripts/claude_loop231_agent.py, sealed, read-only)
OUTERMOST, exactly as loop231 puts it on loop221:

  ears  = Chain231Mixin > TableAsk221Mixin > Loop232Ears (138i list +
          Verb232Mixin with the 232c subject rule)
  loop  = Loop232AgentLoop (232's pending-drop parity step)
  build = build_agent221 with those classes swapped in (as build_agent231).

Nothing else: no 236 first-name resolution, no table v1.1.
228 guard installed at import and in the builder; SrcGuardMixin228 first in
the daemon bases. New file only.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from claude_fix228_srcguard import (  # noqa: E402 (required 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import claude_loop221x232c_agent as B  # noqa: E402 (the base arm)
import claude_loop231_agent as L231  # noqa: E402 (sealed 231, read-only)

L221 = B.L221


class Loop231bEars(L231.Chain231Mixin, B.Loop221x232cEars):
    name = "loop231b-chain"


class Loop231bAgentLoop(B.Loop221x232cAgentLoop):
    """Unchanged (renamed for logs)."""


DEFAULT_CONFIG231B: dict = copy.deepcopy(B.DEFAULT_CONFIG221X232C)
DEFAULT_CONFIG231B["ears"]["stand_in"] = (
    B.DEFAULT_CONFIG221X232C["ears"]["stand_in"]
    + "; 231 possessive chains in table-question subjects outermost "
      "(read-only, taught facts only)")
DEFAULT_CONFIG231B["daemon"]["module"] = (
    "Loop231bDaemon (scripts/claude_loop231b_agent.py)")


def build_agent231b(cfg: dict | None = None) -> Loop231bAgentLoop:
    loop = B._build_swapped221(Loop231bEars, Loop231bAgentLoop,
                               dict(DEFAULT_CONFIG231B, **(cfg or {})))
    loop.notes.append("loop231b: loop221 + 232c fix + Chain231Mixin "
                      "outermost (chains in table-question subjects)")
    return loop


class Loop231bDaemon(SrcGuardMixin228, L221.Loop221Daemon):
    """Loop221Daemon shape with the 231b agent inside."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = L221.D141.SETTLE_GRACE_S) -> None:
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
        self.pid = _os.getpid()
        self.boot_time = time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent231b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L221.D108.boot_reconcile(self)
        self.settle = L221.D141.SettleGate141(grace_s=grace_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 231b chains on 221+232c")
    ap.add_argument("--config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG231B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop231bDaemon(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds).run()
    if args.once:
        if not args.state_dir:
            ap.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent231b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
