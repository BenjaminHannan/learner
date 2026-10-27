#!/usr/bin/env python3
"""Experiment 139b -- loop139b = loop129b + the exp-139b value-guard mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE vs exp 139 lives
in scripts/fable_fix139b_valueguard.py (ValueGuard139BMixin: rule + open
UN table instead of the gold-sourced KNOWN_AND_NAMES); this file stacks it
onto loop129b at both levels (ears hear + loop _act just before the write).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop139b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-fix139b-20260922/loop139b-config.json
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

import fable_fix139b_valueguard as V139b  # noqa: E402 (this experiment's mixin)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


class Loop139bEars(V139b.ValueGuard139BMixin, L129b.Loop129bEars):
    """Loop129bEars + 139b value-span guard on outgoing teach/correct."""

    name = "loop139b-valueguard"


class Loop139bAgentLoop(V139b.ValueGuard139BMixin, L129b.Loop129bAgentLoop):
    """Loop129bAgentLoop + 139b value-span guard just before the write."""


DEFAULT_CONFIG139B: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG139B["ears"]["stand_in"] = (
    "Loop139bEars (loop129b + exp-139b value-span validator: negation/hedge, "
    "bare and/or by of-phrase rule + open UN table, sentence boundary) "
    "over loop129b chain")
DEFAULT_CONFIG139B["daemon"]["module"] = "Loop139bDaemon (this file)"


def build_agent139b(cfg: dict | None = None) -> Loop139bAgentLoop:
    """Build the loop129b agent shape with the 139b guard mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG139B, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop139bEars
    loop.ears.name = Loop139bEars.name
    loop.__class__ = Loop139bAgentLoop
    return loop


class Loop139bDaemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop139b agent inside (mailbox same)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        self.cfg = dict(cfg or {})
        if sleep_threshold is not None:
            self.cfg["sleep_threshold"] = sleep_threshold
        self.root = Path(root)
        self.idle_seconds = float(idle_seconds)
        self.inbox = self.root / "inbox"
        self.outbox = self.root / "outbox"
        self.done = self.root / "done"
        for sub in (self.inbox, self.outbox, self.done):
            sub.mkdir(parents=True, exist_ok=True)
        self.stop_file = self.root / "STOP"
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent139b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon139b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop139bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 139b and-name guard loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG139B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG139B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG139B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon139b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent139b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
