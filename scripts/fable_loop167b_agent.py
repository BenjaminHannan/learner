#!/usr/bin/env python3
"""Experiment 167b -- loop167b = loop167 + verb-object value screen.

Thin wrapper only (no existing file edited -- in particular no 167 file,
no 139e/139c file, no 162b file): the behaviour change lives in
scripts/fable_fix167b_valuescreen.py (ValueScreen167bMixin: strip trailing
tail words with loop139e's sealed tail machinery, then refuse
article/determiner-led or lowercase-led objects with loop167's own
no-write clarify), stacked OUTERMOST onto loop167 in the style of
scripts/fable_loop167_agent.py:

  Loop167bEars(ValueScreen167bMixin, Loop167Ears):

the 167b screen runs first but only touches turns loop167's verb stage
claims (statements get screened, questions pass through to the 167 path
literally); everything else takes the loop167 code path literally, so
non-verb behaviour is byte-identical by construction, and screened-out
turns reply exactly loop167's own clarify with no write.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop167b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-verb167b-20260922/loop167b-config.json
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

import fable_fix167b_valuescreen as S167B  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (builder base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (wrapped base agent, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (config donor, read-only)
import fable_loop167_agent as L167  # noqa: E402 (base agent, read-only)


class Loop167bEars(S167B.ValueScreen167bMixin, L167.Loop167Ears):
    """Loop167Ears + outermost 167b verb-object value screen."""

    name = "loop167b-valuescreen"


class Loop167bAgentLoop(L162.Loop162AgentLoop):
    """Loop162AgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG167B: dict = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
DEFAULT_CONFIG167B["ears"]["stand_in"] = (
    "Loop167bEars (loop167 + exp-167b verb-object value screen: trailing "
    "tail words stripped with loop139e's sealed tail machinery, then "
    "article/determiner-led or lowercase-led objects refused with loop167's "
    "own no-write clarify; verb questions and everything else take the "
    "loop167 code path literally) over loop150 chain")
DEFAULT_CONFIG167B["daemon"]["module"] = "Loop167bDaemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent167b(cfg: dict | None = None) -> Loop167bAgentLoop:
    """Build the loop167 shape with the 167b value screen stacked outermost."""
    cfg = dict(DEFAULT_CONFIG167B, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop167bEars,
                      Loop167bAgentLoop)


class _DaemonBase167b(L162B._DaemonBase162b):
    """162b's daemon base (idle_seconds intact) with the 167b agent inside."""

    _builder = staticmethod(build_agent167b)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop167bDaemon(_DaemonBase167b):
    """Loop150Daemon shape with the loop167b agent inside (mailbox same)."""

    _builder = staticmethod(build_agent167b)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 167b verb value-screen loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop167)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG167B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG167B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG167B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop167bDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent167b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
