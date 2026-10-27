#!/usr/bin/env python3
"""Experiment 153 -- loop153 = loop150 + the exp-153 reverse-question stage.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix153_reverse.py (Reverse153Mixin: on a forward miss only,
parse four closed reverse frames and answer from the loop's own live taught
triples; clarify actions only, so never a write). This file stacks it onto
loop150 (scripts/fable_loop150_agent.py, artifacts/fable-fix150-20260922/
loop150-config.json; loop150 = loop129b + 139b value guard + 150 subject
guard) in the style of scripts/fable_loop140_agent.py: ears subclass only,
no _act override needed (reverse stage emits clarify, which the loop's _act
passes through without writing).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop153_agent.py --daemon --dir DIR \\
    --config artifacts/fable-reverse153-20260922/loop153-config.json
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

import fable_fix153_reverse as R153  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop153Ears(R153.Reverse153Mixin, L150.Loop150Ears):
    """Loop150Ears + 153 reverse-question stage on forward-miss "?" turns."""

    name = "loop153-reverse"


class Loop153AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop (acts unchanged; reverse answers are clarifies)."""


DEFAULT_CONFIG153: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG153["ears"]["stand_in"] = (
    "Loop153Ears (loop150 + exp-153 reverse-question stage: on the forward "
    "miss only, four closed frames answered from live taught triples; "
    "clarify-only, never a write) over loop150 chain")
DEFAULT_CONFIG153["daemon"]["module"] = "Loop153Daemon (this file)"


def build_agent153(cfg: dict | None = None) -> Loop153AgentLoop:
    """Build the loop150 agent shape with the 153 reverse mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG153, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop153Ears
    loop.ears.name = Loop153Ears.name
    loop.__class__ = Loop153AgentLoop
    return loop


class Loop153Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop153 agent inside (mailbox same)."""

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
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
        self.heartbeat_path = self.root / "heartbeat.json"
        self.status_path = self.root / "daemon_status.json"
        self.log_path = self.root / "daemon.log.jsonl"
        import os as _os
        import time as _time
        self.pid = _os.getpid()
        self.boot_time = _time.time()
        self.idle_seconds = float(idle_seconds)
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = build_agent153(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon153(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop153Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 153 reverse loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG153 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG153)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG153)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon153(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent153(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
