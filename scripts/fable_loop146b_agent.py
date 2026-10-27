#!/usr/bin/env python3
"""Experiment 146b -- the exp-146 doubt mixin on top of loop139 (ONE CHANGE).

Thin wrapper only (no existing file edited): loop146b = loop139 +
Doubt146Mixin, so refusals that are COMMON on loop139 (the exp-139
value-span guard) become doubts instead of stale confident answers. The
doubt module is scripts/fable_doubt146_store.py (shared with loop146);
the base is scripts/fable_loop139_agent.py (read-only here).

Stacking order (outermost first): Doubt146Mixin, ValueGuard139Mixin,
Loop129bEars/Loop129bAgentLoop. The doubt hear() pre-parses with the
existing parsers, sees the guard's clarify, and records (subject,
relation); the doubt _act() sees guard-level clarify kinds too. A later
successful teach clears.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop146b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-doubt146-20260922/loop146b-config.json
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

import fable_doubt146_store as D146  # noqa: E402 (this experiment's mixin)
import fable_loop139_agent as L139  # noqa: E402 (wrapped base, read-only)


class Loop146bEars(D146.Doubt146Mixin, L139.Loop139Ears):
    """Loop139Ears + refused-correction doubt (record + ask screening)."""

    name = "loop146b-doubt-on139"


class Loop146bAgentLoop(D146.Doubt146Mixin, L139.Loop139AgentLoop):
    """Loop139AgentLoop + doubt (act-level record/clear, ask backup)."""


DEFAULT_CONFIG146B: dict = copy.deepcopy(L139.DEFAULT_CONFIG139)
DEFAULT_CONFIG146B["ears"]["stand_in"] = (
    "Loop146bEars (loop139 + exp-146 refused-correction doubt; doubts146.json "
    "notebook-side) over loop139 value-guard chain")
DEFAULT_CONFIG146B["daemon"]["module"] = "Loop146bDaemon (this file)"


def build_agent146b(cfg: dict | None = None) -> Loop146bAgentLoop:
    """Build the loop139 agent shape with the doubt mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG146B, **(cfg or {}))
    loop = L139.build_agent139(cfg)
    loop.ears.__class__ = Loop146bEars
    loop.ears.name = Loop146bEars.name
    loop.__class__ = Loop146bAgentLoop
    state_dir = Path(cfg.get("state_dir", "."))
    store = D146.DoubtStore146(state_dir)
    loop.doubt_store146 = store
    loop.ears.doubt_store146 = store
    return loop


class Loop146bDaemon(L139.Loop139Daemon):
    """Loop139Daemon shape with the loop146b agent inside (mailbox same)."""

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
        self.loop = build_agent146b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon146b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop146bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 146 doubt-on-139 loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop139)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG146B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG146B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG146B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon146b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent146b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
