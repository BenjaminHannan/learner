#!/usr/bin/env python3
"""Experiment 165 -- loop165 = loop162b + missing-apostrophe possessive fix.

Thin wrapper only (no existing file edited -- in particular no 162b file):
the behaviour change lives in scripts/fable_fix165_typo.py (Typo165Mixin:
"W R is V." / "Who is W R?" for person relations, with W ending in s and no
apostrophe, read as the possessive of W-minus-s iff W-minus-s resolves to
exactly one known entity while W itself is unknown and not a known plural
name; the rewritten turn is delegated to the base hear literally). This file
stacks it OUTERMOST onto loop162b:

  Loop165Ears(Typo165Mixin, Loop162bEars):

the 165 typo stage runs first (it only claims full-shape no-apostrophe
turns whose notebook gates hold, which loop162b always clarifies); every
other turn takes the loop162b code path literally, so non-claimed behaviour
is byte-identical by construction.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop165_agent.py --daemon --dir DIR \\
    --config artifacts/fable-typo165-20260922/loop165-config.json
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

import fable_fix165_typo as T165  # noqa: E402 (this experiment)
import fable_loop162b_agent as L162B  # noqa: E402 (wrapped base, read-only)


class Loop165Ears(T165.Typo165Mixin, L162B.Loop162bEars):
    """Loop162bEars + outermost 165 missing-apostrophe possessive stage."""

    name = "loop165-typo"


class Loop165AgentLoop(L162B.Loop162bAgentLoop):
    """Loop162bAgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG165: dict = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
DEFAULT_CONFIG165["ears"]["stand_in"] = (
    "Loop165Ears (loop162b + exp-165 missing-apostrophe possessive stage: "
    "W R frames for person relations, W ending in s with no apostrophe, "
    "read as W-minus-s possessive iff W-minus-s resolves to exactly one "
    "known entity while W itself is unknown and not a known plural name; "
    "rewritten turn takes the loop162b path literally) over loop162b chain")
DEFAULT_CONFIG165["daemon"]["module"] = "Loop165Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent165(cfg: dict | None = None) -> Loop165AgentLoop:
    """Build the loop162b shape with the 165 typo mixin stacked outermost."""
    cfg = dict(DEFAULT_CONFIG165, **(cfg or {}))
    return _swap_loop(L162B.build_agent162b(cfg), Loop165Ears,
                      Loop165AgentLoop)


class Loop165Daemon(L162B._DaemonBase162b):
    """Loop162bDaemon shape with the loop165 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent165)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 165 typo loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop162b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG165 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG165)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG165)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop165Daemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent165(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
