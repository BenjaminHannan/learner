#!/usr/bin/env python3
"""Exp 231b base arm: loop221 + 232c's fix ("221+232c").

loop221 (scripts/fable_loop221_agent.py) = loop138i + TableAsk221Mixin
outermost on the 138i ears. 232c (scripts/claude_loop232c_agent.py) =
loop138i + Verb232Mixin (inside 174/165, outside the 167b screen, i.e. the
Loop232Ears base list) + Loop232AgentLoop's pending-drop parity step, with
the 232c subject rule rebound into 232 at import (install232c()).

This arm is exactly both, and nothing else:
  ears  = TableAsk221Mixin outermost over Loop232Ears (the 138i list with
          Verb232Mixin where 232 puts it)
  loop  = Loop232AgentLoop (232's _act parity step over Loop138iAgentLoop)
  build = build_agent221 (sets table221_path) with those two classes swapped
          in for the call, as loop231 does.
Not included: 236 (first-name resolution), table v1.1, anything else.

The 228 guard: install_srcguard228() runs at import and in the builder, and
SrcGuardMixin228 is first in the daemon bases (as scripts/claude_loop228_agent.py).
New file only; every imported module is read-only.
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

import claude_loop232c_agent as L232C  # noqa: E402 (sealed 232c, read-only)
import fable_fix221_tableask as T221  # noqa: E402 (read-only)
import fable_loop221_agent as L221  # noqa: E402 (sealed 221, read-only)

L232 = L232C.L232
L232C.install232c()


class Loop221x232cEars(T221.TableAsk221Mixin, L232.Loop232Ears):
    """232c's ears (138i list + Verb232Mixin) with 221's table stage outermost."""

    name = "loop221x232c"


class Loop221x232cAgentLoop(L232.Loop232AgentLoop):
    """232's agent loop (pending-drop parity for v232 twins), unchanged."""


DEFAULT_CONFIG221X232C: dict = copy.deepcopy(L221.DEFAULT_CONFIG221)
DEFAULT_CONFIG221X232C["ears"]["stand_in"] = (
    L221.DEFAULT_CONFIG221["ears"]["stand_in"]
    + "; 232c multi-word verb subjects + complete name particles "
      "(Verb232Mixin beside the verb mixins)")
DEFAULT_CONFIG221X232C["daemon"]["module"] = (
    "Loop221x232cDaemon (scripts/claude_loop221x232c_agent.py)")


def _build_swapped221(ears_cls, loop_cls, cfg: dict):
    """build_agent221 with its ears / loop classes swapped for the call."""
    install_srcguard228()
    L232C.install232c()
    orig_ears, orig_loop = L221.Loop221Ears, L221.Loop221AgentLoop
    L221.Loop221Ears, L221.Loop221AgentLoop = ears_cls, loop_cls
    try:
        return L221.build_agent221(cfg)
    finally:
        L221.Loop221Ears, L221.Loop221AgentLoop = orig_ears, orig_loop


def build_agent221x232c(cfg: dict | None = None) -> Loop221x232cAgentLoop:
    loop = _build_swapped221(Loop221x232cEars, Loop221x232cAgentLoop,
                             dict(DEFAULT_CONFIG221X232C, **(cfg or {})))
    loop.notes.append("loop221x232c: loop221 + 232c fix (Verb232Mixin with "
                      "the 232c subject rule + 232 pending-drop parity)")
    return loop


class Loop221x232cDaemon(SrcGuardMixin228, L221.Loop221Daemon):
    """Loop221Daemon shape with the 221+232c agent inside."""

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
        self.loop = build_agent221x232c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = L221.D108.boot_reconcile(self)
        self.settle = L221.D141.SettleGate141(grace_s=grace_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 231b base arm 221+232c")
    ap.add_argument("--config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    cfg = copy.deepcopy(DEFAULT_CONFIG221X232C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop221x232cDaemon(args.dir, cfg=cfg,
                                  idle_seconds=args.idle_seconds).run()
    if args.once:
        if not args.state_dir:
            ap.error("--once needs --state-dir (never the repo notebook)")
        cfg["state_dir"] = args.state_dir
        loop = build_agent221x232c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
