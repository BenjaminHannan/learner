#!/usr/bin/env python3
"""Experiment 157 -- loop157 = loop150 + the exp-157 leading-filler mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix157_filler.py (Filler157Mixin: strip ONE leading
discourse filler from a closed list, comma-or-lowercase title rule, only
when the remainder parses as a complete teach or question by the
unchanged loop150 chain); this file stacks it onto loop150 at ears level
in the style of scripts/fable_loop140_agent.py and
scripts/fable_loop150_agent.py. Values, relation keys, forget/ask/
clarify paths, correction markers, and titles are untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop157_agent.py --daemon --dir DIR \\
    --config artifacts/fable-filler157-20260922/loop157-config.json
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

import fable_fix157_filler as F157  # noqa: E402 (this experiment's mixin)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop157Ears(F157.Filler157Mixin, L150.Loop150Ears):
    """Loop150Ears + exp-157 one-filler strip gated on a full re-parse."""

    name = "loop157-filler"


class Loop157AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop unchanged (filler strip lives at ears level)."""


DEFAULT_CONFIG157: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG157["ears"]["stand_in"] = (
    "Loop157Ears (loop150 + exp-157 leading-filler strip: ONE filler from "
    "a closed list, comma-or-lowercase title rule, only when the remainder "
    "parses as a complete teach or question by the unchanged loop150 chain) "
    "over loop150 chain")
DEFAULT_CONFIG157["daemon"]["module"] = "Loop157Daemon (this file)"


def build_agent157(cfg: dict | None = None) -> Loop157AgentLoop:
    """Build the loop150 agent shape with the 157 filler mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG157, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop157Ears
    loop.ears.name = Loop157Ears.name
    loop.__class__ = Loop157AgentLoop
    return loop


class Loop157Daemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop157 agent inside (mailbox same)."""

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
        self.loop = build_agent157(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon157(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop157Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 157 filler-strip loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG157 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG157)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG157)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon157(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent157(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
