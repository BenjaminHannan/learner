#!/usr/bin/env python3
"""Exp 281b agent: 281 + one outermost casual-typing layer (one change).

Everything is 281 (scripts/claude_loop281_agent.py, read-only) except
scripts/claude_fix281b_casual.py install_casual281b, which wraps the whole
built turn outside 281's turn281 (so a formalised question runs through the
entire head exactly as if typed alone) and only ever substitutes the reply
of a turn the head already failed on, with the head's own answer to the
formal called/named question.

It is installed inside the build (like 281/280), so the daemon's boot
reconcile already runs through it. The daemon keeps SrcGuardMixin228
first, exactly where 281 has it.
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

import claude_fix281b_casual as F281B  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop260_agent as L260  # noqa: E402 (read-only)
import claude_loop281_agent as L281  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build281b(cfg=None):
    loop = L281._build281(cfg)        # 281 build (260 + called layer)
    F281B.install_casual281b(loop)    # outermost
    return loop


def _with_281b(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build281b)]):
        return fn(*args, **kwargs)


NOTE281B = ("loop281b: loop281 + casual called/named questions read as the "
            "formal called/named question (outermost turn layer)")


DEFAULT_CONFIG281B: dict = copy.deepcopy(L281.DEFAULT_CONFIG281)
DEFAULT_CONFIG281B["daemon"]["module"] = (
    "Loop281bDaemon (scripts/claude_loop281b_agent.py) over Loop138kDaemon "
    "with the 138m classes")
DEFAULT_CONFIG281B["self"] = dict(DEFAULT_CONFIG281B.get("self", {}))
DEFAULT_CONFIG281B["self"]["rule281b"] = (
    "281b (scripts/claude_fix281b_casual.py): a called/named question typed "
    "casually (any case, whats/what's/what is, no-apostrophe possessive of "
    "a known entity, missing ? after a question word) is read as the "
    "formal called/named question; teaches and writes untouched; never "
    "writes")
DEFAULT_CONFIG281B["exp281b"] = {
    "base": "loop281 (scripts/claude_loop281_agent.py)",
    "added": ["281b casual called/named layer (outermost, instance)"],
    "instance": ["turn281b(turn281(turn260(turn224c(class turn))))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("281b: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("281b: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("281b: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn281b":
        raise RuntimeError("281b: turn281b not installed")
    if getattr(loop.turn281b_inner, "__name__", "") != "turn281":
        raise RuntimeError("281b: 281 not under turn281b")
    if getattr(loop.turn281_inner, "__name__", "") != "turn260":
        raise RuntimeError("281b: 260 not under turn281")
    loop.notes.append(L260.NOTE260)
    loop.notes.append(L281.NOTE281)
    loop.notes.append(NOTE281B)


def build_agent281b(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG281B, **(cfg or {}))
    loop = _with_281b(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes281bMixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    281b-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_281b(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop281bDaemon(SrcGuardMixin228, Classes281bMixin,
                     L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 281b
    build mixin ahead of the 220 mixin, exactly as 281 stacks its own."""


assert [c.__name__ for c in Loop281bDaemon.__mro__][:5] == [
    "Loop281bDaemon", "SrcGuardMixin228", "Classes281bMixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 281b (281 + casual)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG281B)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG281B)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop281bDaemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent281b(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
