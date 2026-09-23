#!/usr/bin/env python3
"""Experiment 166 -- loop166 = loop162b + first-person ("my") user entity.

Thin wrapper only (no existing file edited -- in particular no 162b/162
file): the behaviour change lives in scripts/fable_fix166_me.py (Me166Mixin:
"My <R> is <V>." teaches and "Who/What/Where is|are my <chain>?" asks map to
the reserved notebook entity USER_KEY="USER" through the canonical save/hop
path). This file stacks it OUTERMOST onto loop162b:

  Loop166Ears(Me166Mixin, Plural162bMixin, TheName162Mixin,
              OfficeholderGuardMixin, Loop150Ears):

the me stage runs first (it only claims "my"-headed turns loop162b always
refuses); everything else takes the loop162b code path literally, so
non-first-person behaviour is byte-identical by construction.

Second change, REPLY RENDERING (this file, disclosed): Loop166AgentLoop
overrides _listening_tick only to rewrite said lines for turns claimed by
the me parser (USER -> your/Your, unknown -> "I don't know your <rel> yet").
Turns the parser does not claim return super()'s event untouched.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop166_agent.py --daemon --dir DIR \\
    --config artifacts/fable-me166-20260922/loop166-config.json
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
import fable_fix162_thename as T162  # noqa: E402 (coexistence stack, read-only)
import fable_fix162b_plural as B162  # noqa: E402 (coexistence stack, read-only)
import fable_fix166_me as M166  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)
import fable_loop162b_agent as L162B  # noqa: E402 (wrapped base agent, read-only)


class Loop166Ears(M166.Me166Mixin, B162.Plural162bMixin,
                  T162.TheName162Mixin, F135.OfficeholderGuardMixin,
                  L150.Loop150Ears):
    """Loop162bEars + outermost exp-166 first-person teach/ask stage."""

    name = "loop166-me"


def rewrite_me166_reply(line: str, turn: str) -> str:
    """Render a said line for a me-claimed turn without the raw USER key.

    Only called for turns claimed by this experiment's parser; lines without
    the raw key pass through unchanged.
    """
    if M166.USER_KEY not in line:
        return line
    q = M166.parse_me_ask(turn)
    chain = M166.chain_display(q["relations"]) if q else ""
    if line == "I don't know anyone called %s." % M166.USER_KEY:
        return "I don't know your %s yet." % chain
    out = line.replace("%s's" % M166.USER_KEY, "your")
    if (line.startswith("%s's " % M166.USER_KEY)
            or line.startswith("Saved: %s's " % M166.USER_KEY)):
        out = out[0].upper() + out[1:]
    if (out.startswith("I don't know your ") and out.endswith(".")
            and not out.endswith(" yet.")):
        out = out[:-1] + " yet."
    out = out.replace(M166.USER_KEY, "you")  # last resort: never leak raw
    return out


class Loop166AgentLoop(L162B.Loop162bAgentLoop):
    """Loop162bAgentLoop + first-person reply rendering (this file only)."""

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        event = super()._listening_tick()
        try:
            turn = event.get("detail", {}).get("turn", "")
        except Exception:  # noqa: BLE001 -- never break the loop on render
            return event
        claimed = (M166.parse_me_teach(turn) is not None
                   or M166.parse_me_ask(turn) is not None)
        if not claimed:
            return event
        try:
            event["said"] = [rewrite_me166_reply(line, turn)
                             for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event


DEFAULT_CONFIG166: dict = copy.deepcopy(L162B.DEFAULT_CONFIG162B)
DEFAULT_CONFIG166["ears"]["stand_in"] = (
    "Loop166Ears (loop162b + exp-166 first-person stage: 'My <R> is <V>. '"
    "teaches and 'Who/What/Where is|are my <chain>?' asks map to the "
    "reserved notebook entity USER through the canonical save/hop path; "
    "replies render your/Your; every other turn is the loop162b code "
    "literally) over loop150 chain")
DEFAULT_CONFIG166["daemon"]["module"] = "Loop166Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent166(cfg: dict | None = None) -> Loop166AgentLoop:
    """Build the loop162b shape with the 166 first-person mixin outermost."""
    cfg = dict(DEFAULT_CONFIG166, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop166Ears,
                      Loop166AgentLoop)


class _DaemonBase166(L162B._DaemonBase162b):
    """162b's daemon base with the loop166 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent166)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop166Daemon(_DaemonBase166):
    """Loop150Daemon shape with the loop166 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent166)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 166 first-person loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop162b)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG166 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG166)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG166)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop166Daemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent166(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
