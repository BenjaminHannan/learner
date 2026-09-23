#!/usr/bin/env python3
"""Experiment 155 -- loop155 = loop150 + the exp-155 inverted-frame mixin.

Thin wrapper only (no existing file edited): the ONE CHANGE lives in
scripts/fable_fix155_inverted.py (InvertedFrame155Mixin: "V is X's R." /
"V is the R of X." / "The R of X is V." -> (X, R, V) for relation cues in
the loop's own tables, never the officeholder catch-all, through the same
guards/audit/replies as canonical "X's R is V."). This file stacks it onto
loop150 at the ears level (loop _act guards apply unchanged), in the style
of scripts/fable_loop140_agent.py:

  Loop155Ears(InvertedFrame155Mixin, Loop150Ears): loop150 + inverted stage.
  Loop155AgentLoop(Loop150AgentLoop): unchanged acts (subclass for naming,
    so the marks123 harness finds the loop155 names).

Plus the coexistence stack (loop150 + exp-135 officeholder guard + 155):

  Loop155x135Ears(InvertedFrame155Mixin, OfficeholderGuardMixin,
    Loop150Ears): the 135 mixin stays second so its transient
    hear_teach_template patch still wraps the base hear; the 155 stage runs
    first and falls through to it untouched for office phrases.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop155_agent.py --daemon --dir DIR \\
    --config artifacts/fable-inverted155-20260922/loop155-config.json
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
import fable_fix155_inverted as I155  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)


class Loop155Ears(I155.InvertedFrame155Mixin, L150.Loop150Ears):
    """Loop150Ears + 155 inverted-frame teach stage (stackable mixin first)."""

    name = "loop155-inverted"


class Loop155AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop (acts unchanged); ears differ."""


class Loop155x135Ears(I155.InvertedFrame155Mixin,
                      F135.OfficeholderGuardMixin, L150.Loop150Ears):
    """Loop150Ears + 135 officeholder guard + 155 inverted stage."""

    name = "loop155-inverted-x135"


class Loop155x135AgentLoop(L150.Loop150AgentLoop):
    """Loop150AgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG155: dict = copy.deepcopy(L150.DEFAULT_CONFIG150)
DEFAULT_CONFIG155["ears"]["stand_in"] = (
    "Loop155Ears (loop150 + exp-155 inverted-frame teach stage: V-is-X's-R "
    "frames for table relations save (X, R, V) via the canonical path; "
    "officeholder catch-all never touched) over loop150 chain")
DEFAULT_CONFIG155["daemon"]["module"] = "Loop155Daemon (this file)"

DEFAULT_CONFIG155X135: dict = copy.deepcopy(DEFAULT_CONFIG155)
DEFAULT_CONFIG155X135["ears"]["stand_in"] = (
    "Loop155x135Ears (loop150 + exp-135 officeholder catch-all guard + "
    "exp-155 inverted-frame teach stage) over loop150 chain")
DEFAULT_CONFIG155X135["daemon"]["module"] = "Loop155x135Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent155(cfg: dict | None = None) -> Loop155AgentLoop:
    """Build the loop150 agent shape with the 155 mixin stacked in."""
    cfg = dict(DEFAULT_CONFIG155, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop155Ears,
                      Loop155AgentLoop)


def build_agent155x135(cfg: dict | None = None) -> Loop155x135AgentLoop:
    """Build the loop150+135 coexistence shape with the 155 mixin stacked."""
    cfg = dict(DEFAULT_CONFIG155X135, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop155x135Ears,
                      Loop155x135AgentLoop)


class _DaemonBase(L150.Loop150Daemon):
    _builder = staticmethod(build_agent155)

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
        self.loop = self._builder(agent_cfg)
        self.torn_found = any("torn notebook tail" in note
                              for note in self.loop.notes)


class Loop155Daemon(_DaemonBase):
    """Loop150Daemon shape with the loop155 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent155)


class Loop155x135Daemon(_DaemonBase):
    """Loop150Daemon shape with the loop155x135 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent155x135)


def run_daemon155(root, cfg: dict | None = None,
                  idle_seconds: float = 30.0) -> int:
    daemon = Loop155Daemon(root, cfg=cfg, idle_seconds=idle_seconds)
    return daemon.run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 155 inverted-frame loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop150)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG155 to PATH and exit")
    parser.add_argument("--variant", default="loop155",
                        choices=("loop155", "loop155x135"))
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.variant == "loop155x135":
        default, builder, runner = (DEFAULT_CONFIG155X135, build_agent155x135,
                                    Loop155x135Daemon)
    else:
        default, builder, runner = (DEFAULT_CONFIG155, build_agent155,
                                    Loop155Daemon)

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
