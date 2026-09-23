#!/usr/bin/env python3
"""Exp 281 agent: 260 + one outermost called/named-question layer (one change).

Everything is 260 (scripts/claude_loop260_agent.py, read-only) except
scripts/claude_fix281_called.py install_called281, which wraps the whole
built turn outside 260's turn260 (so a rewritten question runs through the
entire head exactly as if typed alone) and only ever substitutes the reply
of a question turn that the head already failed on, with the head's own
answer to the plain possessive question.

It is installed inside the build (like 260/280), so the daemon's boot
reconcile already runs through it. The daemon keeps SrcGuardMixin228
first, exactly where 260 has it.
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

import claude_fix281_called as F281  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (read-only)
import claude_loop260_agent as L260  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build281(cfg=None):
    loop = L260._build260(cfg)        # 260 build (138m + 224/224c + 260)
    F281.install_called281(loop)      # outermost
    return loop


def _with_281(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build281)]):
        return fn(*args, **kwargs)


NOTE281 = ("loop281: loop260 + 281 called/named questions read as the plain "
           "possessive question (outermost turn layer, question turns only)")


DEFAULT_CONFIG281: dict = copy.deepcopy(L260.DEFAULT_CONFIG260)
DEFAULT_CONFIG281["daemon"]["module"] = (
    "Loop281Daemon (scripts/claude_loop281_agent.py) over Loop138kDaemon "
    "with the 138m classes")
DEFAULT_CONFIG281["self"] = dict(DEFAULT_CONFIG281.get("self", {}))
DEFAULT_CONFIG281["self"]["rule281"] = (
    "281 (scripts/claude_fix281_called.py): trailing called/named, "
    "'what do you call X?' and 'name of X?' question turns are read as the "
    "plain possessive question; teaches and writes untouched; never writes")
DEFAULT_CONFIG281["exp281"] = {
    "base": "loop260 (scripts/claude_loop260_agent.py)",
    "added": ["281 called/named question layer (outermost, instance)"],
    "instance": ["turn281(turn260(turn224c(turn224(class turn))))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("281: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("281: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("281: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn281":
        raise RuntimeError("281: turn281 not installed")
    if getattr(loop.turn281_inner, "__name__", "") != "turn260":
        raise RuntimeError("281: 260 not under turn281")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("281: 224c not under turn260")
    loop.notes.append(L260.NOTE260)
    loop.notes.append(NOTE281)


def build_agent281(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG281, **(cfg or {}))
    loop = _with_281(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes281Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    281-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_281(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop281Daemon(SrcGuardMixin228, Classes281Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases with SrcGuardMixin228 first and the 281
    build mixin ahead of the 220 mixin, exactly as 260 stacks its own."""


assert [c.__name__ for c in Loop281Daemon.__mro__][:5] == [
    "Loop281Daemon", "SrcGuardMixin228", "Classes281Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 281 (260 + called/named)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG281)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG281)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop281Daemon(
            args.dir, cfg=cfg, idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent281(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
