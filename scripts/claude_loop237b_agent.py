#!/usr/bin/env python3
"""Exp 237b -- relation table v1.2 on loop237 (questions only).

loop237b = loop237 with ONE change: the question stage reads
artifacts/claude-table237b-20260922/relation_table_v1_2.json (built by
scripts/claude_table237b_build.py from a category-by-category enumeration
of everyday relations) instead of v1.1. The table path is forced in code,
so a config cannot point this agent back at v1.1.

No reader code changes: the 237 reader (TableAsk237Mixin), the 221 answer
rules, the 138i stack and the writes are all used as they are.
The 228 guard is installed at import and SrcGuardMixin228 comes first in
the daemon bases (copied shape of Loop237Daemon). No existing file is edited.
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

from claude_fix228_srcguard import (  # noqa: E402 (REQUIRED 228 guard)
    SrcGuardMixin228, install_srcguard228)

install_srcguard228()

import fable_daemon108_run as D108  # noqa: E402 (read-only)
import fable_daemon141_settle as D141  # noqa: E402 (read-only)
import fable_loop90_agent as L90  # noqa: E402 (read-only)
import fable_loop221_agent as L221  # noqa: E402 (read-only)
import claude_loop237_agent as L237  # noqa: E402 (base, read-only)

ROOT = SCRIPTS.parent
TABLE_PATH237B = (ROOT / "artifacts" / "claude-table237b-20260922"
                  / "relation_table_v1_2.json")

DEFAULT_CONFIG237B: dict = copy.deepcopy(L237.DEFAULT_CONFIG237)
DEFAULT_CONFIG237B["ears"]["stand_in"] = (
    L237.DEFAULT_CONFIG237["ears"]["stand_in"].replace(
        "relation table v1.1 (237)", "relation table v1.2 (237b)"))
DEFAULT_CONFIG237B["daemon"]["module"] = (
    "Loop237bDaemon (scripts/claude_loop237b_agent.py)")
DEFAULT_CONFIG237B["table221_path"] = str(TABLE_PATH237B)


def build_agent237b(cfg: dict | None = None):
    """build_agent237 with the table path forced to v1.2."""
    install_srcguard228()
    cfg = dict(DEFAULT_CONFIG237B, **(cfg or {}))
    cfg["table221_path"] = str(TABLE_PATH237B)
    loop = L237.build_agent237(cfg)
    loop.notes.append("loop237b: loop237 with relation table v1.2 "
                      "(questions only; writes untouched; 228 guard)")
    return loop


class Loop237bDaemon(SrcGuardMixin228, L221.Loop221Daemon):
    """Loop237Daemon shape with the 237b agent inside; 228 guard first."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None,
                 grace_s: float = D141.SETTLE_GRACE_S) -> None:
        install_srcguard228()
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
        self.loop = build_agent237b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)
        self.reconcile_report = D108.boot_reconcile(self)
        self.settle = D141.SettleGate141(grace_s=grace_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exp 237b table v1.2")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG237B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print("Wrote %s" % args.write_config)
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG237B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.dir:
        return Loop237bDaemon(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds).run()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
