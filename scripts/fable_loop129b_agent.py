#!/usr/bin/env python3
"""Experiment 129b -- loop121 + the exp-129 punctuation mixin (ONE CHANGE).

loop129b = loop121 + fable_fix129_punct, subclass only. No existing file is
edited; everything new lives in this file (+ scripts/fable_fix129_punct.py).

  Loop129bEars(Loop121Ears): hear() sanitizes the subject/value of outgoing
    teach/correct actions (covers the 121 teach paths: bench73, exp-92
    extra patterns, correction prefix).
  Loop129bAgentLoop(Loop121AgentLoop): _act() sanitizes teach/correct
    actions again just before the notebook write (covers the inner-chain
    Bench73Stage/FakeStage delegate path). Forget/ask/clarify untouched;
    relation keys byte-identical; question side identical to loop121.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop129b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-fix129-20260922/loop129b-config.json
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

import fable_fix129_punct as P129  # noqa: E402 (this experiment's mixin)
import fable_loop121_agent as L121  # noqa: E402 (wrapped base, read-only)


class Loop129bEars(L121.Loop121Ears):
    """Loop121Ears + punctuation sanitize on outgoing teach/correct."""

    name = "loop129b-punct"

    def hear(self, turn: str) -> list[dict]:
        return P129.sanitize_actions(super().hear(turn))


class Loop129bAgentLoop(L121.Loop121AgentLoop):
    """Loop121AgentLoop + sanitize teach/correct just before the write."""

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            action = P129.sanitize_action(action)
        return super()._act(action)


DEFAULT_CONFIG129B: dict = copy.deepcopy(L121.DEFAULT_CONFIG121)
DEFAULT_CONFIG129B["ears"]["stand_in"] = (
    "Loop129bEars (loop121 teach coverage + exp-129 sentence-punctuation "
    "strip on teach/correct name+value) over " + "loop121 chain")
DEFAULT_CONFIG129B["daemon"]["module"] = "Loop129bDaemon (this file)"


def build_agent129b(cfg: dict | None = None) -> Loop129bAgentLoop:
    """Build the loop121 agent shape with Loop129bEars/Loop swapped in."""
    cfg = dict(DEFAULT_CONFIG129B, **(cfg or {}))
    loop = L121.build_agent121(cfg)
    loop.ears.__class__ = Loop129bEars
    loop.ears.name = Loop129bEars.name
    loop.__class__ = Loop129bAgentLoop
    return loop


class Loop129bDaemon(L121.Loop121Daemon):
    """Loop121Daemon shape with the loop129b agent inside (mailbox same)."""

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
        self.loop = build_agent129b(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon129b(root, cfg: dict | None = None,
                   idle_seconds: float = 30.0) -> int:
    daemon = Loop129bDaemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 129b patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop121)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG129B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG129B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG129B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon129b(args.dir, cfg=cfg,
                              idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent129b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
