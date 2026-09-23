#!/usr/bin/env python3
"""Experiment 158 -- loop150 + the exp-158 question-surface mixin (ONE CHANGE).

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix158_qform.py (Qform158Mixin: what's/who's/where's/when's
expansion, tell/show/give-me imperatives, trailing-mark collapse, applied
only when the normalised text parses as a question by the unchanged
loop); this file stacks it onto loop150 at the outermost ears hear()
(question actions never write, so no loop _act override is needed).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop158_agent.py --daemon --dir DIR \\
    --config artifacts/fable-qform158-20260922/loop158-config.json
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

import fable_fix158_qform as Q158  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop158Ears(Q158.Qform158Mixin, L150.Loop150Ears):
    """Loop150Ears + 158 question-surface normalisation before parsing."""

    name = "loop158-qform"


class Loop158AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop (question path only; acts untouched)."""


DEFAULT_CONFIG158: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG158["ears"]["stand_in"] = (
    "Loop158Ears (loop150 + exp-158 question-surface normalisation: "
    "leading what's/who's/where's/when's -> what/who/where/when is, "
    "tell/show/give-me X's R and tell-me-who/what imperatives -> the "
    "question, trailing [?.!]+ -> one '?', applied only when the "
    "normalised text parses as a question by the unchanged loop) "
    "over loop150 chain")
DEFAULT_CONFIG158["daemon"]["module"] = "Loop158Daemon (this file)"


def build_agent158(cfg: dict | None = None) -> Loop158AgentLoop:
    """Build the loop150 agent shape with the 158 mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG158, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop158Ears
    loop.ears.name = Loop158Ears.name
    loop.__class__ = Loop158AgentLoop
    return loop


class Loop158Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop158 agent inside (mailbox same)."""

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
        self.loop = build_agent158(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon158(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop158Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 158 question-form loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG158 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG158)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG158)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon158(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent158(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
