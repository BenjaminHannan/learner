#!/usr/bin/env python3
"""Experiment 162b -- loop162b = loop162 + plural possessive fix (+ daemon fix).

Thin wrapper only (no existing file edited -- in particular no 162 file):
the behaviour change lives in scripts/fable_fix162b_plural.py
(Plural162bMixin: "The Xs' R is V." for table relations -> (The Xs, R, V)
with the stem-final "s" restored, through the canonical save path). This file
stacks it OUTERMOST onto loop162, in the style of
scripts/fable_loop162_agent.py:

  Loop162bEars(Plural162bMixin, TheName162Mixin, OfficeholderGuardMixin,
               Loop150Ears):

the 162b plural stage runs first (it only claims ``s'`` turns loop162
rejects); everything else takes the loop162 code path literally, so singular
behaviour is byte-identical by construction.

HARNESS-ONLY second change (disclosed, not behaviour): 162's _DaemonBase
copy dropped the ``self.idle_seconds = float(idle_seconds)`` line its loop150
template has, so run() raises AttributeError and the daemon-mailbox suites
(p3/rt110/q4, soak) hang. _DaemonBase162b re-adds that one line after
delegating to 162's own __init__. No teach/ask code is touched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop162b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-plural162b-20260922/loop162b-config.json
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
import fable_fix162_thename as T162  # noqa: E402 (wrapped base mixin, read-only)
import fable_fix162b_plural as B162  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (wrapped base agent, read-only)


class Loop162bEars(B162.Plural162bMixin, T162.TheName162Mixin,
                   F135.OfficeholderGuardMixin, L150.Loop150Ears):
    """Loop162Ears + outermost 162b plural teach stage."""

    name = "loop162b-plural"


class Loop162bAgentLoop(L162.Loop162AgentLoop):
    """Loop162AgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG162B: dict = copy.deepcopy(L162.DEFAULT_CONFIG162)
DEFAULT_CONFIG162B["ears"]["stand_in"] = (
    "Loop162bEars (loop162 + exp-162b plural possessive teach stage: "
    "The Xs' R frames for table relations save (The Xs, R, V) via the "
    "canonical path; singular/office/ask paths are the loop162 code "
    "literally) over loop150 chain")
DEFAULT_CONFIG162B["daemon"]["module"] = "Loop162bDaemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent162b(cfg: dict | None = None) -> Loop162bAgentLoop:
    """Build the loop162 shape with the 162b plural mixin stacked outermost."""
    cfg = dict(DEFAULT_CONFIG162B, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop162bEars,
                      Loop162bAgentLoop)


class _DaemonBase162b(L162._DaemonBase):
    """162's daemon base + the dropped idle_seconds line (harness only)."""

    _builder = staticmethod(build_agent162b)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        # 162's copy of Loop150Daemon.__init__ dropped this line; re-add:
        self.idle_seconds = float(idle_seconds)


class Loop162bDaemon(_DaemonBase162b):
    """Loop150Daemon shape with the loop162b agent inside (mailbox same)."""

    _builder = staticmethod(build_agent162b)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 162b plural loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop162)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG162B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG162B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG162B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop162bDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent162b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
