#!/usr/bin/env python3
"""Exp 280m agent: join of the talking line's three pieces on base 260.

Everything is 260 (scripts/claude_loop260_agent.py, read-only) plus the
piece files imported read-only and unchanged, installed in the note's
order, inner to outer:

  260, then 281, then 280/280b, then 282/282b.

That is: turn282b(turn282(turn280b(turn280(turn281(turn260(...)))))).
No new behaviour: the one new file is this join agent (plus its config).
Each layer only ever substitutes the reply of a turn its own head already
mishandled (or serves its sealed text), and otherwise passes through
byte-identical, so the three triggers never fire on the same turn (shown
on the builder's own dev turns before the seal; 0 overlaps).

It is installed inside the build (like 260/281/280/282), so the daemon's
boot reconcile already runs through it. The daemon keeps
SrcGuardMixin228 first, exactly where 260 has it.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_fix228_srcguard as G228  # noqa: E402 (228 guard, read-only)
from claude_fix228_srcguard import SrcGuardMixin228  # noqa: E402

G228.install_srcguard228()

import claude_fix280_capab as F280  # noqa: E402 (piece, read-only)
import claude_fix280b_general as F280B  # noqa: E402 (piece, read-only)
import claude_fix281_called as F281  # noqa: E402 (piece, read-only)
import claude_fix282_small as F282  # noqa: E402 (piece, read-only)
import claude_fix282b_vocab as F282B  # noqa: E402 (piece, read-only)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop260_agent as L260  # noqa: E402 (base, read-only)
import claude_loop282b_agent as L282B  # noqa: E402 (config base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build280m(cfg=None):
    loop = L260._build260(cfg)          # base 260 (138m + 224/224c + 260)
    F281.install_called281(loop)        # innermost piece (over 260)
    F280.install_capab280(loop)         # 280 over 281
    F280B.install_general280b(loop)     # 280b over 280
    F282.install_small282(loop)         # 282 over 280b
    F282B.install_small282b(loop)       # 282b outermost
    return loop


def _with_280m(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build280m)]):
        return fn(*args, **kwargs)


NOTE280M = ("loop280m: join of 281 + 280/280b + 282/282b on base 260 "
            "(outermost turn stack "
            "turn282b(turn282(turn280b(turn280(turn281(turn260))))))")


def _base_config280m() -> dict:
    cfg = copy.deepcopy(L282B.DEFAULT_CONFIG282B)
    cfg["daemon"]["module"] = (
        "Loop280mDaemon (scripts/claude_loop280m_agent.py) over "
        "Loop138kDaemon with the 138m classes")
    cfg["self"] = dict(cfg.get("self", {}))
    cfg["self"]["rule281"] = (
        "281 (scripts/claude_fix281_called.py): trailing called/named, "
        "'what do you call X?' and 'name of X?' question turns are read as "
        "the plain possessive question; teaches and writes untouched; "
        "never writes")
    cfg["self"]["rule280"] = (
        "280 (scripts/claude_fix280_capab.py): general ability questions and "
        "any C24-shaped head reply are answered with the sealed CAN280 text "
        "(6 table-backed abilities, 3 dropped); everything else byte-identical "
        "to the layer below; never writes")
    cfg["self"]["rule280b"] = (
        "280b (scripts/claude_fix280b_general.py): question-shaped turns "
        "addressing the assistant with an ability cue and no named "
        "entity/relation get the sealed CAN280 text (0 writes); "
        "'Can you <specific>?' keeps the lower reply; everything else "
        "byte-identical; never writes")
    cfg["self"]["rule282"] = (
        "282 (scripts/claude_fix282_small.py): whole-turn pure-small-talk "
        "greetings and closings that the head mishandles get the head's own "
        "canonical reply for their class; mixed turns keep the lower route; "
        "never writes")
    cfg["self"]["rule282b"] = (
        "282b (scripts/claude_fix282b_vocab.py): a whole turn is small talk "
        "when every word belongs to the sealed vocabulary, it holds a "
        "greeting/thanks/closing word, and it names no stored entity and no "
        "relation word; class = the first such word; mishandled turns get "
        "the head's own canonical reply for their class; mixed turns keep "
        "the lower route; never writes")
    cfg["exp280m"] = {
        "base": "loop260 (scripts/claude_loop260_agent.py)",
        "added": ["281 called/named layer", "280 ability table + 280b "
                  "general-question layer", "282 small-talk + 282b "
                  "vocabulary layer (all outermost, instance, in order)"],
        "instance": ["turn282b(turn282(turn280b(turn280(turn281(turn260("
                     "turn224c(turn224(class turn))))))))"],
    }
    return cfg


DEFAULT_CONFIG280M: dict = _base_config280m()


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("280m: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("280m: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("280m: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn282b":
        raise RuntimeError("280m: turn282b not outermost")
    if getattr(loop.turn282b_inner, "__name__", "") != "turn282":
        raise RuntimeError("280m: 282 not under turn282b")
    if getattr(loop.turn282_inner, "__name__", "") != "turn280b":
        raise RuntimeError("280m: 280b not under turn282")
    if getattr(loop.turn280b_inner, "__name__", "") != "turn280":
        raise RuntimeError("280m: 280 not under turn280b")
    if getattr(loop.turn280_inner, "__name__", "") != "turn281":
        raise RuntimeError("280m: 281 not under turn280")
    if getattr(loop.turn281_inner, "__name__", "") != "turn260":
        raise RuntimeError("280m: 260 not under turn281")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("280m: 224c not under turn260")
    loop.notes.append(L260.NOTE260)
    loop.notes.append(NOTE280M)


def build_agent280m(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG280M, **(cfg or {}))
    loop = _with_280m(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes280mMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    280m-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_280m(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop280mDaemon(SrcGuardMixin228, Classes280mMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 280m
    build mixin ahead of the 220 mixin, exactly as 260 stacks its own."""


assert [c.__name__ for c in Loop280mDaemon.__mro__][:5] == [
    "Loop280mDaemon", "SrcGuardMixin228", "Classes280mMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 280m (join on 260)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG280M)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG280M)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop280mDaemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent280m(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
