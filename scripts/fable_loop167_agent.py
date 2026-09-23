#!/usr/bin/env python3
"""Experiment 167 -- loop167 = loop162b + verb-phrase-to-relation mixin.

Thin wrapper only (no existing file edited -- in particular no 162b file):
the behaviour change lives in scripts/fable_fix167_verb.py (Verb167Mixin:
closed table mapping "lives in"->city, "works for"->employer,
"was born in"->place_of_birth statements to their possessive twins, plus the
four matching verb questions; "is married to" statements stay on the base
path which already teaches them). This file stacks it OUTERMOST onto
loop162b, in the style of scripts/fable_loop162b_agent.py:

  Loop167Ears(Verb167Mixin, Plural162bMixin, TheName162Mixin,
              OfficeholderGuardMixin, Loop150Ears):

the 167 verb stage runs first (it only claims verb turns loop162b clarifies,
plus verb questions the base clarifies); everything else takes the loop162b
code path literally, so non-verb behaviour is byte-identical by
construction. Claimed turns are rewritten to their possessive twin and the
base possessive path runs literally, so writes/answers are the possessive
form's own by construction.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop167_agent.py --daemon --dir DIR \\
    --config artifacts/fable-verb167-20260922/loop167-config.json
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
import fable_fix162b_plural as B162  # noqa: E402 (wrapped base mixin, read-only)
import fable_fix167_verb as V167  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (wrapped base agent, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (base agent, read-only)


class Loop167Ears(V167.Verb167Mixin, B162.Plural162bMixin,
                  T162.TheName162Mixin, F135.OfficeholderGuardMixin,
                  L150.Loop150Ears):
    """Loop162bEars + outermost 167 verb-phrase stage."""

    name = "loop167-verb"


class Loop167AgentLoop(L162.Loop162AgentLoop):
    """Loop162AgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG167: dict = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
DEFAULT_CONFIG167["ears"]["stand_in"] = (
    "Loop167Ears (loop162b + exp-167 verb-phrase stage: lives in->city, "
    "works for->employer, was born in->place_of_birth statements and their "
    "verb questions rewrite to possessive twins via the canonical path; "
    "is-married-to statements stay on the base path; all else is the "
    "loop162b code literally) over loop150 chain")
DEFAULT_CONFIG167["daemon"]["module"] = "Loop167Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent167(cfg: dict | None = None) -> Loop167AgentLoop:
    """Build the loop162b shape with the 167 verb mixin stacked outermost."""
    cfg = dict(DEFAULT_CONFIG167, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop167Ears,
                      Loop167AgentLoop)


class _DaemonBase167(L162B._DaemonBase162b):
    """162b's daemon base (idle_seconds intact) with the 167 agent inside."""

    _builder = staticmethod(build_agent167)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop167Daemon(_DaemonBase167):
    """Loop150Daemon shape with the loop167 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent167)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 167 verb loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop162b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG167 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG167)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG167)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop167Daemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent167(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
