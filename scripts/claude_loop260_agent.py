#!/usr/bin/env python3
"""Exp 260 agent: 138m + one outermost turn-opener layer (one change).

Everything is 138m (scripts/claude_loop138m_agent.py, read-only) except
scripts/claude_fix260_openers.py install_openers260, which wraps the whole
built turn (outside 138m's 224/224c instance wrappers, so a stripped turn
runs through the entire head exactly as if typed alone) and adds the
opener-comma write guard at the inner ears and at _act.

It is installed inside the build (like 224/224c), so the daemon's boot
reconcile already runs through it. The daemon keeps SrcGuardMixin228 first.
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

import claude_fix260_openers as F260  # noqa: E402 (THE ONE CHANGE)
import claude_loop138k_agent as L138K  # noqa: E402 (read-only)
import claude_loop138m_agent as L138M  # noqa: E402 (base, read-only)
import fable_loop138j_agent as L138J  # noqa: E402 (build site, read-only)


def _build260(cfg=None):
    loop = L138M._build138j_plus224c(cfg)   # 138m build (224 + 224c)
    F260.install_openers260(loop)           # outermost
    return loop


def _with_260(fn, *args, **kwargs):
    with L138M._Swap([(L138J, "Loop138jEars", L138M.Loop138mEars),
                      (L138J, "Loop138jAgentLoop", L138M.Loop138mAgentLoop),
                      (L138J, "build_agent138j", _build260)]):
        return fn(*args, **kwargs)


NOTE260 = ("loop260: loop138m + 260 turn openers/greetings never part of a "
           "fact (outermost turn layer + opener-comma write guard)")

DEFAULT_CONFIG260: dict = copy.deepcopy(L138M.DEFAULT_CONFIG138M)
DEFAULT_CONFIG260["daemon"]["module"] = (
    "Loop260Daemon (scripts/claude_loop260_agent.py) over Loop138kDaemon "
    "with the 138m classes")
DEFAULT_CONFIG260["self"] = dict(DEFAULT_CONFIG260.get("self", {}))
DEFAULT_CONFIG260["self"]["rule260"] = (
    "260 (scripts/claude_fix260_openers.py): listed openers/greetings at the "
    "start of a turn (at most 2) are dropped when the head gives the rest a "
    "non-clarify reply; bare greetings get the head's reply to 'Hello.'; no "
    "stored subject may start with a listed opener + comma")
DEFAULT_CONFIG260["exp260"] = {
    "base": "loop138m (scripts/claude_loop138m_agent.py)",
    "added": ["260 turn openers + greetings layer (outermost, instance)"],
    "instance": ["turn260(turn224c(turn224(class turn)))"],
}


def _check(loop):
    if not isinstance(loop, L138M.Loop138mAgentLoop):
        raise RuntimeError("260: loop is not Loop138mAgentLoop")
    if not isinstance(getattr(loop, "_inner138j_ears", None),
                      L138M.Loop138mEars):
        raise RuntimeError("260: inner ears are not Loop138lEars")
    if not G228.is_installed():
        raise RuntimeError("260: 228 guard not installed")
    t = vars(loop).get("turn")
    if getattr(t, "__name__", "") != "turn260":
        raise RuntimeError("260: turn260 not installed")
    if getattr(loop.turn260_inner, "__name__", "") != "turn224c":
        raise RuntimeError("260: 224c not under turn260")
    loop.notes.append(L138M.NOTE138M)
    loop.notes.append(NOTE260)


def build_agent260(cfg: dict | None = None):
    G228.install_srcguard228()
    cfg = dict(DEFAULT_CONFIG260, **(cfg or {}))
    loop = _with_260(L138K.build_agent138k, cfg)
    _check(loop)
    return loop


class Classes260Mixin:
    """Daemon mixin: 138k's daemon __init__ with the 138m classes and the
    260-installing build swapped in for the build."""

    def __init__(self, *args, **kwargs):
        G228.install_srcguard228()
        _with_260(super().__init__, *args, **kwargs)
        _check(self.loop)


class Loop260Daemon(SrcGuardMixin228, Classes260Mixin,
                    L138K.RestartIndex220Mixin, L138J.Loop138jDaemon):
    """Loop138kDaemon's own bases (228 guard > 220 restart index >
    Loop138jDaemon) with SrcGuardMixin228 first and the 260 build mixin
    (138m classes + the 260 layer) ahead of the 220 mixin, as 138m's
    Classes138mMixin sits ahead of Loop138kDaemon."""


assert [c.__name__ for c in Loop260Daemon.__mro__][:5] == [
    "Loop260Daemon", "SrcGuardMixin228", "Classes260Mixin",
    "RestartIndex220Mixin", "Loop138jDaemon"]


def main(argv=None) -> int:
    import argparse
    import json
    import fable_loop90_agent as L90  # noqa: E402 (read-only)
    ap = argparse.ArgumentParser(description="Exp 260 (138m + openers)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--write-config", default=None)
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--idle-seconds", type=float, default=30.0)
    ap.add_argument("--once", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args(argv)
    if args.write_config:
        out = copy.deepcopy(DEFAULT_CONFIG260)
        out["thinker"]["module"] = L90.THINKER_MODULE
        Path(args.write_config).write_text(json.dumps(out, indent=1),
                                           encoding="utf-8")
        print(f"Wrote {args.write_config}")
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG260)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
    if args.daemon or (args.dir and not args.once):
        if not args.dir:
            ap.error("--daemon needs --dir")
        return Loop260Daemon(args.dir, cfg=cfg,
                             idle_seconds=args.idle_seconds).run()
    if args.once:
        cfg["state_dir"] = args.state_dir or cfg.get("state_dir", ".")
        print(" ".join(build_agent260(cfg).turn(args.once)), flush=True)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
