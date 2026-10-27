#!/usr/bin/env python3
"""Experiment 167d -- loop167d = loop167b + widened verb table.

Thin wrapper only (no existing file edited -- in particular no 167b,
167, 139e/139c, or 162b file): the behaviour change lives in
scripts/fable_fix167d_verb.py (Verb167dMixin: four added rows --
"works at"->employer, "speaks"->language statements plus "Where does X
work?" and "What language(s) does X speak?" questions -- rewritten to
their possessive twins; new-shape statements screened with the same
S167B.screen_value 167b applies). Stacked INSIDE the untouched 167b
value screen, in the style of scripts/fable_loop167b_agent.py:

  Loop167dEars(ValueScreen167bMixin, Verb167dMixin, Plural162bMixin,
               TheName162Mixin, OfficeholderGuardMixin, Loop150Ears):

the outer 167b screen runs first on 167's shapes (byte-identical for
everything 167b claims); added 167d shapes fall through it untouched
(V167.parse_verb_turn declines them) and reach Verb167dMixin, which
claims ONLY the added shapes -- so non-verb behaviour and all 167/167b
behaviour is byte-identical by construction, and screened-out or
declined turns reply exactly the base clarify with no write.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop167d_agent.py --daemon --dir DIR \\
    --config artifacts/fable-verb167d-20260922/loop167d-config.json
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
import fable_fix167b_valuescreen as S167B  # noqa: E402 (outer screen, read-only)
import fable_fix167d_verb as V167D  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (builder base, read-only)
import fable_loop162_agent as L162  # noqa: E402 (wrapped base agent, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (config donor, read-only)


class Loop167dEars(S167B.ValueScreen167bMixin, V167D.Verb167dMixin,
                   B162.Plural162bMixin, T162.TheName162Mixin,
                   F135.OfficeholderGuardMixin, L150.Loop150Ears):
    """Loop167bEars + inner 167d widened-verb stage."""

    name = "loop167d-verb"


class Loop167dAgentLoop(L162.Loop162AgentLoop):
    """Loop162AgentLoop (acts unchanged); ears differ."""


DEFAULT_CONFIG167D: dict = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
DEFAULT_CONFIG167D["ears"]["stand_in"] = (
    "Loop167dEars (loop167b + exp-167d widened verb stage inside the "
    "untouched 167b value screen: works at->employer, speaks->language "
    "statements and Where-does-X-work / What-language(s)-does-X-speak "
    "questions rewrite to possessive twins via the canonical path; "
    "new-shape statement objects pass the same 167b value screen; "
    "Who-does-X-work-for stays as 167 left it; all else is the loop167b "
    "code literally) over loop150 chain")
DEFAULT_CONFIG167D["daemon"]["module"] = "Loop167dDaemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent167d(cfg: dict | None = None) -> Loop167dAgentLoop:
    """Build the loop167b shape with the 167d verb mixin stacked inside."""
    cfg = dict(DEFAULT_CONFIG167D, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop167dEars,
                      Loop167dAgentLoop)


class _DaemonBase167d(L162B._DaemonBase162b):
    """162b's daemon base (idle_seconds intact) with the 167d agent inside."""

    _builder = staticmethod(build_agent167d)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop167dDaemon(_DaemonBase167d):
    """Loop150Daemon shape with the loop167d agent inside (mailbox same)."""

    _builder = staticmethod(build_agent167d)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 167d widened-verb loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop167b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG167D to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG167D)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG167D)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop167dDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent167d(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
