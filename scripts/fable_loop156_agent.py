#!/usr/bin/env python3
"""Experiment 156 -- loop156 = loop150 + the exp-156 small-talk mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix156_smalltalk.py (Smalltalk156Mixin: no-write class
replies on the exact generic fallthrough when every normalised word is
in the closed small-talk list); this file stacks it onto loop150 as the
outermost ears layer (loop150 = loop129b + 139b value guard + 150
subject guard, imported read-only).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop156_agent.py --daemon --dir DIR \\
    --config artifacts/fable-smalltalk156-20260922/loop156-config.json
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

import fable_fix156_smalltalk as S156  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop156Ears(S156.Smalltalk156Mixin, L150.Loop150Ears):
    """Loop150Ears + 156 small-talk stage on the generic fallthrough."""

    name = "loop156-smalltalk"


class Loop156AgentLoop(S156.Smalltalk156Mixin, L150.Loop150AgentLoop):
    """Loop150AgentLoop (mixin is ears-active; clarify acts never write)."""


DEFAULT_CONFIG156: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG156["ears"]["stand_in"] = (
    "Loop156Ears (loop150 + exp-156 no-write small-talk stage: fixed "
    "class replies on the generic fallthrough when every normalised "
    "word is in the closed small-talk list) over loop150 chain")
DEFAULT_CONFIG156["daemon"]["module"] = "Loop156Daemon (this file)"


def build_agent156(cfg: dict | None = None) -> Loop156AgentLoop:
    """Build the loop150 agent shape with the 156 mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG156, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop156Ears
    loop.ears.name = Loop156Ears.name
    loop.__class__ = Loop156AgentLoop
    return loop


class Loop156Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop156 agent inside (mailbox same)."""

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
        self.loop = build_agent156(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon156(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop156Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 156 small-talk loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG156 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG156)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG156)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon156(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent156(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
