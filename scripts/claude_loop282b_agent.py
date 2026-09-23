#!/usr/bin/env python3
"""Exp 282b agent: 282 + one outermost vocabulary small-talk layer.

Everything is 282 (scripts/claude_loop282_agent.py, read-only) except
scripts/claude_fix282b_vocab.py install_small282b, which wraps the whole
built turn outside 282's turn282 (so a canonical small-talk reply runs
through the entire head exactly as if typed alone) and only ever
substitutes the reply of a whole-turn pure-small-talk turn that the head
already mishandled, with the head's own canonical reply for its class.

It is installed inside the build (like 260/281/282), so the daemon's
boot reconcile already runs through it. The daemon keeps
SrcGuardMixin228 first, exactly where 282 has it.
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

import claude_fix282b_vocab as F282B  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop282_agent as L282  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build282b(cfg=None):
    loop = L282._build282(cfg)        # 282 build (260 + small282)
    F282B.install_small282b(loop)     # outermost
    return loop


def _with_282b(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build282b)]):
        return fn(*args, **kwargs)


NOTE282B = ("loop282b: loop282 + 282b whole-turn small talk by sealed "
            "vocabulary (outermost turn layer; class = first "
            "greeting/thanks/closing word)")


DEFAULT_CONFIG282B: dict = copy.deepcopy(L282.DEFAULT_CONFIG282)
DEFAULT_CONFIG282B["daemon"]["module"] = (
    "Loop282bDaemon (scripts/claude_loop282b_agent.py) over "
    "Loop138kDaemon with the 138m classes")
DEFAULT_CONFIG282B["self"] = dict(DEFAULT_CONFIG282B.get("self", {}))
DEFAULT_CONFIG282B["self"]["rule282b"] = (
    "282b (scripts/claude_fix282b_vocab.py): a whole turn is small talk "
    "when every word (lowercased, punctuation/emoji stripped) belongs "
    "to the sealed vocabulary, it holds a greeting/thanks/closing "
    "word, and it names no stored entity and no relation word; class "
    "= the first such word; mishandled turns get the head's own "
    "canonical reply for their class; mixed turns keep 282's route; "
    "never writes")
DEFAULT_CONFIG282B["exp282b"] = {
    "base": "loop282 (scripts/claude_loop282_agent.py)",
    "added": ["282b vocabulary small-talk layer (outermost, instance)"],
    "instance": ["turn282b(turn282(turn260(turn224c(class turn))))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("282b: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("282b: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("282b: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn282b":
        raise RuntimeError("282b: turn282b not installed")
    if getattr(loop.turn282b_inner, "__name__", "") != "turn282":
        raise RuntimeError("282b: 282 not under turn282b")
    if getattr(loop.turn282_inner, "__name__", "") != "turn260":
        raise RuntimeError("282b: 260 not under turn282")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("282b: 224c not under turn260")
    loop.notes.append(L282.NOTE282)
    loop.notes.append(NOTE282B)


def build_agent282b(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG282B, **(cfg or {}))
    loop = _with_282b(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes282bMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    282b-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_282b(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop282bDaemon(SrcGuardMixin228, Classes282bMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 282b
    build mixin ahead of the 220 mixin, exactly as 282 stacks its own."""


assert [c.__name__ for c in Loop282bDaemon.__mro__][:5] == [
    "Loop282bDaemon", "SrcGuardMixin228", "Classes282bMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 282b (282 + vocab small talk)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG282B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG282B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop282bDaemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent282b(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
