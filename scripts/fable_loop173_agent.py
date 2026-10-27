#!/usr/bin/env python3
"""Experiment 173 -- loop173 = loop166 + user-name learning (muse).

Thin wrapper only (no existing file edited -- in particular no 166/162b
file): the behaviour change lives in scripts/fable_fix173_username.py
(Name173Mixin: user-name statements set the USER entity's name, user-name
questions answer it, stored-name-headed possessive turns resolve to USER,
"Is X <Owner>'s <R>?" compares by lookup). This file stacks it OUTERMOST
onto loop166:

  Loop173Ears(Name173Mixin, Loop166Ears):

the name stage runs first (it only claims turns loop166 always refuses,
plus stored-name-headed turns that cannot occur before a name is set --
and no suite input sets one); everything else takes the loop166 code path
literally, so non-name behaviour is byte-identical by construction.

Second change, REPLY RENDERING + namecheck answering (this file,
disclosed): Loop173AgentLoop reuses loop166's rewrite_me166_reply for
173-claimed turns, and additionally rewrites "yes"/"no" turns that complete
a pending USER-name change (their "Saved: USER's name is ..." reply would
otherwise leak the raw key). It answers {"act": "namecheck"} actions by
looking up (<Owner>, <R>) and comparing to the stored name, returning the
reasoner's own record untouched when the lookup misses (so unknown wordings
stay exactly the existing ones).

Daemon launch (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop173_agent.py --daemon --dir DIR \\
    --config artifacts/fable-username173-20260922/loop173-config.json
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

import fable_fix166_me as M166  # noqa: E402 (USER key, parsers, read-only)
import fable_fix173_username as N173  # noqa: E402 (this experiment)
import fable_loop150_agent as L150  # noqa: E402 (wrapped base, read-only)
import fable_loop166_agent as L166  # noqa: E402 (wrapped base agent)


class Loop173Ears(N173.Name173Mixin, L166.Loop166Ears):
    """Loop166Ears + outermost exp-173 user-name stage."""

    name = "loop173-username"


def rewrite_name173_reply(line: str, turn: str) -> str:
    """Name-aware reply rendering (this file, disclosed).

    When no name (and no other fact) was ever taught, the USER entity does
    not exist yet, so a user-name question misses as UNKNOWN_ENTITY ("I
    don't know anyone called USER.") instead of taking the me166 MISSING
    path. Both miss shapes render as the honest don't-know
    "I don't know your name yet." -- never the raw key. Every other
    173-claimed turn reuses loop166's rewrite verbatim.
    """
    if (N173.parse_name_question(turn) is not None
            and line == "I don't know anyone called %s." % M166.USER_KEY):
        return "I don't know your name yet."
    return L166.rewrite_me166_reply(line, turn)


def _pre_pending_is_name_confirm(loop) -> bool:
    try:
        pend = loop.listening.pending
    except Exception:  # noqa: BLE001
        return False
    return (isinstance(pend, dict) and pend.get("kind") == "confirm"
            and pend.get("name") == M166.USER_KEY
            and pend.get("relation") == N173.NAME_REL)


class Loop173AgentLoop(L166.Loop166AgentLoop):
    """Loop166AgentLoop + name rendering + namecheck answering (this file)."""

    def _act(self, action: dict) -> dict:  # type: ignore[no-untyped-def]
        if isinstance(action, dict) and action.get("act") == "namecheck":
            return self._answer_namecheck(action)
        return super()._act(action)

    def _answer_namecheck(self, action: dict) -> dict:  # type: ignore[no-untyped-def]
        rec = self.reasoner.answer(
            {"name": action["owner"],
             "relations": list(action["relations"])}, self.nb)
        if rec.get("status") != "OK":
            return rec  # existing unknown wording, untouched
        ans = (rec.get("fields") or {}).get("answer")
        x = str(action.get("x", ""))
        owner = str(action.get("owner", ""))
        rel = " ".join(list(action.get("relations") or ["?"]))
        if ans is not None and _norm(ans).lower() == _norm(x).lower():
            return {"kind": "note",
                    "text": "Yes, %s is %s's %s." % (x, owner, rel)}
        return {"kind": "note",
                "text": "No, %s's %s is %s." % (owner, rel, ans)}

    def _listening_tick(self):  # type: ignore[no-untyped-def]
        try:
            turn = self.inbox[0] if self.inbox else ""
        except Exception:  # noqa: BLE001
            turn = ""
        completes = (N173._YESNO.match(_norm(turn)) is not None
                     and _pre_pending_is_name_confirm(self))
        event = super()._listening_tick()
        claimed = completes
        if not claimed:
            try:
                claimed = (
                    N173.parse_name_statement(turn) is not None
                    or N173.parse_name_question(turn) is not None
                    or self._x_claimed(turn))
            except Exception:  # noqa: BLE001
                claimed = False
        if not claimed:
            return event
        try:
            event["said"] = [rewrite_name173_reply(line, turn)
                             for line in event.get("said", [])]
        except Exception:  # noqa: BLE001
            pass
        return event

    def _x_claimed(self, turn: str) -> bool:  # type: ignore[no-untyped-def]
        try:
            knob = N173.current_name(self.nb)
        except Exception:  # noqa: BLE001
            return False
        if not knob:
            return False
        return (N173.parse_x_teach(turn, knob) is not None
                or N173.parse_x_ask(turn, knob) is not None
                or N173.parse_name_check(turn, knob) is not None)


def _norm(text: object) -> str:
    return " ".join(str(text).split())


DEFAULT_CONFIG173: dict = copy.deepcopy(L166.DEFAULT_CONFIG166)
DEFAULT_CONFIG173["ears"]["stand_in"] = (
    "Loop173Ears (loop166 + exp-173 user-name stage: name statements set "
    "the reserved USER entity's name through the listening change-prompt, "
    "name questions answer it, stored-name-headed possessive turns resolve "
    "to USER; every other turn is the loop166 code literally) over loop166")
DEFAULT_CONFIG173["daemon"]["module"] = "Loop173Daemon (this file)"


def _swap_loop(loop, ears_cls, loop_cls):
    loop.ears.__class__ = ears_cls
    loop.ears.name = ears_cls.name
    loop.__class__ = loop_cls
    return loop


def build_agent173(cfg: dict | None = None) -> Loop173AgentLoop:
    """Build the loop166 shape with the 173 user-name mixin outermost."""
    cfg = dict(DEFAULT_CONFIG173, **(cfg or {}))
    return _swap_loop(L150.build_agent150(cfg), Loop173Ears,
                      Loop173AgentLoop)


class _DaemonBase173(L166._DaemonBase166):
    """166's daemon base with the loop173 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent173)

    def __init__(self, root, cfg: dict | None = None,
                 idle_seconds: float = 30.0,
                 sleep_threshold: int | None = None) -> None:
        super().__init__(root, cfg=cfg, idle_seconds=idle_seconds,
                         sleep_threshold=sleep_threshold)
        self.idle_seconds = float(idle_seconds)


class Loop173Daemon(_DaemonBase173):
    """Loop150Daemon shape with the loop173 agent inside (mailbox same)."""

    _builder = staticmethod(build_agent173)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 173 user-name loop")
    parser.add_argument("--config", default=None,
                        help="JSON config (same plug points as loop166)")
    parser.add_argument("--write-config", default=None,
                        help="write DEFAULT_CONFIG173 to PATH and exit")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--dir", default=None, help="daemon directory")
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", default=None,
                        help="one turn through a fresh build, then exit")
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)

    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG173)
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"wrote {args.write_config}")
        return 0

    cfg = copy.deepcopy(DEFAULT_CONFIG173)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    if args.daemon:
        if not args.dir:
            parser.error("--daemon needs --dir")
        daemon = Loop173Daemon(args.dir, cfg=cfg,
                               idle_seconds=args.idle_seconds)
        return daemon.run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        loop = build_agent173(cfg)
        print(" ".join(loop.turn(args.once)), flush=True)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
