#!/usr/bin/env python3
"""Experiment 173b -- loop173b = loop173 + word-name mixin (muse).

Thin wrapper only (no existing file edited -- in particular no 173/166
file): the behaviour change lives in scripts/fable_fix173b_username.py
(Name173bMixin: 173b name-shape test for user-name statements only).
This file stacks it OUTERMOST onto loop173:

  Loop173bEars(N173b.Name173bMixin, L173.Loop173Ears):

Name173bMixin handles name statements itself (173b parser) and bypasses
loop173's name stage exactly when 173 would claim but 173b rejects
(Call-me-lowercase, sealed case S13); every other turn takes the loop173
code path literally. The listening tick below mirrors loop173's tick but
keys the reply-rewrite flag on the 173b parser, so S13 keeps loop166's
clarify reply byte-identically.

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop173b_agent.py --daemon --dir DIR \\
    --config artifacts/fable-username173b-20260922/loop173b-config.json
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

import fable_fix166_me as M166  # noqa: E402 (USER key, read-only)
import fable_fix173_username as N173  # noqa: E402 (base shapes, read-only)
import fable_fix173b_username as N173b  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)
import fable_loop173_agent as L173  # noqa: E402 (wrapped base agent)


class Loop173bEars(N173b.Name173bMixin, L173.Loop173Ears):
    """Loop173Ears + outermost exp-173b word-name stage."""

    name = "loop173b-username"


def _norm(text: object) -> str:
    return " ".join(str(text).split())


class Loop173bAgentLoop(L173.Loop173AgentLoop):
    """Loop173AgentLoop with the 173b claimed-turn flag (this file)."""

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        try:
            turn = self.inbox[0] if self.inbox else ""
        except Exception:  # noqa: BLE001
            turn = ""
        completes = (N173._YESNO.match(_norm(turn)) is not None
                     and L173._pre_pending_is_name_confirm(self))
        event = super(L173.Loop173AgentLoop, self)._listening_tick()
        claimed = completes
        if not claimed:
            try:
                claimed = (
                    N173b.parse_name_statement_173b(turn) is not None
                    or N173.parse_name_question(turn) is not None
                    or self._x_claimed(turn))
            except Exception:  # noqa: BLE001
                claimed = False
        if not claimed:
            return event
        try:
            event["said"] = [L173.rewrite_name173_reply(line, turn)
                             for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event


DEFAULT_CONFIG173B: dict = copy.deepcopy(L173.DEFAULT_CONFIG173)
DEFAULT_CONFIG173B["ears"]["stand_in"] = (
    "Loop173bEars (loop173 + exp-173b word-name stage: My-name/Call-me "
    "accept 1-3 letter tokens even if dictionary words except the sealed "
    "closed list/determiner/digit; Call-me requires Title-case; I'm keeps "
    "173's rule with propernames added; every other turn is the loop173 "
    "code literally) over loop173")
DEFAULT_CONFIG173B["daemon"]["module"] = "Loop173bDaemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent173b(cfg: dict | None = None) -> Loop173bAgentLoop:
    """Build the loop173 shape with the 173b word-name mixin outermost."""
    cfg = dict(DEFAULT_CONFIG173B, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop173bEars,
                      Loop173bAgentLoop)


class _DaemonBase173b(L173._DaemonBase173):
    """173's daemon base with the loop173b agent inside (mailbox same)."""

    _builder = staticmethod(build_agent173b)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super(L173._DaemonBase173, self).__init__(
            root, cfg=cfg, idle_seconds=idle_seconds,
            sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop173bDaemon(_DaemonBase173b):
    """Loop150Daemon shape with the loop173b agent inside (mailbox same)."""

    _builder = staticmethod(build_agent173b)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 173b word-name loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop173)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG173B to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG173B)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG173B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop173bDaemon(args.dir, cfg=cfg,
                                idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent173b(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
