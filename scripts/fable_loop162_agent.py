#!/usr/bin/env python3
"""Experiment 162 -- loop162 = loop150 + 135 officeholder guard + 162 The-name mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix162_thename.py (TheName162Mixin: "The X's R is V." /
"The Xs' R is V." for table relations -> (The X, R, V) with "The" kept,
through the canonical save path; "The X's R" / "the R of The X" asks
resolve to that entity). This file stacks it onto loop150 together with
the 135 mixin, in the style of scripts/fable_loop155_agent.py:

  Loop162Ears(TheName162Mixin, OfficeholderGuardMixin, Loop150Ears):
    the 162 stage runs first (it must pre-empt the office catch-all); the
    135 transient hear_teach_template patch still wraps the base hear for
    everything the 162 stage declines (office phrases, non-table relations).

It also provides the G1 reference stack (loop150 + the 135 mixin, no 162):

  Loop150x135Ears(OfficeholderGuardMixin, Loop150Ears)

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop162_agent.py --daemon --dir DIR \\
    --config artifacts/fable-thename162-20260922/loop162-config.json
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

import fable_fix135_office as F135  # noqa: E402 (coexistence stack, read-only)
import fable_fix162_thename as T162  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop162Ears(T162.TheName162Mixin, F135.OfficeholderGuardMixin,
                  L150.Loop150Ears):
    """Loop150Ears + 135 officeholder guard + 162 The-name teach stage."""

    name = "loop162-thename"


class Loop162AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop (acts unchanged); ears differ."""


class Loop150x135Ears(F135.OfficeholderGuardMixin, L150.Loop150Ears):
    """Reference stack for G1: loop150 + 135 guard, no 162 stage."""

    name = "loop150-x135"


class Loop150x135AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG162: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG162["ears"]["stand_in"] = (
    "Loop162Ears (loop150 + exp-135 officeholder catch-all guard + "
    "exp-162 The-name possessive teach stage: The X's R / The Xs' R frames "
    "for table relations save (The X, R, V) via the canonical path; "
    "officeholder catch-all never touched) over loop150 chain")
DEFAULT_CONFIG162["daemon"]["module"] = "Loop162Daemon (this file)"

DEFAULT_CONFIG150X135: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG150X135["ears"]["stand_in"] = (
    "Loop150x135Ears (loop150 + exp-135 officeholder catch-all guard, "
    "no 162 stage; G1 reference) over loop150 chain")
DEFAULT_CONFIG150X135["daemon"]["module"] = "Loop150x135Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent162(cfg: dict | None = None) -> Loop162AgentLoop:
    """Build the loop150+135 shape with the 162 mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG162, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop162Ears,
                      Loop162AgentLoop)


def build_agent150x135(cfg: dict | None = None) -> Loop150x135AgentLoop:
    """Build the G1 reference: loop150 + 135 guard, no 162 stage."""
    cfg = dict(DEFAULT_CONFIG150X135, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop150x135Ears,
                      Loop150x135AgentLoop)


class _DaemonBase(L150.Loop150Daemon):
    _builder = staticmethod(build_agent162)

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
        agent_cfg = dict(self.cfg)
        agent_cfg["state_dir"] = str(self.root)
        self.loop = self._builder(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


class Loop162Daemon(_DaemonBase):
    """Loop150Daemon shape with the loop162 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent162)


class Loop150x135Daemon(_DaemonBase):
    """Loop150Daemon shape with the loop150x135 reference agent inside."""

    _builder = staticmethod(build_agent150x135)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 162 The-name loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG162 to PATH and exit")
    parser.add_argument("--variant", default="loop162",
                        choices=("loop162", "loop150x135"))
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.variant == "loop150x135":
        default, builder, runner = (DEFAULT_CONFIG150X135,
                                    build_agent150x135, Loop150x135Daemon)
    else:
        default, builder, runner = (DEFAULT_CONFIG162, build_agent162,
                                    Loop162Daemon)

    if args.write_config:
        out = copy.deepcopy(default)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(default)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = runner(args.dir, cfg=cfg, idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = builder(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
