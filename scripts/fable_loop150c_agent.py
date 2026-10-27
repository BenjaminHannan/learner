#!/usr/bin/env python3
"""Experiment 150c -- loop150c = loop150 + the exp-150c closed-class-subject
mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix150c_closedclass.py (ClosedClass150CMixin: refuse with the
loop's OWN total-miss reply any teach/correct whose subject span, after the
loop's own normalisation, is WHOLLY a closed-class word or phrase;
capitalised names that merely contain such a word still teach); this file
stacks it onto loop150 at both levels (ears hear + loop _act just before
the write). Values, relation keys, forget/ask/clarify paths untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop150c_agent.py --daemon --dir DIR \\
    --config artifacts/fable-subject150c-20260922/loop150c-config.json
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

import fable_fix150c_closedclass as S150c  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop150cEars(S150c.ClosedClass150CMixin, L150.Loop150Ears):
    """Loop150Ears + 150c closed-class-subject guard on outgoing teach/correct."""

    name = "loop150c-closedclass"


class Loop150cAgentLoop(S150c.ClosedClass150CMixin, L150.Loop150AgentLoop):
    """Loop150AgentLoop + 150c closed-class-subject guard before the write."""


DEFAULT_CONFIG150C: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG150C["ears"]["stand_in"] = (
    "Loop150cEars (loop150 + exp-150c closed-class-subject guard: refuse "
    "with the loop's own total-miss reply any teach/correct whose subject "
    "span is wholly a closed-class word or phrase; names that merely "
    "contain one still teach) over loop150 chain")
DEFAULT_CONFIG150C["daemon"]["module"] = "Loop150cDaemon (this file)"


def build_agent150c(cfg: dict | None = None) -> Loop150cAgentLoop:
    """Build the loop150 agent shape with the 150c guard mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG150C, **(cfg or {}))
    loop = L150.build_agent150(cfg)
    loop.ears.__class__ = Loop150cEars
    loop.ears.name = Loop150cEars.name
    loop.__class__ = Loop150cAgentLoop
    return loop


class Loop150cDaemon(L150.Loop150Daemon):
    """Loop150Daemon shape with the loop150c agent inside (mailbox same)."""

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
        self.loop = build_agent150c(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon150c(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop150cDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 150c closed-class loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG150C to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG150C)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG150C)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon150c(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent150c(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
