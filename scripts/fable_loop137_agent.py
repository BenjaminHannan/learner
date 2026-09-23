#!/usr/bin/env python3
"""Experiment 137 -- loop129b + the exp-137 multi-word possessive mixin.

Thin wrapper: loop137 = loop129b + fable_fix137_names.Fix137PossessiveMixin,
subclass only. No existing file is edited; everything new lives in this file
(+ scripts/fable_fix137_names.py).

  Loop137Ears(Fix137PossessiveMixin, Loop129bEars): base hears first; only an
    all-clarify result on a 2-4-token possessive teach upgrades to a
    structured teach/correct action (same relation map, same value screens,
    same exp-129 punct sanitize). "?" turns delegate byte-identical.
  Loop137AgentLoop(Loop129bAgentLoop): unchanged behaviour (structured actions
    already route to Listening._teach; the 129b _act sanitize still applies).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop137_agent.py --daemon --dir DIR \\
    --config artifacts/fable-fix137-20260922/loop137-config.json
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

import fable_fix137_names as F137  # noqa: E402 (this experiment's mixin)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


class Loop137Ears(F137.Fix137PossessiveMixin, L129b.Loop129bEars):
    """Loop129bEars + multi-word possessive-teach subjects (stacked mixin)."""

    name = "loop137-multiword-possessive"


class Loop137AgentLoop(L129b.Loop129bAgentLoop):
    """Loop129bAgentLoop; ears differ, acts don't."""


DEFAULT_CONFIG137: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG137["ears"]["stand_in"] = (
    "Loop137Ears (Fix137PossessiveMixin: 2-4-token possessive subjects over "
    "Loop129bEars (loop121 teach coverage + exp-129 sentence-punctuation "
    "strip on teach/correct name+value))")
DEFAULT_CONFIG137["daemon"]["module"] = "Loop137Daemon (this file)"


def build_agent137(cfg: dict | None = None) -> Loop137AgentLoop:
    """Build the loop129b agent shape with Loop137Ears swapped in."""
    cfg = dict(DEFAULT_CONFIG137, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop137Ears
    loop.ears.name = Loop137Ears.name
    loop.__class__ = Loop137AgentLoop
    return loop


class Loop137Daemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop137 agent inside (mailbox same)."""

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
        self.loop = build_agent137(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon137(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop137Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 137 patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG137 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG137)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG137)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon137(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent137(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
