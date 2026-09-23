#!/usr/bin/env python3
"""Experiment 140 -- loop129b + the exp-140 value-tail mixin (ONE CHANGE).

loop140 = loop129b + fable_fix140_tail, subclass only. No existing file is
edited; everything new lives in this file (+ scripts/fable_fix140_tail.py).

  Loop140Ears(Loop129bEars): hear() sanitizes the subject/value of outgoing
    teach/correct actions with the exp-140 cleaner (emoji/symbol tails,
    unmatched trailing quotes, abbreviation-aware dots).
  Loop140AgentLoop(Loop129bAgentLoop): _act() sanitizes teach/correct
    actions again just before the notebook write (covers the inner-chain
    Bench73Stage/FakeStage delegate path).
  TailFakeEars swap: every fable_agent_loop.FakeEars instance inside the
    ears chain (FakeStage._fake) is replaced with TailFakeEars, which uses
    the same cleaner instead of value.rstrip(".") on the possessive path.
    Forget/ask/clarify/question paths are byte-identical.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop140_agent.py --daemon --dir DIR \\
    --config artifacts/fable-fix140-20260922/loop140-config.json
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

import fable_agent_loop as A  # noqa: E402 (FakeEars base, read-only)
import fable_fix140_tail as T140  # noqa: E402 (this experiment's mixin)
import fable_loop129b_agent as L129b  # noqa: E402 (wrapped base, read-only)


class Loop140Ears(L129b.Loop129bEars):
    """Loop129bEars + exp-140 tail sanitize on outgoing teach/correct."""

    name = "loop140-tail"

    def hear(self, turn: str) -> list[dict]:
        return T140.sanitize_actions(super().hear(turn))


class Loop140AgentLoop(L129b.Loop129bAgentLoop):
    """Loop129bAgentLoop + exp-140 sanitize teach/correct before the write."""

    def _act(self, action: dict) -> dict:
        if isinstance(action, dict) and action.get("act") in (
                "teach", "correct"):
            action = T140.sanitize_action(action)
        return super()._act(action)


def _swap_fake_ears(obj, _seen: set[int] | None = None) -> int:
    """Replace plain FakeEars instances under obj with TailFakeEars.

    Walks __dict__ trees (and lists) below the ears wrappers only; the
    notebook (``nb``) is never descended into. Returns the swap count.
    """
    if _seen is None:
        _seen = set()
    if id(obj) in _seen:
        return 0
    _seen.add(id(obj))
    n = 0
    d = getattr(obj, "__dict__", None)
    if not isinstance(d, dict):
        return 0
    for key, val in list(d.items()):
        if key == "nb":
            continue
        if type(val) is A.FakeEars:
            d[key] = T140.TailFakeEars()
            n += 1
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if type(item) is A.FakeEars:
                    val[i] = T140.TailFakeEars()
                    n += 1
                elif hasattr(item, "__dict__"):
                    n += _swap_fake_ears(item, _seen)
        elif hasattr(val, "__dict__"):
            n += _swap_fake_ears(val, _seen)
    return n


DEFAULT_CONFIG140: dict = copy.deepcopy(L129b.DEFAULT_CONFIG129B)
DEFAULT_CONFIG140["ears"]["stand_in"] = (
    "Loop140Ears (loop129b + exp-140 value-tail cleaner on teach/correct "
    "name+value; TailFakeEars replaces rstrip('.') on the possessive path) "
    "over loop129b chain")
DEFAULT_CONFIG140["daemon"]["module"] = "Loop140Daemon (this file)"


def build_agent140(cfg: dict | None = None) -> Loop140AgentLoop:
    """Build the loop129b agent shape with Loop140Ears/Loop + TailFakeEars."""
    cfg = dict(DEFAULT_CONFIG140, **(cfg or {}))
    loop = L129b.build_agent129b(cfg)
    loop.ears.__class__ = Loop140Ears
    loop.ears.name = Loop140Ears.name
    loop.__class__ = Loop140AgentLoop
    loop.tail_swaps = _swap_fake_ears(loop.ears)
    return loop


class Loop140Daemon(L129b.Loop129bDaemon):
    """Loop129bDaemon shape with the loop140 agent inside (mailbox same)."""

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
        self.loop = build_agent140(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


def run_daemon140(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop140Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 140 patched loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop129b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG140 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG140)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG140)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        return run_daemon140(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds)
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent140(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
